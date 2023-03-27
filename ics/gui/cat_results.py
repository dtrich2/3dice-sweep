import os

def cat_results(input_file, other_params_file, output_file):
	other_params={}
	with open(other_params_file,'r') as fp:
		for line in fp:
			key,value=tuple(line.split(","))
			other_params[key]=value.strip()
	with open(input_file,'r') as fp:
		lines=fp.readlines()
		header=lines[0].split(",")
		to_append=[x.split(",") for x in lines[1:]]
	for param in other_params:
		header.insert(0,param)
		for line in to_append:
			line.insert(0,other_params[param])
	if not os.path.exists(output_file): write_header=True
	else: write_header=False
	with open(output_file,'a') as fp:
		if write_header:
			fp.write(",".join(header))
		for line in to_append:
			fp.write(",".join(line))

def record_params(param_dict):
	with open("other_params.csv",'w') as fp:
		for param in param_dict:
			fp.write(f"{param},{param_dict[param]}\n")

if __name__=="__main__":
	cat_results("results.csv","other_params.csv","combined_results.csv")
