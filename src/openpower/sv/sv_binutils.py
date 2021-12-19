import argparse as _argparse
import codecs as _codecs
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


PATTERN = "".join((
    r"^\s*",
    r"(?P<opcode>(?:2#[01]+#)|(?:[0-9]+)|(?:[01-]+))",
    r"\s?=>\s?",
    r"\(",
    r",\s".join((
        rf"(?P<ptype>{'|'.join(item.name for item in _SVPtype)})",
        rf"(?P<etype>{'|'.join(item.name for item in _SVEtype)})",
        rf"(?P<in1>{'|'.join(item.name for item in _In1Sel)})",
        rf"(?P<in2>{'|'.join(item.name for item in _In2Sel)})",
        rf"(?P<in3>{'|'.join(item.name for item in _In3Sel)})",
        rf"(?P<out>{'|'.join(item.name for item in _OutSel)})",
        rf"(?P<out2>{'|'.join(item.name for item in _OutSel)})",
        rf"(?P<cr_in>{'|'.join(item.name for item in _CRInSel)})",
        rf"(?P<cr_out>{'|'.join(item.name for item in _CROutSel)})",
        rf"(?P<sv_in1>{'|'.join(item.name for item in _SVEXTRA)})",
        rf"(?P<sv_in2>{'|'.join(item.name for item in _SVEXTRA)})",
        rf"(?P<sv_in3>{'|'.join(item.name for item in _SVEXTRA)})",
        rf"(?P<sv_out>{'|'.join(item.name for item in _SVEXTRA)})",
        rf"(?P<sv_out2>{'|'.join(item.name for item in _SVEXTRA)})",
        rf"(?P<sv_cr_in>{'|'.join(item.name for item in _SVEXTRA)})",
        rf"(?P<sv_cr_out>{'|'.join(item.name for item in _SVEXTRA)})",
    )),
    r"\)",
    r",",
    r"\s?--\s?",
    r"(?P<insn>[A-Za-z0-9_\./]+)",
    r"\s*$",
))
REGEX = _re.compile(PATTERN)


def parse(stream):
    for line in stream:
        match = REGEX.match(line)
        if match is not None:
            yield match.groupdict()


def main(vhdl):
    insns = []
    with _codecs.open(vhdl, "rb", "UTF-8") as stream:
        for insn in parse(stream):
            insns.append(insn)

    print(f"{len(insns)} instructions found")


if __name__ == "__main__":
    parser = _argparse.ArgumentParser()
    parser.add_argument("vhdl", type=_pathlib.Path, help="sv_decode.vhdl path")

    args = vars(parser.parse_args())
    main(**args)
