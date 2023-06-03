import argparse
import enum
import sys
import os

from openpower.decoder.power_enums import (
    find_wiki_dir,
)
from openpower.insndb.dbtypes import (
    Style,
    Database,
    WordInstruction,
    PrefixedInstruction,
    SVP64Instruction,
)


class ByteOrder(enum.Enum):
    LITTLE = "little"
    BIG = "big"

    def __str__(self):
        return self.name.lower()


def load(ifile, byteorder=ByteOrder.LITTLE, **_):
    byteorder = str(byteorder)

    while True:
        insn = ifile.read(4)
        length = len(insn)
        if length == 0:
            return
        elif length < 4:
            raise IOError(insn)
        insn = WordInstruction.integer(value=insn, byteorder=byteorder)
        if insn.PO == 0x1:
            suffix = ifile.read(4)
            length = len(suffix)
            if length == 0:
                yield insn
                return
            elif length < 4:
                raise IOError(suffix)

            prefix = insn
            suffix = WordInstruction.integer(value=suffix, byteorder=byteorder)
            insn = SVP64Instruction.pair(prefix=prefix, suffix=suffix)
            if insn.prefix.id != 0b11:
                insn = PrefixedInstruction.pair(prefix=prefix, suffix=suffix)
        yield insn


def dump(insns, style, **_):
    db = Database(find_wiki_dir())
    for insn in insns:
        record = db[insn]
        yield from insn.disassemble(record=record, style=style)


# this is the entry-point for the console-script pysvp64dis
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ifile", nargs="?",
        type=argparse.FileType("rb"), default=sys.stdin.buffer)
    parser.add_argument("ofile", nargs="?",
        type=argparse.FileType("w"), default=sys.stdout)
    parser.add_argument("-b", "--byteorder",
        type=ByteOrder, default=ByteOrder.LITTLE)
    parser.add_argument("-s", "--short",
        dest="style", default=Style.NORMAL,
        action="store_const", const=Style.SHORT)
    parser.add_argument("-v", "--verbose",
        dest="style", default=Style.NORMAL,
        action="store_const", const=Style.VERBOSE)
    parser.add_argument("-l", "--legacy",
        dest="style", default=Style.NORMAL,
        action="store_const", const=Style.LEGACY)
    parser.add_argument("-L", "--log",
        action="store_true", default=False)

    args = dict(vars(parser.parse_args()))

    # if logging requested do not disable it.
    if not args['log']:
        os.environ['SILENCELOG'] = '1'

    # load instructions and dump them
    insns = load(**args)
    for line in dump(insns, **args):
        print(line, file=args["ofile"])


# still here but use "python3 setup.py develop" then run the
# command "pysvp64dis" instead of "python3 src/openpower/sv/trans/pysvp64dis.py"
if __name__ == "__main__":
    main()
