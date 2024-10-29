# Chrystal Chern and Claudio Perez
# Fall 2024
"""
Parse a NSMP smc strong motion data file.
https://escweb.wr.usgs.gov/nsmp-data/smcfmt.html
"""
import sys
import zipfile
import warnings
from pathlib import Path
from collections import defaultdict

import numpy as np

from evnt.utils.parseutils import open_quake

from evnt.core import (
     EventRecord,
     Vector,
     TimeSeries
)

# TODO: A utility to convert general strings into
# appropriate keys; this was copied from v2.py;
# it should be imported from a common utility module.
_make_key = lambda strng: strng.strip().replace(" ", "_").lower()

# def read(file)->"":
#     pass


def read(read_file, verbosity=0, summarize=False, **kwds)->EventRecord:
    """
    """

    zippath    = Path(read_file)
    archive    = zipfile.ZipFile(zippath)
    file_data = defaultdict(lambda : defaultdict(dict))


    # Loop over files in the zipped archive
    for file in archive.namelist():

        # Disregard any files that are not .smc
        if not file.endswith(".smc"):
            continue

        # Optional info logging
        if verbosity > 2:
            print(f"\t\t{file}", file=sys.stderr)

        series, motion_data = read_series(file, archive, verbosity=verbosity,
                                          summarize=summarize, **kwds)
        
        if verbosity > 2:
            print(f"\t{motion_data['location_name']}")

        stype = file.split("_")[-1]
        stype = {
            "a.smc": "accel",
            "d.smc": "displ",
            "v.smc": "veloc",
        }[stype]

        component = file_data[motion_data["location_name"]][motion_data["component"]]

        if stype in component and "corrected" in component[stype]["type"].lower():
            # If we already have the corrected values, pass
            if verbosity > 2:
                print(f"\t\t\tskipping component {component}", file=sys.stderr)
        else:
            if stype in component:
                if verbosity > 1:
                    warnings.warn(f"possibly overwritten channel at ")
                
                # Find a new unique location name for the motion
                while motion_data["location_name"] in file_data:
                    motion_data["location_name"] += "_anothaone"

                component = file_data[motion_data["location_name"]][motion_data["component"]]

            component[stype] = series
            component["station_channel"] = motion_data["station_channel"]
            component["file_name"] = file
            if verbosity > 2:
                print(f"\t\t\tadded component {component}", file=sys.stderr)


    date = None
    motions = {
            k: Vector({
                dir: TimeSeries(
                       component.get("accel", None),
                       component.get("veloc", None),
                       component.get("displ", None),
                    meta=dict(component=dir,
                              station_channel=component["station_channel"],
                              file_name = component["file_name"]
                    )
                )
                for dir,component in motion.items()
            }, dict(location_name=k))
            for k, motion in file_data.items()
    }

    # Collect some other information from the first file (component)
    # first_motion    = list(motions.values())[0]
    # first_component = list(first_motion.components.values())[0]


    metadata = {
        "file_name": str(read_file),
        # "station_name":      first_component.get("station_name", "NA"),
        # "station_coord":     first_component.get("station.coord", "NA"),
        # "record_identifier": first_component.get("record_identifier", "NA"),
        # "station_number":    first_component.get("station.no", "NA")
    }
    return EventRecord(motions, event_date=date, meta=metadata)


def read_record(read_file, archive = None, summarize=False):
    NUM_COLUMNS = 8

    with open_quake(read_file, "r", archive) as f:

        # Text header; first 11 lines
        txt_header = [next(f) for _ in range(11)]

        # 48 integer values spanning 6 lines
        int_header = np.genfromtxt(
            f,
            dtype=int,
            max_rows=5,
            ).flatten()
        int_header = np.append(int_header , np.genfromtxt(
            f,
            dtype=int,
            max_rows=1,
            ).flatten()
        )
        assert len(int_header) == 48

        # Value representing "undefined" or "null" in the integer header.
        int_null = int_header[0]

        # real_header = [next(f) for _ in range(10)]

        real_header = np.genfromtxt(
          f,
          max_rows= 10,
#         delimiter=10,
        ).flatten()

        num_comment_lines = int_header[15]
        len_accel = int_header[16]

        # Parse comments
        comments = [str(next(f)) for _ in range(num_comment_lines)]

        # Parse data

        if not summarize:
            options = dict(
                delimiter=10,
                # skip_header=HEADER_END_LINE + 1,
                #
            )
            data = np.genfromtxt(f, max_rows=np.ceil(len_accel/NUM_COLUMNS) - 1, **options).flatten()
            data = np.append(data, np.genfromtxt(f, max_rows=1, **options))
        else:
            data = []

    return txt_header, int_header, real_header, comments, data


def read_series(
    read_file,
    archive: zipfile.ZipFile = None,
    verbosity: int  = 0,
    summarize: bool =False,
    exclusions: tuple = (),
    **kwds
) -> TimeSeries:

        txt_header, int_header, real_header, comments, data = read(read_file, archive, summarize=summarize)

        time_step = 1/float(real_header[1])

        station = txt_header[5][10:].decode().split("component")[0].strip()
        location = station 
        for line in comments:
            if "<loclbl" in line:
                location = line[12:line.find("<end>")]
                break

        motion_data = {
            "component":       int(int_header[12]),
            "location_name":   location,
            "key":             _make_key(str(txt_header[5][10:]).split("component")[0].strip()),
            "station_channel": str(int_header[8]),
            "time_step":       time_step
        }

        return TimeSeries(data, meta={"type": txt_header[0].decode(),
                                       "ihdr": int_header,
                                       "rhdr": real_header,
                                       "time_step": time_step}), motion_data


