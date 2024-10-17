# gets called when running evnt from the command line:
#    python -m evnt ...
#

import evnt
import sys

HELP = """
python -m evnt <path to zip>
python -m evnt -p <path to zip>
python -m evnt --path <path to zip>
"""


def parse_args(args):
    filepath = None
    argi = iter(args[1:])
    for arg in argi:
        if arg in ["-p", "--path"]:
            filepath = next(argi)
        elif filepath is None:
            filepath = arg
        else:
            print(HELP)
            sys.exit()
    return


def main():
    parse_args(sys.argv)


if __name__ == "__main__":
    main()
    sys.exit()

