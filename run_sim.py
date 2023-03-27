import numpy as np, time, sys, traceback
from ic import ic_class,sweephelper,yamlhelper

def sim_wrapper(simdata_old, handle_exceptions, lock):
	try:
		simdata=simdata_old[:]
		layer,toinsert=make_layers(simdata)
		simdata[2]=build_powers(simdata,layer)
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

def make_layers(simdata):
	if 'layerorder' in simdata[0].keys():
		layerorder=simdata[0]['layerorder']
		if simdata[0]['floorplan']['powerfile'] == 'neuron':
			layer_list=[1]+[2]*simdata[0]['dimscalingfactor']
			layerorder=''
			for i in layer_list: layerorder=layerorder+str(i)
		layer=sweephelper.buildlayers(simdata[1]['layermapping'], layerorder)
		toinsert=[layerorder]
	else:
		Lc, Lm=(int(np.floor(simdata[0]['Lc']+0.99)),int(np.floor(simdata[0]['Lm']+0.99)))
		Zm=np.floor(simdata[0]['Zmratio']*((Lm*Lc)+0.99))
		orderscalar=simdata[0]['alpha']
		layer=yamlhelper.specific_layer_order(Lc,Lm,Zm,alpha=orderscalar)
		if 'bottomlayer' in simdata[1]['layermapping']:
			layer=['bottomlayer']+layer
		layerorder=sweephelper.to_layerorder(layer, simdata[1]['layermapping'])
		toinsert=[] #[Zm, orderscalar]
	return layer,toinsert

def build_powers(simdata,layers):
	floorplan=simdata[0]['floorplan']
	"""
	elif floorplan['powerfile'] == 'neuron':
		n_lines_orig=int(cfg['defaultdimensions'][0]/simdata[0]['wlines'])
		n_lines=n_lines_orig*simdata[0]['dimscalingfactor']
		simdata[0]['activity-factor']=int(n_lines_orig*simdata[0]['activity-factor'])/n_lines_orig
		n_activated_lines=int(n_lines_orig*simdata[0]['activity-factor'])
		activated_lines=sweephelper.gen_activated_lines(n_activated_lines=n_activated_lines, n_layers=simdata[0]['dimscalingfactor'], n_lines=n_lines)
		power=gen_mc_power.generate_neuron_floorplan(n_lines=n_lines, activated_lines=activated_lines, activated_power=simdata[0]['activated-power'])
	"""
	if floorplan['powerfile'] == 'random':
		powerfile='powers/'+str(simdata[0]['floorplan-config'])
		power=yamlhelper.getcfg(powerfile)
	elif floorplan['powerfile'] == 'uniform':
		power={}
	else:
		powerfile='powers/'+floorplan['powerfile']
		power=yamlhelper.getcfg(powerfile)
	if 'scalar' in floorplan.keys():
		power=modify_power(power, layers, scalar=floorplan['scalar'])
	if 'bgpower' in floorplan.keys():
		power=modify_power(power, layers, bg_power=floorplan['bgpower'])
	if 'compute1' in power.keys():
		nlayers=layers.count('compute')
		power['compute']=power['compute'+str(nlayers)]
	return power

def build_ic_and_simulate(simdata, to_file, layers, toinsert, lock):
	params, cfg, powers, simdir, dimension_keys, resultsfile=simdata
	mydir=simdir+'/a'+str(int(time.time()*1000000))
	
	#last-minute modifications
	if params['floorplan']['powerfile']=='neuron':
		defaultdimensions=np.multiply(cfg['defaultdimensions'],params['dimscalingfactor'])
		defaultresolution=np.multiply(cfg['defaultresolution'],params['dimscalingfactor'])
	else:
		defaultdimensions=cfg['defaultdimensions']
		defaultresolution=cfg['defaultresolution']
	if not 'lattices' in params.keys(): params['lattices']={}
	
	#remove zero-thickness layers
	my_layer_orders=cfg['tierorders'].copy()
	for layer in params['layers']['layerdict']:
		for tier in params['layers']['layerdict'][layer]['tiers']:
			#for every material layer in the tier
			if tier[-7:]!='-bounds': #for sobol
				if params['layers']['layerdict'][layer]['tiers'][tier]<=0:
					#remove layer if thickness 0
					if my_layer_orders[layer].index(tier)<params['layers']['layerdict'][layer]['sourcetier']:
						params['layers']['layerdict'][layer]['sourcetier']=params['layers']['layerdict'][layer]['sourcetier']-1
					my_layer_orders[layer]=[mytier for mytier in my_layer_orders[layer] if mytier != tier]
	
	#build and run IC object
	myic = ic_class.ic(heatsinks=params['heatsinks'],
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
	tj, tavglayers=myic.simulate(simulator=cfg['simulator'],verbose=False)	#fitting contains lh, g.
	if 'fitting' in cfg:
		pass #g, lh=saraswat_model.get_lh(tj=tj+273.15-params['heatsinks']['externalT'],p_dens=powers['compute']['bgpowers'][0], k=params['materials']['spreader']['kxy'], t=params['layers']['layerdict']['compute']['tiers']['spreader'], pitch=params['lattices']['through']['pitch'])
	#tj, tavglayers=(0, [1,2])
	tavg=sum(tavglayers)/len(tavglayers)
	infofile=mydir+'/siminfo.txt'
	flat_params=yamlhelper.flatten(params)
	with lock:
		try:
			yamlhelper.writeheader(flat_pspace=flat_params, keys=dimension_keys, resultsfile=infofile, toinsert=toinsert)
			yamlhelper.writevalues(flat_params=flat_params, keys=dimension_keys, resultsfile=infofile, toinsert=toinsert)
			if to_file:
				#write results
				yamlhelper.writevalues(flat_params=yamlhelper.flatten(params), keys=dimension_keys, resultsfile=resultsfile, toinsert=toinsert)
				results = open(resultsfile, "a")
				if 'fitting' in cfg:
					pass #results.write("{:.2f},{:.2f},".format(g, lh))
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

def modify_power(powers, layers, scalar=None, bg_power=None):
	if bg_power:
		if not type(bg_power) is list:
			bg_power=[bg_power]
		for power,layer in zip(bg_power,layers):
			if not layer in powers:
				powers[layer]={'hslocs': [], 'hslocs-mode': 'center', 'hspowers': [], 'hssize': [], 'bgpowers': []}
			powers[layer]['bgpowers'].append(power)
	if scalar:
		for layer_type in powers:
			for layernum, layer in enumerate(powers[layer_type]['hspowers']):
				for powernum, power in enumerate(layer):
					powers[layer_type]['hspowers'][layernum][powernum]=power*scalar
			for powernum, power in enumerate(powers[layer_type]['bgpowers']):
				powers[layer_type]['bgpowers'][powernum]=power*scalar
	return powers
