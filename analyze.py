#required packages
import sys
import os
import seaborn as sns
from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt

#helper files
from pandashelper import *
from yamlhelper import *

###
#FOR 3D-ICE RESULTS
###

#plot point in paramspace defined by 'default' in "filenames".yml, varying 'tovary' (vector of 1 or 2 parameters)
#modify default space with dict 'changed', each key is the path in the .yml file separated with underscores
def plotter(filenames, tovary, changed={}, comsol=False):
    if comsol: dfname='comsol/'+filenames+'_comsol'
    else: dfname=filenames
    #'jan14log_n3xtv2_old'
    defaults=getdefault(getcfg(filenames), getcoupled=False, getstatic=False, flat=True, detailed=False)
    print(defaults.keys())
    defaults=change(defaults, changed)
    for vary in tovary:
        del defaults[vary]
    df_test=getdf(dfname)
    df_test['Tj']=df_test['Tj']
    if defaults:
        getsubset(mydf=df_test, params=defaults, inplace=True)
    if comsol:
        figname="./results/comsol/"+filenames+"/"
        if os.access(figname, os.R_OK):
            figname=figname+"plots/"
    else: figname="./results/"+filenames+"/"
    if not os.access(figname, os.R_OK):
        os.mkdir(figname)
    for arg in tovary:
        figname+=arg+"_"
    for val in changed:
        figname+="_"+val+"-{}".format(changed[val])
    df_test.to_csv(path_or_buf=figname+'log.csv')
    
    plt.rcParams.update({'font.size': 20})
    plt.figure(figsize=(8, 8), dpi=80)
    if len(tovary)==1:
        sns_plot=sns.scatterplot(x=tovary[0], y='Tj',data=df_test)
        fig=sns_plot.get_figure()
    elif len(tovary)==2:
        #df_test.query("nmemory==1|nmemory==3|nmemory==7", inplace = True)
        df=pd.pivot_table(data=df_test, index=tovary[0], columns=tovary[1], values='Tj')
        """
        x=df.index.values
        y=df.keys().values
        X, Y = np.meshgrid(x,y)
        Z=df.values.transpose()
        cp = ax.contour(X, Y, Z)
        ax.clabel(cp, inline=True, fontsize=10)
        fig.savefig('test.png')
        """
        sns_plot=sns.heatmap(df)
        fig=sns_plot.get_figure()
    elif len(tovary)==3:
        df_test.query("nrepeats<4&nrepeats>1", inplace = True)
        sns_plot = sns.FacetGrid(df_test, col=tovary[0], hue=tovary[1], 
                  #col_order=['red', 'white'], hue_order=['low', 'medium', 'high'],
                  aspect=0.7, height=3.5)
        #sns_plot.set(ylim=(25, 150))
        sns_plot.map(plt.scatter, tovary[2], 'Tj', alpha=0.9, 
              edgecolor='white', linewidth=0.5, s=100)
        l = sns_plot.add_legend(title=tovary[1])
        fig = sns_plot.fig
        plt.figure(figsize=(10,10))
        #fig.subplots_adjust(top=0.8, wspace=0.3)
        #fig.suptitle('Wine Type - Alcohol - Quality - Acidity', fontsize=14)
        #nrepeats nmemory materials_beol_k heatsinks_top_coefficient
        #materials_beol_k nrepeats nmemory Tj
    print("Plotted "+figname+".png")
    
    fig.savefig(figname+".png")
    fig.clf()

def graddf(filenames):
    grads = pd.DataFrame()
    resultsdf=getdf(filenames)
    cfg=getcfg(filenames)
    pspace=getpspace(cfg)
    pspace_info=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
    dim_keys=getdefault(cfg, getcoupled=False, getstatic=False, flat=True, detailed=False).keys()
    print("total: {}".format(pspace.volume))
    for params in tqdm(pspace):
        flat_params=flatten(params)
        dellist=[]
        for param in flat_params:
            if not (param in dim_keys):
                dellist.append(param)
        for param in dellist:
            del flat_params[param]
        currentvals=flat_params.copy()
        dictadd={}
        currtemp=getsubset(mydf=resultsdf, params=flat_params)['T'].values[0]
        for param in flat_params:
            if isinstance(pspace_info[param], paramspace.paramdim.ParamDim):
                sortedvalues=sorted(pspace_info[param].values)
                if not flat_params[param]>=sortedvalues[-1]:    #if the current param isn't maximized
                    nextval=sortedvalues[sortedvalues.index(flat_params[param])+1]
                    flat_params[param]=nextval
                    #print(param+"={}, next={}, T={}".format(currentvals[param], flat_params[param], currtemp))
                    #print(flat_params)
                    nexttemp=getsubset(mydf=resultsdf, params=flat_params)['T'].values[0]
                    flat_params[param]=currentvals[param]
                    dictadd[param+'_grad']=nexttemp-currtemp
        grads=grads.append({**dictadd, **flat_params}, ignore_index=True)  #combine 'dictadd' and 'flat_params' dictionaries

    gradfilename="./results/"+filenames+"/"+filenames+"_grads.csv"
    grads.to_csv(path_or_buf=gradfilename)
    print("Printed "+gradfilename)

def grads(filenames):
    myarray=to_array(filenames, 'Tj')
    grads=np.array(np.gradient(myarray))
    return grads

def avg_effect(g, pspace, dimension, dimval,nrepeats):
    tot_effect=0
    tot=0
    ind=get_dim_index(pspace, dimension)
    nrepeats_ind=get_dim_index(pspace,'nrepeats')
    nmemory_ind=get_dim_index(pspace,'nmemory')
    for index, x in np.ndenumerate(g):
         if index[ind+1]==dimval and index[0]==ind and index[nmemory_ind+1]==1 and index[nrepeats_ind+1]==nrepeats-1:
            tot_effect+=x
            tot+=1
    return tot_effect/tot

#run this if called from command line
if __name__ == "__main__":
    """
    filenames=sys.argv[1]
    g=grads(filenames)
    cfg=getcfg(filenames)
    pspace=getpspace(cfg)
    print(get_dim_val(pspace, 'nrepeats'))
    keys=list(getdefault(cfg).keys())
    results = open(filenames+"_4mem_avg_effects_by_layer.csv", "w")
    keys.remove('nmemory')
    keys.remove('nrepeats')
    for param in keys:
        results.write("{},".format(param))
    results.write("\n")
    avg_effects_by_layer=[]
    for nrepeats in range(1,9):
        avg_effects=[]
        for key in keys:
            avg_effects.append(avg_effect(g, pspace, key,0,nrepeats))
        avg_effects.append(nrepeats)
        for result in avg_effects:
            results.write("{},".format(result))
        results.write("\n")
    results.close()
    """
    plotter(filenames=sys.argv[1], tovary=sys.argv[2:], comsol=False, changed={"heatsinks_top_coefficient": 2e4})
    #to_array(filenames=sys.argv[1])
    """
    filenames='floorplanned_flat_detailed1'
    g=grads(filenames)
    cfg=getcfg(filenames)
    pspace=getpspace(cfg)
    print(get_dim_index(pspace, 'nrepeats'))
    """
    #graddf(filenames=sys.argv[1])
    #cfg=getcfg(filenames=sys.argv[1])
    #listvals(cfg=cfg)
