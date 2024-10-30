"""
.. currentmodule:: evnt
"""

from evnt.core import get_parser
from pathlib import Path

def read(path_to_zipfile, **kwds):
    """
    Get the `EventRecord` or `TimeSeries` from a file.

    :param path_to_zipfile:     path to zipfile with extension .zip
                                or motion file with extension .smc, .v2, etc.
    :type path_to_zipfile:      pathlib Path object, or string.
    
    :return:                    parsed records that are printable (`print`)
                                and summarizable (`.meta`).
    :rtype:                     if zipfile: `EventRecord`object.
                                if motion file: `TimeSeries` object.
    """

    _, parser = get_parser(path_to_zipfile)
    record = parser(path_to_zipfile,**kwds)
    return record
