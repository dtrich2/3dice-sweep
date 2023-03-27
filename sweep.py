#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
from itertools import permutations
import concurrent.futures, threading, multiprocessing, time, pprint, os, sys, traceback, numpy as np, logging

#helper files
from ic import yamlhelper, sweephelper
import run_sim

def sweep(ymlfile):
	duplicate_int=1
	resultsfile='./results/'+ymlfile+'.csv'
	while os.path.isfile(resultsfile):
		duplicate_int=duplicate_int+1
		resultsfile='./results/'+ymlfile+str(duplicate_int)+'.csv'
	cfg=yamlhelper.getcfg(ymlfile)
	pspace=yamlhelper.getpspace(cfg)
	flat_pspace=yamlhelper.getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
	defaults=yamlhelper.getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
	dimension_keys=yamlhelper.getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
	if 'layerorder' in dimension_keys:
		print("Lc,Lm,Zm,alpha overridden\n")
	print(pspace.get_info_str())
	print("{}it total".format(pspace.volume))
	#printinfo(cfg)
	simdir=sweephelper.prep_filesystem(ymlfile)

	#SWEEP PARAMETER SPACE
	#results = open(resultsfile, "w")
	if 'fitting' in cfg:
		toinsert=['g', 'lh']
	else:
		toinsert=[]
	yamlhelper.writeheader(flat_pspace, dimension_keys, resultsfile, toinsert=toinsert) #['nsteps', 'layerorder', 'alpha'])
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
				pool.submit(run_sim.sim_wrapper, simdata, handle_exceptions=True, lock=lock)
			if cfg['parallel']=='False':
				run_sim.sim_wrapper(simdata, handle_exceptions=False, lock=lock)
				nsims_done=nsims_done+1
				logging.info(f"{nsims_done} of {pspace.volume} sims done in {(time.time()-t)/60:.2f} minutes")


#run this if called from command line
if __name__ == "__main__":
	ymlfile=sys.argv[1]
	level = logging.INFO #notset, debug, info, warning, error, critical
	FORMAT = '[%(levelname)s] %(asctime)s - %(message)s'
	logging.basicConfig(level=level, format=FORMAT)
	sweep(ymlfile=ymlfile)


"""
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
	layerorder=sweephelper.to_layerorder(layers, cfg['layermapping'])
	Tj_list=[run_sim.build_ic_and_simulate(simdata, to_file=True, layers=['bottomlayer']+layers,toinsert=[nsteps, layerorder])[0]]
	while layers!=['memory']*Lm+['compute']*Lc:
		nsteps=nsteps+1
		incremented_layers=sweephelper.get_incremented_layers(layers)
		results=[]
		with concurrent.futures.ThreadPoolExecutor(max_workers=10) as subpool:
			jobs=[]
			for candidate_layer in incremented_layers:
				layerorder=sweephelper.to_layerorder(['bottomlayer']+candidate_layer, cfg['layermapping'])
				jobs.append(subpool.submit(run_sim.build_ic_and_simulate, simdata, to_file=True, layers=['bottomlayer']+candidate_layer, toinsert=[nsteps, layerorder]))
		for job in jobs: results.append(job.result()[0])
		if decision_rule=='max':
			Tj_list.append(max(results))
		elif decision_rule=='min':
			Tj_list.append(min(results))
		layers=incremented_layers[results.index(Tj_list[-1])]
		layerlist.append(layers)
	Tj_list.append(run_sim.build_ic_and_simulate(simdata, to_file=True, layers=['bottomlayer']+layers, toinsert=[nsteps, layerorder])[0])
	return Tj_list
"""
