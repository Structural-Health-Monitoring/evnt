import warnings

def localize(serieses,**kwds):
    """
    A dictionary mapping unique locations to lists of `TimeSeries` objects.

    :param serieses:     collection of `TimeSeries` objects
    :type serieses:      iterable collection (list, tuple, set)
    
    :return:                    ``motions``
    :rtype:                     dictionary
    """    
    motions = {}
    for series in serieses:
        # get the series location
        try:
            loc = series["location_name"]
        # if the series is not labeled with a location, assign it to "no location found"
        except KeyError:
            if kwds.get('verbosity',0)>=2:
                warnings.warn(f"No location found for series {series}")
            loc = "no location found"
        
        # add the series into the corresponding location in motions
        if loc in motions.keys():
            motions[loc].append(series)
        else:
            motions[loc] = [series]
    return motions
