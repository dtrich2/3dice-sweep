#script for sweeping parameter space defined in .yml file (supplied in first argument in command line)
#outputs to .csv of same name

#required packages
from tqdm import tqdm
import seaborn as sns
import matplotlib.pyplot as plt

#helper files
from sweephelper import *
from pandashelper import *
from power_class_def import *
from ic import *

def plot_map(ymlfile,floorplanfile,nlayers,plotlayer,ice=True):
  floorplanfile=floorplanfile+'_'+str(nlayers)
  #load from ymlfile (defaults only)
  cfg=getcfg(ymlfile)
  pspace=getpspace(cfg)
  flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
  dimension_keys=getdefault(cfg, getcoupled=True, getstatic=False, flat=True, detailed=False).keys()
  simdir=prep_filesystem(ymlfile)

  #initial IC build and simulate with starting floorplan
  params=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
  with open(floorplanfile+'.yml', mode='r') as f:
    compute_floorplan = yaml.load(f)
  params['layers']['powers']['compute']= compute_floorplan['compute']
  layers=buildlayers(nrepeats=nlayers, ncompute=1, nmemory=1)
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
  
  plt.rcParams.update({'font.size': 20})
  plt.figure(figsize=(8, 8), dpi=80)
  if ice:
    t_min, tavglayers=myic.simulate(verbose=False)
    outputfile=simdir+'/'+"output_from_3DICE"+str(plotlayer)
    ice_map=np.round(pd.read_csv(outputfile, comment='%', delimiter='  ', dtype=np.float64, engine='python').to_numpy(),3)
    sns_plot=sns.heatmap(ice_map, square=True)
    fig=sns_plot.get_figure()
    fig.savefig(floorplanfile+"_ice_"+str(plotlayer)+".png")
    fig.clf()
    cleanup(simdir)
  
  power_map=myic.writeflp(layer='compute', index=plotlayer, flpfile='holder.flp', return_only=True)
  sns_plot=sns.heatmap(np.array(power_map).T.tolist(), square=True)
  fig=sns_plot.get_figure()
  fig.savefig(floorplanfile+"_power_"+str(plotlayer)+".png")
  fig.clf()

  


#run this if called from command line
if __name__ == "__main__":
  ymlfile=sys.argv[1]
  floorplanfile=sys.argv[2]
  nlayers=int(sys.argv[3])
  plotlayer=int(sys.argv[4])
  plot_map(ymlfile,floorplanfile,nlayers,plotlayer,ice=True)

