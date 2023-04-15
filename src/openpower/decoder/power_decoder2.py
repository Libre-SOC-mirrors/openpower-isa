"""Power ISA Decoder second stage

based on Anton Blanchard microwatt decode2.vhdl

Note: OP_TRAP is used for exceptions and interrupts (micro-code style) by
over-riding the internal opcode when an exception is needed.
"""

from nmigen import Module, Elaboratable, Signal, Mux, Const, Cat, Repl, Record
from nmigen.cli import rtlil
from nmutil.util import sel

from nmutil.picker import PriorityPicker
from nmutil.iocontrol import RecordObject
from nmutil.extend import exts

from openpower.exceptions import LDSTException

from openpower.decoder.power_svp64_prefix import SVP64PrefixDecoder
from openpower.decoder.power_svp64_extra import SVP64CRExtra, SVP64RegExtra
from openpower.decoder.power_svp64_rm import (SVP64RMModeDecode,
                                              sv_input_record_layout,
                                              SVP64RMMode)
from openpower.sv.svp64 import SVP64Rec

from openpower.decoder.power_regspec_map import regspec_decode_read
from openpower.decoder.power_decoder import (create_pdecode,
                                             create_pdecode_svp64_ldst,
                                             PowerOp)
from openpower.decoder.power_enums import (MicrOp, CryIn, Function,
                                           CRInSel, CROutSel,
                                           LdstLen, In1Sel, In2Sel, In3Sel,
                                           OutSel, SPRfull, SPRreduced,
                                           RCOE, SVP64LDSTmode, LDSTMode,
                                           SVEXTRA, SVEType, SVPType)
from openpower.decoder.decode2execute1 import (Decode2ToExecute1Type, Data,
                                               Decode2ToOperand)

from openpower.consts import (MSR, SPEC, EXTRA2, EXTRA3, SVP64P, field,
                              SPEC_SIZE, SPECb, SPEC_AUG_SIZE, SVP64CROffs,
                              FastRegsEnum, XERRegsEnum, TT)

from openpower.state import CoreState
from openpower.util import (spr_to_fast, spr_to_state, log)


def decode_spr_num(spr):
    return Cat(spr[5:10], spr[0:5])


def instr_is_priv(m, op, insn):
    """determines if the instruction is privileged or not
    """
    comb = m.d.comb
    is_priv_insn = Signal(reset_less=True)
    with m.Switch(op):
        with m.Case(MicrOp.OP_ATTN, MicrOp.OP_MFMSR, MicrOp.OP_MTMSRD,
                    MicrOp.OP_MTMSR, MicrOp.OP_RFID):
            comb += is_priv_insn.eq(1)
        with m.Case(MicrOp.OP_TLBIE):
            comb += is_priv_insn.eq(1)
        with m.Case(MicrOp.OP_MFSPR, MicrOp.OP_MTSPR):
            with m.If(insn[20]):  # field XFX.spr[-1] i think
                comb += is_priv_insn.eq(1)
    return is_priv_insn


class SPRMap(Elaboratable):
    """SPRMap: maps POWER9 SPR numbers to internal enum values, fast and slow
    """

    def __init__(self, regreduce_en):
        self.regreduce_en = regreduce_en
        if regreduce_en:
            SPR = SPRreduced
        else:
            SPR = SPRfull

        self.spr_i = Signal(10, reset_less=True)
        self.spr_o = Data(SPR, name="spr_o")
        self.fast_o = Data(4, name="fast_o")
        self.state_o = Data(3, name="state_o")

    def elaborate(self, platform):
        m = Module()
        if self.regreduce_en:
            SPR = SPRreduced
        else:
            SPR = SPRfull
        with m.Switch(self.spr_i):
            for i, x in enumerate(SPR):
                with m.Case(x.value):
                    m.d.comb += self.spr_o.data.eq(i)
                    m.d.comb += self.spr_o.ok.eq(1)
            for x, v in spr_to_fast.items():
                with m.Case(x.value):
                    m.d.comb += self.fast_o.data.eq(v)
                    m.d.comb += self.fast_o.ok.eq(1)
            for x, v in spr_to_state.items():
                with m.Case(x.value):
                    m.d.comb += self.state_o.data.eq(v)
                    m.d.comb += self.state_o.ok.eq(1)
        return m


class DecodeA(Elaboratable):
    """DecodeA from instruction

    decodes register RA, implicit and explicit CSRs
    """

    def __init__(self, dec, op, regreduce_en):
        self.regreduce_en = regreduce_en
        if self.regreduce_en:
            SPR = SPRreduced
        else:
            SPR = SPRfull
        self.dec = dec
        self.op = op
        self.sel_in = Signal(In1Sel, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.reg_out = Data(5, name="reg_a")
        self.spr_out = Data(SPR, "spr_a")
        self.fast_out = Data(4, "fast_a")
        self.state_out = Data(3, "state_a")
        self.sv_nz = Signal(1)

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        op = self.op
        reg = self.reg_out
        m.submodules.sprmap = sprmap = SPRMap(self.regreduce_en)

        # select Register A field, if *full 7 bits* are zero (2 more from SVP64)
        ra = Signal(5, reset_less=True)
        comb += ra.eq(self.dec.RA)
        with m.If((self.sel_in == In1Sel.RA) |
                  ((self.sel_in == In1Sel.RA_OR_ZERO) &
                   ((ra != Const(0, 5)) | (self.sv_nz != Const(0, 1))))):
            comb += reg.data.eq(ra)
            comb += reg.ok.eq(1)

        # some Logic/ALU ops have RS as the 3rd arg, but no "RA".
        # moved it to 1st position (in1_sel)... because
        rs = Signal(5, reset_less=True)
        comb += rs.eq(self.dec.RS)
        with m.If(self.sel_in == In1Sel.RS):
            comb += reg.data.eq(rs)
            comb += reg.ok.eq(1)

        # select Register FRA field,
        fra = Signal(5, reset_less=True)
        comb += fra.eq(self.dec.FRA)
        with m.If(self.sel_in == In1Sel.FRA):
            comb += reg.data.eq(fra)
            comb += reg.ok.eq(1)

        # select Register FRS field,
        frs = Signal(5, reset_less=True)
        comb += frs.eq(self.dec.FRS)
        with m.If(self.sel_in == In1Sel.FRS):
            comb += reg.data.eq(frs)
            comb += reg.ok.eq(1)

        # decode Fast-SPR based on instruction type
        with m.Switch(op.internal_op):

            # BC or BCREG: implicit register (CTR) NOTE: same in DecodeOut
            with m.Case(MicrOp.OP_BC):
                with m.If(~self.dec.BO[2]):  # 3.0B p38 BO2=0, use CTR reg
                    # constant: CTR
                    comb += self.fast_out.data.eq(FastRegsEnum.CTR)
                    comb += self.fast_out.ok.eq(1)
            with m.Case(MicrOp.OP_BCREG):
                xo9 = self.dec.FormXL.XO[9]  # 3.0B p38 top bit of XO
                xo5 = self.dec.FormXL.XO[5]  # 3.0B p38
                with m.If(xo9 & ~xo5):
                    # constant: CTR
                    comb += self.fast_out.data.eq(FastRegsEnum.CTR)
                    comb += self.fast_out.ok.eq(1)

            # MFSPR move from SPRs
            with m.Case(MicrOp.OP_MFSPR):
                spr = Signal(10, reset_less=True)
                comb += spr.eq(decode_spr_num(self.dec.SPR))  # from XFX
                comb += sprmap.spr_i.eq(spr)
                comb += self.spr_out.eq(sprmap.spr_o)
                comb += self.fast_out.eq(sprmap.fast_o)
                comb += self.state_out.eq(sprmap.state_o)

        return m


class DecodeAImm(Elaboratable):
    """DecodeA immediate from instruction

    decodes register RA, whether immediate-zero, implicit and
    explicit CSRs.  SVP64 mode requires 2 extra bits
    """

    def __init__(self, dec):
        self.dec = dec
        self.sel_in = Signal(In1Sel, reset_less=True)
        self.immz_out = Signal(reset_less=True)
        self.sv_nz = Signal(1)  # EXTRA bits from SVP64

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        # zero immediate requested
        ra = Signal(5, reset_less=True)
        comb += ra.eq(self.dec.RA)
        with m.If((self.sel_in == In1Sel.RA_OR_ZERO) &
                  (ra == Const(0, 5)) &
                  (self.sv_nz == Const(0, 1))):
            comb += self.immz_out.eq(1)

        return m


class DecodeB(Elaboratable):
    """DecodeB from instruction

    decodes register RB, different forms of immediate (signed, unsigned),
    and implicit SPRs.  register B is basically "lane 2" into the CompUnits.
    by industry-standard convention, "lane 2" is where fully-decoded
    immediates are muxed in.
    """

    def __init__(self, dec, op):
        self.dec = dec
        self.op = op
        self.sel_in = Signal(In2Sel, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.reg_out = Data(7, "reg_b")
        self.reg_isvec = Signal(1, name="reg_b_isvec")  # TODO: in reg_out
        self.fast_out = Data(4, "fast_b")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        op = self.op
        reg = self.reg_out

        # select Register B field
        with m.Switch(self.sel_in):
            with m.Case(In2Sel.FRB):
                comb += reg.data.eq(self.dec.FRB)
                comb += reg.ok.eq(1)
            with m.Case(In2Sel.RB):
                comb += reg.data.eq(self.dec.RB)
                comb += reg.ok.eq(1)
            with m.Case(In2Sel.RS):
                # for M-Form shiftrot
                comb += reg.data.eq(self.dec.RS)
                comb += reg.ok.eq(1)

        # decode SPR2 based on instruction type
        # BCREG implicitly uses LR or TAR for 2nd reg
        # CTR however is already in fast_spr1 *not* 2.
        with m.If(op.internal_op == MicrOp.OP_BCREG):
            xo9 = self.dec.FormXL.XO[9]  # 3.0B p38 top bit of XO
            xo5 = self.dec.FormXL.XO[5]  # 3.0B p38
            with m.If(~xo9):
                comb += self.fast_out.data.eq(FastRegsEnum.LR)
                comb += self.fast_out.ok.eq(1)
            with m.Elif(xo5):
                comb += self.fast_out.data.eq(FastRegsEnum.TAR)
                comb += self.fast_out.ok.eq(1)

        return m


class DecodeBImm(Elaboratable):
    """DecodeB immediate from instruction
    """

    def __init__(self, dec):
        self.dec = dec
        self.sel_in = Signal(In2Sel, reset_less=True)
        self.imm_out = Data(64, "imm_b")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        # select Register B Immediate
        with m.Switch(self.sel_in):
            with m.Case(In2Sel.CONST_UI):  # unsigned
                comb += self.imm_out.data.eq(self.dec.UI)
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_SI):  # sign-extended 16-bit
                si = Signal(16, reset_less=True)
                comb += si.eq(self.dec.SI)
                comb += self.imm_out.data.eq(exts(si, 16, 64))
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_SI_HI):  # sign-extended 16+16=32 bit
                si_hi = Signal(32, reset_less=True)
                comb += si_hi.eq(self.dec.SI << 16)
                comb += self.imm_out.data.eq(exts(si_hi, 32, 64))
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_UI_HI):  # unsigned
                ui = Signal(16, reset_less=True)
                comb += ui.eq(self.dec.UI)
                comb += self.imm_out.data.eq(ui << 16)
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_LI):  # sign-extend 24+2=26 bit
                li = Signal(26, reset_less=True)
                comb += li.eq(self.dec.LI << 2)
                comb += self.imm_out.data.eq(exts(li, 26, 64))
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_BD):  # sign-extend (14+2)=16 bit
                bd = Signal(16, reset_less=True)
                comb += bd.eq(self.dec.BD << 2)
                comb += self.imm_out.data.eq(exts(bd, 16, 64))
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_DS):  # sign-extended (14+2=16) bit
                ds = Signal(16, reset_less=True)
                comb += ds.eq(self.dec.DS << 2)
                comb += self.imm_out.data.eq(exts(ds, 16, 64))
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_M1):  # signed (-1)
                comb += self.imm_out.data.eq(~Const(0, 64))  # all 1s
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_SH):  # unsigned - for shift
                comb += self.imm_out.data.eq(self.dec.sh)
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_SH32):  # unsigned - for shift
                comb += self.imm_out.data.eq(self.dec.SH32)
                comb += self.imm_out.ok.eq(1)
            with m.Case(In2Sel.CONST_XBI):  # unsigned - for grevi
                comb += self.imm_out.data.eq(self.dec.FormXB.XBI)
                comb += self.imm_out.ok.eq(1)

        return m


class DecodeC(Elaboratable):
    """DecodeC from instruction

    decodes register RC.  this is "lane 3" into some CompUnits (not many)
    """

    def __init__(self, dec, op):
        self.dec = dec
        self.op = op
        self.sel_in = Signal(In3Sel, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.reg_out = Data(5, "reg_c")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        op = self.op
        reg = self.reg_out

        # select Register C field
        with m.Switch(self.sel_in):
            with m.Case(In3Sel.RB):
                # for M-Form shiftrot
                comb += reg.data.eq(self.dec.RB)
                comb += reg.ok.eq(1)
            with m.Case(In3Sel.FRS):
                comb += reg.data.eq(self.dec.FRS)
                comb += reg.ok.eq(1)
            with m.Case(In3Sel.FRC):
                comb += reg.data.eq(self.dec.FRC)
                comb += reg.ok.eq(1)
            with m.Case(In3Sel.RS):
                comb += reg.data.eq(self.dec.RS)
                comb += reg.ok.eq(1)
            with m.Case(In3Sel.RC):
                comb += reg.data.eq(self.dec.RC)
                comb += reg.ok.eq(1)
            with m.Case(In3Sel.RT):
                # for TLI-form ternlogi
                comb += reg.data.eq(self.dec.RT)
                comb += reg.ok.eq(1)

        return m


class DecodeOut(Elaboratable):
    """DecodeOut from instruction

    decodes output register RA, RT, FRS, FRT, or SPR
    """

    def __init__(self, dec, op, regreduce_en):
        self.regreduce_en = regreduce_en
        if self.regreduce_en:
            SPR = SPRreduced
        else:
            SPR = SPRfull
        self.dec = dec
        self.op = op
        self.sel_in = Signal(OutSel, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.reg_out = Data(5, "reg_o")
        self.spr_out = Data(SPR, "spr_o")
        self.fast_out = Data(4, "fast_o")
        self.state_out = Data(3, "state_o")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        m.submodules.sprmap = sprmap = SPRMap(self.regreduce_en)
        op = self.op
        reg = self.reg_out

        # select Register out field
        with m.Switch(self.sel_in):
            with m.Case(OutSel.FRS):
                comb += reg.data.eq(self.dec.FRS)
                comb += reg.ok.eq(1)
            with m.Case(OutSel.FRT):
                comb += reg.data.eq(self.dec.FRT)
                comb += reg.ok.eq(1)
            with m.Case(OutSel.RT):
                comb += reg.data.eq(self.dec.RT)
                comb += reg.ok.eq(1)
            with m.Case(OutSel.RA):
                comb += reg.data.eq(self.dec.RA)
                comb += reg.ok.eq(1)
            with m.Case(OutSel.SPR):
                spr = Signal(10, reset_less=True)
                comb += spr.eq(decode_spr_num(self.dec.SPR))  # from XFX
                # MFSPR move to SPRs - needs mapping
                with m.If(op.internal_op == MicrOp.OP_MTSPR):
                    comb += sprmap.spr_i.eq(spr)
                    comb += self.spr_out.eq(sprmap.spr_o)
                    comb += self.fast_out.eq(sprmap.fast_o)
                    comb += self.state_out.eq(sprmap.state_o)

        # determine Fast Reg
        with m.Switch(op.internal_op):

            # BC or BCREG: implicit register (CTR) NOTE: same in DecodeA
            with m.Case(MicrOp.OP_BC, MicrOp.OP_BCREG):
                with m.If(~self.dec.BO[2]):  # 3.0B p38 BO2=0, use CTR reg
                    # constant: CTR
                    comb += self.fast_out.data.eq(FastRegsEnum.CTR)
                    comb += self.fast_out.ok.eq(1)

            # RFID 1st spr (fast)
            with m.Case(MicrOp.OP_RFID):
                comb += self.fast_out.data.eq(FastRegsEnum.SRR0)  # SRR0
                comb += self.fast_out.ok.eq(1)

        return m


class DecodeOut2(Elaboratable):
    """DecodeOut2 from instruction

    decodes output registers (2nd one).  note that RA is *implicit* below,
    which now causes problems with SVP64

    TODO: SVP64 is a little more complex, here.  svp64 allows extending
    by one more destination by having one more EXTRA field.  RA-as-src
    is not the same as RA-as-dest.  limited in that it's the same first
    5 bits (from the v3.0B opcode), but still kinda cool.  mostly used
    for operations that have src-as-dest: mostly this is LD/ST-with-update
    but there are others.
    """

    def __init__(self, dec, op):
        self.dec = dec
        self.op = op
        self.sel_in = Signal(OutSel, reset_less=True)
        self.implicit_rs = Signal(reset_less=True)  # SVP64 implicit RS/FRS
        self.implicit_from_rc = Signal(reset_less=True)# implicit RS from RC
        self.lk = Signal(reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.reg_out = Data(5, "reg_o2")
        self.rs_en = Signal(reset_less=True)  # FFT instruction detected
        self.fast_out = Data(4, "fast_o2")
        self.fast_out3 = Data(4, "fast_o3")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        op = self.op
        #m.submodules.svdec = svdec = SVP64RegExtra()

        # get the 5-bit reg data before svp64-munging it into 7-bit plus isvec
        #reg = Signal(5, reset_less=True)

        if hasattr(op, "upd"):
            # update mode LD/ST uses read-reg A also as an output
            with m.If(op.upd == LDSTMode.update):
                comb += self.reg_out.data.eq(self.dec.RA)
                comb += self.reg_out.ok.eq(1)

        # B, BC or BCREG: potential implicit register (LR) output
        # these give bl, bcl, bclrl, etc.
        with m.Switch(op.internal_op):

            # BC* implicit register (LR)
            with m.Case(MicrOp.OP_BC, MicrOp.OP_B, MicrOp.OP_BCREG):
                with m.If(self.lk):  # "link" mode
                    comb += self.fast_out.data.eq(FastRegsEnum.LR)  # LR
                    comb += self.fast_out.ok.eq(1)

            # RFID 2nd and 3rd spr (fast)
            with m.Case(MicrOp.OP_RFID):
                comb += self.fast_out.data.eq(FastRegsEnum.SRR1)  # SRR1
                comb += self.fast_out.ok.eq(1)
                comb += self.fast_out3.data.eq(FastRegsEnum.SVSRR0)  # SVSRR0
                comb += self.fast_out3.ok.eq(1)

        # SVP64 FFT mode, FP mul-add: 2nd output reg (FRS) same as FRT
        # will be offset by VL in hardware
        # with m.Case(MicrOp.OP_FP_MADD):
        with m.If(self.implicit_rs):
            with m.If(self.implicit_from_rc):
                comb += self.reg_out.data.eq(self.dec.FRC) # same as RC
            with m.Else():
                comb += self.reg_out.data.eq(self.dec.FRT) # same as RT
            comb += self.reg_out.ok.eq(1)
            comb += self.rs_en.eq(1)

        return m


class DecodeRC(Elaboratable):
    """DecodeRc from instruction

    decodes Record bit Rc
    """

    def __init__(self, dec):
        self.dec = dec
        self.sel_in = Signal(RCOE, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.rc_out = Data(1, "rc")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        # select Record bit out field
        with m.Switch(self.sel_in):
            with m.Case(RCOE.RC, RCOE.RC_ONLY):
                comb += self.rc_out.data.eq(self.dec.Rc)
                comb += self.rc_out.ok.eq(1)
            with m.Case(RCOE.ONE):
                comb += self.rc_out.data.eq(1)
                comb += self.rc_out.ok.eq(1)
            with m.Case(RCOE.NONE):
                comb += self.rc_out.data.eq(0)
                comb += self.rc_out.ok.eq(1)

        return m


class DecodeOE(Elaboratable):
    """DecodeOE from instruction

    decodes OE field: uses RC decode detection which has now been
    updated to separate out RC_ONLY.  all cases RC_ONLY are *NOT*
    listening to the OE field, here.
    """

    def __init__(self, dec, op):
        self.dec = dec
        self.op = op
        self.sel_in = Signal(RCOE, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.oe_out = Data(1, "oe")

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        with m.Switch(self.sel_in):
            with m.Case(RCOE.RC):
                comb += self.oe_out.data.eq(self.dec.OE)
                comb += self.oe_out.ok.eq(1)
            with m.Default():
                # default: clear OE.
                comb += self.oe_out.data.eq(0)
                comb += self.oe_out.ok.eq(0)

        return m


class DecodeCRIn(Elaboratable):
    """Decodes input CR from instruction

    CR indices - insn fields - (not the data *in* the CR) require only 3
    bits because they refer to CR0-CR7
    """

    def __init__(self, dec, op):
        self.dec = dec
        self.op = op
        self.sel_in = Signal(CRInSel, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.cr_bitfield = Data(3, "cr_bitfield")
        self.cr_bitfield_b = Data(3, "cr_bitfield_b")
        self.cr_bitfield_o = Data(3, "cr_bitfield_o")
        self.whole_reg = Data(8,  "cr_fxm")
        self.sv_override = Signal(2, reset_less=True)  # do not do EXTRA spec

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        op = self.op
        m.submodules.ppick = ppick = PriorityPicker(8, reverse_i=True,
                                                    reverse_o=True)

        # zero-initialisation
        comb += self.cr_bitfield.ok.eq(0)
        comb += self.cr_bitfield_b.ok.eq(0)
        comb += self.cr_bitfield_o.ok.eq(0)
        comb += self.whole_reg.ok.eq(0)
        comb += self.sv_override.eq(0)

        # select the relevant CR bitfields
        with m.Switch(self.sel_in):
            with m.Case(CRInSel.NONE):
                pass  # No bitfield activated
            with m.Case(CRInSel.CR0):
                comb += self.cr_bitfield.data.eq(0)  # CR0 (MSB0 numbering)
                comb += self.cr_bitfield.ok.eq(1)
                comb += self.sv_override.eq(1)
            with m.Case(CRInSel.CR1):
                comb += self.cr_bitfield.data.eq(1)  # CR1 (MSB0 numbering)
                comb += self.cr_bitfield.ok.eq(1)
                comb += self.sv_override.eq(2)
            with m.Case(CRInSel.BI):
                comb += self.cr_bitfield.data.eq(self.dec.BI[2:5])
                comb += self.cr_bitfield.ok.eq(1)
            with m.Case(CRInSel.BFA):
                comb += self.cr_bitfield.data.eq(self.dec.FormX.BFA)
                comb += self.cr_bitfield.ok.eq(1)
            with m.Case(CRInSel.BA_BB):
                comb += self.cr_bitfield.data.eq(self.dec.BA[2:5])
                comb += self.cr_bitfield.ok.eq(1)
                comb += self.cr_bitfield_b.data.eq(self.dec.BB[2:5])
                comb += self.cr_bitfield_b.ok.eq(1)
                comb += self.cr_bitfield_o.data.eq(self.dec.BT[2:5])
                comb += self.cr_bitfield_o.ok.eq(1)
            with m.Case(CRInSel.BC):
                comb += self.cr_bitfield.data.eq(self.dec.BC[2:5])
                comb += self.cr_bitfield.ok.eq(1)
            with m.Case(CRInSel.WHOLE_REG):
                comb += self.whole_reg.ok.eq(1)
                move_one = Signal(reset_less=True)
                comb += move_one.eq(self.insn_in[20])  # MSB0 bit 11
                with m.If((op.internal_op == MicrOp.OP_MFCR) & move_one):
                    # must one-hot the FXM field
                    comb += ppick.i.eq(self.dec.FXM)
                    comb += self.whole_reg.data.eq(ppick.o)
                with m.Else():
                    # otherwise use all of it
                    comb += self.whole_reg.data.eq(0xff)

        return m


class DecodeCROut(Elaboratable):
    """Decodes input CR from instruction

    CR indices - insn fields - (not the data *in* the CR) require only 3
    bits because they refer to CR0-CR7
    """

    def __init__(self, dec, op):
        self.dec = dec
        self.op = op
        self.rc_in = Signal(reset_less=True)
        self.sel_in = Signal(CROutSel, reset_less=True)
        self.insn_in = Signal(32, reset_less=True)
        self.cr_bitfield = Data(3, "cr_bitfield")
        self.whole_reg = Data(8,  "cr_fxm")
        self.sv_override = Signal(2, reset_less=True)  # do not do EXTRA spec
        self.cr_5bit = Signal(reset_less=True)  # set True for 5-bit
        self.cr_2bit = Signal(2, reset_less=True)  # get lowest 2 bits

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        op = self.op
        m.submodules.ppick = ppick = PriorityPicker(8, reverse_i=True,
                                                    reverse_o=True)

        comb += self.cr_bitfield.ok.eq(0)
        comb += self.whole_reg.ok.eq(0)
        comb += self.sv_override.eq(0)
        comb += self.cr_5bit.eq(0)

        # please note these MUST match (setting of cr_bitfield.ok) exactly
        # with write_cr0 below in PowerDecoder2.  the reason it's separated
        # is to avoid having duplicate copies of DecodeCROut in multiple
        # PowerDecoderSubsets.  register decoding should be a one-off in
        # PowerDecoder2.  see https://bugs.libre-soc.org/show_bug.cgi?id=606

        with m.Switch(self.sel_in):
            with m.Case(CROutSel.NONE):
                pass  # No bitfield activated
            with m.Case(CROutSel.CR0):
                comb += self.cr_bitfield.data.eq(0)  # CR0 (MSB0 numbering)
                comb += self.cr_bitfield.ok.eq(self.rc_in)  # only when RC=1
                comb += self.sv_override.eq(1)
            with m.Case(CROutSel.CR1):
                comb += self.cr_bitfield.data.eq(1)  # CR1 (MSB0 numbering)
                comb += self.cr_bitfield.ok.eq(self.rc_in)  # only when RC=1
                comb += self.sv_override.eq(2)
            with m.Case(CROutSel.BF):
                comb += self.cr_bitfield.data.eq(self.dec.FormX.BF)
                comb += self.cr_bitfield.ok.eq(1)
            with m.Case(CROutSel.BT):
                comb += self.cr_bitfield.data.eq(self.dec.FormXL.BT[2:5])
                comb += self.cr_bitfield.ok.eq(1)
                comb += self.cr_5bit.eq(1)
                comb += self.cr_2bit.eq(self.dec.FormXL.BT[0:2])
            with m.Case(CROutSel.WHOLE_REG):
                comb += self.whole_reg.ok.eq(1)
                move_one = Signal(reset_less=True)
                comb += move_one.eq(self.insn_in[20])
                with m.If((op.internal_op == MicrOp.OP_MTCRF)):
                    with m.If(move_one):
                        # must one-hot the FXM field
                        comb += ppick.i.eq(self.dec.FXM)
                        with m.If(ppick.en_o):
                            comb += self.whole_reg.data.eq(ppick.o)
                        with m.Else():
                            comb += self.whole_reg.data.eq(0b00000001)  # CR7
                    with m.Else():
                        comb += self.whole_reg.data.eq(self.dec.FXM)
                with m.Else():
                    # otherwise use all of it
                    comb += self.whole_reg.data.eq(0xff)

        return m


# dictionary of Input Record field names that, if they exist,
# will need a corresponding CSV Decoder file column (actually, PowerOp)
# to be decoded (this includes the single bit names)
record_names = {'insn_type': 'internal_op',
                'fn_unit': 'function_unit',
                'SV_Ptype': 'SV_Ptype',
                'SV_mode': 'SV_mode',
                'rc': 'rc_sel',
                'oe': 'rc_sel',
                'zero_a': 'in1_sel',
                'imm_data': 'in2_sel',
                'invert_in': 'inv_a',
                'invert_out': 'inv_out',
                'rc': 'cr_out',
                'oe': 'cr_in',
                'output_carry': 'cry_out',
                'input_carry': 'cry_in',
                'is_32bit': 'is_32b',
                'is_signed': 'sgn',
                'lk': 'lk',
                'data_len': 'ldst_len',
                'reserve': 'rsrv',
                'byte_reverse': 'br',
                'sign_extend': 'sgn_ext',
                'ldst_mode': 'upd',
                }


class PowerDecodeSubset(Elaboratable):
    """PowerDecodeSubset: dynamic subset decoder

    only fields actually requested are copied over. hence, "subset" (duh).
    """

    def __init__(self, dec, opkls=None, fn_name=None, final=False, state=None,
                 svp64_en=True, regreduce_en=False, fp_en=False):

        self.svp64_en = svp64_en
        self.regreduce_en = regreduce_en
        self.fp_en = fp_en
        if svp64_en:
            self.is_svp64_mode = Signal()  # mark decoding as SVP64 Mode
            self.implicit_rs = Signal()    # implicit RS/FRS
            self.extend_rb_maxvl = Signal() # jumps RB by an additional MAXVL
            self.extend_rc_maxvl = Signal() # jumps RS by MAXVL from RC
            self.sv_rm = SVP64Rec(name="dec_svp64")  # SVP64 RM field
            self.rm_dec = SVP64RMModeDecode("svp64_rm_dec")
            # set these to the predicate mask bits needed for the ALU
            self.pred_sm = Signal()  # TODO expand to SIMD mask width
            self.pred_dm = Signal()  # TODO expand to SIMD mask width
        self.sv_a_nz = Signal(1)
        self.final = final
        self.opkls = opkls
        self.fn_name = fn_name
        if opkls is None:
            opkls = Decode2ToOperand
        self.do = opkls(fn_name)
        if final:
            col_subset = self.get_col_subset(self.do)
            row_subset = self.rowsubsetfn
        else:
            col_subset = None
            row_subset = None

        # "conditions" for Decoders, to enable some weird and wonderful
        # alternatives.  useful for PCR (Program Compatibility Register)
        # amongst other things
        if svp64_en:
            conditions = {
                          # XXX NO 'SVP64FFT': self.use_svp64_fft,
                          }
        else:
            conditions = None

        # only needed for "main" PowerDecode2
        if not self.final:
            self.e = Decode2ToExecute1Type(name=self.fn_name, do=self.do,
                                           regreduce_en=regreduce_en)

        # create decoder if one not already given
        if dec is None:
            dec = create_pdecode(name=fn_name, col_subset=col_subset,
                                 row_subset=row_subset,
                                 conditions=conditions, include_fp=fp_en)
        self.dec = dec

        # set up a copy of the PowerOp
        self.op = PowerOp.like(self.dec.op)

        # state information needed by the Decoder
        if state is None:
            state = CoreState("dec2")
        self.state = state

    def get_col_subset(self, do):
        subset = {'cr_in', 'cr_out', 'rc_sel'}  # needed, non-optional
        for k, v in record_names.items():
            if hasattr(do, k):
                subset.add(v)
        log("get_col_subset", self.fn_name, do.fields, subset)
        return subset

    def rowsubsetfn(self, opcode, row):
        """select per-Function-Unit subset of opcodes to be processed

        normally this just looks at the "unit" column.  MMU is different
        in that it processes specific SPR set/get operations that the SPR
        pipeline should not.
        """
        return (row['unit'] == self.fn_name or
                # sigh a dreadful hack: MTSPR and MFSPR need to be processed
                # by the MMU pipeline so we direct those opcodes to MMU **AND**
                # SPR pipelines, then selectively weed out the SPRs that should
                # or should not not go to each pipeline, further down.
                # really this should be done by modifying the CSV syntax
                # to support multiple tasks (unit column multiple entries)
                # see https://bugs.libre-soc.org/show_bug.cgi?id=310
                (self.fn_name == 'MMU' and row['unit'] == 'SPR' and
                 row['internal op'] in ['OP_MTSPR', 'OP_MFSPR']) or
                # urrr... and the KAIVB SPR, which must also be redirected
                # (to the TRAP pipeline)
                # see https://bugs.libre-soc.org/show_bug.cgi?id=859
                (self.fn_name == 'TRAP' and row['unit'] == 'SPR' and
                 row['internal op'] in ['OP_MTSPR', 'OP_MFSPR'])
                )

    def ports(self):
        ports = self.dec.ports() + self.e.ports()
        if self.svp64_en:
            ports += self.sv_rm.ports()
            ports.append(self.is_svp64_mode)
            ports.append(self.implicit_rs)
        return ports

    def needs_field(self, field, op_field):
        if self.final:
            do = self.do
        else:
            do = self.e_tmp.do
        return hasattr(do, field) and self.op_get(op_field) is not None

    def do_get(self, field, final=False):
        if final or self.final:
            do = self.do
        else:
            do = self.e_tmp.do
        return getattr(do, field, None)

    def do_copy(self, field, val, final=False):
        df = self.do_get(field, final)
        if df is not None and val is not None:
            return df.eq(val)
        return []

    def op_get(self, op_field):
        return getattr(self.op, op_field, None)

    def elaborate(self, platform):
        if self.regreduce_en:
            SPR = SPRreduced
        else:
            SPR = SPRfull
        m = Module()
        comb = m.d.comb
        state = self.state
        op, do = self.dec.op, self.do
        msr, cia, svstate = state.msr, state.pc, state.svstate
        # fill in for a normal instruction (not an exception)
        # copy over if non-exception, non-privileged etc. is detected
        if not self.final:
            if self.fn_name is None:
                name = "tmp"
            else:
                name = self.fn_name + "tmp"
            self.e_tmp = Decode2ToExecute1Type(name=name, opkls=self.opkls,
                                               regreduce_en=self.regreduce_en)

        # set up submodule decoders
        m.submodules.dec = dec = self.dec
        m.submodules.dec_rc = self.dec_rc = dec_rc = DecodeRC(self.dec)
        m.submodules.dec_oe = dec_oe = DecodeOE(self.dec, op)

        if self.svp64_en:
            # and SVP64 RM mode decoder
            m.submodules.sv_rm_dec = rm_dec = self.rm_dec

        # copy op from decoder
        comb += self.op.eq(self.dec.op)

        # copy instruction through...
        for i in [do.insn, dec_rc.insn_in, dec_oe.insn_in, ]:
            comb += i.eq(self.dec.opcode_in)

        # ...and subdecoders' input fields
        comb += dec_rc.sel_in.eq(self.op_get("rc_sel"))
        comb += dec_oe.sel_in.eq(self.op_get("rc_sel"))  # XXX should be OE sel

        # copy "state" over
        comb += self.do_copy("msr", msr)
        comb += self.do_copy("cia", cia)
        comb += self.do_copy("svstate", svstate)

        # set up instruction type
        # no op: defaults to OP_ILLEGAL
        internal_op = self.op_get("internal_op")
        comb += self.do_copy("insn_type", internal_op)

        # function unit for decoded instruction: requires minor redirect
        # for SPR set/get
        fn = self.op_get("function_unit")
        spr = Signal(10, reset_less=True)
        comb += spr.eq(decode_spr_num(self.dec.SPR))  # from XFX

        # Microwatt doesn't implement the partition table
        # instead has PRTBL register (SPR) to point to process table
        # Kestrel has a KAIVB SPR to "rebase" exceptions. rebasing is normally
        # done with Hypervisor Mode which is not implemented (yet)
        is_spr_mv = Signal()
        is_mmu_spr = Signal()
        is_trap_spr = Signal()
        comb += is_spr_mv.eq((internal_op == MicrOp.OP_MTSPR) |
                             (internal_op == MicrOp.OP_MFSPR))
        comb += is_mmu_spr.eq((spr == SPR.DSISR.value) |
                              (spr == SPR.DAR.value) |
                              (spr == SPR.PRTBL.value) |
                              (spr == SPR.PIDR.value))
        comb += is_trap_spr.eq((spr == SPR.KAIVB.value)
                              )
        # MMU must receive MMU SPRs
        with m.If(is_spr_mv & (fn == Function.SPR) & is_mmu_spr):
            comb += self.do_copy("fn_unit", Function.MMU)
            comb += self.do_copy("insn_type", internal_op)
        # TRAP must receive TRAP SPR KAIVB
        with m.If(is_spr_mv & (fn == Function.SPR) & is_trap_spr):
            comb += self.do_copy("fn_unit", Function.TRAP)
            comb += self.do_copy("insn_type", internal_op)
        # SPR pipe must *not* receive MMU or TRAP SPRs
        with m.Elif(is_spr_mv & ((fn == Function.MMU) & ~is_mmu_spr) &
                                ((fn == Function.TRAP) & ~is_trap_spr)):
            comb += self.do_copy("fn_unit", Function.NONE)
            comb += self.do_copy("insn_type", MicrOp.OP_ILLEGAL)
        # all others ok
        with m.Else():
            comb += self.do_copy("fn_unit", fn)

        # immediates
        if self.needs_field("zero_a", "in1_sel"):
            m.submodules.dec_ai = dec_ai = DecodeAImm(self.dec)
            comb += dec_ai.sv_nz.eq(self.sv_a_nz)
            comb += dec_ai.sel_in.eq(self.op_get("in1_sel"))
            comb += self.do_copy("zero_a", dec_ai.immz_out)  # RA==0 detected
        if self.needs_field("imm_data", "in2_sel"):
            m.submodules.dec_bi = dec_bi = DecodeBImm(self.dec)
            comb += dec_bi.sel_in.eq(self.op_get("in2_sel"))
            comb += self.do_copy("imm_data", dec_bi.imm_out)  # imm in RB

        # CR in/out - note: these MUST match with what happens in
        # DecodeCROut!
        rc_out = self.dec_rc.rc_out.data
        with m.Switch(self.op_get("cr_out")):
            with m.Case(CROutSel.CR0, CROutSel.CR1):
                comb += self.do_copy("write_cr0", rc_out)  # only when RC=1
            with m.Case(CROutSel.BF, CROutSel.BT):
                comb += self.do_copy("write_cr0", 1)

        comb += self.do_copy("input_cr", self.op_get("cr_in"))   # CR in
        comb += self.do_copy("output_cr", self.op_get("cr_out"))  # CR out

        if self.svp64_en:
            # connect up SVP64 RM Mode decoding.  however... we need a shorter
            # path, for the LDST bit-reverse detection.  so perform partial
            # decode when SVP64 is detected.  then, bit-reverse mode can be
            # quickly determined, and the Decoder result MUXed over to
            # the alternative decoder, svdecldst. what a mess... *sigh*
            sv_ptype = self.op_get("SV_Ptype")
            sv_mode = self.op_get("SV_mode")
            fn = self.op_get("function_unit")
            print ("sv_mode n", sv_mode)
            comb += rm_dec.sv_mode.eq(sv_mode)  # BRANCH/CROP/LDST_IMM etc.
            comb += rm_dec.fn_in.eq(fn)  # decode needs to know Fn type
            comb += rm_dec.ptype_in.eq(sv_ptype)  # Single/Twin predicated
            comb += rm_dec.rc_in.eq(rc_out)  # Rc=1
            comb += rm_dec.rm_in.eq(self.sv_rm)  # SVP64 RM mode
            if self.needs_field("imm_data", "in2_sel"):
                bzero = dec_bi.imm_out.ok & ~dec_bi.imm_out.data.bool()
                comb += rm_dec.ldst_imz_in.eq(bzero)  # B immediate is zero

            # main PowerDecoder2 determines if different SVP64 modes enabled
            # detect if SVP64 FFT mode enabled (really bad hack),
            # exclude fcfids and others
            # XXX this is a REALLY bad hack, REALLY has to be done better.
            # likely with a sub-decoder.
            # what this ultimately does is enable the 2nd implicit register
            # (FRS) for SVP64-decoding.  all of these instructions are
            # 3-in 2-out but there is not enough room either in the
            # opcode *or* EXTRA2/3 to specify a 5th operand.
            major = Signal(6)
            comb += major.eq(self.dec.opcode_in[26:32])
            xo = Signal(10)
            comb += xo.eq(self.dec.opcode_in[1:11])
            comb += self.implicit_rs.eq(0)
            comb += self.extend_rb_maxvl.eq(0)
            comb += self.extend_rc_maxvl.eq(0)
            # implicit RS for major 59
            with m.If((major == 59) & xo.matches(
                    '-----00100',  # ffmsubs
                    '-----00101',  # ffmadds
                    '-----00110',  # ffnmsubs
                    '-----00111',  # ffnmadds
                    '1111100000',  # ffadds
                    '-----11011',  # fdmadds
                )):
                comb += self.implicit_rs.eq(1)
                comb += self.extend_rb_maxvl.eq(1) # extend RB
            xo6 = Signal(6)
            comb += xo6.eq(self.dec.opcode_in[0:6])
            # implicit RS for major 4
            with m.If((major == 4) & xo6.matches(
                    '111000',  # pcdec
                    '110010',  # maddedu
                    '111001',  # maddedus
                    '111010',  # divmod2du
                    '11010-',  # dsld
                    '11011-',  # dsrd
                )):
                comb += self.implicit_rs.eq(1)
                comb += self.extend_rc_maxvl.eq(1) # RS=RT+MAXVL or RS=RC

        # rc and oe out
        comb += self.do_copy("rc", dec_rc.rc_out)
        if self.svp64_en:
            # OE only enabled when SVP64 not active
            with m.If(~self.is_svp64_mode):
                comb += self.do_copy("oe", dec_oe.oe_out)
            # RC1 overrides Rc if rc type is NONE or ONE or Rc=0, in svp64_mode
            # for instructions with a forced-Rc=1 (stbcx., pcdec.)
            # the RC1 RM bit *becomes* Rc=0/1, but for instructions
            # that have Rc=0/1 then when Rc=0 RC1 *becomes* (replaces) Rc.
            with m.Elif((dec_rc.sel_in.matches(RCOE.RC, RCOE.RC_ONLY) &
                         dec_rc.rc_out.data == 0) |
                         (dec_rc.sel_in == RCOE.ONE)):
                RC1 = Data(1, "RC1")
                comb += RC1.ok.eq(rm_dec.RC1)
                comb += RC1.RC1.eq(rm_dec.RC1)
                comb += self.do_copy("rc", RC1)
        else:
            comb += self.do_copy("oe", dec_oe.oe_out)

        # decoded/selected instruction flags
        comb += self.do_copy("data_len", self.op_get("ldst_len"))
        comb += self.do_copy("invert_in", self.op_get("inv_a"))
        comb += self.do_copy("invert_out", self.op_get("inv_out"))
        comb += self.do_copy("input_carry", self.op_get("cry_in"))
        comb += self.do_copy("output_carry", self.op_get("cry_out"))
        comb += self.do_copy("is_32bit", self.op_get("is_32b"))
        comb += self.do_copy("is_signed", self.op_get("sgn"))
        lk = self.op_get("lk")
        if lk is not None:
            with m.If(lk):
                comb += self.do_copy("lk", self.dec.LK)  # XXX TODO: accessor

        comb += self.do_copy("byte_reverse", self.op_get("br"))
        comb += self.do_copy("sign_extend", self.op_get("sgn_ext"))
        comb += self.do_copy("ldst_mode", self.op_get("upd"))  # LD/ST mode
        comb += self.do_copy("reserve", self.op_get("rsrv"))  # atomic

        # copy over SVP64 input record fields (if they exist)
        if self.svp64_en:
            # TODO, really do we have to do these explicitly?? sigh
            # for (field, _) in sv_input_record_layout:
            #    comb += self.do_copy(field, self.rm_dec.op_get(field))
            comb += self.do_copy("sv_saturate", self.rm_dec.saturate)
            comb += self.do_copy("sv_Ptype", self.rm_dec.ptype_in)
            comb += self.do_copy("sv_ldstmode", self.rm_dec.ldstmode)
            # these get set up based on incoming mask bits.  TODO:
            # pass in multiple bits (later, when SIMD backends are enabled)
            with m.If(self.rm_dec.pred_sz):
                comb += self.do_copy("sv_pred_sz", ~self.pred_sm)
            with m.If(self.rm_dec.pred_dz):
                comb += self.do_copy("sv_pred_dz", ~self.pred_dm)

        return m


class PowerDecode2(PowerDecodeSubset):
    """PowerDecode2: the main instruction decoder.

    whilst PowerDecode is responsible for decoding the actual opcode, this
    module encapsulates further specialist, sparse information and
    expansion of fields that is inconvenient to have in the CSV files.
    for example: the encoding of the immediates, which are detected
    and expanded out to their full value from an annotated (enum)
    representation.

    implicit register usage is also set up, here.  for example: OP_BC
    requires implicitly reading CTR, OP_RFID requires implicitly writing
    to SRR1 and so on.

    in addition, PowerDecoder2 is responsible for detecting whether
    instructions are illegal (or privileged) or not, and instead of
    just leaving at that, *replacing* the instruction to execute with
    a suitable alternative (trap).

    LDSTExceptions are done the cycle _after_ they're detected (after
    they come out of LDSTCompUnit).  basically despite the instruction
    being decoded, the results of the decode are completely ignored
    and "exception.happened" used to set the "actual" instruction to
    "OP_TRAP".  the LDSTException data structure gets filled in,
    in the CompTrapOpSubset and that's what it fills in SRR.

    to make this work, TestIssuer must notice "exception.happened"
    after the (failed) LD/ST and copies the LDSTException info from
    the output, into here (PowerDecoder2).  without incrementing PC.

    also instr_fault works the same way: the instruction is "rewritten"
    so that the "fake" op that gets created is OP_FETCH_FAILED
    """

    def __init__(self, dec, opkls=None, fn_name=None, final=False,
                 state=None, svp64_en=True, regreduce_en=False, fp_en=False):
        super().__init__(dec, opkls, fn_name, final, state, svp64_en,
                         regreduce_en=False, fp_en=fp_en)
        self.ldst_exc = LDSTException("dec2_exc")  # rewrites as OP_TRAP
        self.instr_fault = Signal()  # rewrites instruction as OP_FETCH_FAILED
        self.crout_5bit = Signal()  # CR out is 5-bit

        if self.svp64_en:
            self.cr_out_isvec = Signal(1, name="cr_out_isvec")
            self.cr_in_isvec = Signal(1, name="cr_in_isvec")
            self.cr_in_b_isvec = Signal(1, name="cr_in_b_isvec")
            self.cr_in_o_isvec = Signal(1, name="cr_in_o_isvec")
            self.in1_isvec = Signal(1, name="reg_a_isvec")
            self.in2_isvec = Signal(1, name="reg_b_isvec")
            self.in3_isvec = Signal(1, name="reg_c_isvec")
            self.o_isvec = Signal(7, name="reg_o_isvec")
            self.o2_isvec = Signal(7, name="reg_o2_isvec")
            self.in1_step = Signal(7, name="reg_a_step")
            self.in2_step = Signal(7, name="reg_b_step")
            self.in3_step = Signal(7, name="reg_c_step")
            self.o_step = Signal(7, name="reg_o_step")
            self.o2_step = Signal(7, name="reg_o2_step")
            self.remap_active = Signal(5, name="remap_active")  # per reg
            self.no_in_vec = Signal(1, name="no_in_vec")  # no inputs vector
            self.no_out_vec = Signal(1, name="no_out_vec")  # no outputs vector
            self.loop_continue = Signal(1, name="loop_continue")
        else:
            self.no_in_vec = Const(1, 1)
            self.no_out_vec = Const(1, 1)
            self.loop_continue = Const(0, 1)

    def get_col_subset(self, opkls):
        subset = super().get_col_subset(opkls)
        subset.add("asmcode")
        subset.add("in1_sel")
        subset.add("in2_sel")
        subset.add("in3_sel")
        subset.add("out_sel")
        if self.svp64_en:
            subset.add("sv_in1")
            subset.add("sv_in2")
            subset.add("sv_in3")
            subset.add("sv_out")
            subset.add("sv_out2")
            subset.add("sv_cr_in")
            subset.add("sv_cr_out")
            subset.add("SV_Etype")
            subset.add("SV_Ptype")
            subset.add("SV_mode")
            # from SVP64RMModeDecode
            for (field, _) in sv_input_record_layout:
                subset.add(field)
        subset.add("lk")
        subset.add("internal_op")
        subset.add("form")
        return subset

    def elaborate(self, platform):
        m = super().elaborate(platform)
        comb = m.d.comb
        state = self.state
        op, e_out, do_out = self.op, self.e, self.e.do
        dec_spr, msr, cia, ext_irq = state.dec, state.msr, state.pc, state.eint
        rc_out = self.dec_rc.rc_out.data
        e = self.e_tmp
        do = e.do

        # fill in for a normal instruction (not an exception)
        # copy over if non-exception, non-privileged etc. is detected

        # set up submodule decoders
        m.submodules.dec_a = dec_a = DecodeA(self.dec, op, self.regreduce_en)
        m.submodules.dec_b = dec_b = DecodeB(self.dec, op)
        m.submodules.dec_c = dec_c = DecodeC(self.dec, op)
        m.submodules.dec_o = dec_o = DecodeOut(self.dec, op, self.regreduce_en)
        m.submodules.dec_o2 = dec_o2 = DecodeOut2(self.dec, op)
        m.submodules.dec_cr_in = self.dec_cr_in = DecodeCRIn(self.dec, op)
        m.submodules.dec_cr_out = self.dec_cr_out = DecodeCROut(self.dec, op)
        comb += dec_a.sv_nz.eq(self.sv_a_nz)
        comb += self.crout_5bit.eq(self.dec_cr_out.cr_5bit)

        if self.svp64_en:
            # and SVP64 Extra decoders
            m.submodules.crout_svdec = crout_svdec = SVP64CRExtra()
            m.submodules.crin_svdec = crin_svdec = SVP64CRExtra()
            m.submodules.crin_svdec_b = crin_svdec_b = SVP64CRExtra()
            m.submodules.crin_svdec_o = crin_svdec_o = SVP64CRExtra()
            m.submodules.in1_svdec = in1_svdec = SVP64RegExtra()
            m.submodules.in2_svdec = in2_svdec = SVP64RegExtra()
            m.submodules.in3_svdec = in3_svdec = SVP64RegExtra()
            m.submodules.o_svdec = o_svdec = SVP64RegExtra()
            m.submodules.o2_svdec = o2_svdec = SVP64RegExtra()

            # debug access to cr svdec (used in get_pdecode_cr_in/out)
            self.crout_svdec = crout_svdec
            self.crin_svdec = crin_svdec

        # get the 5-bit reg data before svp64-munging it into 7-bit plus isvec
        reg = Signal(5, reset_less=True)

        # copy instruction through...
        for i in [do.insn, dec_a.insn_in, dec_b.insn_in,
                  self.dec_cr_in.insn_in, self.dec_cr_out.insn_in,
                  dec_c.insn_in, dec_o.insn_in, dec_o2.insn_in]:
            comb += i.eq(self.dec.opcode_in)

        # CR setup
        comb += self.dec_cr_in.sel_in.eq(self.op_get("cr_in"))
        comb += self.dec_cr_out.sel_in.eq(self.op_get("cr_out"))
        comb += self.dec_cr_out.rc_in.eq(rc_out)

        # CR register info
        comb += self.do_copy("read_cr_whole", self.dec_cr_in.whole_reg)
        comb += self.do_copy("write_cr_whole", self.dec_cr_out.whole_reg)

        # ...and subdecoders' input fields
        comb += dec_a.sel_in.eq(self.op_get("in1_sel"))
        comb += dec_b.sel_in.eq(self.op_get("in2_sel"))
        comb += dec_c.sel_in.eq(self.op_get("in3_sel"))
        comb += dec_o.sel_in.eq(self.op_get("out_sel"))
        comb += dec_o2.sel_in.eq(self.op_get("out_sel"))
        if self.svp64_en:
            comb += dec_o2.implicit_rs.eq(self.implicit_rs)
            comb += dec_o2.implicit_from_rc.eq(self.extend_rc_maxvl)
        if hasattr(do, "lk"):
            comb += dec_o2.lk.eq(do.lk)

        if self.svp64_en:
            # now do the SVP64 munging.  op.SV_Etype and op.sv_in1 comes from
            # PowerDecoder which in turn comes from LDST-RM*.csv and RM-*.csv
            # which in turn were auto-generated by sv_analysis.py
            extra = self.sv_rm.extra            # SVP64 extra bits 10:18

            #######
            # CR out
            # SVP64 CR out
            comb += crout_svdec.idx.eq(self.op_get("sv_cr_out"))
            comb += self.cr_out_isvec.eq(crout_svdec.isvec)

            #######
            # CR in - selection slightly different due to shared CR field sigh
            cr_a_idx = Signal(SVEXTRA)
            cr_b_idx = Signal(SVEXTRA)

            # these change slightly, when decoding BA/BB.  really should have
            # their own separate CSV column: sv_cr_in1 and sv_cr_in2, but hey
            comb += cr_a_idx.eq(self.op_get("sv_cr_in"))
            comb += cr_b_idx.eq(SVEXTRA.NONE)
            with m.If(self.op_get("sv_cr_in") == SVEXTRA.Idx_1_2.value):
                comb += cr_a_idx.eq(SVEXTRA.Idx1)
                comb += cr_b_idx.eq(SVEXTRA.Idx2)

            comb += self.cr_in_isvec.eq(crin_svdec.isvec)
            comb += self.cr_in_b_isvec.eq(crin_svdec_b.isvec)
            comb += self.cr_in_o_isvec.eq(crin_svdec_o.isvec)

            # indices are slightly different, BA/BB mess sorted above
            comb += crin_svdec.idx.eq(cr_a_idx)       # SVP64 CR in A
            comb += crin_svdec_b.idx.eq(cr_b_idx)     # SVP64 CR in B
            # SVP64 CR out
            comb += crin_svdec_o.idx.eq(self.op_get("sv_cr_out"))

            # get SVSTATE srcstep (TODO: elwidth etc.) needed below
            vl = Signal.like(self.state.svstate.vl)
            maxvl = Signal.like(self.state.svstate.maxvl)
            subvl = Signal.like(self.rm_dec.rm_in.subvl)
            srcstep = Signal.like(self.state.svstate.srcstep)
            dststep = Signal.like(self.state.svstate.dststep)
            ssubstep = Signal.like(self.state.svstate.ssubstep)
            dsubstep = Signal.like(self.state.svstate.ssubstep)
            comb += vl.eq(self.state.svstate.vl)
            comb += maxvl.eq(self.state.svstate.maxvl)
            comb += subvl.eq(self.rm_dec.rm_in.subvl)
            comb += srcstep.eq(self.state.svstate.srcstep)
            comb += dststep.eq(self.state.svstate.dststep)
            comb += ssubstep.eq(self.state.svstate.ssubstep)
            comb += dsubstep.eq(self.state.svstate.dsubstep)

            in1_step, in2_step = self.in1_step, self.in2_step
            in3_step = self.in3_step
            o_step, o2_step = self.o_step, self.o2_step

            # multiply vl by subvl - note that this is only 7 bit!
            # when elwidth overrides get involved this will have to go up
            vmax = Signal(7)
            comb += vmax.eq(vl*(subvl+1))

            # registers a, b, c and out and out2 (LD/ST EA)
            sv_etype = self.op_get("SV_Etype")
            for i, stuff in enumerate((
                ("RA", e.read_reg1, dec_a.reg_out, in1_svdec, in1_step, False),
                ("RB", e.read_reg2, dec_b.reg_out, in2_svdec, in2_step, False),
                ("RC", e.read_reg3, dec_c.reg_out, in3_svdec, in3_step, False),
                ("RT", e.write_reg, dec_o.reg_out, o_svdec, o_step, True),
                ("EA", e.write_ea, dec_o2.reg_out, o2_svdec, o2_step, True))):
                rname, to_reg, fromreg, svdec, remapstep, out = stuff
                comb += svdec.extra.eq(extra)     # EXTRA field of SVP64 RM
                comb += svdec.etype.eq(sv_etype)  # EXTRA2/3 for this insn
                comb += svdec.reg_in.eq(fromreg.data)  # 3-bit (CR0/BC/BFA)
                comb += to_reg.ok.eq(fromreg.ok)
                # *screaam* FFT mode needs an extra offset for RB
                # similar to FRS/FRT (below).  all of this needs cleanup
                offs = Signal(7, name="offs_"+rname, reset_less=True)
                comb += offs.eq(0)
                if rname == 'RB':
                    # when FFT sv.ffmadd detected, and REMAP not in use,
                    # automagically add on an extra offset to RB.
                    # however when REMAP is active, the FFT REMAP
                    # schedule takes care of this offset.
                    with m.If(dec_o2.reg_out.ok & dec_o2.rs_en &
                              self.extend_rb_maxvl):
                        with m.If(~self.remap_active[i]):
                            with m.If(svdec.isvec):
                                comb += offs.eq(maxvl)  # MAXVL for Vectors
                # detect if Vectorised: add srcstep/dststep if yes.
                # to_reg is 7-bits, outs get dststep added, ins get srcstep
                with m.If(svdec.isvec):
                    selectstep = dststep if out else srcstep
                    subselect = dsubstep if out else ssubstep
                    step = Signal(7, name="step_%s" % rname.lower())
                    with m.If(self.remap_active[i]):
                        comb += step.eq((remapstep*(subvl+1))+subselect)
                    with m.Else():
                        comb += step.eq((selectstep*(subvl+1))+subselect)
                    # reverse gear goes the opposite way
                    with m.If(self.rm_dec.reverse_gear):
                        comb += to_reg.offs.eq(offs+(vmax-1-step))
                    with m.Else():
                        comb += to_reg.offs.eq(offs+step)
                with m.Else():
                    comb += to_reg.offs.eq(offs)
                comb += to_reg.base.eq(svdec.reg_out)
                comb += to_reg.data.eq(to_reg.base + to_reg.offs)

            # SVP64 in/out fields
            comb += in1_svdec.idx.eq(self.op_get("sv_in1"))  # reg #1 (in1_sel)
            comb += in2_svdec.idx.eq(self.op_get("sv_in2"))  # reg #2 (in2_sel)
            comb += in3_svdec.idx.eq(self.op_get("sv_in3"))  # reg #3 (in3_sel)
            comb += o_svdec.idx.eq(self.op_get("sv_out"))    # output (out_sel)
            # output (implicit)
            comb += o2_svdec.idx.eq(self.op_get("sv_out2"))
            # XXX TODO - work out where this should come from.  the problem is
            # that LD-with-update is implied (computed from "is instruction in
            # "update mode" rather than specified cleanly as its own CSV column

            # output reg-is-vectorised (and when no in/out is vectorised)
            comb += self.in1_isvec.eq(in1_svdec.isvec)
            comb += self.in2_isvec.eq(in2_svdec.isvec)
            comb += self.in3_isvec.eq(in3_svdec.isvec)
            comb += self.o_isvec.eq(o_svdec.isvec)
            comb += self.o2_isvec.eq(o2_svdec.isvec)

            # urrr... don't ask... the implicit register FRS in FFT mode
            # "tracks" FRT exactly except it's offset by MAXVL.  rather than
            # mess up the above with if-statements, override it here.
            # same trick is applied to FRB, above, but it's a lot cleaner there
            with m.If(dec_o2.reg_out.ok & dec_o2.rs_en):
                imp_reg_out = Signal(7)
                imp_isvec   = Signal(1)
                with m.If(self.extend_rc_maxvl): # maddedu etc. from RC
                    comb += imp_isvec.eq(in3_svdec.isvec)
                    comb += imp_reg_out.eq(in3_svdec.reg_out)
                with m.Else():
                    comb += imp_isvec.eq(o_svdec.isvec)
                    comb += imp_reg_out.eq(o_svdec.reg_out)
                comb += offs.eq(0)
                with m.If(~self.remap_active[4]):
                    with m.If(imp_isvec):
                        comb += offs.eq(maxvl)  # MAXVL for Vectors
                    with m.Elif(self.extend_rc_maxvl): # maddedu etc. from RC
                        comb += offs.eq(0)  # keep as RC
                    with m.Else():
                        comb += offs.eq(1)  # add 1 if scalar
                with m.If(imp_isvec):
                    step = Signal(7, name="step_%s" % rname.lower())
                    with m.If(self.remap_active[4]):
                        with m.If(self.extend_rc_maxvl): # maddedu etc. from RC
                            comb += step.eq(in3_step)
                        with m.Else():
                            comb += step.eq(o2_step)
                    with m.Else():
                        comb += step.eq(dststep)
                    # reverse gear goes the opposite way
                    with m.If(self.rm_dec.reverse_gear):
                        roffs = offs+(vl-1-step)
                        comb += e.write_ea.data.eq(roffs)
                    with m.Else():
                        comb += e.write_ea.data.eq(offs+step)
                with m.Else():
                    comb += e.write_ea.offs.eq(offs)
                comb += e.write_ea.base.eq(imp_reg_out)
                comb += e.write_ea.data.eq(e.write_ea.base + e.write_ea.offs)
                # ... but write to *second* output
                comb += self.o2_isvec.eq(imp_isvec)
                comb += o2_svdec.idx.eq(self.op_get("sv_out"))

            # TODO add SPRs here.  must be True when *all* are scalar
            l = map(lambda svdec: svdec.isvec, [in1_svdec, in2_svdec, in3_svdec,
                                                crin_svdec, crin_svdec_b,
                                                crin_svdec_o])
            comb += self.no_in_vec.eq(~Cat(*l).bool())  # all input scalar
            l = map(lambda svdec: svdec.isvec, [
                    o2_svdec, o_svdec, crout_svdec])
            # in mapreduce mode, scalar out is *allowed*
            with m.If(self.rm_dec.mode == SVP64RMMode.MAPREDUCE.value):
                comb += self.no_out_vec.eq(0)
            with m.Else():
                # all output scalar
                comb += self.no_out_vec.eq(~Cat(*l).bool())
            # now create a general-purpose "test" as to whether looping
            # should continue.  this doesn't include predication bit-tests
            loop = self.loop_continue
            with m.Switch(self.op_get("SV_Ptype")):
                with m.Case(SVPType.P2.value):
                    # twin-predication
                    # TODO: *and cache-inhibited LD/ST!*
                    comb += loop.eq(~(self.no_in_vec | self.no_out_vec))
                with m.Case(SVPType.P1.value):
                    # single-predication, test relies on dest only
                    comb += loop.eq(~self.no_out_vec)
                with m.Default():
                    # not an SV operation, no looping
                    comb += loop.eq(0)

            # condition registers (CR)
            for to_reg, cr, name, svdec, out in (
                (e.read_cr1, self.dec_cr_in, "cr_bitfield", crin_svdec, 0),
                (e.read_cr2, self.dec_cr_in, "cr_bitfield_b", crin_svdec_b, 0),
                (e.read_cr3, self.dec_cr_in, "cr_bitfield_o", crin_svdec_o, 0),
                (e.write_cr, self.dec_cr_out, "cr_bitfield", crout_svdec, 1)):
                fromreg = getattr(cr, name)
                comb += svdec.extra.eq(extra)     # EXTRA field of SVP64 RM
                comb += svdec.etype.eq(sv_etype)  # EXTRA2/3 for this insn
                comb += svdec.cr_in.eq(fromreg.data)  # 3-bit (CR0/BC/BFA)
                with m.If(svdec.isvec):
                    # check if this is CR0 or CR1: treated differently
                    # (does not "listen" to EXTRA2/3 spec for a start)
                    # also: the CRs start from completely different locations
                    step = dststep if out else srcstep
                    with m.If(cr.sv_override == 1):  # CR0
                        offs = SVP64CROffs.CR0
                        comb += to_reg.data.eq(step+offs)
                    with m.Elif(cr.sv_override == 2):  # CR1
                        offs = SVP64CROffs.CR1
                        comb += to_reg.data.eq(step+1)
                    with m.Else():
                        comb += to_reg.data.eq(step+svdec.cr_out)  # 7-bit out
                with m.Else():
                    comb += to_reg.data.eq(svdec.cr_out)  # 7-bit output
                comb += to_reg.ok.eq(fromreg.ok)

            # sigh must determine if RA is nonzero (7 bit)
            comb += self.sv_a_nz.eq(e.read_reg1.data != Const(0, 7))
        else:
            # connect up to/from read/write GPRs
            for to_reg, fromreg in ((e.read_reg1, dec_a.reg_out),
                                    (e.read_reg2, dec_b.reg_out),
                                    (e.read_reg3, dec_c.reg_out),
                                    (e.write_reg, dec_o.reg_out),
                                    (e.write_ea, dec_o2.reg_out)):
                comb += to_reg.data.eq(fromreg.data)
                comb += to_reg.ok.eq(fromreg.ok)

            # connect up to/from read/write CRs
            for to_reg, cr, name in (
                (e.read_cr1, self.dec_cr_in, "cr_bitfield", ),
                (e.read_cr2, self.dec_cr_in, "cr_bitfield_b", ),
                (e.read_cr3, self.dec_cr_in, "cr_bitfield_o", ),
                    (e.write_cr, self.dec_cr_out, "cr_bitfield", )):
                fromreg = getattr(cr, name)
                comb += to_reg.data.eq(fromreg.data)
                comb += to_reg.ok.eq(fromreg.ok)

        if self.svp64_en:
            comb += self.rm_dec.ldst_ra_vec.eq(self.in1_isvec)  # RA is vector
            comb += self.rm_dec.cr_5bit_in.eq(self.crout_5bit)  # CR is 5-bit
            # take bottom 2 bits of CR out (CR field selector)
            with m.If(self.crout_5bit):
                comb += self.rm_dec.cr_2bit_in.eq(self.dec_cr_out.cr_2bit)

        # SPRs out
        comb += e.read_spr1.eq(dec_a.spr_out)
        comb += e.write_spr.eq(dec_o.spr_out)

        # Fast regs out including SRR0/1/SVSRR0
        comb += e.read_fast1.eq(dec_a.fast_out)
        comb += e.read_fast2.eq(dec_b.fast_out)
        comb += e.write_fast1.eq(dec_o.fast_out)   # SRR0 (OP_RFID)
        comb += e.write_fast2.eq(dec_o2.fast_out)  # SRR1 (ditto)
        comb += e.write_fast3.eq(dec_o2.fast_out3)  # SVSRR0 (ditto)
        # and State regs (DEC, TB)
        comb += e.read_state1.eq(dec_a.state_out)    # DEC/TB
        comb += e.write_state1.eq(dec_o.state_out)   # DEC/TB

        # sigh this is exactly the sort of thing for which the
        # decoder is designed to not need.  MTSPR, MFSPR and others need
        # access to the XER bits.  however setting e.oe is not appropriate
        internal_op = self.op_get("internal_op")
        with m.If(internal_op == MicrOp.OP_MFSPR):
            comb += e.xer_in.eq(0b111)  # SO, CA, OV
        with m.If(internal_op == MicrOp.OP_CMP):
            comb += e.xer_in.eq(1 << XERRegsEnum.SO)  # SO
        with m.If(internal_op == MicrOp.OP_MTSPR):
            comb += e.xer_out.eq(1)

        # set the trapaddr to 0x700 for a td/tw/tdi/twi operation
        with m.If(op.internal_op == MicrOp.OP_TRAP):
            # *DO NOT* call self.trap here.  that would reset absolutely
            # everything including destroying read of RA and RB.
            comb += self.do_copy("trapaddr", 0x70)  # strip first nibble

        ####################
        # ok so the instruction's been decoded, blah blah, however
        # now we need to determine if it's actually going to go ahead...
        # *or* if in fact it's a privileged operation, whether there's
        # an external interrupt, etc. etc.  this is a simple priority
        # if-elif-elif sequence.  decrement takes highest priority,
        # EINT next highest, privileged operation third.

        # check if instruction is privileged
        is_priv_insn = instr_is_priv(m, op.internal_op, e.do.insn)

        # different IRQ conditions
        ext_irq_ok = Signal()
        dec_irq_ok = Signal()
        priv_ok = Signal()
        illeg_ok = Signal()
        ldst_exc = self.ldst_exc

        comb += ext_irq_ok.eq(ext_irq & msr[MSR.EE])  # v3.0B p944 (MSR.EE)
        comb += dec_irq_ok.eq(dec_spr[63] & msr[MSR.EE])  # 6.5.11 p1076
        comb += priv_ok.eq(is_priv_insn & msr[MSR.PR])
        comb += illeg_ok.eq(op.internal_op == MicrOp.OP_ILLEGAL)

        # absolute top priority: check for an instruction failed
        with m.If(self.instr_fault):
            comb += self.e.eq(0)  # reset eeeeeverything
            comb += self.do_copy("insn", self.dec.opcode_in, True)
            comb += self.do_copy("insn_type", MicrOp.OP_FETCH_FAILED, True)
            comb += self.do_copy("fn_unit", Function.MMU, True)
            comb += self.do_copy("cia", self.state.pc, True)  # PC
            comb += self.do_copy("msr", self.state.msr, True)  # MSR
            # special override on internal_op, due to being a "fake" op
            comb += self.dec.op.internal_op.eq(MicrOp.OP_FETCH_FAILED)

        # LD/ST exceptions.  TestIssuer copies the exception info at us
        # after a failed LD/ST.
        with m.Elif(ldst_exc.happened):
            with m.If(ldst_exc.alignment):
                self.trap(m, TT.MEMEXC, 0x600)
            with m.Elif(ldst_exc.instr_fault):
                with m.If(ldst_exc.segment_fault):
                    self.trap(m, TT.MEMEXC, 0x480)
                with m.Else():
                    # pass exception info to trap to create SRR1
                    self.trap(m, TT.MEMEXC, 0x400, ldst_exc)
            with m.Else():
                with m.If(ldst_exc.segment_fault):
                    self.trap(m, TT.MEMEXC, 0x380)
                with m.Else():
                    self.trap(m, TT.MEMEXC, 0x300)

        # decrement counter (v3.0B p1099): TODO 32-bit version (MSR.LPCR)
        with m.Elif(dec_irq_ok):
            self.trap(m, TT.DEC, 0x900)   # v3.0B 6.5 p1065

        # external interrupt? only if MSR.EE set
        with m.Elif(ext_irq_ok):
            self.trap(m, TT.EINT, 0x500)

        # privileged instruction trap
        with m.Elif(priv_ok):
            self.trap(m, TT.PRIV, 0x700)

        # illegal instruction must redirect to trap. this is done by
        # *overwriting* the decoded instruction and starting again.
        # (note: the same goes for interrupts and for privileged operations,
        # just with different trapaddr and traptype)
        with m.Elif(illeg_ok):
            # illegal instruction trap
            self.trap(m, TT.ILLEG, 0x700)

        # no exception, just copy things to the output
        with m.Else():
            comb += e_out.eq(e)

        ####################
        # follow-up after trap/irq to set up SRR0/1

        # trap: (note e.insn_type so this includes OP_ILLEGAL) set up fast regs
        # Note: OP_SC could actually be modified to just be a trap
        with m.If((do_out.insn_type == MicrOp.OP_TRAP) |
                  (do_out.insn_type == MicrOp.OP_SC)):
            # TRAP write fast1 = SRR0
            comb += e_out.write_fast1.data.eq(FastRegsEnum.SRR0)  # SRR0
            comb += e_out.write_fast1.ok.eq(1)
            # TRAP write fast2 = SRR1
            comb += e_out.write_fast2.data.eq(FastRegsEnum.SRR1)  # SRR1
            comb += e_out.write_fast2.ok.eq(1)
            # TRAP write fast2 = SRR1
            comb += e_out.write_fast3.data.eq(FastRegsEnum.SVSRR0)  # SVSRR0
            comb += e_out.write_fast3.ok.eq(1)

        # RFID: needs to read SRR0/1
        with m.If(do_out.insn_type == MicrOp.OP_RFID):
            # TRAP read fast1 = SRR0
            comb += e_out.read_fast1.data.eq(FastRegsEnum.SRR0)  # SRR0
            comb += e_out.read_fast1.ok.eq(1)
            # TRAP read fast2 = SRR1
            comb += e_out.read_fast2.data.eq(FastRegsEnum.SRR1)  # SRR1
            comb += e_out.read_fast2.ok.eq(1)
            # TRAP read fast2 = SVSRR0
            comb += e_out.read_fast3.data.eq(FastRegsEnum.SVSRR0)  # SVSRR0
            comb += e_out.read_fast3.ok.eq(1)

        # annoying simulator bug.
        # asmcode may end up getting used for perfcounters?
        asmcode = self.op_get("asmcode")
        if hasattr(e_out, "asmcode") and asmcode is not None:
            comb += e_out.asmcode.eq(asmcode)

        return m

    def trap(self, m, traptype, trapaddr, ldst_exc=None):
        """trap: this basically "rewrites" the decoded instruction as a trap
        """
        comb = m.d.comb
        e = self.e
        comb += e.eq(0)  # reset eeeeeverything

        # start again
        comb += self.do_copy("insn", self.dec.opcode_in, True)
        comb += self.do_copy("insn_type", MicrOp.OP_TRAP, True)
        comb += self.do_copy("fn_unit", Function.TRAP, True)
        comb += self.do_copy("trapaddr", trapaddr >> 4, True)  # bottom 4 bits
        comb += self.do_copy("traptype", traptype, True)  # request type
        comb += self.do_copy("ldst_exc", ldst_exc, True)  # request type
        comb += self.do_copy("msr", self.state.msr,
                             True)  # copy of MSR "state"
        comb += self.do_copy("cia", self.state.pc, True)  # copy of PC "state"
        comb += self.do_copy("svstate", self.state.svstate, True)  # SVSTATE


def get_rdflags(m, e, cu):
    """returns a sequential list of the read "ok" flags for a given FU.
    this list is in order of the CompUnit input specs
    """
    rdl = []
    for idx in range(cu.n_src):
        regfile, regname, _ = cu.get_in_spec(idx)
        decinfo = regspec_decode_read(m, e, regfile, regname)
        rdl.append(decinfo.okflag)
    log("rdflags", rdl)
    return Cat(*rdl)


if __name__ == '__main__':
    pdecode = create_pdecode()
    dec2 = PowerDecode2(pdecode, svp64_en=True)
    vl = rtlil.convert(dec2, ports=dec2.ports() + pdecode.ports())
    with open("dec2.il", "w") as f:
        f.write(vl)
