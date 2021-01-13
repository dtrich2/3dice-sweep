def paths(tree, cur=()):
    if not isinstance(tree, dict):
        yield cur
    else:
        for n, s in tree.items():
            for path in paths(s, cur+(n,)):
                yield path

def writeheader(pspace, results):
    pathlist=paths(getattr(pspace,'default'))
    for mypath in pathlist:
        firststep=True
        for step in mypath:
            if not firststep:
                results.write("_")
            firststep=False
            results.write("{}".format(step))
        results.write(",")
    results.write("T\n")

def writevalues(params, results):
    for mypath in paths(params):
        evalstring=""
        for step in mypath:
            evalstring=evalstring+"['"+step+"']"
        evalstring="results.write(\"{}\".format(params"+evalstring+"))"
        eval(evalstring)
        results.write(",")
