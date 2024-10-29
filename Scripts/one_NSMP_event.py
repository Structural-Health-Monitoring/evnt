import os
from pathlib import Path
from zipfile import ZipFile
from evnt.series import core
from matplotlib import pyplot as plt
import json
import numpy as np
import pandas as pd
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
filetype, parse_function = core.get_parser(event)
event_processed = parse_function(event, summarize=False)
print(event_processed.__dict__)
name = event_processed['file_name']
event_out_dir = out_dir/my_station/name
if not event_out_dir.exists:
    os.makedirs(event_out_dir)
channel_locations = event_processed.motions

fig,ax = plt.subplots()
records = {}
for motion in event_processed.motions.values():
    location = motion['location_name']
    records[location] = {}
    for component in motion.components.values():
        direction = component.get('component','?')
        if component.accel is not None: # change .accel to .veloc or .displ as needed
            records[location][direction] = component.accel.data
            ax.plot(component.accel.data, label=f"{location} - {direction}")
ax.legend()
fig.suptitle(f"Motions for {my_station}; filetype: {filetype}")
fig.savefig(event_out_dir/"motions")
plt.close('all')
from evnt.utils.processing import json_serialize
with open(event_out_dir/"motions.json", "w") as writefile:
    json.dump(records, writefile, cls=json_serialize)

print(f"{len([record for record in records.values() if len(record)>0])} channel responses read and plotted for Station {my_station} at event {event}.")

