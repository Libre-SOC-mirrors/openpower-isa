import collections as _collections
import csv as _csv
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import os as _os
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
    Array as _Array,
    Mapping as _Mapping,
    DecodeFields as _DecodeFields,
)
from openpower.decoder.pseudo.pagereader import ISA as _ISA


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
    class Value(int):
        def __repr__(self):
            if self.bit_length() <= 32:
                return f"0x{self:08x}"
            else:
                return f"0x{self:016x}"

    class Mask(int):
        def __repr__(self):
            if self.bit_length() <= 32:
                return f"0x{self:08x}"
            else:
                return f"0x{self:016x}"

    value: Value
    mask: Mask = None

    def __lt__(self, other):
        if not isinstance(other, Opcode):
            return NotImplemented
        return ((self.value, self.mask) < (other.value, other.mask))

    def __post_init__(self):
        (value, mask) = (self.value, self.mask)

        if isinstance(value, Opcode):
            if mask is not None:
                raise ValueError(mask)
            (value, mask) = (value.value, value.mask)
        elif isinstance(value, str):
            if mask is not None:
                raise ValueError(mask)
            value = int(value, 0)

        if not isinstance(value, int):
            raise ValueError(value)
        if mask is None:
            mask = value
        if not isinstance(mask, int):
            raise ValueError(mask)

        object.__setattr__(self, "value", self.__class__.Value(value))
        object.__setattr__(self, "mask", self.__class__.Mask(mask))


class IntegerOpcode(Opcode):
    def __init__(self, value):
        if isinstance(value, str):
            value = int(value, 0)
        return super().__init__(value=value, mask=None)


class PatternOpcode(Opcode):
    def __init__(self, value):
        (pattern, value, mask) = (value, 0, 0)

        for symbol in pattern:
            if symbol not in {"0", "1", "-"}:
                raise ValueError(pattern)
            value |= (symbol == "1")
            mask |= (symbol != "-")
            value <<= 1
            mask <<= 1
        value >>= 1
        mask >>= 1

        return super().__init__(value=value, mask=mask)


class FieldsOpcode(Opcode):
    def __init__(self, fields):
        def field(opcode, field):
            (value, mask) = opcode
            (field, bits) = field
            shifts = map(lambda bit: (31 - bit), reversed(tuple(bits)))
            for (index, shift) in enumerate(shifts):
                bit = ((field & (1 << index)) != 0)
                value |= (bit << shift)
                mask |= (1 << shift)
            return (value, mask)

        (value, mask) = _functools.reduce(field, fields, (0, 0))

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
    def CSV(cls, record, opcode_cls=Opcode):
        typemap = {field.name:field.type for field in _dataclasses.fields(cls)}
        typemap["opcode"] = opcode_cls

        flags = set()
        for flag in frozenset(PPCRecord.Flags):
            if bool(record.pop(flag, "")):
                flags.add(flag)
        record["flags"] = PPCRecord.Flags(flags)

        return dataclass(cls, record, keymap=PPCRecord.__KEYMAP, typemap=typemap)

    @cached_property
    def names(self):
        return frozenset(self.comment.split("=")[-1].split("/"))


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

        record["extra"] = cls.ExtraMap(record.pop(f"{index}") for index in range(0, 4))

        return dataclass(cls, record, keymap=cls.__KEYMAP)


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
    opcode: Opcode
    bitsel: BitSel
    suffix: Suffix
    mode: Mode

    @classmethod
    def CSV(cls, record):
        return dataclass(cls, record)


class Fields:
    def __init__(self, items):
        if isinstance(items, dict):
            items = items.items()

        def transform(item):
            (name, bitrange) = item
            return (name, list(bitrange.values()))

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


class Operands:
    @_dataclasses.dataclass(eq=True, frozen=True)
    class Operand:
        name: str

        def disassemble(self, value, record, verbose=False):
            raise NotImplementedError

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperand(Operand):
        def disassemble(self, value, record, verbose=False):
            span = record.fields[self.name]
            value = value[span]
            if verbose:
                return f"{int(value):0{value.bits}b} {span}"
            else:
                return str(int(value))

    @_dataclasses.dataclass(eq=True, frozen=True)
    class StaticOperand(Operand):
        value: int

        def disassemble(self, value, record, verbose=False):
            span = record.fields[self.name]
            value = value[span]
            if verbose:
                return f"{int(value):0{value.bits}b} {span}"
            else:
                return str(int(value))

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperandIFormLI(DynamicOperand):
        def disassemble(self, value, record, verbose=False):
            span = record.fields["LI"]
            value = value[span]
            if verbose:
                return f"{int(value):0{value.bits}b}{{00}} {span}"
            else:
                return hex(int(_selectconcat(value,
                    _SelectableInt(value=0b00, bits=2))))

    class DynamicOperandBFormBD(DynamicOperand):
        def disassemble(self, value, record, verbose=False):
            span = record.fields["BD"]
            value = value[span]
            if verbose:
                return f"{int(value):0{value.bits}b}{{00}} {span}"
            else:
                return hex(int(_selectconcat(value,
                    _SelectableInt(value=0b00, bits=2))))

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperandGPR(DynamicOperand):
        def disassemble(self, value, record, verbose=False):
            result = super().disassemble(value=value,
                record=record, verbose=verbose)
            if not verbose:
                result = f"r{result}"
            return result

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperandFPR(DynamicOperand):
        def disassemble(self, value, record, verbose=False):
            result = super().disassemble(value=value,
                record=record, verbose=verbose)
            if not verbose:
                result = f"f{result}"
            return result

    def __init__(self, insn, iterable):
        branches = {
            "b": {"LI": self.__class__.DynamicOperandIFormLI},
            "ba": {"LI": self.__class__.DynamicOperandIFormLI},
            "bl": {"LI": self.__class__.DynamicOperandIFormLI},
            "bla": {"LI": self.__class__.DynamicOperandIFormLI},
            "bc": {"BD": self.__class__.DynamicOperandBFormBD},
            "bca": {"BD": self.__class__.DynamicOperandBFormBD},
            "bcl": {"BD": self.__class__.DynamicOperandBFormBD},
            "bcla": {"BD": self.__class__.DynamicOperandBFormBD},
        }

        operands = []
        for operand in iterable:
            dynamic_cls = self.__class__.DynamicOperand
            static_cls = self.__class__.StaticOperand

            if "=" in operand:
                (name, value) = operand.split("=")
                operand = static_cls(name=name, value=int(value))
            else:
                if insn in branches and operand in branches[insn]:
                    dynamic_cls = branches[insn][operand]

                if operand in _RegType.__members__:
                    regtype = _RegType[operand]
                    if regtype is _RegType.GPR:
                        dynamic_cls = self.__class__.DynamicOperandGPR
                    elif regtype is _RegType.FPR:
                        dynamic_cls = self.__class__.DynamicOperandFPR

                operand = dynamic_cls(name=operand)

            operands.append(operand)

        self.__operands = operands

        return super().__init__()

    def __repr__(self):
        return self.__operands.__repr__()

    def __iter__(self):
        yield from self.__operands

    def __contains__(self, key):
        return self.__getitem__(key) is not None

    def __getitem__(self, key):
        for operand in self.__operands:
            if operand.name == key:
                return operand

        return None

    @property
    def dynamic(self):
        for operand in self:
            if isinstance(operand, self.__class__.DynamicOperand):
                yield operand

    @property
    def static(self):
        for operand in self:
            if isinstance(operand, self.__class__.StaticOperand):
                yield operand


@_functools.total_ordering
@_dataclasses.dataclass(eq=True, frozen=True)
class Record:
    name: str
    section: Section
    ppc: PPCRecord
    fields: Fields
    operands: Operands
    svp64: SVP64Record = None

    __EXTRA = (
        _SVExtra.Idx0,
        _SVExtra.Idx1,
        _SVExtra.Idx2,
        _SVExtra.Idx3,
    )

    def __lt__(self, other):
        if not isinstance(other, Record):
            return NotImplemented
        return (self.opcode < other.opcode)

    @cached_property
    def opcode(self):
        fields = []
        if self.section.opcode:
            fields += [(self.section.opcode.value, BitSel((0, 5)))]
            fields += [(self.ppc.opcode.value, self.section.bitsel)]
        else:
            fields += [(self.ppc.opcode.value, self.section.bitsel)]

        for operand in self.operands.static:
            fields += [(operand.value, self.fields[operand.name])]

        return FieldsOpcode(fields)

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

    def sv_extra(self, key):
        if key not in frozenset({
                    "in1", "in2", "in3", "cr_in",
                    "out", "out2", "cr_out",
                }):
            raise KeyError(key)

        sel = getattr(self.svp64, key)
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
            for entry in self.svp64.extra[index]:
                extra_map[entry.regtype][entry.reg] = Record.__EXTRA[index]

        for regtype in (_SVExtraRegType.SRC, _SVExtraRegType.DST):
            extra = extra_map[regtype].get(reg, _SVExtra.NONE)
            if extra is not _SVExtra.NONE:
                return extra

        return _SVExtra.NONE

    sv_in1 = property(_functools.partial(sv_extra, key="in1"))
    sv_in2 = property(_functools.partial(sv_extra, key="in2"))
    sv_in3 = property(_functools.partial(sv_extra, key="in3"))
    sv_out = property(_functools.partial(sv_extra, key="out"))
    sv_out2 = property(_functools.partial(sv_extra, key="out2"))
    sv_cr_in = property(_functools.partial(sv_extra, key="cr_in"))
    sv_cr_out = property(_functools.partial(sv_extra, key="cr_out"))

    @property
    def sv_ptype(self):
        if self.svp64 is None:
            return _SVPtype.NONE
        return self.svp64.ptype

    @property
    def sv_etype(self):
        if self.svp64 is None:
            return _SVEtype.NONE
        return self.svp64.etype


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

    def disassemble(self, db, byteorder="little", verbose=False):
        raise NotImplementedError


class WordInstruction(Instruction):
    _: _Field = range(0, 32)
    po: _Field = range(0, 6)

    @classmethod
    def integer(cls, value, byteorder="little"):
        return super().integer(bits=32, value=value, byteorder=byteorder)

    def spec(self, record):
        dynamic_operands = []
        for operand in record.operands.dynamic:
            dynamic_operands.append(operand.name)
        static_operands = []
        for operand in record.operands.static:
            static_operands.append(f"{operand.name}={operand.value}")
        operands = ""
        if dynamic_operands:
            operands += f" {','.join(dynamic_operands)}"
        if static_operands:
            operands += f" ({' '.join(static_operands)})"
        return f"{record.name}{operands}"

    def opcode(self, record):
        return f"0x{record.opcode.value:08x}"

    def mask(self, record):
        return f"0x{record.opcode.mask:08x}"

    def disassemble(self, db, byteorder="little", verbose=False):
        integer = int(self)
        blob = integer.to_bytes(length=4, byteorder=byteorder)
        blob = " ".join(map(lambda byte: f"{byte:02x}", blob))

        record = db[self]
        if record is None:
            yield f"{blob}    .long 0x{integer:08x}"
            return

        operands = []
        for operand in record.operands.dynamic:
            operand = operand.disassemble(value=self,
                record=record, verbose=False)
            operands.append(operand)
        if operands:
            operands = ",".join(operands)
            operands = f" {operands}"
        else:
            operands = ""

        yield f"{blob}    {record.name}{operands}"

        if verbose:
            indent = (" " * 4)
            spec = self.spec(record=record)
            opcode = self.opcode(record=record)
            mask = self.mask(record=record)
            yield f"{indent}{'spec':11}{spec}"
            yield f"{indent}{'opcode':11}{opcode}"
            yield f"{indent}{'mask':11}{mask}"
            for operand in record.operands:
                name = operand.name
                value = operand.disassemble(value=self,
                    record=record, verbose=True)
                yield f"{indent}{name:11}{value}"


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
    extra: _Field = range(10, 19)
    mode: Mode.remap(range(19, 24))
    extra2: _Array[4] = (
        range(10, 12),
        range(12, 14),
        range(14, 16),
        range(16, 18),
    )
    smask: _Field = range(16, 19)
    extra3: _Array[3] = (
        range(10, 13),
        range(13, 16),
        range(16, 19),
    )


class SVP64Instruction(PrefixedInstruction):
    """SVP64 instruction: https://libre-soc.org/openpower/sv/svp64/"""
    class Prefix(PrefixedInstruction.Prefix):
        id: _Field = (7, 9)
        rm: RM.remap((6, 8) + tuple(range(10, 32)))

    prefix: Prefix

    def disassemble(self, db, byteorder="little", verbose=False):
        integer_prefix = int(self.prefix)
        blob_prefix = integer_prefix.to_bytes(length=4, byteorder=byteorder)
        blob_prefix = " ".join(map(lambda byte: f"{byte:02x}", blob_prefix))

        integer_suffix = int(self.suffix)
        blob_suffix = integer_suffix.to_bytes(length=4, byteorder=byteorder)
        blob_suffix = " ".join(map(lambda byte: f"{byte:02x}", blob_suffix))

        record = db[self.suffix]
        if record is None or record.svp64 is None:
            yield f"{blob_prefix}    .long 0x{int(self.prefix):08x}"
            yield f"{blob_suffix}    .long 0x{int(self.suffix):08x}"
            return

        Rc = False
        if record.operands["Rc"] is not None:
            Rc = bool(self[record.fields["Rc"]])

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

        if type(mode) is Mode:
            raise NotImplementedError

        yield f"{blob_prefix}    sv.{record.name}"
        yield f"{blob_suffix}"


def parse(stream, factory):
    lines = filter(lambda line: not line.strip().startswith("#"), stream)
    entries = _csv.DictReader(lines)
    entries = filter(lambda entry: "TODO" not in frozenset(entry.values()), entries)
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
            db[name] = Operands(insn=name, iterable=operands)
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
    def __init__(self, root, mdwndb, fieldsdb):
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
                factory = _functools.partial(PPCRecord.CSV, opcode_cls=opcode_cls)
                with open(path, "r", encoding="UTF-8") as stream:
                    for insn in parse(stream, factory):
                        records[section][insn.comment].add(insn)

        # Once we collected all instructions with the same identifier,
        # it's time to merge the different opcodes into the single pattern.
        # At this point, we only consider masks; the algorithm as follows:
        # 1. If any of two masks ignores the bit, it's ignored entirely.
        # 2. If the bit is not equal between masks, it's ignored.
        # 3. Otherwise the bits are equal and considered.
        def merge(lhs, rhs):
            value = 0
            mask = 0
            lvalue = lhs.opcode.value
            rvalue = rhs.opcode.value
            lmask = lhs.opcode.mask
            rmask = rhs.opcode.mask
            bits = max(lmask.bit_length(), rmask.bit_length())
            for bit in range(bits):
                lvstate = ((lvalue & (1 << bit)) != 0)
                rvstate = ((rvalue & (1 << bit)) != 0)
                lmstate = ((lmask & (1 << bit)) != 0)
                rmstate = ((rmask & (1 << bit)) != 0)
                vstate = lvstate
                mstate = True
                if (not lmstate or not rmstate) or (lvstate != rvstate):
                    vstate = 0
                    mstate = 0
                value |= (vstate << bit)
                mask |= (mstate << bit)
            return _dataclasses.replace(lhs, opcode=Opcode(value=value, mask=mask))

        db = dd(set)
        for (section, group) in records.items():
            for records in group.values():
                db[section].add(_functools.reduce(merge, records))

        self.__db = db
        self.__mdwndb = mdwndb
        self.__fieldsdb = fieldsdb

        return super().__init__()

    def __getitem__(self, key):
        def exact_match(key, record):
            for name in record.names:
                if name == key:
                    return True

            return False

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

            if self.__mdwndb[key]["AA"] is None:
                return False

            return (exact_match(key[:-1], record) or
                LK_match(key[:-1], record))

        for (section, records) in self.__db.items():
            for record in records:
                if (exact_match(key, record) or
                        Rc_match(key, record) or
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
        ppcdb = PPCDatabase(root=root, mdwndb=mdwndb, fieldsdb=fieldsdb)
        svp64db = SVP64Database(root=root, ppcdb=ppcdb)

        db = set()
        for (name, operands) in mdwndb:
            (section, ppc) = ppcdb[name]
            if ppc is None:
                continue
            svp64 = svp64db[name]
            fields = fieldsdb[ppc.form]
            record = Record(name=name,
                section=section, ppc=ppc, svp64=svp64,
                operands=operands, fields=fields)
            db.add(record)

        self.__db = tuple(sorted(db))

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
            for record in self:
                opcode = record.opcode
                if ((opcode.value & opcode.mask) ==
                        (key & opcode.mask)):
                    return record
            return None
        elif isinstance(key, Opcode):
            for record in self:
                if record.opcode == key:
                    return record
        elif isinstance(key, str):
            for record in self:
                if record.name == key:
                    return record
        return None
