import argparse as _argparse
import enum as _enum
import functools as _functools
import sys as _sys

from openpower.decoder.power_enums import (
    find_wiki_dir as _find_wiki_dir,
)
from openpower.decoder.power_insn import (
    Database as _Database,
    Instruction as _Instruction,
    PrefixedInstruction as _PrefixedInstruction,
    SVP64Instruction as _SVP64Instruction,
)


class ByteOrder(_enum.Enum):
    LITTLE = "little"
    BIG = "big"

    def __str__(self):
        return self.name.lower()


def load(ifile, byteorder, **_):
    db = _Database(_find_wiki_dir())

    def load(ifile):
        prefix = ifile.read(4)
        length = len(prefix)
        if length == 0:
            return None
        elif length < 4:
            raise IOError(prefix)
        prefix = _Instruction(value=prefix, byteorder=byteorder, db=db)
        if prefix.major != 0x1:
            return prefix

        suffix = ifile.read(4)
        length = len(suffix)
        if length == 0:
            return prefix
        elif length < 4:
            raise IOError(suffix)
        try:
            return _SVP64Instruction(prefix=prefix, suffix=suffix,
                byteorder=byteorder, db=db)
        except _SVP64Instruction.PrefixError:
            return _PrefixedInstruction(prefix=prefix, suffix=suffix,
                byteorder=byteorder, db=db)

    while True:
        insn = load(ifile)
        if insn is None:
            break
        yield insn


def dump(insns, **_):
    for insn in insns:
        yield from insn.disassemble()


def main():
    parser = _argparse.ArgumentParser()
    parser.add_argument("ifile", nargs="?",
        type=_argparse.FileType("rb"), default=_sys.stdin.buffer)
    parser.add_argument("ofile", nargs="?",
        type=_argparse.FileType("w"), default=_sys.stdout)
    parser.add_argument("-b", "--byteorder",
        type=ByteOrder, default=ByteOrder.LITTLE)

    args = dict(vars(parser.parse_args()))
    ifile = args["ifile"]
    ofile = args["ofile"]
    byteorder = args["byteorder"]

    insns = load(ifile, byteorder)
    for line in dump(insns):
        print(line, file=ofile)


if __name__ == "__main__":
    main()
