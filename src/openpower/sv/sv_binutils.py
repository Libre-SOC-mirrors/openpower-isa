import abc as _abc
import argparse as _argparse
import codecs as _codecs
import dataclasses as _dataclasses
import enum as _enum
import pathlib as _pathlib
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


def indent(strings):
    return map(lambda string: ("    " + string), strings)


class Field:
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


class Enum(Field, _enum.Enum):
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
        yield f"enum {c_tag} {name};"


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


class Opcode(Field, str):
    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}\"{self}\"{suffix}"

    @classmethod
    def c_var(cls, name):
        yield f"const char *{name};"


class Name(Field, str):
    def __repr__(self):
        escaped = self.replace("\"", "\\\"")
        return f"\"{escaped}\""

    def c_value(self, prefix="", suffix=""):
        yield f"{prefix}{self!r}{suffix}"

    @classmethod
    def c_var(cls, name):
        yield f"const char *{name};"


@_dataclasses.dataclass(eq=True, frozen=True)
class Entry:
    name: Name
    opcode: Opcode
    in1: In1Sel
    in2: In2Sel
    in3: In3Sel
    out: OutSel
    out2: OutSel
    cr_in: CRInSel
    cr_out: CROutSel
    ptype: SVPType
    etype: SVEType
    sv_in1: SVEXTRA
    sv_in2: SVEXTRA
    sv_in3: SVEXTRA
    sv_out: SVEXTRA
    sv_out2: SVEXTRA
    sv_cr_in: SVEXTRA
    sv_cr_out: SVEXTRA

    @classmethod
    def c_decl(cls):
        yield f"struct svp64_entry {{"
        for field in _dataclasses.fields(cls):
            if issubclass(field.type, Enum):
                bits = len(field.type).bit_length()
                yield from indent([f"uint64_t {field.name} : {bits};"])
            else:
                yield from indent(field.type.c_var(name=field.name))
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
        yield f"struct svp64_entry {name};"


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


def parse(stream):
    for line in stream:
        match = REGEX.match(line)
        if match is not None:
            entry = match.groupdict()
            for field in _dataclasses.fields(Entry):
                key = field.name
                value = entry[key]
                if issubclass(field.type, _enum.Enum):
                    value = {item.name:item for item in field.type}[value]
                else:
                    value = field.type(value)
                entry[key] = value
            yield Entry(**entry)


def main(vhdl):
    with _codecs.open(vhdl, "rb", "UTF-8") as stream:
        entries = tuple(parse(stream))

    print(f"{len(entries)} entries found")


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("vhdl", type=_pathlib.Path, help="sv_decode.vhdl path")

    args = vars(parser.parse_args())
    main(**args)
