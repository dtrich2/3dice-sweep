#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
from tqdm import tqdm

#helper files
from sweephelper import *
from ic import *

def sweep(ymlfile, resultsfile):
  cfg=getcfg(ymlfile)
  powerfile='powers/'+cfg['powerfile']
  powers=getcfg(powerfile)
  pspace=getpspace(cfg)
  flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
  dimension_keys=getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
  print(pspace.get_info_str())
  print("ETA: {:.2f} hours".format(pspace.volume*2/(3600)))
  print("{}it total".format(pspace.volume))
  #printinfo(cfg)
  simdir=prep_filesystem(ymlfile)

  #SWEEP PARAMETER SPACE
  results = open(resultsfile, "w")
  writeheader(flat_pspace, dimension_keys, results)
  for params in tqdm(pspace):
      params['layers']['powers']=powers
      for material in params['materials']:
      	params['materials'][material]['k']=params['materials'][material]['k']/cfg['kscalar']
      layers=buildlayers(layermapping=cfg['layermapping'], layerorder=params['layerorder'])
      if params['floorplan-type']==0:
        params['layers']['powers']['compute']=params['layers']['powers']['compute1']
      elif params['floorplan-type']==1:
        computekey='compute'+str(layers.count('compute'))
        params['layers']['powers']['compute']=params['layers']['powers'][computekey]
      elif params['floorplan-type']==2:
        params['layers']['powers']['compute']=params['layers']['powers']['compute_uniform']
        params['layers']['powers']['compute']['bgpowers']=[params['layers']['powers']['compute']['bgpowers'][0] for i in range(0,layers.count('compute'))]
      myic = ic(heatsinks=params['heatsinks'],
            materialdict=params['materials'],
            powers=params['layers']['powers'],
            layerdict=params['layers']['layerdict'],
            tierorders=cfg['tierorders'],
            layers=layers,
            dimensions=cfg['defaultdimensions'],
            resolution=cfg['defaultresolution'],
            mydir=simdir,
            outputfile="output_from_3DICE")
      writevalues(flat_params=flatten(params), keys=dimension_keys, results=results)
      tj, tavglayers=myic.simulate(verbose=False)
      tavg=sum(tavglayers)/len(tavglayers)
      results.write("{:.2f},{:.2f}".format(tj,tavg))
      for temp in tavglayers:
        results.write(",{:.2f}".format(temp))
      results.write("\n".format(tj))
  results.close()
  cleanup(simdir)

#run this if called from command line
if __name__ == "__main__":
  ymlfile=sys.argv[1]
  resultsfile='./results/'+sys.argv[1]+'.csv'
  sweep(ymlfile=ymlfile, resultsfile=resultsfile)

