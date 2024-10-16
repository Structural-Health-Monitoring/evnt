import glob
from pathlib import Path
from zipfile import ZipFile
import quakeio
from matplotlib import pyplot as plt
import json

# 1) List of `station_codes`

in_dir = Path("buildings/motions_ready")    # set this as the directory where you have saved the zip files

in_patterns = ["[NWP][PR]????", "CE?????"]
station_dirs = []
for i in in_patterns:
    station_dirs.extend(in_dir.glob(i))
station_codes = [station_dir.name for station_dir in station_dirs]
print(station_codes)


# 2) Read the data from the `i`th event of `my_station`

my_station = "NP1103"  # set this as the station code of interest. see stations_of_interest.md
i = 0                  # set this as the event number of interest

events = in_dir.glob(f"{my_station}/*p.zip")
event = list(events)[i]
with ZipFile(event, "r") as readfile:
    if any('.smc' in name for name in readfile.namelist()):
        parser = 'smc.read_event'
    else:
        parser = None
event_processed = quakeio.read(event, parser=parser, summarize=False)
channel_locations = event_processed.motions

for motion in event_processed.motions.values():
    for component in motion.components.values():
        location = motion['location_name']
        direction = component.get('component','?')
        if component.accel is not None: # change .accel to .veloc or .displ as needed
            plt.plot(component.accel.data, label=f"{location} - {direction}")
plt.legend()



