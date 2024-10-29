import sys
import quakeio
from quakeio.smc import read_event

#event = read_event(sys.argv[1], verbosity=3)

event = quakeio.read(sys.argv[1], parser="smc.read_event")

print(event)


for m in event.motions.values():
    print(m)
    for c in m.components.values():
        print("    ", c)

