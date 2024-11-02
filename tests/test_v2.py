#!/bin/env python
from pathlib import Path
import json

import evnt

csmip_archive = Path("dat/58658_007_20210426_10.09.54.P.zip")
csmip_dir = Path("dat/58658_007_20210426_10.09.54.P/")

#----------------------------------------------------------------------
# Event Record (.zip with .v2)
#----------------------------------------------------------------------
def test_read_event():
    return evnt.read(csmip_archive)

def test_unique():
    event = test_read_event()
    assert len(event.series) == 20

#----------------------------------------------------------------------
# Time series (.v2)
#----------------------------------------------------------------------
def test_2():
    csmip_series = evnt.parse.v2.read_record(csmip_dir / "chan001.v2")
    with open("-", "w") as writefile:
        json.dump(csmip_series.meta, writefile)

def test_read():
    csmip_series = evnt.read(csmip_dir / "chan001.v2")
    with open("-", "w") as writefile:
        json.dump(csmip_series.meta, writefile)
    return csmip_series

def test_peak():
    meta = test_read().meta
    assert meta["peak_accel"] == 17.433
    assert meta["peak_veloc"] == 0.205
    assert meta["peak_displ"] == -0.004

def test_accel_data():
    series = test_read()
    assert series.accel[0]  == -0.000102
    assert series.accel[-1] ==  0.000105

def test_veloc_data():
    series = test_read()
    assert series.veloc[0]  == 0.0000950
    assert series.veloc[-1] == 0.0001009


if __name__ == "__main__":
    import sys, yaml
    from pathlib import Path
    from collections import defaultdict

    file_list = sys.argv[1:]

    fields = {k: defaultdict(lambda: 0) for k in ("collection", "motion", "component", "series")}

    
    counts = defaultdict(lambda: 0)
    for file in file_list:
        try:
            collection = evnt.read(file)
        except:
            print(file)
            continue

        counts["collection"] += 1
        for k,v in collection.items():
            fields["collection"][k] += 1
            for motion in collection.serieses.values():
                counts["motion"] += 1
                for k,v in motion.items():
                    fields["motion"][k] += 1
                    for component in motion.components.values():
                        counts["component"] += 1
                        for k,v in component.items():
                            fields["component"][k] += 1
                            for series in "accel", "veloc", "displ":
                                counts["series"] += 1
                                for k,v in getattr(component, series).items():
                                    fields["series"][k] += 1

    results = {
        f"{typ} ({counts[typ]})": {field: fields[typ][field] / counts[typ] for field in fields[typ]}
        for typ in counts
    }
    yaml.dump(results, sys.stdout)
        





