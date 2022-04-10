import abc as _abc
import argparse as _argparse
import dataclasses as _dataclasses
import enum as _enum

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
    RC as _RC,
)
from openpower.consts import SVP64MODE as _SVP64MODE
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


class EnumMeta(_enum.EnumMeta):
    def __call__(metacls, *args, **kwargs):
        if len(args) > 1:
            names = args[1]
        else:
            names = kwargs.pop("names")

        if isinstance(names, type) and issubclass(names, _enum.Enum):
            names = dict(names.__members__)
        if isinstance(names, dict):
            names = tuple(names.items())

        return super().__call__(*args, names=names, **kwargs)


class Enum(CType, _enum.Enum, metaclass=EnumMeta):
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


In1Sel = Enum("In1Sel", names=_In1Sel.__members__.items())
In2Sel = Enum("In2Sel", names=_In2Sel.__members__.items())
In3Sel = Enum("In3Sel", names=_In3Sel.__members__.items())
OutSel = Enum("OutSel", names=_OutSel.__members__.items())
CRInSel = Enum("CRInSel", names=_CRInSel.__members__.items())
CROutSel = Enum("CROutSel", names=_CROutSel.__members__.items())
SVPType = Enum("SVPType", names=_SVPtype.__members__.items())
SVEType = Enum("SVEType", names=_SVEtype.__members__.items())
SVEXTRA = Enum("SVEXTRA", names=_SVEXTRA.__members__.items())


class Constant(CType, _enum.Enum):
    @classmethod
    def c_decl(cls):
        c_tag = f"svp64_{cls.__name__.lower()}"
        yield f"/* {c_tag.upper()} constants */"
        for (key, item) in cls.__members__.items():
            key = f"{c_tag.upper()}_{key.upper()}"
            value = f"0x{item.value:08x}U"
            yield f"#define {key} {value}"

    def c_value(self, prefix="", suffix=""):
        c_tag = f"svp64_{self.__class__.__name__.lower()}"
        yield f"{prefix}{c_tag.upper()}_{self.name.upper()}{suffix}"


Mode = Constant("Mode", names=_SVP64MODE.__members__.items())


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

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.__value < other.__value

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
class Record(CType):
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

    @classmethod
    def c_decl(cls):
        bits_all = 0
        yield f"struct svp64_record {{"
        for field in _dataclasses.fields(cls):
            bits = len(field.type).bit_length()
            yield from indent([f"uint64_t {field.name} : {bits};"])
            bits_all += bits
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
        yield f"struct svp64_record {name}"


@_dataclasses.dataclass(eq=True, frozen=True)
class Entry(CType):
    name: Name
    record: Record

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.name < other.name

    @classmethod
    def c_decl(cls):
        yield f"struct svp64_entry {{"
        for field in _dataclasses.fields(cls):
            yield from indent(field.type.c_var(name=f"{field.name};"))
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

            enums = (
                In1Sel, In2Sel, In3Sel, OutSel,
                CRInSel, CROutSel,
                SVPType, SVEType, SVEXTRA,
                Mode,
            )
            for enum in enums:
                yield from enum.c_decl()
                yield ""

            yield from Record.c_decl()
            yield ""

            yield from Entry.c_decl()
            yield ""

            yield "extern const struct svp64_entry svp64_entries[];"
            yield "extern const unsigned int svp64_num_entries;"
            yield ""

            yield f"#define SVP64_NAME_MAX {max(map(lambda entry: len(entry.name), entries))}"
            yield ""

            yield "enum svp64_reg_category {"
            yield "    SVP64_REG_CATEGORY_UNKNOWN,"
            yield "    SVP64_REG_CATEGORY_GPR,"
            yield "    SVP64_REG_CATEGORY_FPR,"
            yield "    SVP64_REG_CATEGORY_CR_3BIT,"
            yield "    SVP64_REG_CATEGORY_CR_5BIT,"
            yield "};"
            yield ""

            yield "enum svp64_reg_category"
            yield "svp64_reg_category(unsigned char type);"

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

            yield "const struct svp64_entry svp64_entries[] = {"
            for (index, entry) in enumerate(entries):
                yield from indent(entry.c_value(prefix=f"[{index}] = ", suffix=","))
            yield f"}};"
            yield ""

            yield "const unsigned int svp64_num_entries = \\"
            yield "    sizeof (svp64_entries) / sizeof (svp64_entries[0]);"
            yield ""

            yield "#ifndef BC"
            yield "#define BC CRB"
            yield "#endif"
            yield ""
            yield "enum svp64_reg_category"
            yield "svp64_reg_category(unsigned char type)"
            yield "{"
            yield "    size_t i;"
            yield "    static struct {"
            yield "        unsigned char type;"
            yield "        unsigned char category;"
            yield "    } const table[] = {"
            yield "        {BF  , SVP64_REG_CATEGORY_CR_3BIT},"
            yield "        {BFA , SVP64_REG_CATEGORY_CR_3BIT},"
            yield "        {BA  , SVP64_REG_CATEGORY_CR_5BIT},"
            yield "        {BB  , SVP64_REG_CATEGORY_CR_5BIT},"
            yield "        {BC  , SVP64_REG_CATEGORY_CR_5BIT},"
            yield "        {BI  , SVP64_REG_CATEGORY_CR_5BIT},"
            yield "        {BT  , SVP64_REG_CATEGORY_CR_5BIT},"
            yield "        {RA  , SVP64_REG_CATEGORY_GPR},"
            yield "        {RB  , SVP64_REG_CATEGORY_GPR},"
            yield "        {RC  , SVP64_REG_CATEGORY_GPR},"
            yield "        {RS  , SVP64_REG_CATEGORY_GPR},"
            yield "        {RT  , SVP64_REG_CATEGORY_GPR},"
            yield "        {FRA , SVP64_REG_CATEGORY_FPR},"
            yield "        {FRB , SVP64_REG_CATEGORY_FPR},"
            yield "        {FRC , SVP64_REG_CATEGORY_FPR},"
            yield "        {FRS , SVP64_REG_CATEGORY_FPR},"
            yield "        {FRT , SVP64_REG_CATEGORY_FPR},"
            yield "    };"
            yield ""
            yield "    for (i = 0; i < sizeof (table) / sizeof (table[0]); ++i) {"
            yield "        if (table[i].type == type)"
            yield "            return (enum svp64_reg_category)table[i].category;"
            yield "    }"
            yield ""
            yield "    return SVP64_REG_CATEGORY_UNKNOWN;"
            yield "}"

        return {
            Codegen.PPC_SVP64_H: ppc_svp64_h,
            Codegen.PPC_SVP64_OPC_C: ppc_svp64_opc_c,
        }[self](entries)


ISA = _SVP64RM()
FIELDS = {field.name:field.type for field in _dataclasses.fields(Record)}
FIELDS.update({field.name:field.type for field in _dataclasses.fields(Entry)})

def parse(path, opcode_cls):
    visited = set()

    def name_filter(name):
        if name.startswith("l") and name.endswith("br"):
            return False
        if name in {"mcrxr", "mcrxrx", "darn"}:
            return False
        if name in {"bctar", "bcctr"}:
            return False
        if "rfid" in name:
            return False
        if name in {"setvl"}:
            return False
        if name in visited:
            return False

        visited.add(name)

        return True

    def item_mapper(item):
        (key, value) = item
        key = key.lower().replace(" ", "_")
        cls = FIELDS.get(key, object)
        if not isinstance(value, cls):
            if issubclass(cls, _enum.Enum):
                value = {item.name:item for item in cls}[value]
            else:
                value = cls(value)
        return (key, value)

    def item_filter(item):
        (key, _) = item
        return (key in FIELDS)

    for record in ISA.get_svp64_csv(path):
        opcode = opcode_cls(record.pop("opcode"))
        names = record.pop("comment").split("=")[-1].split("/")
        names = set(filter(name_filter, names))
        if names:
            rc = _RC[record["rc"] if record["rc"] else "NONE"]
            if rc is _RC.RC:
                names.update({f"{name}." for name in names})
            record = dict(filter(item_filter, map(item_mapper, record.items())))
            for name in map(Name, names):
                yield Entry(name=name, record=Record(**record))


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
