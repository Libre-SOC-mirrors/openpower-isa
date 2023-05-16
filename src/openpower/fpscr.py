# SPDX-License-Identifier: LGPLv3+
# Funded by NLnet https://nlnet.nl/

# XXX TODO: get this into openpower/consts.py instead.
# create the layout from an auto-created Enum FPSCRb
""" Record for FPSCR as defined in
Power ISA v3.1B Book I section 4.2.2 page 136(162)

FPSCR fields in MSB0:

|Bits |Mnemonic | Description                                                 |
|-----|---------|-------------------------------------------------------------|
|0:28 | &nbsp;  | Reserved                                                    |
|29:31| DRN     | Decimal Rounding Mode                                       |
|32   | FX      | FP Exception Summary                                        |
|33   | FEX     | FP Enabled Exception Summary                                |
|34   | VX      | FP Invalid Operation Exception Summary                      |
|35   | OX      | FP Overflow Exception                                       |
|36   | UX      | FP Underflow Exception                                      |
|37   | ZX      | FP Zero Divide Exception                                    |
|38   | XX      | FP Inexact Exception                                        |
|39   | VXSNAN  | FP Invalid Operation Exception (SNaN)                       |
|40   | VXISI   | FP Invalid Operation Exception (∞ - ∞)                      |
|41   | VXIDI   | FP Invalid Operation Exception (∞ ÷ ∞)                      |
|42   | VXZDZ   | FP Invalid Operation Exception (0 ÷ 0)                      |
|43   | VXIMZ   | FP Invalid Operation Exception (∞ × 0)                      |
|44   | VXVC    | FP Invalid Operation Exception (Invalid Compare)            |
|45   | FR      | FP Fraction Rounded                                         |
|46   | FI      | FP Fraction Inexact                                         |
|47:51| FPRF    | FP Result Flags                                             |
|47   | C       | FP Result Class Descriptor                                  |
|48:51| FPCC    | FP Condition Code                                           |
|48   | FL      | FP Less Than or Negative                                    |
|49   | FG      | FP Greater Than or Positive                                 |
|50   | FE      | FP Equal or Zero                                            |
|51   | FU      | FP Unordered or NaN                                         |
|52   | &nbsp;  | Reserved                                                    |
|53   | VXSOFT  | FP Invalid Operation Exception (Software-Defined Condition) |
|54   | VXSQRT  | FP Invalid Operation Exception (Invalid Square Root)        |
|55   | VXCVI   | FP Invalid Operation Exception (Invalid Integer Convert)    |
|56   | VE      | FP Invalid Operation Exception Enable                       |
|57   | OE      | FP Overflow Exception Enable                                |
|58   | UE      | FP Underflow Exception Enable                               |
|59   | ZE      | FP Zero Divide Exception Enable                             |
|60   | XE      | FP Inexact Exception Enable                                 |
|61   | NI      | FP Non-IEEE Mode                                            |
|62:63| RN      | FP Rounding Control                                         |
"""

from nmigen import Record
from copy import deepcopy
from openpower.util import log
from openpower.decoder.selectable_int import (
    FieldSelectableInt, SelectableInt)


class FPSCRRecord(Record):
    layout = [("RN", 2),
              ("NI", 1),
              ("XE", 1),
              ("ZE", 1),
              ("UE", 1),
              ("OE", 1),
              ("VE", 1),
              ("VXCVI", 1),
              ("VXSQRT", 1),
              ("VXSOFT", 1),
              ("rsvd1", 1),
              ("FPRF", [
                  ("FPCC", [
                      ("FU", 1),
                      ("FE", 1),
                      ("FG", 1),
                      ("FL", 1),
                  ]),
                  ("C", 1),
              ]),
              ("FI", 1),
              ("FR", 1),
              ("VXVC", 1),
              ("VXIMZ", 1),
              ("VXZDZ", 1),
              ("VXIDI", 1),
              ("VXISI", 1),
              ("VXSNAN", 1),
              ("XX", 1),
              ("ZX", 1),
              ("UX", 1),
              ("OX", 1),
              ("VX", 1),
              ("FEX", 1),
              ("FX", 1),
              ("DRN", 3),
              ("rsvd2", 29),
    ]

    def __init__(self, name=None):
        super().__init__(name=name, layout=FPSCRRecord.layout)


class FPSCR_FPRF(FieldSelectableInt):
    """ special FieldSelectableInt instance to handle assigning strings to
    FPSCR.FPRF

    Translation Table from:
    PowerISA v3.1B Book I Section 4.2.2 Page 139(165)
    Figure 47 Floating-Point Result Flags
    """
    TRANSLATION_TABLE = (
        ("Quiet NaN", 0b10001),
        ("QNaN", 0b10001),
        ("- Infinity", 0b01001),
        ("- Normalized Number", 0b01000),
        ("- Normal Number", 0b01000),
        ("- Denormalized Number", 0b11000),
        ("- Zero", 0b10010),
        ("+ Zero", 0b00010),
        ("+ Denormalized Number", 0b10100),
        ("+ Normalized Number", 0b00100),
        ("+ Normal Number", 0b00100),
        ("+ Infinity", 0b00101),
    )
    TRANSLATION_TABLE_DICT = {k.casefold(): v for k, v in TRANSLATION_TABLE}

    def eq(self, b):
        if isinstance(b, str):
            b = FPSCR_FPRF.TRANSLATION_TABLE_DICT[b.casefold()]
        super().eq(b)


class FPSCRState(SelectableInt):
    def __init__(self, value=0):
        self.__do_update_summary_bits = False
        SelectableInt.__init__(self, value, 64)
        self.fsi = {}
        offs = 0
        # set up sub-fields from Record layout
        self.fsi = {}
        l = deepcopy(FPSCRRecord.layout)
        l.reverse()
        for field, width in l:
            if field == "FPRF":
                v = FPSCR_FPRF(self, tuple(range(47, 52)))
                end = 52
            else:
                end = offs + width
                fs = tuple(range(offs, end))
                v = FieldSelectableInt(self, fs)
            self.fsi[field] = v
            offs = end
        # extra fields, temporarily explicitly added. TODO nested layout above
        extras = [
            (47, "C"),
            (range(48, 52), "FPCC"),
            (48, "FL"),
            (49, "FG"),
            (50, "FE"),
            (51, "FU"),
        ]
        for offs, field in extras:
            if isinstance(offs, int):
                fs = (offs,)
            else:
                fs = tuple(offs)
            v = FieldSelectableInt(self, fs)
            self.fsi[field] = v
        self.__update_summary_bits()

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value
        if self.__do_update_summary_bits:
            self.__update_summary_bits()

    def __update_summary_bits(self):
        self.__do_update_summary_bits = False
        try:
            # update summary bits -- FX is manually handled by pseudo-code,
            # so we don't update it here
            self.VX = (self.VXSNAN |
                       self.VXISI |
                       self.VXIDI |
                       self.VXZDZ |
                       self.VXIMZ |
                       self.VXVC |
                       self.VXSOFT |
                       self.VXSQRT |
                       self.VXCVI)
            self.FEX = ((self.VX & self.VE) |
                        (self.OX & self.OE) |
                        (self.UX & self.UE) |
                        (self.ZX & self.ZE) |
                        (self.XX & self.XE))
        finally:
            self.__do_update_summary_bits = True

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
    print("FPSCRRecord.layout:")
    pprint(FPSCRRecord.layout)
    print("FPSCRState.fsi:")
    pprint(FPSCRState().fsi)

    # quick test of setter/getters
    fpscr = FPSCRState()
    fpscr.FPCC = 0b0001
    print(fpscr.FPCC, fpscr.FL, fpscr.FG, fpscr.FE, fpscr.FU)
    fpscr.FG = 0b1
    print(fpscr.FPCC, fpscr.FL, fpscr.FG, fpscr.FE, fpscr.FU)
    fpscr.FPRF = 0b00011
    print(fpscr.FPRF, fpscr.C)
    fpscr[63] = 1
    print(fpscr.RN)
