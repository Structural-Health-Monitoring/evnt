import os
from pathlib import Path
from zipfile import ZipFile
from matplotlib import pyplot as plt
import json
import numpy as np
import evnt
from evnt.parse import smc, v2, v2c

# 0) Output directory
out_dir = Path("out")    # set this as the directory in which to save outputs
if not out_dir.exists():
    os.makedirs(out_dir)

# 1) List of `station_codes`

in_dir = Path("/Users/cchern/seismology/NSMP/buildings/motions_ready")    # set this as the directory where you have saved the zip files

in_patterns = ["[NWP][PR]????", "CE?????"]
station_dirs = []
for i in in_patterns:
    station_dirs.extend(in_dir.glob(i))
station_codes = [station_dir.name for station_dir in station_dirs]
with open(out_dir/"station_codes.txt", "w") as writefile:
    print(station_codes, file=writefile)


# 2) Read the data from the `i`th event of `my_station`

my_station = "NP1103"  # set this as the station code of interest. see stations_of_interest.md
i = 0                  # set this as the event number of interest

events = in_dir.glob(f"{my_station}/*p.zip")
event = list(events)[i]
with ZipFile(event, "r") as readfile:
    if any(file.endswith(".smc") for file in readfile.namelist()):
        parser = smc
    else:
        parser = None
event_processed = evnt.parse.smc.read_event(event, summarize=False)
channel_locations = event_processed.motions

fig,ax = plt.subplots()
for motion in event_processed.motions.values():
    for component in motion.components.values():
        location = motion['location_name']
        direction = component.get('component','?')
        if component.accel is not None: # change .accel to .veloc or .displ as needed
            ax.plot(component.accel.data, label=f"{location} - {direction}")
ax.legend()
fig.savefig(out_dir/f"{my_station}")
plt.close('all')

