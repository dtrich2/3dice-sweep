import numpy as np
import copy
import yaml
import sys

def generate_random_floorplan(max_layers, n_tiles, mean, sd, peak):
	N=n_tiles[0]*n_tiles[1]
	bg_mean=(mean*N-peak)/(N-1)
	floorplan={'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[]}
	for layer in range(0,max_layers):
		layer_floorplan={'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[]}
		core_loc=np.random.randint(low=1, high=5, size=2)
		for tile_x in range(0,n_tiles[0]):
			x=tile_x/n_tiles[0]
			for tile_y in range(0,n_tiles[1]):
				y=tile_y/n_tiles[1]
				layer_floorplan['hslocs'].append([x,y])
				if ([tile_x,tile_y]==core_loc).all(): power=peak
				else:
					power=np.random.uniform(low=bg_mean-sd, high=bg_mean+sd)
				layer_floorplan['hspowers'].append(power)
				layer_floorplan['hssize'].append([1/n for n in n_tiles])
				layer_floorplan['bgpowers'].append(0)
		for key in layer_floorplan:
			floorplan[key].append(layer_floorplan[key])
	return floorplan

def generate_neuron_floorplan(n_lines, activated_lines, activated_power):
	max_layers=len(activated_lines)
	floorplan={'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[]}
	for layer in range(0,max_layers):
		layer_floorplan={'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[]}
		for line in activated_lines[layer]:
			x=line/n_lines
			layer_floorplan['hslocs'].append([x,0])
			layer_floorplan['hspowers'].append(activated_power)
			layer_floorplan['hssize'].append([1/n_lines,1.0])
		layer_floorplan['bgpowers']=0
		for key in layer_floorplan:
			floorplan[key].append(layer_floorplan[key])
	flp={'compute': floorplan,
	'memory': {'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[0]},
	'bottomlayer': {'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[0]}}
	return flp

def generate_full_floorplan(max_layers, n_tiles, mean, sd, peak, mem_power, neuron=False):
	flp={'compute': generate_random_floorplan(max_layers, n_tiles, mean, sd, peak),
		'memory': {'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[mem_power]},
		'bottomlayer': {'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[0]}}
	return flp

if __name__ == "__main__":
	flp=generate_full_floorplan(max_layers=8, n_tiles=[5,5], mean=float(sys.argv[2]), sd=float(sys.argv[3]), mem_power=0.04)
	f = open('ics/powers/'+sys.argv[1]+'.yml', 'w+')
	yaml.dump(flp, f, default_flow_style=False)
