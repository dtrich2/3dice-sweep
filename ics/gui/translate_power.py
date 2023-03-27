# uncompyle6 version 3.8.0
# Python bytecode 3.6 (3379)
# Decompiled from: Python 3.6.8 (default, Nov 16 2020, 16:55:22) 
# [GCC 4.8.5 20150623 (Red Hat 4.8.5-44)]
# Embedded file name: /rsgs/pool0/denrich/3d-ice-latest/simfiles/3dice-sweep/ics/gui/translate_power.py
# Compiled at: 2022-11-14 16:55:44
# Size of source mod 2**32: 3248 bytes
import os, shutil, yaml
import numpy as np
import logging

def read_gui_dump(file):
    with open(file, mode='r', encoding='utf-8') as (input_file):
        txt_data = input_file.readlines()
    scaff_data = []
    power_data = []
    scaff_read = False
    power_read = False
    for line in txt_data:
        if 'scaffolding' in line:
            scaff_read = True
            continue
        else:
            if 'power' in line:
                scaff_read = False
                continue
            if scaff_read:
                scaff_data.append([])
            else:
                power_data.append([])
        for col in line.strip().split(',')[:-1]:
            if scaff_read:
                scaff_data[(-1)].append(int(col))
            else:
                power_data[(-1)].append(int(col))
    return (scaff_data, power_data)


def build_yml(powers, dims, filename):
    yml_data = {'bgpowers':[],  'hslocs':[],  'hspowers':[],  'hssize':[],  'hsnames':[],  'hslocs-mode':'bottom left'}
    bottomlayer_data = {'bgpowers':[
      0], 
     'hslocs':[],  'hspowers':[],  'hssize':[],  'hslocs-mode':'bottom left'}
    for power in powers:
        hslocs_line, hspowers_line, hssize_line, hsname_line = ([], [], [], [])
        for x, row in enumerate(power):
            for y, val in enumerate(row):
                hslocs_line.append([x / dims[0], y / dims[1]])
                hspowers_line.append(val)
                hssize_line.append([1 / dims[0], 1 / dims[1]])
                hsname_line.append(str(val))

        yml_data['hslocs'].append(hslocs_line)
        yml_data['hspowers'].append(hspowers_line)
        yml_data['hssize'].append(hssize_line)
        yml_data['hsnames'].append(hsname_line)
        yml_data['bgpowers'].append(0)

    full_data = {'compute':yml_data,  'bottomlayer':bottomlayer_data}
    yaml.dump(full_data, (open(filename, 'w')), default_flow_style=False)


def build_scaff(scaffs, dims, folder):
    for to_empty in [folder, '/rsgs/pool0/denrich/3d-ice-latest/simfiles/3dice-sweep/ics/scaff/manual/gui_scaff']:
        if os.path.isdir(to_empty):
            shutil.rmtree(to_empty)

    os.mkdir(folder)
    width, height = 1 / dims[0], 1 / dims[1]
    for idx, scaff in enumerate(scaffs):
        with open(f"{folder}/scaff{idx}.flp", 'w') as (fp):
            for x, row in enumerate(scaff):
                for y, val in enumerate(row):
                    if val != 0:
                        fp.write(f"{val},{width},{height},{x / dims[0]},{y / dims[1]}\n")


def replace_template(template_dict, in_template, outfile):
    with open(in_template, 'r') as (fp):
        lines = fp.readlines()
    with open(outfile, 'w') as (fp):
        for line in lines:
            for key in template_dict:
                if key in line:
                    line = line.replace(key, template_dict[key])

            fp.write(line)

def cut_edges(data, size_to_cut):
    size_to_cut_lower=int(np.ceil(size_to_cut/2))
    size_to_cut_upper=int(np.floor(size_to_cut/2))
    if size_to_cut_upper != size_to_cut_lower:
        logging.warning(f"Cutting upper {size_to_cut_upper} cells and lower {size_to_cut_lower} cells")
    new_size_y=len(data) - size_to_cut_upper
    new_size_x=len(data[0]) - size_to_cut_upper
    data=data[size_to_cut_lower:new_size_y]
    data=[x[size_to_cut_lower:new_size_x] for x in data]
    return data


def main(tiers, size_to_cut, dims, template_yml):
    level = logging.WARNING #notset, debug, info, warning, error, critical
    FORMAT = '[%(levelname)s] %(asctime)s - %(message)s'
    logging.basicConfig(level=level, format=FORMAT)
    template_dict = {}
    powers, scaffs = [], []
    first = True
    for tier in tiers:
        scaff_data, power_data = read_gui_dump(tier)
        orig_size_y=len(scaff_data)
        orig_size_x=len(scaff_data[0])
        scaff_data=cut_edges(scaff_data,size_to_cut)
        power_data=cut_edges(power_data,size_to_cut)
        powers.append(power_data)
        x, y = len(power_data), len(power_data[0])
        if first:
            scaffs.append(scaff_data)
            first_x = x
            first_y = y
            first = False
        else:
            if x != first_x or y != first_y:
                raise Exception("Tiers don't have same cell count")
            else:
                scaffs.append(scaff_data)
    #the top geometry gets repeated
    #repeated_scaffs=[scaffs[0]]*len(scaffs)
    #scaffs=repeated_scaffs

    dims[1] = np.round(dims[1]*len(scaff_data)/orig_size_y,2)
    dims[0] = np.round(dims[0]*len(scaff_data[0])/orig_size_x,2)
    template_dict['x_cells'] = str(x)
    template_dict['y_cells'] = str(y)
    template_dict['x_dim'] = str(dims[0])
    template_dict['y_dim'] = str(dims[1])
    template_dict['my_lc'] = str(len(tiers))
    build_yml(powers, (x, y), 'power_gui.yml')
    build_scaff(scaffs, (x, y), 'gui_scaff')
    replace_template(template_dict, template_yml, 'gui.yml')


if __name__ == '__main__':
    main()
