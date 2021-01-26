#required packages
import sys
import os
import matplotlib.pyplot as plt
from paramspace import yaml
from seaborn import color_palette
from collections import OrderedDict

#helper files
from yamlhelper import *

###
#LINEARITY ASSUMPTION
###

#assume linearity and get contribution of each 'material' or 'layer' (set by 'binning') to temperature rise
def rdist(filenames, binning='material', changed={}):
    cfg=getcfg(filenames)
    pspace=getpspace(cfg)
    defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=False)
    defaults=change(defaults,changed)
    defaults=expand(defaults)
    rdict={}
    for layer in defaults['layers']:
        rdict[layer]={}
        for tier in defaults['layers'][layer]['tiers']:
            rdict[layer][tier]=defaults['layers'][layer]['tiers'][tier]*1e-6/defaults['materials'][tier]['k']
    ####calculate contributions to delta T
    bins=OrderedDict()
    powabove=0
    for i in range(0,defaults['nrepeats']):
        for j in range(0,defaults['nmemory']):
            powabove=layerwrite(defaults=defaults, cfg=cfg, layer='memory', rdict=rdict, bins=bins, binning=binning, powabove=powabove)
        for k in range(0,defaults['ncompute']):
            if not (i==defaults['nrepeats']-1 and k==defaults['ncompute']-1):
                powabove=layerwrite(defaults=defaults, cfg=cfg, layer='compute', rdict=rdict, bins=bins, binning=binning, powabove=powabove)
    powabove=layerwrite(defaults=defaults, cfg=cfg, layer='bottomlayer', rdict=rdict, bins=bins, binning=binning, powabove=powabove)
    bins['heatsink']=powabove/defaults['heatsinks']['top']['coefficient']
    if 'beol2' in bins:
        bins['beol']=bins['beol']+bins['beol2']
        del bins['beol2']
    #bins.move_to_end('heatsink',last=False)
    print(changed)
    print(sum(bins.values()))
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
def makeplot(filenames, changelist, binning='material', numonly=False, charttype='bar', legendnames={}, figsize=None):
    resultsdir="./results/"+filenames+"/"
    binlist=[]
    namelist=[]
    figname=[""]
    font = {'size' : 26}

    plt.rc('font', **font)
    for changed in changelist:
        namelist.append(changed['name'])
        del changed['name']
        binlist.append(rdist(filenames=filenames, binning=binning, changed=changed))
        for val in changed:
            figname[-1]+=val+"-{}".format(changed[val])+"_"
        if charttype=='pie':
            figname.append("")
    if legendnames:
        legendlist=[]
        for name in binlist[0].keys():
            if name in legendnames.keys():
                legendlist.append(legendnames[name])
            else:
                legendlist.append(name)
    else:
        legendlist=binlist[0].keys()
    newbinlist=[]
    for mybin in binlist:
        newbin={}
        for material in mybin:
            if material in legendnames:
                if legendnames[material]=='Other':
                    if 'Stack' in newbin.keys():
                        newbin['Stack']+=mybin[material]
                    else:
                        newbin['Stack']=mybin[material]
                else:
                    newbin[legendnames[material]]=mybin[material]
            else:
                newbin[material]=mybin[material]
        newbinlist.append(newbin)
    binlist=newbinlist
    if charttype=='pie':
        for (name, mybin) in zip(figname,binlist):
            piechart, ax = plt.subplots()
            ax.pie(newbin.values(), labels=newbin.keys(), autopct='%1.1f%%')
            if not os.access(resultsdir, os.R_OK):
                os.mkdir(resultsdir)
            figpath=resultsdir+charttype+"_"+binning+"_"+name+".png"
            piechart.savefig(figpath)
            piechart.clf()
    elif charttype=='bar' or numonly:
        barchart, ax = plt.subplots(figsize=figsize)
        xindex=0
        totals=[]
        for mybin in binlist:
            bottom=300-273.15
            for color, element in zip(color_palette("deep"), mybin):
                plt.bar(xindex, mybin[element], color=color, bottom=bottom, edgecolor='white', width=1)
                bottom+=mybin[element]
            totals.append(bottom)
            xindex+=1
        if numonly:
            return totals
        plt.xticks(range(0,xindex), namelist)
        plt.ylabel("T (C)")
        lgd=plt.legend(binlist[0].keys(), bbox_to_anchor=(1.05, 1), loc='upper left')
        if not os.access(resultsdir, os.R_OK):
            os.mkdir(resultsdir)
        figpath=resultsdir+charttype+"_"+binning+"_"+figname[0]+".png"
        barchart.savefig(figpath, bbox_extra_artists=(lgd,), bbox_inches='tight')
        barchart.clf()
    print("Plotted "+figpath)

#run this if called from command line
if __name__ == "__main__":
    def_changelist=[{'name': 'default'}]
    membeol_changelist=[{"name": "3 Memory \n BEOL k=2", "layers_bottomlayer_tiers_beol": 4},
    {"name": "3 Memory \n BEOL k=4", "materials_beol_k": 4, "layers_bottomlayer_tiers_beol": 4},
    {"name": "10 Memory \n BEOL k=2", "nmemory": 10, "layers_bottomlayer_tiers_beol": 4},
    {"name": "10 Memory \n BEOL k=4", "materials_beol_k": 4, "nmemory": 10, "layers_bottomlayer_tiers_beol": 4}]
    membeol_2dic_changelist=[{"name": "2D IC \n BEOL k=2", "nrepeats": 1, "nmemory": 1, "heatsinks_top_coefficient": 2e4, "layers_bottomlayer_tiers_beol": 4},
    {"name": "2D IC \n BEOL k=4", "nrepeats": 1, "nmemory": 1, "heatsinks_top_coefficient": 2e4, "layers_bottomlayer_tiers_beol": 4, "materials_beol_k": 4}]
    past_future_changelist=[{"name": "2D IC", "nrepeats": 1, "nmemory": 1, "heatsinks_top_coefficient": 2e4, "layers_bottomlayer_tiers_beol": 4},
    {"name": "N3XT V1", "nrepeats": 1, "heatsinks_top_coefficient": 2e4, "layers_bottomlayer_tiers_beol": 4},
    {"name": "N3XT V2+", "nmemory": 10, "layers_bottomlayer_tiers_beol": 4}]
    makeplot(filenames=sys.argv[1], changelist=membeol_2dic_changelist, charttype='pie',
        legendnames={'heatsink':'Heatsink','mem': 'Other', 'sio2': 'Other', 'si':'Other', 'beol':'Other'}, figsize=(10,6))
