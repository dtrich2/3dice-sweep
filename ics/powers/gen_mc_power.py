import numpy as np
import copy
import yaml
import sys

def generate_random_floorplan(max_layers, n_tiles, mean, sd):
	floorplan={'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[]}
	for layer in range(0,max_layers):
		layer_floorplan={'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[]}
		core_loc=np.random.randint(low=1, high=5, size=2)
		for tile_x in range(0,n_tiles[0]):
			x=tile_x/n_tiles[0]
			for tile_y in range(0,n_tiles[1]):
				y=tile_y/n_tiles[1]
				layer_floorplan['hslocs'].append([x,y])
				if ([tile_x,tile_y]==core_loc).all(): power=100
				else: power=max([0,np.random.normal(loc=mean, scale=sd)])
				layer_floorplan['hspowers'].append(power)
				layer_floorplan['hssize'].append([1/n for n in n_tiles])
				layer_floorplan['bgpowers'].append(0)
		for key in layer_floorplan:
			floorplan[key].append(layer_floorplan[key])
	return floorplan

if __name__ == "__main__":
	flp={'compute': generate_random_floorplan(max_layers=8, n_tiles=[5,5], mean=float(sys.argv[2]), sd=float(sys.argv[3])),
		'memory': {'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[1.305]},
		'bottomlayer': {'hslocs':[], 'hspowers':[], 'hssize':[], 'bgpowers':[0]}}
	#print(flp)
	f = open(sys.argv[1], 'w+')
	yaml.dump(flp, f, default_flow_style=False)
