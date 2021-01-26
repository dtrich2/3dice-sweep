#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
from tqdm import tqdm
import os

#helper files
from yamlhelper import *
from ic import *

def sweep(ymlfile, resultsfile):
  cfg=getcfg(ymlfile)
  pspace=getpspace(cfg)
  flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
  dimension_keys=getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
  #print(pspace.get_info_str())
  printinfo(cfg)
  if not os.access('ice_files', os.R_OK):
    os.mkdir('ice_files')
  simdir='ice_files/'+ymlfile
  if not os.access(simdir, os.R_OK):
    os.mkdir(simdir)


  #SWEEP PARAMETER SPACE
  results = open(resultsfile, "w")
  writeheader(flat_pspace, dimension_keys, results)
  for params in tqdm(pspace):
      layers=buildlayers(nrepeats=params['nrepeats'], ncompute=params['ncompute'], nmemory=params['nmemory'])
      myic = ic(heatsinks=params['heatsinks'],
            materialdict=params['materials'],
            distdict=params['layers']['powers']['distdict'],
            distlist=params['layers']['powers']['distlist'],
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

def printinfo(cfg):
  pspace=getpspace(cfg)
  #print(pspace.get_info_str())
  listvals(cfg)
  print("ETA: {:.2f} hours".format(pspace.volume/(4*3600)))
  print("{}it total".format(pspace.volume))

def buildlayers(nrepeats, ncompute, nmemory):
    layers=['bottomlayer']
    for repeat in range(nrepeats):
        for compute in range(ncompute):
            if not (repeat==0 and compute==0):
                layers.append('compute')
        for memory in range(nmemory):
            layers.append('memory')
    return layers

def cleanup(simdir):
    files=[simdir+"/stack.stk", "xaxis.txt", "yaxis.txt"]
    for name in files:
        os.remove(name)
    layer=0
    while True:
        name=simdir+"/layer{}.flp".format(layer)
        if os.access(name, os.F_OK):
            os.remove(name)
            layer+=1
        else:
            break
    layer=0
    while True:
        name=simdir+"/output_from_3DICE{}".format(layer)
        if os.access(name, os.F_OK):
            os.remove(name)
            layer+=1
        else:
            break


#run this if called from command line
if __name__ == "__main__":
  ymlfile=sys.argv[1]
  resultsfile='./results/'+sys.argv[1]+'.csv'
  sweep(ymlfile=ymlfile, resultsfile=resultsfile)

