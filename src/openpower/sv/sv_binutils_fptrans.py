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


def collect(db):
    fptrans = tuple(_FPTRANS_INSNS)
    fptrans_Rc = tuple(map(lambda name: f"{name}.", fptrans))

    def fptrans_match(insn):
        return ((insn.name in fptrans) or (insn.name in fptrans_Rc))

    for record in filter(fptrans_match, db):
        if len(record.opcodes) > 1:
            raise NotImplementedError(record.opcodes)

        yield record


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


def asm(record, binutils=False, regex=False):
    operands = tuple(record.dynamic_operands)
    for (idx, operand) in enumerate(operands):
        values = []
        for each in operands:
            if binutils and each.name in ("FRT", "FRA", "FRB"):
                values.append("f0")
            elif binutils and each.name in ("RT", "RA", "RB"):
                values.append("r0")
            else:
                values.append("0")
        value = str((1 << len(operand.span)) - 1)
        if binutils and operand.name in ("FRT", "FRA", "FRB"):
            value = f"f{value}"
        elif binutils and operand.name in ("RT", "RA", "RB"):
            value = f"r{value}"
        values[idx] = value
        sep = "\s+" if regex else " "
        yield f"{record.name}{sep}{','.join(values)}"


def dis(record, binutils=True):
    def objdump(byte):
        return f"{byte:02x}"

    asm_plain = tuple(asm(record, binutils=binutils, regex=False))
    asm_regex = tuple(asm(record, binutils=binutils, regex=True))
    for (idx, dynamic_operand) in enumerate(record.dynamic_operands):
        insn = _WordInstruction.integer(value=0)
        for static_operand in record.static_operands:
            insn[static_operand.span] = static_operand.value
        span = dynamic_operand.span
        insn[span] = ((1 << len(span)) - 1)
        if binutils:
            big = " ".join(map(objdump, insn.bytes(byteorder="big")))
            little = " ".join(map(objdump, insn.bytes(byteorder="little")))
            yield f".*:\s+({big}|{little})\s+{asm_regex[idx]}"
        else:
            yield asm_plain[idx]


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

    if mode in {Mode.ASM, Mode.DIS}:
        for subgenerator in map(generator, entries):
            for line in subgenerator:
                print(line)
    else:
        for line in map(generator, entries):
            print(line)
