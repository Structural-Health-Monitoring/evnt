"""
core classes and functions of `evnt`.
classes: `Record`, `Vector`, and `TimeSeries`
functions: `get_parser`

`Record`
    `.series`: list of `TimeSeries`
    `.meta`: dictionary-like `MetaData` object
    `for i in Record` to iterate through `.series` # TODO: How to implement this??

`Vector`
    `components`: dictionary of `'dirn'`:`TimeSeries`
    `.meta`: dictionary-like `MetaData` object
    `for i in Vector` to iterate through `.series`

`TimeSeries`
    `.accel`, `.veloc`, `.displ`: np.ndarray
    `.meta`: dictionary-like `MetaData` object

"""

from pathlib import Path
from zipfile import ZipFile
import warnings
import numpy as np



class Record:
    """
    An event or ambient record at a single station.
    `.series`: list of `TimeSeries`
    `.meta`: dictionary-like `MetaData` object
    `for i in Record` to iterate through `.series`
    """

    def __init__(self, series, meta:"MetaData"=None):
        
        self.meta = meta if meta is not None else MetaData()
        # possible items in meta:
        #   'event_date': global date and time at start of record
        #   'event_id': network station event ID, e.g. 'nc72948801'
        #   'building_height': height of building, if applicable
        #   'file_name': name of file,
        #                e.g 'berkeley_04jan2018_72948801_np1103p.zip'

        self.series = list(series)
        self._consolidate()
        
        for s in series:
            s._parent = self


    def __repr__(self):
        if 'event_date' in self.meta.keys():
            return f"Record({self.meta['event_date']}) at {hex(id(self))}" # TODO: is this weird?
        elif 'file_name' in self:
            return f"Record({self.meta['file_name']}) at {hex(id(self))}"
        else:
            return f"Record object at {hex(id(self))}"


    def filter(self, **kwds)->list:
        """
        Returns all `TimeSeries` in this record that satisfy
        the properties specified by `kwds`.
        """
        series = []
        for s in self.series:
            if all(s[k] == v for k,v in kwds.items()):
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
    

    def _consolidate(self,**kwds):
        """
        Consolidates the `TimeSeries` in the Record
        so that there is only one `TimeSeries` per channel.
        Raises warning if multiple `TimeSeries` are found
        for a single channel.
        """
        consolidated = {}
        unknown_channel = []
        for s in self.series:
            key = s.meta.get('channel',None)
            if key is not None:
                # if there isn't already a Timeseries
                # at this channel, add it.
                if key not in consolidated.keys():
                    consolidated[key] = s
                # if there is already a Timeseries at this
                # channel, merge it.
                else:
                    existing_s = consolidated[key]
                    # set the accel, veloc, and/or displ attr
                    # of the existing `TimeSeries` with the 
                    # current `TimeSeries`.
                    for attr in 'accel','veloc','displ':
                        if hasattr(s,attr):
                            # if the existing `TimeSeries` already
                            # has this attr, warn before replacing.
                            if hasattr(existing_s,attr):
                                if kwds.get('verbosity',0)>=0:
                                    warnings.warn(f"Multiple TimeSeries with the key, attribute {key},{attr} were found for Record {Record}. Preceding TimeSeries will be replaced.")
                            setattr(existing_s,attr,getattr(s,attr))
            # if the channel is not known, the TimeSeries
            # is blindly included.
            else:
                unknown_channel.append(s)
        self.series = list(consolidated.values()).extend(unknown_channel)


    def append(self,series): # TODO: is it bad practice to name this the same as a list's append function?
        """
        Adds a `TimeSeries` or collection of `TimeSeries` into
        the existing collection.
        """
        if isinstance(series,TimeSeries):
            self.series.append(series)
        elif isinstance(series,(list,tuple,set)):
            if not all(isinstance(s,TimeSeries) for s in series):
                raise ValueError("All items in collection must be TimeSeries.")
            self.series.extend(list(series))
        self._consolidate()



class Vector:
    """
    Has `.components`, a dictionary of `'dirn'`:`TimeSeries`
    at a single location.

    `'dirn'` includes: 'hor1', 'hor2', 'vert'.

    By custom, 'hor1' is longitudinal and 'hor2' is transverse
    when such axes exist for the station.

    `components`: dictionary of `'dirn'`:`TimeSeries`
    `.meta`: dictionary-like `MetaData` object
    `for i in Vector` to iterate through `.series`
    """
    def _update_components(f):
        def wrapped(*args, **kwds):
            res = f(*args, **kwds)
            [getattr(cmp,attr)._refresh()
                    for cmp in res.components.values()
                        for attr in ["accel","veloc","displ"] if hasattr(cmp,attr)]
            return res
        return wrapped

    def __init__(self,
                 components:dict=None,
                 meta:dict=None):
        
        self.meta = meta if meta is not None else MetaData(self)

        if (components is not None) and (not isinstance(components,dict)):
            raise TypeError("components must be a dictionary.")

        self.components = components if components is not None else {}
        for comp in self.components.values():
            comp._vector_parent = self

    @property
    def accel(self):
        return np.stack(tuple(c.accel for c in self.components)).T

    @property
    def veloc(self):
        return np.stack(tuple(c.veloc for c in self.components)).T

    @property
    def displ(self):
        return np.stack(tuple(c.displ for c in self.components)).T

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
                x = getattr(self.components["hor1"], attr).data
                y = getattr(self.components["hor2"], attr).data
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
                    for dirn in ("hor1", "hor2", "vert")
                        if  dirn in self.components and 
                            self.components[dirn] is not None
                ))
            except AttributeError as e:
                raise e
        return TimeSeries(*vector_norm.values())




class TimeSeries:
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
        # possible items in meta:
        #   'npts': number of time samples
        #   'time_step': length of time step
        #   'start_time': global time at start of record
        #   'component': direction of motion, e.g. 'vert'
        #   'channel': channel number, e.g. 3
        #   'location': location name, e.g. '4th Floor East'
        #   'floor': floor number
        #   'channel_identifier': network station channel ID,
        #                         e.g. 1103.HN2.NP.4E
        #   'file_name': name of file, e.g 'CHAN001.v2'

        self.accel = accel
        self.veloc = veloc
        self.displ = displ
        
        for data in (self.accel, self.veloc, self.displ):
            if data is not None:
                data = np.asarray(data)
                assert data.ndim == 1
                if self.npts is None:
                    self.npts = len(data)


    def __repr__(self):
        if 'channel' in self.meta.keys():
            return f"TimeSeries({self.meta['channel']}) at {hex(id(self))}"
        elif 'file_name' in self:
            return f"TimeSeries({self.meta['file_name']}) at {hex(id(self))}"
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
    # def __init__(self,**kwds):
    #     dict.__init__(self,**kwds)  # TODO: is this right?

    def __setattr__(self, name, value):
        self[name]  = value
        
    def __getattribute__(self, __name: str):
        if __name in self:
            return self[__name]
        return super().__getattribute__(__name)


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
    # and will be parsed into a `Record`
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



def group_by_location(series):
    """
    A dictionary mapping unique locations to lists of `TimeSeries` objects.

    :param series:     collection of `TimeSeries` objects
    :type series:      iterable collection (list, tuple, set)
    
    :return:           ``motions``
    :rtype:            dictionary
    """    
    if not isinstance(series,(list,tuple,set)):
        raise TypeError("series must be a list, tuple, or set.")
    if not all(isinstance(s,TimeSeries) for s in series):
        raise TypeError("every item in series must be a TimeSeries.")
    
    motions = {}
    for s in series:
        # get the series location
        loc = s.meta.get('location',None)
        # add the series into the corresponding location in motions
        if loc in motions.keys():
            motions[loc].append(s)
        else:
            motions[loc] = [s]
    return motions