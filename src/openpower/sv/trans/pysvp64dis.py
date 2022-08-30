import argparse as _argparse
import enum as _enum
import sys as _sys

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


def load(ifile, byteorder, **_):
    byteorder = str(byteorder)

    while True:
        prefix = ifile.read(4)
        length = len(prefix)
        if length == 0:
            return
        elif length < 4:
            raise IOError(prefix)
        prefix = _WordInstruction.integer(value=prefix, byteorder=byteorder)

        suffix = ifile.read(4)
        length = len(suffix)
        if length == 0:
            yield prefix
            return
        elif length < 4:
            raise IOError(suffix)
        suffix = _WordInstruction.integer(value=suffix, byteorder=byteorder)

        if prefix.po == 0x1:
            insn = _SVP64Instruction.pair(prefix=prefix, suffix=suffix)
            if insn.prefix.id != 0b11:
                insn = _PrefixedInstruction.pair(prefix=prefix, suffix=suffix)
            yield insn
        else:
            yield prefix
            yield suffix


def dump(insns, **_):
    db = _Database(_find_wiki_dir())
    for insn in insns:
        yield from insn.disassemble(db=db)


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
