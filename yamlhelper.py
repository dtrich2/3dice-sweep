from paramspace import yaml
import paramspace


def paths(tree, cur=()):
    if not isinstance(tree, dict):
        yield cur
    else:
        for n, s in tree.items():
            for path in paths(s, cur+(n,)):
                yield path

def getcfg(filenames):
    with open("./ics/"+filenames+".yml", mode='r') as cfg_file:
        cfg = yaml.load(cfg_file)
    # cfg is now a dict with keys from .yaml file
    return cfg

def getpspace(cfg):
    for toplevel in cfg:
        if isinstance(cfg[toplevel],paramspace.paramspace.ParamSpace):
            return cfg[toplevel]

def flatten(mydict):
    flatdict={}
    pathlist=paths(mydict)
    for mypath in pathlist:
        path=""
        evalstring=""
        for step in mypath:
            evalstring=evalstring+"['"+step+"']"
            if path:
                path+="_"
            path=path+"{}".format(step)
        exec("flatdict['"+path+"']=mydict"+evalstring)
    return flatdict

def expand(mydict):
    expanded={}
    for param in mydict:
        evalstring=""
        for step in param.split("_"):
            if step==param.split("_")[-1]:  #if this is a leaf node
                evalstring+="['"+step+"']"
                exec("expanded"+evalstring+"=mydict['"+param+"']")
            else:
                exec("expanded"+evalstring+".setdefault('"+step+"',{})")   #add key to dictionary if it doesn't exist
                evalstring+="['"+step+"']"
    return expanded

#act on "filenames".yml to display all pertinent information about simulation
def getdefault(cfg, getcoupled=False, getstatic=False, flat=True, detailed=False):
    default={}
    pspace=getpspace(cfg)
    flat_pspace=flatten(pspace._dict)
    itemadder="default[item]=flat_pspace[item]"
    if not detailed:
        itemadder+=".default.value"
    for item in flat_pspace:
        if isinstance(flat_pspace[item], paramspace.paramdim.ParamDim):
            exec(itemadder)
        elif isinstance(flat_pspace[item], paramspace.paramdim.CoupledParamDim):
            if getcoupled:
                exec(itemadder)
        else:
            if getstatic:
                default[item]=flat_pspace[item]
    if not flat:
        return expand(default)
    else:
        return default

def change(flat_pspace, changed):
    newdict={}
    for val in flat_pspace:
        if val in changed:
            newdict[val]=changed[val]
        else:
            newdict[val]=flat_pspace[val]
    return newdict

def listvals(cfg):
    flat_pspace=getdefault(cfg, getcoupled=True, getstatic=True, flat=True, detailed=True)
    for item in flat_pspace:
        if isinstance(flat_pspace[item], paramspace.paramdim.ParamDim):
            print("""{}
            values: {}
            default: {}""".format(item, flat_pspace[item].values, flat_pspace[item].default.value))
        elif isinstance(flat_pspace[item], paramspace.paramdim.CoupledParamDim):
            print("""{}
            coupled to {}""".format(item, flat_pspace[item].target_name))
            if not flat_pspace[item]._use_coupled_values:
                print("    with values {}".format(flat_pspace[item].values))
            if not flat_pspace[item]._use_coupled_default:
                print("    with default {}".format(flat_pspace[item].default.value))
        else:
            print("{} = {}".format(item, flat_pspace[item]))

def writeheader(flat_pspace, keys, results):
    stackstats=[]
    for key in ['nmemory', 'ncompute', 'nrepeats']:
        if isinstance(flat_pspace[key], int):
            stackstats.append(flat_pspace[key])
        else:
            stackstats.append(max(flat_pspace[key].values))
    nmemory, ncompute, nrepeats=tuple(stackstats)
    maxstack=nrepeats*(nmemory+ncompute)
    if ncompute==0: maxstack+=1
    for param in keys:
        results.write("{},".format(param))
    results.write("Tj,Tavg")
    for layer in list(range(maxstack)):
        results.write(",Tavg{}".format(layer))
    results.write("\n")
    

def writevalues(flat_params, keys, results):
    for param in keys:
            results.write("{},".format(flat_params[param]))
