import argparse as _argparse
import codecs as _codecs
import dataclasses as _dataclasses
import enum as _enum
import pathlib as _pathlib
import re as _re


from openpower.decoder.power_enums import (
    SVPtype as _SVPtype,
    SVEtype as _SVEtype,
    In1Sel as _In1Sel,
    In2Sel as _In2Sel,
    In3Sel as _In3Sel,
    OutSel as _OutSel,
    CRInSel as _CRInSel,
    CROutSel as _CROutSel,
    SVEXTRA as _SVEXTRA,
)


@_dataclasses.dataclass(eq=True, frozen=True)
class Entry:
    opcode: str
    ptype: _SVPtype
    etype: _SVEtype
    in1: _In1Sel
    in2: _In2Sel
    in3: _In3Sel
    out: _OutSel
    out2: _OutSel
    cr_in: _CRInSel
    cr_out: _CROutSel
    sv_in1: _SVEXTRA
    sv_in2: _SVEXTRA
    sv_in3: _SVEXTRA
    sv_out: _SVEXTRA
    sv_out2: _SVEXTRA
    sv_cr_in: _SVEXTRA
    sv_cr_out: _SVEXTRA
    name: str


def regex_enum(enum):
    assert issubclass(enum, _enum.Enum)
    return "|".join(item.name for item in enum)


PATTERN_VHDL_BINARY = r"(?:2#[01]+#)"
PATTERN_DECIMAL = r"(?:[0-9]+)"
PATTERN_PARTIAL_BINARY = r"(?:[01-]+)"

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
                cls = field.type
                key = field.name
                value = entry[key]
                if issubclass(cls, _enum.Enum):
                    value = {item.name:item for item in cls}[value]
                elif key == "opcode":
                    if value.startswith("2#"):
                        value = value[2:-1]
                else:
                    value = cls(value)
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
