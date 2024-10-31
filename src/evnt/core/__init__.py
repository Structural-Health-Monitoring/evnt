"""
core classes and functions of `evnt`.
classes: `Record`, `Vector`, and `TimeSeries`
functions: `get_parser`
"""
from pathlib import Path
from zipfile import ZipFile
import warnings
import numpy as np



class Record():
    """
    An event record at a single station, as a collection of `TimeSeries` objects.
    """

    def __init__(self, series, meta=None):
        
        self.meta = meta if meta is not None else MetaData(self)

        self.series = series
        self.event_date = meta.get('event_date',None)
        
        for s in series:
            s._parent = self

    def __repr__(self):
        return f"Record({dict.__repr__(self)})"

            

    def filter(self, **kwds)->list:
        """
        Returns all `TimeSeries` in this record that satisfy
        the properties specified by `kwds`.
        """
        series = []
        for s in self.series:
            if all(s[k] == v for k, v in kwds.items()):
                series.append(s)
        return series


    def find(self, **kwds)->"TimeSeries":
        """
        Find the `TimeSeries` in this record that satisfies all
        of the properties specified by `kwds`.
        Assumes there is exactly one.
        If multiple or none are found, an exception is raised.
        """
        series = self.filter(**kwds)
        if len(series) >= 1:
            raise Exception("Multiple TimeSeries found. (Use core.filter)")
        elif len(series) == 0:
            raise Exception("No matching TimeSeries found.")
        else:
            return series


class Vector():
    """
    A collection of `TimeSeries` objects at a single location.
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


class TimeSeries():
    """
    Collects the acceleration (`.accel`), velocity (`.veloc`), and
    displacement (`.displ`) at a single component.
    Initialized using at least one of accel, veloc, or displ.
    """

    def __init__(self, accel=None, veloc=None, displ=None,
                 meta=None):

        if not any(i is not None for i in (accel, veloc, displ)):
            raise ValueError("One of accel, veloc or displ must be non-None")
        
        self.meta = meta if meta is not None else MetaData(self)

        self.accel = accel
        self.veloc = veloc
        self.displ = displ

        self.npts = meta.get('npts',None)
        self.time_step = meta.get('time_step',None)
        self.start_time = meta.get('start_time',None)
        
        for data in (self.accel, self.veloc, self.displ):
            if data is not None:
                data = np.asarray(data)
                assert data.ndim == 1
                if self.npts is None:
                    self.npts = len(data)


    def __repr__(self):
        if 'file_name' in self:
            return f"TimeSeries({self['file_name']}) at {hex(id(self))}"
        else:
            return f"TimeSeries object at {hex(id(self))}"
        

    @property
    def time(self,**kwds):
        if self._time is None:
            npts = self.npts
            if self.start_time is None:
                if kwds.get('verbosity',0) >= 2:
                    warnings.warn("No start time specified. Time array will begin at 0.0s.")
                t0 = 0.0
            else:
                t0 = self.start_time
            if self.time_step is None:
                if kwds.get('verbosity',0) >= 2:
                    warnings.warn("No timestep given. Time array will use 1s sampling time.")
                self._time = np.arange(t0,t0+npts,1)
            else:
                dt = self.time_step
                self._time = np.arange(t0,t0+dt*npts,dt)
        return self._time


class MetaData(dict):
    """
    Collects metadata for objects with safe and coherent access
    through keys, properties, and attributes.
    """
    def __init__(self,
                 parent,
                 **kwds):
        
        dict.__init__(self)

        self.update(parent.meta)



from evnt.parse import smc, v2, v2c
EVENT_PARSING_FUNCTIONS = {
    'v2': v2.read,
    'v2c': v2c.read,
    'smc': smc.read,
}
SERIES_PARSING_FUNCTIONS = {
    'v2': v2.read_record,
    'v2c': v2c.read_record,
    'smc': smc.read_record,
}

def get_parser(path_to_file,**kwds):
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
    # and will be parsed into an `Record`
    if path_to_file.suffix.lower()==".zip":
        # open zip file
        with ZipFile(path_to_file, "r") as readfile:
            # check all available file types
            for filetype, parse_function in EVENT_PARSING_FUNCTIONS.items():
                # if found, return file type and corresponding parser
                if any(Path(file).suffix.lower()==f".{filetype}" for file in readfile.namelist()):
                    return filetype, parse_function     
                  
    # otherwise, assume it's an individual series file
    # and will be parsed into a `TimeSeries`
    else:
        # check all available file types
        for filetype, parse_function in SERIES_PARSING_FUNCTIONS.items():
            # if found, return file type and corresponding parser
            if path_to_file.suffix.lower()==f".{filetype}":
                return filetype, parse_function   
            
    # if not found, warn and return None for both file type and parser
    if kwds.get('verbosity',0)>=0:
        warnings.warn(f"No valid parser found for the file {path_to_file}.")
    return None, None


def record_packer(series,record:Record=None,**kwds)->Record:
    """
    Packs a collection of `TimeSeries` objects into a `Record` object.
    Uses the `channel_number` attribute as the key of each `TimeSeries`.
    If no `channel_number` is found, the `'NoChannel'` key is assigned.
    """
    if record is None:
        record = Record({})
    for s in series:
        # set the key as the channel number if it exists
        try:
            key = s['channel_number']
        # otherwise, assign 'NoChannel' key
        except KeyError as e:
            if kwds.get('verbosity',0)>=2:
                warnings.warn("Attempting to pack a TimeSeries with no channel number into a Record. The 'NoChannel' key will be used.")
            key = 'NoChannel'
        # if the record already has a `TimeSeries` for this key
        # (except for the 'NoChannel' key)
        # merge this new `TimeSeries` in with the existing.
        if key in record:
            s_merge = record[key]
            # set the accel, veloc, and/or displ attr of the existing
            # `TimeSeries` with the current `TimeSeries`.
            for attr in 'accel','veloc','displ':
                if hasattr(s,attr):
                    # if the existing `TimeSeries` already has this
                    # attr, warn before replacing it.
                    if hasattr(s_merge,attr):
                        if kwds.get('verbosity',0)>=2:
                            warnings.warn(f"Multiple TimeSeries with the key {key} were found for Record {Record}. Preceding TimeSeries will be replaced.")
                    setattr(s_merge,attr,getattr(s,attr))
        # otherwise, go ahead and and update the record.
        else:
            record[key] = s
    return record


def vector_packer(series):
    """
    Packs a collection of `TimeSeries` objects into a `Vector` object.
    Uses the `component` attribute as the key of each `TimeSeries`.
    If no `component` is found, the `"NoComponent"` key is assigned.
    """
    pass