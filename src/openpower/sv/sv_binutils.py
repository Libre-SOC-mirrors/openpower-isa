import abc as _abc
import argparse as _argparse
import dataclasses as _dataclasses
import enum as _enum
import re as _re

from openpower.decoder.power_enums import (
    In1Sel as _In1Sel,
    In2Sel as _In2Sel,
    In3Sel as _In3Sel,
    OutSel as _OutSel,
    CRInSel as _CRInSel,
    CROutSel as _CROutSel,
    SVPtype as _SVPtype,
    SVEtype as _SVEtype,
    SVEXTRA as _SVEXTRA,
)
from openpower.decoder.power_svp64 import SVP64RM as _SVP64RM


DISCLAIMER = (
    "/*",
    " * this file is auto-generated, do not edit",
    " * https://git.libre-soc.org/?p=openpower-isa.git;a=blob;f=src/openpower/sv/sv_binutils.py",
    " * part of Libre-SOC, sponsored by NLnet",
    " */",
)


def indent(strings):
    return map(lambda string: ("    " + string), strings)


class CType:
    @classmethod
    @_abc.abstractmethod
    def c_decl(self, name):
        pass

    @_abc.abstractmethod
    def c_value(self, prefix="", suffix=""):
        pass

    @classmethod
    @_abc.abstractmethod
    def c_var(self, name):
        pass


class Enum(CType, _enum.Enum):
    @classmethod
    def c_decl(cls):
        c_tag = f"svp64_{cls.__name__.lower()}"
        yield f"enum {c_tag} {{"
        for item in cls:
            yield from indent(item.c_value(suffix=","))
        yield f"}};"

    def c_value(self, prefix="", suffix=""):
        c_tag = f"svp64_{self.__class__.__name__.lower()}"
        yield f"{prefix}{c_tag.upper()}_{self.name.upper()}{suffix}"

    @classmethod
    def c_var(cls, name):
        c_tag = f"svp64_{cls.__name__.lower()}"
        yield f"enum {c_tag} {name}"


# Python forbids inheriting from enum unless it's empty.
In1Sel = Enum("In1Sel", {item.name:item.value for item in _In1Sel})
In2Sel = Enum("In2Sel", {item.name:item.value for item in _In2Sel})
In3Sel = Enum("In3Sel", {item.name:item.value for item in _In3Sel})
OutSel = Enum("OutSel", {item.name:item.value for item in _OutSel})
CRInSel = Enum("CRInSel", {item.name:item.value for item in _CRInSel})
CROutSel = Enum("CROutSel", {item.name:item.value for item in _CROutSel})
SVPType = Enum("SVPType", {item.name:item.value for item in _SVPtype})
SVEType = Enum("SVEType", {item.name:item.value for item in _SVEtype})
SVEXTRA = Enum("SVEXTRA", {item.name:item.value for item in _SVEXTRA})


class Opcode(CType):
    def __init__(self, value, mask, bits):
        self.__value = value
        self.__mask = mask
        self.__bits = bits

        return super().__init__()

    @property
    def value(self):
        return self.__value

    @property
    def mask(self):
        return self.__mask

    @property
    def bits(self):
        return self.__bits

    def __repr__(self):
        fmt = f"{{value:0{self.bits}b}}:{{mask:0{self.bits}b}}"
        return fmt.format(value=self.value, mask=self.mask)

    @classmethod
    def c_decl(cls):
        yield f"struct svp64_opcode {{"
        yield from indent([
            "uint32_t value;",
            "uint32_t mask;",
        ])
        yield f"}};"

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{{"
        yield from indent([
            f".value = UINT32_C(0x{self.value:08X}),",
            f".mask = UINT32_C(0x{self.mask:08X}),",
        ])
        yield f"}}{suffix}"

    @classmethod
    def c_var(cls, name):
        yield f"struct svp64_opcode {name}"


class IntegerOpcode(Opcode):
    def __init__(self, integer):
        value = int(integer, 0)
        bits = max(1, value.bit_length())
        mask = int(("1" * bits), 2)

        return super().__init__(value=value, mask=mask, bits=bits)


class PatternOpcode(Opcode):
    def __init__(self, pattern):
        value = 0
        mask = 0
        bits = len(pattern)
        for bit in pattern:
            value |= (bit == "1")
            mask |= (bit != "-")
            value <<= 1
            mask <<= 1
        value >>= 1
        mask >>= 1

        return super().__init__(value=value, mask=mask, bits=bits)


class Name(CType, str):
    def __repr__(self):
        escaped = self.replace("\"", "\\\"")
        return f"\"{escaped}\""

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{self!r}{suffix}"

    @classmethod
    def c_var(cls, name):
        yield f"const char *{name}"


@_dataclasses.dataclass(eq=True, frozen=True)
class Entry(CType):
    name: Name
    opcode: Opcode
    in1: In1Sel
    in2: In2Sel
    in3: In3Sel
    out: OutSel
    out2: OutSel
    cr_in: CRInSel
    cr_out: CROutSel
    sv_ptype: SVPType
    sv_etype: SVEType
    sv_in1: SVEXTRA
    sv_in2: SVEXTRA
    sv_in3: SVEXTRA
    sv_out: SVEXTRA
    sv_out2: SVEXTRA
    sv_cr_in: SVEXTRA
    sv_cr_out: SVEXTRA

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.name < other.name

    @classmethod
    def c_decl(cls):
        bits_all = 0
        yield f"struct svp64_entry {{"
        for field in _dataclasses.fields(cls):
            if issubclass(field.type, Enum):
                bits = len(field.type).bit_length()
                yield from indent([f"uint64_t {field.name} : {bits};"])
                bits_all += bits
            else:
                yield from indent(field.type.c_var(name=f"{field.name};"))
        bits_rsvd = (64 - (bits_all % 64))
        if bits_rsvd:
            yield from indent([f"uint64_t : {bits_rsvd};"])
        yield f"}};"

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{{"
        for field in _dataclasses.fields(self):
            name = field.name
            attr = getattr(self, name)
            yield from indent(attr.c_value(prefix=f".{name} = ", suffix=","))
        yield f"}}{suffix}"

    @classmethod
    def c_var(cls, name):
        yield f"struct svp64_entry {name}"


class Codegen(_enum.Enum):
    PPC_SVP64_H = _enum.auto()
    PPC_SVP64_OPC_C = _enum.auto()

    @classmethod
    def _missing_(cls, value):
        return {
            "ppc-svp64.h": Codegen.PPC_SVP64_H,
            "ppc-svp64-opc.c": Codegen.PPC_SVP64_OPC_C,
        }.get(value)

    def __str__(self):
        return {
            Codegen.PPC_SVP64_H: "ppc-svp64.h",
            Codegen.PPC_SVP64_OPC_C: "ppc-svp64-opc.c",
        }[self]

    def generate(self, entries):
        def ppc_svp64_h(entries):
            yield from DISCLAIMER
            yield ""

            yield f"#ifndef {self.name}"
            yield f"#define {self.name}"
            yield ""

            yield "#include <stdint.h>"
            yield ""

            yield "#ifdef __cplusplus"
            yield "extern \"C\" {"
            yield "#endif"
            yield ""

            yield from Opcode.c_decl()
            yield ""

            enums = (
                In1Sel, In2Sel, In3Sel, OutSel,
                CRInSel, CROutSel,
                SVPType, SVEType, SVEXTRA,
            )
            for enum in enums:
                yield from enum.c_decl()
                yield ""

            yield from Entry.c_decl()
            yield ""

            yield "extern const struct svp64_entry svp64_entries[];"
            yield "extern const unsigned int svp64_num_entries;"
            yield ""

            yield "#ifdef __cplusplus"
            yield "}"
            yield "#endif"
            yield ""

            yield f"#endif /* {self.name} */"
            yield ""

        def ppc_svp64_opc_c(entries):
            yield from DISCLAIMER
            yield ""

            yield "#include \"opcode/ppc-svp64.h\""
            yield ""

            yield "const struct svp64_entry svp64_entries[] = {{"
            for (index, entry) in enumerate(entries):
                yield from indent(entry.c_value(prefix=f"[{index}] = ", suffix=","))
            yield f"}};"
            yield ""

            yield "const unsigned int svp64_num_entries = \\"
            yield "    sizeof (svp64_entries) / sizeof (svp64_entries[0]);"
            yield ""

        return {
            Codegen.PPC_SVP64_H: ppc_svp64_h,
            Codegen.PPC_SVP64_OPC_C: ppc_svp64_opc_c,
        }[self](entries)


def regex_enum(enum):
    assert issubclass(enum, _enum.Enum)
    return "|".join(item.name for item in enum)


PATTERN_VHDL_BINARY = r"(?:2#[01]+#)"
PATTERN_DECIMAL = r"(?:[0-9]+)"
PATTERN_PARTIAL_BINARY = r"(?:[01-]+)"

# Examples of the entries to be caught by the pattern below:
# 2 => (P2, EXTRA3, RA_OR_ZERO, NONE, NONE, RT, NONE, NONE, NONE, Idx1, NONE, NONE, Idx0, NONE, NONE, NONE), -- lwz
# -----10110 => (P2, EXTRA3, NONE, FRB, NONE, FRT, NONE, NONE, CR1, NONE, Idx1, NONE, Idx0, NONE, NONE, Idx0), -- fsqrts
# 2#0000000000# => (P2, EXTRA3, NONE, NONE, NONE, NONE, NONE, BFA, BF, NONE, NONE, NONE, NONE, NONE, Idx1, Idx0), -- mcrf
PATTERN = "".join((
    r"^\s*",
    rf"(?P<opcode>{PATTERN_VHDL_BINARY}|{PATTERN_DECIMAL}|{PATTERN_PARTIAL_BINARY})",
    r"\s?=>\s?",
    r"\(",
    r",\s".join((
        rf"(?P<ptype>{regex_enum(_SVPtype)})",
        rf"(?P<etype>{regex_enum(_SVEtype)})",
        rf"(?P<in1>{regex_enum(_In1Sel)})",
        rf"(?P<in2>{regex_enum(_In2Sel)})",
        rf"(?P<in3>{regex_enum(_In3Sel)})",
        rf"(?P<out>{regex_enum(_OutSel)})",
        rf"(?P<out2>{regex_enum(_OutSel)})",
        rf"(?P<cr_in>{regex_enum(_CRInSel)})",
        rf"(?P<cr_out>{regex_enum(_CROutSel)})",
        rf"(?P<sv_in1>{regex_enum(_SVEXTRA)})",
        rf"(?P<sv_in2>{regex_enum(_SVEXTRA)})",
        rf"(?P<sv_in3>{regex_enum(_SVEXTRA)})",
        rf"(?P<sv_out>{regex_enum(_SVEXTRA)})",
        rf"(?P<sv_out2>{regex_enum(_SVEXTRA)})",
        rf"(?P<sv_cr_in>{regex_enum(_SVEXTRA)})",
        rf"(?P<sv_cr_out>{regex_enum(_SVEXTRA)})",
    )),
    r"\)",
    r",",
    r"\s?--\s?",
    r"(?P<name>[A-Za-z0-9_\./]+)",
    r"\s*$",
))
REGEX = _re.compile(PATTERN)


ISA = _SVP64RM()
FIELDS = {field.name:field for field in _dataclasses.fields(Entry)}
def parse(path, opcode_cls):
    for entry in ISA.get_svp64_csv(path):
        # skip instructions that are not suitable
        name = entry["name"] = entry.pop("comment").split("=")[-1]
        if name.startswith("l") and name.endswith("br"):
            continue
        if name in {"mcrxr", "mcrxrx", "darn"}:
            continue
        if name in {"bctar", "bcctr"}:
            continue
        if "rfid" in name:
            continue
        if name in {"setvl"}:
            continue

        entry = {key.lower().replace(" ", "_"):value for (key, value) in entry.items()}
        for (key, value) in tuple(entry.items()):
            key = key.lower().replace(" ", "_")
            if key not in FIELDS:
                entry.pop(key)
            else:
                field = FIELDS[key]
                if issubclass(field.type, _enum.Enum):
                    value = {item.name:item for item in field.type}[value]
                elif issubclass(field.type, Opcode):
                    value = opcode_cls(value)
                else:
                    value = field.type(value)
                entry[key] = value

        yield Entry(**entry)


def main(codegen):
    entries = []
    table = {
        "minor_19.csv": IntegerOpcode,
        "minor_30.csv": IntegerOpcode,
        "minor_31.csv": IntegerOpcode,
        "minor_58.csv": IntegerOpcode,
        "minor_62.csv": IntegerOpcode,
        "minor_22.csv": IntegerOpcode,
        "minor_5.csv": PatternOpcode,
        "minor_63.csv": PatternOpcode,
        "minor_59.csv": PatternOpcode,
        "major.csv": IntegerOpcode,
        "extra.csv": PatternOpcode,
    }
    for (path, opcode_cls) in table.items():
        entries.extend(parse(path, opcode_cls))
    entries = sorted(frozenset(entries))

    for line in codegen.generate(entries):
        print(line)


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("codegen", type=Codegen, choices=Codegen, help="code generator")

    args = vars(parser.parse_args())
    main(**args)
