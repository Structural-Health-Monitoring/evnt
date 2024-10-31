"""
.. currentmodule:: evnt
"""

from evnt.core import get_parser

def read(path_to_file, **kwds):
    """
    Get the `Record` or `TimeSeries` from a file.

    :param path_to_file:        path to zipfile with extension .zip
                                or motion file with extension .smc, .v2, etc.
    :type path_to_file:         pathlib Path object, or string.
    
    :return:                    parsed records that are printable (`print`)
                                and summarizable (`.meta`).
    :rtype:                     if zipfile: `Record`object.
                                if motion file: `TimeSeries` object.
    """

    _, parser = get_parser(path_to_file)
    record = parser(path_to_file,**kwds)
    return record
