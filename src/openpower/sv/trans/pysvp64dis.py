import argparse as _argparse
import enum as _enum
import sys as _sys
import os as _os
from io import BytesIO

from openpower.decoder.power_enums import (
    find_wiki_dir as _find_wiki_dir,
)
from openpower.decoder.power_insn import (
    Verbosity as _Verbosity,
    Database as _Database,
    WordInstruction as _WordInstruction,
    PrefixedInstruction as _PrefixedInstruction,
    SVP64Instruction as _SVP64Instruction,
)


class ByteOrder(_enum.Enum):
    LITTLE = "little"
    BIG = "big"

    def __str__(self):
        return self.name.lower()


def load(ifile, byteorder=ByteOrder.LITTLE, **_):
    byteorder = str(byteorder)

    # copy over to persistent binfile (BytesIO)
    cpfile = BytesIO()
    cpfile.write(ifile.read())
    cpfile.seek(0)

    while True:
        insn = cpfile.read(4)
        length = len(insn)
        if length == 0:
            return
        elif length < 4:
            raise IOError(insn)
        insn = _WordInstruction.integer(value=insn, byteorder=byteorder)
        if insn.po == 0x1:
            suffix = cpfile.read(4)
            length = len(suffix)
            if length == 0:
                yield insn
                return
            elif length < 4:
                raise IOError(suffix)

            prefix = insn
            suffix = _WordInstruction.integer(value=suffix, byteorder=byteorder)
            insn = _SVP64Instruction.pair(prefix=prefix, suffix=suffix)
            if insn.prefix.id != 0b11:
                insn = _PrefixedInstruction.pair(prefix=prefix, suffix=suffix)
        yield insn

    cpfile.seek(0) # restore position so that generator can be reused


def dump(insns, verbosity, **_):
    db = _Database(_find_wiki_dir())
    for insn in insns:
        yield from insn.disassemble(db=db, verbosity=verbosity)


# this is the entry-point for the console-script pysvp64dis
def main():
    parser = _argparse.ArgumentParser()
    parser.add_argument("ifile", nargs="?",
        type=_argparse.FileType("rb"), default=_sys.stdin.buffer)
    parser.add_argument("ofile", nargs="?",
        type=_argparse.FileType("w"), default=_sys.stdout)
    parser.add_argument("-b", "--byteorder",
        type=ByteOrder, default=ByteOrder.LITTLE)
    parser.add_argument("-s", "--short",
        dest="verbosity", default=_Verbosity.NORMAL,
        action="store_const", const=_Verbosity.SHORT)
    parser.add_argument("-v", "--verbose",
        dest="verbosity", default=_Verbosity.NORMAL,
        action="store_const", const=_Verbosity.VERBOSE)
    parser.add_argument("-l", "--log",
        action="store_true", default=False)

    args = dict(vars(parser.parse_args()))

    # if logging requested do not disable it.
    if not args['log']:
        _os.environ['SILENCELOG'] = '1'

    # load instructions and dump them
    insns = load(**args)
    for line in dump(insns, **args):
        print(line, file=args["ofile"])


# still here but use "python3 setup.py develop" then run the
# command "pysvp64dis" instead of "python3 src/openpower/sv/trans/pysvp64dis.py"
if __name__ == "__main__":
    main()
