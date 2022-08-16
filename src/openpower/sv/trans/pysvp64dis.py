import argparse as _argparse
import enum as _enum
import functools as _functools
import sys as _sys

from openpower.decoder.selectable_int import SelectableInt as _SelectableInt
from openpower.decoder.isa.caller import SVP64PrefixFields as _SVP64PrefixFields
from openpower.decoder.isa.caller import SVP64RMFields as _SVP64RMFields

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property


class ByteOrder(_enum.Enum):
    LITTLE = "little"
    BIG = "big"

    def __str__(self):
        return self.name.lower()


class Instruction(_SelectableInt):
    def __init__(self, value, byteorder=ByteOrder.LITTLE):
        if isinstance(value, bytes):
            value = int.from_bytes(value, byteorder=str(byteorder))
        if not isinstance(value, int) or (value < 0) or (value > ((1 << 32) - 1)):
            raise ValueError(value)
        return super().__init__(value=value, bits=32)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value:08x})"

    def __str__(self):
        return f".long 0x{self.value:08x}"


class PrefixedInstruction(_SelectableInt):
    def __init__(self, prefix, suffix, byteorder=ByteOrder.LITTLE):
        insn = _functools.partial(Instruction, byteorder=byteorder)
        (prefix, suffix) = map(insn, (prefix, suffix))
        value = ((prefix.value << 32) | suffix.value)
        return super().__init__(value=value, bits=64)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value:016x})"

    def __str__(self):
        return f".llong 0x{self.value:016x}"

    @property
    def prefix(self):
        return self[0:32]

    @property
    def suffix(self):
        return self[32:64]


class SVP64Instruction(PrefixedInstruction):
    @cached_property
    def prefix(self):
        return _SVP64PrefixFields(super().prefix)

    @cached_property
    def rm(self):
        return _SVP64RMFields(self.prefix.rm)


def load(ifile, byteorder, **_):
    def load(ifile):
        prefix = ifile.read(4)
        length = len(prefix)
        if length == 0:
            return None
        elif length < 4:
            raise IOError(prefix)
        sv_prefix = _SVP64PrefixFields(int.from_bytes(prefix, byteorder=str(byteorder)))
        if sv_prefix.major != 0x1:
            return Instruction(prefix, byteorder)

        suffix = ifile.read(4)
        length = len(suffix)
        if length == 0:
            return prefix
        elif length < 4:
            raise IOError(suffix)
        if sv_prefix.pid == 0b11:
            return SVP64Instruction(prefix, suffix, byteorder)
        else:
            return PrefixedInstruction(prefix, suffix, byteorder)

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
    ifile = args["ifile"]
    ofile = args["ofile"]
    byteorder = args["byteorder"]

    insns = load(ifile, byteorder)
    for line in dump(insns, byteorder):
        print(line, file=ofile)


if __name__ == "__main__":
    main()
