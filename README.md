# 3dice-sweep
First, get the thermal simulator [PACT](https://github.com/dtrich2/PACT) by running `git clone https://github.com/dtrich2/PACT` in any directory (my_dir).

Next, add the line `setenv PYTHONPATH $PYTHONPATH\:(my_dir)/PACT/src` to your `~/.cshrc` file

Finally, navigate to the `3dice-sweep` directory and run `python3 sweep.py scaffolding-limits`

Create new config files in the `ics` directory and adjust the command accordingly. Results are in the `results` folder.
