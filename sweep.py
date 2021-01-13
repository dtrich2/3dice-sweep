#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
from helperfcn import *
from paramspace import yaml
from tqdm import tqdm
import os

#'ic' class definition
from methods import *

toplevel='sim_params'

with open(sys.argv[1]+".yml", mode='r') as cfg_file:
    cfg = yaml.load(cfg_file)
# cfg is now a dict with keys from .yaml file
pspace = cfg[toplevel]
print(pspace.get_info_str())
print("ETA: {:.2f} hours".format(pspace.volume/(7*3600)))
results = open(sys.argv[1]+".csv", "w")
writeheader(pspace, results)
for params in tqdm(pspace):
    layers=['bottomlayer']
    for nrepeats in range(params['nrepeats']):
      for ncompute in range(params['ncompute']):
        layers.append('compute')
      for nmemory in range(params['nmemory']):
        layers.append('memory')
    #print(json.dumps(params, indent=4))
    myic = ic(heatsinks=params['heatsinks'],
          materialdict=params['materials'],
          layerdict=params['layers'],
          tierorders=cfg['tierorders'],
          layers=layers,
          dimensions=cfg['defaultdimensions'],
          granularity=cfg['defaultgranularity'])
    writevalues(params, results)
    results.write("{:.2f}\n".format(myic.simulate("sweep.stk", "./output_from_3DICE.txt", verbose=False)))
results.close()
#clean up
files=["sweep.stk", "output_from_3DICE.txt", "xaxis.txt", "yaxis.txt"]
for name in files:
    os.remove(name)
layer=0;
while True:
  name="layer{}.flp".format(layer)
  if os.access(name, os.F_OK):
    os.remove(name)
    layer+=1
  else:
    break


#bashCommands=["rm layer*.flp", "rm sweep.stk", "rm output_from_3DICE.txt", "rm *axis.txt"]
#process = subprocess.Popen("bash -O extglob -c 'cd /tmp/a; rm -rf !(file2); cd -'", stdout=subprocess.PIPE)
"""
output, error = process.communicate() 
print(output)
print(error)
"""
