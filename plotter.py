#required packages
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from paramspace import yaml
import paramspace

#helper file
from helperfcn import *
#name of toplevel 'pspace' directory from yml file
toplevel='sim_params'

#run this if called from command line
if __name__ == "__main__":
   #plotter(filenames=sys.argv[1], tovary=sys.argv[2:])
   makeplot(filenames=sys.argv[1], changelist=[{"name": "default"},{"name": "10memory", "nmemory": 10}])
   #listvals(filenames=sys.argv[1])
   #translate(filenames=sys.argv[1], outputfile=sys.argv[2])

#plot point in paramspace defined by 'default' in "filenames".yml, varying 'tovary' (vector of 1 or 2 parameters)
#modify default space with dict 'changed', each key is the path in the .yml file separated with underscores
def plotter(filenames, tovary, changed={}, getdf=False):
    defaults=listvals(filenames, getdefault=True)
    df_test= pd.read_csv(filenames+'.csv')
    df_test['T']+=-273.15
    for default in defaults:
        if not default in tovary:
            if default in changed.keys():
                qstring=default+"=={}".format(changed[default])
            else:
                qstring=default+"=={}".format(defaults[default])
            df_test.query(qstring, inplace = True)
    if getdf:
        return df_test
    figname="./"+filenames+"/"
    for arg in tovary:
        figname+=arg+"_"
    for val in changed:
        figname+="_"+val+"-{}".format(changed[val])
    plotterlog=open(figname+'log.csv', mode='w')
    plotterlog.write(df_test.to_csv(index=False))
    plotterlog.close()
    print("start scatterplot")
    if len(tovary)==1:
        sns_plot=sns.scatterplot(x=tovary[0], y='T',data=df_test)
    elif len(tovary)==2:
        df=pd.pivot_table(data=df_test, index=tovary[0], columns=tovary[1], values='T')
        sns_plot=sns.heatmap(df)
    print("finish scatterplot")
    fig=sns_plot.get_figure()
    fig.savefig(figname+".png")
    fig.clf()

#output parameters from .yml to .csv for COMSOL import
def translate(filenames, outputfile):
	defaults=listvals(filenames, getall=True)
	f = open(outputfile, "w")
	for param in defaults:
		f.write("{}, {}\n".format(param, defaults[param]))
	f.close()

#act on "filenames".yml to display all pertinent information about simulation
def listvals(filenames, getdefault=False, getall=False):
    default={}
    with open(filenames+".yml", mode='r') as cfg_file:
        cfg = yaml.load(cfg_file)
    # cfg is now a dict with keys from .yaml file
    pspace = cfg[toplevel]
    pathlist=paths(pspace._dict)
    holder={}   #hack for exec
    for mypath in pathlist:
        path=""
        evalstring=""
        for step in mypath:
            evalstring=evalstring+"['"+step+"']"
            if path:
                path+="_"
            path=path+"{}".format(step)
        exec("holder['blank']=pspace._dict"+evalstring)
        if isinstance(holder['blank'], paramspace.paramdim.ParamDim):
            if getdefault or getall:
                default[path]=holder['blank'].default.value
            else:
                print("""{}
                values: {}
                default: {}""".format(path, holder['blank'].values, holder['blank'].default.value))
        elif isinstance(holder['blank'], paramspace.paramdim.CoupledParamDim):
            if getall:
            	default[path]=holder['blank'].default.value
            elif not (getdefault or getall):
                print("""{}
                coupled to {}""".format(path, holder['blank'].target_name))
                if not holder['blank']._use_coupled_values:
                    print("    with values {}".format(holder['blank'].values))
                if not holder['blank']._use_coupled_default:
                    print("    with default {}".format(holder['blank'].default.value))
        else:
            if getall:
            	default[path]=holder['blank']
            elif not (getdefault or getall):
                print("{} = {}".format(path, holder['blank']))
    if getdefault or getall:
        return default

#assume linearity and get contribution of each 'material' or 'layer' (set by 'binning') to temperature rise
def rdist(filenames, binning='material', changed={}):
    with open(filenames+".yml", mode='r') as cfg_file:
        cfg = yaml.load(cfg_file)
    defaults=cfg[toplevel].default
    pathlist=paths(changed)
    for mypath in pathlist:
        path=""
        evalstring=""
        for step in mypath:
            evalstring=evalstring+"['"+step+"']"
            if path:
                path+="_"
            path=path+"{}".format(step)
        exec("defaults"+evalstring+"=changed['"+path+"']")
    rdict={}
    for layer in defaults['layers']:
        rdict[layer]={}
        for tier in defaults['layers'][layer]['tiers']:
            rdict[layer][tier]=defaults['layers'][layer]['tiers'][tier]*1e-6/defaults['materials'][tier]['k']
    ####calculate contributions to delta T
    bins={}
    powabove=0
    for i in range(0,defaults['nrepeats']):
        for j in range(0,defaults['nmemory']):
            powabove=layerwrite(defaults=defaults, cfg=cfg, layer='memory', rdict=rdict, bins=bins, binning=binning, powabove=powabove)
        for k in range(0,defaults['ncompute']):
            powabove=layerwrite(defaults=defaults, cfg=cfg, layer='compute', rdict=rdict, bins=bins, binning=binning, powabove=powabove)
    powabove=layerwrite(defaults=defaults, cfg=cfg, layer='bottomlayer', rdict=rdict, bins=bins, binning=binning, powabove=powabove)
    bins['heatsink']=powabove/defaults['heatsinks']['top']['coefficient']
    if 'beol2' in bins:
        bins['beol']=bins['beol']+bins['beol2']
        del bins['beol2']
    return bins

#helper function for rdist
def layerwrite(defaults, cfg, layer, rdict, bins, binning, powabove):
    for tiernum, tier in zip(range(len(cfg['tierorders'][layer])-1,-1,-1),reversed(cfg['tierorders'][layer])):
        if defaults['layers'][layer]['sourcetier']==tiernum:
            powabove+=defaults['layers'][layer]['power']*1e4 #W/cm2 to W/m2
        deltaT=powabove*rdict[layer][tier]
        if binning=='material':
            if tier in bins:
                bins[tier]+=deltaT
            else:
                bins[tier]=deltaT
        elif binning=='layer':
            if layer in bins:
                bins[layer]+=deltaT
            else:
                bins[layer]=deltaT
    return powabove

#sweep rdist possibilities. each dict in changelist is the parameters altered from the default in .yml file
def makeplot(filenames, changelist, binning='material', numonly=False):
    barchart, ax = plt.subplots(figsize=[10,6])
    binlist=[]
    namelist=[]
    for changed in changelist:
        namelist.append(changed['name'])
        del changed['name']
        binlist.append(rdist(filenames=filenames, binning=binning, changed=changed))
    xindex=0
    totals=[]
    for mybin in binlist:
        bottom=300-273.15
        for color, element in zip(sns.color_palette("deep"), mybin):
            plt.bar(xindex, mybin[element], color=color, bottom=bottom, edgecolor='white', width=1)
            bottom+=mybin[element]
        totals.append(bottom)
        xindex+=1
    if numonly:
        return totals
    plt.xticks(range(0,xindex), namelist, fontweight='bold')
    plt.ylabel("deltaT (C)")
    barchart.legend(binlist[0].keys())
    barchart.savefig(binning+"dist.png")


