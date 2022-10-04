import sys
import numpy as np
import glob
import pandas as pd

#helper files
from yamlhelper import *
from pandashelper import *
from sweephelper import *

def gen_params(filenames, outputfile):
    cfg=getcfg(filenames)
    defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=False)
    f = open(outputfile, "w")
    for param in defaults:
        if not (isinstance(defaults[param],int) or isinstance(defaults[param],float)):
            continue
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
    f.write("{}, {}[um]\n{}, {}[um]\n".format('dimensionx', cfg['defaultdimensions'][0],'dimensiony', cfg['defaultdimensions'][1]))
    f.write("{}, {}[kg/m^3]\n".format('density', 1))
    for layer in ['compute','memory']:
        h=""
        for tier in cfg['tierorders'][layer]:
            if h: h+="+"
            h+="layers_layerdict_"+layer+"_tiers_"+tier
        f.write("{}, {}\n".format("h"+layer,h))
    f.close()

def gen_power_pattern(powerfile, ic_dimensions, origin='center'):    #dimensions in um
    powerfile='powers/'+powerfile
    powers=getcfg(powerfile)
    for layer in powers:
        bg_power=powers[layer]['bgpowers']
        for tier in range(len(bg_power)):
            if not (isinstance(bg_power[tier],int) or isinstance(bg_power[tier],float)):
                bg_power[tier]=bg_power[tier][0]
            output_string="({}".format(bg_power[tier])
            if len(powers[layer]['hslocs'])!=0:
                for loc, size, power in zip(powers[layer]['hslocs'][tier], powers[layer]['hssize'][tier], powers[layer]['hspowers'][tier]):
                    if origin=='center':
                        loc=np.subtract(loc,0.5)
                        size=np.subtract(size,0.5)
                    xlim=np.round(np.multiply([loc[0],loc[0]+size[0]],ic_dimensions[0]),2)
                    ylim=np.round(np.multiply([loc[1],loc[1]+size[1]],ic_dimensions[1]),2)
                    output_string+="+(x>{}e-6)*(x<{}e-6)*(y>{}e-6)*(y<{}e-6)*({}-{})".format(xlim[0],xlim[1],ylim[0],ylim[1],np.round(power,2),bg_power[tier])
            output_string+=") [W/cm^2]/layers_layerdict_compute_tiers_transistors"
            print(layer+" tier {}".format(tier))
            print(output_string)
#(layers_layerdict_compute_power_bg+((x>2300e-6)*(x<2700e-6)*(y>2300e-6)*(y<2700e-6)+(x>-2700e-6)*(x<-2300e-6)*(y>2300e-6)*(y<2700e-6)+(x>2300e-6)*(x<2700e-6)*(y>-2700e-6)*(y<-2300e-6)+(x>-2700e-6)*(x<-2300e-6)*(y>-2700e-6)*(y<-2300e-6))*(layers_layerdict_compute_power-layers_layerdict_compute_power_bg))/layers_layerdict_compute_tiers_transistors

def gen_coords(filenames, outputfile, hbottom, stack_properties=None):
    cfg=getcfg(filenames)
    defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=True)
    zlist=gen_full_zlist(cfg,hbottom, stack_properties)
    granularity=np.divide(cfg['defaultdimensions'],cfg['defaultresolution'])
    xlist=list(np.subtract(list(np.linspace(0,cfg['defaultdimensions'][0]-granularity[0],cfg['defaultresolution'][0])),(cfg['defaultdimensions'][0]-granularity[0])/2))
    ylist=list(np.subtract(list(np.linspace(0,cfg['defaultdimensions'][1]-granularity[1],cfg['defaultresolution'][1])),(cfg['defaultdimensions'][1]-granularity[1])/2))
    #(x>-2700e-6)*(x<-2300e-6)*(y>-2700e-6)*(y<-2300e-6))
    outputfile=outputfile+"_comsolsolnpoints.csv"
    f = open(outputfile, "w")
    writexyz(f, np.round(xlist,2), np.round(ylist,2), zlist)
    f.close()
    #[[2300,2700],[2300,2700]],[[-2700,-2300],[2300,2700]],[[2300,2700],[-2700,-2300]],[[-2700,-2300],[-2700,-2300]]
    """
    hsgranularity=10
    hsranges=[[[-200,200],[-200,200]]]
    f = open(outputfile+"_hs_comsolsolnpoints.csv", "w")
    for hs in hsranges:
    	xhslist=list(range(hs[0][0],hs[0][1]+1,hsgranularity))
    	yhslist=list(range(hs[1][0],hs[1][1]+1,hsgranularity))
    	writexyz(f, np.round(xhslist,2), np.round(yhslist,2), zlist)
    f.close()
    """
    print("written to {}".format(outputfile))

def writexyz(f, xlist, ylist, zlist):
    for z in zlist:
        for y in ylist:
            for x in xlist:
                f.write("{:g},{:g},{:g}\n".format(x,y,z))

def gen_full_zlist(cfg,hbottom,stack_properties=None):
    defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=True)
    stackstats=[]
    keylist=['nmemory', 'ncompute', 'nrepeats']
    if not stack_properties:
        for key in keylist:
            if isinstance(defaults[key], int):
                stackstats.append([defaults[key]])
            else:
                stackstats.append(defaults[key].values)
    else:
        stackstats=stack_properties    
    nmemory, ncompute, nrepeats=tuple(stackstats)
    all_zlist=[]
    nrepeats=max(stackstats[2])
    for nmemory in stackstats[0]:
        for ncompute in stackstats[1]:
            all_zlist.extend(gen_zlist(cfg, nmemory, ncompute, nrepeats, hbottom))
    no_duplicates = [] 
    [no_duplicates.append(x) for x in all_zlist if x not in no_duplicates]
    return no_duplicates

def gen_zlist(cfg, nmemory, ncompute, nrepeats, hbottom):
    defaults=getdefault(cfg, getcoupled=True, getstatic=True, flat=False, detailed=False)
    heights={}
    offsets={}
    for layer in defaults['layers']['layerdict']:
        height=0
        if 'bottom' in layer:
            pass
        else:
            for tier in cfg['tierorders'][layer]:
                if isinstance(defaults['layers']['layerdict'][layer]['tiers'][tier],paramspace.paramdim.CoupledParamDim):
                    height+=defaults['layers']['layerdict'][layer]['tiers'][tier].default.value
                else:
                    height+=defaults['layers']['layerdict'][layer]['tiers'][tier]
                if cfg['tierorders'][layer].index(tier)==defaults['layers']['layerdict'][layer]['sourcetier']:
                    offset=height
            heights[layer]=height
            offsets[layer]=height-offset
    zrunner=hbottom
    zlist=[]
    for r in range(nrepeats):
        for c in range(ncompute):
            zrunner+=heights['compute']
            zlist.append(zrunner-offsets['compute'])
        for m in range(nmemory):
            zrunner+=heights['memory']
            zlist.append(zrunner-offsets['memory'])
    return np.round(zlist,2)

def get_t_by_layer(cfg, comsolfile, nmemory, ncompute, nrepeats, hbottom):
    zlist=gen_zlist(cfg, nmemory, ncompute, nrepeats, hbottom)
    zlist.sort()
    #tlist=np.round(np.loadtxt(comsolfile, comments='%', delimiter=','),2)
    tlist=np.round(pd.read_csv(comsolfile, comment='%', delimiter=',', dtype=np.float64).to_numpy(),2)
    tlist_specific=[]
    for z in zlist:
        mytlist=np.subtract(tlist[np.where(tlist[:,2] == z),3],0)
        tlist_specific.append(np.reshape(mytlist, (-1)))
    return tlist_specific

def write_df_file(filenames, prefix, stackstats, hs=False):
    comsolfolder='results/comsol/'+filenames
    if hs: prefix+='_hs'
    mydf = pd.DataFrame({'Tj' : []})
    cfg=getcfg('spreader_test')
    defaults=getdefault(cfg, getcoupled=False, getstatic=False, flat=True, detailed=False)
    comsollist=[]
    for item in glob.glob(comsolfolder+"/*.csv"):
        if ('hs' in item.split('_'))==hs:
        	comsollist.append(item[:-4])
    for file in comsollist:
        testparams=defaults.copy()
        paramdict=get_paramdict(file, comsolfolder+'/'+prefix)
        #print(file)
        #print(paramdict)
        for param in paramdict:
            testparams[param]=paramdict[param]
        #results from COMSOL
        tlist=get_t_by_layer(cfg, file+'.csv', stackstats[0], stackstats[1], stackstats[2], hbottom=50)
        maxes=[]
        avgs=[]
        for array in tlist:
            avgs.append(sum(array)/len(array))
            testparams['Tavg'+str(len(maxes))]=avgs[-1]
            maxes.append(max(array))
        testparams['Tj']=max(maxes)
        testparams['Tavg']=sum(avgs)/len(avgs)
        mydf=mydf.append(testparams, ignore_index=True)
    mydf.to_csv('results/comsol/'+prefix+'_comsol.csv', float_format='%.2f', index=False, index_label=False)
    print("results written to"+'results/comsol/'+prefix+'_comsol.csv')

def compare(filenames):
    icedf=getdf(filenames)
    comsoldf=getdf('comsol/'+filenames+'_comsol')
    includecols = [x for x in set(icedf.keys()).intersection(set(comsoldf.keys())) if not x.startswith('T')]
    icedf, comsoldf=tuple(reduce([icedf,comsoldf],includecols))
    tjerror=list(np.divide(list(icedf['Tj']),list(comsoldf['Tj'])))
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    maxerrorind=tjerror.index(max(tjerror))
    #print(icedf['Tj'].loc[[maxerrorind]]/comsoldf['Tj'].loc[[maxerrorind]])
    print(comsoldf[includecols].loc[[maxerrorind]])

def reduce(dflist, includecols):
    qstring="("
    for col in includecols:
        unique=[tuple(df[col].unique()) for df in dflist]
        if len(set(unique))==1:
            continue
        subset = set(unique[0])
        for s in unique[1:]:
            subset.intersection_update(set(s))
        if len(subset)==0:
            raise NameError('Dataframes have nothing in common in column '+col)
        qpart=""
        for item in subset:
            if qpart: qpart+="|"
            qpart+=col+'=={}'.format(item)
        if qstring!="(": qstring+=")&("
        qstring+=qpart
    qstring+=")"
    print(qstring)
    returnlist=[]
    for df in dflist:
        df.query(qstring, inplace = True)
        returnlist.append(df.sort_values(by=includecols, ignore_index=True))
    return returnlist

def get_paramdict(file, prefix):
    #print(prefix)
    file = file.replace(prefix+'_','') #ignores sim label
    #print(file)
    plist=file.split("_")
    paramdict={}
    param=""
    for part in plist:
        try:
            value=float(part)
            paramdict[param]=value
            param=""
        except:
            if param: param+="_"
            param+=part
    return paramdict
#top of 3dice output file
#heatsinks_bottom_coefficient,heatsinks_top_coefficient,layers_bottomlayer_power,layers_bottomlayer_sourcetier,layers_bottomlayer_tiers_beol,layers_bottomlayer_tiers_si,layers_bottomlayer_tiers_sio2,layers_compute_power,layers_compute_sourcetier,layers_compute_tiers_beol,layers_compute_tiers_interthermal,layers_compute_tiers_sio2,layers_memory_power,layers_memory_sourcetier,layers_memory_tiers_beol,layers_memory_tiers_beol2,layers_memory_tiers_interthermal,layers_memory_tiers_mem,layers_memory_tiers_sio2,materials_beol_C,materials_beol_k,materials_beol2_C,materials_beol2_k,materials_interthermal_C,materials_interthermal_k,materials_mem_C,materials_mem_k,materials_si_C,materials_si_k,materials_sio2_C,materials_sio2_k,ncompute,nmemory,nrepeats,Tj,Tavg,Tavg0,Tavg1,Tavg2,Tavg3,Tavg4,Tavg5,Tavg6,Tavg7,Tavg8,Tavg9,Tavg10,Tavg11,Tavg12,Tavg13,Tavg14,Tavg15,Tavg16,Tavg17,Tavg18,Tavg19,Tavg20,Tavg21,Tavg22,Tavg23,Tavg24,Tavg25,Tavg27

if __name__ == "__main__":
    #gen_params(filenames=sys.argv[1], outputfile=sys.argv[1]+"_comsolparams.csv")
    #gen_coords(filenames=sys.argv[1], outputfile=sys.argv[1], hbottom=50)
    #write_df_file(filenames=sys.argv[1], prefix=sys.argv[1] , hs=False)
    #write_df_file(filenames=sys.argv[1], prefix=sys.argv[1] , hs=True)
    #compare(filenames=sys.argv[1])
    gen_power_pattern(powerfile='opensparc', ic_dimensions=[1930,4000], origin='corner')
