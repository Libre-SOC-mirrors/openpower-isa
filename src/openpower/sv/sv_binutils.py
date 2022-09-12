import argparse as _argparse
import dataclasses as _dataclasses
import enum as _enum

import os as _os
import sys as _sys

_sys.path.append(_os.path.dirname(_os.path.realpath(__file__)) + "/../../")

from openpower.decoder.power_enums import (
    In1Sel as _In1Sel,
    In2Sel as _In2Sel,
    In3Sel as _In3Sel,
    OutSel as _OutSel,
    CRInSel as _CRInSel,
    CRIn2Sel as _CRIn2Sel,
    CROutSel as _CROutSel,
    SVPtype as _SVPtype,
    SVEtype as _SVEtype,
    SVExtra as _SVExtra,
    Function as _Function,
    find_wiki_dir as _find_wiki_dir,
)
from openpower.consts import SVP64MODE as _SVP64MODE
from openpower.decoder.power_insn import Database as _Database
from openpower.decoder.power_insn import SVP64Instruction as _SVP64Instruction


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


class ObjectMeta(type):
    def __new__(metacls, clsname, bases, ns,
            c_typedef="void", **kwargs):
        if c_typedef == "void":
            for base in bases:
                if (hasattr(base, "c_typedef") and
                        (base.c_typedef != "void")):
                    c_typedef = base.c_typedef
                    break

        ns.setdefault("c_typedef", c_typedef)
        ns.update(kwargs)

        return super().__new__(metacls, clsname, bases, ns)


class Object(metaclass=ObjectMeta):
    @classmethod
    def c_decl(cls):
        yield from ()

    @classmethod
    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}{cls.c_typedef} {name}{suffix}"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield from ()


class ArrayMeta(ObjectMeta):
    def __new__(metacls, clsname, bases, ns,
            c_base, c_size, **kwargs):
        if c_size is Ellipsis:
            clsname = f"{clsname}[]"
        else:
            clsname = f"{clsname}[{c_size}]"

        return super().__new__(metacls, clsname, bases, ns,
            c_typedef=c_base.c_typedef, c_base=c_base, c_size=c_size, **kwargs)

    def __getitem__(cls, key):
        (c_base, c_size) = key
        return cls.__class__(cls.__name__, (cls,), {},
            c_base=c_base, c_size=c_size)


class Array(Object, tuple, metaclass=ArrayMeta,
        c_base=Object, c_size=...):
    @classmethod
    def c_decl(cls):
        if cls.c_size is Ellipsis:
            size = ""
        else:
            size = f"{len(cls)}"
        yield f"{cls.c_base.c_typedef}[{size}]"

    @classmethod
    def c_var(cls, name, prefix="", suffix=""):
        if cls.c_size is Ellipsis:
            size = ""
        else:
            size = f"{len(cls)}"
        return f"{prefix}{cls.c_base.c_typedef} {name}[{size}]{suffix}"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{{"
        for item in self:
            yield from indent(item.c_value(suffix=","))
        yield f"}}{suffix}"


class Void(Object, c_typedef="void"):
    def c_var(cls, name, prefix="", suffix=""):
        raise NotImplementedError


class EnumMeta(_enum.EnumMeta, ObjectMeta):
    def __call__(cls, clsname, entries,
            c_tag=None, c_typedef=None, exclude=None):
        if exclude is None:
            exclude = frozenset()
        if isinstance(entries, type) and issubclass(entries, _enum.Enum):
            # Use __members__, not __iter__, otherwise aliases are lost.
            entries = dict(entries.__members__)
        if isinstance(entries, dict):
            entries = tuple(entries.items())
        entries = ((key, value) for (key, value) in entries if key not in exclude)

        if c_tag is None:
            c_tag = f"svp64_{clsname.lower()}"
        if c_typedef is None:
            c_typedef = f"enum {c_tag}"

        base = ObjectMeta(cls.__name__, (), {},
            c_tag=c_tag, c_typedef=c_typedef)

        return super().__call__(value=clsname, names=entries, type=base)


class Enum(Object, _enum.Enum, metaclass=EnumMeta):
    @property
    def c_name(self):
        return f"{self.c_tag.upper()}_{self.name.upper()}"

    @classmethod
    def c_decl(cls):
        yield f"{cls.c_typedef} {{"
        for item in cls:
            yield from indent(item.c_value(suffix=","))
        yield f"}};"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self.c_name}{suffix}"

    @classmethod
    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}{cls.c_typedef} {name}{suffix}"


In1Sel = Enum("In1Sel", _In1Sel, c_tag="svp64_in1_sel")
In2Sel = Enum("In2Sel", _In2Sel, c_tag="svp64_in2_sel")
In3Sel = Enum("In3Sel", _In3Sel, c_tag="svp64_in3_sel")
OutSel = Enum("OutSel", _OutSel, c_tag="svp64_out_sel")
CRInSel = Enum("CRInSel", _CRInSel, c_tag="svp64_cr_in_sel")
CRIn2Sel = Enum("CRIn2Sel", _CRIn2Sel, c_tag="svp64_cr_in2_sel")
CROutSel = Enum("CROutSel", _CROutSel, c_tag="svp64_cr_out_sel")
PType = Enum("PType", _SVPtype, c_tag="svp64_ptype")
EType = Enum("EType", _SVEtype, c_tag="svp64_etype", exclude="NONE")
Extra = Enum("Extra", _SVExtra, c_tag="svp64_extra", exclude="Idx_1_2")
Function = Enum("Function", _Function, c_tag="svp64_function")


class Constant(_enum.Enum, metaclass=EnumMeta):
    @classmethod
    def c_decl(cls):
        yield f"/* {cls.c_tag.upper()} constants */"
        # Use __members__, not __iter__, otherwise aliases are lost.
        for (key, item) in cls.__members__.items():
            key = f"{cls.c_tag.upper()}_{key.upper()}"
            value = f"0x{item.value:08x}U"
            yield f"#define {key} {value}"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self.c_tag.upper()}_{self.c_name.upper()}{suffix}"


Mode = Constant("Mode", _SVP64MODE)


class StructMeta(ObjectMeta):
    def __new__(metacls, clsname, bases, ns,
            c_tag=None, c_typedef=None):

        if c_tag is None:
            c_tag = f"svp64_{clsname.lower()}"
        if c_typedef is None:
            c_typedef = f"struct {c_tag}"

        return super().__new__(metacls, clsname, bases, ns,
            c_typedef=c_typedef, c_tag=c_tag)


@_dataclasses.dataclass(eq=True, frozen=True)
class Struct(Object, metaclass=StructMeta):
    @classmethod
    def c_decl(cls):
        def transform(field):
            return field.type.c_var(name=f"{field.name}", suffix=";")

        yield f"{cls.c_typedef} {{"
        yield from indent(map(transform, _dataclasses.fields(cls)))
        yield f"}};"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{{"
        for field in _dataclasses.fields(self):
            name = field.name
            attr = getattr(self, name)
            yield from indent(attr.c_value(prefix=f".{name} = ", suffix=","))
        yield f"}}{suffix}"


class Integer(Object, str):
    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}{self}{suffix}"


class Byte(Integer, c_typedef="uint8_t"):
    pass


class Size(Integer, c_typedef="size_t"):
    pass


class UInt32(Integer, c_typedef="uint32_t"):
    pass


class UInt64(Integer, c_typedef="uint64_t"):
    pass


@_dataclasses.dataclass(eq=True, frozen=True)
class Instruction(Struct, c_tag="svp64_insn"):
    value: UInt64

    @classmethod
    def c_decl(cls):
        def mangle(path, action):
            if path.endswith("]"):
                path = path[:-1]
            for symbol in (".", "[", "]"):
                path = path.replace(symbol, "_")
            if path != "":
                return f"{cls.c_tag}_{action}_{path}"
            else:
                return f"{cls.c_tag}_{action}"

        def getter(path, field):
            yield "static inline uint64_t"
            yield f"{mangle(path, 'get')}(const {cls.c_typedef} *insn)"
            yield "{"
            yield from indent(["uint64_t value = insn->value;"])
            yield from indent(["return ("])
            actions = []
            for (dst, src) in enumerate(reversed(field)):
                src = (64 - (src + 1))
                dst = f"UINT64_C({dst})"
                src = f"UINT64_C({src})"
                action = f"(((value >> {src}) & UINT64_C(1)) << {dst})"
                actions.append(action)
            for action in indent(indent(actions[:-1])):
                yield f"{action} |"
            yield from indent(indent([f"{actions[-1]}"]))
            yield from indent([");"])
            yield "}"
            yield ""

        def setter(path, field):
            mask = ((2 ** 64) - 1)
            for bit in field:
                mask &= ~(1 << (64 - (bit + 1)))
            action = mangle(path, "set")
            yield "static inline void"
            yield f"{mangle(path, 'set')}({cls.c_typedef} *insn, uint64_t value)"
            yield "{"
            yield from indent([f"insn->value &= UINT64_C(0x{mask:016x});"])
            actions = []
            for (src, dst) in enumerate(reversed(field)):
                dst = (64 - (dst + 1))
                dst = f"UINT64_C({dst})"
                src = f"UINT64_C({src})"
                action = f"(((value >> {src}) & UINT64_C(1)) << {dst})"
                actions.append(action)
            yield from indent(["insn->value |= ("])
            for action in indent(indent(actions[:-1])):
                yield f"{action} |"
            yield from indent(indent([f"{actions[-1]}"]))
            yield from indent([");"])
            yield "}"
            yield ""

        yield from super().c_decl()
        yield ""
        for (path, field) in _SVP64Instruction.traverse():
            yield from getter(path, field)
            yield from setter(path, field)


class Name(Object, str, c_typedef="const char *"):
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
    function: Function
    in1: In1Sel
    in2: In2Sel
    in3: In3Sel
    out: OutSel
    out2: OutSel
    cr_in: CRInSel
    cr_in2: CRIn2Sel
    cr_out: CROutSel
    ptype: PType
    etype: EType
    extra_idx_in1: Extra
    extra_idx_in2: Extra
    extra_idx_in3: Extra
    extra_idx_out: Extra
    extra_idx_out2: Extra
    extra_idx_cr_in: Extra
    extra_idx_cr_out: Extra

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
class Opcode(Struct):
    class Value(UInt32):
        def __new__(cls, value):
            if isinstance(value, int):
                value = f"0x{value:08x}"
            return super().__new__(cls, value)

    class Mask(UInt32):
        def __new__(cls, value):
            if isinstance(value, int):
                value = f"0x{value:08x}"
            return super().__new__(cls, value)

    value: Value
    mask: Mask


class Opcodes(Object, c_typedef="const struct svp64_opcode *"):
    def __init__(self, offset):
        self.__offset = offset
        return super().__init__()

    @classmethod
    def c_var(cls, name, prefix="", suffix=""):
        return f"{prefix}{cls.c_typedef}{name}{suffix}"

    @classmethod
    def c_decl(cls):
        yield "const struct svp64_opcode *opcodes;"

    def c_value(self, *, prefix="", suffix="", **kwargs):
        yield f"{prefix}&svp64_opcodes[{self.__offset}]{suffix}"


@_dataclasses.dataclass(eq=True, frozen=True)
class Record(Struct):
    name: Name
    desc: Desc
    opcodes: Opcodes
    nr_opcodes: Size

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented

        return self.name < other.name


class Codegen(_enum.Enum):
    PPC_SVP64_GEN_H = "include/opcode/ppc-svp64-gen.h"
    PPC_SVP64_OPC_GEN_C = "opcodes/ppc-svp64-opc-gen.c"

    def __str__(self):
        return self.value

    def generate(self, opcodes, records):
        def ppc_svp64_h(opcodes, nr_opcodes, records, nr_records):
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
                Mode, Function,
            )
            for enum in enums:
                yield from enum.c_decl()
                yield ""

            for cls in (Instruction, Desc, Opcode, Record):
                yield from cls.c_decl()
                yield ""

            yield opcodes.c_var("svp64_opcodes",
                        prefix="extern const ", suffix=";")
            yield nr_opcodes.c_var("svp64_nr_opcodes",
                        prefix="extern const ", suffix=";")
            yield ""

            yield records.c_var("svp64_records",
                        prefix="extern const ", suffix=";")
            yield nr_records.c_var("svp64_nr_records",
                        prefix="extern const ", suffix=";")
            yield ""

            yield "extern const struct powerpc_pd_reg svp64_regs[];"
            yield Size.c_var("svp64_num_regs", prefix="extern const ", suffix=";")
            yield ""

            yield "#ifdef __cplusplus"
            yield "}"
            yield "#endif"
            yield ""

            yield f"#endif /* {self.name} */"

        def ppc_svp64_opc_c(opcodes, nr_opcodes, records, nr_records):
            disclaimer = DISCLAIMER.format(path=str(self),
                desc="PowerPC opcode list (SVP64 extensions)")
            yield from disclaimer.splitlines()
            yield ""

            yield "#include \"opcode/ppc-svp64.h\""
            yield ""

            def opindex(enum, name, table):
                sep = (max(map(len, list(table.values()) + ["UNUSED"])) + 1)
                c_tag = f"svp64_{enum.__name__.lower()}"
                yield "static inline ppc_opindex_t"
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

            yield opcodes.c_var("svp64_opcodes",
                        prefix="const ", suffix=" = \\")
            yield from opcodes.c_value(prefix="", suffix=";")
            yield ""
            yield nr_opcodes.c_var("svp64_nr_opcodes",
                        prefix="const ", suffix=" = \\")
            yield from indent(nr_opcodes.c_value(suffix=";"))
            yield ""

            yield records.c_var("svp64_records",
                        prefix="const ", suffix=" = \\")
            yield from records.c_value(prefix="", suffix=";")
            yield ""
            yield nr_records.c_var("svp64_nr_records",
                        prefix="const ", suffix=" = \\")
            yield from indent(nr_records.c_value(suffix=";"))
            yield ""

            yield "const struct powerpc_pd_reg svp64_regs[] = {"
            regs = {}
            for (category, count, flags) in sorted((
                        ("r", 128, "PPC_OPERAND_GPR"),
                        ("f", 128, "PPC_OPERAND_FPR"),
                        ("cr", 128, "PPC_OPERAND_CR_REG"),
                    )):
                for index in range(count):
                    regs[f"{category}{index}"] = (index, flags)
                    regs[f"{category}.{index}"] = (index, flags)
            for (name, (index, flags)) in sorted(regs.items()):
                yield from indent([f"{{\"{name}\", {index}, {flags}}},"])
            yield "};"
            yield ""

            num_regs = Size("(sizeof (svp64_regs) / sizeof (svp64_regs[0]))")
            yield Size.c_var("svp64_num_regs",
                        prefix="const ", suffix=" = \\")
            yield from indent(num_regs.c_value(suffix=";"))

        opcodes = Array[Opcode, ...](opcodes)
        nr_opcodes = Size("(sizeof (svp64_opcodes) / sizeof (svp64_opcodes[0]))")

        records = Array[Record, ...](records)
        nr_records = Size("(sizeof (svp64_records) / sizeof (svp64_records[0]))")

        yield from {
            Codegen.PPC_SVP64_GEN_H: ppc_svp64_h,
            Codegen.PPC_SVP64_OPC_GEN_C: ppc_svp64_opc_c,
        }[self](opcodes, nr_opcodes, records, nr_records)


def collect(db):
    opcodes = []
    records = []
    fields = {field.name:field.type for field in _dataclasses.fields(Desc)}

    for insn in filter(lambda insn: insn.svp64 is not None, db):
        desc = {}

        for (key, cls) in fields.items():
            value = getattr(insn, key)

            if (((cls is EType) and (value is _SVEtype.NONE)) or
                    ((cls is Extra) and (value is _SVExtra.Idx_1_2))):
                desc = None
                break

            if issubclass(cls, _enum.Enum):
                value = cls[value.name]
            else:
                value = cls(value)
            desc[key] = value

        if desc is None:
            continue

        name = Name(f"sv.{insn.name}")
        offset = len(opcodes)
        for opcode in insn.opcodes:
            value = Opcode.Value(opcode.value)
            mask = Opcode.Mask(opcode.mask)
            opcode = Opcode(value=value, mask=mask)
            opcodes.append(opcode)
        desc = Desc(**desc)

        record = Record(name=name, desc=desc,
            opcodes=Opcodes(offset), nr_opcodes=Size(len(insn.opcodes)))
        records.append(record)

    return (opcodes, records)


def main(codegen):
    db = _Database(_find_wiki_dir())
    (opcodes, records) = collect(db)
    for line in codegen.generate(opcodes, records):
        print(line)


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("codegen",
        type=Codegen, choices=Codegen,
        help="code generator")

    args = vars(parser.parse_args())
    main(**args)
