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


class CTypeMeta(type):
    def __new__(metacls, name, bases, attrs, typedef=None):
        cls = super().__new__(metacls, name, bases, attrs)
        cls.__typedef = typedef

        return cls

    @property
    def c_typedef(cls):
        return cls.__typedef

    @_abc.abstractmethod
    def c_decl(cls):
        yield from ()

    def c_var(cls, name, prefix="", suffix=""):
        yield f"{prefix}{cls.c_typedef} {name}{suffix}"


class CType(metaclass=CTypeMeta):
    @_abc.abstractmethod
    def c_value(self, prefix="", suffix=""):
        yield from ()


class EnumMeta(_enum.EnumMeta, CTypeMeta):
    def __call__(metacls, name, entries, tag=None, **kwargs):
        if isinstance(entries, type) and issubclass(entries, _enum.Enum):
            entries = dict(entries.__members__)
        if isinstance(entries, dict):
            entries = tuple(entries.items())
        if tag is None:
            tag = f"svp64_{name.lower()}"

        cls = super().__call__(value=name, names=entries, **kwargs)
        cls.__tag = tag
        return cls

    @property
    def c_typedef(cls):
        return f"enum {cls.c_tag}"

    @property
    def c_tag(cls):
        return cls.__tag

    def c_var(cls, name, prefix="", suffix=""):
        yield f"{prefix}{cls.c_typedef} {name}{suffix}"


class Enum(CType, _enum.Enum, metaclass=EnumMeta):
    @classmethod
    def c_decl(cls):
        yield f"{cls.c_typedef} {{"
        for item in cls:
            yield from indent(item.c_value(suffix=","))
        yield f"}};"

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{self.__class__.c_tag.upper()}_{self.name.upper()}{suffix}"


In1Sel = Enum("In1Sel", _In1Sel)
In2Sel = Enum("In2Sel", _In2Sel)
In3Sel = Enum("In3Sel", _In3Sel)
OutSel = Enum("OutSel", _OutSel)
CRInSel = Enum("CRInSel", _CRInSel)
CROutSel = Enum("CROutSel", _CROutSel)
SVPType = Enum("SVPType", _SVPtype)
SVEType = Enum("SVEType", _SVEtype)
SVEXTRA = Enum("SVEXTRA", _SVEXTRA)


class Constant(CType, _enum.Enum, metaclass=EnumMeta):
    @classmethod
    def c_decl(cls):
        yield f"/* {cls.c_tag.upper()} constants */"
        for (key, item) in cls.__members__.items():
            key = f"{cls.c_tag.upper()}_{key.upper()}"
            value = f"0x{item.value:08x}U"
            yield f"#define {key} {value}"

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{self.__class__.c_tag.upper()}_{self.name.upper()}{suffix}"


Mode = Constant("Mode", _SVP64MODE)


class StructMeta(CTypeMeta):
    def __new__(metacls, name, bases, attrs, tag=None, **kwargs):
        if tag is None:
            tag = f"svp64_{name.lower()}"
        if "typedef" not in kwargs:
            kwargs["typedef"] = f"struct {tag}"

        cls = super().__new__(metacls, name, bases, attrs, **kwargs)
        cls.__tag = tag

        return cls

    @property
    def c_tag(cls):
        return cls.__tag

    def c_decl(cls):
        yield f"{cls.c_typedef} {{"
        for field in _dataclasses.fields(cls):
            yield from indent(field.type.c_var(name=f"{field.name}", suffix=";"))
        yield f"}};"


@_dataclasses.dataclass(eq=True, frozen=True)
class Struct(CType, metaclass=StructMeta):
    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{{"
        for field in _dataclasses.fields(self):
            name = field.name
            attr = getattr(self, name)
            yield from indent(attr.c_value(prefix=f".{name} = ", suffix=","))
        yield f"}}{suffix}"


class Integer(CType, int):
    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{self}{suffix}"


class Byte(Integer, typedef="uint8_t"):
    pass


class Size(Integer, typedef="size_t"):
    pass


class ArrayMeta(CTypeMeta):
    def __new__(metacls, name, bases, attrs, type=CType, size=0):
        cls = super().__new__(metacls, name, bases, attrs)
        cls.__type = type
        cls.__size = size

        return cls

    def __call__(cls, type, size):
        name = f"{cls.__name__}[{type.__name__}]"
        return ArrayMeta.__new__(ArrayMeta, name, (cls,), {}, type=type, size=size)

    def __len__(cls):
        return cls.__size

    @property
    def c_type(cls):
        return cls.__type

    def c_decl(cls):
        count = f"{cls.__size}" if cls.__size else ""
        yield f"{cls.c_type.c_typedef}[{count}]"

    def c_var(cls, name, prefix="", suffix=""):
        count = f"{cls.__size}" if cls.__size else ""
        yield f"{prefix}{cls.c_type.c_typedef} {name}[{count}]{suffix}"


class Array(CType, tuple, metaclass=ArrayMeta):
    def c_value(self, prefix="", suffix=""):
        items = []
        for item in map(self.__class__.c_type, self):
            items.extend(item.c_value())
        yield f"{prefix}{{{', '.join(items)}}}{suffix}"


class Name(CType, str):
    def __repr__(self):
        escaped = self.replace("\"", "\\\"")
        return f"\"{escaped}\""

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{self!r}{suffix}"

    @classmethod
    def c_var(cls, name, prefix="", suffix=""):
        yield f"{prefix}const char *{name}{suffix}"


@_dataclasses.dataclass(eq=True, frozen=True)
class Record(Struct):
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


@_dataclasses.dataclass(eq=True, frozen=True)
class Entry(Struct):
    name: Name
    record: Record

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.name < other.name


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

            for name in ("in1", "in2", "in3", "out", "out2", "cr_in", "cr_out"):
                yield "unsigned char"
                yield f"svp64_record_{name}_opsel(const struct svp64_record *record);"
                yield ""

            yield from Entry.c_decl()
            yield ""

            yield "extern const struct svp64_entry svp64_entries[];"
            yield "extern const unsigned int svp64_num_entries;"
            yield ""

            yield f"#define SVP64_NAME_MAX {max(map(lambda entry: len(entry.name), entries))}"
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

            def opsel(enum, name, table):
                sep = (max(map(len, list(table.values()) + ["UNUSED"])) + 1)
                c_tag = f"svp64_{enum.__name__.lower()}"
                yield "unsigned char"
                yield f"svp64_record_{name}_opsel(const struct svp64_record *record)"
                yield "{"
                yield from indent(["static const unsigned char table[] = {"])
                for key in enum:
                    value = table.get(key, "UNUSED")
                    c_value = f"{c_tag.upper()}_{key.name.upper()}"
                    yield from indent(indent([f"{value:{sep}}, /* {c_value} */"]))
                yield from indent(["};"])
                yield ""
                yield from indent([f"return table[record->{name}];"])
                yield "}"
                yield ""

            yield from opsel(In1Sel, "in1", {
                In1Sel.RA: "RA",
                In1Sel.RA_OR_ZERO: "RA",
                In1Sel.SPR: "SPR",
                In1Sel.RS: "RS",
                In1Sel.FRA: "FRA",
                In1Sel.FRS: "FRS",
            })
            yield from opsel(In2Sel, "in2", {
                In2Sel.RB: "RB",
                In2Sel.SPR: "SPR",
                In2Sel.RS: "RS",
                In2Sel.FRB: "FRB",
            })
            yield from opsel(In3Sel, "in3", {
                In3Sel.RS: "RS",
                In3Sel.RB: "RB",
                In3Sel.FRS: "FRS",
                In3Sel.FRC: "FRC",
                In3Sel.RC: "RC",
                In3Sel.RT: "RT",
            })
            for name in ("out", "out2"):
                yield from opsel(OutSel, name, {
                    OutSel.RT: "RT",
                    OutSel.RA: "RA",
                    OutSel.SPR: "SPR",
                    OutSel.RT_OR_ZERO: "RT",
                    OutSel.FRT: "FRT",
                    OutSel.FRS: "FRS",
                })
            yield from opsel(CRInSel, "cr_in", {
                CRInSel.BI: "BI",
                CRInSel.BFA: "BFA",
                CRInSel.BC: "CRB",
                CRInSel.WHOLE_REG: "FXM",
            })
            yield from opsel(CROutSel, "cr_out", {
                CROutSel.BF: "BF",
                CROutSel.BT: "BT",
                CROutSel.WHOLE_REG: "FXM",
            })

            yield "const struct svp64_entry svp64_entries[] = {"
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


ISA = _SVP64RM()
FIELDS = {field.name:field.type for field in _dataclasses.fields(Record)}
FIELDS.update({field.name:field.type for field in _dataclasses.fields(Entry)})

def parse(path):
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
    paths = (
        "minor_19.csv",
        "minor_30.csv",
        "minor_31.csv",
        "minor_58.csv",
        "minor_62.csv",
        "minor_22.csv",
        "minor_5.csv",
        "minor_63.csv",
        "minor_59.csv",
        "major.csv",
        "extra.csv",
    )
    for path in paths:
        entries.extend(parse(path))
    entries = sorted(frozenset(entries))

    for line in codegen.generate(entries):
        print(line)


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("codegen", type=Codegen, choices=Codegen, help="code generator")

    args = vars(parser.parse_args())
    main(**args)
