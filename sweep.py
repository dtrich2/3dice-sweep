#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
import concurrent.futures
import threading
import time
from itertools import permutations
from SALib.sample import saltelli
from SALib.analyze import sobol
from SALib.test_functions import Ishigami
import numpy as np
import pprint
import os
import sys
import multiprocessing
import traceback

#helper files
from sweephelper import *
from ic import *
from gen_mc_power import *
import calcs

def sweep(ymlfile):
	duplicate_int=1
	resultsfile='./results/'+ymlfile+'.csv'
	while os.path.isfile(resultsfile):
		duplicate_int=duplicate_int+1
		resultsfile='./results/'+ymlfile+str(duplicate_int)+'.csv'
	cfg=getcfg(ymlfile)
	pspace=getpspace(cfg)
	flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
	defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
	dimension_keys=getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
	if 'layerorder' in dimension_keys:
		print("Lc,Lm,Zm,alpha overriden\n")
	print(pspace.get_info_str())
	print("ETA: {:.2f} hours".format(pspace.volume*33/(3600)))
	print("{}it total".format(pspace.volume))
	#printinfo(cfg)
	simdir=prep_filesystem(ymlfile)

	#SWEEP PARAMETER SPACE
	#results = open(resultsfile, "w")
	if 'fitting' in cfg:
		toinsert=['g', 'lh']
	else:
		toinsert=[]
	writeheader(flat_pspace, dimension_keys, resultsfile, toinsert=toinsert) #['nsteps', 'layerorder', 'alpha'])
	t = time.time()
	nsims_done=0
	with concurrent.futures.ProcessPoolExecutor(max_workers=cfg['maxworkers']) as pool:
		m = multiprocessing.Manager()
		lock = m.Lock()
		for params in pspace:
			#simdata[2] is powers
			simdata=[params, cfg, {}, simdir, list(dimension_keys), resultsfile]
			if cfg['parallel']=='True':
				#keep only 
				pool.submit(sim_wrapper, simdata, handle_exceptions=True, lock=lock)
			if cfg['parallel']=='False':
				print(f"{nsims_done} of {pspace.volume} sims done in {(time.time()-t)/3600} hours")
				sim_wrapper(simdata, handle_exceptions=False, lock=lock)
				nsims_done=nsims_done+1
	#results.close()
	print(f"{pspace.volume} sims done in {(time.time()-t)/3600} hours")
	
def sobol_SA(ymlfile, N):
	resultsfile='./results/SA/'+ymlfile+'_points.csv'
	output_filename='./results/SA/'+ymlfile+'.txt'
	cfg=getcfg(ymlfile)
	flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
	dimension_keys=getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
	defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
	if defaults['floorplan']['powerfile'] != 'random':
		powerfile='powers/'+defaults['floorplan']['powerfile']
		powers=getcfg(powerfile)
	else:
		powers={}
	if 'layerorder' in dimension_keys:
		print("Lc,Lm,Zm,alpha overriden\n")
	simdir=prep_filesystem(ymlfile)

	#GET DEFAULT PARAMETER SPACE
	flat_pspace_search=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=False)
	
	#BUILD SENSITIVITY PROBLEM
	problem={'names':[], 'bounds':[]}
	for param_key in flat_pspace_search:
		if param_key[-7:]=='-bounds':
			problem['names'].append(param_key[:-7])
			problem['bounds'].append(flat_pspace_search[param_key])
	if defaults['floorplan']['powerfile'] == 'random':
		problem['names'].append('floorplan-config')
		problem['bounds'].append([0,1])
	problem['num_vars']=len(problem['names'])
	print(problem)
	problem_size=N*(2*problem['num_vars']+2)
	print("{} sims required".format(problem_size))
	
	#RANDOMLY SAMPLED SPACE
	param_values = saltelli.sample(problem, N)

	#WRITE MONTE CARLO FLOORPLANS
	floorplan=defaults['floorplan']
	unique_configs=list(set(np.array(param_values).T[-1]))
	for floorplan_config in unique_configs:
		powerfile='powers/'+str(floorplan_config)
		powers=generate_full_floorplan(defaults['Lc'], floorplan['n-tiles'], floorplan['mean'], floorplan['sd'], floorplan['peak'], floorplan['mem-power'])
		f = open('ics/'+powerfile+'.yml', 'w+')
		yaml.dump(powers, f, default_flow_style=False)

	#PERFORM SIMS
	Y = np.zeros([param_values.shape[0]])
	Tavg_list=np.zeros([param_values.shape[0]])
	results = open(resultsfile, "w")
	writeheader(flat_pspace, dimension_keys, results, toinsert=['nsteps', 'layerorder', 'alpha'])
	t = time.time()
	mythreads=[]
	flat_pspace_search['floorplans']=[]
	with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
		for i, X in enumerate(param_values):
			for param_key,newvalue in zip(problem['names'],X):
				flat_pspace_search[param_key]=newvalue
			simdata=(expand(flat_pspace_search), cfg, powers, simdir, dimension_keys, results)
			mythreads.append(pool.submit(sim_wrapper,simdata))
			if not flat_pspace_search['floorplan-config'] in flat_pspace_search['floorplans']:
				flat_pspace_search['floorplans'].append(flat_pspace_search['floorplan-config'])
	for mythread,i in zip(mythreads,range(len(mythreads))):
		Y[i],Tavg_list[i]=mythread.result()
	
	#ANALYZE AND PRINT RESULTS
	print(Y)
	print(Tavg_list)
	print("All done, {:.2f} hours elapsed. Analyzing and dumping results...".format((time.time()-t)/3600)+' '*20)
	results.close()
	Si = sobol.analyze(problem, Y, print_to_console=True)
	cleanup(["xaxis.txt", "yaxis.txt"])
	print_SA_results(Si,problem, param_values,Y,Tavg_list,output_filename)

def print_SA_results(Si,problem, param_values,Y,Tavg_list,output_filename):
	f=open(output_filename,"w")
	f.write("problem:"+pprint.pformat(problem, indent=1, width=200, depth=None, compact=False)+"\n")
	f.write("results (S): "+pprint.pformat(Si, indent=1, width=200, depth=None, compact=False)+"\n")
	for header in problem['names']:
		f.write(str(header))
		f.write(',')
	f.write("Tj, Tavg\n")
	for values, i in zip(param_values, range(len(param_values))):
		for value in values:
			f.write(str(value))
			f.write(',')
		f.write("{}, {}".format(str(Y[i]),str(Tavg_list[i])))
		f.write("\n")
	f.close()

def adjust_params(params,var_vals):
	#['beol_k', 'heatsink', 'si_thickness', 'Zm', 'orderscalar', 'trans_coupling', 'ild_k', 'Lm', 'secondary_coeff']
	for beol_mat in ['beol','computebeol','memtopbeol']:
		params['materials'][beol_mat]['k']=var_vals[0]
	params['heatsinks']['top']['coefficient']=var_vals[1]
	params['layers']['layerdict']['bottomlayer']['tiers']['si']=var_vals[2]
	params['materials']['transistors']['k']=var_vals[5]
	params['materials']['sio2']['k']=var_vals[6]
	params['Lm']=int(np.floor(var_vals[7]))
	params['heatsinks']['bottom']['coefficient']=var_vals[8]

def traverse_path(simdata, decision_rule, init_layers=None):
	Lc, Lm=(simdata[0]['Lc'],simdata[0]['Lm'])
	cfg=simdata[1]
	if not init_layers: init_layers=['compute']*Lc+['memory']*Lm
	elif Lc!=init_layers.count('compute') or Lm!=init_layers.count('memory'): raise RuntimeError('Lc={}, Lm={}, init_layers={}: does not match'.format(Lc,Lm,init_layers))
	layers=init_layers
	layerlist=[init_layers]
	nsteps=0
	layerorder=to_layerorder(layers, cfg['layermapping'])
	Tj_list=[build_ic_and_simulate(simdata, to_file=True, layers=['bottomlayer']+layers,toinsert=[nsteps, layerorder])[0]]
	while layers!=['memory']*Lm+['compute']*Lc:
		nsteps=nsteps+1
		incremented_layers=get_incremented_layers(layers)
		results=[]
		with concurrent.futures.ThreadPoolExecutor(max_workers=10) as subpool:
			jobs=[]
			for candidate_layer in incremented_layers:
				layerorder=to_layerorder(['bottomlayer']+candidate_layer, cfg['layermapping'])
				jobs.append(subpool.submit(build_ic_and_simulate, simdata, to_file=True, layers=['bottomlayer']+candidate_layer, toinsert=[nsteps, layerorder]))
		for job in jobs: results.append(job.result()[0])
		if decision_rule=='max':
			Tj_list.append(max(results))
		elif decision_rule=='min':
			Tj_list.append(min(results))
		layers=incremented_layers[results.index(Tj_list[-1])]
		layerlist.append(layers)
	Tj_list.append(build_ic_and_simulate(simdata, to_file=True, layers=['bottomlayer']+layers, toinsert=[nsteps, layerorder])[0])
	return Tj_list

def sim_wrapper(simdata_old, handle_exceptions, lock):
	try:
		simdata=simdata_old[:]
		if 'layerorder' in simdata[0].keys():
			layerorder=simdata[0]['layerorder']
			if simdata[0]['floorplan']['powerfile'] == 'neuron':
				layer_list=[1]+[2]*simdata[0]['dimscalingfactor']
				layerorder=''
				for i in layer_list: layerorder=layerorder+str(i)
			layer=buildlayers(simdata[1]['layermapping'], layerorder)
			toinsert=[layerorder]
		else:
			Lc, Lm=(int(np.floor(simdata[0]['Lc']+0.99)),int(np.floor(simdata[0]['Lm']+0.99)))
			Zm=np.floor(simdata[0]['Zmratio']*((Lm*Lc)+0.99))
			orderscalar=simdata[0]['alpha']
			layer=specific_layer_order(Lc,Lm,Zm,alpha=orderscalar)
			if 'bottomlayer' in simdata[1]['layermapping']:
				layer=['bottomlayer']+layer
			layerorder=to_layerorder(layer, simdata[1]['layermapping'])
			toinsert=[] #[Zm, orderscalar]
		#build powers
		if simdata[0]['floorplan']['powerfile'] == 'neuron':
			simdata[2]={}
		elif simdata[0]['floorplan']['powerfile'] == 'random':
			simdata[2]={}	#doesn't make sense for a sweep, this shouldn't happen
		elif simdata[0]['floorplan']['powerfile'] == 'uniform' or simdata[0]['floorplan']['powerfile'] == 'power':
			powerfile='powers/'+simdata[0]['floorplan']['powerfile']
			simdata[2]=getcfg(powerfile)
		else:
			powerfile='powers/'+simdata[0]['floorplan']['powerfile']+'_'+str(simdata[0]['Lc'])+'layers'
			simdata[2]=getcfg(powerfile)
		results=build_ic_and_simulate(simdata, to_file=True, layers=layer, toinsert=toinsert, lock=lock)
	except Exception as e:
		if not handle_exceptions:
			raise
		else:
			#let the function handle the exception	
			print(e)
			trace_back = traceback.extract_tb(sys.exc_info()[2])
			# Format stacktrace
			stack_trace = list()
			for trace in trace_back:
				stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))
			print(stack_trace)
			
			results=[0,0,0]
			return (results[0], results[2])

def modify_power(powers, scalar=None, bg_power=None):
	if bg_power:
		powers['compute']['bgpowers']=[bg_power]
	if scalar:
		for layer_type in powers:
			for layernum, layer in enumerate(powers[layer_type]['hspowers']):
				for powernum, power in enumerate(layer):
					powers[layer_type]['hspowers'][layernum][powernum]=power*scalar
			for powernum, power in enumerate(powers[layer_type]['bgpowers']):
				powers[layer_type]['bgpowers'][powernum]=power*scalar
	return powers


def build_ic_and_simulate(simdata, to_file, layers, toinsert, lock):
	params, cfg, powers, simdir, dimension_keys, resultsfile=simdata
	preserve_simfiles=False
	if preserve_simfiles:
		mydir=simdir+'/a'+str(threading.get_ident())
	else:
		mydir=simdir+'/a'+str(int(time.time()*1000000))

	floorplan=params['floorplan']
	if floorplan['powerfile']=='random':
		powerfile='powers/'+str(params['floorplan-config'])
		powers=getcfg(powerfile)
	elif floorplan['powerfile']=='neuron':
		n_lines_orig=int(cfg['defaultdimensions'][0]/params['wlines'])
		n_lines=n_lines_orig*params['dimscalingfactor']
		params['activity-factor']=int(n_lines_orig*params['activity-factor'])/n_lines_orig
		n_activated_lines=int(n_lines_orig*params['activity-factor'])
		activated_lines=gen_activated_lines(n_activated_lines=n_activated_lines, n_layers=params['dimscalingfactor'], n_lines=n_lines)
		powers=generate_neuron_floorplan(n_lines=n_lines, activated_lines=activated_lines, activated_power=params['activated-power'])
		defaultdimensions=np.multiply(cfg['defaultdimensions'],params['dimscalingfactor'])
		defaultresolution=np.multiply(cfg['defaultresolution'],params['dimscalingfactor'])
	else:
		defaultdimensions=cfg['defaultdimensions']
		defaultresolution=cfg['defaultresolution']
	if 'scalar' in floorplan.keys():
		powers=modify_power(powers, floorplan['scalar'])
	if 'bgpower' in floorplan.keys():
		powers=modify_power(powers, bg_power=floorplan['bgpower'])
	if not 'lattices' in params.keys(): params['lattices']={}
	#for material in params['materials']:
	#	params['materials'][material]['k']=params['materials'][material]['k']/cfg['kscalar']
	my_layer_orders=cfg['tierorders'].copy()
	for layer in params['layers']['layerdict']:
		for tier in params['layers']['layerdict'][layer]['tiers']:
			if tier[-7:]!='-bounds':
				if params['layers']['layerdict'][layer]['tiers'][tier]<=0:	#remove layer if thickness 0
					if my_layer_orders[layer].index(tier)<params['layers']['layerdict'][layer]['sourcetier']:
						params['layers']['layerdict'][layer]['sourcetier']=params['layers']['layerdict'][layer]['sourcetier']-1
					my_layer_orders[layer]=[mytier for mytier in my_layer_orders[layer] if mytier != tier]
	if 'compute1' in powers.keys():
		nlayers=layers.count('compute')
		powers['compute']=powers['compute'+str(nlayers)]
	myic = ic(heatsinks=params['heatsinks'],
		materialdict=params['materials'],
		powers=powers,
		layerdict=params['layers']['layerdict'],
		latticedict=params['lattices'],
		tierorders=my_layer_orders,
		layers=layers,
		ncopies=params['ncopies'],
		dimensions=defaultdimensions,
		resolution=defaultresolution,
		mydir=mydir,
		pact_engine=cfg['engine'],
		n_cores=cfg['ncores'],
		outputfile="output")
	tj, tavglayers=myic.simulate(simulator=cfg['simulator'],verbose=True)	#fitting contains lh, g.
	if 'fitting' in cfg:
		g, lh=calcs.get_lh(tj=tj+273.15-params['heatsinks']['externalT'],p_dens=powers['compute']['bgpowers'][0], k=params['materials']['spreader']['kxy'], t=params['layers']['layerdict']['compute']['tiers']['spreader'], pitch=params['lattices']['through']['pitch'])
	#tj, tavglayers=(0, [1,2])
	tavg=sum(tavglayers)/len(tavglayers)
	infofile=mydir+'/siminfo.txt'
	flat_params=flatten(params)
	with lock:
		try:
			writeheader(flat_pspace=flat_params, keys=dimension_keys, resultsfile=infofile, toinsert=toinsert)
			writevalues(flat_params=flat_params, keys=dimension_keys, resultsfile=infofile, toinsert=toinsert)
			if to_file:
				#write results
				writevalues(flat_params=flatten(params), keys=dimension_keys, resultsfile=resultsfile, toinsert=toinsert)
				results = open(resultsfile, "a")
				if 'fitting' in cfg:
					results.write("{:.2f},{:.2f},".format(g, lh))
				results.write("{:.2f},{:.2f}".format(tj,tavg))
				for temp in tavglayers:
					results.write(",{:.2f}".format(temp))
				results.write("\n")
				results.flush()
				results.close()
		except Exception as e:
			print(e)
			trace_back = traceback.extract_tb(sys.exc_info()[2])
			# Format stacktrace
			stack_trace = list()
			for trace in trace_back:
				stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))
			print(stack_trace)

	return (tj, tavglayers, tavg)

#run this if called from command line
if __name__ == "__main__":
	ymlfile=sys.argv[1]
	#ymlfile='debugging'
	sweep(ymlfile=ymlfile)

