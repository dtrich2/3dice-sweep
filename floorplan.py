#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
from tqdm import tqdm
from copy import deepcopy
from ruamel.yaml import YAML
import random
import numpy as np

#helper files
from sweephelper import *
from power_class_def import *
from ic import *

def floorplan(ymlfile, block_dict, ar_range, kelvin_constant, maxlayers):
  #load from ymlfile (defaults only)
  cfg=getcfg(ymlfile)
  pspace=getpspace(cfg)
  flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
  dimension_keys=getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
  simdir=prep_filesystem(ymlfile)

  #initial IC build and simulate with starting floorplan
  params=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
  init_floorplan=buildpower(block_dict, dimensions=cfg['defaultdimensions'], ar_range=ar_range)
  params['layers']['powers']['compute']=init_floorplan['compute'] #overwrite layout from file 
  if not init_floorplan['legalized']:
      print('Cannot legalize given default power layout')
      return False
  del init_floorplan['legalized']
  write_floorplan('failed_legalize_0.yml', init_floorplan)
  

  for nlayers in range(1,maxlayers+1):
    #do floorplanning algorithm
    print(nlayers)
    layers=buildlayers(nrepeats=nlayers, ncompute=1, nmemory=1)
    mypowers=power(powers=deepcopy(params['layers']['powers']), ar_range=ar_range, dimensions=cfg['defaultdimensions'])
    myic = ic(heatsinks=params['heatsinks'],
          materialdict=params['materials'],
          powers=mypowers.powers,
          layerdict=params['layers']['layerdict'],
          tierorders=cfg['tierorders'],
          layers=layers,
          dimensions=mypowers.dimensions,
          resolution=cfg['defaultresolution'],
          mydir=simdir,
          outputfile="output_from_3DICE")
    t_min, tavglayers=myic.simulate(verbose=False)
    temp_over_time=[t_min]
    min_powers=deepcopy(mypowers)
    orig_powers=deepcopy(mypowers)
    write_floorplan('tony_'+str(nlayers)+'_orig.yml', orig_powers.powers)
    iter_since_newmin=0
    while iter_since_newmin<nlayers*30:
        iter_since_newmin+=1
        old_powers=deepcopy(mypowers)
        if nlayers>1: other_layer=True
        else: other_layer=False
        nodeinfo=mypowers.gen_unique_nodes(2, other_layer)
        mypowers.node_swap(nodeinfo)
        if not mypowers.legalize():
            mypowers=old_powers
            continue
        myic.powers=mypowers.powers
        t_current, tavglayers=myic.simulate(verbose=False)
        temp_over_time.append(t_current)
        if t_current<t_min:
            t_min=t_current
            min_powers=deepcopy(mypowers)
            iter_since_newmin=0
        else:
            p=np.exp(-1*(t_current-t_min)/kelvin_constant)
            p_test=random.random()
            if p<p_test: mypowers=old_powers
    write_floorplan('tony_'+str(nlayers)+'.yml', min_powers.powers, temp_over_time, t_min)
    params['layers']['powers']['compute']['hslocs'].append(deepcopy(params['layers']['powers']['compute']['hslocs'][0]))
    params['layers']['powers']['compute']['hspowers'].append(deepcopy(params['layers']['powers']['compute']['hspowers'][0]))
    params['layers']['powers']['compute']['hssize'].append(deepcopy(params['layers']['powers']['compute']['hssize'][0]))
    params['layers']['powers']['compute']['bgpowers'].append(deepcopy(params['layers']['powers']['compute']['bgpowers'][0]))  #assume no background power density


  cleanup(simdir)

def write_floorplan(filename, d, temp_over_time=None, t_min=None):
  with open(filename, 'w') as f:
    for layer in d:
      print(layer+":", file=f)
      for myproperty in d[layer]:
        print("  "+myproperty+": ", file=f, end ="")
        print(d[layer][myproperty], file=f)
    if temp_over_time:
      print('temp_over_time: {}'.format(temp_over_time), file=f)
      print('t_min: {}'.format(t_min),file=f)



def buildpower(block_dict, dimensions, ar_range):
  legalize_attempts=0
  while True:
    hslocs,hspowers,hssize=([],[],[])
    for block in block_dict:
        mypower=block_dict[block]['power']*1e-6 #uW to W
        area=block_dict[block]['area'] #um2
        hslocs.append([random.random(),random.random()])  #let legalize take care of placement
        #hslocs.append(block_dict[block]['loc'])
        hspowers.append(mypower/(area*1e-8))
        dimsum=dimensions[0]+dimensions[1]
        hssize.append([area**0.5/dimensions[0],area**0.5/dimensions[1]])
    blockpattern={'compute': {'hslocs':[hslocs], 'hspowers':[hspowers], 'hssize':[hssize], 'bgpowers':[0]}}
    singlelayer=power(powers=blockpattern, ar_range=ar_range, dimensions=dimensions)
    if singlelayer.legalize_pattern(layer='compute', pattern=0, boundarysize=0.05):
        singlelayer.powers['legalized']=True
        break
    else:
      legalize_attempts+=1
      if legalize_attempts>=10:
        singlelayer.powers['legalized']=False
        return singlelayer.powers
  return singlelayer.powers


#run this if called from command line
if __name__ == "__main__":
  ymlfile=sys.argv[1]
  resultsfile='./results/'+sys.argv[1]+'.csv'
  block_dict={'reg': {'power': 25, 'area': 1930*0.2*4000/8},
  'lsu': {'power': 110, 'area': 1930*0.55*4000/5},
  'mmu': {'power': 50, 'area': 1930*0.4*4000/5},
  'fgu': {'power': 30, 'area': 1930*0.8*4000/3.5},
  'ifu': {'power': 50, 'area': 1930*0.55*4000/3.5},
  'exu1': {'power': 130, 'area': 1930*0.2*4000/8},
  'exu2': {'power': 130, 'area': 1930*0.2*4000/8},
  'small': {'power': 110, 'area': 100*100},
  }

  for key in block_dict:
    block_dict[key]['power']=block_dict[key]['power']*1e6*block_dict[key]['area']*1e-8  #convert from W/cm2 to uW
  #print(block_dict)
  ar_range=[0.5,2] #assume flexible aspect ratio for all blocks

  floorplan(ymlfile=ymlfile, block_dict=block_dict, ar_range=ar_range, kelvin_constant=5, maxlayers=9)

  block_dict={'dec': {'power': 4.0895e+03, 'area': 4625.207925},
    'exu': {'power': 1.5507e+04, 'area': 20913.717660},
    'fgu': {'power': 8.0343e+04, 'area': 92130.694453},
    'gkt': {'power': 1.2993e+04, 'area': 14458.163799},
    'ifu_cmu': {'power': 7.1600e+03, 'area': 9056.767890},
    'ifu_ftu': {'power': 2.5727e+04, 'area': 28233.505497},
    'ifu_ibu': {'power': 2.2911e+04, 'area': 29081.513541},
    'lsu': {'power': 5.5836e+04, 'area': 67205.962751},
    'mmu': {'power': 3.2492e+04, 'area': 44475.465188},
    'pku': {'power': 1.0270e+04, 'area': 14311.065783},
    'pmu': {'power': 6.6577e+03, 'area': 11697.615778},
    'tlu': {'power': 5.9831e+04, 'area': 74471.220715}} #from tony 45 nm nanocomp (see get_power_by_block.pl). units are um2 and uW
