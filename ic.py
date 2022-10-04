#class definition for 'ic' (wrapper for 3D-ICE and PACT)

import sys
import os.path
from os import path
import subprocess
import numpy as np
from PACT import *
import time
import cProfile
import glob

class ic:
    def __init__(self, materialdict, latticedict, layerdict, powers, layers, ncopies, tierorders, heatsinks, dimensions, resolution, outputfile, mydir,pact_engine, n_cores, flps=[], ptraces=[]):
        self.pact_engine=pact_engine
        if self.pact_engine=='SPICE_steady':
            self.n_cores=n_cores
        elif self.pact_engine=='SuperLU':
            self.n_cores=1
        self.heatsinks=heatsinks
        self.layerdict=layerdict
        self.latticedict=latticedict
        self.powers=powers
        self.materialdict=materialdict
        self.layers=layers
        self.ncopies=ncopies
        self.dimensions=dimensions
        self.resolution=resolution
        self.area=dimensions[0]/1e6*dimensions[1]/1e6 #area in m^2
        self.granularity=np.round(np.divide(dimensions,resolution),6)
        self.flps=flps
        self.tierorders=tierorders
        self.mydir=mydir
        self.outputfile=mydir+'/'+outputfile
        if not os.access(mydir, os.R_OK):
            os.mkdir(mydir)

    ####################################
    ####3D-ICE FILES#######
    #########################

    def writematerials(self, stk):
        for material in self.materialdict:
            if 'k' not in self.materialdict[material].keys():
                self.materialdict[material]['k']=self.materialdict[material]['kz']
            stk.write("""material {} :
   thermal conductivity     {} ;
   volumetric heat capacity {} ;\n""".format(material,
        self.materialdict[material]['k']*1e-6,  #m to um
        self.materialdict[material]['C']*1e-18))    #m^3 to um^3

    def writeheatsink(self, stk):
            stk.write(f"""top heat sink :
    heat transfer coefficient {self.heatsinks['top']['coefficient']*1e-12};
    temperature {self.heatsinks['externalT']} ;\n""")    #conversion to W/um2K
            stk.write(f"""bottom heat sink :
    heat transfer coefficient {self.heatsinks['bottom']['coefficient']*1e-12};
    temperature {self.heatsinks['externalT']} ;\n""")    #conversion to W/um2K

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

    def writeflp(self, layer, index, flpfile, return_only=False):
        map_matrix=[]
        #normalize ratios to 1
        dimensions=self.dimensions
        resolution=self.resolution
        flp = open(flpfile, "w")
        area_in_cm=dimensions[0]*dimensions[1]*1e-8 #dimensions in um
        tilesize=dimensions[0]/resolution[0]*dimensions[1]/resolution[1]
        loccoords, sizecoords, hslist=([], [], {})
        if len(self.powers[layer]['hslocs'])>0:
            for loc, size, power in zip(self.powers[layer]['hslocs'][index], self.powers[layer]['hssize'][index], self.powers[layer]['hspowers'][index]):
                if self.powers[layer]['hslocs-mode']=='center':
                    loc=np.subtract(loc,np.divide(size,2))   #convert from center to bottom left
                locgrains=np.round(list(np.multiply(loc,resolution)))   #round to fit to granularity
                sizegrains=np.round(list(np.multiply(size,resolution)))
                if sizegrains[0]==0: sizegrains[0]=1        #no hotspot should disappear
                if sizegrains[1]==0: sizegrains[1]=1
                #loccoords.append(list(np.multiply(np.divide(locgrains,resolution),dimensions)))
                #sizecoords.append(list(np.multiply(np.divide(sizegrains,resolution),dimensions)))
                full_hs={}
                for x in range(int(sizegrains[0])):
                    for y in range(int(sizegrains[1])):
                        full_hs[tuple(np.add(locgrains,[x,y]))]=power
                hslist={**hslist, **full_hs}
        for xcoord in list(range(resolution[0])):
            row_powers=[]
            x=xcoord/resolution[0]*dimensions[0]
            for ycoord in list(range(resolution[1])):
                y=ycoord/resolution[1]*dimensions[1]
                power=hslist.get((xcoord,ycoord), self.powers[layer]['bgpowers'][index])
                row_powers.append(power)
                power=np.round(power*1e-8*tilesize,10)  #convert from W/cm2 to W/tile
                #ERROR THROWN: TypeError: can't multiply sequence by non-int of type 'float'
                if not return_only:
                    flp.write("""block_{}_{}:
    position {:.2f}, {:.2f};
    dimension {:.2f}, {:.2f};
    power values {};\n""".format(xcoord, ycoord, x, y, dimensions[0]/resolution[0], dimensions[1]/resolution[1], power))
            map_matrix.append(row_powers)
        flp.close()
        return map_matrix

    def writeflps(self, PACT=False):
        self.flps=[]
        distcounter={}
        origlayer=self.layers.copy()
        dec=False
        #x_mirror_list=[False,True,True,False]
        #y_mirror_list=[False,True,False,True]
        x_mirror_list=[False,False,False,False]
        y_mirror_list=[False,False,False,False]
        for copy in range(self.ncopies):
            for (layer,layernum) in zip(self.layers, list(range(0,len(self.layers)))):
                if layernum==0 and copy>0:
                    dec=True
                    continue
                layernum=layernum+len(self.layers)*copy
                if dec:
                    layernum=layernum-copy
                if not (layer in distcounter) or distcounter[layer]>=len(self.powers[layer]['bgpowers']):
                    distcounter[layer]=0
                if PACT:
                    flpfile=self.mydir+'/'+f"power_layer{layernum}.ptrace"
                    self.write_ptrace_PACT(layer=layer, index=distcounter[layer], ptrace_file=flpfile, x_mirror=x_mirror_list[copy % len(x_mirror_list)], y_mirror=y_mirror_list[copy % len(y_mirror_list)])
                else:
                    flpfile=self.mydir+"/layer{}.flp".format(layernum)
                    self.writeflp(layer=layer, index=distcounter[layer], flpfile=flpfile)
                self.flps.append(flpfile)
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


    def writefiles(self, simulator):
        if simulator=='3D-ICE':
            self.writeflps()
            stk = open(self.mydir+"/stack.stk", "w")
            self.writematerials(stk)
            self.writeheatsink(stk)
            self.writedimensions(stk)
            self.writelayers(stk)
            self.writestack(stk)
            self.writeend(stk)
            stk.close()
        elif simulator=='PACT':
            self.writeflps(PACT=True) #writes ptrace file (3DICE names them differently)
            #cProfile.runctx('self.writeflps(PACT=True)', globals(), locals()) 
            self.write_flps_PACT()
            self.write_config_file_PACT()
            self.write_modelparams_PACT()
            self.write_lcf_PACT()


    #####################
    ####PACT FILES#######
    #####################

    def write_config_file_PACT(self):
        cfg_file = open(self.mydir+"/ic.config", "w")

        #write materials
        for material in self.materialdict:
            cfg_file.write(f"""[{material}]
thermalresistivityxy ((m-k)/w) = {1/self.materialdict[material]['kxy']}
thermalresistivityz ((m-k)/w) = {1/self.materialdict[material]['kz']}
specificheatcapacity (j/m^3k) = {self.materialdict[material]['C']}\n\n""")

        cfg_file.write(f"""[Init]
ambient = {self.heatsinks['externalT']} K
temperature = 273.15 K\n\n""")

        #write heatsink
        if self.heatsinks['top']['type']=='simple':
            cfg_file.write(f"""[NoPackage]
htc = {self.heatsinks['top']['coefficient']}
thickness (m) = {np.round(self.heatsinks['top']['spreader']['thickness']*1e-6,8)}
thermalresistivity ((m-k)/w) = {1/self.heatsinks['top']['spreader']['k']}
specificheatcapacity (j/m^3k) = {self.heatsinks['top']['spreader']['C']}""")
        elif self.heatsinks['top']['type']=='complex':
            cfg_file.write(f"""[HeatSink]
convection_cap (j/k) = {self.heatsinks['top']['coefficient']}
convection_r (k/w) = {1/(self.heatsinks['top']['coefficient']*self.heatsinks['top']['side']*1e-6)}
heatsink_side (m) = {self.heatsinks['top']['side']*1e-6}
heatsink_thickness (m) = {self.heatsinks['top']['thickness']*1e-6}
heatsink_thermalconductivity (w/(m-k)) = {self.heatsinks['top']['k']}
heatsink_specificheatcapacity (j/m^3k) = {self.heatsinks['top']['C']}"
heatspreader_side (m) = {self.heatsinks['top']['spreader']['side']*1e-6}
heatspreader_thickness (m) = {self.heatsinks['top']['spreader']['thickness']*1e-6}
heatspreader_thermalconductivity (w/(m-k)) = {self.heatsinks['top']['spreader']['k']}
heatspreader_specificheatcapacity (j/m^3k) = {self.heatsinks['top']['spreader']['C']}""")

        cfg_file.close()

    def write_modelparams_PACT(self):
        if self.pact_engine=='SuperLU':
            solver_name='SuperLU'
            solver_wrapper='SuperLU.py'
            low_level_solver='KLU'
        elif self.pact_engine=='SPICE_steady':
            solver_name='SPICE_steady'
            solver_wrapper='SPICESolver_steady.py'
            low_level_solver='AZTECOO' #AZTECOO and BELOS: see https://xyce.sandia.gov/downloads/_assets/documents/Users_Guide.pdf
        modelparams=open(self.mydir+"/modelParams.config", "w")
        modelparams.write(f"""[Simulation]
steady_state = True
steady_state_solver = Solver
transient = False
temperature_dependent = False
convergence = 0.1
layer = 1
temperature_dependent_library = TemperatureDependent.py
number_of_core = {self.n_cores}
init_file = False
[Solver]
name = {solver_name}
wrapper = {solver_wrapper}
ll_steady_solver = {low_level_solver}
ll_transient_solver = TRAP
[Grid]
grid_mode = max
type = Uniform
granularity = Grid
rows = {self.resolution[1]}
cols = {self.resolution[0]}
[VirtualNodes]
center_center = 0.5
bottom_center = 1\n""")
        if self.heatsinks['top']['type']=='simple':
            modelparams.write(f"""[NoPackage]
LateralHeatFlow = True
VerticalHeatFlow = False
library_name = NoPackage_sec
library = Solid.py
virtual_node = bottom_center
transient = False
mode = single
[NoPackage_sec]
properties = htc, thickness (m), thermalresistivity ((m-k)/w), specificheatcapacity (j/m^3k)\n""")
        elif self.heatsinks['top']['type']=='complex':
            modelparams.write(f"""[HeatSink]
LateralHeatFlow = True
VerticalHeatFlow = True
library_name = HeatSink_sec
library = HeatSink.py
virtual_node = bottom_center
transient = False
mode = single
[HeatSink_sec]
properties = convection_cap (j/k), convection_r (k/w), heatsink_side (m), heatsink_thickness (m), heatsink_thermalconductivity (w/(m-k)), heatsink_specificheatcapacity (j/m^3k), heatspreader_side (m), heatspreader_thickness (m), heatspreader_thermalconductivity (w/(m-k)), heatspreader_specificheatcapacity (j/m^3k)\n""")
        for material in self.materialdict:
            modelparams.write(f"""[{material}]
library_name = Solid
library = Solid.py
transient = False
virtual_node = bottom_center
mode = single\n""") 
        modelparams.write("""[Solid]
properties = thermalresistivityxy ((m-k)/w), thermalresistivityz ((m-k)/w), specificheatcapacity (j/m^3k)""")

    def write_flp_PACT_regular(self, flpfile,material):
        lattice='through' in self.latticedict.keys()  #for selective patterning, set False. for all the way through patterning, True
        resolution=self.resolution
        dimensions=self.dimensions
        if lattice:
            if material[-8:]!='-lattice':
                lattice_info=self.latticedict['through']
                if material in lattice_info['excluded']:
                    lattice=False
        if material[-8:]=='-lattice':
            material=material[:-8]
            lattice_info=self.latticedict[material]
            lattice=True
        if lattice:
            filler_material=lattice_info['material']
            width=lattice_info['width']   #in um
            pitch=lattice_info['pitch']
            width_in_blocks=np.divide(width,self.granularity).astype(int)
            pitch_in_blocks=np.divide(pitch,self.granularity).astype(int)
            leftover_distance=[int(((resolution[0]-1)%pitch_in_blocks[0]+1)/2),int(((resolution[1]-1)%pitch_in_blocks[1]+1)/2)]
        step=np.round(np.divide(dimensions,resolution)*1e-6,8)  #convert to m
        unitnum=0
        flp = open(flpfile, "w")
        flp.write("UnitName,X,Y,Length (m),Width (m),ConfigFile,Label\n")
        for xcoord in list(range(resolution[0])):
            x=np.round(xcoord/resolution[0]*dimensions[0]*1e-6,8)
            for ycoord in list(range(resolution[1])):
                y=np.round(ycoord/resolution[1]*dimensions[1]*1e-6,8)
                if lattice and lattice_info['type']!='none':
                    if lattice_info['type']=='scaffold':
                        #patterning (or for lines)
                        if (xcoord-leftover_distance[0])%pitch_in_blocks[0]<width_in_blocks[0] or (ycoord-leftover_distance[1])%pitch_in_blocks[1]<width_in_blocks[1]:
                            flp.write(f"{unitnum},{x},{y},{step[0]},{step[1]},,{filler_material}\n")
                        else:
                            flp.write(f"{unitnum},{x},{y},{step[0]},{step[1]},,{material}\n")
                    elif lattice_info['type']=='tsv':
                        #patterning (and for pillars)
                        if (xcoord-leftover_distance[0])%pitch_in_blocks[0]<width_in_blocks[0] and (ycoord-leftover_distance[1])%pitch_in_blocks[1]<width_in_blocks[1]:
                            flp.write(f"{unitnum},{x},{y},{step[0]},{step[1]},,{filler_material}\n")
                        else:
                            flp.write(f"{unitnum},{x},{y},{step[0]},{step[1]},,{material}\n")
                else:
                    flp.write(f"{unitnum},{x},{y},{step[0]},{step[1]},,{material}\n")
                unitnum=unitnum+1
        flp.close()

    def write_flp_PACT_fromfile(self, layernum, flpfile,material,x_mirror,y_mirror):
        resolution=self.resolution
        dimensions=self.dimensions
        lattice_info=self.latticedict['file']
        flps=glob.glob(lattice_info["folder"]+"/*")
        lattice=(material in lattice_info["tiers"])
        step=np.round(np.divide(dimensions,resolution)*1e-6,8)  #convert to m
        if lattice:
            filler_material=lattice_info['material']
            flps.sort(reverse=True)
            flp=flps[(layernum-1) % len(flps)]
            with open(flp,"r") as fp:
                scaff_areas=[]
                for line in fp:
                    w,h,x,y=tuple([float(a) for a in line.split(",")[1:]])
                    w,x=tuple([step[0]*int(dimensions[0]*1e-6*a/step[0]) for a in [w,x]])
                    h,y=tuple([step[1]*int(dimensions[1]*1e-6*a/step[1]) for a in [h,y]])
                    w=max(step[0],w)
                    h=max(step[1],h)
                    scaff_areas.append((w,h,x,y))
        unitnum=0
        flp = open(flpfile, "w")
        flp.write("UnitName,X,Y,Length (m),Width (m),ConfigFile,Label\n")
        for xcoord in list(range(resolution[0])):
            x=np.round(xcoord/resolution[0]*dimensions[0]*1e-6,8)
            for ycoord in list(range(resolution[1])):
                y=np.round(ycoord/resolution[1]*dimensions[1]*1e-6,8)
                mat=material
                if lattice:
                    for w,h,x_test,y_test in scaff_areas:
                        if x_mirror:
                            x_test=dimensions[0]*1e-6-x_test
                            x_bool=(x>x_test-w and x<=x_test)
                        else:
                            x_bool=(x>=x_test and x<x_test+w)
                        if y_mirror:
                            y_test=dimensions[1]*1e-6-y_test
                            y_bool=(y>y_test-h and y<=y_test)
                        else:
                            y_bool=(y>=y_test and y<y_test+h)
                        if x_bool and y_bool:
                            mat=filler_material
                            break
                flp.write(f"{unitnum},{x},{y},{step[0]},{step[1]},,{mat}\n")
                unitnum=unitnum+1
        flp.close()


    def write_flps_PACT(self,fromfile=True):
        self.flps_PACT=[]
        unitnum=0
        compute_counter=0
        #x_mirror_list=[False,True,True,False]
        #y_mirror_list=[False,True,False,True]
        x_mirror_list=[False,False,False,False]
        y_mirror_list=[False,False,False,False]
        for copy in range(self.ncopies):
            for (layer,layernum) in zip(self.layers, list(range(0,len(self.layers)))):
                if layernum==0 and copy>0:
                    continue
                layernum=layernum+(len(self.layers)-1)*copy
                for (tier, tiernum) in zip(self.tierorders[layer], list(range(0,len(self.tierorders[layer])))):
                    flpfile=self.mydir+'/'+f"layer{unitnum}.flp"
                    self.flps_PACT.append(flpfile)
                    if "file" in self.latticedict.keys():
                        if tier=='stackedsi':
                            compute_counter=compute_counter+1
                        self.write_flp_PACT_fromfile(layernum, flpfile=flpfile,material=tier,x_mirror=x_mirror_list[copy % len(x_mirror_list)], y_mirror=y_mirror_list[copy % len(y_mirror_list)])
                    else:
                        self.write_flp_PACT_regular(flpfile=flpfile,material=tier)
                    unitnum=unitnum+1

    def write_ptrace_PACT(self, layer, index, ptrace_file, x_mirror, y_mirror):
        mapmatrix=self.writeflp(layer, index, flpfile="holder.txt", return_only=True)
        unit_area=1e-8*np.multiply(np.divide(self.dimensions[0],self.resolution[0]),np.divide(self.dimensions[1],self.resolution[1]))
        unitnum=0
        ptrace = open(ptrace_file, "w")
        ptrace.write("UnitName,Power\n")
        if y_mirror:
            mapmatrix.reverse()
        for row in mapmatrix:
            if x_mirror:
                row.reverse()
            for unit_power in row:
                ptrace.write(f"{unitnum},{np.multiply(unit_power,unit_area)}\n")
                unitnum=unitnum+1
        ptrace.close()


    def write_lcf_PACT(self):
        lcf = open(self.mydir+"/ic_lcf.csv", "w")
        lcf.write("Layer,FloorplanFile,Thickness (m),PtraceFile,LateralHeatFlow\n")
        unitnum=0
        copies=reversed(list(range(self.ncopies)))
        dec=True
        for copy in copies:
            for (layer,layernum) in zip(list(reversed(self.layers)), list(reversed(range(0,len(self.layers))))):
                if layernum==0 and copy!=0:
                    continue
                layernum=layernum+len(self.layers)*copy
                if dec:
                    layernum=layernum-copy
                for (tier, tiernum) in zip(list(reversed(self.tierorders[layer])), list(reversed(range(0,len(self.tierorders[layer]))))):   #reversing is a hack: lcf file ordered opposite what i thought
                    if tier[-8:]=='-lattice':
                        tier=tier[:-8]
                    if self.layerdict[layer]['sourcetier']==tiernum:
                        if layernum>=len(self.flps):
                            ptrace_file=f"layer{layernum}.bad"
                        else:
                            ptrace_file=self.flps[layernum]
                    else :
                        ptrace_file=""
                    lcf.write(f"{unitnum},{self.flps_PACT[len(self.flps_PACT)-1-unitnum]},{np.round(self.layerdict[layer]['tiers'][tier]*1e-6,9)},{ptrace_file},True\n")
                    unitnum=unitnum+1
        lcf.close()

    #####################
    ####BUILD+SIM########
    #####################

    def simulate(self, simulator, verbose=False):
        start_time=time.time()
        self.writefiles(simulator)
        written_time=time.time()-start_time
        if simulator=='3D-ICE':
            bashCommand = "3D-ICE-Emulator {}".format(self.mydir+"/stack.stk")
            process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()
            if verbose:       
                print(output)
                print(error)
        elif simulator=='PACT':
            if not verbose:
                sys.stdout = open(os.devnull, 'w')  #block print
            PACT(configFile=self.mydir+"/ic.config",
                gridSteadyFile=self.outputfile+".grid.steady",
                initFile=None,
                lcfFile=self.mydir+"/ic_lcf.csv",
                modelParamsFile=self.mydir+"/modelParams.config",
                steadyFile=None)
            if not verbose:
                sys.stdout = sys.__stdout__
        sim_time=time.time()-written_time
        #print(f"files written in {written_time}, executed in {sim_time}")
        return self.readresults(simulator)

    #function to average results from outputfile
    def readresults(self, simulator):
        if simulator=='3D-ICE':
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
        elif simulator=='PACT':
            outputfile=self.outputfile+".grid.steady.layer"
            averages=[]
            maxes=[]
            height=0
            while os.path.exists(outputfile+str(height)):
                temps=np.genfromtxt(outputfile+str(height), delimiter=',')
                averages.append(sum(temps)/len(temps))
                maxes.append(max(temps))
                height=height+1
            averages=[t-273.15 for t in averages]
            maxes=[t-273.15 for t in maxes]
        return (max(maxes), averages, )
