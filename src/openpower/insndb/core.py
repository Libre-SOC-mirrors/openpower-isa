import collections as _collections
import contextlib as _contextlib
import csv as _csv
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import inspect as _inspect
import os as _os
import operator as _operator
import pathlib as _pathlib
import re as _re
import types as _types
import typing as _typing

import mdis.dispatcher
import mdis.walker

try:
    from functools import cached_property
except ImportError:
    from cached_property import cached_property

from openpower.decoder.power_enums import (
    Function as _Function,
    MicrOp as _MicrOp,
    In1Sel as _In1Sel,
    In2Sel as _In2Sel,
    In3Sel as _In3Sel,
    OutSel as _OutSel,
    CRInSel as _CRInSel,
    CRIn2Sel as _CRIn2Sel,
    CROutSel as _CROutSel,
    LDSTLen as _LDSTLen,
    LDSTMode as _LDSTMode,
    RCOE as _RCOE,
    CryIn as _CryIn,
    Form as _Form,
    SVEType as _SVEType,
    SVMaskSrc as _SVMaskSrc,
    SVMode as _SVMode,
    SVPType as _SVPType,
    SVExtra as _SVExtra,
    Reg as _Reg,
    RegType as _RegType,
    SelType as _SelType,
    SVP64SubVL as _SVP64SubVL,
    SVP64Pred as _SVP64Pred,
    SVP64PredMode as _SVP64PredMode,
    SVP64Width as _SVP64Width,
)
from openpower.decoder.selectable_int import (
    SelectableInt as _SelectableInt,
    selectconcat as _selectconcat,
)
from openpower.decoder.power_fields import (
    Field as _Field,
    Mapping as _Mapping,
    DecodeFields as _DecodeFields,
)
from openpower.decoder.pseudo.pagereader import ISA as _ISA


class DataclassMeta(type):
    def __new__(metacls, name, bases, ns):
        cls = super().__new__(metacls, name, bases, ns)
        return _dataclasses.dataclass(cls, eq=True, frozen=True)


class Dataclass(metaclass=DataclassMeta):
    pass


@_functools.total_ordering
class Style(_enum.Enum):
    LEGACY = _enum.auto()
    SHORT = _enum.auto()
    NORMAL = _enum.auto()
    VERBOSE = _enum.auto()

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.value < other.value)


def dataclass(cls, record, keymap=None, typemap=None):
    if keymap is None:
        keymap = {}
    if typemap is None:
        typemap = {field.name:field.type for field in _dataclasses.fields(cls)}

    def transform(key_value):
        (key, value) = key_value
        key = keymap.get(key, key)
        hook = typemap.get(key, lambda value: value)
        if hook is bool and value in ("", "0"):
            value = False
        else:
            value = hook(value)
        return (key, value)

    record = dict(map(transform, record.items()))
    for key in frozenset(record.keys()):
        if record[key] == "":
            record.pop(key)

    return cls(**record)


@_functools.total_ordering
class Opcode:
    class Integer(int):
        def __new__(cls, value):
            if isinstance(value, str):
                value = int(value, 0)
            if not isinstance(value, int):
                raise ValueError(value)

            if value.bit_length() > 64:
                raise ValueError(value)

            return super().__new__(cls, value)

        def __str__(self):
            return self.__repr__()

        def __repr__(self):
            return f"{self:0{self.bit_length()}b}"

        def bit_length(self):
            if super().bit_length() > 32:
                return 64
            return 32

    class Value(Integer):
        pass

    class Mask(Integer):
        pass

    def __init__(self, value, mask):
        self.__value = value
        self.__mask = mask
        return super().__init__()

    @property
    def value(self):
        return self.__value

    @property
    def mask(self):
        return self.__mask

    def __lt__(self, other):
        if not isinstance(other, Opcode):
            return NotImplemented
        return ((self.value, self.mask) < (other.value, other.mask))

    def __int__(self):
        return (self.value & self.mask)

    def __index__(self):
        return int(self).__index__()

    def __repr__(self):
        def pattern(value, mask, bit_length):
            for bit in range(bit_length):
                if ((mask & (1 << (bit_length - bit - 1))) == 0):
                    yield "-"
                elif (value & (1 << (bit_length - bit - 1))):
                    yield "1"
                else:
                    yield "0"

        return "".join(pattern(self.value, self.mask, self.value.bit_length()))

    def match(self, key):
        return ((self.value & self.mask) == (key & self.mask))


@_functools.total_ordering
class IntegerOpcode(Opcode):
    def __init__(self, value):
        if value.startswith("0b"):
           mask = int(("1" * len(value[2:])), 2)
        else:
            mask = 0b111111

        value = Opcode.Value(value)
        mask = Opcode.Mask(mask)

        return super().__init__(value=value, mask=mask)


@_functools.total_ordering
class PatternOpcode(Opcode):
    def __init__(self, pattern):
        if not isinstance(pattern, str):
            raise ValueError(pattern)

        (value, mask) = (0, 0)
        for symbol in pattern:
            if symbol not in {"0", "1", "-"}:
                raise ValueError(pattern)
            value |= (symbol == "1")
            mask |= (symbol != "-")
            value <<= 1
            mask <<= 1
        value >>= 1
        mask >>= 1

        value = Opcode.Value(value)
        mask = Opcode.Mask(mask)

        return super().__init__(value=value, mask=mask)


class PPCRecord(Dataclass):
    class FlagsMeta(type):
        def __iter__(cls):
            yield from (
                "inv A",
                "inv out",
                "cry out",
                "BR",
                "sgn ext",
                "rsrv",
                "32b",
                "sgn",
                "lk",
                "sgl pipe",
            )

    class Flags(tuple, metaclass=FlagsMeta):
        def __new__(cls, flags=frozenset()):
            flags = frozenset(flags)
            diff = (flags - frozenset(cls))
            if diff:
                raise ValueError(flags)
            return super().__new__(cls, sorted(flags))

    opcode: Opcode
    comment: str
    flags: Flags = Flags()
    comment2: str = ""
    function: _Function = _Function.NONE
    intop: _MicrOp = _MicrOp.OP_ILLEGAL
    in1: _In1Sel = _In1Sel.NONE
    in2: _In2Sel = _In2Sel.NONE
    in3: _In3Sel = _In3Sel.NONE
    out: _OutSel = _OutSel.NONE
    cr_in: _CRInSel = _CRInSel.NONE
    cr_in2: _CRIn2Sel = _CRIn2Sel.NONE
    cr_out: _CROutSel = _CROutSel.NONE
    cry_in: _CryIn = _CryIn.ZERO
    ldst_len: _LDSTLen = _LDSTLen.NONE
    upd: _LDSTMode = _LDSTMode.NONE
    Rc: _RCOE = _RCOE.NONE
    form: _Form = _Form.NONE
    conditions: str = ""
    unofficial: str = ""

    __KEYMAP = {
        "unit": "function",
        "internal op": "intop",
        "CR in": "cr_in",
        "CR out": "cr_out",
        "cry in": "cry_in",
        "ldst len": "ldst_len",
        "rc": "Rc",
        "CONDITIONS": "conditions",
    }

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        lhs = (self.opcode, self.comment)
        rhs = (other.opcode, other.comment)
        return (lhs < rhs)

    @classmethod
    def CSV(cls, record, opcode_cls):
        typemap = {field.name:field.type for field in _dataclasses.fields(cls)}
        typemap["opcode"] = opcode_cls

        if record["CR in"] == "BA_BB":
            record["cr_in"] = "BA"
            record["cr_in2"] = "BB"
            del record["CR in"]
        elif record["CR in"] == "BA_BFB":
            record["cr_in"] = "BA"
            record["cr_in2"] = "BFB"
            del record["CR in"]

        flags = set()
        for flag in frozenset(PPCRecord.Flags):
            if bool(record.pop(flag, "")):
                flags.add(flag)
        record["flags"] = PPCRecord.Flags(flags)

        return dataclass(cls, record,
            keymap=PPCRecord.__KEYMAP,
            typemap=typemap)

    @cached_property
    def names(self):
        return frozenset(self.comment.split("=")[-1].split("/"))


class PPCMultiRecord(tuple):
    def __getattr__(self, attr):
        if attr == "opcode":
            if len(self) != 1:
                raise AttributeError(attr)
        return getattr(self[0], attr)


class SVP64Record(Dataclass):
    class ExtraMap(tuple):
        class Extra(tuple):
            @_dataclasses.dataclass(eq=True, frozen=True)
            class Entry:
                seltype: _SelType = _SelType.NONE
                reg: _Reg = _Reg.NONE

                def __repr__(self):
                    return f"{self.seltype.value}:{self.reg.name}"

            def __new__(cls, value="0"):
                if isinstance(value, str):
                    def transform(value):
                        (seltype, reg) = value.split(":")
                        seltype = _SelType(seltype)
                        reg = _Reg(reg)
                        return cls.Entry(seltype=seltype, reg=reg)

                    if value == "0":
                        value = tuple()
                    else:
                        value = map(transform, value.split(";"))

                return super().__new__(cls, value)

            def __repr__(self):
                return repr(list(self))

        def __new__(cls, value=tuple()):
            value = tuple(value)
            if len(value) == 0:
                value = (("0",) * 4)
            return super().__new__(cls, map(cls.Extra, value))

        def __repr__(self):
            return repr({index:self[index] for index in range(0, 4)})

    name: str
    ptype: _SVPType = _SVPType.NONE
    etype: _SVEType = _SVEType.NONE
    msrc: _SVMaskSrc = _SVMaskSrc.NO # MASK_SRC is active
    in1: _In1Sel = _In1Sel.NONE
    in2: _In2Sel = _In2Sel.NONE
    in3: _In3Sel = _In3Sel.NONE
    out: _OutSel = _OutSel.NONE
    out2: _OutSel = _OutSel.NONE
    cr_in: _CRInSel = _CRInSel.NONE
    cr_in2: _CRIn2Sel = _CRIn2Sel.NONE
    cr_out: _CROutSel = _CROutSel.NONE
    extra: ExtraMap = ExtraMap()
    conditions: str = ""
    mode: _SVMode = _SVMode.NORMAL

    __KEYMAP = {
        "insn": "name",
        "CONDITIONS": "conditions",
        "Ptype": "ptype",
        "Etype": "etype",
        "SM": "msrc",
        "CR in": "cr_in",
        "CR out": "cr_out",
    }

    @classmethod
    def CSV(cls, record):
        record["insn"] = record["insn"].split("=")[-1]

        for key in frozenset({
                    "in1", "in2", "in3", "CR in",
                    "out", "out2", "CR out",
                }):
            value = record[key]
            if value == "0":
                record[key] = "NONE"

        if record["CR in"] == "BA_BB":
            record["cr_in"] = "BA"
            record["cr_in2"] = "BB"
            del record["CR in"]
        elif record["CR in"] == "BFA_BFB_BF":
            record["cr_in"] = "BFA"
            record["cr_in2"] = "BFB"
            #record["cr_out"] = "BF" # only use BFA_BFB_BF when BF is a dest
            del record["CR in"]
        elif record["CR in"] == "BA_BFB": # maaamma miiiia... enough!
            record["cr_in"] = "BA"
            record["cr_in2"] = "BFB"
            del record["CR in"]

        extra = []
        for idx in range(0, 4):
            extra.append(record.pop(f"{idx}"))

        record["extra"] = cls.ExtraMap(extra)

        return dataclass(cls, record, keymap=cls.__KEYMAP)

    @cached_property
    def extras(self):
        keys = (
            "in1", "in2", "in3", "cr_in", "cr_in2",
            "out", "out2", "cr_out",
        )

        idxmap = (
            _SVExtra.Idx0,
            _SVExtra.Idx1,
            _SVExtra.Idx2,
            _SVExtra.Idx3,
        )

        def extra(reg):
            extras = {
                _SelType.DST: {},
                _SelType.SRC: {},
            }
            for index in range(0, 4):
                for entry in self.extra[index]:
                    extras[entry.seltype][entry.reg] = idxmap[index]

            for (seltype, regs) in extras.items():
                idx = regs.get(reg, _SVExtra.NONE)
                if idx is not _SVExtra.NONE:
                    yield (reg, seltype, idx)

        sels = {}
        idxs = {}
        regs = {}
        seltypes = {}
        for key in keys:
            # has the word "in", it is a SelType.SRC "out" -> DST
            # in1/2/3 and CR in are SRC, and must match only against "s:NN"
            # out/out1 and CR out are DST, and must match only against "d:NN"
            keytype = _SelType.SRC if ("in" in key) else _SelType.DST
            sel = sels[key] = getattr(self, key)
            reg = regs[key] = _Reg(sel)
            seltypes[key] = _SelType.NONE
            idxs[key] = _SVExtra.NONE
            for (reg, seltype, idx) in extra(reg.alias):
                if keytype != seltype: # only check SRC-to-SRC and DST-to-DST
                    continue
                if idx != idxs[key] and idxs[key] is not _SVExtra.NONE:
                    raise ValueError(idx)
                idxs[key] = idx
                regs[key] = reg
                seltypes[key] = seltype

        if sels["cr_in"] is _CRInSel.BA_BB:
            sels["cr_in"] = _CRIn2Sel.BA
            sels["cr_in2"] = _CRIn2Sel.BB
            idxs["cr_in2"] = idxs["cr_in"]
            for key in ("cr_in", "cr_in2"):
                regs[key] = _Reg(sels[key])
                seltype[key] = _SelType.SRC

        if sels["cr_in"] is _CRInSel.BA_BFB:
            sels["cr_in"] = _CRIn2Sel.BA
            sels["cr_in2"] = _CRIn2Sel.BFB
            idxs["cr_in2"] = idxs["cr_in"]
            for key in ("cr_in", "cr_in2"):
                regs[key] = _Reg(sels[key])
                seltype[key] = _SelType.SRC

        # should only be used when BF is also a destination
        if sels["cr_in"] is _CRInSel.BFA_BFB_BF:
            sels["cr_in"] = _CRIn2Sel.BFA
            sels["cr_in2"] = _CRIn2Sel.BFB
            idxs["cr_in2"] = idxs["cr_in"]
            for key in ("cr_in", "cr_in2"):
                regs[key] = _Reg(sels[key])
                seltype[key] = _SelType.SRC

        records = {}
        for key in keys:
            records[key] = {
                "sel": sels[key],
                "reg": regs[key],
                "seltype": seltypes[key],
                "idx": idxs[key],
            }

        return _types.MappingProxyType(records)

    extra_idx_in1 = property(lambda self: self.extras["in1"]["idx"])
    extra_idx_in2 = property(lambda self: self.extras["in2"]["idx"])
    extra_idx_in3 = property(lambda self: self.extras["in3"]["idx"])
    extra_idx_out = property(lambda self: self.extras["out"]["idx"])
    extra_idx_out2 = property(lambda self: self.extras["out2"]["idx"])
    extra_idx_cr_in = property(lambda self: self.extras["cr_in"]["idx"])
    extra_idx_cr_in2 = property(lambda self: self.extras["cr_in2"]["idx"])
    extra_idx_cr_out = property(lambda self: self.extras["cr_out"]["idx"])

    @cached_property
    def extra_CR(self):
        extra = None
        for idx in range(0, 4):
            for entry in self.extra[idx]:
                if entry.seltype is _SelType.DST:
                    if extra is not None:
                        raise ValueError(self.svp64)
                    extra = entry
                    break

        if _RegType(extra.reg) not in (_RegType.CR_3BIT, _RegType.CR_5BIT):
            raise ValueError(self.svp64)

        return extra

    @cached_property
    def extra_CR_3bit(self):
        return (_RegType(self.extra_CR.reg) is _RegType.CR_3BIT)


class Section(Dataclass):
    class Path(type(_pathlib.Path("."))):
        pass

    class BitSel:
        def __init__(self, value=(0, 32)):
            if isinstance(value, str):
                (start, end) = map(int, value.split(":"))
            else:
                (start, end) = value
            if start < 0 or end < 0 or start >= end:
                raise ValueError(value)

            self.__start = start
            self.__end = end

            return super().__init__()

        def __len__(self):
            return (self.__end - self.__start + 1)

        def __repr__(self):
            return f"[{self.__start}:{self.__end}]"

        def __iter__(self):
            yield from range(self.start, (self.end + 1))

        def __reversed__(self):
            return tuple(reversed(tuple(self)))

        @property
        def start(self):
            return self.__start

        @property
        def end(self):
            return self.__end

    class Mode(_enum.Enum):
        INTEGER = _enum.auto()
        PATTERN = _enum.auto()

        @classmethod
        def _missing_(cls, value):
            if isinstance(value, str):
                return cls[value.upper()]
            return super()._missing_(value)

    class Suffix(int):
        def __new__(cls, value=None):
            if isinstance(value, str):
                if value.upper() == "NONE":
                    value = None
                else:
                    value = int(value, 0)
            if value is None:
                value = 0

            return super().__new__(cls, value)

        def __str__(self):
            return repr(self)

        def __repr__(self):
            return (bin(self) if self else "None")

    class Opcode(IntegerOpcode):
        pass

    @_functools.total_ordering
    class Priority(_enum.Enum):
        LOW = -1
        NORMAL = 0
        HIGH = +1

        @classmethod
        def _missing_(cls, value):
            if isinstance(value, str):
                value = value.upper()
            try:
                return cls[value]
            except ValueError:
                return super()._missing_(value)

        def __lt__(self, other):
            if not isinstance(other, self.__class__):
                return NotImplemented

            # NOTE: the order is inversed, LOW < NORMAL < HIGH
            return (self.value > other.value)

    csv: Path
    bitsel: BitSel
    suffix: Suffix
    mode: Mode
    opcode: Opcode = None
    priority: Priority = Priority.NORMAL

    def __lt__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (self.priority < other.priority)

    @classmethod
    def CSV(cls, record):
        keymap = {"path": "csv"}
        typemap = {field.name:field.type for field in _dataclasses.fields(cls)}
        if record["opcode"] == "NONE":
            typemap["opcode"] = lambda _: None

        return dataclass(cls, record, typemap=typemap, keymap=keymap)


class Fields(dict):
    def __init__(self, items):
        if isinstance(items, dict):
            items = items.items()

        def transform(item):
            (name, bitrange) = item
            return (name, tuple(bitrange.values()))

        mapping = dict(map(transform, items))

        return super().__init__(mapping)

    def __hash__(self):
        return hash(tuple(sorted(self.items())))

    def __iter__(self):
        yield from self.__mapping.items()


class Operands(dict):
    __GPR_PAIRS = (
        _Reg.RTp,
        _Reg.RSp,
    )
    __FPR_PAIRS = (
        _Reg.FRAp,
        _Reg.FRBp,
        _Reg.FRSp,
        _Reg.FRTp,
    )

    def __init__(self, insn, operands):
        custom_insns = {
            "b": {"target_addr": TargetAddrOperandLI},
            "ba": {"target_addr": TargetAddrOperandLI},
            "bl": {"target_addr": TargetAddrOperandLI},
            "bla": {"target_addr": TargetAddrOperandLI},
            "bc": {"target_addr": TargetAddrOperandBD},
            "bca": {"target_addr": TargetAddrOperandBD},
            "bcl": {"target_addr": TargetAddrOperandBD},
            "bcla": {"target_addr": TargetAddrOperandBD},
            "addpcis": {"D": DOperandDX},
            "fishmv": {"D": DOperandDX},
            "fmvis": {"D": DOperandDX},
        }
        custom_fields = {
            "SVi": NonZeroOperand,
            "SVd": NonZeroOperand,
            "SVxd": NonZeroOperand,
            "SVyd": NonZeroOperand,
            "SVzd": NonZeroOperand,
            "BD": SignedOperand,
            "D": SignedImmediateOperand,
            "SI": SignedOperand,
            "IB": SignedOperand,
            "LI": SignedOperand,
            "SIM": SignedOperand,
            "SVD": SignedOperand,
            "SVDS": SignedOperand,
            "RSp": GPRPairOperand,
            "RTp": GPRPairOperand,
            "FRAp": FPRPairOperand,
            "FRBp": FPRPairOperand,
            "FRSp": FPRPairOperand,
            "FRTp": FPRPairOperand,
        }
        custom_immediates = {
            "DQ": EXTSOperandDQ,
            "DS": EXTSOperandDS,
        }

        mapping = {}
        for operand in operands:
            cls = DynamicOperand

            if "=" in operand:
                (name, value) = operand.split("=")
                mapping[name] = (StaticOperand, (
                    ("name", name),
                    ("value", int(value)),
                ))
            else:
                name = operand
                if name.endswith(")"):
                    name = name.replace("(", " ").replace(")", "")
                    (imm_name, _, name) = name.partition(" ")
                else:
                    imm_name = None

                if imm_name is not None:
                    imm_cls = custom_immediates.get(imm_name, ImmediateOperand)

                if insn in custom_insns and name in custom_insns[insn]:
                    cls = custom_insns[insn][name]
                elif name in custom_fields:
                    cls = custom_fields[name]
                elif name in _Reg.__members__:
                    reg = _Reg[name]
                    if reg in self.__class__.__GPR_PAIRS:
                        cls = GPRPairOperand
                    elif reg in self.__class__.__FPR_PAIRS:
                        cls = FPRPairOperand
                    else:
                        regtype = _RegType[name]
                        if regtype is _RegType.GPR:
                            cls = GPROperand
                        elif regtype is _RegType.FPR:
                            cls = FPROperand
                        elif regtype is _RegType.CR_3BIT:
                            cls = CR3Operand
                        elif regtype is _RegType.CR_5BIT:
                            cls = CR5Operand

                if imm_name is not None:
                    mapping[imm_name] = (imm_cls, (
                        ("name", imm_name),
                    ))
                mapping[name] = (cls, (
                    ("name", name),
                ))

        return super().__init__(mapping)

    def __iter__(self):
        for (cls, kwargs) in self.values():
            yield (cls, dict(kwargs))

    def __hash__(self):
        return hash(tuple(sorted(self.items())))

    @cached_property
    def static(self):
        return tuple(filter(lambda pair: issubclass(pair[0], StaticOperand), self))

    @cached_property
    def dynamic(self):
        return tuple(filter(lambda pair: issubclass(pair[0], DynamicOperand), self))


class Arguments(tuple):
    def __new__(cls, record, arguments, operands):
        operands = iter(tuple(operands))
        arguments = iter(tuple(arguments))

        items = []
        while True:
            try:
                operand = next(operands)
            except StopIteration:
                break

            try:
                argument = next(arguments)
            except StopIteration:
                raise ValueError("operands count mismatch")

            if isinstance(operand, ImmediateOperand):
                argument = argument.replace("(", " ").replace(")", "")
                (imm_argument, _, argument) = argument.partition(" ")
                try:
                    (imm_operand, operand) = (operand, next(operands))
                except StopIteration:
                    raise ValueError("operands count mismatch")
                items.append((imm_argument, imm_operand))
            items.append((argument, operand))

        try:
            next(arguments)
        except StopIteration:
            pass
        else:
            raise ValueError("operands count mismatch")

        return super().__new__(cls, items)


class PCode(tuple):
    pass


class MarkdownRecord(Dataclass):
    pcode: PCode
    operands: Operands


@_functools.total_ordering
class Record(Dataclass):
    name: str
    section: Section
    ppc: PPCMultiRecord
    fields: Fields
    mdwn: MarkdownRecord
    svp64: SVP64Record = None

    @property
    def extras(self):
        if self.svp64 is not None:
            return self.svp64.extras
        else:
            return _types.MappingProxyType({})

    @property
    def pcode(self):
        return self.mdwn.pcode

    def __lt__(self, other):
        if not isinstance(other, Record):
            return NotImplemented
        lhs = (min(self.opcodes), self.name)
        rhs = (min(other.opcodes), other.name)
        return (lhs < rhs)

    @cached_property
    def operands(self):
        return (self.static_operands + self.dynamic_operands)

    @cached_property
    def static_operands(self):
        operands = []
        operands.append(POStaticOperand(record=self, value=self.PO))
        for ppc in self.ppc:
            operands.append(XOStaticOperand(
                record=self,
                value=ppc.opcode.value,
                span=self.section.bitsel,
            ))
        for (cls, kwargs) in self.mdwn.operands.static:
            operands.append(cls(record=self, **kwargs))
        return tuple(operands)

    @cached_property
    def dynamic_operands(self):
        operands = []
        for (cls, kwargs) in self.mdwn.operands.dynamic:
            operands.append(cls(record=self, **kwargs))
        return tuple(operands)

    @cached_property
    def opcodes(self):
        def binary(mapping):
            return int("".join(str(int(mapping[bit])) \
                       for bit in sorted(mapping)), 2)

        def PO_XO(value, mask, opcode, bits):
            value = dict(value)
            mask = dict(mask)
            for (src, dst) in enumerate(reversed(bits)):
                value[dst] = ((opcode.value & (1 << src)) != 0)
                mask[dst] = ((opcode.mask & (1 << src)) != 0)
            return (value, mask)

        def PO(value, mask, opcode, bits):
            return PO_XO(value=value, mask=mask, opcode=opcode, bits=bits)

        def XO(value, mask, opcode, bits):
            (value, mask) = PO_XO(value=value, mask=mask,
                                  opcode=opcode, bits=bits)
            for (op_cls, op_kwargs) in self.mdwn.operands.static:
                operand = op_cls(record=self, **op_kwargs)
                for (src, dst) in enumerate(reversed(operand.span)):
                    value[dst] = ((operand.value & (1 << src)) != 0)
                    mask[dst] = True
            return (value, mask)

        pairs = []
        value = {bit:False for bit in range(32)}
        mask = {bit:False for bit in range(32)}
        if self.section.opcode is not None:
            (value, mask) = PO(value=value, mask=mask,
                opcode=self.section.opcode, bits=range(0, 6))
        for ppc in self.ppc:
            pairs.append(XO(value=value, mask=mask,
                opcode=ppc.opcode, bits=self.section.bitsel))

        result = []
        for (value, mask) in pairs:
            value = Opcode.Value(binary(value))
            mask = Opcode.Mask(binary(mask))
            result.append(Opcode(value=value, mask=mask))

        return tuple(result)

    @cached_property
    def PO(self):
        opcode = self.section.opcode
        if opcode is None:
            opcode = self.ppc[0].opcode
            if isinstance(opcode, PatternOpcode):
                value = int(opcode.value)
                bits = opcode.value.bit_length()
                return int(_SelectableInt(value=value, bits=bits)[0:6])

        return int(opcode.value)

    @cached_property
    def XO(self):
        return tuple(ppc.opcode for ppc in self.ppc)

    def match(self, key):
        for opcode in self.opcodes:
            if opcode.match(key):
                return True

        return False

    @property
    def mode(self):
        return self.svp64.mode

    @property
    def in1(self):
        return self.ppc.in1

    @property
    def in2(self):
        return self.ppc.in2

    @property
    def in3(self):
        return self.ppc.in3

    @property
    def out(self):
        return self.ppc.out

    @property
    def out2(self):
        if self.svp64 is None:
            return _OutSel.NONE
        return self.ppc.out

    @property
    def cr_in(self):
        return self.ppc.cr_in

    @property
    def cr_in2(self):
        return self.ppc.cr_in2

    @property
    def cr_out(self):
        return self.ppc.cr_out

    ptype = property(lambda self: self.svp64.ptype)
    etype = property(lambda self: self.svp64.etype)

    extra_idx_in1 = property(lambda self: self.svp64.extra_idx_in1)
    extra_idx_in2 = property(lambda self: self.svp64.extra_idx_in2)
    extra_idx_in3 = property(lambda self: self.svp64.extra_idx_in3)
    extra_idx_out = property(lambda self: self.svp64.extra_idx_out)
    extra_idx_out2 = property(lambda self: self.svp64.extra_idx_out2)
    extra_idx_cr_in = property(lambda self: self.svp64.extra_idx_cr_in)
    extra_idx_cr_in2 = property(lambda self: self.svp64.extra_idx_cr_in2)
    extra_idx_cr_out = property(lambda self: self.svp64.extra_idx_cr_out)

    def __contains__(self, key):
        return self.mdwn.operands.__contains__(key)

    def __getitem__(self, key):
        (cls, kwargs) = self.mdwn.operands.__getitem__(key)
        return cls(record=self, **dict(kwargs))

    @cached_property
    def Rc(self):
        if "Rc" not in self:
            return False
        return self["Rc"].value


class Operand:
    def __init__(self, record, name):
        self.__record = record
        self.__name = name

    def __iter__(self):
        yield ("record", self.record)
        yield ("name", self.__name)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"

    @property
    def name(self):
        return self.__name

    @property
    def record(self):
        return self.__record

    @cached_property
    def span(self):
        return self.record.fields[self.name]

    def assemble(self, insn):
        raise NotImplementedError()

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        raise NotImplementedError()


class DynamicOperand(Operand):
    def assemble(self, insn, value):
        span = self.span
        if isinstance(value, str):
            value = int(value, 0)
            if value < 0:
                raise ValueError("signed operands not allowed")
        insn[span] = value

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        span = self.span
        value = insn[span]

        if style >= Style.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value))


class SignedOperand(DynamicOperand):
    def assemble(self, insn, value):
        if isinstance(value, str):
            value = int(value, 0)
        return super().assemble(value=value, insn=insn)

    def assemble(self, insn, value):
        span = self.span
        if isinstance(value, str):
            value = int(value, 0)
        insn[span] = value

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        span = self.span
        value = insn[span].to_signed_int()
        sign = "-" if (value < 0) else ""
        value = abs(value)

        if style >= Style.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{sign}{value}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield f"{sign}{value}"


class StaticOperand(Operand):
    def __init__(self, record, name, value):
        self.__value = value
        return super().__init__(record=record, name=name)

    def __iter__(self):
        yield ("value", self.__value)
        yield from super().__iter__()

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name}, value={self.value})"

    @property
    def value(self):
        return self.__value

    def assemble(self, insn):
        insn[self.span] = self.value

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        span = self.span
        value = insn[span]

        if style >= Style.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value))


class SpanStaticOperand(StaticOperand):
    def __init__(self, record, name, value, span):
        self.__span = tuple(span)
        return super().__init__(record=record, name=name, value=value)

    def __iter__(self):
        yield ("span", self.__span)
        yield from super().__iter__()

    @property
    def span(self):
        return self.__span


class POStaticOperand(SpanStaticOperand):
    def __init__(self, record, value):
        return super().__init__(record=record, name="PO",
                                value=value, span=range(0, 6))

    def __iter__(self):
        for (key, value) in super().__iter__():
            if key not in {"name", "span"}:
                yield (key, value)


class XOStaticOperand(SpanStaticOperand):
    def __init__(self, record, value, span):
        bits = record.section.bitsel
        value = _SelectableInt(value=value, bits=len(bits))
        span = dict(zip(bits, range(len(bits))))
        span_rev = {value:key for (key, value) in span.items()}

        # This part is tricky: we cannot use record.operands,
        # as this code is called by record.static_operands method.
        for (cls, kwargs) in record.mdwn.operands:
            operand = cls(record=record, **kwargs)
            for idx in operand.span:
                rev = span.pop(idx, None)
                if rev is not None:
                    span_rev.pop(rev, None)

        value = int(_selectconcat(*(value[bit] for bit in span.values())))
        span = tuple(span.keys())

        return super().__init__(record=record, name="XO",
                                value=value, span=span)

    def __iter__(self):
        for (key, value) in super().__iter__():
            if key not in {"name"}:
                yield (key, value)


class ImmediateOperand(DynamicOperand):
    pass


class SignedImmediateOperand(SignedOperand, ImmediateOperand):
    pass


class NonZeroOperand(DynamicOperand):
    def assemble(self, insn, value):
        if isinstance(value, str):
            value = int(value, 0)
        if not isinstance(value, int):
            raise ValueError("non-integer operand")
        if value == 0:
            raise ValueError("non-zero operand")
        value -= 1
        return super().assemble(value=value, insn=insn)

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        span = self.span
        value = insn[span]

        if style >= Style.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value) + 1)


class ExtendableOperand(DynamicOperand):
    def sv_spec_enter(self, value, span):
        return (value, span)

    def sv_spec(self, insn):
        vector = False
        span = self.span
        value = insn[span]
        span = tuple(map(str, span))

        if isinstance(insn, SVP64Instruction):
            (origin_value, origin_span) = (value, span)
            (value, span) = self.sv_spec_enter(value=value, span=span)

            for extra_idx in self.extra_idx:
                if self.record.etype is _SVEType.EXTRA3:
                    spec = insn.prefix.rm.extra3[extra_idx]
                elif self.record.etype is _SVEType.EXTRA2:
                    spec = insn.prefix.rm.extra2[extra_idx]
                else:
                    raise ValueError(self.record.etype)

                if spec != 0:
                    vector = bool(spec[0])
                    spec_span = spec.__class__
                    if self.record.etype is _SVEType.EXTRA3:
                        spec_span = tuple(map(str, spec_span[1, 2]))
                        spec = spec[1, 2]
                    elif self.record.etype is _SVEType.EXTRA2:
                        spec_span = tuple(map(str, spec_span[1,]))
                        spec = _SelectableInt(value=spec[1].value, bits=2)
                        if vector:
                            spec <<= 1
                            spec_span = (spec_span + ("{0}",))
                        else:
                            spec_span = (("{0}",) + spec_span)
                    else:
                        raise ValueError(self.record.etype)

                    vector_shift = (2 + (5 - value.bits))
                    scalar_shift = value.bits
                    spec_shift = (5 - value.bits)

                    bits = (len(span) + len(spec_span))
                    value = _SelectableInt(value=value.value, bits=bits)
                    spec = _SelectableInt(value=spec.value, bits=bits)
                    if vector:
                        value = ((value << vector_shift) | (spec << spec_shift))
                        span = (span + spec_span + ((spec_shift * ("{0}",))))
                    else:
                        value = ((spec << scalar_shift) | value)
                        span = ((spec_shift * ("{0}",)) + spec_span + span)

            (value, span) = self.sv_spec_leave(value=value, span=span,
                origin_value=origin_value, origin_span=origin_span)

        return (vector, value, span)

    def sv_spec_leave(self, value, span, origin_value, origin_span):
        return (value, span)

    @property
    def extra_idx(self):
        for (key, record) in self.record.svp64.extras.items():
            if record["reg"].alias is self.extra_reg.alias:
                yield record["idx"]

    @cached_property
    def extra_reg(self):
        return _Reg(self.name)

    def remap(self, value, vector):
        raise NotImplementedError()

    def assemble(self, value, insn, prefix):
        vector = False

        if isinstance(value, str):
            value = value.lower()
            if value.startswith("%"):
                value = value[1:]
            if value.startswith("*"):
                if not isinstance(insn, SVP64Instruction):
                    raise ValueError(value)
                value = value[1:]
                vector = True
            if value.startswith(prefix):
                if (self.extra_reg.or_zero and (value == f"{prefix}0")):
                    raise ValueError(value)
                value = value[len(prefix):]
            value = int(value, 0)

        if isinstance(insn, SVP64Instruction):
            (value, extra) = self.remap(value=value, vector=vector)

            for extra_idx in self.extra_idx:
                if self.record.etype is _SVEType.EXTRA3:
                    insn.prefix.rm.extra3[extra_idx] = extra
                elif self.record.etype is _SVEType.EXTRA2:
                    insn.prefix.rm.extra2[extra_idx] = extra
                else:
                    raise ValueError(self.record.etype)

        return super().assemble(value=value, insn=insn)

    def disassemble(self, insn,
            style=Style.NORMAL, prefix="", indent=""):
        (vector, value, span) = self.sv_spec(insn=insn)

        if (self.extra_reg.or_zero and (value == 0)):
            prefix = ""

        if style >= Style.VERBOSE:
            mode = "vector" if vector else "scalar"
            yield f"{indent}{self.name} ({mode})"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
            if isinstance(insn, SVP64Instruction):
                for extra_idx in frozenset(self.extra_idx):
                    if self.record.etype is _SVEType.NONE:
                        yield f"{indent}{indent}extra[none]"
                    else:
                        etype = repr(self.record.etype).lower()
                        yield f"{indent}{indent}{etype}{extra_idx!r}"
        else:
            vector = "*" if vector else ""
            yield f"{vector}{prefix}{int(value)}"


class SimpleRegisterOperand(ExtendableOperand):
    def remap(self, value, vector):
        if vector:
            extra = (value & 0b11)
            value = (value >> 2)
        else:
            extra = (value >> 5)
            value = (value & 0b11111)

        # now sanity-check. EXTRA3 is ok, EXTRA2 has limits
        # (and shrink to a single bit if ok)
        if self.record.etype is _SVEType.EXTRA2:
            if vector:
                # range is r0-r127 in increments of 2 (r0 r2 ... r126)
                assert (extra & 0b01) == 0, \
                    ("vector field %s cannot fit into EXTRA2" % value)
                extra = (0b10 | (extra >> 1))
            else:
                # range is r0-r63 in increments of 1
                assert (extra >> 1) == 0, \
                    ("scalar GPR %d cannot fit into EXTRA2" % value)
                extra &= 0b01
        elif self.record.etype is _SVEType.EXTRA3:
            if vector:
                # EXTRA3 vector bit needs marking
                extra |= 0b100
        else:
            raise ValueError(self.record.etype)

        return (value, extra)


class GPROperand(SimpleRegisterOperand):
    def assemble(self, insn, value):
        return super().assemble(value=value, insn=insn, prefix="r")

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        prefix = "" if (style <= Style.SHORT) else "r"
        yield from super().disassemble(prefix=prefix, insn=insn,
            style=style, indent=indent)


class GPRPairOperand(GPROperand):
    pass


class FPROperand(SimpleRegisterOperand):
    def assemble(self, insn, value):
        return super().assemble(value=value, insn=insn, prefix="f")

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        prefix = "" if (style <= Style.SHORT) else "f"
        yield from super().disassemble(prefix=prefix, insn=insn,
            style=style, indent=indent)


class FPRPairOperand(FPROperand):
    pass


class ConditionRegisterFieldOperand(ExtendableOperand):
    def pattern(name_pattern):
        (name, pattern) = name_pattern
        return (name, _re.compile(f"^{pattern}$", _re.S))

    CONDS = {
        "lt": 0,
        "gt": 1,
        "eq": 2,
        "so": 3,
        "un": 3,
    }
    CR = r"(?:CR|cr)([0-9]+)"
    N = r"([0-9]+)"
    BIT = rf"({'|'.join(CONDS.keys())})"
    LBIT = fr"{BIT}\s*\+\s*"  # BIT+
    RBIT = fr"\s*\+\s*{BIT}"  # +BIT
    CRN = fr"{CR}\s*\*\s*{N}" # CR*N
    NCR = fr"{N}\s*\*\s*{CR}" # N*CR
    XCR = fr"{CR}\.{BIT}"
    PATTERNS = tuple(map(pattern, (
        ("CR", CR),
        ("XCR", XCR),
        ("CR*N", CRN),
        ("N*CR", NCR),
        ("BIT+CR", (LBIT + CR)),
        ("CR+BIT", (CR + RBIT)),
        ("BIT+CR*N", (LBIT + CRN)),
        ("CR*N+BIT", (CRN + RBIT)),
        ("BIT+N*CR", (LBIT + NCR)),
        ("N*CR+BIT", (NCR + RBIT)),
    )))

    def remap(self, value, vector, regtype):
        # if 5-bit, take out the lower 2 bits (EQ/LT/GT/SO)
        # and reduce the value down to the CR Field number only
        if regtype is _RegType.CR_5BIT:
            subvalue = (value & 0b11)
            value >>= 2

        if self.record.etype is _SVEType.EXTRA2:
            # very reduced range
            if vector:
                # vector range is CR0-CR120 in increments of 8
                assert value % 8 == 0, "vector CR cannot fit into EXTRA2"
                extra = 0b10 | ((value>>3)&0b1)
                value >>= 4
            else:
                # scalar range is CR0-CR15 in increments of 1
                assert value < 16, "scalar CR cannot fit into EXTRA2"
                extra = (value >> 4)
                value &= 0b1111
        elif self.record.etype is _SVEType.EXTRA3:
            if vector:
                # vector range is CR0-CR124 in increments of 4
                assert value % 4 == 0, "vector CR cannot fit into EXTRA3"
                extra = 0b100 | ((value>>2)&0b1)
                value >>= 3
            else:
                # scalar range is CR0-CR31 in increments of 1
                assert value < 32, "scalar CR cannot fit into EXTRA3"
                extra = (value >> 3)
                value &= 0b111

        # if 5-bit, restore the 2 lower 2 bits
        if regtype is _RegType.CR_5BIT:
            value = ((value << 2) | subvalue)

        return (value, extra)

    def assemble(self, insn, value):
        if isinstance(value, str):
            vector = False

            if value.startswith("*"):
                if not isinstance(insn, SVP64Instruction):
                    raise ValueError(value)
                value = value[1:]
                vector = True

            for (name, pattern) in reversed(self.__class__.PATTERNS):
                match = pattern.match(value)
                if match is not None:
                    keys = name.replace("+", "_").replace("*", "_").split("_")
                    values = match.groups()
                    match = dict(zip(keys, values))
                    CR = int(match["CR"])
                    if name == "XCR":
                        N = 4
                    else:
                        N = int(match.get("N", "1"))
                    BIT = self.__class__.CONDS[match.get("BIT", "lt")]
                    value = ((CR * N) + BIT)
                    break

            value = str(value)
            if vector:
                value = f"*{value}"

        return super().assemble(value=value, insn=insn, prefix="cr")

    def disassemble(self, insn,
            style=Style.NORMAL, prefix="", indent=""):
        (vector, value, span) = self.sv_spec(insn=insn)

        if style >= Style.VERBOSE:
            mode = "vector" if vector else "scalar"
            yield f"{indent}{self.name} ({mode})"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
            if isinstance(insn, SVP64Instruction):
                for extra_idx in frozenset(self.extra_idx):
                    if self.record.etype is _SVEType.NONE:
                        yield f"{indent}{indent}extra[none]"
                    else:
                        etype = repr(self.record.etype).lower()
                        yield f"{indent}{indent}{etype}{extra_idx!r}"
        else:
            vector = "*" if vector else ""
            CR = int(value >> 2)
            CC = int(value & 3)
            cond = ("lt", "gt", "eq", "so")[CC]
            if style >= Style.NORMAL:
                if CR != 0:
                    if isinstance(insn, SVP64Instruction):
                        yield f"{vector}cr{CR}.{cond}"
                    else:
                        yield f"4*cr{CR}+{cond}"
                else:
                    yield cond
            else:
                yield f"{vector}{prefix}{int(value)}"


class CR3Operand(ConditionRegisterFieldOperand):
    def remap(self, value, vector):
        return super().remap(value=value, vector=vector,
            regtype=_RegType.CR_3BIT)


class CR5Operand(ConditionRegisterFieldOperand):
    def remap(self, value, vector):
        return super().remap(value=value, vector=vector,
            regtype=_RegType.CR_5BIT)

    def sv_spec_enter(self, value, span):
        value = _SelectableInt(value=(value.value >> 2), bits=3)
        return (value, span)

    def sv_spec_leave(self, value, span, origin_value, origin_span):
        value = _selectconcat(value, origin_value[3:5])
        span += origin_span
        return (value, span)


class EXTSOperand(SignedOperand):
    field: str # real name to report
    nz: int = 0 # number of zeros
    fmt: str = "d" # integer formatter

    def __init__(self, record, name, field, nz=0, fmt="d"):
        self.__field = field
        self.__nz = nz
        self.__fmt = fmt
        return super().__init__(record=record, name=name)

    @property
    def field(self):
        return self.__field

    @property
    def nz(self):
        return self.__nz

    @property
    def fmt(self):
        return self.__fmt

    @cached_property
    def span(self):
        return self.record.fields[self.field]

    def assemble(self, insn, value):
        span = self.span
        if isinstance(value, str):
            value = int(value, 0)
        insn[span] = (value >> self.nz)

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        span = self.span
        value = insn[span].to_signed_int()
        sign = "-" if (value < 0) else ""
        value = (abs(value) << self.nz)

        if style >= Style.VERBOSE:
            span = (tuple(map(str, span)) + (("{0}",) * self.nz))
            zeros = ("0" * self.nz)
            hint = f"{self.name} = EXTS({self.field} || {zeros})"
            yield f"{indent * 1}{hint}"
            yield f"{indent * 2}{self.field}"
            yield f"{indent * 3}{sign}{value:{self.fmt}}"
            yield f"{indent * 3}{', '.join(span)}"
        else:
            yield f"{sign}{value:{self.fmt}}"


class TargetAddrOperand(EXTSOperand):
    def __init__(self, record, name, field):
        return super().__init__(record=record, name=name, field=field,
                                nz=2, fmt="#x")


class TargetAddrOperandLI(TargetAddrOperand):
    def __init__(self, record, name):
        return super().__init__(record=record, name=name, field="LI")


class TargetAddrOperandBD(TargetAddrOperand):
    def __init__(self, record, name):
        return super().__init__(record=record, name=name, field="BD")


class EXTSOperandDS(EXTSOperand, ImmediateOperand):
    def __init__(self, record, name):
        return super().__init__(record=record, name=name, field="DS", nz=2)


class EXTSOperandDQ(EXTSOperand, ImmediateOperand):
    def __init__(self, record, name):
        return super().__init__(record=record, name=name, field="DQ", nz=4)


class DOperandDX(SignedOperand):
    @cached_property
    def span(self):
        cls = lambda name: DynamicOperand(record=self.record, name=name)
        operands = map(cls, ("d0", "d1", "d2"))
        spans = map(lambda operand: operand.span, operands)
        return sum(spans, tuple())

    def disassemble(self, insn,
            style=Style.NORMAL, indent=""):
        span = self.span
        value = insn[span].to_signed_int()
        sign = "-" if (value < 0) else ""
        value = abs(value)

        if style >= Style.VERBOSE:
            yield f"{indent}D"
            mapping = {
                "d0": "[0:9]",
                "d1": "[10:15]",
                "d2": "[16]",
            }
            for (subname, subspan) in mapping.items():
                operand = DynamicOperand(name=subname)
                span = operand.span
                span = map(str, span)
                yield f"{indent}{indent}{operand.name} = D{subspan}"
                yield f"{indent}{indent}{indent}{sign}{value}"
                yield f"{indent}{indent}{indent}{', '.join(span)}"
        else:
            yield f"{sign}{value}"


class Instruction(_Mapping):
    @classmethod
    def integer(cls, value=0, bits=None, byteorder="little"):
        if isinstance(value, (int, bytes)) and not isinstance(bits, int):
            raise ValueError(bits)

        if isinstance(value, bytes):
            if ((len(value) * 8) != bits):
                raise ValueError(f"bit length mismatch")
            value = int.from_bytes(value, byteorder=byteorder)

        if isinstance(value, int):
            value = _SelectableInt(value=value, bits=bits)
        elif isinstance(value, Instruction):
            value = value.storage

        if not isinstance(value, _SelectableInt):
            raise ValueError(value)
        if bits is None:
            bits = len(cls)
        if len(value) != bits:
            raise ValueError(value)

        value = _SelectableInt(value=value, bits=bits)

        return cls(storage=value)

    def __hash__(self):
        return hash(int(self))

    def __getitem__(self, key):
        return self.storage.__getitem__(key)

    def __setitem__(self, key, value):
        return self.storage.__setitem__(key, value)

    def bytes(self, byteorder="little"):
        nr_bytes = (len(self.__class__) // 8)
        return int(self).to_bytes(nr_bytes, byteorder=byteorder)

    @classmethod
    def record(cls, db, entry):
        record = db[entry]
        if record is None:
            raise KeyError(entry)
        return record

    @classmethod
    def operands(cls, record):
        yield from record.operands

    @classmethod
    def static_operands(cls, record):
        return filter(lambda operand: isinstance(operand, StaticOperand),
            cls.operands(record=record))

    @classmethod
    def dynamic_operands(cls, record):
        return filter(lambda operand: isinstance(operand, DynamicOperand),
            cls.operands(record=record))

    def spec(self, record, prefix):
        dynamic_operands = tuple(map(_operator.itemgetter(0),
            self.spec_dynamic_operands(record=record)))

        static_operands = []
        for (name, value) in self.spec_static_operands(record=record):
            static_operands.append(f"{name}={value}")

        operands = ""
        if dynamic_operands:
            operands += " "
            operands += ",".join(dynamic_operands)
        if static_operands:
            operands += " "
            operands += " ".join(static_operands)

        return f"{prefix}{record.name}{operands}"

    def spec_static_operands(self, record):
        for operand in self.static_operands(record=record):
            if not isinstance(operand, (POStaticOperand, XOStaticOperand)):
                yield (operand.name, operand.value)

    def spec_dynamic_operands(self, record, style=Style.NORMAL):
        imm = False
        imm_name = ""
        imm_value = ""
        for operand in self.dynamic_operands(record=record):
            name = operand.name
            value = " ".join(operand.disassemble(insn=self,
                style=min(style, Style.NORMAL)))
            if imm:
                name = f"{imm_name}({name})"
                value = f"{imm_value}({value})"
                imm = False
            if isinstance(operand, ImmediateOperand):
                imm_name = name
                imm_value = value
                imm = True
            if not imm:
                yield (name, value)

    @classmethod
    def assemble(cls, record, arguments=None):
        if arguments is None:
            arguments = ()

        insn = cls.integer(value=0)

        for operand in cls.static_operands(record=record):
            operand.assemble(insn=insn)

        arguments = Arguments(record=record,
            arguments=arguments, operands=cls.dynamic_operands(record=record))
        for (value, operand) in arguments:
            operand.assemble(insn=insn, value=value)

        return insn

    def disassemble(self, record,
            byteorder="little",
            style=Style.NORMAL):
        raise NotImplementedError()


class WordInstruction(Instruction):
    _: _Field = range(0, 32)
    PO: _Field = range(0, 6)

    @classmethod
    def integer(cls, value, byteorder="little"):
        return super().integer(bits=32, value=value, byteorder=byteorder)

    @property
    def binary(self):
        bits = []
        for idx in range(32):
            bit = int(self[idx])
            bits.append(bit)
        return "".join(map(str, bits))

    def disassemble(self, record,
            byteorder="little",
            style=Style.NORMAL):
        if style <= Style.SHORT:
            blob = ""
        else:
            blob = self.bytes(byteorder=byteorder)
            blob = " ".join(map(lambda byte: f"{byte:02x}", blob))
            blob += "    "

        if record is None:
            yield f"{blob}.long 0x{int(self):08x}"
            return

        # awful temporary hack: workaround for ld-update
        # https://bugs.libre-soc.org/show_bug.cgi?id=1056#c2
        # XXX TODO must check that *EXTENDED* RA != extended-RT
        if (record.svp64 is not None and
           record.mode == _SVMode.LDST_IMM and
           'u' in record.name):
            yield f"{blob}.long 0x{int(self):08x}"
            return

        paired = False
        if style is Style.LEGACY:
            paired = False
            for operand in self.dynamic_operands(record=record):
                if isinstance(operand, (GPRPairOperand, FPRPairOperand)):
                    paired = True

        # unofficial == "0" means an official instruction that needs .long
        if style is Style.LEGACY and (paired or record.ppc.unofficial != ""):
            yield f"{blob}.long 0x{int(self):08x}"
        else:
            operands = tuple(map(_operator.itemgetter(1),
                self.spec_dynamic_operands(record=record, style=style)))
            if operands:
                operands = ",".join(operands)
                yield f"{blob}{record.name} {operands}"
            else:
                yield f"{blob}{record.name}"

        if style >= Style.VERBOSE:
            indent = (" " * 4)
            binary = self.binary
            spec = self.spec(record=record, prefix="")
            yield f"{indent}spec"
            yield f"{indent}{indent}{spec}"
            yield f"{indent}pcode"
            for stmt in record.mdwn.pcode:
                yield f"{indent}{indent}{stmt}"
            yield f"{indent}binary"
            yield f"{indent}{indent}[0:8]   {binary[0:8]}"
            yield f"{indent}{indent}[8:16]  {binary[8:16]}"
            yield f"{indent}{indent}[16:24] {binary[16:24]}"
            yield f"{indent}{indent}[24:32] {binary[24:32]}"
            yield f"{indent}opcodes"
            for opcode in record.opcodes:
                yield f"{indent}{indent}{opcode!r}"
            for operand in self.operands(record=record):
                yield from operand.disassemble(insn=self,
                    style=style, indent=indent)
            yield ""


class PrefixedInstruction(Instruction):
    class Prefix(WordInstruction.remap(range(0, 32))):
        pass

    class Suffix(WordInstruction.remap(range(32, 64))):
        pass

    _: _Field = range(64)
    prefix: Prefix
    suffix: Suffix
    PO: Suffix.PO

    @classmethod
    def integer(cls, value, byteorder="little"):
        return super().integer(bits=64, value=value, byteorder=byteorder)

    @classmethod
    def pair(cls, prefix=0, suffix=0, byteorder="little"):
        def transform(value):
            return WordInstruction.integer(value=value,
                byteorder=byteorder)[0:32]

        (prefix, suffix) = map(transform, (prefix, suffix))
        value = _selectconcat(prefix, suffix)

        return super().integer(bits=64, value=value)


class Mode(_Mapping):
    _: _Field = range(0, 5)
    sel: _Field = (0, 1)


class ExtraRM(_Mapping):
    _: _Field = range(0, 9)


class Extra2RM(ExtraRM):
    idx0: _Field = range(0, 2)
    idx1: _Field = range(2, 4)
    idx2: _Field = range(4, 6)
    idx3: _Field = range(6, 8)

    def __getitem__(self, key):
        return {
            0: self.idx0,
            1: self.idx1,
            2: self.idx2,
            3: self.idx3,
            _SVExtra.Idx0: self.idx0,
            _SVExtra.Idx1: self.idx1,
            _SVExtra.Idx2: self.idx2,
            _SVExtra.Idx3: self.idx3,
        }[key]

    def __setitem__(self, key, value):
        self[key].assign(value)


class Extra3RM(ExtraRM):
    idx0: _Field = range(0, 3)
    idx1: _Field = range(3, 6)
    idx2: _Field = range(6, 9)

    def __getitem__(self, key):
        return {
            0: self.idx0,
            1: self.idx1,
            2: self.idx2,
            _SVExtra.Idx0: self.idx0,
            _SVExtra.Idx1: self.idx1,
            _SVExtra.Idx2: self.idx2,
        }[key]

    def __setitem__(self, key, value):
        self[key].assign(value)


class BaseRM(_Mapping):
    _: _Field = range(24)
    mmode: _Field = (0,)
    mask: _Field = range(1, 4)
    elwidth: _Field = range(4, 6)
    ewsrc: _Field = range(6, 8)
    subvl: _Field = range(8, 10)
    mode: Mode.remap(range(19, 24))
    smask_extra322: _Field = (6,7,18,) # LDST_IDX is EXTRA332
    smask: _Field = range(16, 19)      # everything else use this
    extra: ExtraRM.remap(range(10, 19))
    extra2: Extra2RM.remap(range(10, 19))
    extra3: Extra3RM.remap(range(10, 19))
    # XXX extra332 = (extra3[0], extra3[1], extra2[3])

    def specifiers(self, record):
        subvl = int(self.subvl)
        if subvl > 0:
            yield {
                1: "vec2",
                2: "vec3",
                3: "vec4",
            }[subvl]

    def disassemble(self, style=Style.NORMAL):
        if style >= Style.VERBOSE:
            indent = (" " * 4)
            for (name, span) in self.traverse(path="RM"):
                value = self.storage[span]
                yield f"{name}"
                yield f"{indent}{int(value):0{value.bits}b}"
                yield f"{indent}{', '.join(map(str, span))}"


class FFRc1BaseRM(BaseRM):
    def specifiers(self, record, mode):
        inv = _SelectableInt(value=int(self.inv), bits=1)
        CR = _SelectableInt(value=int(self.CR), bits=2)
        mask = int(_selectconcat(CR, inv))
        predicate = PredicateBaseRM.predicate(True, mask)
        yield f"{mode}={predicate}"

        yield from super().specifiers(record=record)


class FFRc0BaseRM(BaseRM):
    def specifiers(self, record, mode):
        if self.RC1:
            inv = "~" if self.inv else ""
            yield f"{mode}={inv}RC1"

        yield from super().specifiers(record=record)


class SatBaseRM(BaseRM):
    def specifiers(self, record):
        if self.N:
            yield "sats"
        else:
            yield "satu"

        yield from super().specifiers(record=record)


class ZZBaseRM(BaseRM):
    def specifiers(self, record):
        if self.zz:
            yield "zz"

        yield from super().specifiers(record=record)


class ZZCombinedBaseRM(BaseRM):
    def specifiers(self, record):
        if self.sz and self.dz:
            yield "zz"
        elif self.sz:
            yield "sz"
        elif self.dz:
            yield "dz"

        yield from super().specifiers(record=record)


class DZBaseRM(BaseRM):
    def specifiers(self, record):
        if self.dz:
            yield "dz"

        yield from super().specifiers(record=record)


class SZBaseRM(BaseRM):
    def specifiers(self, record):
        if self.sz:
            yield "sz"

        yield from super().specifiers(record=record)


class MRBaseRM(BaseRM):
    def specifiers(self, record):
        if self.RG:
            yield "mrr"
        else:
            yield "mr"

        yield from super().specifiers(record=record)


class ElsBaseRM(BaseRM):
    def specifiers(self, record):
        if self.els:
            yield "els"

        yield from super().specifiers(record=record)


class WidthBaseRM(BaseRM):
    @staticmethod
    def width(FP, width):
        width = {
            0b11: "8",
            0b10: "16",
            0b01: "32",
        }.get(width)
        if width is None:
            return None
        if FP:
            width = ("fp" + width)
        return width

    def specifiers(self, record):
        # elwidths: use "w=" if same otherwise dw/sw
        # FIXME this should consider FP instructions
        FP = False
        dw = WidthBaseRM.width(FP, int(self.elwidth))
        sw = WidthBaseRM.width(FP, int(self.ewsrc))
        if record.svp64.mode is _SVMode.CROP:
            if dw:
                yield ("dw=" + dw)
        else:
            sw = WidthBaseRM.width(FP, int(self.ewsrc))
        if dw == sw and dw:
            yield ("w=" + dw)
        else:
            if dw:
                yield ("dw=" + dw)
            if sw:
                yield ("sw=" + sw)

        yield from super().specifiers(record=record)


class PredicateBaseRM(BaseRM):
    @staticmethod
    def predicate(CR, mask):
        return {
            # integer
            (False, 0b001): "1<<r3",
            (False, 0b010): "r3",
            (False, 0b011): "~r3",
            (False, 0b100): "r10",
            (False, 0b101): "~r10",
            (False, 0b110): "r30",
            (False, 0b111): "~r30",
            # CRs
            (True, 0b000): "lt",
            (True, 0b001): "ge",
            (True, 0b010): "gt",
            (True, 0b011): "le",
            (True, 0b100): "eq",
            (True, 0b101): "ne",
            (True, 0b110): "so",
            (True, 0b111): "ns",
        }.get((CR, mask))

    def specifiers(self, record):
        # predication - single and twin
        # use "m=" if same otherwise sm/dm
        CR = (int(self.mmode) == 1)
        mask = int(self.mask)
        sm = dm = PredicateBaseRM.predicate(CR, mask)
        if record.svp64.ptype is _SVPType.P2:
            # LDST_IDX smask moving to extra322 but not straight away (False)
            if False and record.svp64.mode is _SVMode.LDST_IDX:
                smask = int(self.smask_extra332)
            else:
                smask = int(self.smask)
            sm = PredicateBaseRM.predicate(CR, smask)
        if sm == dm and dm:
            yield ("m=" + dm)
        else:
            if sm:
                yield ("sm=" + sm)
            if dm:
                yield ("dm=" + dm)

        yield from super().specifiers(record=record)


class PredicateWidthBaseRM(WidthBaseRM, PredicateBaseRM):
    pass


class SEABaseRM(BaseRM):
    def specifiers(self, record):
        if self.SEA:
            yield "sea"

        yield from super().specifiers(record=record)


class VLiBaseRM(BaseRM):
    def specifiers(self, record):
        if self.VLi:
            yield "vli"

        yield from super().specifiers(record=record)


class NormalBaseRM(PredicateWidthBaseRM):
    """
    Normal mode
    https://libre-soc.org/openpower/sv/normal/
    """
    pass


class NormalSimpleRM(ZZCombinedBaseRM, NormalBaseRM):
    """normal: simple mode"""
    dz: BaseRM.mode[3]
    sz: BaseRM.mode[4]

    def specifiers(self, record):
        yield from super().specifiers(record=record)


class NormalMRRM(MRBaseRM, NormalBaseRM):
    """normal: scalar reduce mode (mapreduce), SUBVL=1"""
    RG: BaseRM.mode[4]


class NormalFFRc1RM(FFRc1BaseRM, VLiBaseRM, NormalBaseRM):
    """normal: Rc=1: ffirst CR sel"""
    VLi: BaseRM.mode[0]
    inv: BaseRM.mode[2]
    CR: BaseRM.mode[3, 4]

    def specifiers(self, record):
        yield from super().specifiers(record=record, mode="ff")


class NormalFFRc0RM(FFRc0BaseRM, VLiBaseRM, NormalBaseRM):
    """normal: Rc=0: ffirst z/nonz"""
    VLi: BaseRM.mode[0]
    inv: BaseRM.mode[2]
    RC1: BaseRM.mode[4]

    def specifiers(self, record):
        yield from super().specifiers(record=record, mode="ff")


class NormalSatRM(SatBaseRM, ZZCombinedBaseRM, NormalBaseRM):
    """normal: sat mode: N=0/1 u/s, SUBVL=1"""
    N: BaseRM.mode[2]
    dz: BaseRM.mode[3]
    sz: BaseRM.mode[4]


class NormalRM(NormalBaseRM):
    simple: NormalSimpleRM
    mr: NormalMRRM
    ffrc1: NormalFFRc1RM
    ffrc0: NormalFFRc0RM
    sat: NormalSatRM


class LDSTImmBaseRM(PredicateWidthBaseRM):
    """
    LD/ST Immediate mode
    https://libre-soc.org/openpower/sv/ldst/
    """
    pass


class LDSTImmSimpleRM(ElsBaseRM, ZZBaseRM, LDSTImmBaseRM):
    """ld/st immediate: simple mode"""
    pi: BaseRM.mode[2]  # Post-Increment Mode
    lf: BaseRM.mode[4]  # Fault-First Mode (not *Data-Dependent* Fail-First)
    zz: BaseRM.mode[3]
    els: BaseRM.mode[0]
    dz: BaseRM.mode[3]
    sz: BaseRM.mode[3]

    def specifiers(self, record):
        if self.pi:
            yield "pi"
        if self.lf:
            yield "lf"

        yield from super().specifiers(record=record)


class LDSTFFRc1RM(FFRc1BaseRM, VLiBaseRM, LDSTImmBaseRM):
    """ld/st immediate&indexed: Rc=1: ffirst CR sel"""
    VLi: BaseRM.mode[0]
    inv: BaseRM.mode[2]
    CR: BaseRM.mode[3, 4]

    def specifiers(self, record):
        yield from super().specifiers(record=record, mode="ff")


class LDSTFFRc0RM(FFRc0BaseRM, VLiBaseRM, LDSTImmBaseRM):
    """ld/st immediate&indexed: Rc=0: ffirst z/nonz"""
    VLi: BaseRM.mode[0]
    inv: BaseRM.mode[2]
    RC1: BaseRM.mode[4]

    def specifiers(self, record):
        yield from super().specifiers(record=record, mode="ff")


class LDSTImmRM(LDSTImmBaseRM):
    simple: LDSTImmSimpleRM
    ffrc1: LDSTFFRc1RM
    ffrc0: LDSTFFRc0RM


class LDSTIdxBaseRM(PredicateWidthBaseRM):
    """
    LD/ST Indexed mode
    https://libre-soc.org/openpower/sv/ldst/
    """
    pass


class LDSTIdxSimpleRM(SEABaseRM, ZZBaseRM, LDSTIdxBaseRM):
    """ld/st index: simple mode (includes element-strided and Signed-EA)"""
    pi: BaseRM.mode[2]  # Post-Increment Mode
    els: BaseRM.mode[0]
    SEA: BaseRM.mode[4]
    zz: BaseRM.mode[3]
    dz: BaseRM.mode[3]
    sz: BaseRM.mode[3]

    def specifiers(self, record):
        if self.els:
            yield "els"
        if self.pi:
            yield "pi"

        yield from super().specifiers(record=record)


class LDSTIdxRM(LDSTIdxBaseRM):
    simple: LDSTIdxSimpleRM
    ffrc1: LDSTFFRc1RM
    ffrc0: LDSTFFRc0RM



class CROpBaseRM(BaseRM):
    """
    CR ops mode
    https://libre-soc.org/openpower/sv/cr_ops/
    """
    SNZ: BaseRM[7]


class CROpSimpleRM(PredicateBaseRM, ZZCombinedBaseRM, CROpBaseRM):
    """crop: simple mode"""
    RG: BaseRM[21]
    dz: BaseRM[22]
    sz: BaseRM[23]

    def specifiers(self, record):
        if self.RG:
            yield "rg" # simple CR Mode reports /rg

        yield from super().specifiers(record=record)


class CROpMRRM(MRBaseRM, ZZCombinedBaseRM, CROpBaseRM):
    """crop: scalar reduce mode (mapreduce)"""
    RG: BaseRM[21]
    dz: BaseRM[22]
    sz: BaseRM[23]


class CROpFF5RM(FFRc0BaseRM, PredicateBaseRM, VLiBaseRM, DZBaseRM,
                SZBaseRM, CROpBaseRM):
    """crop: ffirst 5-bit mode"""
    VLi: BaseRM[19]
    RC1 = 1
    inv: BaseRM[21]
    dz: BaseRM[22]
    sz: BaseRM[23]

    def specifiers(self, record):
        yield from super().specifiers(record=record, mode="ff")


# FIXME: almost everything in this class contradicts the specs (it doesn't)
# The modes however are swapped: 5-bit is 3-bit, 3-bit is 5-bit
class CROpFF3RM(FFRc1BaseRM, PredicateBaseRM, VLiBaseRM, ZZBaseRM, CROpBaseRM):
    """cr_op: ffirst 3-bit mode"""
    VLi: BaseRM[19]
    inv: BaseRM[21]
    CR: BaseRM[22, 23]
    zz: BaseRM[6]

    def specifiers(self, record):
        yield from super().specifiers(record=record, mode="ff")


class CROpRM(CROpBaseRM):
    simple: CROpSimpleRM
    mr: CROpMRRM
    ff3: CROpFF3RM
    ff5: CROpFF5RM


# ********************
# Branches mode
# https://libre-soc.org/openpower/sv/branches/
class BranchBaseRM(BaseRM):
    ALL: BaseRM[4]
    SNZ: BaseRM[5]
    SL: BaseRM[17]
    SLu: BaseRM[18]
    LRu: BaseRM[22]
    sz: BaseRM[23]
    CTR: BaseRM[19]
    VLS: BaseRM[20]

    def specifiers(self, record):
        if self.ALL:
            yield "all"

        # /sz
        #   branch.sz=1
        #   branch.snz=0
        # /snz
        #   branch.sz=1
        #   branch.snz=1
        if self.SNZ:
            if not self.sz:
                raise ValueError(self.sz)
            yield "snz"
        elif self.sz:
            yield "sz"

        if self.SL:
            yield "sl"
        if self.SLu:
            yield "slu"
        if self.LRu:
            yield "lru"

        # Branch modes lack source mask.
        # Therefore a custom code is needed.
        CR = (int(self.mmode) == 1)
        mask = int(self.mask)
        m = PredicateBaseRM.predicate(CR, mask)
        if m is not None:
            yield ("m=" + m)

        yield from super().specifiers(record=record)


class BranchSimpleRM(BranchBaseRM):
    """branch: simple mode"""
    pass


class BranchVLSRM(BranchBaseRM):
    """branch: VLSET mode"""
    VSb: BaseRM[7]
    VLi: BaseRM[21]

    def specifiers(self, record):
        yield {
            (0b0, 0b0): "vs",
            (0b0, 0b1): "vsi",
            (0b1, 0b0): "vsb",
            (0b1, 0b1): "vsbi",
        }[int(self.VSb), int(self.VLi)]

        yield from super().specifiers(record=record)


class BranchCTRRM(BranchBaseRM):
    """branch: CTR-test mode"""
    CTi: BaseRM[6]

    def specifiers(self, record):
        if self.CTi:
            yield "cti"
        else:
            yield "ctr"

        yield from super().specifiers(record=record)


class BranchCTRVLSRM(BranchVLSRM, BranchCTRRM):
    """branch: CTR-test+VLSET mode"""
    pass


class BranchRM(BranchBaseRM):
    simple: BranchSimpleRM
    vls: BranchVLSRM
    ctr: BranchCTRRM
    ctrvls: BranchCTRVLSRM


class RM(BaseRM):
    normal: NormalRM
    ldst_imm: LDSTImmRM
    ldst_idx: LDSTIdxRM
    crop: CROpRM
    branch: BranchRM


@_dataclasses.dataclass(eq=True, frozen=True)
class Specifier:
    record: Record

    @classmethod
    def match(cls, desc, record):
        raise NotImplementedError()

    def validate(self, others):
        pass

    def assemble(self, insn):
        raise NotImplementedError()


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierWidth(Specifier):
    width: _SVP64Width

    @classmethod
    def match(cls, desc, record, etalon):
        (mode, _, value) = desc.partition("=")
        mode = mode.strip()
        value = value.strip()
        if mode != etalon:
            return None
        width = _SVP64Width(value)

        return cls(record=record, width=width)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierW(SpecifierWidth):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, etalon="w")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        if self.record.svp64.mode is not _SVMode.CROP:
            selector.ewsrc = self.width.value
        selector.elwidth = self.width.value


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSW(SpecifierWidth):
    @classmethod
    def match(cls, desc, record):
        if record.svp64.mode is _SVMode.CROP:
            return None
        return super().match(desc=desc, record=record, etalon="sw")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.ewsrc = self.width.value


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierDW(SpecifierWidth):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, etalon="dw")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.elwidth = self.width.value


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSubVL(Specifier):
    value: _SVP64SubVL

    @classmethod
    def match(cls, desc, record):
        try:
            value = _SVP64SubVL(desc)
        except ValueError:
            return None

        return cls(record=record, value=value)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.subvl = int(self.value.value)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierPredicate(Specifier):
    mode: str
    pred: _SVP64Pred

    @classmethod
    def match(cls, desc, record, mode_match, pred_match):
        (mode, _, pred) = desc.partition("=")

        mode = mode.strip()
        if not mode_match(mode):
            return None

        pred = _SVP64Pred(pred.strip())
        if not pred_match(pred):
            raise ValueError(pred)

        return cls(record=record, mode=mode, pred=pred)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierFF(SpecifierPredicate):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            mode_match=lambda mode_arg: mode_arg == "ff",
            pred_match=lambda pred_arg: pred_arg.mode in (
                _SVP64PredMode.CR,
                _SVP64PredMode.RC1,
            ))

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        if selector.mode.sel != 0:
            raise ValueError("cannot override mode")
        if self.record.svp64.mode is _SVMode.CROP:
            selector.mode.sel = 0b01
            # HACK: please finally provide correct logic for CRs.
            if self.pred in (_SVP64Pred.RC1, _SVP64Pred.RC1_N):
                selector.mode[2] = (self.pred is _SVP64Pred.RC1_N)
            else:
                selector.mode[2] = self.pred.inv
                selector.mode[3, 4] = self.pred.state
        else:
            selector.mode.sel = 0b01 if self.mode == "ff" else 0b11
            selector.inv = self.pred.inv
            if self.record.Rc:
                selector.CR = self.pred.state
            else:
                selector.RC1 = self.pred.state


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierMask(SpecifierPredicate):
    @classmethod
    def match(cls, desc, record, mode):
        return super().match(desc=desc, record=record,
            mode_match=lambda mode_arg: mode_arg == mode,
            pred_match=lambda pred_arg: pred_arg.mode in (
                _SVP64PredMode.INT,
                _SVP64PredMode.CR,
            ))

    def assemble(self, insn):
        raise NotImplementedError()


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierM(SpecifierMask):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, mode="m")

    def validate(self, others):
        for spec in others:
            if isinstance(spec, SpecifierSM):
                raise ValueError("source-mask and predicate mask conflict")
            elif isinstance(spec, SpecifierDM):
                raise ValueError("dest-mask and predicate mask conflict")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.mask = int(self.pred)
        if ((self.record.ptype is _SVPType.P2) and
                (self.record.svp64.mode is not _SVMode.BRANCH)):
            selector.smask = int(self.pred)
            # LDST_IDX smask moving to extra322 but not straight away (False)
            if False and self.record.svp64.mode is _SVMode.LDST_IDX:
                selector.smask_extra332 = int(self.pred)
            else:
                selector.smask = int(self.pred)

        selector.mmode = (self.pred.mode is _SVP64PredMode.CR)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSM(SpecifierMask):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, mode="sm")

    def validate(self, others):
        if self.record.svp64.ptype is _SVPType.P1:
            raise ValueError("source-mask on non-twin predicate")

        if self.pred.mode is _SVP64PredMode.CR:
            twin = None
            for spec in others:
                if isinstance(spec, SpecifierDM):
                    twin = spec

            if twin is None:
                raise ValueError("missing dest-mask in CR twin predication")
            if self.pred.mode != twin.pred.mode:
                raise ValueError(f"predicate masks mismatch: "
                                 f"{self.pred!r} vs {twin.pred!r}")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        # LDST_IDX smask moving to extra322 but not straight away (False)
        if False and self.record.svp64.mode is _SVMode.LDST_IDX:
            selector.smask_extra332 = int(self.pred)
        else:
            selector.smask = int(self.pred)
        selector.mmode = (self.pred.mode is _SVP64PredMode.CR)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierDM(SpecifierMask):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, mode="dm")

    def validate(self, others):
        if self.record.svp64.ptype is _SVPType.P1:
            raise ValueError("dest-mask on non-twin predicate")

        if self.pred.mode is _SVP64PredMode.CR:
            twin = None
            for spec in others:
                if isinstance(spec, SpecifierSM):
                    twin = spec

            if twin is None:
                raise ValueError("missing source-mask in CR twin predication")
            if self.pred.mode != twin.pred.mode:
                raise ValueError(f"predicate masks mismatch: "
                                 f"{self.pred!r} vs {twin.pred!r}")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.mask = int(self.pred)
        selector.mmode = (self.pred.mode is _SVP64PredMode.CR)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierZZ(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "zz":
            return None

        return cls(record=record)

    def validate(self, others):
        for spec in others:
            # Since zz takes precedence (overrides) sz and dz,
            # treat them as mutually exclusive.
            if isinstance(spec, (SpecifierSZ, SpecifierDZ)):
                raise ValueError("mutually exclusive predicate masks")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        if hasattr(selector, "zz"): # this should be done in a different way
            selector.zz = 1
        else:
            selector.sz = 1
            selector.dz = 1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierXZ(Specifier):
    desc: str
    hint: str = _dataclasses.field(repr=False)

    @classmethod
    def match(cls, desc, record, etalon, hint):
        if desc != etalon:
            return None

        return cls(desc=desc, record=record, hint=hint)

    def validate(self, others):
        if self.record.svp64.ptype is _SVPType.P1:
            raise ValueError(f"{self.hint} on non-twin predicate")

        if self.pred.mode is _SVP64PredMode.CR:
            twin = None
            for spec in others:
                if isinstance(spec, SpecifierXZ):
                    twin = spec

            if twin is None:
                raise ValueError(f"missing {self.hint} in CR twin predication")
            if self.pred != twin.pred:
                raise ValueError(f"predicate masks mismatch: "
                                 f"{self.pred!r} vs {twin.pred!r}")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        setattr(selector, self.desc, 1)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSZ(SpecifierXZ):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="sz", hint="source-mask")

    def validate(self, others):
        for spec in others:
            if self.record.svp64.mode is not _SVMode.CROP:
                if isinstance(spec, SpecifierFF):
                    raise ValueError("source-zero not allowed in ff mode")


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierDZ(SpecifierXZ):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="dz", hint="dest-mask")

    def validate(self, others):
        for spec in others:
            if ((self.record.svp64.mode is not _SVMode.CROP) and
                    isinstance(spec, SpecifierFF) and
                    (spec.pred.mode is _SVP64PredMode.RC1)):
                raise ValueError(f"dest-zero not allowed in ff mode BO")


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierEls(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "els":
            return None

        if record.svp64.mode not in (_SVMode.LDST_IMM, _SVMode.LDST_IDX):
            raise ValueError("els is only valid in ld/st modes, not "
                             "%s" % str(self.record.svp64.mode))

        return cls(record=record)

    def assemble(self, insn):
        if self.record.svp64.mode is _SVMode.LDST_IDX: # stride mode
            insn.prefix.rm.mode[1] = 0

        selector = insn.select(record=self.record)
        selector.els = 1



@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSEA(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "sea":
            return None

        return cls(record=record)

    def validate(self, others):
        if self.record.svp64.mode is not _SVMode.LDST_IDX:
            raise ValueError("sea is only valid in ld/st modes, not "
                             "%s" % str(self.record.svp64.mode))

        for spec in others:
            if isinstance(spec, SpecifierFF):
                raise ValueError(f"sea cannot be used in ff mode")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        if selector.mode.sel not in (0b10, 0b00):
            raise ValueError("sea is only valid for normal and els modes, "
                             "not %d" % int(selector.mode.sel))
        selector.SEA = 1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSat(Specifier):
    desc: str
    sign: bool

    @classmethod
    def match(cls, desc, record, etalon, sign):
        if desc != etalon:
            return None

        if record.svp64.mode not in (_SVMode.NORMAL, _SVMode.LDST_IMM,
                                     _SVMode.LDST_IDX):
            raise ValueError("only normal, ld/st imm and "
                             "ld/st idx modes supported")

        return cls(record=record, desc=desc, sign=sign)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.mode[0] = 0b1
        selector.mode[1] = 0b0
        selector.N = int(self.sign)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSatS(SpecifierSat):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="sats", sign=True)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSatU(SpecifierSat):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="satu", sign=False)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierMapReduce(Specifier):
    RG: bool

    @classmethod
    def match(cls, record, RG):
        if record.svp64.mode not in (_SVMode.NORMAL, _SVMode.CROP):
            raise ValueError("only normal and crop modes supported")

        return cls(record=record, RG=RG)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        if self.record.svp64.mode not in (_SVMode.NORMAL, _SVMode.CROP):
            raise ValueError("only normal and crop modes supported")
        selector.mode[0] = 0
        selector.mode[1] = 0
        selector.mode[2] = 1
        selector.RG = self.RG


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierMR(SpecifierMapReduce):
    @classmethod
    def match(cls, desc, record):
        if desc != "mr":
            return None

        return super().match(record=record, RG=False)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierMRR(SpecifierMapReduce):
    @classmethod
    def match(cls, desc, record):
        if desc != "mrr":
            return None

        return super().match(record=record, RG=True)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierBranch(Specifier):
    @classmethod
    def match(cls, desc, record, etalon):
        if desc != etalon:
            return None

        if record.svp64.mode is not _SVMode.BRANCH:
            raise ValueError("only branch modes supported")

        return cls(record=record)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierAll(SpecifierBranch):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, etalon="all")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.ALL = 1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSNZ(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "snz":
            return None

        if record.svp64.mode not in (_SVMode.BRANCH, _SVMode.CROP):
            raise ValueError("only branch and crop modes supported")

        return cls(record=record)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        if self.record.svp64.mode in (_SVMode.CROP, _SVMode.BRANCH):
            selector.SNZ = 1
            if self.record.svp64.mode is _SVMode.BRANCH:
                selector.sz = 1
        else:
            raise ValueError("only branch and crop modes supported")


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSL(SpecifierBranch):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, etalon="sl")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.SL = 1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierSLu(SpecifierBranch):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, etalon="slu")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.SLu = 1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierLRu(SpecifierBranch):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record, etalon="lru")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.LRu = 1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierVSXX(SpecifierBranch):
    VSb: bool
    VLi: bool

    @classmethod
    def match(cls, desc, record, etalon, VSb, VLi):
        if desc != etalon:
            return None

        if record.svp64.mode is not _SVMode.BRANCH:
            raise ValueError("only branch modes supported")

        return cls(record=record, VSb=VSb, VLi=VLi)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.VLS = 1
        selector.VSb = int(self.VSb)
        selector.VLi = int(self.VLi)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierVS(SpecifierVSXX):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="vs", VSb=False, VLi=False)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierVSi(SpecifierVSXX):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="vsi", VSb=False, VLi=True)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierVSb(SpecifierVSXX):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="vsb", VSb=True, VLi=False)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierVSbi(SpecifierVSXX):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="vsbi", VSb=True, VLi=True)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierCTX(Specifier):
    CTi: bool

    @classmethod
    def match(cls, desc, record, etalon, CTi):
        if desc != etalon:
            return None

        if record.svp64.mode is not _SVMode.BRANCH:
            raise ValueError("only branch modes supported")

        return cls(record=record, CTi=CTi)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.CTR = 1
        selector.CTi = int(self.CTi)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierCTR(SpecifierCTX):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="ctr", CTi=False)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierCTi(SpecifierCTX):
    @classmethod
    def match(cls, desc, record):
        return super().match(desc=desc, record=record,
            etalon="cti", CTi=True)


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierPI(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "pi":
            return None

        if record.svp64.mode not in [_SVMode.LDST_IMM, _SVMode.LDST_IDX]:
            raise ValueError("only ld/st imm/idx mode supported")

        return cls(record=record)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.mode[2] = 0b1
        selector.pi = 0b1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierLF(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "lf":
            return None

        if record.svp64.mode is not _SVMode.LDST_IMM:
            raise ValueError("only ld/st imm mode supported")

        return cls(record=record)

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.mode[1] = 0
        selector.lf = 0b1


@_dataclasses.dataclass(eq=True, frozen=True)
class SpecifierVLi(Specifier):
    @classmethod
    def match(cls, desc, record):
        if desc != "vli":
            return None

        return cls(record=record)

    def validate(self, others):
        for spec in others:
            if isinstance(spec, SpecifierFF):
                return

        raise ValueError("VLi only allowed in failfirst")

    def assemble(self, insn):
        selector = insn.select(record=self.record)
        selector.mode[1] = 1
        selector.VLi = 1


class Specifiers(tuple):
    SPECS = (
        SpecifierW,
        SpecifierSW,
        SpecifierDW,
        SpecifierSubVL,
        SpecifierFF,
        SpecifierM,
        SpecifierSM,
        SpecifierDM,
        SpecifierZZ,
        SpecifierSZ,
        SpecifierDZ,
        SpecifierEls,
        SpecifierSEA,
        SpecifierSatS,
        SpecifierSatU,
        SpecifierMR,
        SpecifierMRR,
        SpecifierAll,
        SpecifierSNZ,
        SpecifierSL,
        SpecifierSLu,
        SpecifierLRu,
        SpecifierVS,
        SpecifierVSi,
        SpecifierVSb,
        SpecifierVSbi,
        SpecifierVLi,
        SpecifierCTR,
        SpecifierCTi,
        SpecifierPI,
        SpecifierLF,
    )

    def __new__(cls, items, record):
        def transform(item):
            for spec_cls in cls.SPECS:
                spec = spec_cls.match(item, record=record)
                if spec is not None:
                    return spec
            raise ValueError(item)

        # TODO: remove this hack
        items = dict.fromkeys(items)
        if "vli" in items:
            del items["vli"]
            items["vli"] = None
        items = tuple(items)

        specs = tuple(map(transform, items))
        for (index, spec) in enumerate(specs):
            head = specs[:index]
            tail = specs[index + 1:]
            spec.validate(others=(head + tail))

        return super().__new__(cls, specs)


class SVP64OperandMeta(type):
    class SVP64NonZeroOperand(NonZeroOperand):
        def assemble(self, insn, value):
            if isinstance(value, str):
                value = int(value, 0)
            if not isinstance(value, int):
                raise ValueError("non-integer operand")

            # FIXME: this is really weird
            if self.record.name in ("svstep", "svstep."):
                value += 1 # compensation

            return super().assemble(value=value, insn=insn)

    class SVP64XOStaticOperand(SpanStaticOperand):
        def __init__(self, record, value, span):
            return super().__init__(record=record, name="XO",
                                    value=value, span=span)

    __TRANSFORM = {
        NonZeroOperand: SVP64NonZeroOperand,
        XOStaticOperand: SVP64XOStaticOperand,
    }

    def __new__(metacls, name, bases, ns):
        bases = list(bases)
        for (index, base_cls) in enumerate(bases):
            bases[index] = metacls.__TRANSFORM.get(base_cls, base_cls)

        bases = tuple(bases)

        return super().__new__(metacls, name, bases, ns)


class SVP64Operand(Operand, metaclass=SVP64OperandMeta):
    @property
    def span(self):
        return tuple(map(lambda bit: (bit + 32), super().span))


class RMSelector:
    def __init__(self, insn, record):
        self.__insn = insn
        self.__record = record
        return super().__init__()

    def __str__(self):
        return self.rm.__doc__

    def __repr__(self):
        return repr(self.rm)

    @property
    def insn(self):
        return self.__insn

    @property
    def record(self):
        return self.__record

    @property
    def rm(self):
        rm = getattr(self.insn.prefix.rm, self.record.svp64.mode.name.lower())

        # The idea behind these tables is that they are now literally
        # in identical format to insndb.csv and minor_xx.csv and can
        # be done precisely as that. The only thing to watch out for
        # is the insertion of Rc=1 as a "mask/value" bit and likewise
        # regtype detection (3-bit BF/BFA, 5-bit BA/BB/BT) also inserted
        # as the LSB.
        table = None
        if self.record.svp64.mode is _SVMode.NORMAL:
            # concatenate mode 5-bit with Rc (LSB) then do a mask/map search
            #    mode  Rc  mask  Rc  member
            table = (
                (0b000000, 0b111000, "simple"), # simple     (no Rc)
                (0b001000, 0b111100, "mr"),     # mapreduce  (no Rc)
                (0b010001, 0b010001, "ffrc1"),  # ffirst,     Rc=1
                (0b010000, 0b010001, "ffrc0"),  # ffirst,     Rc=0
                (0b100000, 0b110000, "sat"),    # saturation (no Rc)
                (0b001100, 0b111100, "rsvd"),   # reserved
            )
            mode = int(self.insn.prefix.rm.normal.mode)
            search = ((mode << 1) | self.record.Rc)

        elif self.record.svp64.mode is _SVMode.LDST_IMM:
            # concatenate mode 5-bit with Rc (LSB) then do a mask/map search
            #    mode  Rc  mask  Rc  member
            # ironically/coincidentally this table is identical to NORMAL
            # mode except reserved in place of mr
            table = (
                (0b000000, 0b010000, "simple"), # simple     (no Rc involved)
                (0b010001, 0b010001, "ffrc1"),  # ffirst,     Rc=1
                (0b010000, 0b010001, "ffrc0"),  # ffirst,     Rc=0
            )
            search = ((int(self.insn.prefix.rm.ldst_imm.mode) << 1) |
                      self.record.Rc)

        elif self.record.svp64.mode is _SVMode.LDST_IDX:
            # concatenate mode 5-bit with Rc (LSB) then do a mask/map search
            #    mode  Rc  mask  Rc  member
            table = (
                (0b000000, 0b010000, "simple"), # simple     (no Rc involved)
                (0b010001, 0b010001, "ffrc1"),  # ffirst,     Rc=1
                (0b010000, 0b010001, "ffrc0"),  # ffirst,     Rc=0
            )
            search = ((int(self.insn.prefix.rm.ldst_idx.mode) << 1) |
                      self.record.Rc)

        elif self.record.svp64.mode is _SVMode.CROP:
            # concatenate mode 5-bit with regtype (LSB) then do mask/map search
            #    mode  3b  mask  3b  member
            table = (
                (0b000000, 0b111000, "simple"), # simple
                (0b001000, 0b111000, "mr"),     # mapreduce
                (0b010001, 0b010001, "ff3"),    # ffirst, 3-bit CR
                (0b010000, 0b010000, "ff5"),    # ffirst, 5-bit CR
            )
            search = ((int(self.insn.prefix.rm.crop.mode) << 1) |
                      int(self.record.svp64.extra_CR_3bit))

        elif self.record.svp64.mode is _SVMode.BRANCH:
            # just mode 2-bit
            #    mode  mask  member
            table = (
                (0b00, 0b11, "simple"), # simple
                (0b01, 0b11, "vls"),    # VLset
                (0b10, 0b11, "ctr"),    # CTR mode
                (0b11, 0b11, "ctrvls"), # CTR+VLset mode
            )
            # slightly weird: doesn't have a 5-bit "mode" field like others
            search = int(self.insn.prefix.rm.branch.mode.sel)

        # look up in table
        if table is not None:
            for (value, mask, field) in table:
                if field.startswith("rsvd"):
                    continue
                if ((value & mask) == (search & mask)):
                    return getattr(rm, field)

        return rm

    def __getattr__(self, key):
        if key.startswith(f"_{self.__class__.__name__}__"):
            return super().__getattribute__(key)

        return getattr(self.rm, key)

    def __setattr__(self, key, value):
        if key.startswith(f"_{self.__class__.__name__}__"):
            return super().__setattr__(key, value)

        rm = self.rm
        if not hasattr(rm, key):
            raise AttributeError(key)

        return setattr(rm, key, value)


class SVP64Instruction(PrefixedInstruction):
    """SVP64 instruction: https://libre-soc.org/openpower/sv/svp64/"""
    class Prefix(PrefixedInstruction.Prefix):
        id: _Field = (7, 9)
        rm: RM.remap((6, 8) + tuple(range(10, 32)))

    prefix: Prefix

    def select(self, record):
        return RMSelector(insn=self, record=record)

    @property
    def binary(self):
        bits = []
        for idx in range(64):
            bit = int(self[idx])
            bits.append(bit)
        return "".join(map(str, bits))

    @classmethod
    def assemble(cls, record, arguments=None, specifiers=None):
        insn = super().assemble(record=record, arguments=arguments)

        specifiers = Specifiers(items=specifiers, record=record)
        for specifier in specifiers:
            specifier.assemble(insn=insn)

        insn.prefix.PO = 0x1
        insn.prefix.id = 0x3

        return insn

    def disassemble(self, record,
            byteorder="little",
            style=Style.NORMAL):
        def blob(insn):
            if style <= Style.SHORT:
                return ""
            else:
                blob = insn.bytes(byteorder=byteorder)
                blob = " ".join(map(lambda byte: f"{byte:02x}", blob))
                return f"{blob}    "

        blob_prefix = blob(self.prefix)
        blob_suffix = blob(self.suffix)
        if record is None:
            yield f"{blob_prefix}.long 0x{int(self.prefix):08x}"
            yield f"{blob_suffix}.long 0x{int(self.suffix):08x}"
            return

        assert record.svp64 is not None

        name = f"sv.{record.name}"

        rm = self.select(record=record)

        # convert specifiers to /x/y/z (sorted lexicographically)
        specifiers = sorted(rm.specifiers(record=record))
        if specifiers: # if any add one extra to get the extra "/"
            specifiers = ([""] + specifiers)
        specifiers = "/".join(specifiers)

        # convert operands to " ,x,y,z"
        operands = tuple(map(_operator.itemgetter(1),
            self.spec_dynamic_operands(record=record, style=style)))
        operands = ",".join(operands)
        if len(operands) > 0: # if any separate with a space
            operands = (" " + operands)

        if style <= Style.LEGACY:
            yield f"{blob_prefix}.long 0x{int(self.prefix):08x}"
            suffix = WordInstruction.integer(value=int(self.suffix))
            yield from suffix.disassemble(record=record,
                byteorder=byteorder, style=style)
        else:
            yield f"{blob_prefix}{name}{specifiers}{operands}"
            if blob_suffix:
                yield f"{blob_suffix}"

        if style >= Style.VERBOSE:
            indent = (" " * 4)
            binary = self.binary
            spec = self.spec(record=record, prefix="sv.")

            yield f"{indent}spec"
            yield f"{indent}{indent}{spec}"
            yield f"{indent}pcode"
            for stmt in record.mdwn.pcode:
                yield f"{indent}{indent}{stmt}"
            yield f"{indent}binary"
            yield f"{indent}{indent}[0:8]   {binary[0:8]}"
            yield f"{indent}{indent}[8:16]  {binary[8:16]}"
            yield f"{indent}{indent}[16:24] {binary[16:24]}"
            yield f"{indent}{indent}[24:32] {binary[24:32]}"
            yield f"{indent}{indent}[32:40] {binary[32:40]}"
            yield f"{indent}{indent}[40:48] {binary[40:48]}"
            yield f"{indent}{indent}[48:56] {binary[48:56]}"
            yield f"{indent}{indent}[56:64] {binary[56:64]}"
            yield f"{indent}opcodes"
            for opcode in record.opcodes:
                yield f"{indent}{indent}{opcode!r}"
            for operand in self.operands(record=record):
                yield from operand.disassemble(insn=self,
                    style=style, indent=indent)
            yield f"{indent}RM"
            yield f"{indent}{indent}{str(rm)}"
            for line in rm.disassemble(style=style):
                yield f"{indent}{indent}{line}"
            yield ""

    @classmethod
    def operands(cls, record):
        for operand in super().operands(record=record):
            parent = operand.__class__
            name = f"SVP64{parent.__name__}"
            bases = (SVP64Operand, parent)
            child = type(name, bases, {})
            yield child(**dict(operand))


def parse(stream, factory):
    def match(entry):
        return ("TODO" not in frozenset(entry.values()))

    lines = filter(lambda line: not line.strip().startswith("#"), stream)
    entries = _csv.DictReader(lines)
    entries = filter(match, entries)
    return tuple(map(factory, entries))


class MarkdownDatabase:
    def __init__(self):
        db = {}
        for (name, desc) in _ISA():
            operands = []
            if desc.regs:
                (dynamic, *static) = desc.regs
                operands.extend(dynamic)
                operands.extend(static)
            pcode = PCode(filter(str.strip, desc.pcode))
            operands = Operands(insn=name, operands=operands)
            db[name] = MarkdownRecord(pcode=pcode, operands=operands)

        self.__db = dict(sorted(db.items()))

        return super().__init__()

    def __iter__(self):
        yield from self.__db.items()

    def __contains__(self, key):
        return self.__db.__contains__(key)

    def __getitem__(self, key):
        return self.__db.__getitem__(key)


class FieldsDatabase:
    def __init__(self):
        db = {}
        df = _DecodeFields()
        df.create_specs()
        for (form, fields) in df.instrs.items():
            if form in {"DQE", "TX"}:
                continue
            if form == "all":
                form = "NONE"
            db[_Form[form]] = Fields(fields)

        self.__db = db

        return super().__init__()

    def __getitem__(self, key):
        return self.__db.__getitem__(key)


class PPCDatabase:
    def __init__(self, root, mdwndb):
        # The code below groups the instructions by name:section.
        # There can be multiple names for the same instruction.
        # The point is to capture different opcodes for the same instruction.
        sections = {}
        records = _collections.defaultdict(set)
        path = (root / "insndb.csv")
        with open(path, "r", encoding="UTF-8") as stream:
            for section in sorted(parse(stream, Section.CSV)):
                path = (root / section.csv)
                opcode_cls = {
                    section.Mode.INTEGER: IntegerOpcode,
                    section.Mode.PATTERN: PatternOpcode,
                }[section.mode]
                factory = _functools.partial(PPCRecord.CSV,
                    opcode_cls=opcode_cls)
                with open(path, "r", encoding="UTF-8") as stream:
                    for insn in parse(stream, factory):
                        for name in insn.names:
                            records[name].add(insn)
                            sections[name] = section

        items = sorted(records.items())
        records = {}
        for (name, multirecord) in items:
            records[name] = PPCMultiRecord(sorted(multirecord))

        def exact_match(name):
            record = records.get(name)
            if record is None:
                return None
            return name

        def LK_match(name):
            if not name.endswith("l"):
                return None
            alias = exact_match(name[:-1])
            if alias is None:
                return None
            record = records[alias]
            if "lk" not in record.flags:
                raise ValueError(record)
            return alias

        def AA_match(name):
            if not name.endswith("a"):
                return None
            alias = LK_match(name[:-1])
            if alias is None:
                alias = name[:-1]
            record = records[alias]
            if record.intop not in {_MicrOp.OP_B, _MicrOp.OP_BC}:
                raise ValueError(record)
            if "AA" not in mdwndb[name].operands:
                raise ValueError(record)
            return alias

        def Rc_match(name):
            if not name.endswith("."):
                return None
            alias = exact_match(name[:-1])
            if alias is None:
                return None
            record = records[alias]
            if record.Rc is _RCOE.NONE:
                raise ValueError(record)
            return alias

        db = {}
        matches = (exact_match, LK_match, AA_match, Rc_match)
        for (name, _) in mdwndb:
            if name.startswith("sv."):
                continue
            alias = None
            for match in matches:
                alias = match(name)
                if alias is not None:
                    break
            if alias is None:
                continue
            section = sections[alias]
            record = records[alias]
            db[name] = (section, record)

        self.__db = dict(sorted(db.items()))

        return super().__init__()

    @_functools.lru_cache(maxsize=512, typed=False)
    def __getitem__(self, key):
        return self.__db.get(key, (None, None))


class SVP64Database:
    def __init__(self, root, ppcdb):
        db = set()
        pattern = _re.compile(r"^(?:LDST)?RM-(1P|2P)-.*?\.csv$")
        for (prefix, _, names) in _os.walk(root):
            prefix = _pathlib.Path(prefix)
            for name in filter(lambda name: pattern.match(name), names):
                path = (prefix / _pathlib.Path(name))
                with open(path, "r", encoding="UTF-8") as stream:
                    db.update(parse(stream, SVP64Record.CSV))
        db = {record.name:record for record in db}

        self.__db = dict(sorted(db.items()))
        self.__ppcdb = ppcdb

        return super().__init__()

    def __getitem__(self, key):
        (_, record) = self.__ppcdb[key]
        if record is None:
            return None

        for name in record.names:
            record = self.__db.get(name, None)
            if record is not None:
                return record

        return None


class Records(tuple):
    def __new__(cls, records):
        return super().__new__(cls, sorted(records))


class Database:
    def __init__(self, root):
        root = _pathlib.Path(root)
        mdwndb = MarkdownDatabase()
        fieldsdb = FieldsDatabase()
        ppcdb = PPCDatabase(root=root, mdwndb=mdwndb)
        svp64db = SVP64Database(root=root, ppcdb=ppcdb)

        db = set()
        names = {}
        opcodes = _collections.defaultdict(
            lambda: _collections.defaultdict(set))

        for (name, mdwn) in mdwndb:
            if name.startswith("sv."):
                continue
            (section, ppc) = ppcdb[name]
            if ppc is None:
                continue
            svp64 = svp64db[name]
            fields = fieldsdb[ppc.form]
            record = Record(name=name,
                section=section, ppc=ppc, svp64=svp64,
                mdwn=mdwn, fields=fields)
            db.add(record)
            names[record.name] = record
            opcodes[section][record.PO].add(record)

        self.__db = Records(db)
        self.__names = dict(sorted(names.items()))
        self.__opcodes = dict(sorted(opcodes.items()))

        return super().__init__()

    def __repr__(self):
        return repr(self.__db)

    def __iter__(self):
        yield from self.__db

    @_functools.lru_cache(maxsize=None)
    def __contains__(self, key):
        return self.__getitem__(key) is not None

    @_functools.lru_cache(maxsize=None)
    def __getitem__(self, key):
        if isinstance(key, SVP64Instruction):
            key = key.suffix

        if isinstance(key, Instruction):
            PO = int(key.PO)
            key = int(key)
            sections = sorted(self.__opcodes)
            for section in sections:
                group = self.__opcodes[section]
                for record in group[PO]:
                    if record.match(key=key):
                        return record

            return None

        elif isinstance(key, str):
            return self.__names.get(key)

        raise ValueError("instruction or name expected")


class Walker(mdis.walker.Walker):
    @mdis.dispatcher.Hook(Database)
    def dispatch_database(self, node):
        yield from self(tuple(node))
