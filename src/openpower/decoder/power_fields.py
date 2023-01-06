from collections import namedtuple

import operator as _operator
import functools as _functools

from openpower.decoder.power_enums import find_wiki_file as _find_wiki_file
from openpower.decoder.selectable_int import (
    SelectableInt as _SelectableInt,
    BitRange as _BitRange,
    selectconcat as _selectconcat,
    selectltu as _selectltu,
)


class RemapError(ValueError):
    pass


class Descriptor:
    def __init__(self, cls):
        self.__cls = cls
        return super().__init__()

    def __get__(self, instance, owner):
        if instance is None:
            return self.__cls
        return self.__cls(storage=instance.storage)

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("read-only attribute")
        self.__cls(storage=instance.storage).assign(value)


@_functools.total_ordering
class Reference:
    def __init__(self, storage, *args, **kwargs):
        if not isinstance(storage, _SelectableInt):
            raise ValueError(storage)

        self.storage = storage

        super().__init__()
        self.__post_init__()

    def __post_init__(self, *args, **kwargs):
        _ = (args, kwargs)

    def __binary_operator(self, op, other):
        span = dict.fromkeys(self.__class__.span).keys()
        lhs = _selectconcat(*(self.storage[bit] for bit in span))

        if isinstance(other, Reference):
            span = dict.fromkeys(other.__class__.span).keys()
            rhs = _selectconcat(*(other.storage[bit] for bit in span))
        elif isinstance(other, int):
            bits = len(self.__class__)
            if other.bit_length() > bits:
                raise OverflowError(other)
            rhs = _SelectableInt(value=other, bits=bits)
        elif isinstance(other, _SelectableInt):
            rhs = other
        else:
            raise ValueError(other)

        return op(lhs, rhs)

    def __lt__(self, other):
        return self.__binary_operator(_selectltu, other)

    def __eq__(self, other):
        return self.__binary_operator(_operator.eq, other)

    def __bool__(self):
        return bool(int(self))

    def __int__(self):
        span = dict.fromkeys(self.__class__.span).keys()
        return int(_selectconcat(*(self.storage[bit] for bit in span)))

    def __index__(self):
        return int(self).__index__()

    @property
    def storage(self):
        return self.__storage

    @storage.setter
    def storage(self, storage):
        if not isinstance(storage, _SelectableInt):
            raise ValueError(storage)

        self.__storage = storage

    def assign(self, value, bits=None):
        if bits is None:
            bits = range(len(self.__class__))
        elif isinstance(bits, int):
            bits = (bits,)
        elif isinstance(bits, slice):
            assert bits.step is None or bits.step == 1
            bits = range(bits.start, bits.stop)
        bits = tuple(bits)

        if isinstance(value, (int, self.__class__)):
            value = int(value)
            if value.bit_length() > len(bits):
                raise OverflowError(value)
            value = _SelectableInt(value=value, bits=len(bits))
        if not isinstance(value, _SelectableInt):
            raise ValueError(value)
        if value.bits != len(bits):
            raise OverflowError(value)

        span = tuple(self.__class__.span)
        mapping = dict(enumerate(span))
        for (src, bit) in enumerate(bits):
            if src >= value.bits:
                raise OverflowError(src)
            dst = mapping.get(bit)
            if dst is None:
                raise OverflowError(bit)
            self.storage[dst] = value[src]


class FieldMeta(type):
    def __new__(metacls, clsname, bases, ns, items=()):
        assert "__members__" not in ns

        members = []
        for item in items:
            if not isinstance(item, int):
                raise ValueError(item)
            if item < 0:
                raise ValueError(item)
            members.append(item)

        ns["__members__"] = tuple(members)

        return super().__new__(metacls, clsname, bases, ns)

    def __repr__(cls):
        if not cls.__members__:
            return cls.__name__
        return f"{cls.__name__}{cls.__members__!r}"

    def __iter__(cls):
        yield from cls.__members__

    def __len__(cls):
        return len(cls.__members__)

    def __getitem__(cls, selector):
        if isinstance(selector, int):
            selector = (selector,)

        items = []
        for idx in selector:
            if not isinstance(idx, int):
                raise ValueError(selector)
            item = cls.__members__[idx]
            items.append(item)

        return cls.__class__(cls.__name__, (Field,), {}, items=items)

    def remap(cls, scheme):
        if isinstance(scheme, type) and issubclass(scheme, Mapping):
            scheme = range(len(scheme))
        scheme = cls.__class__(cls.__name__, (cls,), {}, items=scheme)

        if len(cls) == 0:
            return scheme
        elif len(cls) > len(scheme):
            llen = f"len(scheme)"
            rlen = f"len({cls.__name__})"
            raise RemapError(f"{llen} != {rlen}")

        ns = {}
        ns["__doc__"] = cls.__doc__
        items = map(lambda item: scheme.__members__[item], cls)

        return cls.__class__(cls.__name__, (cls,), ns, items=items)

    @property
    def span(cls):
        return cls.__members__


class Field(Reference, metaclass=FieldMeta):
    def __repr__(self):
        return f"[{len(self.__class__)}]0x{int(self):x}"

    def __iter__(self):
        for bit in self.__class__:
            yield self.storage[bit]

    def __getitem__(self, key):
        if isinstance(key, int):
            bit = self.storage[self.__class__.__members__[key]]
            return _SelectableInt(value=bit, bits=1)
        if isinstance(key, slice):
            assert key.step is None or key.step == 1
            key = range(key.start, key.stop)

        return _selectconcat(*(self[bit] for bit in key))

    def __setitem__(self, key, value):
        return self.assign(value=value, bits=key)

    @classmethod
    def traverse(cls, path):
        yield (path, cls.__members__)


class MappingMeta(type):
    def __new__(metacls, clsname, bases, ns):
        members = {}

        for cls in bases:
            if isinstance(cls, metacls):
                members.update(cls.__members__)

        for (name, cls) in ns.get("__annotations__", {}).items():
            if not (isinstance(cls, type) and
                    issubclass(cls, (Mapping, Field))):
                raise ValueError(f"{clsname}.{name}: {cls!r}")

            if name in ns:
                try:
                    members[name] = cls.remap(ns[name])
                except RemapError as error:
                    raise RemapError(f"{name}: {error}")
            else:
                if cls is Field:
                    raise ValueError(f"{clsname}.{name}: missing initializer")
                members[name] = cls

        ns["__members__"] = members
        for (name, cls) in members.items():
            ns[name] = Descriptor(cls)

        return super().__new__(metacls, clsname, bases, ns)

    def __repr__(cls):
        return f"{cls.__name__}({cls.__members__!r})"

    def __iter__(cls):
        yield from cls.__members__.items()

    def __len__(cls):
        length = 0
        for field in cls.__members__.values():
            length = max(length, len(field))
        return length

    def __getitem__(cls, selector):
        return cls.__members__["_"][selector]

    def remap(cls, scheme):
        ns = {}
        annotations = {}

        for (name, field) in cls:
            annotations[name] = field.remap(scheme)
        ns["__annotations__"] = annotations
        ns["__doc__"] = cls.__doc__

        return cls.__class__(cls.__name__, (cls,), ns)

    @property
    def span(cls):
        for field in cls.__members__.values():
            yield from field.span


class Mapping(Reference, metaclass=MappingMeta):
    def __init__(self, storage, **kwargs):
        members = {}
        for (name, cls) in self.__class__:
            members[name] = cls(storage)

        self.__members = members

        return super().__init__(storage, **kwargs)

    def __repr__(self):
        items = tuple(f"{name}={field!r}" for (name, field) in self)
        return f"{{{', '.join(items)}}}"

    def __iter__(self):
        yield from self.__members.items()

    def __getitem__(self, key):
        if isinstance(key, (int, slice, list, tuple, range)):
            return self["_"].__getitem__(key)

        return self.__members.__getitem__(key)

    def __setitem__(self, key, value):
        if isinstance(key, (int, slice, list, tuple, range)):
            return self["_"].assign(value=value, bits=key)

        return self.assign(value=value, bits=key)

    def __getattr__(self, key):
        raise AttributeError(key)

    @classmethod
    def traverse(cls, path):
        for (name, member) in cls.__members__.items():
            if name == "_":
                yield from member.traverse(path=path)
            elif path == "":
                yield from member.traverse(path=name)
            else:
                yield from member.traverse(path=f"{path}.{name}")


def decode_instructions(form):
    res = {}
    accum = []
    for l in form:
        if l.strip().startswith("Formats"):
            l = l.strip().split(":")[-1]
            l = l.replace(" ", "")
            l = l.split(",")
            for fmt in l:
                if fmt not in res:
                    res[fmt] = [accum[0]]
                else:
                    res[fmt].append(accum[0])
            accum = []
        else:
            accum.append(l.strip())
    return res


def decode_form_header(hdr):
    res = {}
    count = 0
    hdr = hdr.strip()
    for f in hdr.split("|"):
        if not f:
            continue
        if f[0].isdigit():
            idx = int(f.strip().split(' ')[0])
            res[count] = idx
        count += len(f) + 1
    return res


def find_unique(d, key):
    if key not in d:
        return key
    idx = 1
    while "%s_%d" % (key, idx) in d:
        idx += 1
    return "%s_%d" % (key, idx)


def decode_line(header, line):
    line = line.strip()
    res = {}
    count = 0
    prev_fieldname = None
    for f in line.split("|"):
        if not f:
            continue
        end = count + len(f) + 1
        fieldname = f.strip()
        if not fieldname or fieldname.startswith('/'):
            if prev_fieldname is not None:
                res[prev_fieldname] = (res[prev_fieldname], header[count])
                prev_fieldname = None
            count = end
            continue
        bitstart = header[count]
        if prev_fieldname is not None:
            res[prev_fieldname] = (res[prev_fieldname], bitstart)
        res[fieldname] = bitstart
        count = end
        prev_fieldname = fieldname
    res[prev_fieldname] = (bitstart, 32)
    return res


def decode_form(form):
    header = decode_form_header(form[0])
    res = []
    for line in form[1:]:
        dec = decode_line(header, line)
        if dec:
            res.append(dec)
    fields = {}
    falternate = {}
    for l in res:
        for k, (start, end) in l.items():
            if k in fields:
                if (start, end) == fields[k]:
                    continue  # already in and matching for this Form
                if k in falternate:
                    alternate = "%s_%d" % (k, falternate[k])
                    if (start, end) == fields[alternate]:
                        continue
                falternate[k] = fidx = falternate.get(k, 0) + 1
                fields["%s_%d" % (k, fidx)] = (start, end)
            else:
                fields[k] = (start, end)
    return fields


class DecodeFields:

    def __init__(self, bitkls=_BitRange, bitargs=(), fname=None,
                 name_on_wiki=None):
        self.bitkls = bitkls
        self.bitargs = bitargs
        if fname is None:
            assert name_on_wiki is None
            fname = "fields.txt"
            name_on_wiki = "fields.text"
        self.fname = _find_wiki_file(name_on_wiki)

    @property
    def form_names(self):
        return self.instrs.keys()

    def create_specs(self):
        self.forms, self.instrs = self.decode_fields()
        forms = self.form_names
        #print ("specs", self.forms, forms)
        for form in forms:
            fields = self.instrs[form]
            fk = fields.keys()
            Fields = namedtuple("Fields", fk)
            instr = Fields(**fields)
            setattr(self, "Form%s" % form, instr)
        # now add in some commonly-used fields (should be done automatically)
        # note that these should only be ones which are the same on all Forms
        # note: these are from microwatt insn_helpers.vhdl
        self.common_fields = {
            "PO": self.Formall.PO,
            "FRS": self.FormX.FRS,
            "FRT": self.FormX.FRT,
            "FRA": self.FormX.FRA,
            "FRB": self.FormX.FRB,
            "FRC": self.FormA.FRC,
            "RS": self.FormX.RS,
            "RT": self.FormX.RT,
            "RA": self.FormX.RA,
            "RB": self.FormX.RB,
            "RC": self.FormVA.RC,
            "SI": self.FormD.SI,
            "UI": self.FormD.UI,
            "L": self.FormD.L,
            "SH32": self.FormM.SH,
            "sh": self.FormMD.sh,
            "MB32": self.FormM.MB,
            "ME32": self.FormM.ME,
            "LI": self.FormI.LI,
            "LK": self.FormI.LK,
            "AA": self.FormB.AA,
            "Rc": self.FormX.Rc,
            "OE": self.FormXO.OE,
            "BD": self.FormB.BD,
            "BF": self.FormX.BF,
            "CR": self.FormXL.XO,
            "BB": self.FormXL.BB,
            "BA": self.FormXL.BA,
            "BT": self.FormXL.BT,
            "FXM": self.FormXFX.FXM,
            "BO": self.FormXL.BO,
            "BI": self.FormXL.BI,
            "BH": self.FormXL.BH,
            "D": self.FormD.D,
            "DS": self.FormDS.DS,
            "TO": self.FormX.TO,
            "BC": self.FormA.BC,
            "SH": self.FormX.SH,
            "ME": self.FormM.ME,
            "MB": self.FormM.MB,
            "SPR": self.FormXFX.SPR}
        for k, v in self.common_fields.items():
            setattr(self, k, v)

    def decode_fields(self):
        with open(self.fname) as f:
            txt = f.readlines()
        #print ("decode", txt)
        forms = {}
        reading_data = False
        for l in txt:
            l = l.strip()
            if len(l) == 0:
                continue
            if reading_data:
                if l[0] == '#':
                    reading_data = False
                else:
                    forms[heading].append(l)
            if not reading_data:
                assert l[0] == '#'
                heading = l[1:].strip()
                # if heading.startswith('1.6.28'): # skip instr fields for now
                #     break
                heading = heading.split(' ')[-1]
                reading_data = True
                forms[heading] = []

        res = {}
        inst = {}

        for hdr, form in forms.items():
            if heading == 'Fields':
                i = decode_instructions(form)
                for form, field in i.items():
                    inst[form] = self.decode_instruction_fields(field)
            # else:
            #     res[hdr] = decode_form(form)
        return res, inst

    def decode_instruction_fields(self, fields):
        res = {}
        for field in fields:
            f, spec = field.strip().split(" ")
            ss = spec[1:-1].split(",")
            fs = f.split(",")
            if len(fs) > 1:
                individualfields = []
                for f0, s0 in zip(fs, ss):
                    txt = "%s (%s)" % (f0, s0)
                    individualfields.append(txt)
                if len(fs) > 1:
                    res.update(self.decode_instruction_fields(
                        individualfields))
            d = self.bitkls(*self.bitargs)
            idx = 0
            for s in ss:
                s = s.split(':')
                if len(s) == 1:
                    d[idx] = int(s[0])
                    idx += 1
                else:
                    start = int(s[0])
                    end = int(s[1])
                    while start <= end:
                        d[idx] = start
                        idx += 1
                        start += 1
            f = f.replace(",", "_")
            unique = find_unique(res, f)
            res[unique] = d

        return res


if __name__ == '__main__':
    dec = DecodeFields()
    dec.create_specs()
    forms, instrs = dec.forms, dec.instrs
    for form, fields in instrs.items():
        print("Form", form)
        for field, bits in fields.items():
            print("\tfield", field, bits)
