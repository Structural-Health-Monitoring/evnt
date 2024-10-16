import os
import glob
from libs.compute_params import GMProcessWaveforms
import inspect

building_data_dir = "/Users/utpalkumar/Library/CloudStorage/Box-Box/NSMP/buildings/motions_ready"

## All stations
all_stations_dir = glob.glob(os.path.join(building_data_dir, "*"))

counter = 0
## Loop over all stations
for station_dir in all_stations_dir:
    station = os.path.basename(station_dir)
    # print(f"> Running for Station: {station}...")

    all_events_zip = glob.glob(os.path.join(station_dir, "*.zip"))

    ## Loop over all events
    for zip_data_file in all_events_zip:
        event = os.path.basename(zip_data_file).replace(".zip", "")
        print(f">> Running for Station: {station}, Event: {event}...")

        # zip_data_file = "/Users/utpalkumar/Library/CloudStorage/Box-Box/NSMP/buildings/motions_ready/CE58389/southnapa_24aug2014_72282711_ce58389p.zip"
        # zip_data_file = "/Users/utpalkumar/Library/CloudStorage/Box-Box/NSMP/buildings/motions_ready/NP1103/piedmont_17aug2015_72507396_np1103p.zip"
        # print(f"    >> Running for file: {zip_data_file}") 
        gm_process = GMProcessWaveforms(zip_data_file)

        ## Get all channel files
        all_chan_data, format_type = gm_process.get_all_channel_files(format_type='.V2c')
        # print(f"    >> Total channel files: {len(all_chan_data)} of format: {format_type}")

        if len(all_chan_data) == 0:
            continue

        ## Read building data
        for sel_chan_file in all_chan_data:
            try:
                counter+=1
                streams = gm_process.read_building_data(sel_chan_file)
                # print(f">>>> Channel file: {sel_chan_file}, Stream: {streams[0]}")
                for trace in streams:
                    trace.detrend(type="linear")
                    trace.detrend(type="constant")
                    print(trace)
                    print(trace[0].stats)

            except Exception as e:
                continue

# print(inspect.getsource(read_dmg))

print(f"Total V2 files: {counter}")