import argparse as _argparse
import enum as _enum
import sys as _sys
import os

from openpower.decoder.power_enums import (
    find_wiki_dir as _find_wiki_dir,
)
from openpower.decoder.power_insn import (
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
    curpos = ifile.tell() # get file position

    while True:
        insn = ifile.read(4)
        length = len(insn)
        if length == 0:
            return
        elif length < 4:
            raise IOError(insn)
        insn = _WordInstruction.integer(value=insn, byteorder=byteorder)
        if insn.po == 0x1:
            suffix = ifile.read(4)
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

    ifile.seek(curpos) # restore position so that generator can be reused


def dump(insns, verbose, short=False, **_):
    db = _Database(_find_wiki_dir())
    for insn in insns:
        yield from insn.disassemble(db=db, verbose=verbose, short=short)


# this is the entry-point for the console-script pysvp64dis
def main():
    parser = _argparse.ArgumentParser()
    parser.add_argument("ifile", nargs="?",
        type=_argparse.FileType("rb"), default=_sys.stdin.buffer)
    parser.add_argument("ofile", nargs="?",
        type=_argparse.FileType("w"), default=_sys.stdout)
    parser.add_argument("-b", "--byteorder",
        type=ByteOrder, default=ByteOrder.LITTLE)
    parser.add_argument("-v", "--verbose",
        action="store_true", default=False)
    parser.add_argument("-s", "--short",
        action="store_true", default=False)
    parser.add_argument("-l", "--log",
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
