#!/bin/env python
from pathlib import Path
import json

import evnt

nsmp_archive = Path("dat/berkeley_04jan2018_72948801_np1103p.zip")
nsmp_dir = Path("dat/berkeley_04jan2018_72948801_np1103p/")


#----------------------------------------------------------------------
# Event Record (.zip with .smc)
#----------------------------------------------------------------------
def test_read_event():
    return evnt.read(nsmp_archive)

def test_unique():
    event = test_read_event()
    all_components = [c for m in event.serieses.values() for c in m.components]
    #all_components = [m for m in event.motions]# for c in m.components]
    assert len(all_components) == 20

    for m in event.motions.values():
        print(m)
        for c in m.components.values():
            print("    ", c)


#----------------------------------------------------------------------
# Time series (.smc)
#----------------------------------------------------------------------
def test_a():
    nsmp_record = evnt.parse.smc.read_record(nsmp_dir / "1103.HN2.NP.4E_a.smc")
    with open("-", "w") as writefile:
        json.dump(nsmp_record, writefile)


