import sys
#helper files
from yamlhelper import *
import numpy as np

def gen_params(filenames, outputfile):
    defaults=getdefault(getcfg(filenames), getcoupled=True, getstatic=True, flat=True, detailed=False)
    f = open(outputfile, "w")
    for param in defaults:
        f.write("{}, {}".format(param, defaults[param]))
        steps=param.split('_')
        if steps[-1]=='k':
            f.write("[W/m/K]")
        elif steps[-1]=='coefficient':
            f.write("[W/m^2/K]")
        elif steps[-1]=='C':
            f.write("[J/m^3/K]")
        elif steps[-1]=='power':
            f.write("[W/cm^2]")
        if len(steps)>1:
            if steps[-2]=='tiers':
                f.write("[um]")
        f.write("\n")
    f.close()

def gen_coords(filenames, outputfile, hbottom):
    cfg=getcfg(filenames)
    defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=True)
    defaultsonly=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
    heights={}
    offsets={}
    for layer in defaults['layers']:
        height=0
        if 'bottom' in layer:
            pass
        else:
            for tier in cfg['tierorders'][layer]:
                height+=defaultsonly['layers'][layer]['tiers'][tier]
                if cfg['tierorders'][layer].index(tier)==defaults['layers'][layer]['sourcetier']:
                    offset=height
            heights[layer]=height
            offsets[layer]=height-offset
    stackstats=[]
    keylist=['nmemory', 'ncompute', 'nrepeats']
    for key in keylist:
        if isinstance(defaults[key], int):
            stackstats.append([defaults[key]])
        else:
            stackstats.append(defaults[key].values)
    nmemory, ncompute, nrepeats=tuple(stackstats)
    zlist=[]
    zrunner=hbottom
    nrepeats=max(stackstats[2])
    for r in range(nrepeats):
        for nmemory in stackstats[0]:
            for ncompute in stackstats[1]:
                for c in range(ncompute):
                    zrunner+=heights['compute']
                    if not zrunner-offsets['compute'] in zlist:
                        zlist.append(zrunner-offsets['compute'])
                for m in range(nmemory):
                    zrunner+=heights['memory']
                    if not zrunner-offsets['memory'] in zlist:
                        zlist.append(zrunner-offsets['memory'])
    xlist=np.add(0.5,list(range(cfg['defaultresolution'][0])))
    ylist=np.add(0.5,list(range(cfg['defaultresolution'][1])))
    f = open(outputfile, "w")
    for z in zlist:
        for y in ylist:
            for x in xlist:
                f.write("{:2f},{:2f},{:2f}\n".format(x,y,z))
    f.close()



if __name__ == "__main__":
    gen_params(filenames=sys.argv[1], outputfile=sys.argv[1]+"_comsolparams.csv")
    gen_coords(filenames=sys.argv[1], outputfile=sys.argv[1]+"_comsolsolnpoints.csv", hbottom=50)
