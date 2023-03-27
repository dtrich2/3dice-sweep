import tkinter as tk
from tkinter.filedialog import asksaveasfilename,askopenfilename
import numpy as np
import translate_power, cat_results
import os, subprocess, logging

def change_mode(my_mode):
	global mode
	mode=my_mode
	if "pillar" in mode:
		global scaff_geom
		load(scaff_geom,"scaff")
	if "power" in mode:
		global power_geom
		load(power_geom,"power")

def get_grid_cell(x,y):
	global pitch
	global grid_max
	grid_cell=[int(min(np.floor(x/pitch),grid_max[0]-1)),int(min(np.floor(y/pitch),grid_max[1]-1))]
	return grid_cell

def draw_grid_cell(grid_cell,cell_class):
	global pitch
	if cell_class=="scaff":
		global scaff_geom
		scaff_geom[grid_cell[0]][grid_cell[1]]=1
		color="green"
		global scaff_rects
		if scaff_rects[grid_cell[0]][grid_cell[1]]==0:
			scaff_rects[grid_cell[0]][grid_cell[1]]=canvas.create_rectangle((grid_cell[0])*pitch+1, (grid_cell[1])*pitch+1, (grid_cell[0]+1)*pitch-1, (grid_cell[1]+1)*pitch-1, fill=color)
	elif cell_class=="power":
		global power_geom
		global power_count
		power_geom[grid_cell[0]][grid_cell[1]]=power_count
		global power_rects
		color=get_color(power_count)
		if power_rects[grid_cell[0]][grid_cell[1]]==0:
			power_rects[grid_cell[0]][grid_cell[1]]=canvas.create_rectangle((grid_cell[0])*pitch+1, (grid_cell[1])*pitch+1, (grid_cell[0]+1)*pitch-1, (grid_cell[1]+1)*pitch-1, fill=color)

def get_color(power_count,color=None):
	colors=["red","blue","yellow","orange","magenta","cyan"]
	if not color:
		return colors[power_count-1]
	else:
		return colors.index(color)+1

def fill_rect(ll,ur):
	draw_power_box()
	for row in range(ur[0]-ll[0]+1):
		for col in range(ur[1]-ll[1]+1):
			draw_grid_cell([row+ll[0],col+ll[1]],"power")

def draw_power_box():
	global power_count
	global grid_idx
	global power_boxes
	global labels
	idx=len(power_boxes)
	labels.append(tk.Label(frm_buttons,text=get_color(power_count)))
	labels[-1].grid(row=grid_idx+2*idx,column=0,sticky="ew", padx=5, pady=5)
	power_boxes.append(tk.Text(frm_buttons, height=1, width=30))
	power_boxes[-1].grid(row=grid_idx+2*idx+1, column=0, sticky="ew", padx=5, pady=5)

def load(to_load,cell_class):
	global power_rects
	global power_count
	global scaff_rects
	global power_boxes
	global labels
	if cell_class=="power":
		power_count=0
		powers=[]
	for x,row in enumerate(to_load):
		for y,col in enumerate(row):
			if col!=0:
				if cell_class=="power":
					if not col in powers:
						powers.append(col)
					power_count=powers.index(col)+1
					power_rects[x][y]=0
					canvas.delete(power_rects[x][y])
				elif cell_class=="scaff":
					scaff_rects[x][y]=0
					canvas.delete(scaff_rects[x][y])
				draw_grid_cell([x,y],cell_class)
	if cell_class=="power":
		if powers:
			if 'power_boxes' in globals():
				for box in power_boxes:
					box.destroy()
			if 'labels' in globals():
				for label in labels:
					label.destroy()
			for count in range(len(powers)):
				power_count=count+1
				draw_power_box()
				power_boxes[-1].insert(tk.END, str(powers[count]))
			power_count=len(powers)+1
		else:
			power_count=1

def load_from_file():
	#filepath = askopenfilename(
	#	filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
	#)
	#if not filepath:
	#	return
	selected_files = [listbox.get(i) for i in listbox.curselection()]
	filepath=selected_files[0]
	with open(filepath, mode="r", encoding="utf-8") as input_file:
		txt_data = input_file.readlines()
	global scaff_geom
	global power_geom
	scaff_data=[]
	power_data=[]
	scaff_read=False
	power_read=False
	for line in txt_data:
		if "scaffolding" in line:
			scaff_read=True
			continue
		elif "power" in line:
			scaff_read=False
			continue
		if scaff_read:
			scaff_data.append([])
		else:
			power_data.append([])
		for col in line.strip().split(",")[:-1]:
			if scaff_read:
				scaff_data[-1].append(int(col))
			else:
				power_data[-1].append(int(col))
	x=len(scaff_data)
	y=len(scaff_data[0])
	txt_bounds.delete('1.0', tk.END)
	txt_bounds.insert(tk.END, f"{y},{x}")
	redraw_canvas()
	for data,cell_class in zip([scaff_data,power_data],["scaff","power"]):
		data=np.array(data).T.tolist()
		load(data,cell_class)

def redraw_canvas():
	global pitch
	global grid_max
	global scaff_geom
	global power_geom
	global scaff_rects
	global power_rects
	global power_count
	global mode
	global power_boxes
	global labels
	power_boxes=[]
	labels=[]
	mode="pillar"
	power_count=1
	canvas.delete("all")
	pitch=10
	try:
		bounds=txt_bounds.get("1.0",'end-1c')
		x,y=(int(bounds.split(",")[0]),int(bounds.split(",")[1]))
	except:
		txt_bounds.delete('1.0', tk.END)
		txt_bounds.insert(tk.END, "10,10")
		bounds=txt_bounds.get("1.0",'end-1c')
		x,y=(int(bounds.split(",")[0]),int(bounds.split(",")[1]))
	save_filename.delete('1.0', tk.END)
	save_filename.insert(tk.END, "file_to_save.txt")
	grid_max=(x,y)
	scaff_geom=np.zeros((x,y),dtype=int).tolist()
	power_geom=np.zeros((x,y),dtype=int).tolist()
	scaff_rects=np.zeros((x,y),dtype=int).tolist()
	power_rects=np.zeros((x,y),dtype=int).tolist()
	for myx in range(x):
	   canvas.create_line(myx*pitch,0,myx*pitch,y*pitch, fill="black", width=1)
	for myy in range(y):
	   canvas.create_line(0,myy*pitch,x*pitch,myy*pitch, fill="black", width=1)

def get_real_powers(power_geom):
	real_powers=[]
	global power_boxes
	#get power translation data structure
	powers=[]
	for box in power_boxes:
		try:
			power=int(box.get("1.0",'end-1c'))
		except:
			print("Powers (W/cm2) not entered")
			return 0
		powers.append(power)
	for row in power_geom:
		real_powers.append([])
		for val in row:
			if val!=0:
				real_powers[-1].append(powers[val-1])
			else:
				real_powers[-1].append(0)
	return real_powers

def save_file():
	filepath=save_filename.get("1.0",'end-1c')
	if not filepath:
		filepath = asksaveasfilename(
			defaultextension=".txt",
			filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
		)
		if not filepath:
			return	
	global scaff_geom
	global power_geom
	real_powers=get_real_powers(power_geom)
	with open(filepath, mode="w", encoding="utf-8") as output_file:
		for to_save,name in zip([scaff_geom,real_powers],['scaffolding','power']):
			output_file.write(f"{name}\n")
			data=np.array(to_save).T.tolist()
			for row in data:
				for col in row:
					output_file.write(f"{str(col)},")
				output_file.write("\n")
	listbox.insert('end', filepath.split('/')[-1])

def mouse_move_canvas(event):
	global mode
	if mode=="pillar":
		grid_cell=get_grid_cell(event.x,event.y)
		draw_grid_cell(grid_cell,"scaff")

def click_canvas(event):
	global mode
	global power_ll
	if mode=="power_ll":
		power_ll=get_grid_cell(event.x,event.y)
		mode="power_ur"
	elif mode=="power_ur":
		global power_count
		fill_rect(power_ll,get_grid_cell(event.x,event.y))
		power_count+=1
		mode="power_ll"
	elif mode=="pillar":
		grid_cell=get_grid_cell(event.x,event.y)
		draw_grid_cell(grid_cell,"scaff")
	elif mode=="erase_pillar":
		global scaff_rects
		grid_cell=get_grid_cell(event.x,event.y)
		canvas.delete(scaff_rects[grid_cell[0]][grid_cell[1]])
		global scaff_geom
		scaff_geom[grid_cell[0]][grid_cell[1]]=0
		scaff_rects[grid_cell[0]][grid_cell[1]]=0
	elif mode=="erase_power":
		global power_rects
		grid_cell=get_grid_cell(event.x,event.y)
		canvas.delete(power_rects[grid_cell[0]][grid_cell[1]])
		power_geom[grid_cell[0]][grid_cell[1]]=0
		power_rects[grid_cell[0]][grid_cell[1]]=0

def move_up():
	posList = listbox.curselection()

	# exit if the list is empty
	if not posList:
	    return

	for pos in posList:

	    # skip if item is at the top
	    if pos == 0:
	        continue

	    text = listbox.get(pos)
	    listbox.delete(pos)
	    listbox.insert(pos-1, text)

def get_temp(dims,size_to_cut,selected_files=None,template_yml="template.yml"):
	global power_boxes
	if not selected_files:
		selected_files = [listbox.get(i) for i in listbox.curselection()]
	translate_power.main(selected_files,size_to_cut,dims,template_yml)
	#subprocess.run('./move_inputs.sh')
	os.system('./move_inputs.sh')

def run_sweep():
	level = logging.INFO #notset, debug, info, warning, error, critical
	FORMAT = '[%(levelname)s] %(asctime)s - %(message)s'
	logging.basicConfig(level=level, format=FORMAT)
	if os.path.exists("combined_results.csv"):
		os.remove("combined_results.csv")
	if os.path.exists("other_params.csv"):
		os.remove("other_params.csv")
	for side_len in [2.2, 4.4, 6.6]:
		for n_repeats in [1,2,3]:
			for size_to_cut in [8,6,4,2,0]:
				data_dict={"n_repeats":n_repeats,"size_to_cut":size_to_cut,"side_len":side_len}
				cat_results.record_params(data_dict)
				logging.info([f"{key} - {value}" for key, value in data_dict.items()])
				stack=["sram0.txt","sram1.txt","sram2.txt","sram3.txt"]*n_repeats
				get_temp([side_len,side_len],size_to_cut,stack,"template-m3d.yml")

if __name__=="__main__":
	sweep=True
	if sweep:
		run_sweep()
	else:
		window = tk.Tk()
		window.title("Scaffolding/Power Layout")

		window.rowconfigure(0, minsize=800, weight=1)
		window.columnconfigure(1, minsize=800, weight=1)

		canvas= tk.Canvas(window)
		canvas.bind("<B1-Motion>", mouse_move_canvas)
		canvas.bind("<Button-1>", click_canvas)
		frm_buttons = tk.Frame(window, relief=tk.RAISED, bd=2)
		txt_bounds = tk.Text(frm_buttons, height=1, width=30)
		save_filename = tk.Text(frm_buttons, height=1, width=30)

		btn_pillar = tk.Button(frm_buttons, text="Draw Pillars", command=lambda: change_mode("pillar"))
		btn_erase_pillar = tk.Button(frm_buttons, text="Erase Pillars", command=lambda: change_mode("erase_pillar"))
		btn_erase_power = tk.Button(frm_buttons, text="Erase Power", command=lambda: change_mode("erase_power"))
		btn_power = tk.Button(frm_buttons, text="Draw Power Rects", command=lambda: change_mode("power_ll"))
		btn_grid = tk.Button(frm_buttons, text="Reset", command=redraw_canvas)
		btn_save = tk.Button(frm_buttons, text="Save Geom", command=save_file)
		btn_load = tk.Button(frm_buttons, text="Load Geom", command=load_from_file)
		btn_temp = tk.Button(frm_buttons, text="Calculate Temp", command=get_temp)
		listbox = tk.Listbox(frm_buttons, selectmode = "multiple")
		btn_up = tk.Button(frm_buttons, text="Move Selected Up", command=move_up)
		for name in os.listdir('.'):
			if name.split('.')[-1]=='txt':
			    listbox.insert('end', name)
		buttons=[txt_bounds,btn_grid,btn_pillar,btn_erase_pillar,btn_power,btn_erase_power,save_filename,btn_save,btn_load,btn_temp,btn_up,listbox]

		for idx,btn in enumerate(buttons):
			btn.grid(row=idx, column=0, sticky="ew", padx=5, pady=5)
		global grid_idx
		grid_idx=len(buttons)

		frm_buttons.grid(row=0, column=0, sticky="ns")
		canvas.grid(row=0, column=1, sticky="nsew")

		redraw_canvas()
		window.mainloop()

