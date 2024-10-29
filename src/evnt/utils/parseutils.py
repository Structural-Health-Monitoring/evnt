import re
import io
from os import PathLike
from pathlib import Path
from typing import Union, IO, Callable
import contextlib

# Regular expression for extracting decimal number
RE_DECIMAL = "[-]?[0-9]*[.]?[0-9]*"
# Regular expression for extracting units
RE_UNITS = "[A-z,/,0-9]*"

CRE_WHITE = re.compile("\\W+")


def maybe_t(pattern: str, typ: Callable, strict: bool = True):
    cpattern = re.compile(pattern, re.IGNORECASE)
    def proc(match):
        if match:
            return typ(re.search(cpattern, match).group(1))
        else:
            return None

    return proc


@contextlib.contextmanager
def open_quake(file, mode=None, archive=None):
    import sys

    if file == "-":
        if mode is None or mode == "" or "r" in mode:
            fh = sys.stdin
        else:
            fh = sys.stdout

    elif not archive and isinstance(file, (PathLike, str)):
        fh = open(file, mode)
    elif archive:
        fh = archive.open(file, mode)
    else:
        fh = file
    # if file != "-":
    #     yield fh
    #     fh.close()
    try:
        yield fh

    finally:
        if isinstance(file, str) and file != "-":
            fh.close()


def parse_sequential_fields(data, field_spec: dict, parsed_fields={}, verbose=False) -> dict:
    field_iterator = iter(field_spec.items())
    fields, (typs, pat) = next(field_iterator)
    #print(f"\tfields: {fields}")
    for ln, line in enumerate(data):
        #if not ln % 100: print(f"\t\tline: {ln}")
        if hasattr(pat, "findall"):
            match = pat.findall(str(line))
            if match:
                prefix = ""
                assert len(fields) == len(typs) == len(match[0]), (pat, match[0])
                for field, typ, val in zip(fields, typs, match[0]):
                    if field[0] == ".":
                        key = prefix + field
                    else:
                        prefix = field
                        key = field

                    parsed_fields[key] = typ(val)
                try:
                    fields, (typs, pat) = next(field_iterator)
                    #print(f"\tfields: {fields}")
                except StopIteration:
                    # All fields have been parsed out
                    break
            else:
                pass
        else:
            lnum, line_pat = pat
            lnum -= 1
            assert ln <= lnum
            if ln < lnum: continue

            prefix = ""
            line_str = str(line)
            if isinstance(line_pat, tuple):
                match = ( [line_str[s] for s in line_pat] , )
            else:
                match = line_pat.findall(line_str)
                #assert len(fields) == len(typs) == len(match[0]), (line_pat, match[0])
            if match:
                for field, typ, val in zip(fields, typs, match[0]):
                    if field[0] == ".":
                        key = prefix + field
                    else:
                        prefix = field
                        key = field
                    parsed_fields[key] = typ(val)
            fields, (typs, pat) = next(field_iterator)

    if verbose:
        print(fields)

    return parsed_fields


def get_file_type(
    file: Union[str, Path, IO], file_type: str, module: str = None
) -> str:
    if isinstance(file, io.IOBase):
        return file_type
