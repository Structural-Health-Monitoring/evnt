"""
core classes and functions of `evnt`.
classes: `EventRecord`, `Vector`, and `TimeSeries`
functions: `get_parser`
"""
from copy import copy
from pathlib import Path
from zipfile import ZipFile
import warnings
import numpy as np


class EventRecord(dict):
    """
    An event record at a single station, as a collection of `TimeSeries` objects.
    Initialized using a dictionary of `'location'`:`TimeSeries` pairs.
    """

    def __init__(self,
                 serieses:dict,
                 event_date=None,
                 meta:dict=None,
                 **kwds):
        
        dict.__init__(self)

        self.serieses = serieses
        self.event_date = event_date
        
        self.update(meta if meta is not None else {})
        for series in serieses.values():
            series._parent = self

    def __repr__(self):
        return f"EventRecord({dict.__repr__(self)})"

    def get_series(self, **kwds):
        """
        Look for a `TimeSeries` in this record that satisfies all
        of the properties specified by `kwds`.
        Only returns the first found.
        """
        for series in self.serieses.values():
            if all(series[k] == v for k, v in kwds.items()):
                return series


class Vector(dict):
    """
    A collection of `TimeSeries` objects at a single location.
    Initialized using a dictionary of `'direction'`:`TimeSeries` pairs.
    """
    def _update_components(f):
        def wrapped(*args, **kwds):
            res = f(*args, **kwds)
            [getattr(cmp,s)._refresh()
                    for cmp in res.components.values()
                        for s in ["accel","veloc","displ"] if hasattr(cmp,s)]
            return res
        return wrapped

    def __init__(self,
                 components:dict=None,
                 meta:dict=None,
                 name=None):
        
        dict.__init__(self)
        
        self.update(meta if meta is not None else {})

        self.components = components if components is not None else {}
        for comp in self.components.values():
            comp._vector_parent = self

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
        return f"Vector({dict.__repr__(self)})"


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
            raise AttributeError("Attempt to rotate a vector that"\
                    f"does not have a '{e.args[0]}' component")

        return self

    def resultant(self):
        # initialize
        vector_norm = {k:None for k in ("accel", "veloc", "displ")}
        for typ in vector_norm:
            try:
                vector_norm[typ] = np.sqrt(sum(
                    np.power(getattr(self.components[dirn],typ), 2)
                    for dirn in ("long", "tran", "vert")
                        if  dirn in self.components and 
                            self.components[dirn] is not None
                ))
            except AttributeError as e:
                raise e
        return TimeSeries(*vector_norm.values())


class TimeSeries(dict):
    """
    Collects the acceleration (`accel`), velocity (`veloc`), and
    displacement (`displ`) at a single component.
    """

    def __init__(self, accel, veloc, displ, dt=None, time_zero=None, record=None, meta=None):
        dict.__init__(self)

        if not any(i is not None for i in (accel, veloc, displ)):
            raise ValueError("One of accel, veloc or displ must be non-None")
        
        self.update(meta if meta is not None else {})

        self.accel = accel
        self.veloc = veloc
        self.displ = displ
            
        self._parent = record

        self.npts = None
        
        for data in (self.accel, self.veloc, self.displ):
            if data is not None:
                assert data.ndim == 1
                if self.npts is None:
                    self.npts = len(data)

        self.time_step = dt
        self.time_zero = time_zero

    def __repr__(self):
        if 'file_name' in self:
            return f"TimeSeries({self['file_name']}) at {hex(id(self))}"
        else:
            return f"TimeSeries object at {hex(id(self))}"

    @property
    def time(self):
        if self._time is None:
            npts = self.npts
            if self.time_zero is None:
                warnings.warn("No time_zero specified. Time array will begin at 0.0s.")
                t0 = 0.0
            else:
                t0 = self.time_zero
            if self.time_step is None:
                warnings.warn("No timestep given. Time array will use 1s sampling time.")
                self._time = np.arange(t0,t0+npts,1)
            else:
                dt = self.time_step
                self._time = np.arange(t0,t0+dt*npts,dt)
        return self._time



from evnt.parse import smc, v2, v2c
ZIP_PARSING_FUNCTIONS = {
    'v2': v2.read,
    'v2c': v2c.read,
    'smc': smc.read,
}
FILE_PARSING_FUNCTIONS = {
    'v2': v2.read_record,
    'v2c': v2c.read_record,
    'smc': smc.read_record,
}

def get_parser(path_to_file):
    """
    Returns the file type and parser to use on the files in the zip.

    :param path_to_file:     path to event zipfile or series file
    :type path_to_file:      pathlib Path object, or string.
    
    :return:                 (``'filetype'``,``parser``)
    :rtype:                  tuple of string, `evnt` parsing function object
    """    
    # recast the path as a Path object
    path_to_file = Path(path_to_file)

    # if it's a zip file, assume it's an event collection
    if path_to_file.suffix.lower()==".zip":
        # open zip file
        with ZipFile(path_to_file, "r") as readfile:
            # check all available file types
            for filetype, parse_function in ZIP_PARSING_FUNCTIONS.items():
                # if found, return file type and corresponding parser
                if any(Path(file).suffix.lower()==f".{filetype}" for file in readfile.namelist()):
                    return filetype, parse_function     
                  
    # otherwise, assume it's an individual series file
    else:
        for filetype, parse_function in FILE_PARSING_FUNCTIONS.items():
            # if found, return file type and corresponding parser
            if path_to_file.suffix.lower()==f".{filetype}":
                return filetype, parse_function   
            
    # if not found, warn and return None for both file type and parser
    warnings.warn(f"No valid parser found for the file {path_to_file}.")
    return None, None

