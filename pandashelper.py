import pandas as pd
import numpy as np
from yamlhelper import *

def getdf(filenames):
    df_test= pd.read_csv('results/'+filenames+'.csv', sep=',')
    return df_test

def getsubset(mydf, params, inplace=False):    #params is flattened
    qstring=""
    for param in params:
        if qstring:
            qstring+="&"
        qstring+=param+"=={}".format(params[param])
    print(qstring)
    if not inplace:
        newframe=mydf.copy()
        newframe.query(qstring, inplace = True)
        return newframe
    else:
        mydf.query(qstring, inplace = True)

def to_array(filenames, column):
    resultsdf=getdf(filenames)
    cfg=getcfg(filenames)
    pspace=getpspace(cfg)
    flat_pspace=getdefault(cfg, getcoupled=False, getstatic=False, flat=True, detailed=True)
    resultarray=np.array(resultsdf[column])
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
        if dimension==name:
            return index

def path_to_name(pspace, dimpath):
    pathlist=dimpath.split('_')
    for dim in pspace.get_info_dict()['dims']:
        if dim['full_path']==pathlist:
            return dim['name']

def add_column(filenames):
    resultsdf=getdf(filenames)
    
    #definitions for new columns
    n_new_columns=3
    if 'Lc' not in resultsdf.columns: resultsdf['Lc']=[list(map(int, str(order))).count(2) for order in resultsdf['layerorder']]
    if 'Lm' not in resultsdf.columns: resultsdf['Lm']=[list(map(int, str(order))).count(3) for order in resultsdf['layerorder']]
    if 'Zm' not in resultsdf.columns: resultsdf['Zm']=[get_zm(order) for order in resultsdf['layerorder']]
    
    #reorder columns to keep results on right
    cols=resultsdf.columns.tolist()
    target_index=cols.index('Tj')
    cols=cols[:target_index]+cols[-1*n_new_columns:]+cols[target_index:-1*n_new_columns]
    resultsdf[cols].to_csv(path_or_buf='results/'+filenames+'.csv', index=False)


if __name__ == "__main__":
    filenames='apr21'
    #print(get_zm(13))
    add_column(filenames)

