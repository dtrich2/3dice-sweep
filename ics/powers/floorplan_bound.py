import sys
import yamlhelper

powerfile='../'+sys.argv[1]
powers=yamlhelper.getcfg(powerfile)
index=0
layer='compute'
tot_area_in_cm=1930*1e-4*4000*1e-4
flp_elements_remaining=[]
for size, power in zip(powers[layer]['hssize'][index], powers[layer]['hspowers'][index]):
	flp_elements_remaining.append([power,size[0]*size[1],1])	#1 is the number of elements remaining to be placed
flp_elements_remaining.sort(key=lambda y: y[0], reverse=True)


with open(sys.argv[1]+'_bounded.yml', 'w') as f:
#make a floorplan for each system of size nlayers
	for nlayers in range(1,61):
		powers=[]
		f.write(f"""compute{nlayers}:
  hslocs:  []
  hspowers: []
  hssize: []
  bgpowers: """)
		for flp_element in flp_elements_remaining:
			#add a counter of size nlayers to each flp element. represents unplaced elements: will subtract 1 when one is placed
			flp_element[2]=nlayers
		#place on each layer, from bottom to top
		for current_layer in range(nlayers):
			area=0
			total_power=0
			while True:	#while the layer isn't full
				placed=False
				#place the highest-power element that fits from all unplaced elements
				for flp_element in flp_elements_remaining:
					if (flp_element[1]+area)<=1 and flp_element[2]>0:
						flp_element[2]=flp_element[2]-1
						area=area+flp_element[1]
						total_power=total_power+flp_element[0]*flp_element[1]*tot_area_in_cm
						placed=True
						break
				if placed==False:	#if no more flp elements can be placed on this layer
					powers.append("{:.2f}".format(total_power/tot_area_in_cm))
					break
		translation = {39: None}
		f.write(str(powers).translate(translation)+'\n')
	f.write("""memory:
  hslocs:  []
  hspowers: []
  hssize: []
  bgpowers: [0.04]
bottomlayer:
  hslocs: []
  hspowers: []
  hssize: []
  bgpowers: [0]""")
				
