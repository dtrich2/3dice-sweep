#required packages
import sys
import os
import seaborn as sns
from tqdm import tqdm
import numpy as np

#helper files
from pandashelper import *
from yamlhelper import *

###
#FOR 3D-ICE RESULTS
###

#plot point in paramspace defined by 'default' in "filenames".yml, varying 'tovary' (vector of 1 or 2 parameters)
#modify default space with dict 'changed', each key is the path in the .yml file separated with underscores
def plotter(filenames, tovary, changed={}):
    defaults=getdefault(getcfg(filenames), getcoupled=False, getstatic=False, flat=True, detailed=False)
    defaults=change(defaults, changed)
    for vary in tovary:
        del defaults[vary]
    df_test=getdf(filenames)
    df_test['Tj']=df_test['Tj']
    if defaults:
        getsubset(mydf=df_test, params=defaults, inplace=True)
    figname="./results/"+filenames+"/"
    if not os.access(figname, os.R_OK):
        os.mkdir(figname)
    for arg in tovary:
        figname+=arg+"_"
    for val in changed:
        figname+="_"+val+"-{}".format(changed[val])
    df_test.to_csv(path_or_buf=figname+'log.csv')
    if len(tovary)==1:
        sns_plot=sns.scatterplot(x=tovary[0], y='Tj',data=df_test)
    elif len(tovary)==2:
        df=pd.pivot_table(data=df_test, index=tovary[0], columns=tovary[1], values='Tj')
        sns_plot=sns.heatmap(df)
    print("Plotted "+figname+".png")
    fig=sns_plot.get_figure()
    fig.savefig(figname+".png")
    fig.clf()

def getsubset(mydf, params, inplace=False):    #params is flattened
    qstring=""
    for param in params:
        if qstring:
            qstring+="&"
        qstring+=param+"=={}".format(params[param])
    if not inplace:
        newframe=mydf.copy()
        newframe.query(qstring, inplace = True)
        return newframe
    else:
        mydf.query(qstring, inplace = True)

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

def to_array(filenames):
    resultsdf=getdf(filenames)
    cfg=getcfg(filenames)
    pspace=getpspace(cfg)
    flat_pspace=getdefault(cfg, getcoupled=False, getstatic=False, flat=True, detailed=True)
    resultarray=np.array(resultsdf['T'])
    resultarray=np.reshape(resultarray, pspace.shape)
    return resultarray
    #print(get_dim_index(pspace, 'materials_mem_k'))
    #print(get_dim_val(pspace,'materials_mem_k'))

def get_dim_val(pspace, dimension):
    if isinstance(dimension, int):  #provided the index
        name=list(pspace.dims.items())[dimension][0]
        value=list(pspace.dims.items())[0][1].values
        return {name: value}
    elif isinstance(dimension, str):    #provided the dimension name
        dimension=path_to_name(pspace,dimension)
        value=pspace.dims[dimension].values
    return value

def get_dim_index(pspace, dimension):
    dimension=path_to_name(pspace,dimension)
    for index, name in zip(list(range(len(pspace.dims))),pspace.dims):
        if name==dimension:
            return index

def path_to_name(pspace, dimpath):
    pathlist=dimpath.split('_')
    for dim in pspace.get_info_dict()['dims']:
        if dim['full_path']==pathlist:
            return dim['name']

def grads(filenames):
    myarray=to_array(filenames)
    grads=np.array(np.gradient(myarray))
    return grads

#run this if called from command line
if __name__ == "__main__":
    
    plotter(filenames=sys.argv[1], tovary=sys.argv[2:])
    #to_array(filenames=sys.argv[1])
    #graddf(filenames=sys.argv[1])
    #cfg=getcfg(filenames=sys.argv[1])
    #listvals(cfg=cfg)
