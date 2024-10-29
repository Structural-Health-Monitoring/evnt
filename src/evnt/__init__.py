"""
.. currentmodule:: evnt
"""

from evnt.core import get_parser
from pathlib import Path
from evnt.core import EventRecord, TimeSeries

def read(path_to_zipfile, **kwds) -> EventRecord:
    """
    Get the parsed ``record`` from a zip file of event records.

    :param path_to_zipfile:     path to zipfile.
    :type path_to_zipfile:      pathlib Path object, or string.
    
    :return:                    parsed records that are printable (`print`)
                                and summarizable (`.stats`).
    :rtype:                     `evnt` EventRecord object.
    """

    _, parser = get_parser(path_to_zipfile)
    record = parser(path_to_zipfile,**kwds)
    return record


def read_series(path_to_file, **kwds) -> TimeSeries:
    """
    Get the parsed ``series`` from a series file.

    :param path_to_file:     path to file.
    :type path_to_file:      pathlib Path object, or string.
    
    :return:                 parsed series that is printable (`print`)
                             and summarizable (`.stats`).
    :rtype:                  `evnt` TimeSeries object.
    """

    _, parser = get_parser(path_to_file)
    series = parser(path_to_file,**kwds)
    return series