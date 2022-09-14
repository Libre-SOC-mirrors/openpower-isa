import argparse as _argparse
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools


from openpower.decoder.power_enums import (
    FPTRANS_INSNS as _FPTRANS_INSNS,
    find_wiki_dir as _find_wiki_dir,
)
from openpower.decoder.power_insn import (
    Database as _Database,
    StaticOperand as _StaticOperand,
    WordInstruction as _WordInstruction,
)


@_dataclasses.dataclass(eq=True, frozen=True)
class StaticOperand:
    name: str
    value: int
    span: tuple


@_dataclasses.dataclass(eq=True, frozen=True)
class DynamicOperand:
    name: str
    span: tuple


@_functools.total_ordering
@_dataclasses.dataclass(eq=True, frozen=True)
class Entry:
    name: str
    static_operands: tuple
    dynamic_operands: tuple

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return ((self.PO, self.XO, self.Rc) <
            (other.PO, other.XO, other.Rc))

    @property
    def PO(self):
        for operand in self.static_operands:
            if operand.name == "PO":
                return operand.value
        raise ValueError(self)

    @property
    def XO(self):
        for operand in self.static_operands:
            if operand.name == "XO":
                return operand.value
        raise ValueError(self)

    @property
    def Rc(self):
        for operand in self.static_operands:
            if operand.name == "Rc":
                return operand.value
        raise ValueError(self)


def collect(db):
    fptrans = tuple(_FPTRANS_INSNS)
    fptrans_Rc = tuple(map(lambda name: f"{name}.", fptrans))

    def fptrans_match(insn):
        return ((insn.name in fptrans) or (insn.name in fptrans_Rc))

    for record in filter(fptrans_match, db):
        if len(record.opcodes) > 1:
            raise NotImplementedError(record.opcodes)
        PO = record.section.opcode
        if PO is None:
            PO = tuple(record.ppc)[0].opcode
            XO = None
        else:
            XO = tuple(record.ppc)[0].opcode

        @_dataclasses.dataclass(eq=True, frozen=True)
        class POStaticOperand(_StaticOperand):
            def __init__(self, PO):
                value = (PO.value & PO.mask)
                return super().__init__(name="PO", value=value)

            def span(self, record):
                return tuple(range(0, 6))

        @_dataclasses.dataclass(eq=True, frozen=True)
        class XOStaticOperand(_StaticOperand):
            def __init__(self, XO):
                value = (XO.value & XO.mask)
                return super().__init__(name="XO", value=value)

            def span(self, record):
                return tuple(record.section.bitsel)

        static_operands = [POStaticOperand(PO=PO)]
        if XO is not None:
            static_operands.append(XOStaticOperand(XO=XO))
        static_operands.extend(record.mdwn.operands.static)
        dynamic_operands = record.mdwn.operands.dynamic

        def static_operand(operand):
            return StaticOperand(name=operand.name,
                value=operand.value, span=operand.span(record=record))

        def dynamic_operand(operand):
            return DynamicOperand(name=operand.name,
                span=operand.span(record=record))

        static_operands = tuple(map(static_operand, static_operands))
        dynamic_operands = tuple(map(dynamic_operand, dynamic_operands))

        yield Entry(name=record.name,
            static_operands=static_operands,
            dynamic_operands=dynamic_operands)


def opcodes(entry):
    operands = entry.dynamic_operands
    operands = ", ".join(operand.name for operand in operands)
    string = ",\t".join((
        f"\"{entry.name}\"",
        f"XRC({entry.PO},{entry.XO},{entry.Rc})",
        "X_MASK",
        "SVP64",
        "PPCVLE",
        f"{{{operands}}}",
    ))
    return f"{{{string}}},"


def asm(entry, regex=False):
    operands = tuple(entry.dynamic_operands)
    for (idx, operand) in enumerate(operands):
        values = []
        for each in operands:
            if each.name in ("FRT", "FRA", "FRB"):
                values.append("f0")
            elif each.name in ("RB"):
                values.append("r0")
            else:
                values.append("0")
        value = str((1 << len(operand.span)) - 1)
        if operand.name in ("FRT", "FRA", "FRB"):
            value = f"f{value}"
        elif operand.name in ("RB"):
            value = f"r{value}"
        values[idx] = value
        return f"{entry.name} {'+' if regex else ''}{','.join(values)}"


def dis(entry):
    def objdump(byte):
        return f"{byte:02x}"

    for dynamic_operand in entry.dynamic_operands:
        insn = _WordInstruction.integer(value=0)
        for static_operand in entry.static_operands:
            span = static_operand.span
            insn[span] = static_operand.value
        span = dynamic_operand.span
        insn[span] = ((1 << len(span)) - 1)
        big = " ".join(map(objdump, insn.bytes(byteorder="big")))
        little = " ".join(map(objdump, insn.bytes(byteorder="little")))
        return f".*:\t({big}|{little}) \t{asm(entry, regex=True)}"


class Mode(_enum.Enum):
    OPCODES = "opcodes"
    ASM = "asm"
    DIS = "dis"

    def __str__(self):
        return self.name.lower()


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("mode", type=Mode, choices=Mode)
    args = dict(vars(parser.parse_args()))

    mode = args["mode"]
    db = _Database(_find_wiki_dir())
    entries = sorted(collect(db))

    generator = {
        Mode.OPCODES: opcodes,
        Mode.ASM: asm,
        Mode.DIS: dis,
    }[mode]
    if mode is Mode.DIS:
        print("#as: -mlibresoc")
        print("#objdump: -dr -Mlibresoc")
        print("")
        print(".*:     file format .*")
        print("")
        print("")
        print("Disassembly of section \\.text:")
        print("0+ <\.text>:")

    for line in map(generator, entries):
        print(line)
