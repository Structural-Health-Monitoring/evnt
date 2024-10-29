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
    return evnt.read(csmip_archive, verbosity=12)

def test_unique():
    event = test_read_event()
    all_components = [c for m in event.serieses.values() for c in m.components]
    #all_components = [m for m in event.motions]# for c in m.components]
    assert len(all_components) == 20

#----------------------------------------------------------------------
# Time series (.v2)
#----------------------------------------------------------------------
def test_2():
    csmip_record = evnt.parse.v2.read_record(csmip_dir / "chan001.v2")
    with open("-", "w") as writefile:
        json.dump(csmip_record, writefile)


def test_read():
    csmip_record = evnt.read(csmip_dir / "chan001.v2")
    evnt.write("-", csmip_record, "yaml", summarize=True)
    return csmip_record


def test_peak():
    csmip_motion = test_read()
    assert csmip_motion.accel["peak_value"] == 17.433
    assert csmip_motion.veloc["peak_value"] == 0.205
    assert csmip_motion.displ["peak_value"] == -0.004


def test_peak_time():
    csmip_motion = test_read()
    assert csmip_motion.accel["peak_time"] == 20.270
    assert csmip_motion.veloc["peak_time"] == 20.290
    assert csmip_motion.displ["peak_time"] == 20.270

def test_accel_data():
    csmip_record = test_read()
    assert csmip_record.accel.data[0]  == -0.000102
    assert csmip_record.accel.data[-1] ==  0.000105

def test_veloc_data():
    csmip_record = test_read()
    assert csmip_record.veloc.data[0]  == 0.0000950
    assert csmip_record.veloc.data[-1] == 0.0001009


# csmip_record = quakeio.QuakeComponent(csmip_dir/"chan001.v2")
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
        





