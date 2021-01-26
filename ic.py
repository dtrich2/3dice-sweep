#class definition for 'ic' (wrapper for 3D-ICE)

import sys
import os.path
from os import path
import subprocess
import numpy as np

class ic:
    def __init__(self, materialdict, layerdict, distdict, distlist, layers, tierorders, heatsinks, dimensions, resolution, outputfile, mydir, flps=[]):  #layer keys entered in 'layers' from bottom to top
        self.heatsinks=heatsinks
        self.layerdict=layerdict
        self.distlist=distlist
        self.materialdict=materialdict
        self.distdict=distdict
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
        self.layers[0]='compute'    #remove bottomlayer for simplicity
        for (layer,layernum) in zip(self.layers, list(range(0,len(self.layers)))):

            if not (layer in distcounter) or distcounter[layer]>=len(self.distlist[layer]):
                distcounter[layer]=0
            flpfile=self.mydir+"/layer{}.flp".format(layernum)
            self.flps.append(flpfile)
            self.writeflp(powerdens=self.layerdict[layer]['power'], flpfile=flpfile, dist=self.distlist[layer][distcounter[layer]])
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

    def writeflp(self, powerdens, flpfile, dist):
        #normalize ratios to 1
        dimensions=self.dimensions
        resolution=self.resolution
        flp = open(flpfile, "w")
        area_in_cm=dimensions[0]*dimensions[1]*1e-8 #dimensions in um
        totalpower=powerdens*area_in_cm
        loccoords, sizecoords, hslist=([], [], [])
        hstotalsize, weightedratio=(0,0)
        for loc, ratio, size in zip(self.distdict[dist]['hslocs'], self.distdict[dist]['hsratio'], self.distdict[dist]['hssize']):
            loc=np.subtract(loc,np.divide(size,2))   #convert from center to bottom left
            locgrains=np.round(list(np.multiply(loc,resolution)))   #round to fit to granularity
            sizegrains=np.round(list(np.multiply(size,resolution)))
            if sizegrains[0]==0: sizegrains[0]=1        #no hotspot should disappear
            if sizegrains[1]==0: sizegrains[1]=1
            loccoords.append(list(np.multiply(np.divide(locgrains,resolution),dimensions)))
            sizecoords.append(list(np.multiply(np.divide(sizegrains,resolution),dimensions)))
            full_hs=[]
            for x in range(int(sizegrains[0])):
                for y in range(int(sizegrains[1])):
                    full_hs.append(list(np.add(locgrains,[x,y])))
            hslist.append(full_hs)
            weightedratio+=ratio*(sizecoords[-1][0]*sizecoords[-1][1])
            hstotalsize+=sizecoords[-1][0]*sizecoords[-1][1]
        bgsize=dimensions[0]*dimensions[1]-hstotalsize
        weightedratio+=1*bgsize
        weightedratio=totalpower/weightedratio
        normratio = list(np.multiply(weightedratio,self.distdict[dist]['hsratio']))
        normratio.append(weightedratio)
        for xcoord in list(range(resolution[0])):
            x=xcoord/resolution[0]*dimensions[0]
            for ycoord in list(range(resolution[1])):
                y=ycoord/resolution[1]*dimensions[1]
                power=normratio[-1]  #assumed background square until revealed otherwise below
                for hs in hslist:
                    if [xcoord,ycoord] in hs:
                        power=normratio[hslist.index(hs)]
                        break
                power=power*dimensions[0]/resolution[0]*dimensions[1]/resolution[1]
                flp.write("""block_{}_{}:
    position {:.2f}, {:.2f};
    dimension {:.2f}, {:.2f};
    power values {};\n""".format(xcoord, ycoord, x, y, dimensions[0]/resolution[0], dimensions[1]/resolution[1], power))
        flp.close()
