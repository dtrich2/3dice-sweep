import translate_power
import numpy as np

def scaffold(file,outfile,pitch,offset=0):
	scaff_data,power_data=translate_power.read_gui_dump(file)
	new_scaff_data=[]
	for y,row in enumerate(power_data):
		new_scaff_data.append([])
		for x,power in enumerate(row):
			scaff_val=0
			if (y%pitch==np.floor(pitch/2)+offset) and (x%pitch==np.floor(pitch/2)+offset):
				scaff_val=1
			new_scaff_data[-1].append(scaff_val)

	write_file(outfile,new_scaff_data,power_data)

def write_file(outfile,scaff_data,power_data):
	with open(outfile, mode="w", encoding="utf-8") as output_file:
		for to_save,name in zip([scaff_data,power_data],['scaffolding','power']):
			output_file.write(f"{name}\n")
			data=np.array(to_save).T.tolist()
			for row in data:
				for col in row:
					output_file.write(f"{str(col)},")
				output_file.write("\n")

if __name__=="__main__":
	scaffold("sys_array.txt","sys_array6.txt",6,-2)
