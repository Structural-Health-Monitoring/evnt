# Claudio Perez
# Summer 2021
# Continued by Chrystal Chern
# Fall 2024
"""
Parse a CSMIP V2C strong motion data file.
"""
import re
import sys
import fnmatch
import zipfile
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import numpy as np

from quakeio.core import (
    QuakeCollection,
    QuakeMotion,
    QuakeComponent,
    QuakeSeries,
)

from quakeio.utils.parseutils import (
    parse_sequential_fields,
    open_quake,
    RE_DECIMAL,  # Regular expression for extracting decimal values
    RE_UNITS,    # Regular expression for extracting units
    CRE_WHITE,
    maybe_t,
)

re_digits = re.compile(r"([0-9]+)")

# Module constants
NUM_COLUMNS = 8
HEADER_END_LINE = 45

INTEGER_HEADER_START_LINE = 25
INTEGER_HEADER_END_LINE = 25+7
REAL_HEADER_END_LINE = 45

DATEFMT = "%m/%d/%y, %H:%M" #:%S.%f %Z"

# A utility to convert general strings into
# appropriate keys.
_make_key = lambda strng: strng.strip().replace(" ", "_").lower()

# Definition of some type constructors, used to coerce
# the result of a regex match.
words  = lambda x: CRE_WHITE.sub(" ", str(x)).strip()
units  = lambda x: str(x).strip().lower()

class FindDate:
    pat1  = re.compile(r"([A-z]* of )? ([A-z]{,5} [A-z]{,5} [0-9]{,2}, [0-9]{4} [0-9]{2}:[0-9]{2}:"+RE_DECIMAL+" [A-Z]{,4})")
    def findall(self, line):
        if line[0].upper() == "R":
            return FindDate.pat1.findall(line)
        else:
            print(line)
            match = FindDate.pat2.findall(line)
            print(match)
            return (["", *match[0]],)

# PARSE TABLE
# ----------------------------------------------------------------
# The parse table defines all of the fields than can be extracted
# from a CSMIP file, and maps these fields to (1) a data type and 
# (2) regular expression. This table has the following structure:
#
#   Dict[
#     Tuple[*[Key]],
#     Tuple[ Tuple[*[Type]], RegExp]
#   ]
#
# leading key (ie key.split(".")[0]) determines whether
# field is part of record or accel/veloc/displ series.
# fmt: off
HEADER_FIELDS = {
    # line 1
    ("_", "record.record_identifier"): ((str, str),
        re.compile(r"([A-z ]*) ([A-z0-9\-\.]*)", re.IGNORECASE)
    ),
    # line 5
    ("_", "record.date"): ((str,lambda s: datetime.strptime(s.strip(),DATEFMT).isoformat(),),
        #(5,
            re.compile(r"(.*): *([0-9]{,2}/[0-9]{,2}/[0-9]{,4}, *[0-9]{2}:[0-9]{2})")#[:.0-9]{,4} [A-Z]{,4})")
        #)
    ),
    # line 6
    ("record.station.no", "record.station.coord"): ((str, str),
        re.compile(
            rf"Station No\. *([0-9]*) *({RE_DECIMAL}[NSEW]*, *{RE_DECIMAL}[NSEW]*)",
            re.IGNORECASE
        )
    ),
    # line 7
    ("record.station_name",): ((words, ),
        ( 7,  (slice(40), ) )
    #("record.station_name", "_"): ((str, str),
            #re.compile("(.*) *(CGS)", re.IGNORECASE) 
        # )
    ),
    # line 8
    ("record.channel", "record.component", "_", "record.station_channel", "record.location_name"): (
    # ("record.channel", "record.component", "_", "_", "record.location_name"): (
        (str, str, maybe_t("(DegR*)",str), maybe_t("Sta Chn: ([0-9]*)", words), words),
        re.compile(# (  1   )   (---------)  (---)   (--)             (------)
            rf"Chan *([0-9]*): *([A-z0-9]*) *(DegR*)? *(.*) *Location: *([ -~]*)\s",
            re.IGNORECASE
        )
    ),
    # line 11
    ("record.instr_period", ".units"): ((float, units),
        re.compile(
            rf"Instr Period *= *({RE_DECIMAL}) *({RE_UNITS}),",
            re.IGNORECASE
        )
    ),
    #    # line 15
    #    (
    #        "filter.bandpass.point",
    #        "filter.bandpass.point.units",
    #        "filter.bandpass.limit_low",
    #        "filter.bandpass.limit_high",
    #        "filter.bandpass.limit.units"
    #    ) : (
    #        (float, units, float, float, units),
    #        re.compile(
    #            rf"Accelerogram bandpass filtered with *({RE_DECIMAL}) *({RE_UNITS}) pts at *({RE_DECIMAL}) and *({RE_DECIMAL}) *({RE_UNITS})\s",
    #            re.IGNORECASE
    #        )
    #    ),
    ("accel.peak_value", "accel.units", "accel.peak_time"): ((float, units, float),
        re.compile(
            rf"Peak *acceleration *= *({RE_DECIMAL}) *({RE_UNITS}) *at *({RE_DECIMAL})",
            re.IGNORECASE
        )
    ),
    ("veloc.peak_value", "veloc.units", "veloc.peak_time"): ((float, units, float),
        re.compile(
            rf"Peak *velocity *= *({RE_DECIMAL}) *({RE_UNITS}) *at *({RE_DECIMAL})",
            re.IGNORECASE
        )
    ),
    ("displ.peak_value", "displ.units", "displ.peak_time"): ((float, units, float),
        re.compile(
            rf"Peak *displacement *= *({RE_DECIMAL}) *({RE_UNITS}) *at *({RE_DECIMAL})",
            re.IGNORECASE
        )
    ),
    ("record.init_veloc", ".units", "record.init_displ", ".units"): ((float, units, float, units),
        re.compile(
            rf"Initial velocity *= *({RE_DECIMAL}) *({RE_UNITS}); *Initial displacement *= *({RE_DECIMAL}) *({RE_UNITS})\s",
            re.IGNORECASE
        )
    ),
    ("accel.shape", "accel.time_step"): ((int, float),
        re.compile(f"([0-9]*) *points of accel data equally spaced at *({RE_DECIMAL})", re.IGNORECASE)
    ),
    ("veloc.shape", "veloc.time_step"): ((int, float),
        re.compile(f"([0-9]*) *points of veloc data equally spaced at *({RE_DECIMAL})", re.IGNORECASE)
    ),
    ("displ.shape", "displ.time_step"): ((int, float),
        re.compile(f"([0-9]*) *points of displ data equally spaced at *({RE_DECIMAL})", re.IGNORECASE)
    ),
}
# fmt: on

V1_HEADER_FIELDS = HEADER_FIELDS.copy()
V1_HEADER_FIELDS.update({
    ("record.station_name",): ((words, ),
        ( 6,  (slice(40),) )
    )
})

def read_event(read_file, verbosity=0, summarize=False, **kwds):
    """
    Take the name of a CSMIP zip file and extract record data for the event.

    - kwds are passed to read_motion_v2
    """

    components = []
    zippath    = Path(read_file)
    archive    = zipfile.ZipFile(zippath)
    motions    = defaultdict(QuakeMotion)

    v1 = False

    # Loop over V1 and V2 files in the zipped archive
    for file in archive.namelist():
        # Disregard any files that are not V1 or V2
        if not file.endswith((".v2", ".V2", ".v1", ".V1")):
            continue

        # Optional info logging
        if verbosity > 2: print(f"\t\t{file}", file=sys.stderr)

        v1 = True if file.endswith((".v1", ".V1")) else False

        cmp = read_record_v2(file, archive, verbosity=verbosity, summarize=summarize, v1=v1, **kwds)
        loc = _make_key(cmp.get("location_name", str(file)))
        drn = _make_key(cmp.get("component", "NA"))

        # Check that a Component with this direction has not already been
        # added to the Motion container under this location. This should
        # not happen, but is checked for robustness.
        if drn in motions[loc].components:
            loc += "_alt"

        motions[loc]["key"] = loc
        motions[loc].components[drn] = cmp


    # EVENT-LEVEL METADATA
    # Compute peak values over the entire archive.
    # --------------------------------------------
    # V1 files may not give peak values for the individual files (components), 
    # so in this case they are computed manually.
    if v1 and not summarize:
        peak_accel = max(
            (max(c.accel.data, key=abs) for m in motions.values() for c in m.components.values()),
            key=abs
        )

    # Otherwise, just take the peaks from the parsed metadata.
    else:
        peak_accel = max(
            (c.accel.get("peak_value", 0.0) for m in motions.values() for c in m.components.values()),
            key=abs
        )

    # Collect someother information from the first file (component)
    first_motion    = list(motions.values())[0]
    first_component = list(first_motion.components.values())[0]

    date = first_component.get("date", "NA")
    metadata = {
        "file_name": str(read_file),
        "peak_accel": peak_accel,
        "event_date": date,
        "station_name":      first_component.get("station_name", "NA"),
        "station_coord":     first_component.get("station.coord", "NA"),
        "record_identifier": first_component.get("record_identifier", "NA"),
        "station_number":    first_component.get("station.no", "NA")
    }
    return QuakeCollection(dict(motions), event_date=date, meta=metadata)


# Fields that are not provided in the V1 format.
V1_EXCLUDE = ("filter*", "*peak*", "*init*", "*disp*", "*velo*")


def read_record_v2(
    read_file,
    archive: zipfile.ZipFile = None,
    verbosity: int  = 0,
    summarize: bool =False,
    v1: bool = False,
    exclusions: tuple = (),
    **kwds
) -> QuakeComponent:
    """
    Read a ground motion record using the CSMIP Volume 2 format
    """
    if v1:
        exclusions = V1_EXCLUDE
        FIELDS = V1_HEADER_FIELDS
    else:
        FIELDS = HEADER_FIELDS

    filename = Path(read_file)

    # 1. PARSE READABLE HEADER (Regular expressions)
    # Collect keys to exclude
    keys = []
    for x in exclusions:
        for k in FIELDS:
            if any(fnmatch.fnmatch(kk,x) for kk in k):
                keys.append(k)

    header_fields = {k: v for k,v in FIELDS.items() if k not in keys}

    # Parse header fields
    try:
        with open_quake(read_file, "r", archive) as f:
            header_data = parse_sequential_fields(f, header_fields, verbose=verbosity)
        header_data.pop("_")
    except:
        if verbosity:
            print("Failed to parse header data for file {filename.name}", file=sys.stderr)
        header_data = {}


    # 2. PARSE NUMERIC HEADERS
    # Reopen and parse out data; Note, only the first call
    # provides a skip_header argument as successive reads
    # pick up where the previous left off.
    with open_quake(read_file, "r", archive) as f:
        # 50 integer values spanning 7 lines between lines 26-32
        int_header = np.genfromtxt(
            f,
            dtype=int,
            skip_header=13 if v1 else 25,
            max_rows=6,
            delimiter=5,
            ).flatten()
        int_header = np.append(int_header , np.genfromtxt(
            f,
            dtype=int,
            max_rows=1,
            delimiter=5,
            ).flatten()
        )
        assert len(int_header) == 100, int_header[:5]

        # 100 floating point values on lines 33-45
        real_header = np.genfromtxt(
            f,
            max_rows= 27-21 if v1 else 45-33,
            delimiter=10,
        ).flatten()
        real_header = np.append(real_header , np.genfromtxt(
            f,
            max_rows=1,
            delimiter=10,
            ).flatten()
        )

        assert len(real_header) == (50 if v1 else 100)

        # Clean and process numeric header data, setup for parse stage 3.
        num_header = _process_numeric_headers_v2(int_header, real_header, header_data)
        # extract information about shape of data
        s = next(f)
        s = s if isinstance(s, str) else s.decode("utf-8")
        len_accel = int(re.match("^ *([0-9]*) *.*", s).group(1))
        # extract format specifier, eg "(8f9.6)" if provided
        data_fmt = re.match(r"\(8f(.*)\)", s)
        if data_fmt:
            field_width = int(data_fmt.group(1).split(".")[0])
        else:
            field_width = 9 if v1 else 10

        parse_options = dict(
            delimiter = field_width,  # fields are 10 chars wide
            dtype=float,
        )

        # 3. PARSE OUT SENSOR DATA
        # Note that successive file reads will begin where we left off
        if not summarize:
            accel = np.genfromtxt(
                f,
                # skip_header=HEADER_END_LINE + 1,
                max_rows=np.ceil(len_accel/NUM_COLUMNS) - 1,
                **parse_options,
            ).flatten()
            accel = np.append(accel, np.genfromtxt(f,max_rows=1,**parse_options))
            if not v1:
                s = next(f)
                s = s if isinstance(s, str) else s.decode("utf-8")
                len_veloc = int(re.match("^ *([0-9]*)", s).group(0))
                veloc = np.genfromtxt(
                    f, max_rows=np.ceil(len_veloc/NUM_COLUMNS)-1, **parse_options
                ).flatten()
                veloc = np.append(veloc, np.genfromtxt(f,max_rows=1,**parse_options))

                s = next(f)
                s = s if isinstance(s, str) else s.decode("utf-8")
                len_displ = int(re.match("^ *([0-9]*)", s).group(0))
                displ = np.genfromtxt(
                    f, max_rows=np.ceil(len_displ/NUM_COLUMNS)-1, **parse_options
                ).flatten()
                displ = np.append(displ, np.genfromtxt(f,max_rows=1,**parse_options))
            else:
                veloc, displ = [], []
        else:
            accel, veloc, displ = [], [], []



    # Treat metadata
    try:
        filter_data = {
            key[16:]: header_data.pop(key)
            for key in [
              "filter.bandpass.point",
              "filter.bandpass.point.units",
              "filter.bandpass.limit_low",
              "filter.bandpass.limit_high",
              "filter.bandpass.limit.units"
            ]
        }
    except:
        filter_data = {}

    record_data = {"filters": [{"filter_type": "bandpass",**filter_data}]}
    series_data = defaultdict(dict)

    for key, val in header_data.items():
        typ, k = key.split(".", 1)
        if typ == "record":
            record_data.update({k: val})
        elif typ in ["accel", "veloc", "displ"]:
            series_data[typ].update({k: val})

    record_data["file_name"] = filename.name

    if "station_channel" not in record_data or not record_data["station_channel"]:
        record_data["station_channel"] = str(int(re_digits.search(filename.name.split(".")[0]).group(0)))

    try:
        record_data.update({
            "peak_displ": series_data["displ"]["peak_value"],
            "peak_veloc": series_data["veloc"]["peak_value"],
            "peak_accel": series_data["accel"]["peak_value"]
        })
    except:
        pass

    # The raw numeric header data hasnt been too useful
    # record_data["ihdr"] = list(int_header)
    # record_data["rhdr"] = list(real_header)
    return QuakeComponent(
        QuakeSeries(accel, meta=series_data["accel"]),
        QuakeSeries(veloc, meta=series_data["veloc"]),
        QuakeSeries(displ, meta=series_data["displ"]),
        meta=record_data,
    )

def _process_numeric_headers_v2(ihdr, rhdr, txthdr):
    data = {}
    ref_azimuth = ihdr[32 -1]
    rel_orientation = ihdr[27 -1]
    #assert txthdr["veloc.shape"] == ihdr[64 - 1]
    #txthdr["record.earthquake_name"] = txthdr["record.earthquake_name"][:ihdr[29 - 1]+1]

    #assert ihdr[51 -1] == ihdr[52-1]
    #assert ihdr[28 -1] == ihdr[51-1]


# Declare file types handled by this module
FILE_TYPES = {
    "csmip.v1":  {"type": QuakeComponent,  "read": read_record_v2},
    "csmip.v2":  {"type": QuakeComponent,  "read": read_record_v2},
    "csmip.v3":  {"type": QuakeComponent,  "read": read_record_v2, "spec": ""},
    "csmip.zip": {"type": QuakeCollection, "read": read_event},
}


def read_record(read_file, *args):
    file = Path(read_file)
    if file.suffix.lower() == ".v2":
        return read_record_v2(file)

def read(read_file, input_format=None):
    pass

