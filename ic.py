#class definition for 'ic' (wrapper for 3D-ICE)

import sys
import os.path
from os import path
import subprocess
import numpy as np

class ic:
    def __init__(self, materialdict, layerdict, powers, layers, tierorders, heatsinks, dimensions, resolution, outputfile, mydir, flps=[]):  #layer keys entered in 'layers' from bottom to top
        self.heatsinks=heatsinks
        self.layerdict=layerdict
        self.powers=powers
        self.materialdict=materialdict
        self.layers=layers
        self.dimensions=dimensions
        self.resolution=resolution
        self.area=dimensions[0]/1e6*dimensions[1]/1e6 #area in m^2
        self.granularity=np.divide(dimensions,resolution)
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
        distcounter={}
        origlayer=self.layers.copy()
        for (layer,layernum) in zip(self.layers, list(range(0,len(self.layers)))):
            if not (layer in distcounter) or distcounter[layer]>=len(self.powers[layer]['bgpowers']):
                distcounter[layer]=0
            flpfile=self.mydir+"/layer{}.flp".format(layernum)
            self.flps.append(flpfile)
            self.writeflp(layer=layer, index=distcounter[layer], flpfile=flpfile)
            distcounter[layer]+=1
        self.layers=origlayer

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

    def writeflp(self, layer, index, flpfile, return_only=False):
        map_matrix=[]
        #normalize ratios to 1
        dimensions=self.dimensions
        resolution=self.resolution
        flp = open(flpfile, "w")
        area_in_cm=dimensions[0]*dimensions[1]*1e-8 #dimensions in um
        tilesize=dimensions[0]/resolution[0]*dimensions[1]/resolution[1]
        loccoords, sizecoords, hslist=([], [], [])
        if len(self.powers[layer]['hslocs'])>0:
            for loc, size in zip(self.powers[layer]['hslocs'][index], self.powers[layer]['hssize'][index]):
                #loc=np.subtract(loc,np.divide(size,2))   #convert from center to bottom left
                locgrains=np.round(list(np.multiply(loc,resolution)))   #round to fit to granularity
                sizegrains=np.round(list(np.multiply(size,resolution)))
                if sizegrains[0]==0: sizegrains[0]=1        #no hotspot should disappear
                if sizegrains[1]==0: sizegrains[1]=1
                #loccoords.append(list(np.multiply(np.divide(locgrains,resolution),dimensions)))
                #sizecoords.append(list(np.multiply(np.divide(sizegrains,resolution),dimensions)))
                full_hs=[]
                for x in range(int(sizegrains[0])):
                    for y in range(int(sizegrains[1])):
                        full_hs.append(list(np.add(locgrains,[x,y])))
                hslist.append(full_hs)
        for xcoord in list(range(resolution[0])):
            row_powers=[]
            x=xcoord/resolution[0]*dimensions[0]
            for ycoord in list(range(resolution[1])):
                y=ycoord/resolution[1]*dimensions[1]
                power=self.powers[layer]['bgpowers'][index]  #assumed background square until revealed otherwise below
                for hs in hslist:
                    if [xcoord,ycoord] in hs:
                        power=self.powers[layer]['hspowers'][index][hslist.index(hs)]
                        break
                row_powers.append(power)
                power=np.round(power*1e-8*tilesize,10)  #convert from W/cm2 to W/tile
                if not return_only:
                    flp.write("""block_{}_{}:
    position {:.2f}, {:.2f};
    dimension {:.2f}, {:.2f};
    power values {};\n""".format(xcoord, ycoord, x, y, dimensions[0]/resolution[0], dimensions[1]/resolution[1], power))
            map_matrix.append(row_powers)
        flp.close()
        return map_matrix
