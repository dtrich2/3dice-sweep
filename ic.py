#class definition for 'ic' (wrapper for 3D-ICE)

import sys
import os.path
from os import path
import subprocess

class ic:
    def __init__(self, materialdict, layerdict, layers, tierorders, heatsinks, dimensions, granularity, outputfile, mydir, flps=[]):  #layer keys entered in 'layers' from bottom to top
        self.heatsinks=heatsinks
        self.layerdict=layerdict
        self.materialdict=materialdict
        self.layers=layers
        self.dimensions=dimensions
        self.area=dimensions[0]/1e6*dimensions[1]/1e6 #area in m^2
        self.granularity=granularity
        self.flps=flps
        self.tierorders=tierorders
        self.mydir=mydir
        self.outputfile=mydir+'/'+outputfile

    def writematerials(self, stk):
        for material in self.materialdict:
            stk.write("""material {} :
   thermal conductivity     {} ;
   volumetric heat capacity {} ;\n""".format(material,
        self.materialdict[material]['k']*1e-6,  #m to um
        self.materialdict[material]['C']*1e-18))    #m^3 to um^3
    
    def writeheatsink(self, stk):
            stk.write("""top heat sink :
    heat transfer coefficient {};
    temperature 300 ;\n""".format(self.heatsinks['top']['coefficient']*1e-12))    #conversion to W/um2K
            stk.write("""bottom heat sink :
    heat transfer coefficient {};
    temperature 300 ;\n""".format(self.heatsinks['bottom']['coefficient']*1e-12))    #conversion to W/um2K

    def writedimensions(self, stk):
        stk.write("""dimensions :
    chip length {}, width  {};
    cell length  {}, width    {} ;\n""".format(self.dimensions[0], self.dimensions[1], self.granularity[0], self.granularity[1]))

    
    def writelayers(self, stk):
        #iterate over each layer (e.g. compute)
        for layer in self.layerdict:
            stk.write("die {} :\n".format(layer))
            #iterate over tiers in layer
            for (tier, tiernum) in zip(self.tierorders[layer], list(range(0,len(self.tierorders[layer])))): 
                if self.layerdict[layer]['sourcetier']==tiernum:
                    stk.write("    source") 
                else :
                    stk.write("    layer")
                stk.write(" {} {};\n".format(self.layerdict[layer]['tiers'][tier], tier))

    def writeflps(self):
        self.flps=[]
        for (layer,layernum) in zip(self.layers, list(range(0,len(self.layers)))):
            power=self.layerdict[layer]['power']*self.area*1e4     #conversion from m^2 to cm^2
            flpfile=self.mydir+"/layer{}.flp".format(layernum)
            self.flps.append(flpfile)
            flp = open(flpfile, "w")
            flp.write("""C:
    rectangle(0,0,{},{});
    power values {};\n""".format(self.dimensions[0], self.dimensions[1], power))
            flp.close()

    def writestack(self, stk):
        stk.write("stack:\n")
        for (layer,layernum) in zip(self.layers, list(range(0,len(self.layers)))):
            stk.write("    die DIE{} {} floorplan \"{}\";\n".format(layernum, layer, self.flps[layernum]))
    
    def writeend(self,stk):
        stk.write("""solver:
    steady ;
    initial temperature 300.0 ;

output:\n""")
        for layer in list(range(len(self.layers))):
            stk.write("    Tmap (DIE{}, \"{}\", final) ;\n".format(layer, self.outputfile+str(layer)))


    def writefiles(self):
        self.writeflps()
        stk = open(self.mydir+"/stack.stk", "w")
        self.writematerials(stk)
        self.writeheatsink(stk)
        self.writedimensions(stk)
        self.writelayers(stk)
        self.writestack(stk)
        self.writeend(stk)
        stk.close()

    def simulate(self, verbose=False):
        self.writefiles()
        bashCommand = "3D-ICE-Emulator {}".format(self.mydir+"/stack.stk")
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        if verbose:       
            print(output)
            print(error)
        return self.readresults()

    #function to average results from outputfile
    #TODO: MODIFY TO MAX (NOT AVG) WHEN HEAT DIST IS NONUNIFORM
    def readresults(self):
        averages=[]
        maxes=[]
        for height in list(range(len(self.layers))):
            output=open(self.outputfile+str(height), "r")
            output.readline()
            flist=[]
            for line in output:
                a=[float(i) for i in line.split()]
                if len(a)!=0:
                    flist.extend(a)
            averages.append(sum(flist)/len(flist))
            maxes.append(max(flist))
        averages=[t-273.15 for t in averages]
        maxes=[t-273.15 for t in maxes]
        return (max(maxes), averages)


