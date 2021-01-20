import pandas as pd

def getdf(filenames):
    df_test= pd.read_csv('results/'+filenames+'.csv')
    return df_test
