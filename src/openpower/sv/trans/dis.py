import argparse as _argparse
import enum as _enum
import sys as _sys


class ByteOrder(_enum.Enum):
    LITTLE = "little"
    BIG = "big"

    def __str__(self):
        return self.name.lower()


class Instruction(int):
    def __new__(cls, value, byteorder=ByteOrder.LITTLE):
        if isinstance(value, bytes):
            value = int.from_bytes(value, byteorder=str(byteorder))
        if not isinstance(value, int) or (value < 0):
            raise ValueError(value)
        return super().__new__(cls, value)

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self)})"

    def __str__(self):
        return f".long 0x{self:08x}"

    @property
    def major(self):
        return (((self & ((1 << 32) - 1)) >> 26) & 0x3f)


class PrefixedInstruction(Instruction):
    def __new__(cls, prefix, suffix, byteorder=ByteOrder.LITTLE):
        (prefix, suffix) = map(Instruction, (prefix, suffix))
        return super().__new__(cls, ((prefix << 32) | suffix))

    def __str__(self):
        return f".llong 0x{self:016x}"

    @property
    def prefix(self):
        return Instruction((self >> 32) & ((1 << 32) - 1))

    @property
    def suffix(self):
        return Instruction((self >> 0) & ((1 << 32) - 1))


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
