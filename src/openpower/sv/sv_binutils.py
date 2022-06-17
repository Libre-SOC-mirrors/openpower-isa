import abc as _abc
import argparse as _argparse
import dataclasses as _dataclasses
import enum as _enum
import operator as _operator

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
from openpower.decoder.isa.caller import SVP64RMFields as _SVP64RMFields
from openpower.decoder.isa.caller import SVP64PrefixFields as _SVP64PrefixFields
from openpower.decoder.selectable_int import SelectableIntMapping


DISCLAIMER = """\
/* {path} -- {desc}
   Copyright (C) 2022 Free Software Foundation, Inc.
   Written by Dmitry Selyutin (ghostmansd).
   Sponsored by NLnet and NGI POINTER under EU Grants 871528 and 957073.

   This file is part of the GNU opcodes library.

   This library is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; either version 3, or (at your option)
   any later version.

   It is distributed in the hope that it will be useful, but WITHOUT
   ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
   or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public
   License for more details.

   You should have received a copy of the GNU General Public License
   along with this file; see the file COPYING.  If not, write to the
   Free Software Foundation, 51 Franklin Street - Fifth Floor, Boston,
   MA 02110-1301, USA. */\
"""


def indent(strings):
    return map(lambda string: ("  " + string), strings)


class CTypeMeta(type):
    def __new__(metacls, name, bases, attrs, typedef=None):
        cls = super().__new__(metacls, name, bases, attrs)
        cls.__typedef = typedef

        return cls

    def __getitem__(cls, size):
        name = f"{cls.__name__}[{'' if size is Ellipsis else size}]"
        return type(name, (Array,), {}, type=cls, size=size)

    @property
    def c_typedef(cls):
        return cls.__typedef

    @_abc.abstractmethod
    def c_decl(cls):
        yield from ()

    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}{cls.c_typedef} {name}{suffix}"


class ArrayMeta(CTypeMeta):
    def __new__(metacls, name, bases, attrs, type, size, **kwargs):
        cls = super().__new__(metacls, name, bases, attrs, **kwargs)
        cls.__type = type
        cls.__ellipsis = (size is Ellipsis)
        cls.__size = 0 if cls.__ellipsis else size

        return cls

    def __len__(cls):
        return cls.__size

    def c_decl(cls):
        size = "" if cls.__ellipsis else f"{cls.__size}"
        yield f"{cls.__type.c_typedef}[{size}]"

    def c_var(cls, name, prefix="", suffix=""):
        size = "" if cls.__ellipsis else f"{cls.__size}"
        return f"{prefix}{cls.__type.c_typedef} {name}[{size}]{suffix}"


class BitmapMeta(CTypeMeta):
    def __new__(metacls, name, bases, attrs,
            typedef="uint64_t", bits=0, **kwargs):
        cls = super().__new__(metacls, name, bases, attrs,
            typedef=typedef, **kwargs)
        cls.__bits = bits
        return cls

    def __len__(cls):
        return cls.__bits

    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}{cls.c_typedef} {name} : {cls.__bits}{suffix}"


class CType(metaclass=CTypeMeta):
    @_abc.abstractmethod
    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield from ()


class Array(CType, tuple, metaclass=ArrayMeta, type=CType, size=...):
    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{{"
        for (index, item) in enumerate(self):
            yield from indent(item.c_value(suffix=","))
        yield f"}}{suffix}"


class Bitmap(metaclass=BitmapMeta):
    pass


class Void(CType, typedef="void"):
    def c_var(cls, name, prefix="", suffix=""):
        raise NotImplementedError


class EnumMeta(_enum.EnumMeta, CTypeMeta):
    def __call__(metacls, name, entries, tag=None, exclude=None, **kwargs):
        if exclude is None:
            exclude = frozenset()
        if isinstance(entries, type) and issubclass(entries, _enum.Enum):
            # Use __members__, not __iter__, otherwise aliases are lost.
            entries = dict(entries.__members__)
        if isinstance(entries, dict):
            entries = tuple(entries.items())
        entries = ((key, value) for (key, value) in entries if key not in exclude)
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

    def c_decl(cls):
        yield f"{cls.c_typedef} {{"
        for item in cls:
            yield from indent(item.c_value(suffix=","))
        yield f"}};"

    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}{cls.c_typedef} {name}{suffix}"


class Enum(CType, _enum.Enum, metaclass=EnumMeta):
    @property
    def c_name(self):
        return f"{self.__class__.c_tag.upper()}_{self.name.upper()}"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self.c_name}{suffix}"


In1Sel = Enum("In1Sel", _In1Sel, tag="svp64_in1_sel")
In2Sel = Enum("In2Sel", _In2Sel, tag="svp64_in2_sel")
In3Sel = Enum("In3Sel", _In3Sel, tag="svp64_in3_sel")
OutSel = Enum("OutSel", _OutSel, tag="svp64_out_sel")
CRInSel = Enum("CRInSel", _CRInSel, tag="svp64_cr_in_sel")
CROutSel = Enum("CROutSel", _CROutSel, tag="svp64_cr_out_sel")
PType = Enum("PType", _SVPtype, tag="svp64_ptype")
EType = Enum("EType", _SVEtype, tag="svp64_etype", exclude="NONE")
Extra = Enum("Extra", _SVEXTRA, tag="svp64_extra", exclude="Idx_1_2")


class Constant(CType, _enum.Enum, metaclass=EnumMeta):
    @classmethod
    def c_decl(cls):
        yield f"/* {cls.c_tag.upper()} constants */"
        # Use __members__, not __iter__, otherwise aliases are lost.
        for (key, item) in cls.__members__.items():
            key = f"{cls.c_tag.upper()}_{key.upper()}"
            value = f"0x{item.value:08x}U"
            yield f"#define {key} {value}"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self.__class__.c_tag.upper()}_{self.c_name.upper()}{suffix}"


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
            yield from indent([field.type.c_var(name=f"{field.name}",
                                    suffix=";")])
        yield f"}};"


@_dataclasses.dataclass(eq=True, frozen=True)
class Struct(CType, metaclass=StructMeta):
    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{{"
        for field in _dataclasses.fields(self):
            name = field.name
            attr = getattr(self, name)
            yield from indent(attr.c_value(prefix=f".{name} = ", suffix=","))
        yield f"}}{suffix}"


class Integer(CType, str):
    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self}{suffix}"


class Byte(Integer, typedef="uint8_t"):
    pass


class Size(Integer, typedef="size_t"):
    pass


class UInt32(Integer, typedef="uint32_t"):
    pass


class Name(CType, str):
    def __repr__(self):
        escaped = self.replace("\"", "\\\"")
        return f"\"{escaped}\""

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self!r}{suffix}"

    @classmethod
    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}const char *{name}{suffix}"


@_dataclasses.dataclass(eq=True, frozen=True)
class Desc(Struct):
    in1: In1Sel
    in2: In2Sel
    in3: In3Sel
    out: OutSel
    out2: OutSel
    cr_in: CRInSel
    cr_out: CROutSel
    sv_ptype: PType
    sv_etype: EType
    sv_in1: Extra
    sv_in2: Extra
    sv_in3: Extra
    sv_out: Extra
    sv_out2: Extra
    sv_cr_in: Extra
    sv_cr_out: Extra

    @classmethod
    def c_decl(cls):
        bits_all = 0
        yield f"struct svp64_desc {{"
        for field in _dataclasses.fields(cls):
            bits = len(field.type).bit_length()
            yield from indent([f"uint64_t {field.name} : {bits};"])
            bits_all += bits
        bits_rsvd = (64 - (bits_all % 64))
        if bits_rsvd:
            yield from indent([f"uint64_t : {bits_rsvd};"])
        yield f"}};"


@_dataclasses.dataclass(eq=True, frozen=True)
class Record(Struct):
    name: Name
    desc: Desc

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.name < other.name


class FunctionMeta(CTypeMeta):
    def __new__(metacls, name, bases, attrs, rv, args):
        cls = super().__new__(metacls, name, bases, attrs)
        cls.__rv = rv
        cls.__args = args

        return cls

    def c_var(cls, name, prefix="", suffix=""):
        rv = cls.__rv.c_typedef
        args = ", ".join(arg_cls.c_var(arg_name) \
                    for (arg_name, arg_cls) in cls.__args)
        return f"{prefix}{rv} {name}({args}){suffix}"


class FieldsMappingMeta(EnumMeta):
    class HelperMeta(FunctionMeta):
        def __new__(metacls, name, bases, attrs, rv, args, enum):
            cls = super().__new__(metacls, name, bases, attrs, rv=rv, args=args)
            cls.__enum = enum
            return cls

        def __iter__(cls):
            short_c_tag = cls.__enum.c_tag[:-len("_field")]
            # Use __members__, not __iter__, otherwise aliases are lost.
            for (name, value) in cls.__enum.__members__.items():
                yield (f"{short_c_tag}_{name}".upper(), value)

    class GetterMeta(HelperMeta):
        def __new__(metacls, name, bases, attrs, enum, struct):
            return super().__new__(metacls, name, bases, attrs,
                                    enum=enum, rv=UInt32, args=(
                ("storage", struct),
                ("field", enum),
            ))

    class SetterMeta(HelperMeta):
        def __new__(metacls, name, bases, attrs, enum, struct):
            return super().__new__(metacls, name, bases, attrs, enum=enum,
                                   rv=Void, args=(
                ("*storage", struct),
                ("field", enum),
                ("value", UInt32),
            ))

    def __call__(metacls, name, base=SelectableIntMapping, **kwargs):
        def flatten(mapping, parent=""):
            for (key, value) in mapping.items():
                key = f"{parent}_{key}" if parent else key
                if isinstance(value, dict):
                    yield from flatten(mapping=value, parent=key)
                else:
                    value = map(lambda bit: bit, reversed(value))
                    # value = map(lambda bit: ((base.bits - 1) - bit),
                    # reversed(value))
                    yield (key.upper(), tuple(value))

        tag = f"svp64_{name.lower()}"
        fields = dict(flatten(mapping=dict(base)))
        bitmap = type(name, (Bitmap,), {}, typedef="uint32_t", bits=base.bits)
        struct = _dataclasses.make_dataclass(name, (("value", bitmap),),
            bases=(Struct,), frozen=True, eq=True)

        cls = super().__call__(name=name, entries=fields, tag=f"{tag}_field",
                               **kwargs)

        def c_value(fields, stmt):
            yield "switch (field) {"
            for (field_name, field_value) in fields:
                yield from indent([f"case {field_name}:"])
                yield from indent(indent(map(stmt,
                                             enumerate(field_value.value))))
                yield from indent(indent(["break;"]))
            yield "}"

        class Getter(metaclass=FieldsMappingMeta.GetterMeta,
                enum=cls, struct=struct):
            def c_value(self, prefix="", suffix=""):
                yield f"{prefix}{{"
                yield from indent([
                    UInt32.c_var(name="result", suffix=" = UINT32_C(0);"),
                    UInt32.c_var(name="origin", suffix=" = storage.value;"),
                ])
                yield ""
                yield from indent(c_value(fields=self.__class__,
                    stmt=lambda kv: f"result |= SVP64_FIELD_GET(origin, {kv[1]}, {kv[0]});"))
                yield ""
                yield from indent(["return result;"])
                yield f"}}{suffix}"

        class Setter(metaclass=FieldsMappingMeta.SetterMeta,
                enum=cls, struct=struct):
            def c_value(self, prefix="", suffix=""):
                yield f"{prefix}{{"
                yield from indent([
                    UInt32.c_var(name="result", suffix=" = storage->value;"),
                ])
                yield ""
                yield from indent(c_value(fields=self.__class__,
                    stmt=lambda kv: f"SVP64_FIELD_SET(&result, value, {kv[0]}, {kv[1]});"))
                yield ""
                yield from indent(["storage->value = result;"])
                yield f"}}{suffix}"

        cls.__tag = tag
        cls.__struct = struct
        cls.__getter = Getter()
        cls.__setter = Setter()

        return cls

    @property
    def c_getter(cls):
        return cls.__getter

    @property
    def c_setter(cls):
        return cls.__setter

    def c_decl(cls):
        yield f"{cls.c_typedef} {{"
        for field_name in cls.__members__.keys():
            short_c_tag = cls.c_tag[:-len("_field")]
            yield from indent([f"{short_c_tag}_{field_name},".upper()])
        yield f"}};"
        yield from cls.__struct.c_decl()
        yield cls.__getter.__class__.c_var(name=f"{cls.__tag}_get", suffix=";")
        yield cls.__setter.__class__.c_var(name=f"{cls.__tag}_set", suffix=";")


class FieldsMapping(Enum, metaclass=FieldsMappingMeta):
    @property
    def c_name(self):
        short_c_tag = self.__class__.c_tag[:-len("_field")]
        return f"{short_c_tag}_{self.name}".upper()


Prefix = FieldsMapping("Prefix", base=_SVP64PrefixFields)
RM = FieldsMapping("RM", base=_SVP64RMFields)


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

    def generate(self, records):
        def ppc_svp64_h(records, num_records):
            disclaimer = DISCLAIMER.format(path=str(self),
                desc="Header file for PowerPC opcode table (SVP64 extensions)")
            yield from disclaimer.splitlines()
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
                PType, EType, Extra,
                Mode,
            )
            for enum in enums:
                yield from enum.c_decl()
                yield ""

            for cls in (Desc, Record, Prefix, RM):
                yield from cls.c_decl()
                yield ""

            for name in ("in1", "in2", "in3", "out", "out2", "cr_in", "cr_out"):
                yield "ppc_opindex_t"
                yield f"svp64_desc_{name}_opindex(const struct svp64_desc *desc);"
                yield ""

            yield records.__class__.c_var("svp64_records",
                        prefix="extern const ", suffix=";")
            yield num_records.__class__.c_var("svp64_num_records",
                        prefix="extern const ", suffix=";")
            yield ""

            yield f"#define SVP64_NAME_MAX {max(map(lambda record: len(record.name), records))}"
            yield ""

            yield "#ifdef __cplusplus"
            yield "}"
            yield "#endif"
            yield ""

            yield f"#endif /* {self.name} */"
            yield ""

        def ppc_svp64_opc_c(records, num_records):
            disclaimer = DISCLAIMER.format(path=str(self),
                desc="PowerPC opcode list (SVP64 extensions)")
            yield from disclaimer.splitlines()
            yield ""

            yield "#include \"opcode/ppc-svp64.h\""
            yield ""

            def opindex(enum, name, table):
                sep = (max(map(len, list(table.values()) + ["UNUSED"])) + 1)
                c_tag = f"svp64_{enum.__name__.lower()}"
                yield "ppc_opindex_t"
                yield f"svp64_desc_{name}_opindex(const struct svp64_desc *desc)"
                yield "{"
                yield from indent(["static const ppc_opindex_t table[] = {"])
                for key in enum:
                    value = table.get(key, "UNUSED")
                    yield from indent(indent([f"{value:{sep}}, /* {key.c_name} */"]))
                yield from indent(["};"])
                yield ""
                yield from indent([f"return table[desc->{name}];"])
                yield "}"
                yield ""

            yield from opindex(In1Sel, "in1", {
                In1Sel.RA: "RA",
                In1Sel.RA_OR_ZERO: "RA0",
                In1Sel.SPR: "SPR",
                In1Sel.RS: "RS",
                In1Sel.FRA: "FRA",
                In1Sel.FRS: "FRS",
            })
            yield from opindex(In2Sel, "in2", {
                In2Sel.RB: "RB",
                In2Sel.SPR: "SPR",
                In2Sel.RS: "RS",
                In2Sel.FRB: "FRB",
            })
            yield from opindex(In3Sel, "in3", {
                In3Sel.RS: "RS",
                In3Sel.RB: "RB",
                In3Sel.FRS: "FRS",
                In3Sel.FRC: "FRC",
                In3Sel.RC: "RC",
                In3Sel.RT: "RT",
            })
            for name in ("out", "out2"):
                yield from opindex(OutSel, name, {
                    OutSel.RT: "RT",
                    OutSel.RA: "RA",
                    OutSel.SPR: "SPR",
                    OutSel.RT_OR_ZERO: "RT",
                    OutSel.FRT: "FRT",
                    OutSel.FRS: "FRS",
                })
            yield from opindex(CRInSel, "cr_in", {
                CRInSel.BI: "BI",
                CRInSel.BFA: "BFA",
                CRInSel.BC: "BC",
                CRInSel.WHOLE_REG: "FXM",
            })
            yield from opindex(CROutSel, "cr_out", {
                CROutSel.BF: "BF",
                CROutSel.BT: "BT",
                CROutSel.WHOLE_REG: "FXM",
            })

            yield records.__class__.c_var("svp64_records",
                        prefix="const ", suffix=" = \\")
            yield from records.c_value(prefix="", suffix=";")
            yield ""
            yield num_records.__class__.c_var("svp64_num_records",
                        prefix="const ", suffix=" = \\")
            yield from indent(num_records.c_value(suffix=";"))
            yield ""

            bit_shl = lambda val, pos: f"({val} << UINT32_C({pos}))"
            bit_shr = lambda val, pos: f"({val} >> UINT32_C({pos}))"
            bit_get = lambda val, pos: f"({bit_shr(val, pos)} & UINT32_C(1))"
            bit_or = lambda lhs, rhs: f"({lhs} | {rhs})"
            bit_and = lambda lhs, rhs: f"({lhs} & {rhs})"
            bit_not = lambda val: f"~({val})"

            macros = (
                (
                    "SVP64_FIELD_CLEAR",
                    ("VALUE", "BIT"),
                    bit_and("VALUE", bit_not(bit_shl("UINT32_C(1)", "BIT"))),
                ),
                (
                    "SVP64_FIELD_REMAP",
                    ("VALUE", "SRC", "DST"),
                    bit_shl(bit_get("VALUE", "SRC"), "DST"),
                ),
                (
                    "SVP64_FIELD_GET",
                    ("ORIGIN", "SRC", "DST"),
                    "SVP64_FIELD_REMAP(ORIGIN, SRC, DST)",
                ),
                (
                    "SVP64_FIELD_SET",
                    ("RESULT", "VALUE", "SRC", "DST"),
                    ("do { (*RESULT) = " + bit_or(
                        lhs="SVP64_FIELD_CLEAR(*(RESULT), DST)",
                        rhs="SVP64_FIELD_REMAP(VALUE, SRC, DST)",
                    ) + "; } while (0)"),
                ),
            )
            for (name, args, body) in macros:
                yield f"#define {name}({', '.join(args)}) \\"
                yield from indent([body])
                yield ""

            for cls in (Prefix, RM):
                table = {
                    "get": cls.c_getter,
                    "set": cls.c_setter,
                }
                for (mode, subcls) in table.items():
                    yield subcls.__class__.c_var(name=f"svp64_{cls.__name__.lower()}_{mode}")
                    yield from subcls.c_value()
                    yield ""

            for name in map(_operator.itemgetter(0), macros):
                yield f"#undef {name}"
            yield ""


        records = Record[...](records)
        num_records = Size("(sizeof (svp64_records) / sizeof (svp64_records[0]))")

        return {
            Codegen.PPC_SVP64_H: ppc_svp64_h,
            Codegen.PPC_SVP64_OPC_C: ppc_svp64_opc_c,
        }[self](records, num_records)


ISA = _SVP64RM()
FIELDS = {field.name:field.type for field in _dataclasses.fields(Desc)}

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

    for data in ISA.get_svp64_csv(path):
        comment = data.pop("comment")
        names = comment.split("=")[-1].split("/")
        names = set(filter(name_filter, names))
        if not names:
            continue
        rc = _RC[data["rc"] if data["rc"] else "NONE"]
        if rc is _RC.RC:
            names.update({f"{name}." for name in names})

        desc = {}
        for (key, value) in data.items():
            key = key.lower().replace(" ", "_")
            cls = FIELDS.get(key)
            if cls is None:
                continue

            if ((cls is EType and value == "NONE") or
                    (cls is Extra and value == "Idx_1_2")):
                desc = {}
                break

            if not isinstance(value, cls):
                if issubclass(cls, _enum.Enum):
                    value = {item.name:item for item in cls}[value]
                else:
                    value = cls(value)
            desc[key] = value

        if not desc:
            continue

        desc = Desc(**desc)
        for name in map(Name, names):
            yield Record(name=name, desc=desc)


def main(codegen):
    records = []
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
        records.extend(parse(path))
    records = sorted(frozenset(records))

    for line in codegen.generate(records):
        print(line)


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("codegen",
        type=Codegen, choices=Codegen,
        help="code generator")

    args = vars(parser.parse_args())
    main(**args)
