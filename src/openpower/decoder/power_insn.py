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
    rc: _RCOE = _RCOE.NONE
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
    pu: bool = False
    conditions: str = ""
    mode: _SVMode = _SVMode.NORMAL

    __KEYMAP = {
        "insn": "name",
        "CONDITIONS": "conditions",
        "Ptype": "ptype",
        "Etype": "etype",
        "CR in": "cr_in",
        "CR out": "cr_out",
        "PU": "pu",
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
    pass


class Operands(tuple):
    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperand(Operand):
        name: str

        def disassemble(self, value, record):
            return str(int(value[record.fields[self.name]]))

    @_dataclasses.dataclass(eq=True, frozen=True)
    class StaticOperand(Operand):
        name: str
        value: int = None

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperandIFormLI(DynamicOperand):
        def disassemble(self, value, record):
            return hex(int(_selectconcat(
                value[record.fields["LI"]],
                _SelectableInt(value=0b00, bits=2))))

    class DynamicOperandBFormBD(DynamicOperand):
        def disassemble(self, value, record):
            return hex(int(_selectconcat(
                value[record.fields["BD"]],
                _SelectableInt(value=0b00, bits=2))))

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperandGPR(DynamicOperand):
        def disassemble(self, value, record):
            return f"r{super().disassemble(value=value, record=record)}"

    @_dataclasses.dataclass(eq=True, frozen=True)
    class DynamicOperandFPR(DynamicOperand):
        def disassemble(self, value, record):
            return f"f{super().disassemble(value=value, record=record)}"

    def __new__(cls, insn, iterable):
        branches = {
            "b": {"LI": cls.DynamicOperandIFormLI},
            "ba": {"LI": cls.DynamicOperandIFormLI},
            "bl": {"LI": cls.DynamicOperandIFormLI},
            "bla": {"LI": cls.DynamicOperandIFormLI},
            "bc": {"BD": cls.DynamicOperandBFormBD},
            "bca": {"BD": cls.DynamicOperandBFormBD},
            "bcl": {"BD": cls.DynamicOperandBFormBD},
            "bcla": {"BD": cls.DynamicOperandBFormBD},
        }

        operands = []
        for operand in iterable:
            dynamic_cls = cls.DynamicOperand
            static_cls = cls.StaticOperand

            if "=" in operand:
                (name, value) = operand.split("=")
                operand = static_cls(name=name, value=int(value))
            else:
                if insn in branches and operand in branches[insn]:
                    dynamic_cls = branches[insn][operand]

                if operand in _RegType.__members__:
                    regtype = _RegType[operand]
                    if regtype is _RegType.GPR:
                        dynamic_cls = cls.DynamicOperandGPR
                    elif regtype is _RegType.FPR:
                        dynamic_cls = cls.DynamicOperandFPR

                operand = dynamic_cls(name=operand)

            operands.append(operand)

        return super().__new__(cls, operands)


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

    def __repr__(self):
        return f"{self.__class__.__name__}(name={self.name!r}, opcode={self.opcode})"

    @cached_property
    def opcode(self):
        fields = []
        if self.section.opcode:
            fields += [(self.section.opcode.value, BitSel((0, 5)))]
            fields += [(self.ppc.opcode.value, self.section.bitsel)]
        else:
            fields += [(self.ppc.opcode.value, self.section.bitsel)]

        for operand in self.static_operands:
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

    @property
    def dynamic_operands(self):
        for operand in self.operands:
            if isinstance(operand, Operands.DynamicOperand):
                yield operand

    @property
    def static_operands(self):
        for operand in self.operands:
            if isinstance(operand, Operands.StaticOperand):
                yield operand


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

    def disassemble(self, db):
        raise NotImplementedError


class WordInstruction(Instruction):
    _: _Field = range(0, 32)
    po: _Field = range(0, 6)

    @classmethod
    def integer(cls, value, byteorder="little"):
        return super().integer(bits=32, value=value, byteorder=byteorder)

    def disassemble(self, db):
        record = db[self]
        if record is None:
            yield f".long 0x{int(self):08x}"
        else:
            operands = []
            for operand in record.dynamic_operands:
                operand = operand.disassemble(self, record)
                operands.append(operand)
            if operands:
                operands = ",".join(operands)
                operands = f" {operands}"
            else:
                operands = ""

            yield f"{record.name}{operands}"

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

    def disassemble(self, db):
        record = db[self.suffix]
        if record is None:
            yield f".llong 0x{int(self):016x}"
        else:
            yield f".llong 0x{int(self):016x} # {record.name}"


class SVP64Instruction(PrefixedInstruction):
    """SVP64 instruction: https://libre-soc.org/openpower/sv/svp64/"""
    class Prefix(PrefixedInstruction.Prefix):
        class RM(_Mapping):
            _: _Field = range(24)
            mmode: _Field = (0,)
            mask: _Field = range(1, 4)
            elwidth: _Field = range(4, 6)
            ewsrc: _Field = range(6, 8)
            subvl: _Field = range(8, 10)
            extra: _Field = range(10, 19)
            mode: _Field = range(19, 24)
            extra2: _Field[4] = (
                range(10, 12),
                range(12, 14),
                range(14, 16),
                range(16, 18),
            )
            smask: _Field = range(16, 19)
            extra3: _Field[3] = (
                range(10, 13),
                range(13, 16),
                range(16, 19),
            )

        id: _Field = (7, 9)
        rm: RM = ((6, 8) + tuple(range(10, 32)))

    prefix: Prefix

    def disassemble(self, db):
        record = db[self.suffix]
        if record is None:
            yield f".llong 0x{int(self):016x}"
        else:
            yield f".llong 0x{int(self):016x} # sv.{record.name}"


def parse(stream, factory):
    lines = filter(lambda line: not line.strip().startswith("#"), stream)
    entries = _csv.DictReader(lines)
    entries = filter(lambda entry: "TODO" not in frozenset(entry.values()), entries)
    return tuple(map(factory, entries))


class PPCDatabase:
    def __init__(self, root):
        db = _collections.defaultdict(set)
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
                    db[section].update(parse(stream, factory))
        self.__db = db
        return super().__init__()

    def __getitem__(self, key):
        for (section, records) in self.__db.items():
            for record in records:
                for name in record.names:
                    if ((key == name) or
                            ((record.rc is _RC.RC) and
                                key.endswith(".") and
                                name == key[:-1])):
                        return (section, record)
        return (None, None)


class SVP64Database:
    def __init__(self, root):
        db = set()
        pattern = _re.compile(r"^(?:LDST)?RM-(1P|2P)-.*?\.csv$")
        for (prefix, _, names) in _os.walk(root):
            prefix = _pathlib.Path(prefix)
            for name in filter(lambda name: pattern.match(name), names):
                path = (prefix / _pathlib.Path(name))
                with open(path, "r", encoding="UTF-8") as stream:
                    db.update(parse(stream, SVP64Record.CSV))
        self.__db = {record.name:record for record in db}
        return super().__init__()

    def __getitem__(self, key):
        for name in key:
            record = self.__db.get(name, None)
            if record is not None:
                return record
        return None


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


class Database:
    def __init__(self, root):
        root = _pathlib.Path(root)

        mdwndb = MarkdownDatabase()
        fieldsdb = FieldsDatabase()
        svp64db = SVP64Database(root)
        ppcdb = PPCDatabase(root)

        db = set()
        for (name, operands) in mdwndb:
            (section, ppc) = ppcdb[name]
            if ppc is None:
                continue
            svp64 = svp64db[ppc.names]
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
