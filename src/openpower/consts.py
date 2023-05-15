import enum as _enum


# Can't think of a better place to put these functions.
# Return an arbitrary subfield of a larger field.
def field_slice(msb0_start, msb0_end, field_width=64):
    """field_slice

    Answers with a subfield slice of the signal r ("register"),
    where the start and end bits use IBM "MSB 0" conventions.

    see: https://en.wikipedia.org/wiki/Bit_numbering#MSB_0_bit_numbering

    * assertion: msb0_start < msb0_end.
    * The range specified is inclusive on both ends.
    * field_width specifies the total number of bits (note: not bits-1)
    """
    if msb0_start >= msb0_end:
        raise ValueError(
            "start ({}) must be less than end ({})".format(msb0_start, msb0_end)
        )
    # sigh.  MSB0 (IBM numbering) is inverted.  converting to python
    # we *swap names* so as not to get confused by having "end, start"
    lsb0_end = (field_width-1) - msb0_start
    lsb0_start = (field_width-1) - msb0_end

    return slice(lsb0_start, lsb0_end + 1)


def field(r, msb0_start, msb0_end=None, field_width=64):
    """Answers with a subfield of the signal r ("register"), where
    the start and end bits use IBM conventions.  start < end, if
    end is provided.  The range specified is inclusive on both ends.

    Answers with a subfield of the signal r ("register"),
    where the start and end bits use IBM "MSB 0" conventions.
    If end is not provided, a single bit subfield is returned.

    see: https://en.wikipedia.org/wiki/Bit_numbering#MSB_0_bit_numbering

    * assertion: msb0_start < msb0_end.
    * The range specified is inclusive on both ends.
    * field_width specifies the total number of bits (note: not bits-1)

    Example usage:

        comb += field(insn, 0, 6, field_width=32).eq(17)
        # NOTE: NEVER DIRECTLY ACCESS OPCODE FIELDS IN INSTRUCTIONS.
        # This example is purely for illustrative purposes only.
        # Use self.fields.FormXYZ.etcetc instead.

        comb += field(msr, MSRb.TEs, MSRb.TEe).eq(0)

    Proof by substitution:

           field(insn, 0, 6, field_width=32).eq(17)
        == insn[field_slice(0, 6, field_width=32)].eq(17)
        == insn[slice((31-6), (31-0)+1)].eq(17)
        == insn[slice(25, 32)].eq(17)
        == insn[25:32].eq(17)

           field(msr, MSRb.TEs, MSRb.TEe).eq(0)
        == field(msr, 53, 54).eq(0)
        == msr[field_slice(53, 54)].eq(0)
        == msr[slice((63-54), (63-53)+1)].eq(0)  # note cross-over!
        == msr[slice(9, 11)].eq(0)
        == msr[9:11].eq(0)
    """
    if msb0_end is None:
        return r[(field_width - 1) - msb0_start]
    else:
        return r[field_slice(msb0_start, msb0_end, field_width)]


# just... don't ask.  MSB0 is a massive pain in the neck.
# this module, aside from creating various field constants,
# helps out by creating alternative (identical) classes with
# a "b" name to indicate "MSB0 big-endian".
class _Const(_enum.IntEnum):
    pass


class _ConstLEMeta(_enum.EnumMeta):
    def __call__(metacls, *args, **kwargs):
        if len(args) > 1:
            names = args[1]
        else:
            names = kwargs.pop("names")

        if isinstance(names, type) and issubclass(names, _enum.Enum):
            names = dict(names.__members__)
        if isinstance(names, dict):
            names = tuple(names.items())

        msb = kwargs.pop("msb")
        names = {key:(msb - value) for (key, value) in names}

        return super().__call__(*args, names=names, **kwargs)


class _ConstLE(_Const, metaclass=_ConstLEMeta):
    pass


# Listed in V3.0B Book III Chap 4.2.1
# MSR bit numbers, *bigendian* order (PowerISA format)
# use this in the simulator
class MSRb(_Const):
    SF  = 0     # Sixty-Four bit mode
    HV  = 3     # Hypervisor state
    UND = 5     # Undefined behavior state (see Bk 2, Sect. 3.2.1)
    TSs = 29    # Transactional State (subfield)
    TSe = 30    # Transactional State (subfield)
    TM  = 31    # Transactional Memory Available
    VEC = 38    # Vector Available
    VSX = 40    # VSX Available
    S   = 41    # Secure state
    EE  = 48    # External interrupt Enable
    PR  = 49    # PRoblem state
    FP  = 50    # FP available
    ME  = 51    # Machine Check int enable
    FE0 = 52    # Floating-Point Exception Mode 0
    TEs = 53    # Trace Enable (subfield)
    TEe = 54    # Trace Enable (subfield)
    FE1 = 55    # Floating-Point Exception Mode 1
    IR  = 58    # Instruction Relocation
    DR  = 59    # Data Relocation
    PMM = 60    # Performance Monitor Mark
    RI  = 62    # Recoverable Interrupt
    LE  = 63    # Little Endian

# use this inside the HDL (where everything is little-endian)
MSR = _ConstLE("MSR", names=MSRb, msb=63)


# Listed in V3.0B Book III 7.5.9 "Program Interrupt"

# note that these correspond to trap_input_record.traptype bits 0,1,2,3,4
# (TODO: add more?)
# IMPORTANT: when adding extra bits here it is CRITICALLY IMPORTANT
# to expand traptype to cope with the increased range

# use this in the simulator
class PIb(_Const):
    INVALID      = 33    # 1 for an invalid mem err
    PERMERR      = 35    # 1 for an permanent mem err
    TM_BAD_THING = 42    # 1 for a TM Bad Thing type interrupt
    FP           = 43    # 1 if FP exception
    ILLEG        = 44    # 1 if illegal instruction (not doing hypervisor)
    PRIV         = 45    # 1 if privileged interrupt
    TRAP         = 46    # 1 if exception is "trap" type
    ADR          = 47    # 0 if SRR0 = address of instruction causing exception

# and use this in the HDL
PI = _ConstLE("PI", names=PIb, msb=63)


# see traptype (and trap main_stage.py)
# IMPORTANT: when adding extra bits here it is CRITICALLY IMPORTANT
# to expand traptype to cope with the increased range

class TT:
    FP = 1<<0
    PRIV = 1<<1
    TRAP = 1<<2
    ADDR = 1<<3
    EINT = 1<<4  # external interrupt
    DEC = 1<<5   # decrement counter
    MEMEXC = 1<<6 # LD/ST exception
    ILLEG = 1<<7 # currently the max
    # TODO: support for TM_BAD_THING (not included yet in trap main_stage.py)
    size = 8 # MUST update this to contain the full number of Trap Types


# EXTRA3 3-bit subfield (spec)
class SPECb(_Const):
    VEC = 0  # 1 for vector, 0 for scalar
    MSB = 1  # augmented register number, MSB
    LSB = 2  # augmented register number, LSB


SPEC_SIZE = 3
SPEC_AUG_SIZE = 2  # augmented subfield size (MSB+LSB above)
SPEC = _ConstLE("SPEC", names=SPECb, msb=SPEC_SIZE-1)



# EXTRA field, with EXTRA2 subfield encoding
class EXTRA2b(_Const):
    IDX0_VEC = 0
    IDX0_MSB = 1
    IDX1_VEC = 2
    IDX1_MSB = 3
    IDX2_VEC = 4
    IDX2_MSB = 5
    IDX3_VEC = 6
    IDX3_MSB = 7
    RESERVED = 8


EXTRA2_SIZE = 9
EXTRA2 = _ConstLE("EXTRA2", names=EXTRA2b, msb=EXTRA2_SIZE-1)

# sigh, make these convenience-modifications afterwards (aliases)
# see RM-2P-1S1D-PU in https://libre-soc.org/openpower/sv/svp64
EXTRA2b.PACK_en   = EXTRA2b.IDX2_VEC
EXTRA2b.UNPACK_en = EXTRA2b.IDX2_MSB
EXTRA2.PACK_en    = EXTRA2.IDX2_VEC
EXTRA2.UNPACK_en  = EXTRA2.IDX2_MSB


# EXTRA field, with EXTRA3 subfield encoding
class EXTRA3:
    IDX0 = [0, 1, 2]
    IDX1 = [3, 4, 5]
    IDX2 = [6, 7, 8]
    MASK = [6, 7, 8]


EXTRA3_SIZE = 9


# SVP64 ReMapped Field (from v3.1 EXT001 Prefix)
class SVP64P:
    OPC = range(0, 6)
    SVP64_7_9 = [7, 9]
    RM = [6, 8] + list(range(10, 32))

# 24 bits in RM
SVP64P_SIZE = 24


# CR SVP64 offsets
class SVP64CROffs:
    CR0 = 0    # TODO: increase when CRs are expanded to 128
    CR1 = 1    # TODO: increase when CRs are expanded to 128
    CRPred = 4 # TODO: increase when CRs are expanded to 128


class SVP64MODEb(_Const):
    # mode bits
    MOD2_MSB = 0
    MOD2_LSB = 1
    MOD3 = 3
    SEA = 2
    # when predicate not set: 0=ignore/skip 1=zero
    DZ = 3  # for destination
    SZ = 4  # for source
    ZZ = 3  # for both sz/dz, on all but CR-ops, which, whoops, is RM bit 6.
    # for branch-conditional
    BC_SNZ = 3  # for branch-conditional mode
    BC_VLI = 2  # for VL include/exclude on VLSET mode
    BC_VLSET = 1 # VLSET mode
    BC_CTRTEST = 0 # CTR-test mode
    # reduce mode
    REDUCE = 2  # 0=normal predication 1=reduce mode
    CRM = 4  # CR mode on reduce (Rc=1) 0=some 1=all
    RG = 4   # Reverse-gear on reduce
    CROP_RG = 3   # Reverse-gear on reduce CR-ops
    # saturation mode
    N = 2  # saturation signed mode 0=signed 1=unsigned
    # ffirst and predicate result modes
    INV = 2  # invert CR sense 0=set 1=unset
    CR_MSB = 3  # CR bit to update (with Rc=1)
    CR_LSB = 4
    VLI = 3
    RC1 = 4  # update CR as if Rc=1 (when Rc=0)
    # LD immediate els (element-stride) locations, depending on mode
    ELS_NORMAL = 4
    ELS_FFIRST_PRED = 3
    ELS_SAT = 4
    LDI_POST = 2 # LD-Immediate Post/FF Mode
    LDI_PI = 3 # LD-Immediate Post-Increment
    LDI_FF = 4 # LD-Immediate Fault-First
    # LDST Indexed
    LDIDX_ELS = 0 # Indexed element-strided
    # LDST VLI for ffirst is in bit 0
    LDST_VLI = 0
    # BO bits
    BO_MSB = 2
    BO_LSB = 4


SVP64MODE_SIZE = 5


SVP64MODE = _ConstLE("SVP64MODE", names=SVP64MODEb, msb=SVP64MODE_SIZE-1)


# add subfields to use with nmutil.sel
SVP64MODE.MOD2 = [0, 1]
SVP64MODE.CR = [3, 4]


# CR sub-fields
class CRb(_Const):
    LT = 0
    GT = 1
    EQ = 2
    SO = 3


CR_SIZE = 4


CR = _ConstLE("CR", names=CRb, msb=CR_SIZE-1)


# POWER9 Register Files
# XXX these are specific to Libre-SOC's decoder. really, they
# should be in libre-soc.  however... long story: because the
# PowerDecoder2 has been moved to openpower-isa, and its decoding
# depends on that, then... whoops.

# "State" Regfile
class StateRegsEnum:
    PC = 0
    MSR = 1
    SVSTATE = 2
    DEC = 3
    TB = 4
    N_REGS = 5 # maximum number of regs

# Fast SPRs Regfile
class FastRegsEnum:
    LR = 0
    CTR = 1
    SRR0 = 2
    SRR1 = 3
    HSRR0 = 4
    HSRR1 = 5
    SPRG0 = 6
    SPRG1 = 7
    SPRG2 = 8
    SPRG3 = 9
    HSPRG0 = 10
    HSPRG1 = 11
    XER = 12 # non-XER bits
    TAR = 13
    SVSRR0 = 14
    # only one spare!
    N_REGS = 15 # maximum number of regs

# XER Regfile
class XERRegsEnum:
    SO=0 # this is actually 2-bit but we ignore 1 bit of it
    CA=1 # CA and CA32
    OV=2 # OV and OV32
    N_REGS = 3 # maximum number of regs


if __name__ == '__main__':
    print ("EXTRA2 pack", EXTRA2.PACK_en, EXTRA2.PACK_en.value)
