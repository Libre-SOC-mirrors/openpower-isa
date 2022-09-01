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
    def _missing_(cls, value):
        if isinstance(value, str):
            try:
                if value == "":
                    value = 0
                else:
                    value = int(value, 0)
            except ValueError:
                pass
        keys = {item.name:item for item in cls}
        values = {item.value:item for item in cls}
        item = keys.get(value, values.get(value))
        if item is None:
            raise ValueError(value)
        return item


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
    SVM = 32  # Simple-V SHAPE mode - TEMPORARY TEMPORARY TEMPORARY
    SVRM = 33  # Simple-V REMAP mode
    TLI = 34  # ternlogi
    XB = 35
    BM2 = 36 # bmask
    SVI = 37  # Simple-V Index Mode
    VA2 = 38
    SVC = 39
    SVR = 40

# Simple-V svp64 fields https://libre-soc.org/openpower/sv/svp64/


class SVMode(Enum):
    NORMAL = auto()
    LDST = auto()
    BRANCH = auto()
    CROP = auto()


@unique
class SVPtype(Enum):
    NONE = 0
    P1 = 1
    P2 = 2

    @classmethod
    def _missing_(cls, value):
        return {"1P": SVPtype.P1, "2P": SVPtype.P2}[value]


@unique
class SVEtype(Enum):
    NONE = 0
    EXTRA2 = 1
    EXTRA3 = 2


@unique
class SVExtra(Enum):
    NONE = 0
    Idx0 = 1
    Idx1 = 2
    Idx2 = 3
    Idx3 = 4
    Idx_1_2 = 5  # due to weird BA/BB for crops

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

    @classmethod
    def _missing_(cls, value):
        selectors = (
            In1Sel, In2Sel, In3Sel, CRInSel,
            OutSel, CROutSel,
        )
        if isinstance(value, selectors):
            return cls.__members__.get(value.name, cls.NONE)
        return super()._missing_(value)


@unique
class SVP64PredMode(Enum):
    ALWAYS = 0
    INT = 1
    CR = 2


@unique
class SVP64PredInt(Enum):
    ALWAYS = 0
    R3_UNARY = 1
    R3 = 2
    R3_N = 3
    R10 = 4
    R10_N = 5
    R30 = 6
    R30_N = 7


@unique
class SVP64PredCR(Enum):
    LT = 0
    GE = 1
    GT = 2
    LE = 3
    EQ = 4
    NE = 5
    SO = 6
    NS = 7


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
class SVP64width(Enum):
    DEFAULT = 0
    EW_32 = 1
    EW_16 = 2
    EW_8 = 3


@unique
class SVP64subvl(Enum):
    VEC1 = 0
    VEC2 = 1
    VEC3 = 2
    VEC4 = 3


@unique
class SVP64sat(Enum):
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
    RT = GPR

    FPR = 1
    FRA = FPR
    FRB = FPR
    FRC = FPR
    FRS = FPR
    FRT = FPR

    CR_REG = 2
    BF = CR_REG
    BFA = CR_REG

    CR_BIT = 3
    BA = CR_BIT
    BB = CR_BIT
    BC = CR_BIT
    BI = CR_BIT
    BT = CR_BIT
    BFT = CR_BIT


# supported instructions: make sure to keep up-to-date with CSV files
# just like everything else
_insns = [
    "NONE", "add", "addc", "addco", "adde", "addeo",
    "addi", "addic", "addic.", "addis",
    "addme", "addmeo", "addo", "addze", "addzeo",
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
    "divdeuo", "divdo", "divdu", "divduo", "divw", "divwe", "divweo",
    "divweu", "divweuo", "divwo", "divwu", "divwuo",
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
    "fsins", "fcoss",                                   # FP SIN/COS
    "fmvis",                                            # FP load immediate
    "fishmv",                                           # Float Replace Lower-Half Single, Immediate
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
    "maddhd", "maddhdu", "maddld",                      # INT multiply-and-add
    "mcrf", "mcrxr", "mcrxrx", "mfcr/mfocrf",           # CR mvs
    "mfmsr", "mfspr",
    "mins", "maxs", "minu", "maxu",                     # AV bitmanip
    "modsd", "modsw", "modud", "moduw",
    "mtcrf/mtocrf", "mtmsr", "mtmsrd", "mtspr",
    "mulhd", "mulhdu", "mulhw", "mulhwu", "mulld", "mulldo",
    "mulli", "mullw", "mullwo",
    "nand", "neg", "nego",
    "nop",
    "nor", "or", "orc", "ori", "oris",
    "popcntb", "popcntd", "popcntw",
    "prtyd", "prtyw",
    "rfid",
    "rldcl", "rldcr", "rldic", "rldicl", "rldicr", "rldimi",
    "rlwimi", "rlwinm",    "rlwnm",
    "setb",
    "setvl",  # https://libre-soc.org/openpower/sv/setvl
    "svindex",  # https://libre-soc.org/openpower/sv/remap
    "svremap",  # https://libre-soc.org/openpower/sv/remap - TEMPORARY
    "svshape",  # https://libre-soc.org/openpower/sv/remap
    "svstep",  # https://libre-soc.org/openpower/sv/setvl
    "sim_cfg",
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


@unique
class In1Sel(Enum):
    NONE = 0
    RA = 1
    RA_OR_ZERO = 2
    SPR = 3
    RS = 4  # for some ALU/Logical operations
    FRA = 5
    FRS = 6


@unique
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
    FRB = 14
    CONST_SVD = 15  # for SVD-Form
    CONST_SVDS = 16  # for SVDS-Form
    CONST_XBI = 17


@unique
class In3Sel(Enum):
    NONE = 0
    RS = 1
    RB = 2  # for shiftrot (M-Form)
    FRS = 3
    FRC = 4
    RC = 5  # for SVP64 bit-reverse LD/ST
    RT = 6  # for ternlog[i]


@unique
class OutSel(Enum):
    NONE = 0
    RT = 1
    RA = 2
    SPR = 3
    RT_OR_ZERO = 4
    FRT = 5
    FRS = 6


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
class RC(Enum):
    NONE = 0
    ONE = 1
    RC_OE = 2    # includes OE
    RC_ONLY = 3  # does not include OE


@unique
class CryIn(Enum):
    ZERO = 0
    ONE = 1
    CA = 2
    # TODO OV = 3


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
