import os
import numpy as np
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

def to_layerorder(layers, layermapping):
    layerorder_str=''
    for layer in layers:
      layerorder_str=layerorder_str+str(layermapping.index(layer)+1)
    return int(layerorder_str)

def gen_activated_lines(n_activated_lines, n_layers, n_lines):
    activated_lines=[]
    for layer in range(n_layers):
        activated_lines.append(np.random.choice(n_lines, n_activated_lines, replace=False))
    return activated_lines

def get_incremented_layers(layers):
    #layers made up of 'memory' and 'compute'
    incremented_layers=[]
    indices = [i for i, x in enumerate(layers) if x == "compute"] #indices of all compute layers
    for index in indices:
      if index<len(layers)-1 and layers[index+1]=='memory':
        newlayer=layers.copy()
        newlayer[index], newlayer[index+1]=(newlayer[index+1],newlayer[index])
        incremented_layers.append(newlayer)
    return incremented_layers

def cleanup(files):
    #files=[simdir+"/stack.stk", "xaxis.txt", "yaxis.txt"]
    for name in files:
        os.remove(name)
    """
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
    """

def prep_filesystem(ymlfile):
  if not os.access('ice_files', os.R_OK):
    os.mkdir('ice_files')
  simdir='ice_files/'+ymlfile
  if not os.access(simdir, os.R_OK):
    os.mkdir(simdir)
  return simdir
