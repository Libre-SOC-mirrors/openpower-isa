# SPDX-License-Identifier: LGPLv3+
# Funded by NLnet https://nlnet.nl/
""" Record for FPSCR as defined in
Power ISA v3.1B Book I section 4.2.2 page 136(162)

FPSCR fields in MSB0:

| Bits  | Mnemonic | Description                                                             |
|-------|----------|-------------------------------------------------------------------------|
| 0:28  | &nbsp;   | Reserved                                                                |
| 29:31 | DRN      | Decimal Rounding Mode                                                   |
| 32    | FX       | Floating-Point Exception Summary                                        |
| 33    | FEX      | Floating-Point Enabled Exception Summary                                |
| 34    | VX       | Floating-Point Invalid Operation Exception Summary                      |
| 35    | OX       | Floating-Point Overflow Exception                                       |
| 36    | UX       | Floating-Point Underflow Exception                                      |
| 37    | ZX       | Floating-Point Zero Divide Exception                                    |
| 38    | XX       | Floating-Point Inexact Exception                                        |
| 39    | VXSNAN   | Floating-Point Invalid Operation Exception (SNaN)                       |
| 40    | VXISI    | Floating-Point Invalid Operation Exception (∞ - ∞)                      |
| 41    | VXIDI    | Floating-Point Invalid Operation Exception (∞ ÷ ∞)                      |
| 42    | VXZDZ    | Floating-Point Invalid Operation Exception (0 ÷ 0)                      |
| 43    | VXIMZ    | Floating-Point Invalid Operation Exception (∞ × 0)                      |
| 44    | VXVC     | Floating-Point Invalid Operation Exception (Invalid Compare)            |
| 45    | FR       | Floating-Point Fraction Rounded                                         |
| 46    | FI       | Floating-Point Fraction Inexact                                         |
| 47:51 | FPRF     | Floating-Point Result Flags                                             |
| 47    | C        | Floating-Point Result Class Descriptor                                  |
| 48:51 | FPCC     | Floating-Point Condition Code                                           |
| 48    | FL       | Floating-Point Less Than or Negative                                    |
| 49    | FG       | Floating-Point Greater Than or Positive                                 |
| 50    | FE       | Floating-Point Equal or Zero                                            |
| 51    | FU       | Floating-Point Unordered or NaN                                         |
| 52    | &nbsp;   | Reserved                                                                |
| 53    | VXSOFT   | Floating-Point Invalid Operation Exception (Software-Defined Condition) |
| 54    | VXSQRT   | Floating-Point Invalid Operation Exception (Invalid Square Root)        |
| 55    | VXCVI    | Floating-Point Invalid Operation Exception (Invalid Integer Convert)    |
| 56    | VE       | Floating-Point Invalid Operation Exception Enable                       |
| 57    | OE       | Floating-Point Overflow Exception Enable                                |
| 58    | UE       | Floating-Point Underflow Exception Enable                               |
| 59    | ZE       | Floating-Point Zero Divide Exception Enable                             |
| 60    | XE       | Floating-Point Inexact Exception Enable                                 |
| 61    | NI       | Floating-Point Non-IEEE Mode                                            |
| 62:63 | RN       | Floating-Point Rounding Control                                         |
"""

from nmigen import Record
from typing import NoReturn
from nmutil.plain_data import plain_data
import linecache
from openpower.decoder.selectable_int import (
    FieldSelectableInt, SelectableInt)


def _parse_line_fields(line):
    # type: (str) -> None | list[str]
    sline = line.strip()
    if not sline.startswith("|"):
        return None
    if not sline.endswith("|"):
        return None
    if sline == "|":
        return None
    return [v.strip() for v in sline[1:-2].split("|")]


_BITS_FIELD = "Bits"
_MNEMONIC_FIELD = "Mnemonic"
FPSCR_WIDTH = 64


@plain_data()
class _MutableField:
    __slots__ = "name", "bits_msb0", "lineno", "include_in_record"

    def __init__(self, name, bits_msb0, lineno, include_in_record=True):
        # type: (str, int | range, int, bool) -> None
        self.name = name
        self.bits_msb0 = bits_msb0
        self.lineno = lineno
        self.include_in_record = include_in_record

    def bits_msb0_iter(self):
        # type: () -> range | tuple[int]
        if isinstance(self.bits_msb0, int):
            return self.bits_msb0,
        return self.bits_msb0

    def to_field(self):
        # type () -> FPSCRField
        return FPSCRField(name=self.name, bits_msb0=self.bits_msb0,
                          include_in_record=self.include_in_record)


@plain_data(frozen=True, unsafe_hash=True)
class FPSCRField:
    __slots__ = "name", "bits_msb0", "include_in_record"

    def __init__(self, name, bits_msb0, include_in_record):
        # type: (str, int | range, bool) -> None
        self.name = name
        self.bits_msb0 = bits_msb0
        self.include_in_record = include_in_record
        """True if this field should be
        included in `FPSCRRecord`, since there are some overlapping fields and
        `Record` doesn't support that.
        """

    def bits_msb0_iter(self):
        # type: () -> range | tuple[int]
        if isinstance(self.bits_msb0, int):
            return self.bits_msb0,
        return self.bits_msb0


def _parse_fields():
    # type: () -> tuple[FPSCRField, ...]
    lines = __doc__.splitlines()
    in_header_sep = False
    in_table_body = False
    header_fields = []  # type: list[str]
    header_lineno = 0
    fields = {}  # type: dict[str, _MutableField]
    bit_fields = [None] * FPSCR_WIDTH  # type: list[_MutableField | None]
    lineno = 0

    def raise_(msg, col=1, err_lineno=None):
        # type: (str, int, int | None) -> NoReturn
        nonlocal lineno
        if err_lineno is None:
            err_lineno = lineno
        for i in range(10000):  # 10000 is random limit if we can't read
            if linecache.getline(__file__, i).strip().startswith('"'):
                break
            err_lineno += 1  # lines before doc comment start
        raise SyntaxError(msg, (
            __file__, err_lineno + 3, col, lines[err_lineno]))

    for lineno, line in enumerate(lines):
        line_fields = _parse_line_fields(line)
        if in_table_body:
            if line_fields is None:
                if len(fields) == 0:
                    raise_("missing table body")
                break
            if len(line_fields) != len(header_fields):
                raise_("wrong number of fields")
            fields_dict = {k: v for k, v in zip(header_fields, line_fields)}
            name = fields_dict[_MNEMONIC_FIELD]
            if name == "" or name == "&nbsp;":
                continue
            if not name.isidentifier():
                raise_(f"invalid field name {name!r}")
            if name in fields:
                raise_(f"duplicate field name {name}")
            bits_str = fields_dict[_BITS_FIELD]
            bits_fields_str = bits_str.split(":")
            if len(bits_fields_str) not in (1, 2) or not all(
                    v.isascii() and v.isdigit() for v in bits_fields_str):
                raise_(f"`{_BITS_FIELD}` field must be "
                       f"of the form `23` or `23:56`")
            bits_fields = [int(v, base=10) for v in bits_fields_str]
            if not all(0 <= v < FPSCR_WIDTH for v in bits_fields):
                raise_(f"`{_BITS_FIELD}` field value is beyond the "
                       f"limits of FPSCR: must be `0 <= v < {FPSCR_WIDTH}`")
            if len(bits_fields) == 2:
                first, last = bits_fields
                if first > last:
                    raise_(f"`{_BITS_FIELD}` field value is an improper "
                           f"range: {first} > {last}")
                bits = range(first, last + 1)
            else:
                bits = bits_fields[0]
            field = _MutableField(name=name, bits_msb0=bits, lineno=lineno)
            fields[name] = field
            for bit in field.bits_msb0_iter():
                old_field = bit_fields[bit]
                if old_field is not None:
                    # field is overwritten -- don't include in Record
                    old_field.include_in_record = False
                bit_fields[bit] = field
        elif in_header_sep:
            if line_fields is None:
                raise_("missing header separator line")
            for v in line_fields:
                if v != "-" * len(v):
                    raise_("header separator field isn't just hyphens")
            if len(line_fields) != len(header_fields):
                raise_("wrong number of fields")
            in_header_sep = False
            in_table_body = True
        else:
            if line_fields is None:
                continue
            if _BITS_FIELD not in line_fields:
                raise_(f"missing `{_BITS_FIELD}` field")
            if _MNEMONIC_FIELD not in line_fields:
                raise_(f"missing `{_MNEMONIC_FIELD}` field")
            if len(set(line_fields)) != len(line_fields):
                raise_("duplicate header field")
            header_fields = line_fields
            in_header_sep = True
            header_lineno = lineno
    if len(fields) == 0:
        raise_("missing table")
    # insert reserved fields and check for partially overwritten fields
    for bit in range(FPSCR_WIDTH):
        field = bit_fields[bit]
        if field is None:
            start = bit
            bit += 1
            while bit < FPSCR_WIDTH and bit_fields[bit] is None:
                bit += 1
            field = _MutableField(name=f"RESERVED_{start}_{bit - 1}",
                                  bits_msb0=range(start, bit),
                                  lineno=header_lineno)
            if len(field.bits_msb0) == 1:
                field.bits_msb0 = start
                field.name = f"RESERVED_{start}"
            for bit in field.bits_msb0_iter():
                bit_fields[bit] = field
            if field.name in fields:
                raise_(f"field {field.name}'s name conflicts with a "
                       f"generated reserved field",
                       err_lineno=fields[field.name].lineno)
            fields[field.name] = field
        elif not field.include_in_record:
            raise_(f"field {field.name} is partially overwritten -- "
                   f"this is an error because FPSCRRecord will have "
                   f"incorrect fields", err_lineno=field.lineno)
        else:
            bit += 1
    return tuple(f.to_field() for f in fields.values())


FPSCR_FIELDS_MSB0 = _parse_fields()  # type: tuple[FPSCRField, ...]
""" All fields in FPSCR. """


def _calc_record_layout_lsb0():
    # type: () -> list[tuple[str, int]]
    fields_lsb0 = []  # type: list[tuple[int, int, str]]
    for field in FPSCR_FIELDS_MSB0:
        if not field.include_in_record:
            continue
        start_msb0 = field.bits_msb0_iter()[0]
        field_len = len(field.bits_msb0_iter())
        start_lsb0 = FPSCR_WIDTH - 1 - start_msb0
        fields_lsb0.append((start_lsb0, field_len, field.name))
    fields_lsb0.sort()
    # _parse_fields already checks for partially overlapping fields and
    # inserts reserved fields ensuring the returned fields cover every bit
    # exactly one, therefore this is correct
    return [(name, f_len) for _, f_len, name in fields_lsb0]


class FPSCRRecord(Record):
    layout = _calc_record_layout_lsb0()

    def __init__(self, name=None):
        super().__init__(name=name, layout=FPSCRRecord.layout)


class FPSCRState(SelectableInt):
    def __init__(self, value=0):
        SelectableInt.__init__(self, value, FPSCR_WIDTH)
        self.fsi = {}
        for field in FPSCR_FIELDS_MSB0:
            bits_msb0 = tuple(field.bits_msb0_iter())
            self.fsi[field.name] = FieldSelectableInt(self, bits_msb0)

    @property
    def DRN(self):
        return self.fsi['DRN'].asint(msb0=True)

    @DRN.setter
    def DRN(self, value):
        self.fsi['DRN'].eq(value)

    @property
    def FX(self):
        return self.fsi['FX'].asint(msb0=True)

    @FX.setter
    def FX(self, value):
        self.fsi['FX'].eq(value)

    @property
    def FEX(self):
        return self.fsi['FEX'].asint(msb0=True)

    @FEX.setter
    def FEX(self, value):
        self.fsi['FEX'].eq(value)

    @property
    def VX(self):
        return self.fsi['VX'].asint(msb0=True)

    @VX.setter
    def VX(self, value):
        self.fsi['VX'].eq(value)

    @property
    def OX(self):
        return self.fsi['OX'].asint(msb0=True)

    @OX.setter
    def OX(self, value):
        self.fsi['OX'].eq(value)

    @property
    def UX(self):
        return self.fsi['UX'].asint(msb0=True)

    @UX.setter
    def UX(self, value):
        self.fsi['UX'].eq(value)

    @property
    def ZX(self):
        return self.fsi['ZX'].asint(msb0=True)

    @ZX.setter
    def ZX(self, value):
        self.fsi['ZX'].eq(value)

    @property
    def XX(self):
        return self.fsi['XX'].asint(msb0=True)

    @XX.setter
    def XX(self, value):
        self.fsi['XX'].eq(value)

    @property
    def VXSNAN(self):
        return self.fsi['VXSNAN'].asint(msb0=True)

    @VXSNAN.setter
    def VXSNAN(self, value):
        self.fsi['VXSNAN'].eq(value)

    @property
    def VXISI(self):
        return self.fsi['VXISI'].asint(msb0=True)

    @VXISI.setter
    def VXISI(self, value):
        self.fsi['VXISI'].eq(value)

    @property
    def VXIDI(self):
        return self.fsi['VXIDI'].asint(msb0=True)

    @VXIDI.setter
    def VXIDI(self, value):
        self.fsi['VXIDI'].eq(value)

    @property
    def VXZDZ(self):
        return self.fsi['VXZDZ'].asint(msb0=True)

    @VXZDZ.setter
    def VXZDZ(self, value):
        self.fsi['VXZDZ'].eq(value)

    @property
    def VXIMZ(self):
        return self.fsi['VXIMZ'].asint(msb0=True)

    @VXIMZ.setter
    def VXIMZ(self, value):
        self.fsi['VXIMZ'].eq(value)

    @property
    def VXVC(self):
        return self.fsi['VXVC'].asint(msb0=True)

    @VXVC.setter
    def VXVC(self, value):
        self.fsi['VXVC'].eq(value)

    @property
    def FR(self):
        return self.fsi['FR'].asint(msb0=True)

    @FR.setter
    def FR(self, value):
        self.fsi['FR'].eq(value)

    @property
    def FI(self):
        return self.fsi['FI'].asint(msb0=True)

    @FI.setter
    def FI(self, value):
        self.fsi['FI'].eq(value)

    @property
    def FPRF(self):
        return self.fsi['FPRF'].asint(msb0=True)

    @FPRF.setter
    def FPRF(self, value):
        self.fsi['FPRF'].eq(value)

    @property
    def C(self):
        return self.fsi['C'].asint(msb0=True)

    @C.setter
    def C(self, value):
        self.fsi['C'].eq(value)

    @property
    def FPCC(self):
        return self.fsi['FPCC'].asint(msb0=True)

    @FPCC.setter
    def FPCC(self, value):
        self.fsi['FPCC'].eq(value)

    @property
    def FL(self):
        return self.fsi['FL'].asint(msb0=True)

    @FL.setter
    def FL(self, value):
        self.fsi['FL'].eq(value)

    @property
    def FG(self):
        return self.fsi['FG'].asint(msb0=True)

    @FG.setter
    def FG(self, value):
        self.fsi['FG'].eq(value)

    @property
    def FE(self):
        return self.fsi['FE'].asint(msb0=True)

    @FE.setter
    def FE(self, value):
        self.fsi['FE'].eq(value)

    @property
    def FU(self):
        return self.fsi['FU'].asint(msb0=True)

    @FU.setter
    def FU(self, value):
        self.fsi['FU'].eq(value)

    @property
    def VXSOFT(self):
        return self.fsi['VXSOFT'].asint(msb0=True)

    @VXSOFT.setter
    def VXSOFT(self, value):
        self.fsi['VXSOFT'].eq(value)

    @property
    def VXSQRT(self):
        return self.fsi['VXSQRT'].asint(msb0=True)

    @VXSQRT.setter
    def VXSQRT(self, value):
        self.fsi['VXSQRT'].eq(value)

    @property
    def VXCVI(self):
        return self.fsi['VXCVI'].asint(msb0=True)

    @VXCVI.setter
    def VXCVI(self, value):
        self.fsi['VXCVI'].eq(value)

    @property
    def VE(self):
        return self.fsi['VE'].asint(msb0=True)

    @VE.setter
    def VE(self, value):
        self.fsi['VE'].eq(value)

    @property
    def OE(self):
        return self.fsi['OE'].asint(msb0=True)

    @OE.setter
    def OE(self, value):
        self.fsi['OE'].eq(value)

    @property
    def UE(self):
        return self.fsi['UE'].asint(msb0=True)

    @UE.setter
    def UE(self, value):
        self.fsi['UE'].eq(value)

    @property
    def ZE(self):
        return self.fsi['ZE'].asint(msb0=True)

    @ZE.setter
    def ZE(self, value):
        self.fsi['ZE'].eq(value)

    @property
    def XE(self):
        return self.fsi['XE'].asint(msb0=True)

    @XE.setter
    def XE(self, value):
        self.fsi['XE'].eq(value)

    @property
    def NI(self):
        return self.fsi['NI'].asint(msb0=True)

    @NI.setter
    def NI(self, value):
        self.fsi['NI'].eq(value)

    @property
    def RN(self):
        return self.fsi['RN'].asint(msb0=True)

    @RN.setter
    def RN(self, value):
        self.fsi['RN'].eq(value)


if __name__ == "__main__":
    from pprint import pprint
    print("FPSCR_FIELDS_MSB0:")
    pprint(FPSCR_FIELDS_MSB0)
    print("FPSCRRecord.layout:")
    pprint(FPSCRRecord.layout)
    print("FPSCRState.fsi:")
    pprint(FPSCRState().fsi)
