# Claudio Perez
# 2021
import json
from copy import copy
from pathlib import Path
from zipfile import ZipFile
import warnings
from enum import Enum

#import opensees.units
import numpy as np

class st(Enum): ACCEL, DISPL, VELOC = range(3)
class dt(Enum): LONG,  TRAN,  VERT  = range(3)
class pt(Enum): SECT,  PLAN,  ELEV  = range(3)


DIRECTIONS = ["long", "tran", "up"]


class QuakeCollection(dict):
    """
    Container for a collection of QuakeMotion objects
    """

    def __init__(self, motions, event_date=None, meta=None, **kwds):
        meta = meta if meta is not None else {}
        dict.__init__(self, **meta)

        self.motions = motions
        self.event_date = event_date
        for motion in motions.values():
            motion._parent = self
            for comp in motion.components.values():
                comp._parent = motion

    def __repr__(self):
        return f"QuakeCollection({dict.__repr__(self)})"

    @property
    def components(self):
        for motion in self.motions.values():
            for component in motion.components.values():
                yield component

    def serialize(self, serialize_data=True, **kwds) -> dict:
        data = {k: v for k, v in self.items()}
        return {**data, "motions": [i.serialize(**kwds) for i in self.motions.values()]}

    @property
    def components(self):
        for m in self.motions.values():
            for v in m.components.values():
                yield v

    def convert_units(self, units):
        for component in self.components:
            component.convert_units(units)

    def match(self, t, *args, **kwds):
        if callable(t):
            pass

        assert type(t) == str

        if t[0] == "l":
            return self.at(*args, **kwds)
        if t[0] == "r":
            import re
            test = lambda x, y: re.match(str(x), str(y))
        elif t == ">":
            test = lambda x, y: x > y
        elif t == "<":
            test = lambda x, y: x < y

        if len(t) > 1:
            typ = "multi"
        else:
            typ = "single"

        if typ=="single":
            for motion in self.motions.values():
                tests = (
                  k in motion and test(v, motion[k]) for k, v in kwds.items()
                )
                if all(tests):
                    return motion
                for component in motion.components.values():
                    if all(k in component and test(v,component[k]) for k, v in kwds.items()):
                        return component
        elif typ=="multi":
            res = []
            for motion in self.motions.values():
                tests = (
                  k in motion and test(v, motion[k]) for k, v in kwds.items()
                )
                if all(tests):
                    res.append(motion)
                for component in motion.components.values():
                    if all(k in component and test(v,component[k]) for k, v in kwds.items()):
                        res.append(component)
            return res

        return self.at(*args, **kwds)

    def at(self, rtol=1e-05, atol=1e-08, **kwds):
        for motion in self.motions.values():
            tests = (
              k in motion and (
                np.isclose(motion[k],v, rtol=rtol, atol=atol) if isinstance(v,float)\
                        else (motion[k] == v)
              ) for k, v in kwds.items()
            )
            if all(tests):
                return motion

        return self.get_component(**kwds)

    def get_component(self, **kwds):
        for motion in self.motions.values():
            for component in motion.components.values():
                if all(component[k] == v for k, v in kwds.items()):
                    return component


class QuakeMotion(dict):
    """
    A container of `QuakeComponent` objects.
    """
    def _update_components(f):
        def wrapped(*args, **kwds):
            res = f(*args, **kwds)
            [getattr(cmp,s)._refresh()
                    for cmp in res.components.values()
                        for s in ["accel","veloc","displ"] if hasattr(cmp,s)]
            return res
        return wrapped

    def __init__(self, components: dict = None, meta:dict=None, name=None):
        dict.__init__(self)
        self.directions = ["long", "tran", "up"]
        self.components = components if components is not None else {}
        #for k,v in self.components.items():
        #    setattr(self,k,v)
        self.update(meta if meta is not None else {})
        for comp in self.components.values():
            comp._parent = self

    @property
    def long(self):
        return self.components["long"]
    @property
    def tran(self):
        return self.components["tran"]

    @property
    def accel(self):
        return np.stack(tuple(c.accel for c in self.components.values())).T

    @property
    def veloc(self):
        return np.stack(tuple(c.veloc for c in self.components.values())).T

    @property
    def displ(self):
        return np.stack(tuple(c.displ for c in self.components.values())).T

    def __repr__(self):
        #return f"QuakeMotion({dict.__repr__(self)})"
        return f"QuakeMotion({dict.__repr__(self)})"

    def __sub__(self, other):
        ret = copy(self)
        ret.components = {}
        for dirn in DIRECTIONS:
            if dirn in other.components and dirn in self.components:
                ret.components[dirn] = self.components[dirn] - other.components[dirn] 
        return ret

    def __add__(self, other):
        ret = copy(self)
        ret.components = {}
        for dirn in DIRECTIONS:
            if dirn in other.components and dirn in self.components:
                ret.components[dirn] = self.components[dirn] + other.components[dirn] 

        return ret

    def __rsub__(self, other):
        return self.__sub__(other)

    def __radd__(self, other):
        return self.__add__(other)


    def serialize(self, serialize_data=True, **kwds) -> dict:
        return {
            **self,
            "components": [c.serialize(**kwds) for c in self.components.values()]
        }

    @_update_components
    def slice(self, *args):
        for c in self.components.values():
            c.slice(*args)
        return self

    @_update_components
    def rotate(self, angle=None, rotation=None, vert=None):
        """
        > NOTE: This method changes data in the class instance.
        """

        if vert == 3:
            angle *= -1

        rx, ry = (
            np.array([[ np.cos(angle),-np.sin(angle)], 
                      [ np.sin(angle), np.cos(angle)]])
            if not rotation else rotation
        )

        try:
            for attr in ["accel", "veloc", "displ"]:
                x = getattr(self.components["long"], attr).data
                y = getattr(self.components["tran"], attr).data
                X = np.array([x, y])
                x[:] = np.dot(rx, X)
                y[:] = np.dot(ry, X)

        except KeyError as e:
            raise AttributeError("Attempt to rotate a motion that"\
                    f"does not have a '{e.args[0]}' component")

        return self

    def resultant(self):
        # initialize
        series = {k:None for k in ("accel", "veloc", "displ")}
        for typ in series:
            try:
                series[typ] = np.sqrt(sum(
                    np.power(getattr(self.components[dirn],typ), 2)
                    for dirn in self.directions
                        if dirn in self.components and self.components[dirn]
                ))
            except AttributeError as e:
                raise e
        return QuakeComponent(*series.values())

    def match(self, t, *args, **kwds):
        if callable(t):
            pass

        assert type(t) == str

        if t[0] == "l":
            return self.at(*args, **kwds)
        if t[0] == "r":
            import re
            test = lambda x, y: re.match(x, str(y))
        elif t == ">":
            test = lambda x, y: x > y
        elif t == "<":
            test = lambda x, y: x < y

        if len(t) > 1:
            typ = "multi"
        else:
            typ = "single"

        if typ=="single":
            for motion in self.components.values():
                tests = (
                  k in motion and test(v, motion[k]) for k, v in kwds.items()
                )
                if all(tests):
                    return motion

        elif typ=="multi":
            res = []
            for motion in self.components.values():
                tests = (
                  k in motion and test(v, motion[k]) for k, v in kwds.items()
                )
                if all(tests):
                    res.append(motion)
            return res

        return self.at(*args, **kwds)

    def at(self, rtol=1e-05, atol=1e-08, **kwds):
        print(kwds)
        for motion in self.components.values():
            tests = (
              k in motion and (
                np.isclose(motion[k],v, rtol=rtol, atol=atol) if isinstance(v,float)\
                        else (motion[k] == v)
              ) for k, v in kwds.items()
            )
            if all(tests):
                return motion

        return []


class QuakeComponent(dict):
    """A container of QuakeSeries objects"""
    schema_dir = Path(__file__).parents[2] / "etc/schemas"
    schema_file = schema_dir / "component.schema.json"

    def __init__(self, accel, veloc, displ, motion=None, meta=None):
        meta = meta if meta is not None else {}
        self.accel = accel
        self.displ = displ
        self.veloc = veloc
        self._parent = motion

        if not any(i is not None for i in (accel, veloc, displ)):
            raise ValueError("One of accel, veloc or displ must be non-None")
        
        for series in (accel, veloc, displ):
            if series is not None:
                series._parent = self

        dict.__init__(self, **meta)

    @property
    def series(self):
        for s in "accel","veloc","displ":
            yield getattr(self,s)

    def __repr__(self):
        if 'file_name' in self:
            return f"QuakeComponent({self['file_name']}) at {hex(id(self))}"
        else:
            return f"QuakeComponent({self['component']}, " + ", ".join(repr(getattr(self, s, False)) or "" for s in ("accel", "veloc", "displ")) + ")"

    def find_components(self):
        loc = self["location_name"]
        for comp in self._parent.components.values():
            if comp["location_name"] == loc:
                yield comp

    def slice(self, *args):
        for s in "accel","veloc","displ":
            getattr(self,s).slice(*args)
        return self

    def serialize(
        self,
        ljust=0,
        serialize_data=True,
        serialize_series=True,
        humanize_keys=False,
        **kwds,
    ) -> dict:
        if humanize_keys:
            key_name = get_schema_key_map(self.schema_file)
            ret = {key_name(k).ljust(ljust, "."): val for k, val in self.items()}
        else:
            ret = dict(self)
        if serialize_series:
            ret.update(
                {
                    "accel": self.accel.serialize(
                        "accel", serialize_data=serialize_data, **kwds
                    ),
                    "veloc": self.veloc.serialize(
                        "veloc", serialize_data=serialize_data, **kwds
                    ),
                    "displ": self.displ.serialize(
                        "displ", serialize_data=serialize_data, **kwds
                    ),
                }
            )
        return ret



    def __sub__(self, other):
        ret = copy(self)
        if isinstance(other, QuakeComponent):
            for k in ["accel", "veloc", "displ"]:
                setattr(ret, k, getattr(other, k) - getattr(self, k))

        elif isinstance(other, (float, int)):
            for k in ["accel", "veloc", "displ"]:
                setattr(ret, k, other - getattr(self, k))
        return ret

    def __add__(self, other):
        ret = copy(self)
        if isinstance(other, QuakeComponent):
            for k in ["accel", "veloc", "displ"]:
                setattr(ret, k, getattr(other, k) + getattr(self, k))

        elif isinstance(other, (float, int)):
            for k in ["accel", "veloc", "displ"]:
                setattr(ret, k, other + getattr(self, k))
        return ret

    def __mul__(self, other):
        ret = copy(self)
        if isinstance(other, QuakeComponent):
            for k in ["accel", "veloc", "displ"]:
                setattr(ret, k, getattr(other, k) * getattr(self, k))
        elif isinstance(other, (float, int)):
            for k in ["accel", "veloc", "displ"]:
                setattr(ret, k,  other * getattr(self, k))
        return ret

    def __rsub__(self, other):
        return self.__sub__(other)

    def __radd__(self, other):
        return self.__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)


class QuakeSeries(dict):
    def _update_metadata(f):
        def wrapped(*args, **kwds):
            res = f(*args, **kwds)
            res._refresh()
            return res
        return wrapped

    def __init__(self, input_array, dt=None, meta=None, time_zero=0.0, **kwds):
        self._data = np.asarray(input_array)
        assert len(self.data.shape) == 1
        self.update(meta if meta is not None else {})
        self.update(kwds)
        self._time = None
        self.time_zero = time_zero
        if dt is not None:
            self.time_step = self["time_step"] = dt
        if "peak_value" not in self:
            self._refresh()

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self,key)
        except KeyError as e:
            if hasattr(self, "_parent"):
                return self._parent[key]
            else:
                raise e

    def _refresh(self):
        if len(self.data) > 0:
            self["peak_value"] = max(self.data, key=abs)
        return self

    @property
    def data(self):
        return self._data

    def __repr__(self):
        try:
            filename=hex(id(self))
            return f"QuakeSeries({filename},{self['units']})" #{dict.__repr__(self)})"
        except:
            return f"QuakeSeries([{self.data[0]}...{self.data[-1]}])"
    
    def serialize(
        self, key=None, summarize=False, serialize_data=True, humanize_keys=False
    ):

        attributes = {
            #".".join((key, k)): v for k,v in self.items() if k[0] != "_"
            k: v for k,v in self.items() if k[0] != "_"
        }
        if serialize_data and not summarize:
            attributes.update({"data": list(self.data)})
        return attributes

    @_update_metadata
    def __pow__(self, other):
        ret = copy(self)
        ret._data = np.power(ret.data, other)
        return ret

    @_update_metadata
    def __sub__(self, other):
        ret = copy(self)
        if isinstance(other, QuakeSeries):
            ret._data = other.data - self.data

        elif isinstance(other, (float, int)):
            ret._data = other - self.data
        return ret

    @_update_metadata
    def __add__(self, other):
        ret = copy(self)
        if isinstance(other, QuakeSeries):
            ret._data += other.data

        elif isinstance(other, (float, int)):
            ret._data += other
        return ret

    @_update_metadata
    def __mul__(self, other):
        if isinstance(other, (float, int)):
            ret = copy(self)
            ret._data *= other
        else:
            raise TypeError()
        return ret

    @_update_metadata
    def sqrt(self, inplace=False):
        ret = copy(self)
        out = self._data if inplace else None
        ret._data = np.sqrt(self._data, out=out)
        return ret

    def __array__(self,dtype=None):
        return self._data
    
    def __array_ufunc__(self, ufunc, method, *inputs, **kwds):
        if method=="__call__":
            inputs = [i.data if isinstance(i,self.__class__) else i for i in inputs]
            return self.__class__(ufunc(*inputs, **kwds),meta=self,time_zero=self.time_zero)._refresh()
    
    def __rsub__(self, other):
        return self.__sub__(other)
    
    def __radd__(self, other):
        return self.__add__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    @property
    def time(self):
        if self._time is None:
            dt = self["time_step"]
            t0 = self.time_zero
            self._time = np.arange(t0,t0+dt*len(self.data),dt)
        return self._time

    def slice(self,*args):
        time = self.time
        idx = (args[0] < time) & (time < args[1])
        self._time = time[idx]
        self.time_zero = self._time[0]
        self._data = self.data[idx]
        return self

    def plot(self, ax=None, fig=None, label=None, index=(None,), scale=1.0, **kwds):
        # matplotlib takes a very long time to import; avoid
        # loading at module level.
        import matplotlib.pyplot as plt
        idx = slice(*index)
        time = self.time

        if ax is None:
            fig, ax = plt.subplots()
        if label in self:
            label=self[label]
        if label is not None:
            kwds["label"] = label
        ax.plot(time[idx],self.data[idx]*scale, **kwds)
        ax.set_ylabel(f"({self['units']})")
        ax.set_xlabel("time (sec.)")
        return ax



def rotate(data, angle):
    #output = copy(data)
    if isinstance(data, QuakeComponent):
        try:
            data._parent.rotate(angle)
        except Exception as e:
            raise Exception(f"Unable to rotate single component ({e})")

    elif isinstance(data, QuakeCollection):
        for name, record in data.items():
            try:
                record.rotate(angle)
            except KeyError:
                warnings.warn(f"Not rotating record {name}")


def get_schema_key_map(schema_file):
    with open(schema_file, "r") as f:
        schema = json.load(f)["properties"]

    def get_name(key):
        return schema[key]["title"] if key in schema else key

    return get_name


def write_pretty(data):
    output = copy(data)
    schema_dir = Path(__file__).parents[2] / "etc/schemas"
    schema_file = schema_dir / "component.schema.json"
    with open(schema_file, "r") as f:
        schema = json.load(f)["properties"]
    if isinstance(data, QuakeComponent):
        for k in data:
            if k in schema and "units" not in k:
                output[schema[k]["title"]] = output.pop(k)
            else:
                pass

    elif isinstance(data, QuakeCollection):
        for name, record in data.items():
            output[name] = copy(record)
            for dirn, component in record.items():
                output[name][dirn] = copy(component)
                for k, v in component.items():
                    if k in schema and "units" not in k:
                        output[name][dirn][schema[k]["title"]] = output[name][dirn].pop(
                            k
                        )
                    else:
                        pass

    return output


def get_file_type(path_to_zipfile):
    with ZipFile(path_to_zipfile, "r") as readfile:
        if any('.smc' in name for name in readfile.namelist()):
            parser = 'smc.read_event'
        else:
            parser = None