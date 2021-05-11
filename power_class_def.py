
#used to perform simulated annealing floorplanning

import random
import numpy as np
from copy import deepcopy

class power:
    def __init__(self, powers, ar_range, dimensions):  #layer keys entered in 'layers' from bottom to top
        self.powers=powers
        self.legalized={}
        for layer in self.powers.keys():
            self.legalized[layer]=[]
            for pattern in range(0,len(self.powers[layer]['hslocs'])):
                self.legalized[layer].append(False)
        self.dimensions=dimensions
        self.ar_range=ar_range
        self.layerorder=list(self.powers.keys()) #used to preserve order
        (self.n_nodes, self.tot_nodes)=self.get_n_nodes()


    def get_n_nodes(self):
        n_nodes={}
        tot_nodes=0
        for layer in self.layerorder:
            n_nodes[layer]=[]
            for pattern in self.powers[layer]['hspowers']:
                n_nodes[layer].append(len(pattern))
                tot_nodes+=len(pattern)
        return (n_nodes, tot_nodes)

    def gen_random_node(self):
        ind=random.randrange(0,self.tot_nodes)
        for layer in self.n_nodes:
            for (node_num,patterncount) in zip(self.n_nodes[layer],range(0,len(self.n_nodes[layer]))):
                ind-=node_num
                if ind<0:
                    key=layer
                    final_ind=(ind+node_num) #correct for 0-index
                    final_pattern=patterncount
                    break
        return {'layer': key, 'pattern': final_pattern, 'ind': final_ind}

    def gen_unique_nodes(self, n_nodes, other_layer):
        nodeinfo=[]
        patterns=[]
        for i in range(n_nodes):
            while True:
                new_node=self.gen_random_node()
                if other_layer and new_node['pattern'] in patterns:
                    continue
                if not(new_node in nodeinfo):
                    nodeinfo.append(new_node)
                    patterns.append(new_node['pattern'])
                    break
        return nodeinfo

    #layer ops
    def node_swap(self, nodeinfo):
        for node in nodeinfo:
            self.legalized[node['layer']][node['pattern']]=False
        for myproperty in ['hspowers', 'hssize']:
            mycopy=deepcopy(self.powers[nodeinfo[0]['layer']][myproperty][nodeinfo[0]['pattern']][nodeinfo[0]['ind']])
            self.powers[nodeinfo[0]['layer']][myproperty][nodeinfo[0]['pattern']][nodeinfo[0]['ind']]=self.powers[nodeinfo[1]['layer']][myproperty][nodeinfo[1]['pattern']][nodeinfo[1]['ind']]
            self.powers[nodeinfo[1]['layer']][myproperty][nodeinfo[1]['pattern']][nodeinfo[1]['ind']]=mycopy

    def pack(self, layer, pattern):
        tot_hotspots=len(self.powers[layer]['hssize'][pattern])
        packed=[]
        for loc,size,hsnum in zip(self.powers[layer]['hslocs'][pattern], self.powers[layer]['hssize'][pattern], range(0,tot_hotspots)):
            packed.append(deepcopy([loc,size,hsnum]))
        return packed

    def legalize(self):
        success=True
        for layer in self.powers:
            for pattern in range(0,len(self.powers[layer]['hslocs'])):
                if not self.legalized[layer][pattern]:
                    i=0
                    while not self.legalize_pattern(layer,pattern,0.05):
                        if i>5: return False
                        i+=1
                self.legalized[layer][pattern]=True
        return success

    def legalize_pattern(self, layer, pattern, boundarysize):
        packed=self.pack(layer, pattern)
        placed=[]
        for hs in random.sample(packed, k=len(packed)):
            open_boxes=find_all_boxes(placed, boundarysize)
            dist_from_point=[]
            for box in open_boxes:
                if hs[1][0]<box[1][0] and hs[1][1]<box[1][1]:
                    if hs[2]%4==0: slack=[0,0]
                    elif hs[2]%4==1: slack=[box[1][0]-hs[1][0],0]
                    elif hs[2]%4==2: slack=[0,box[1][1]-hs[1][1]]
                    elif hs[2]%4==3: slack=[box[1][0]-hs[1][0],box[1][1]-hs[1][1]]
                    dist_from_point.append([(hs[0][0]-box[0][0]+hs[0][1]-box[0][1])**2, list(np.add(box[0],slack))])
            if dist_from_point:
                place_loc=min(dist_from_point)[1]
                placed.append([place_loc, hs[1], hs[2]])
            else:
                for box in open_boxes:
                    area=hs[1][0]*hs[1][1]
                    if area<box[1][1]*box[1][0]:   #if resizing could work
                        if hs[1][0]>=box[1][0]:
                            new_dims_0=box[1][0]
                            new_dims_1=area/hs[1][0]
                            if hs[2]%2==1: slack=[0,box[1][1]-new_dims_1]
                        elif hs[1][1]>=box[1][1]:
                            new_dims_1=box[1][1]
                            new_dims_0=area/hs[1][1]
                            if hs[2]%2==1: slack=[box[1][0]-new_dims_0,0]
                        newar=new_dims_0*self.dimensions[0]/(new_dims_1*self.dimensions[1])
                        if newar>min(self.ar_range) and newar<max(self.ar_range):
                            dist_from_point.append([(hs[0][0]-box[0][0]+hs[0][1]-box[0][1])**2, list(np.add(box[0],slack)), [new_dims_0, new_dims_1]])
                if dist_from_point:
                    place_loc=min(dist_from_point)[1]
                    new_size=min(dist_from_point)[2]
                    placed.append([place_loc, new_size, hs[2]])
                else: return False
        for hs in placed:
            self.powers[layer]['hslocs'][pattern][hs[2]]=hs[0]
            self.powers[layer]['hssize'][pattern][hs[2]]=hs[1]
        return True


def find_all_boxes(packed, boundarysize, smallest_dim=0.05, cladding=0.05):
    lowest_empty_points=find_lowest_empty(packed, boundarysize, dim=1, smallest_dim=smallest_dim)
    all_boxes=[]
    for point in lowest_empty_points:
        point_range=[[[0,0],[0,0]],[[0,0],[0,0]]]   #dim 1: test level min (0) or max (1). dim 2: direction. dim 3: min (0) or max (1)
        for dim in [0,1]:
            point_range[0][dim]=get_point_range(packed, boundarysize, smallest_dim, point=point, dim=dim)
        for dim,linewidth in zip([0,1],[point_range[0][1][1]-point[1]-cladding,point_range[0][0][1]-point[0]-cladding]):
            point_range[1][dim]=get_ceiling(packed, boundarysize, point=point, linewidth=linewidth, dim=dim)
        for first_dim in [0,1]:
            other_first_dim=int(not first_dim)
            bot_left=point
            size=[0,0]
            size[first_dim]=point_range[0][first_dim][1]-point_range[0][first_dim][0]
            size[other_first_dim]=point_range[1][other_first_dim][1]-point_range[1][other_first_dim][0]
            if not [bot_left,size] in all_boxes:
                all_boxes.append([bot_left, size])
    return all_boxes

def get_point_range(packed, boundarysize, smallest_dim, point, dim):    #return empty range along dim nearest to testlevel
    other_dim=int(not dim)
    ranges_on_dim,min_top_hs_on_level=find_ranges_on_level(packed, testlevel=point[other_dim], dim=dim, boundarysize=boundarysize, smallest_dim=smallest_dim)
    ranges_on_dim_inverted=invert_range(ranges_on_dim, boundarysize)
    #print("{}, {}".format(ranges_on_dim_inverted, point))
    dist_from_point=[]
    range_end=0
    for myrange in ranges_on_dim_inverted:
        if point[dim]>=myrange[0] and point[dim]<myrange[1]:
            range_end=myrange[1]
    #if not range_end: print(ranges_on_dim_inverted)
    return [point[dim], range_end]

def get_ceiling(packed, boundarysize, point, linewidth, dim):     #return when a line intersects a hotspot as it is moved up. dim is the direction of movement
    other_dim=int(not dim)
    hs_min_dim=[1-boundarysize]
    for hs in packed:
        if (point[other_dim]<hs[0][other_dim] and point[other_dim]+linewidth>hs[0][other_dim]) or (point[other_dim]<hs[0][other_dim]+hs[1][other_dim] and point[other_dim]+linewidth>hs[0][other_dim]+hs[1][other_dim]):
            #if hs and line overlap in other_dim
            if hs[0][dim]>point[dim]:
                hs_min_dim.append(hs[0][dim])
    return [point[dim], min(hs_min_dim)]

def find_lowest_empty(packed, boundarysize, dim, smallest_dim, cladding=0.005):
    testlevel=boundarysize
    delta=smallest_dim
    other_dim=int(not dim)
    lowest_empty_points=[]
    while testlevel<1-boundarysize:
        lowest_empty_dim=[]
        range_on_level,min_top_hs_on_level=find_ranges_on_level(packed, testlevel, dim, boundarysize, smallest_dim) 
        range_on_level_inverted=invert_range(range_on_level, boundarysize)
        if not range_on_level_inverted: #level is full
            testlevel=min_top_hs_on_level+delta
            continue
        else:
            for hs_range in range_on_level_inverted: #assumes not inverted
                lowest_empty_dim.append(hs_range[0])
        for val in lowest_empty_dim:
            point=[0,0]
            #move every point as far down in other_dim direction as it will go (replace testlevel), remove duplicates
            point[dim]=val
            point[other_dim]=testlevel
            range_on_other_level,min_top_hs_on_other_level=find_ranges_on_level(packed, testlevel=point[dim], dim=other_dim, boundarysize=boundarysize, smallest_dim=smallest_dim) 
            range_on_other_level_inverted=invert_range(range_on_other_level, boundarysize)
            for myrange in range_on_other_level_inverted:
                if testlevel>=myrange[0] and testlevel<myrange[1]:
                    pass#point[other_dim]=myrange[0]
            #print("{} -> {}".format(testlevel, point[other_dim]))
            if not point in lowest_empty_points:
                lowest_empty_points.append(point)
        testlevel=min_top_hs_on_level+delta
    return lowest_empty_points


def find_ranges_on_level(packed, testlevel, dim, boundarysize, smallest_dim):
    range_on_level,top_hs_on_level,bottom_hs_above_level=([],[],[1-boundarysize])
    other_dim=int(not dim)
    for hs,myind in zip(packed, range(0,len(packed))):
        if hs[0][other_dim]<=testlevel and (hs[0][other_dim]+hs[1][other_dim])>testlevel:
            range_on_level.append([hs[0][dim], hs[0][dim]+hs[1][dim]])
            top_hs_on_level.append(hs[0][other_dim]+hs[1][other_dim])
        elif hs[0][other_dim]>=testlevel:
            bottom_hs_above_level.append(hs[0][other_dim])
    if range_on_level:
        range_on_level.sort()
        range_on_level=combine_ranges(range_on_level, smallest_dim, boundarysize)
        return (range_on_level, min(top_hs_on_level))
    elif bottom_hs_above_level:
        return (range_on_level, min(bottom_hs_above_level))
    else:
        return (range_on_level, 1-boundarysize)

def combine_ranges(range_on_level, smallest_dim, boundarysize): #all range_on_level inputs are not inverted
    range_on_level_inverted=invert_range(range_on_level, boundarysize)
    range_on_level_inverted.sort()
    newrange=[]
    for myrange, range_ind in zip(range_on_level_inverted,range(0,len(range_on_level_inverted))):
        if myrange[1]-myrange[0]>=smallest_dim:
            newrange.append(myrange)    
    return invert_range(newrange, boundarysize)

def invert_range(range_on_level, boundarysize):
    newrange=[]
    if range_on_level==[] or range_on_level==[[]]:
        newrange=[[boundarysize, 1-boundarysize]]
        return newrange
    if range_on_level[0][0]>boundarysize:
        newrange.append([boundarysize,range_on_level[0][0]])
    if range_on_level[-1][1]<1-boundarysize:   #last element doesn't hit the boundary
        newrange.append([range_on_level[-1][1],1-boundarysize])
    range_on_level_ind=1
    while range_on_level_ind<len(range_on_level):
        newrange.append([range_on_level[range_on_level_ind-1][1],range_on_level[range_on_level_ind][0]])
        range_on_level_ind+=1
    newrange.sort()
    return newrange

def check_overlaps(packed, hs_index):
    hs_to_check=packed[hs_index]
    overlap_index=[]
    for hs,myind in zip(packed, range(0,len(packed))):
        if myind==hs_index: continue
        overlap=[False,False]
        for dim in [0,1]: #if the lines intersect (if the other hotspot's - and + side span the current hotspot's - or + side)
            if (hs[0][dim]<=hs_to_check[0][dim] and (hs[0][dim]+hs[1][dim])>hs_to_check[0][dim]) or (hs[0][dim]<=(hs_to_check[0][dim]+hs_to_check[1][dim]) and (hs[0][dim]+hs[1][dim])>(hs_to_check[0][dim]+hs_to_check[1][dim])):
                overlap[dim]=True
        if overlap[0] and overlap[1]: overlap_index.append(hs)
    return overlap_index

if __name__ == "__main__":
    boundarysize=0.05
    smallest_dim=0.05
    invert=False
    range_on_level=[[0.1, 0.5],[0.5,0.7],[0.75,0.9]]
    packed=[[[0.1,0.3],[0.4,0.2]]]
    print(find_lowest_empty(packed, boundarysize, dim=1, smallest_dim=smallest_dim, cladding=0.005))

