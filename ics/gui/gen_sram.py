import numpy as np

def build_geom(pitch,n_via,sram_power,sram_repeats):
	scaff=[]
	power=[]
	dim=pitch*(n_via-1)+1
	assert(dim%2==1)
	if sram_repeats==2:
		not_sram_vals=[0,int((dim-1)/2),dim-1]
	elif sram_repeats==1:
		not_sram_vals=[0,dim-1]

	via_vals=[]
	for idx in range(n_via):
		via_vals.append(idx*pitch)
	for x in range(dim):
		scaff.append([])
		power.append([])
		for y in range(dim):
			#power
			if x in not_sram_vals or y in not_sram_vals:
				power[-1].append(0)
			else:
				power[-1].append(sram_power)

			#vias
			if (x in via_vals and y in via_vals) and (x in not_sram_vals or y in not_sram_vals):
				scaff[-1].append(1)
			else:
				scaff[-1].append(0)
	return scaff,power

def write_file(filepath,geom):
	scaff_geom,real_powers=geom
	with open(filepath, mode="w", encoding="utf-8") as output_file:
		for to_save,name in zip([scaff_geom,real_powers],['scaffolding','power']):
			output_file.write(f"{name}\n")
			data=np.array(to_save).T.tolist()
			for row in data:
				for col in row:
					output_file.write(f"{str(col)},")
				output_file.write("\n")

if __name__=="__main__":
	sram_repeats=1
	sram_power=9
	#[2,3,5,9,17],[16,8,4,2,1]
	for n_via,pitch in zip([2,3,5,9],[16,8,4,2]):
		write_file(f"sram{n_via}_{sram_repeats}x{sram_repeats}.txt",build_geom(pitch,n_via,sram_power,sram_repeats))
