#class definition for 'ic' (wrapper for 3D-ICE)

import sys
import subprocess

class ic:
    def __init__(self, materialdict, layerdict, layers, tierorders, heatsinks, dimensions, granularity, flps=[]):  #layer keys entered in 'layers' from bottom to top
        self.heatsinks=heatsinks
        self.layerdict=layerdict
        self.materialdict=materialdict
        self.layers=layers
        self.dimensions=dimensions
        self.area=dimensions[0]/1e6*dimensions[1]/1e6 #area in m^2
        self.granularity=granularity
        self.flps=flps
        self.tierorders=tierorders

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
            flpfile="layer{}.flp".format(layernum)
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
    
    def writeend(self,stk,outputfile):
        stk.write("""solver:
    steady ;
    initial temperature 300.0 ;

output:
    Tmap (DIE{}, \"{}\", final) ;\n""".format(len(self.layers)-1, outputfile))


    def writefiles(self, stkfile, outputfile):
        self.writeflps()
        stk = open(stkfile, "w")
        self.writematerials(stk)
        self.writeheatsink(stk)
        self.writedimensions(stk)
        self.writelayers(stk)
        self.writestack(stk)
        self.writeend(stk, outputfile)
        stk.close()

    def simulate(self, stkfile, outputfile, verbose=False):
        self.writefiles(stkfile, outputfile)
        bashCommand = "3D-ICE-Emulator ./{}".format(stkfile)
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        if verbose:       
            print(output)
            print(error)
        return readresults(outputfile)

#function to average results from outputfile
#TODO: MODIFY TO MAX (NOT AVG) WHEN HEAT DIST IS NONUNIFORM
def readresults(outputfile):
    output=open(outputfile, "r")
    output.readline()
    runner=[]
    for line in output:
            flist=[float(i) for i in line.split()]
            if len(flist)!=0:
                runner.append(sum(flist)/len(flist))
    return sum(runner)/len(runner)
