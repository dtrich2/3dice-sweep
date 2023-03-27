import read_helper
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import pandas as pd
import sys
import glob
from PIL import Image
from csv import reader
import matplotlib.patches as patches
import os.path

def plot_temps(base_folder):
	for idx,folder in enumerate(glob.glob(base_folder+"/*")):
		sim_filename=get_sim_filename(f"{folder}/siminfo.txt")
		outfile=f"outputs/temperature_maps/{sim_filename}"
		i=0
		f"{outfile}_{i}.png"
		while os.path.isfile(f"{outfile}_{i}.png"):
			i+=1
		print(f"{outfile}_{i}.png")
		plot_temp(folder,f"{outfile}_{i}")

def get_sim_filename(siminfo_file):
	sim_filename=""
	with open(siminfo_file, "r") as sf:
		data=sf.readlines()[:2]
	for label,val in zip(data[0].split(","),data[1].split(",")):
		if not val.strip():
			break
		sim_filename=sim_filename+f"{label}_{val}_"
	return sim_filename

def plot_temp(base_folder,outfile):
	active_layers=read_helper.get_active_layers(base_folder+"/ic_lcf.csv")
	siminfo=read_helper.get_sim_info(base_folder+"/siminfo.txt")
	grid=read_helper.get_grid(base_folder+"/modelParams.config")
	temps_by_layer=read_helper.read_temps(base_folder+"/output",grid,active_layers)
	figs=[]
	df = pd.DataFrame(data=temps_by_layer[0].astype(float))
	df.to_csv('outfile.csv', sep=' ', header=False, float_format='%.2f', index=False)
	for idx,layer in enumerate(temps_by_layer):
		figs.append(f"{outfile}{idx}.png")
		plot_matrix(layer,[166,174],figs[-1])
	read_helper.combine_figs(figs,f"{outfile}.png")

def plot_matrix(matrix,plot_range,outfile):
	ax = plt.subplot()
	im = ax.imshow(matrix)
	#im.set_clim(plot_range[0],plot_range[1])

	# create an axes on the right side of ax. The width of cax will be 5%
	# of ax and the padding between cax and ax will be fixed at 0.05 inch.
	divider = make_axes_locatable(ax)
	cax = divider.append_axes("right", size="5%", pad=0.05)

	plt.colorbar(im, cax=cax)
	
	

	#display plot
	plt.savefig(outfile)
	plt.clf()

def plot_scaffoldings(scaff_folder):
	ptrace_files=glob.glob(f"{scaff_folder}/power_layer*.ptrace")
	ptrace_files.sort()
	flp_files=get_flp_files(f"{scaff_folder}/ic_lcf.csv")
	
	dims,nlayers=read_helper.get_dims("inputs/dims.info")
	size=(int(dims[0]),int(dims[1]))
	figs=[]
	for idx,flp in enumerate(flp_files):
		figs.append(plot_scaffolding(flp,None,f"outputs/scaffolding{idx}.png",size))
	if len(figs)>0:
		read_helper.combine_figs(figs,"outputs/scaffolding.png")

def get_flp_files(lcf_file):
	flps=[]
	with open(lcf_file, "r") as lcf:
		first=True
		for lcf_line in lcf.readlines():
			if first:
				continue
			split_lcf=lcf_line.strip().split(",")
			flp=split_lcf[1]
			ptrace=split_lcf[-2]
			if ptrace:
				flps.append(f"{scaff_folder}/{flp.split('/')[-1]}")
	flps.reverse()
	print(flps)
	return flps

def plot_scaffolding(scaffolding_flp_file, ptrace_file, outfile, size):
	#VISUALIZE PACT FLP FILE (materials)
	im = Image.new(mode='RGB',size=size)

	# Create figure and axes
	fig, ax = plt.subplots()
	ax.imshow(im)
	ax.invert_yaxis()
	scalar=1e6
	dims=[]
	sizes=[]
	dimsx=[]
	dimsy=[]
	ntsvs=0
	with open(scaffolding_flp_file, 'r') as read_obj:
		flp = reader(read_obj)
		header = next(flp)
		for row in flp:
			if row[-1]=='tsvpillar' or row[-1]=='scaffoldingmat':
				color='g'
				ntsvs=ntsvs+1
			else:
				color='b'
				#print(f"{int(float(row[1])*scalar)},{int(scalar*float(row[2]))},{int(scalar*float(row[3]))},{int(scalar*float(row[4]))}")
			dims.append((int(float(row[1])*scalar), int(scalar*float(row[2]))))
			sizes.append([int(scalar*float(row[3])), int(scalar*float(row[4]))])
			if row[-1]=='tsvpillar':
				dimsx.append(dims[-1][0])
				dimsy.append(dims[-1][1])
			if sizes[-1][0]==0:
				sizes[-1][0]=1
			if sizes[-1][1]==0:
				sizes[-1][1]=1
			rect = patches.Rectangle(dims[-1], 15, 15, linewidth=None, facecolor=color)
			ax.add_patch(rect)
	ax.text(size[0]/2.2,size[1]*0.95,scaffolding_flp_file.split("/")[-1])
	dimsx=list(set(dimsx))
	dimsx.sort()
	dimsy=list(set(dimsy))
	dimsy.sort()
	
	if ptrace_file:
		tile_size_in_cm2=sizes[0][0]*sizes[0][1]/pow(scalar,2)*1e4
		color='r'
		with open(ptrace_file, 'r') as read_obj:
			ptrace = reader(read_obj)
			header = next(ptrace)
			for row in ptrace:
				draw=True
				index=int(row[0])
				power_per_cm2=int(float(row[-1])/tile_size_in_cm2)
				if power_per_cm2>50:
					rect = patches.Rectangle(dims[index], sizes[index][0], sizes[index][1], linewidth=None, facecolor=color)
					ax.add_patch(rect)
	plt.savefig(outfile, dpi=300)
	ax.clear()
	return outfile

if __name__=="__main__":
	temp_map_input="inputs/temp_map"
	plot_temps(temp_map_input)
