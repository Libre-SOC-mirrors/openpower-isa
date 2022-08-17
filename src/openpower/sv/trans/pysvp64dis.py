import argparse as _argparse
import enum as _enum
import functools as _functools
import sys as _sys

from openpower.decoder.power_enums import find_wiki_dir as _find_wiki_dir
from openpower.decoder.power_insn import Database as _Database
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


DATABASE = _Database(_find_wiki_dir())


class Instruction(_SelectableInt):
    def __init__(self, value, byteorder=ByteOrder.LITTLE):
        if isinstance(value, _SelectableInt):
            value = value.value
        elif isinstance(value, bytes):
            value = int.from_bytes(value, byteorder=str(byteorder))

        if not isinstance(value, int) or (value < 0) or (value > ((1 << 32) - 1)):
            raise ValueError(value)

        return super().__init__(value=value, bits=32)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value:08x})"

    def __str__(self):
        if not self.dbrecord:
            return f".long 0x{self.value:08x}"
        return f".long 0x{self.value:08x} # {self.dbrecord.name}"

    @property
    def major(self):
        return self[0:6]

    @property
    def dbrecord(self):
        try:
            return DATABASE[int(self)]
        except KeyError:
            return None


class PrefixedInstruction(_SelectableInt):
    def __init__(self, prefix, suffix, byteorder=ByteOrder.LITTLE):
        insn = _functools.partial(Instruction, byteorder=byteorder)
        (prefix, suffix) = map(insn, (prefix, suffix))
        value = ((prefix.value << 32) | suffix.value)
        return super().__init__(value=value, bits=64)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.value:016x})"

    def __str__(self):
        if self.dbrecord is None:
            return f".llong 0x{self.value:016x}"
        return f".llong 0x{self.value:016x} # {self.dbrecord.name}"

    @cached_property
    def prefix(self):
        return Instruction(self[0:32])

    @cached_property
    def suffix(self):
        return Instruction(self[32:64])

    @cached_property
    def dbrecord(self):
        return self.suffix.dbrecord


class SVP64Instruction(PrefixedInstruction):
    class PrefixError(ValueError):
        pass

    class Prefix(_SVP64PrefixFields, Instruction):
        class RM(_SVP64RMFields):
            @cached_property
            def sv_mode(self):
                return (self.mode & 0b11)

        @cached_property
        def rm(self):
            return self.__class__.RM(super().rm)

    class Suffix(Instruction):
        pass

    def __init__(self, prefix, suffix, byteorder=ByteOrder.LITTLE):
        if SVP64Instruction.Prefix(prefix).pid != 0b11:
            raise SVP64Instruction.PrefixError(prefix)
        return super().__init__(prefix, suffix, byteorder)

    def __str__(self):
        if self.dbrecord is None:
            return f".llong 0x{self.value:016x}"
        return f".llong 0x{self.value:016x} # sv.{self.dbrecord.name}"

    @cached_property
    def prefix(self):
        return self.__class__.Prefix(super().prefix)

    @cached_property
    def suffix(self):
        return self.__class__.Suffix(super().suffix)


def load(ifile, byteorder, **_):
    def load(ifile):
        prefix = ifile.read(4)
        length = len(prefix)
        if length == 0:
            return None
        elif length < 4:
            raise IOError(prefix)
        prefix = Instruction(prefix, byteorder)
        if prefix.major != 0x1:
            return Instruction(prefix, byteorder)

        suffix = ifile.read(4)
        length = len(suffix)
        if length == 0:
            return prefix
        elif length < 4:
            raise IOError(suffix)
        try:
            return SVP64Instruction(prefix, suffix, byteorder)
        except SVP64Instruction.PrefixError:
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
