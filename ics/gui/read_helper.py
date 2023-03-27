import yaml
import csv
import numpy as np
import os
from PIL import Image

def get_dims(filename):
	data={}
	with open(filename, 'r') as fp:
		csvreader = csv.reader(fp)
		for line in csvreader:
			data[line[0]]=float(line[1])
	return [data["dimx"],data["dimy"]],data["nlayers"]

def read_yml(filename):
	flp=[]
	with open(filename, 'r') as stream:
		flp = yaml.safe_load(stream)
	return flp

def get_active_layers(lcf_file):
	active_layers=[]
	with open(lcf_file,"r") as fp:
		header=fp.readline().split(",")
		ptrace_idx=header.index("PtraceFile")
		for line in fp:
			data=line.split(",")
			ptrace_file=data[ptrace_idx].strip()
			if ptrace_file and ptrace_file.split("/")[-1].split(".")[0].strip()!="power_layer0":
				active_layers.append(int(data[0]))
	return active_layers

def get_sim_info(siminfo_file):
	siminfo={}
	with open(siminfo_file, "r") as fp:
		header=fp.readline().split(",")
		data=fp.readline().split(",")
		for idx,item in enumerate(data):
			if item:
				siminfo[header[idx]]=item

def read_temps(basefilename,grid,active_layers):
	outputfile=basefilename+".grid.steady.layer"
	temp_by_layer=[]
	for layer in active_layers:
		temps=np.genfromtxt(outputfile+str(layer), delimiter=',')
		temps=[t-273.15 for t in temps]
		temps=np.reshape(temps,grid)
		temp_by_layer.append(temps)
	return temp_by_layer

def get_grid(modelparams_file):
	with open(modelparams_file, "r") as fp:
		for line in fp:
			if "rows" in line:
				rows=int(line.split("=")[-1].strip())
			if "cols" in line:
				cols=int(line.split("=")[-1].strip())
	return (rows,cols)

def combine_figs(figs,outname):
	images = [Image.open(x) for x in figs]
	widths, heights = zip(*(i.size for i in images))

	total_width = sum(widths)
	max_height = max(heights)

	new_im = Image.new('RGB', (total_width, max_height))

	x_offset = 0
	for fig,im in zip(figs,images):
	  new_im.paste(im, (x_offset,0))
	  x_offset += im.size[0]
	  os.remove(fig)

	new_im.save(outname)
