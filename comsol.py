import sys
#helper files
from yamlhelper import *

def translate(filenames, outputfile):
    defaults=getalldefault(getcfg(filenames))
    f = open(outputfile, "w")
    for param in defaults:
        f.write("{}, {}\n".format(param, defaults[param]))
    f.close()

if __name__ == "__main__":
	translate(filenames=sys.argv[1], outputfile=sys.argv[1]+"_comsol.csv")
