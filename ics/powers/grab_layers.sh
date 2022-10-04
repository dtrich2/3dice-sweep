sourcedir=/rsgs/pool0/denrich/power/mflowgen/designs/chipyard/build-dc-rocket/8-thermal-sim-translate/outputs
prefix=rocket_dhrystone
files=${sourcedir}/*.yaml
for file in $files
do
	filename=`basename $file`
	filename="${filename%.*}"
	cp $file ./${prefix}_${filename}.yml
done 
