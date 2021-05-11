import os
from yamlhelper import *

def printinfo(cfg):
  pspace=getpspace(cfg)
  #print(pspace.get_info_str())
  listvals(cfg)

def buildlayers(layermapping, layerorder):
    layers=[]
    for layer in list(map(int, str(layerorder))):
        layers.append(layermapping[layer-1])
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

def prep_filesystem(ymlfile):
  if not os.access('ice_files', os.R_OK):
    os.mkdir('ice_files')
  simdir='ice_files/'+ymlfile
  if not os.access(simdir, os.R_OK):
    os.mkdir(simdir)
  return simdir
