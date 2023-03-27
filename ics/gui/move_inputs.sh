cd ../..
mv ics/gui/gui.yml ics
mv ics/gui/power_gui.yml ics/powers
mv ics/gui/gui_scaff ics/scaff/manual
python3 sweep.py gui
mv results/gui.csv ics/gui/results.csv
mv ice_files/gui/* ics/gui/inputs/temp_map
rm -r ics/scaff/manual/gui_scaff
rm ics/powers/power_gui.yml
rm ics/gui.yml
cd ics/gui
python3 cat_results.py
#cat results.csv >> combined_results.csv
