import argparse as _argparse
import enum as _enum
import functools as _functools
import sys as _sys

from openpower.decoder.selectable_int import SelectableInt as _SelectableInt


class ByteOrder(_enum.Enum):
    LITTLE = "little"
    BIG = "big"

    def __str__(self):
        return self.name.lower()


class Instruction(_SelectableInt):
    def __init__(self, value, bits=32, byteorder=ByteOrder.LITTLE):
        if isinstance(value, bytes):
            value = int.from_bytes(value, byteorder=str(byteorder))
        if not isinstance(value, (int, _SelectableInt)) or (value < 0):
            raise ValueError(value)
        return super().__init__(value=value, bits=bits)

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self)})"

    def __str__(self):
        return f".long 0x{self.value:08x}"

    @property
    def major(self):
        return self[0:6]


class PrefixedInstruction(Instruction):
    def __init__(self, prefix, suffix, byteorder=ByteOrder.LITTLE):
        insn = _functools.partial(Instruction, bits=64)
        (prefix, suffix) = map(insn, (prefix, suffix))
        value = ((prefix.value << 32) | suffix.value)
        return super().__init__(value=value, bits=64)

    def __str__(self):
        return f".llong 0x{self.value:016x}"

    @property
    def prefix(self):
        return self[0:32]

    @property
    def suffix(self):
        return self[32:64]


def load(ifile, byteorder, **_):
    def load(ifile):
        prefix = ifile.read(4)
        length = len(prefix)
        if length == 0:
            return None
        elif length < 4:
            raise IOError(prefix)
        prefix = Instruction(prefix, byteorder=byteorder)
        if prefix.major != 0x1:
            return prefix

        suffix = ifile.read(4)
        length = len(suffix)
        if length == 0:
            return prefix
        elif length < 4:
            raise IOError(suffix)

        return PrefixedInstruction(prefix, suffix, byteorder=byteorder)

    while True:
        insn = load(ifile)
        if insn is None:
            break
        yield insn


def dump(insns, ofile, **_):
    for insn in insns:
        yield str(insn)


def main():
    parser = _argparse.ArgumentParser()
    parser.add_argument("ifile", nargs="?",
        type=_argparse.FileType("rb"), default=_sys.stdin.buffer)
    parser.add_argument("ofile", nargs="?",
        type=_argparse.FileType("w"), default=_sys.stdout)
    parser.add_argument("-b", "--byteorder",
        type=ByteOrder, default=ByteOrder.LITTLE)
    args = dict(vars(parser.parse_args()))

    insns = load(**args)
    for line in dump(insns, **args):
        print(line)


if __name__ == "__main__":
    main()
