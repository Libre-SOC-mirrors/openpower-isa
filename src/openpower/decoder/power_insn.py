import collections as _collections
import csv as _csv
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import itertools as _itertools
import os as _os
import operator as _operator
import pathlib as _pathlib
import re as _re

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
    CROutSel as _CROutSel,
    LDSTLen as _LDSTLen,
    LDSTMode as _LDSTMode,
    RCOE as _RCOE,
    CryIn as _CryIn,
    Form as _Form,
    SVEtype as _SVEtype,
    SVMode as _SVMode,
    SVPtype as _SVPtype,
    SVExtra as _SVExtra,
    RegType as _RegType,
    SVExtraRegType as _SVExtraRegType,
    SVExtraReg as _SVExtraReg,
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


@_functools.total_ordering
class Verbosity(_enum.Enum):
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
@_dataclasses.dataclass(eq=True, frozen=True)
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
            return super().__repr__()

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

    value: Value
    mask: Mask

    def __lt__(self, other):
        if not isinstance(other, Opcode):
            return NotImplemented
        return ((self.value, self.mask) < (other.value, other.mask))

    def __post_init__(self):
        if self.value.bit_length() != self.mask.bit_length():
            raise ValueError("bit length mismatch")

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


class IntegerOpcode(Opcode):
    def __init__(self, value):
        if value.startswith("0b"):
           mask = int(("1" * len(value[2:])), 2)
        else:
            mask = 0b111111

        value = Opcode.Value(value)
        mask = Opcode.Mask(mask)

        return super().__init__(value=value, mask=mask)


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


@_dataclasses.dataclass(eq=True, frozen=True)
class PPCRecord:
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

    class Flags(frozenset, metaclass=FlagsMeta):
        def __new__(cls, flags=frozenset()):
            flags = frozenset(flags)
            diff = (flags - frozenset(cls))
            if diff:
                raise ValueError(flags)
            return super().__new__(cls, flags)

    opcode: Opcode
    comment: str
    flags: Flags = Flags()
    comment2: str = ""
    function: _Function = _Function.NONE
    intop: _MicrOp = _MicrOp.OP_ILLEGAL
    in1: _In1Sel = _In1Sel.RA
    in2: _In2Sel = _In2Sel.NONE
    in3: _In3Sel = _In3Sel.NONE
    out: _OutSel = _OutSel.NONE
    cr_in: _CRInSel = _CRInSel.NONE
    cr_out: _CROutSel = _CROutSel.NONE
    cry_in: _CryIn = _CryIn.ZERO
    ldst_len: _LDSTLen = _LDSTLen.NONE
    upd: _LDSTMode = _LDSTMode.NONE
    Rc: _RCOE = _RCOE.NONE
    form: _Form = _Form.NONE
    conditions: str = ""
    unofficial: bool = False

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

    @classmethod
    def CSV(cls, record, opcode_cls):
        typemap = {field.name:field.type for field in _dataclasses.fields(cls)}
        typemap["opcode"] = opcode_cls

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
            raise AttributeError(attr)
        return getattr(self[0], attr)


@_dataclasses.dataclass(eq=True, frozen=True)
class SVP64Record:
    class ExtraMap(tuple):
        class Extra(tuple):
            @_dataclasses.dataclass(eq=True, frozen=True)
            class Entry:
                regtype: _SVExtraRegType = _SVExtraRegType.NONE
                reg: _SVExtraReg = _SVExtraReg.NONE

                def __repr__(self):
                    return f"{self.regtype.value}:{self.reg.name}"

            def __new__(cls, value="0"):
                if isinstance(value, str):
                    def transform(value):
                        (regtype, reg) = value.split(":")
                        regtype = _SVExtraRegType(regtype)
                        reg = _SVExtraReg(reg)
                        return cls.Entry(regtype=regtype, reg=reg)

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
    ptype: _SVPtype = _SVPtype.NONE
    etype: _SVEtype = _SVEtype.NONE
    in1: _In1Sel = _In1Sel.NONE
    in2: _In2Sel = _In2Sel.NONE
    in3: _In3Sel = _In3Sel.NONE
    out: _OutSel = _OutSel.NONE
    out2: _OutSel = _OutSel.NONE
    cr_in: _CRInSel = _CRInSel.NONE
    cr_out: _CROutSel = _CROutSel.NONE
    extra: ExtraMap = ExtraMap()
    conditions: str = ""
    mode: _SVMode = _SVMode.NORMAL

    __KEYMAP = {
        "insn": "name",
        "CONDITIONS": "conditions",
        "Ptype": "ptype",
        "Etype": "etype",
        "CR in": "cr_in",
        "CR out": "cr_out",
    }

    @classmethod
    def CSV(cls, record):
        for key in ("in1", "in2", "in3", "out", "out2", "CR in", "CR out"):
            value = record[key]
            if value == "0":
                record[key] = "NONE"

        extra = []
        for idx in range(0, 4):
            extra.append(record.pop(f"{idx}"))

        record["extra"] = cls.ExtraMap(extra)

        return dataclass(cls, record, keymap=cls.__KEYMAP)

    @_functools.lru_cache(maxsize=None)
    def extra_idx(self, key):
        extra_idx = (
            _SVExtra.Idx0,
            _SVExtra.Idx1,
            _SVExtra.Idx2,
            _SVExtra.Idx3,
        )

        if key not in frozenset({
                    "in1", "in2", "in3", "cr_in",
                    "out", "out2", "cr_out",
                }):
            raise KeyError(key)

        sel = getattr(self, key)
        if sel is _CRInSel.BA_BB:
            return _SVExtra.Idx_1_2
        reg = _SVExtraReg(sel)
        if reg is _SVExtraReg.NONE:
            return _SVExtra.NONE

        extra_map = {
            _SVExtraRegType.SRC: {},
            _SVExtraRegType.DST: {},
        }
        for index in range(0, 4):
            for entry in self.extra[index]:
                extra_map[entry.regtype][entry.reg] = extra_idx[index]

        for regtype in (_SVExtraRegType.SRC, _SVExtraRegType.DST):
            extra = extra_map[regtype].get(reg, _SVExtra.NONE)
            if extra is not _SVExtra.NONE:
                return extra

        return _SVExtra.NONE

    extra_idx_in1 = property(_functools.partial(extra_idx, key="in1"))
    extra_idx_in2 = property(_functools.partial(extra_idx, key="in2"))
    extra_idx_in3 = property(_functools.partial(extra_idx, key="in3"))
    extra_idx_out = property(_functools.partial(extra_idx, key="out"))
    extra_idx_out2 = property(_functools.partial(extra_idx, key="out2"))
    extra_idx_cr_in = property(_functools.partial(extra_idx, key="cr_in"))
    extra_idx_cr_out = property(_functools.partial(extra_idx, key="cr_out"))

    @_functools.lru_cache(maxsize=None)
    def extra_reg(self, key):
        return _SVExtraReg(getattr(self, key))

    extra_reg_in1 = property(_functools.partial(extra_reg, key="in1"))
    extra_reg_in2 = property(_functools.partial(extra_reg, key="in2"))
    extra_reg_in3 = property(_functools.partial(extra_reg, key="in3"))
    extra_reg_out = property(_functools.partial(extra_reg, key="out"))
    extra_reg_out2 = property(_functools.partial(extra_reg, key="out2"))
    extra_reg_cr_in = property(_functools.partial(extra_reg, key="cr_in"))
    extra_reg_cr_out = property(_functools.partial(extra_reg, key="cr_out"))


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


@_dataclasses.dataclass(eq=True, frozen=True)
class Section:
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

    path: _pathlib.Path
    bitsel: BitSel
    suffix: Suffix
    mode: Mode
    opcode: IntegerOpcode = None

    @classmethod
    def CSV(cls, record):
        typemap = {field.name:field.type for field in _dataclasses.fields(cls)}
        if record["opcode"] == "NONE":
            typemap["opcode"] = lambda _: None

        return dataclass(cls, record, typemap=typemap)


class Fields:
    def __init__(self, items):
        if isinstance(items, dict):
            items = items.items()

        def transform(item):
            (name, bitrange) = item
            return (name, tuple(bitrange.values()))

        self.__mapping = dict(map(transform, items))

        return super().__init__()

    def __repr__(self):
        return repr(self.__mapping)

    def __iter__(self):
        yield from self.__mapping.items()

    def __contains__(self, key):
        return self.__mapping.__contains__(key)

    def __getitem__(self, key):
        return self.__mapping.get(key, None)


@_dataclasses.dataclass(eq=True, frozen=True)
class Operand:
    name: str

    def span(self, record):
        return record.fields[self.name]

    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        raise NotImplementedError


class DynamicOperand(Operand):
    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        span = self.span(record=record)
        if isinstance(insn, SVP64Instruction):
            span = tuple(map(lambda bit: (bit + 32), span))
        value = insn[span]

        if verbosity >= Verbosity.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value))


@_dataclasses.dataclass(eq=True, frozen=True)
class StaticOperand(Operand):
    value: int

    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        span = self.span(record=record)
        if isinstance(insn, SVP64Instruction):
            span = tuple(map(lambda bit: (bit + 32), span))
        value = insn[span]

        if verbosity >= Verbosity.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value))


class ImmediateOperand(DynamicOperand):
    pass


class NonZeroOperand(DynamicOperand):
    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        span = self.span(record=record)
        if isinstance(insn, SVP64Instruction):
            span = tuple(map(lambda bit: (bit + 32), span))
        value = insn[span]

        if verbosity >= Verbosity.VERBOSE:
            span = map(str, span)
            yield f"{indent}{self.name}"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value) + 1)


class RegisterOperand(DynamicOperand):
    def sv_spec_enter(self, value, span):
        return (value, span)

    def sv_spec_leave(self, value, span, origin_value, origin_span):
        return (value, span)

    def spec(self, insn, record):
        vector = False
        span = self.span(record=record)
        if isinstance(insn, SVP64Instruction):
            span = tuple(map(lambda bit: (bit + 32), span))
        value = insn[span]
        span = tuple(map(str, span))

        if isinstance(insn, SVP64Instruction):
            (origin_value, origin_span) = (value, span)
            (value, span) = self.sv_spec_enter(value=value, span=span)

            extra_idx = self.extra_idx(record=record)
            if extra_idx is _SVExtra.NONE:
                return (vector, value, span)

            if record.etype is _SVEtype.EXTRA3:
                spec = insn.prefix.rm.extra3[extra_idx]
            elif record.etype is _SVEtype.EXTRA2:
                spec = insn.prefix.rm.extra2[extra_idx]
            else:
                raise ValueError(record.etype)

            if spec != 0:
                vector = bool(spec[0])
                spec_span = spec.__class__
                if record.etype is _SVEtype.EXTRA3:
                    spec_span = tuple(map(str, spec_span[1, 2]))
                    spec = spec[1, 2]
                elif record.etype is _SVEtype.EXTRA2:
                    spec_span = tuple(map(str, spec_span[1,]))
                    spec = _SelectableInt(value=spec[1].value, bits=2)
                    if vector:
                        spec <<= 1
                        spec_span = (spec_span + ("{0}",))
                    else:
                        spec_span = (("{0}",) + spec_span)
                else:
                    raise ValueError(record.etype)

                vector_shift = (2 + (5 - value.bits))
                scalar_shift = value.bits
                spec_shift = (5 - value.bits)

                bits = (len(span) + len(spec_span))
                value = _SelectableInt(value=value.value, bits=bits)
                spec = _SelectableInt(value=spec.value, bits=bits)
                if vector:
                    value = ((value << vector_shift) | (spec << spec_shift))
                    span = (span + spec_span + ((spec_shift * ('{0}',))))
                else:
                    value = ((spec << scalar_shift) | value)
                    span = ((spec_shift * ('{0}',)) + spec_span + span)

                (value, span) = self.sv_spec_leave(value=value, span=span,
                    origin_value=origin_value, origin_span=origin_span)

        return (vector, value, span)

    @property
    def extra_reg(self):
        return _SVExtraReg(self.name)

    def extra_idx(self, record):
        for key in frozenset({
                    "in1", "in2", "in3", "cr_in",
                    "out", "out2", "cr_out",
                }):
            extra_reg = record.svp64.extra_reg(key=key)
            if extra_reg is self.extra_reg:
                return record.extra_idx(key=key)

        return _SVExtra.NONE

    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, prefix="", indent=""):
        (vector, value, span) = self.spec(insn=insn, record=record)

        if verbosity >= Verbosity.VERBOSE:
            mode = "vector" if vector else "scalar"
            yield f"{indent}{self.name} ({mode})"
            yield f"{indent}{indent}{int(value):0{value.bits}b}"
            yield f"{indent}{indent}{', '.join(span)}"
            if isinstance(insn, SVP64Instruction):
                extra_idx = self.extra_idx(record)
                if record.etype is _SVEtype.NONE:
                    yield f"{indent}{indent}extra[none]"
                else:
                    etype = repr(record.etype).lower()
                    yield f"{indent}{indent}{etype}{extra_idx!r}"
        else:
            vector = "*" if vector else ""
            yield f"{vector}{prefix}{int(value)}"


class GPROperand(RegisterOperand):
    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        prefix = "" if (verbosity <= Verbosity.SHORT) else "r"
        yield from super().disassemble(prefix=prefix,
            insn=insn, record=record,
            verbosity=verbosity, indent=indent)


class FPROperand(RegisterOperand):
    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        prefix = "" if (verbosity <= Verbosity.SHORT) else "f"
        yield from super().disassemble(prefix=prefix,
            insn=insn, record=record,
            verbosity=verbosity, indent=indent)


class CR3Operand(RegisterOperand):
    pass


class CR5Operand(RegisterOperand):
    def sv_spec_enter(self, value, span):
        value = _SelectableInt(value=(value.value >> 2), bits=3)
        return (value, span)

    def sv_spec_leave(self, value, span, origin_value, origin_span):
        value = _selectconcat(value, origin_value[3:5])
        span += origin_span
        return (value, span)


class TargetAddrOperand(RegisterOperand):
    def disassemble(self, insn, record, field,
            verbosity=Verbosity.NORMAL, indent=""):
        span = self.span(record=record)
        if isinstance(insn, SVP64Instruction):
            span = tuple(map(lambda bit: (bit + 32), span))
        value = insn[span]

        if verbosity >= Verbosity.VERBOSE:
            span = tuple(map(str, span))
            yield f"{indent}{self.name} = EXTS({field} || 0b00))"
            yield f"{indent}{indent}{field}"
            yield f"{indent}{indent}{indent}{int(value):0{value.bits}b}00"
            yield f"{indent}{indent}{indent}{', '.join(span + ('{0}', '{0}'))}"
        else:
            yield hex(int(_selectconcat(value,
                _SelectableInt(value=0b00, bits=2))))


class TargetAddrOperandLI(TargetAddrOperand):
    def span(self, record):
        return record.fields["LI"]

    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        return super().disassemble(field="LI",
            insn=insn, record=record,
            verbosity=verbosity, indent=indent)


class TargetAddrOperandBD(TargetAddrOperand):
    def span(self, record):
        return record.fields["BD"]

    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        return super().disassemble(field="BD",
            insn=insn, record=record,
            verbosity=verbosity, indent=indent)


class DOperandDX(DynamicOperand):
    def span(self, record):
        operands = map(DynamicOperand, ("d0", "d1", "d2"))
        spans = map(lambda operand: operand.span(record=record), operands)
        return sum(spans, tuple())

    def disassemble(self, insn, record,
            verbosity=Verbosity.NORMAL, indent=""):
        span = self.span(record=record)
        if isinstance(insn, SVP64Instruction):
            span = tuple(map(lambda bit: (bit + 32), span))
        value = insn[span]

        if verbosity >= Verbosity.VERBOSE:
            yield f"{indent}D"
            mapping = {
                "d0": "[0:9]",
                "d1": "[10:15]",
                "d2": "[16]",
            }
            for (subname, subspan) in mapping.items():
                operand = DynamicOperand(name=subname)
                span = operand.span(record=record)
                if isinstance(insn, SVP64Instruction):
                    span = tuple(map(lambda bit: (bit + 32), span))
                value = insn[span]
                span = map(str, span)
                yield f"{indent}{indent}{operand.name} = D{subspan}"
                yield f"{indent}{indent}{indent}{int(value):0{value.bits}b}"
                yield f"{indent}{indent}{indent}{', '.join(span)}"
        else:
            yield str(int(value))


class Operands(tuple):
    def __new__(cls, insn, iterable):
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
        }

        operands = []
        for operand in iterable:
            dynamic_cls = DynamicOperand
            static_cls = StaticOperand

            if "=" in operand:
                (name, value) = operand.split("=")
                operand = static_cls(name=name, value=int(value))
                operands.append(operand)
            else:
                if operand.endswith(")"):
                    operand = operand.replace("(", " ").replace(")", "")
                    (immediate, _, operand) = operand.partition(" ")
                else:
                    immediate = None

                if immediate is not None:
                    operands.append(ImmediateOperand(name=immediate))

                if insn in custom_insns and operand in custom_insns[insn]:
                    dynamic_cls = custom_insns[insn][operand]
                if operand in custom_fields:
                    dynamic_cls = custom_fields[operand]

                if operand in _RegType.__members__:
                    regtype = _RegType[operand]
                    if regtype is _RegType.GPR:
                        dynamic_cls = GPROperand
                    elif regtype is _RegType.FPR:
                        dynamic_cls = FPROperand
                    if regtype is _RegType.CR_BIT: # 5-bit
                        dynamic_cls = CR5Operand
                    if regtype is _RegType.CR_REG: # actually CR Field, 3-bit
                        dynamic_cls = CR3Operand

                operand = dynamic_cls(name=operand)
                operands.append(operand)

        return super().__new__(cls, operands)

    def __contains__(self, key):
        return self.__getitem__(key) is not None

    def __getitem__(self, key):
        for operand in self:
            if operand.name == key:
                return operand

        return None

    @property
    def dynamic(self):
        for operand in self:
            if isinstance(operand, DynamicOperand):
                yield operand

    @property
    def static(self):
        for operand in self:
            if isinstance(operand, StaticOperand):
                yield operand


class PCode:
    def __init__(self, iterable):
        self.__pcode = tuple(iterable)
        return super().__init__()

    def __iter__(self):
        yield from self.__pcode

    def __repr__(self):
        return self.__pcode.__repr__()


@_dataclasses.dataclass(eq=True, frozen=True)
class MarkdownRecord:
    pcode: PCode
    operands: Operands


@_functools.total_ordering
@_dataclasses.dataclass(eq=True, frozen=True)
class Record:
    name: str
    section: Section
    ppc: PPCRecord
    fields: Fields
    mdwn: MarkdownRecord
    svp64: SVP64Record = None

    def __lt__(self, other):
        if not isinstance(other, Record):
            return NotImplemented
        return (min(self.opcodes) < min(other.opcodes))

    @property
    def opcodes(self):
        def opcode(ppc):
            value = ([0] * 32)
            mask = ([0] * 32)

            PO = self.section.opcode
            if PO is not None:
                for (src, dst) in enumerate(reversed(BitSel((0, 5)))):
                    value[dst] = int((PO.value & (1 << src)) != 0)
                    mask[dst] = int((PO.mask & (1 << src)) != 0)

            XO = ppc.opcode
            for (src, dst) in enumerate(reversed(self.section.bitsel)):
                value[dst] = int((XO.value & (1 << src)) != 0)
                mask[dst] = int((XO.mask & (1 << src)) != 0)

            for operand in self.mdwn.operands.static:
                for (src, dst) in enumerate(reversed(operand.span(record=self))):
                    value[dst] = int((operand.value & (1 << src)) != 0)
                    mask[dst] = 1

            value = Opcode.Value(int(("".join(map(str, value))), 2))
            mask = Opcode.Mask(int(("".join(map(str, mask))), 2))

            return Opcode(value=value, mask=mask)

        return tuple(sorted(map(opcode, self.ppc)))

    def match(self, key):
        for opcode in self.opcodes:
            if ((opcode.value & opcode.mask) ==
                    (key & opcode.mask)):
                return True
        return False

    @property
    def function(self):
        return self.ppc.function

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
    def cr_out(self):
        return self.ppc.cr_out

    ptype = property(lambda self: self.svp64.ptype)
    etype = property(lambda self: self.svp64.etype)

    def extra_idx(self, key):
        return self.svp64.extra_idx(key)

    extra_idx_in1 = property(lambda self: self.svp64.extra_idx_in1)
    extra_idx_in2 = property(lambda self: self.svp64.extra_idx_in2)
    extra_idx_in3 = property(lambda self: self.svp64.extra_idx_in3)
    extra_idx_out = property(lambda self: self.svp64.extra_idx_out)
    extra_idx_out2 = property(lambda self: self.svp64.extra_idx_out2)
    extra_idx_cr_in = property(lambda self: self.svp64.extra_idx_cr_in)
    extra_idx_cr_out = property(lambda self: self.svp64.extra_idx_cr_out)


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

    def record(self, db):
        record = db[self]
        if record is None:
            raise KeyError(self)
        return record

    def spec(self, db, prefix):
        record = self.record(db=db)

        dynamic_operands = tuple(map(_operator.itemgetter(0),
            self.dynamic_operands(db=db)))

        static_operands = []
        for (name, value) in self.static_operands(db=db):
            static_operands.append(f"{name}={value}")

        operands = ""
        if dynamic_operands:
            operands += f" {','.join(dynamic_operands)}"
        if static_operands:
            operands += f" ({' '.join(static_operands)})"

        return f"{prefix}{record.name}{operands}"

    def dynamic_operands(self, db, verbosity=Verbosity.NORMAL):
        record = self.record(db=db)

        imm = False
        imm_name = ""
        imm_value = ""
        for operand in record.mdwn.operands.dynamic:
            name = operand.name
            dis = operand.disassemble(insn=self, record=record,
                verbosity=min(verbosity, Verbosity.NORMAL))
            value = " ".join(dis)
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

    def static_operands(self, db):
        record = self.record(db=db)
        for operand in record.mdwn.operands.static:
            yield (operand.name, operand.value)

    def disassemble(self, db,
            byteorder="little",
            verbosity=Verbosity.NORMAL):
        raise NotImplementedError


class WordInstruction(Instruction):
    _: _Field = range(0, 32)
    po: _Field = range(0, 6)

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

    def disassemble(self, db,
            byteorder="little",
            verbosity=Verbosity.NORMAL):
        integer = int(self)
        if verbosity <= Verbosity.SHORT:
            blob = ""
        else:
            blob = integer.to_bytes(length=4, byteorder=byteorder)
            blob = " ".join(map(lambda byte: f"{byte:02x}", blob))
            blob += "    "

        record = db[self]
        if record is None:
            yield f"{blob}.long 0x{integer:08x}"
            return

        operands = tuple(map(_operator.itemgetter(1),
            self.dynamic_operands(db=db, verbosity=verbosity)))
        if operands:
            yield f"{blob}{record.name} {','.join(operands)}"
        else:
            yield f"{blob}{record.name}"

        if verbosity >= Verbosity.VERBOSE:
            indent = (" " * 4)
            binary = self.binary
            spec = self.spec(db=db, prefix="")
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
            for operand in record.mdwn.operands:
                yield from operand.disassemble(insn=self, record=record,
                    verbosity=verbosity, indent=indent)
            yield ""


class PrefixedInstruction(Instruction):
    class Prefix(WordInstruction.remap(range(0, 32))):
        pass

    class Suffix(WordInstruction.remap(range(32, 64))):
        pass

    _: _Field = range(64)
    prefix: Prefix
    suffix: Suffix
    po: Suffix.po

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

        return super().integer(value=value)


class Mode(_Mapping):
    _: _Field = range(0, 5)
    sel: _Field = range(0, 2)


class NormalMode(Mode):
    class simple(Mode):
        """simple mode"""
        dz: Mode[3]
        sz: Mode[4]

    class smr(Mode):
        """scalar reduce mode (mapreduce), SUBVL=1"""
        RG: Mode[4]

    class pmr(Mode):
        """parallel reduce mode (mapreduce), SUBVL=1"""
        pass

    class svmr(Mode):
        """subvector reduce mode, SUBVL>1"""
        SVM: Mode[3]

    class pu(Mode):
        """Pack/Unpack mode, SUBVL>1"""
        SVM: Mode[3]

    class ffrc1(Mode):
        """Rc=1: ffirst CR sel"""
        inv: Mode[2]
        CRbit: Mode[3, 4]

    class ffrc0(Mode):
        """Rc=0: ffirst z/nonz"""
        inv: Mode[2]
        VLi: Mode[3]
        RC1: Mode[4]

    class sat(Mode):
        """sat mode: N=0/1 u/s, SUBVL=1"""
        N: Mode[2]
        dz: Mode[3]
        sz: Mode[4]

    class satx(Mode):
        """sat mode: N=0/1 u/s, SUBVL>1"""
        N: Mode[2]
        zz: Mode[3]
        dz: Mode[3]
        sz: Mode[3]

    class satpu(Mode):
        """Pack/Unpack sat mode: N=0/1 u/s, SUBVL>1"""
        N: Mode[2]
        zz: Mode[3]
        dz: Mode[3]
        sz: Mode[3]

    class prrc1(Mode):
        """Rc=1: pred-result CR sel"""
        inv: Mode[2]
        CRbit: Mode[3, 4]

    class prrc0(Mode):
        """Rc=0: pred-result z/nonz"""
        inv: Mode[2]
        zz: Mode[3]
        RC1: Mode[4]
        dz: Mode[3]
        sz: Mode[3]

    simple: simple
    smr: smr
    pmr: pmr
    svmr: svmr
    pu: pu
    ffrc1: ffrc1
    ffrc0: ffrc0
    sat: sat
    satx: satx
    satpu: satpu
    prrc1: prrc1
    prrc0: prrc0


class LDSTImmMode(Mode):
    class simple(Mode):
        """simple mode"""
        zz: Mode[3]
        els: Mode[4]
        dz: Mode[3]
        sz: Mode[3]

    class spu(Mode):
        """Structured Pack/Unpack"""
        zz: Mode[3]
        els: Mode[4]
        dz: Mode[3]
        sz: Mode[3]

    class ffrc1(Mode):
        """Rc=1: ffirst CR sel"""
        inv: Mode[2]
        CRbit: Mode[3, 4]

    class ffrc0(Mode):
        """Rc=0: ffirst z/nonz"""
        inv: Mode[2]
        els: Mode[3]
        RC1: Mode[4]

    class sat(Mode):
        """sat mode: N=0/1 u/s"""
        N: Mode[2]
        zz: Mode[3]
        els: Mode[4]
        dz: Mode[3]
        sz: Mode[3]

    class prrc1(Mode):
        """Rc=1: pred-result CR sel"""
        inv: Mode[2]
        CRbit: Mode[3, 4]

    class prrc0(Mode):
        """Rc=0: pred-result z/nonz"""
        inv: Mode[2]
        els: Mode[3]
        RC1: Mode[4]

    simple: simple
    spu: spu
    ffrc1: ffrc1
    ffrc0: ffrc0
    sat: sat
    prrc1: prrc1
    prrc0: prrc0


class LDSTIdxMode(Mode):
    class simple(Mode):
        """simple mode"""
        SEA: Mode[2]
        sz: Mode[3]
        dz: Mode[3]

    class stride(Mode):
        """strided (scalar only source)"""
        SEA: Mode[2]
        dz: Mode[3]
        sz: Mode[4]

    class sat(Mode):
        """sat mode: N=0/1 u/s"""
        N: Mode[2]
        dz: Mode[3]
        sz: Mode[4]

    class prrc1(Mode):
        """Rc=1: pred-result CR sel"""
        inv: Mode[2]
        CRbit: Mode[3, 4]

    class prrc0(Mode):
        """Rc=0: pred-result z/nonz"""
        inv: Mode[2]
        zz: Mode[3]
        RC1: Mode[4]
        dz: Mode[3]
        sz: Mode[3]

    simple: simple
    stride: stride
    sat: sat
    prrc1: prrc1
    prrc0: prrc0


class Extra(_Mapping):
    _: _Field = range(0, 9)


class Extra2(Extra):
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


class Extra3(Extra):
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


class RM(_Mapping):
    class Mode(Mode):
        normal: NormalMode
        ldst_imm: LDSTImmMode
        ldst_idx: LDSTIdxMode

    _: _Field = range(24)
    mmode: _Field = (0,)
    mask: _Field = range(1, 4)
    elwidth: _Field = range(4, 6)
    ewsrc: _Field = range(6, 8)
    subvl: _Field = range(8, 10)
    mode: Mode.remap(range(19, 24))
    smask: _Field = range(16, 19)

    extra: Extra.remap(range(10, 19))
    extra2: Extra2.remap(range(10, 19))
    extra3: Extra3.remap(range(10, 19))


class SVP64Instruction(PrefixedInstruction):
    """SVP64 instruction: https://libre-soc.org/openpower/sv/svp64/"""
    class Prefix(PrefixedInstruction.Prefix):
        id: _Field = (7, 9)
        rm: RM.remap((6, 8) + tuple(range(10, 32)))

    prefix: Prefix

    def record(self, db):
        record = db[self.suffix]
        if record is None:
            raise KeyError(self)
        return record

    @property
    def binary(self):
        bits = []
        for idx in range(64):
            bit = int(self[idx])
            bits.append(bit)
        return "".join(map(str, bits))

    def mode(self, db):
        record = self.record(db=db)

        Rc = False
        if record.mdwn.operands["Rc"] is not None:
            Rc = bool(self[record.fields["Rc"]])

        record = self.record(db=db)
        subvl = self.prefix.rm.subvl
        mode = self.prefix.rm.mode
        sel = mode.sel

        if record.svp64.mode is _SVMode.NORMAL:
            mode = mode.normal
            if sel == 0b00:
                if mode[2] == 0b0:
                    mode = mode.simple
                else:
                    if subvl == 0b00:
                        if mode[3] == 0b0:
                            mode = mode.smr
                        else:
                            mode = mode.pmr
                    else:
                        if mode[4] == 0b0:
                            mode = mode.svmr
                        else:
                            mode = mode.pu
            elif sel == 0b01:
                if Rc:
                    mode = mode.ffrc1
                else:
                    mode = mode.ffrc0
            elif sel == 0b10:
                if subvl == 0b00:
                    mode = mode.sat
                else:
                    if mode[4]:
                        mode = mode.satx
                    else:
                        mode = mode.satpu
            elif sel == 0b11:
                if Rc:
                    mode = mode.prrc1
                else:
                    mode = mode.prrc0
        elif record.svp64.mode is _SVMode.LDST_IMM:
            mode = mode.ldst_imm
            if sel == 0b00:
                if mode[2] == 0b0:
                    mode = mode.simple
                else:
                    mode = mode.spu
            elif sel == 0b01:
                if Rc:
                    mode = mode.ffrc1
                else:
                    mode = mode.ffrc0
            elif sel == 0b10:
                mode = mode.sat
            elif sel == 0b11:
                if Rc:
                    mode = mode.prrc1
                else:
                    mode = mode.prrc0
        elif record.svp64.mode is _SVMode.LDST_IMM:
            mode = mode.ldst_idx
            if mode.sel == 0b00:
                mode = mode.simple
            elif mode.sel == 0b01:
                mode = mode.stride
            elif mode.sel == 0b10:
                mode = mode.sat
            elif mode.sel == 0b11:
                if Rc:
                    mode = mode.prrc1
                else:
                    mode = mode.prrc0

        modes = {
            NormalMode.simple: "normal: simple",
            NormalMode.smr: "normal: smr",
            NormalMode.pmr: "normal: pmr",
            NormalMode.svmr: "normal: svmr",
            NormalMode.pu: "normal: pu",
            NormalMode.ffrc1: "normal: ffrc1",
            NormalMode.ffrc0: "normal: ffrc0",
            NormalMode.sat: "normal: sat",
            NormalMode.satx: "normal: satx",
            NormalMode.satpu: "normal: satpu",
            NormalMode.prrc1: "normal: prrc1",
            NormalMode.prrc0: "normal: prrc0",
            LDSTImmMode.simple: "ld/st imm: simple",
            LDSTImmMode.spu: "ld/st imm: spu",
            LDSTImmMode.ffrc1: "ld/st imm: ffrc1",
            LDSTImmMode.ffrc0: "ld/st imm: ffrc0",
            LDSTImmMode.sat: "ld/st imm: sat",
            LDSTImmMode.prrc1: "ld/st imm: prrc1",
            LDSTImmMode.prrc0: "ld/st imm: prrc0",
            LDSTIdxMode.simple: "ld/st idx simple",
            LDSTIdxMode.stride: "ld/st idx stride",
            LDSTIdxMode.sat: "ld/st idx sat",
            LDSTIdxMode.prrc1: "ld/st idx prrc1",
            LDSTIdxMode.prrc0: "ld/st idx prrc0",
        }
        for (cls, desc) in modes.items():
            if isinstance(mode, cls):
                return (mode, desc)

        if record.svp64.mode is _SVMode.BRANCH:
            return (self.prefix.rm.mode, "branch")

        raise ValueError(self)

    def disassemble(self, db,
            byteorder="little",
            verbosity=Verbosity.NORMAL):
        def blob(integer):
            if verbosity <= Verbosity.SHORT:
                return ""
            else:
                blob = integer.to_bytes(length=4, byteorder=byteorder)
                blob = " ".join(map(lambda byte: f"{byte:02x}", blob))
                return f"{blob}    "

        blob_prefix = blob(int(self.prefix))
        blob_suffix = blob(int(self.suffix))
        record = db[self]
        if record is None or record.svp64 is None:
            yield f"{blob_prefix}.long 0x{int(self.prefix):08x}"
            yield f"{blob_suffix}.long 0x{int(self.suffix):08x}"
            return

        operands = tuple(map(_operator.itemgetter(1),
            self.dynamic_operands(db=db, verbosity=verbosity)))
        if operands:
            yield f"{blob_prefix}sv.{record.name} {','.join(operands)}"
        else:
            yield f"{blob_prefix}{record.name}"
        if blob_suffix:
            yield f"{blob_suffix}"

        (mode, mode_desc) = self.mode(db=db)

        if verbosity >= Verbosity.VERBOSE:
            indent = (" " * 4)
            binary = self.binary
            spec = self.spec(db=db, prefix="sv.")
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
            for operand in record.mdwn.operands:
                yield from operand.disassemble(insn=self, record=record,
                    verbosity=verbosity, indent=indent)

            yield f"{indent}mode"
            yield f"{indent}{indent}{mode_desc}"
            yield ""


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
            pcode = PCode(iterable=desc.pcode)
            operands = Operands(insn=name, iterable=operands)
            db[name] = MarkdownRecord(pcode=pcode, operands=operands)

        self.__db = db

        return super().__init__()

    def __iter__(self):
        yield from self.__db.items()

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
        # The code below groups the instructions by section:identifier.
        # We use the comment as an identifier, there's nothing better.
        # The point is to capture different opcodes for the same instruction.
        dd = _collections.defaultdict
        records = dd(lambda: dd(set))
        path = (root / "insndb.csv")
        with open(path, "r", encoding="UTF-8") as stream:
            for section in parse(stream, Section.CSV):
                path = (root / section.path)
                opcode_cls = {
                    section.Mode.INTEGER: IntegerOpcode,
                    section.Mode.PATTERN: PatternOpcode,
                }[section.mode]
                factory = _functools.partial(
                    PPCRecord.CSV, opcode_cls=opcode_cls)
                with open(path, "r", encoding="UTF-8") as stream:
                    for insn in parse(stream, factory):
                        records[section][insn.comment].add(insn)

        db = dd(set)
        for (section, group) in records.items():
            for records in group.values():
                db[section].add(PPCMultiRecord(records))

        self.__db = db
        self.__mdwndb = mdwndb

        return super().__init__()

    def __getitem__(self, key):
        def exact_match(key, record):
            return (key in record.names)

        def Rc_match(key, record):
            if not key.endswith("."):
                return False

            if not record.Rc is _RCOE.RC:
                return False

            return exact_match(key[:-1], record)

        def LK_match(key, record):
            if not key.endswith("l"):
                return False

            if "lk" not in record.flags:
                return False

            return exact_match(key[:-1], record)

        def AA_match(key, record):
            if not key.endswith("a"):
                return False

            if record.intop not in {_MicrOp.OP_B, _MicrOp.OP_BC}:
                return False

            if self.__mdwndb[key].operands["AA"] is None:
                return False

            return (exact_match(key[:-1], record) or
                LK_match(key[:-1], record))

        for (section, records) in self.__db.items():
            for record in records:
                if exact_match(key, record):
                    return (section, record)

            for record in records:
                if (Rc_match(key, record) or
                        LK_match(key, record) or
                        AA_match(key, record)):
                    return (section, record)

        return (None, None)


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

        self.__db = {record.name:record for record in db}
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


class Database:
    def __init__(self, root):
        root = _pathlib.Path(root)
        mdwndb = MarkdownDatabase()
        fieldsdb = FieldsDatabase()
        ppcdb = PPCDatabase(root=root, mdwndb=mdwndb)
        svp64db = SVP64Database(root=root, ppcdb=ppcdb)

        db = set()
        names = {}
        opcodes = _collections.defaultdict(set)

        for (name, mdwn) in mdwndb:
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
            PO = section.opcode
            if PO is None:
                PO = ppc[0].opcode
            opcodes[PO.value].add(record)

        self.__db = db
        self.__names = names
        self.__opcodes = opcodes

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
        if isinstance(key, (int, Instruction)):
            key = int(key)
            XO = int(_SelectableInt(value=int(key), bits=32)[0:6])
            for record in self.__opcodes[XO]:
                if record.match(key=key):
                   return record

        elif isinstance(key, str):
            return record.__names[key]

        return None
