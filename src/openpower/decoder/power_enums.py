# SPDX-License-Identifier: LGPL-3-or-later
# Copyright (C) 2020, 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Copyright (C) 2020, Michael Nolan

"""Enums used in OpenPOWER ISA decoding

Note: for SV, from v3.1B p12:

    The designated SPR sandbox consists of non-privileged SPRs 704-719 and
    privileged SPRs 720-735.

Note: the option exists to select a much shorter list of SPRs, to reduce
regfile size in HDL.  this is SPRreduced and the supported list is in
get_spr_enum
"""

from enum import (
    auto,
    Enum as _Enum,
    unique,
)
import csv
import os
from os.path import dirname, join
from collections import namedtuple
import functools


def find_wiki_dir():
    filedir = os.path.dirname(os.path.abspath(__file__))
    basedir = dirname(dirname(dirname(filedir)))
    tabledir = join(basedir, 'openpower')
    isatables = join(tabledir, 'isatables')
    #print ("find_wiki_dir", isatables)
    return isatables


def find_wiki_file(name):
    return join(find_wiki_dir(), name)


def get_csv(name):
    """gets a not-entirely-csv-file-formatted database, which allows comments
    """
    file_path = find_wiki_file(name)
    with open(file_path, 'r') as csvfile:
        csvfile = filter(lambda row: row[0] !='#', csvfile) # strip "#..."
        reader = csv.DictReader(csvfile)
        return list(reader)


# names of the fields in the tables that don't correspond to an enum
single_bit_flags = ['inv A', 'inv out',
                    'cry out', 'BR', 'sgn ext', 'rsrv', '32b',
                    'sgn', 'lk', 'sgl pipe']

# default values for fields in the table
default_values = {'unit': "NONE", 'internal op': "OP_ILLEGAL",
                  'in1': "RA", 'in2': 'NONE', 'in3': 'NONE', 'out': 'NONE',
                  'CR in': 'NONE',
                  'ldst len': 'NONE',
                  'upd': '0',
                  'rc': 'NONE', 'cry in': 'ZERO', 'form': 'NONE'}


def get_signal_name(name):
    if name[0].isdigit():
        name = "is_" + name
    return name.lower().replace(' ', '_')


class Enum(_Enum):
    @classmethod
    def _missing_(cls, desc):
        if isinstance(desc, str):
            try:
                if desc == "":
                    desc = 0
                else:
                    desc = int(desc, 0)
            except ValueError:
                pass
        keys = {item.name:item for item in cls}
        descs = {item.value:item for item in cls}
        return keys.get(desc, descs.get(desc))


# this corresponds to which Function Unit (pipeline-with-Reservation-Stations)
# is to process and guard the operation.  they are roughly divided by having
# the same register input/output signature (X-Form, etc.)


@unique
class Function(Enum):
    NONE = 0
    ALU = 1 << 1
    LDST = 1 << 2
    SHIFT_ROT = 1 << 3
    LOGICAL = 1 << 4
    BRANCH = 1 << 5
    CR = 1 << 6
    TRAP = 1 << 7
    MUL = 1 << 8
    DIV = 1 << 9
    SPR = 1 << 10
    MMU = 1 << 11
    SV = 1 << 12  # Simple-V https://libre-soc.org/openpower/sv
    VL = 1 << 13  # setvl
    FPU = 1 << 14  # FPU

    @functools.lru_cache(maxsize=None)
    def __repr__(self):
        counter = 0
        value = int(self.value)
        if value != 0:
            while value != 0:
                counter += 1
                value >>= 1
            counter -= 1
            desc = f"(1 << {counter})"
        else:
            desc = "0"
        return f"<{self.__class__.__name__}.{self.name}: {desc}>"


@unique
class Form(Enum):
    NONE = 0
    I = 1
    B = 2
    SC = 3
    D = 4
    DS = 5
    DQ = 6
    DX = 7
    X = 8
    XL = 9
    XFX = 10
    XFL = 11
    XX1 = 12
    XX2 = 13
    XX3 = 14
    XX4 = 15
    XS = 16
    XO = 17
    A = 18
    M = 19
    MD = 20
    MDS = 21
    VA = 22
    VC = 23
    VX = 24
    EVX = 25
    EVS = 26
    Z22 = 27
    Z23 = 28
    SVL = 29  # Simple-V for setvl instruction
    SVD = 30  # Simple-V for LD/ST bit-reverse, variant of D-Form
    SVDS = 31  # Simple-V for LD/ST bit-reverse, variant of DS-Form
    SVM = 32  # Simple-V SHAPE mode
    SVM2 = 33  # Simple-V SHAPE2 mode - fits into SVM
    SVRM = 34  # Simple-V REMAP mode
    TLI = 35  # ternlogi
    XB = 36
    BM2 = 37 # bmask
    SVI = 38  # Simple-V Index Mode
    VA2 = 39
    SVC = 40
    SVR = 41
    CRB = 42 # crternlogi / crbinlut
    MM = 43  # [f]minmax[s][.]
    CW = 44
    CW2 = 45
    DCT = 46 # fdmadds

# Simple-V svp64 fields https://libre-soc.org/openpower/sv/svp64/


class SVMode(Enum):
    NONE = 0          # for non-SV instructions only
    NORMAL = auto()
    LDST_IDX = auto()
    LDST_IMM = auto()
    BRANCH = auto()
    CROP = auto()


@unique
class SVPType(Enum):
    NONE = 0
    P1 = 1
    P2 = 2

    @classmethod
    def _missing_(cls, desc):
        return {"1P": SVPType.P1, "2P": SVPType.P2}.get(desc)

    def __repr__(self):
        return {
            SVPType.NONE: "NONE",
            SVPType.P1: "1P",
            SVPType.P2: "2P",
        }[self]


@unique
class SVEType(Enum):
    NONE = 0
    EXTRA2 = 1
    EXTRA3 = 2

    def __repr__(self):
        return self.name


@unique
class SVMaskSrc(Enum):
    NO = 0
    EN = 1

    def __repr__(self):
        return self.name


@unique
class SVExtra(Enum):
    NONE = 0
    Idx0 = 1
    Idx1 = 2
    Idx2 = 3
    Idx3 = 4
    Idx_1_2 = 5  # due to weird BA/BB for crops

    def __repr__(self):
        return {
            SVExtra.NONE: "NONE",
            SVExtra.Idx0: "[0]",
            SVExtra.Idx1: "[1]",
            SVExtra.Idx2: "[2]",
            SVExtra.Idx3: "[3]",
            SVExtra.Idx_1_2: "[1:2]",
        }[self]

# Backward compatibility
SVEXTRA = SVExtra


class SVExtraRegType(Enum):
    NONE = None
    SRC = 's'
    DST = 'd'


class SVExtraReg(Enum):
    NONE = auto()
    RA = auto()
    RA_OR_ZERO = RA
    RB = auto()
    RC = auto()
    RS = auto()
    RT = auto()
    RT_OR_ZERO = RT
    FRA = auto()
    FRB = auto()
    FRC = auto()
    FRS = auto()
    FRT = auto()
    CR = auto()
    CR0 = auto()
    CR1 = auto()
    BF = auto()
    BFA = auto()
    BA = auto()
    BB = auto()
    BC = auto()
    BI = auto()
    BT = auto()
    BFT = auto()
    WHOLE_REG = auto()
    SPR = auto()
    RSp = auto()
    RTp = auto()
    FRAp = auto()
    FRBp = auto()
    FRSp = auto()
    FRTp = auto()

    @classmethod
    def _missing_(cls, desc):
        selectors = (
            In1Sel, In2Sel, In3Sel, CRInSel, CRIn2Sel,
            OutSel, CROutSel,
        )
        if isinstance(desc, selectors):
            return cls.__members__.get(desc.name)

        return cls.__members__.get(desc)


@unique
class SVP64PredMode(Enum):
    ALWAYS = 0
    INT = 1
    CR = 2
    RC1 = 3


@unique
class SVP64PredInt(Enum):
    ALWAYS = 0b000
    R3_UNARY = 0b001
    R3 = 0b010
    R3_N = 0b011
    R10 = 0b100
    R10_N = 0b101
    R30 = 0b110
    R30_N = 0b111

    @classmethod
    def _missing_(cls, desc):
        if isinstance(desc, str):
            value = desc
            values = {
                "^r3": cls.R3_UNARY,
                "r3": cls.R3,
                "~r3": cls.R3_N,
                "r10": cls.R10,
                "~r10": cls.R10_N,
                "r30": cls.R30,
                "~r30": cls.R30_N,
            }
            if value.startswith("~"):
                value = f"~{value[1:].strip()}"
            elif "<<" in value: # 1 << r3
                (lhs, _, rhs) = value.partition("<<")
                lhs = lhs.strip().lower()
                rhs = rhs.strip().lower()
                if (lhs == "1") and (rhs in ("r3", "%r3")):
                    value = "^r3"

            return values.get(value)

        return super()._missing_(desc)

    def __str__(self):
        return {
            self.__class__.ALWAYS: "",
            self.__class__.R3_UNARY: "^r3",
            self.__class__.R3: "r3",
            self.__class__.R3_N: "~r3",
            self.__class__.R10: "r10",
            self.__class__.R10_N: "~r10",
            self.__class__.R30: "r30",
            self.__class__.R30_N: "~r30",
        }[self]

    def __repr__(self):
        return f"{self.__class__.__name__}({str(self)})"

    def __int__(self):
        return self.value

    @property
    def mode(self):
        return SVP64PredMode.INT

    @property
    def inv(self):
        return (self.value & 0b1)

    @property
    def state(self):
        return (self.value >> 1)


class SVP64PredCR(Enum):
    LT = 0
    GE = 1
    NL = GE
    GT = 2
    LE = 3
    NG = LE
    EQ = 4
    NE = 5
    SO = 6
    UN = SO
    NS = 7
    NU = NS

    @classmethod
    def _missing_(cls, desc):
        if isinstance(desc, str):
            name = desc.upper()
            return cls.__members__.get(name)

        return super()._missing_(desc)

    def __int__(self):
        return self.value

    @property
    def mode(self):
        return SVP64PredMode.CR

    @property
    def inv(self):
        return (self.value & 0b1)

    @property
    def state(self):
        return (self.value >> 1)


@unique
class SVP64PredRC1(Enum):
    RC1 = 0
    RC1_N = 1

    @classmethod
    def _missing_(cls, desc):
        return {
            "RC1": SVP64PredRC1.RC1,
            "~RC1": SVP64PredRC1.RC1_N,
        }.get(desc)

    def __int__(self):
        return 1

    @property
    def mode(self):
        return SVP64PredMode.RC1

    @property
    def inv(self):
        return (self is SVP64PredRC1.RC1_N)

    @property
    def state(self):
        return 1


class SVP64Pred(Enum):
    ALWAYS = SVP64PredInt.ALWAYS
    R3_UNARY = SVP64PredInt.R3_UNARY
    R3 = SVP64PredInt.R3
    R3_N = SVP64PredInt.R3_N
    R10 = SVP64PredInt.R10
    R10_N = SVP64PredInt.R10_N
    R30 = SVP64PredInt.R30
    R30_N = SVP64PredInt.R30_N

    LT = SVP64PredCR.LT
    GE = SVP64PredCR.GE
    GT = SVP64PredCR.GT
    LE = SVP64PredCR.LE
    EQ = SVP64PredCR.EQ
    NE = SVP64PredCR.NE
    SO = SVP64PredCR.SO
    NS = SVP64PredCR.NS

    RC1 = SVP64PredRC1.RC1
    RC1_N = SVP64PredRC1.RC1_N

    @classmethod
    def _missing_(cls, desc):
        if isinstance(desc, str):
            values = {item.value:item for item in cls}
            for subcls in (SVP64PredInt, SVP64PredCR, SVP64PredRC1):
                try:
                    return values.get(subcls(desc))
                except ValueError:
                    pass
            return None

        return super()._missing_(desc)

    def __int__(self):
        return int(self.value)

    @property
    def mode(self):
        return self.value.mode

    @property
    def inv(self):
        return self.value.inv

    @property
    def state(self):
        return self.value.state


@unique
class SVP64RMMode(Enum):
    NORMAL = 0
    MAPREDUCE = 1
    FFIRST = 2
    SATURATE = 3
    PREDRES = 4
    BRANCH = 5


@unique
class SVP64BCPredMode(Enum):
    NONE = 0
    MASKZERO = 1
    MASKONE = 2


@unique
class SVP64BCVLSETMode(Enum):
    NONE = 0
    VL_INCL = 1
    VL_EXCL = 2


# note that these are chosen to be exactly the same as
# SVP64 RM bit 4.  ALL=1 => bit4=1
@unique
class SVP64BCGate(Enum):
    ANY = 0
    ALL = 1


class SVP64BCCTRMode(Enum):
    NONE = 0
    TEST = 1
    TEST_INV = 2


@unique
class SVP64Width(Enum):
    DEFAULT = 0
    EW_32 = 1
    EW_16 = 2
    EW_8 = 3

    @classmethod
    def _missing_(cls, desc):
        if isinstance(desc, str):
            return {
                "32": SVP64Width.EW_32,
                "16": SVP64Width.EW_16,
                "8": SVP64Width.EW_8,
            }.get(desc)

        return super()._missing_(desc)


@unique
class SVP64SubVL(Enum):
    VEC1 = 0
    VEC2 = 1
    VEC3 = 2
    VEC4 = 3

    @classmethod
    def _missing_(cls, desc):
        if isinstance(desc, str):
            name = desc.upper()
            return cls.__members__.get(name)

        return super()._missing_(desc)


@unique
class SVP64Sat(Enum):
    NONE = 0
    SIGNED = 1
    UNSIGNED = 2


@unique
class SVP64LDSTmode(Enum):
    NONE = 0
    INDEXED = 1
    ELSTRIDE = 2
    UNITSTRIDE = 3


class RegType(Enum):
    GPR = 0
    RA = GPR
    RB = GPR
    RC = GPR
    RS = GPR
    RSp = RS
    RT = GPR
    RTp = RT

    FPR = 1
    FRA = FPR
    FRAp = FRA
    FRB = FPR
    FRBp = FRB
    FRC = FPR
    FRS = FPR
    FRSp = FRS
    FRT = FPR
    FRTp = FRT

    CR_3BIT = 2 # CR field; the CR register is 32-bit
    BF = CR_3BIT
    BFA = CR_3BIT

    CR_5BIT = 3 # bit of the 32-bit CR register
    BA = CR_5BIT
    BB = CR_5BIT
    BC = CR_5BIT
    BI = CR_5BIT
    BT = CR_5BIT

    XER_BIT = 4   # XER bits, includes OV, OV32, SO, CA, CA32
    OV = XER_BIT
    OV32 = XER_BIT
    CA = XER_BIT
    CA32 = XER_BIT
    SO = XER_BIT

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, SVExtraReg):
            return cls.__members__.get(value.name)

        return super()._missing_(value)


FPTRANS_INSNS = (
    "fatan2", "fatan2s",
    "fatan2pi", "fatan2pis",
    "fpow", "fpows",
    "fpown", "fpowns",
    "fpowr", "fpowrs",
    "frootn", "frootns",
    "fhypot", "fhypots",
    "frsqrt", "frsqrts",
    "fcbrt", "fcbrts",
    "frecip", "frecips",
    "fexp2m1", "fexp2m1s",
    "flog2p1", "flog2p1s",
    "fexp2", "fexp2s",
    "flog2", "flog2s",
    "fexpm1", "fexpm1s",
    "flogp1", "flogp1s",
    "fexp", "fexps",
    "flog", "flogs",
    "fexp10m1", "fexp10m1s",
    "flog10p1", "flog10p1s",
    "fexp10", "fexp10s",
    "flog10", "flog10s",
    "fsin", "fsins",
    "fcos", "fcoss",
    "ftan", "ftans",
    "fasin", "fasins",
    "facos", "facoss",
    "fatan", "fatans",
    "fsinpi", "fsinpis",
    "fcospi", "fcospis",
    "ftanpi", "ftanpis",
    "fasinpi", "fasinpis",
    "facospi", "facospis",
    "fatanpi", "fatanpis",
    "fsinh", "fsinhs",
    "fcosh", "fcoshs",
    "ftanh", "ftanhs",
    "fasinh", "fasinhs",
    "facosh", "facoshs",
    "fatanh", "fatanhs",
    # fmin*/fmax* need to be replaced with fminmax
    # https://bugs.libre-soc.org/show_bug.cgi?id=1057
    # commented for now to make space for fmv/cvt
    # "fminnum08", "fminnum08s",
    # "fmaxnum08", "fmaxnum08s",
    # "fmin19", "fmin19s",
    # "fmax19", "fmax19s",
    # "fminnum19", "fminnum19s",
    # "fmaxnum19", "fmaxnum19s",
    # "fminc", "fmincs",
    # "fmaxc", "fmaxcs",
    # "fminmagnum08", "fminmagnum08s",
    # "fmaxmagnum08", "fmaxmagnum08s",
    # "fminmag19", "fminmag19s",
    # "fmaxmag19", "fmaxmag19s",
    # "fminmagnum19", "fminmagnum19s",
    # "fmaxmagnum19", "fmaxmagnum19s",
    # "fminmagc", "fminmagcs",
    # "fmaxmagc", "fmaxmagcs",
    "fmod", "fmods",
    "fremainder", "fremainders",
)


# supported instructions: make sure to keep up-to-date with CSV files
# just like everything else
_insns = [
    "NONE", "add", "addc", "addco", "adde", "addeo",
    "addi", "addic", "addic.", "addis",
    "addme", "addmeo", "addo", "addze", "addzeo",
    "addex",
    "addg6s",
    "and", "andc", "andi.", "andis.",
    "attn",
    "absdu", "absds",                         # AV bitmanip
    "absdacs", "absdacu",                     # AV bitmanip
    "avgadd",                                 # AV bitmanip
    "b", "bc", "bcctr", "bclr", "bctar",
    "bmask",                                  # AV bitmanip
    "bpermd",
    "cbcdtd",
    "cdtbcd",
    "cmp", "cmpb", "cmpeqb", "cmpi", "cmpl", "cmpli", "cmprb",
    "cntlzd", "cntlzw", "cnttzd", "cnttzw",
    "cprop", # AV bitmanip
    "crand", "crandc", "creqv",
    "crnand", "crnor", "cror", "crorc", "crxor",
    "darn",
    "dcbf", "dcbst", "dcbt", "dcbtst", "dcbz",
    "divd", "divde", "divdeo", "divdeu",
    "divdeuo", "divdo", "divdu", "divduo",
    "divmod2du",
    "divw", "divwe", "divweo",
    "divweu", "divweuo", "divwo", "divwu", "divwuo",
    "dsld", "dsld.", "dsrd", "dsrd.",
    "eieio", "eqv",
    "extsb", "extsh", "extsw", "extswsli",
    "fadd", "fadds", "fsub", "fsubs",                   # FP add / sub
    "fcfids", "fcfidus", "fsqrts", "fres", "frsqrtes",  # FP stuff
    "fdmadds",                                          # DCT FP 3-arg
    "fmsubs", "fmadds", "fnmsubs", "fnmadds",           # FP 3-arg
    "ffadds", "ffsubs", "ffmuls", "ffdivs",             # FFT FP 2-arg
    "ffmsubs", "ffmadds", "ffnmsubs", "ffnmadds",       # FFT FP 3-arg
    "fmul", "fmuls", "fdiv", "fdivs",                   # FP mul / div
    "fmr", "fabs", "fnabs", "fneg", "fcpsgn",           # FP move/abs/neg
    "fmvis",                                            # FP load immediate
    "fishmv",                                           # Float Replace Lower-Half Single, Immediate
    "fcvttg", "fcvttgo", "fcvttgs", "fcvttgso",
    "fmvtg", "fmvtgs",
    "fcvtfg", "fcvtfgs",
    "fmvfg", "fmvfgs",
    'grev', 'grev.', 'grevi', 'grevi.',
    'grevw', 'grevw.', 'grevwi', 'grevwi.',
    "hrfid", "icbi", "icbt", "isel", "isync",
    "lbarx", "lbz", "lbzcix", "lbzu", "lbzux", "lbzx",  # load byte
    "ld", "ldarx", "ldbrx", "ldu", "ldux", "ldx",       # load double
    # "lbzbr", "lbzubr",  # load byte SVP64 bit-reversed
    # "ldbr", "ldubr",    # load double SVP64 bit-reversed
    "lfs", "lfsx", "lfsu", "lfsux",                     # FP load single
    "lfd", "lfdx", "lfdu", "lfdux", "lfiwzx", "lfiwax",  # FP load double
    "lha", "lharx", "lhau", "lhaux", "lhax",            # load half
    "lhbrx", "lhz", "lhzu", "lhzux", "lhzx",            # more load half
    # "lhabr", "lhaubr",  # load half SVP64 bit-reversed
    # "lhzbr", "lhzubr",  # more load half SVP64 bit-reversed
    "lwa", "lwarx", "lwaux", "lwax", "lwbrx",           # load word
    "lwz", "lwzcix", "lwzu", "lwzux", "lwzx",           # more load word
    # "lwabr",           # load word SVP64 bit-reversed
    # "lwzbr", "lwzubr", # more load word SVP64 bit-reversed
    "maddedu", "maddedus",
    "maddhd", "maddhdu", "maddld",                      # INT multiply-and-add
    "maddsubrs",         # Integer DCT Butterfly Add Sub and Round Shift
    "maddrs",            # Integer DCT Butterfly Add and Accumulate and Round Shift
    "msubrs",            # Integer DCT Butterfly Subtract From and Round Shift
    "mcrf", "mcrxr", "mcrxrx", "mfcr/mfocrf",           # CR mvs
    "mfmsr", "mfspr",
    "minmax",                     # AV bitmanip
    "modsd", "modsw", "modud", "moduw",
    "mtcrf/mtocrf", "mtmsr", "mtmsrd", "mtspr",
    "mulhd", "mulhdu", "mulhw", "mulhwu", "mulld", "mulldo",
    "mulli", "mullw", "mullwo",
    "nand", "neg", "nego",
    "nop",
    "nor", "or", "orc", "ori", "oris",
    "pcdec",
    "popcntb", "popcntd", "popcntw",
    "prtyd", "prtyw",
    "rfid",
    "rldcl", "rldcr", "rldic", "rldicl", "rldicr", "rldimi",
    "rlwimi", "rlwinm",    "rlwnm",
    "setb",
    "setvl",  # https://libre-soc.org/openpower/sv/setvl
    "svindex",  # https://libre-soc.org/openpower/sv/remap
    "svremap",  # https://libre-soc.org/openpower/sv/remap - TEMPORARY
    "svshape",  # https://libre-soc.org/openpower/sv/remap/#svshape
    "svshape2",  # https://libre-soc.org/openpower/sv/remap/discussion TODO
    "svstep",  # https://libre-soc.org/openpower/sv/setvl
    "sim_cfg",
    "shadd", "shaddw", "shadduw",
    "slbia", "sld", "slw", "srad", "sradi",
    "sraw", "srawi", "srd", "srw",
    "stb", "stbcix", "stbcx", "stbu", "stbux", "stbx",
    "std", "stdbrx", "stdcx", "stdu", "stdux", "stdx",
    "stfs", "stfsx", "stfsu", "stfux", "stfsux",        # FP store single
    "stfd", "stfdx", "stfdu", "stfdux", "stfiwx",       # FP store double
    "sth", "sthbrx", "sthcx", "sthu", "sthux", "sthx",
    "stw", "stwbrx", "stwcx", "stwu", "stwux", "stwx",
    "subf", "subfc", "subfco", "subfe", "subfeo", "subfic",
    "subfme", "subfmeo", "subfo", "subfze", "subfzeo",
    "sync",
    "ternlogi",
    "td", "tdi",
    "tlbie", "tlbiel", "tlbsync",
    "tw", "twi",
    "wait",
    "xor", "xori", "xoris",
    *FPTRANS_INSNS,
]

# two-way lookup of instruction-to-index and vice-versa
insns = {}
asmidx = {}
for i, insn in enumerate(_insns):
    insns[i] = insn
    asmidx[insn] = i

# must be long enough to cover all instructions
asmlen = len(_insns).bit_length()

# Internal Operation numbering.  Add new opcodes here (FPADD, FPMUL etc.)


@unique
class MicrOp(Enum):
    OP_ILLEGAL = 0     # important that this is zero (see power_decoder.py)
    OP_NOP = 1
    OP_ADD = 2
    OP_ADDPCIS = 3
    OP_AND = 4
    OP_ATTN = 5
    OP_B = 6
    OP_BC = 7
    OP_BCREG = 8
    OP_BPERM = 9
    OP_CMP = 10
    OP_CMPB = 11
    OP_CMPEQB = 12
    OP_CMPRB = 13
    OP_CNTZ = 14
    OP_CRAND = 15
    OP_CRANDC = 16
    OP_CREQV = 17
    OP_CRNAND = 18
    OP_CRNOR = 19
    OP_CROR = 20
    OP_CRORC = 21
    OP_CRXOR = 22
    OP_DARN = 23
    OP_DCBF = 24
    OP_DCBST = 25
    OP_DCBT = 26
    OP_DCBTST = 27
    OP_DCBZ = 28
    OP_DIV = 29
    OP_DIVE = 30
    OP_EXTS = 31
    OP_EXTSWSLI = 32
    OP_ICBI = 33
    OP_ICBT = 34
    OP_ISEL = 35
    OP_ISYNC = 36
    OP_LOAD = 37
    OP_STORE = 38
    OP_MADDHD = 39
    OP_MADDHDU = 40
    OP_MADDLD = 41
    OP_MCRF = 42
    OP_MCRXR = 43
    OP_MCRXRX = 44
    OP_MFCR = 45
    OP_MFSPR = 46
    OP_MOD = 47
    OP_MTCRF = 48
    OP_MTSPR = 49
    OP_MUL_L64 = 50
    OP_MUL_H64 = 51
    OP_MUL_H32 = 52
    OP_OR = 53
    OP_POPCNT = 54
    OP_PRTY = 55
    OP_RLC = 56
    OP_RLCL = 57
    OP_RLCR = 58
    OP_SETB = 59
    OP_SHL = 60
    OP_SHR = 61
    OP_SYNC = 62
    OP_TRAP = 63
    OP_XOR = 67
    OP_SIM_CONFIG = 68
    OP_CROP = 69
    OP_RFID = 70
    OP_MFMSR = 71
    OP_MTMSRD = 72
    OP_SC = 73
    OP_MTMSR = 74
    OP_TLBIE = 75
    OP_SETVL = 76
    OP_FPOP = 77  # temporary: replace with actual ops
    OP_FPOP_I = 78  # temporary: replace with actual ops
    OP_FP_MADD = 79
    OP_SVREMAP = 80
    OP_SVSHAPE = 81
    OP_SVSTEP = 82
    OP_ADDG6S = 83
    OP_CDTBCD = 84
    OP_CBCDTD = 85
    OP_TERNLOG = 86
    OP_FETCH_FAILED = 87
    OP_GREV = 88
    OP_MINMAX = 89
    OP_AVGADD = 90
    OP_ABSDIFF = 91
    OP_ABSADD = 92
    OP_CPROP = 93
    OP_BMASK = 94
    OP_SVINDEX = 95
    OP_FMVIS = 96
    OP_FISHMV = 97
    OP_PCDEC = 98
    OP_MADDEDU = 99
    OP_DIVMOD2DU = 100
    OP_DSHL = 101
    OP_DSHR = 102
    OP_SHADD = 103
    OP_MADDSUBRS = 104
    OP_MADDRS = 105
    OP_MSUBRS = 106


class In1Sel(Enum):
    NONE = 0
    RA = 1
    RA_OR_ZERO = 2
    SPR = 3
    RS = 4  # for some ALU/Logical operations
    RSp = RS
    FRA = 5
    FRAp = FRA
    FRS = 6
    FRSp = FRS
    FRT = 7
    CIA = 8 # for addpcis
    RT = 9


class In2Sel(Enum):
    NONE = 0
    RB = 1
    CONST_UI = 2
    CONST_SI = 3
    CONST_UI_HI = 4
    CONST_SI_HI = 5
    CONST_LI = 6
    CONST_BD = 7
    CONST_DS = 8
    CONST_M1 = 9
    CONST_SH = 10
    CONST_SH32 = 11
    SPR = 12
    RS = 13  # for shiftrot (M-Form)
    RSp = RS
    FRB = 14
    FRBp = FRB
    CONST_SVD = 15  # for SVD-Form
    CONST_SVDS = 16  # for SVDS-Form
    CONST_XBI = 17
    CONST_DXHI4 = 18 # for addpcis
    CONST_DQ = 19 # for ld/st-quad


class In3Sel(Enum):
    NONE = 0
    RS = 1
    RSp = RS
    RB = 2  # for shiftrot (M-Form)
    FRS = 3
    FRSp = FRS
    FRC = 4
    RC = 5  # for SVP64 bit-reverse LD/ST
    RT = 6  # for ternlog[i]
    RTp = RT
    FRA = 7


class OutSel(Enum):
    NONE = 0
    RT = 1
    RTp = RT
    RA = 2
    SPR = 3
    RT_OR_ZERO = 4
    FRT = 5
    FRTp = FRT
    FRS = 6
    FRSp = FRS
    RS = 7
    RSp = RS
    FRA = 8


@unique
class LDSTLen(Enum):
    NONE = 0
    is1B = 1
    is2B = 2
    is4B = 4
    is8B = 8

# Backward compatibility
LdstLen = LDSTLen


@unique
class LDSTMode(Enum):
    NONE = 0
    update = 1
    cix = 2
    cx = 3


@unique
class RCOE(Enum):
    NONE = 0
    ONE = 1
    RC = 2    # includes OE
    RC_ONLY = 3  # does not include OE


@unique
class CryIn(Enum):
    ZERO = 0
    ONE = 1
    CA = 2
    OV = 3


@unique
class CRInSel(Enum):
    NONE = 0
    CR0 = 1
    BI = 2
    BFA = 3
    BA_BB = 4
    BC = 5
    WHOLE_REG = 6
    CR1 = 7
    BA = 8


@unique
class CRIn2Sel(Enum):
    NONE = 0
    BB = 1


@unique
class CROutSel(Enum):
    NONE = 0
    CR0 = 1
    BF = 2
    BT = 3
    WHOLE_REG = 4
    CR1 = 5


# SPRs - Special-Purpose Registers.  See V3.0B Figure 18 p971 and
# http://libre-riscv.org/openpower/isatables/sprs.csv
# http://bugs.libre-riscv.org/show_bug.cgi?id=261
# http://bugs.libre-riscv.org/show_bug.cgi?id=859 - KAIVB

def get_spr_enum(full_file):
    """get_spr_enum - creates an Enum of SPRs, dynamically
    has the option to reduce the enum to a much shorter list.
    this saves drastically on the size of the regfile
    """
    short_list = {'PIDR', 'DAR', 'PRTBL', 'DSISR', 'SVSRR0', 'SVSTATE',
                  'SVSTATE0', 'SVSTATE1', 'SVSTATE2', 'SVSTATE3',
                  'SPRG0_priv', 'SPRG1_priv', 'SPRG2_priv', 'SPRG3_priv',
                  'SPRG0', 'SPRG1', 'SPRG2', 'SPRG3', 'KAIVB',
                  # hmmm should not be including these, they are FAST regs
                  'CTR', 'LR', 'TAR', 'SRR0', 'SRR1', 'XER', 'DEC', 'TB', 'TBU',
                  'HSRR0', 'HSRR1', 'HSPRG0', 'HSPRG1',
                  }
    spr_csv = []
    for row in get_csv("sprs.csv"):
        if full_file or row['SPR'] in short_list:
            spr_csv.append(row)

    spr_info = namedtuple('spr_info', 'SPR priv_mtspr priv_mfspr length idx')
    spr_dict = {}
    spr_byname = {}
    for row in spr_csv:
        info = spr_info(SPR=row['SPR'], priv_mtspr=row['priv_mtspr'],
                        priv_mfspr=row['priv_mfspr'], length=int(row['len']),
                        idx=int(row['Idx']))
        spr_dict[int(row['Idx'])] = info
        spr_byname[row['SPR']] = info
    fields = [(row['SPR'], int(row['Idx'])) for row in spr_csv]
    SPR = Enum('SPR', fields)
    return SPR, spr_dict, spr_byname


SPRfull, spr_dict, spr_byname = get_spr_enum(full_file=True)
SPRreduced, _, _ = get_spr_enum(full_file=False)

XER_bits = {
    'SO': 32,
    'OV': 33,
    'CA': 34,
    'OV32': 44,
    'CA32': 45
}

MSRSpec = namedtuple("MSRSpec", ["dr", "pr", "sf"])

if __name__ == '__main__':
    # find out what the heck is in SPR enum :)
    print("sprs full", len(SPRfull))
    print(dir(SPRfull))
    print("sprs reduced", len(SPRreduced))
    print(dir(SPRreduced))
    print(dir(Enum))
    print(SPRfull.__members__['TAR'])
    for x in SPRfull:
        print("full", x, x.value, str(x), x.name)
    for x in SPRreduced:
        print("reduced", x, x.value, str(x), x.name)

    print("function", Function.ALU.name)
