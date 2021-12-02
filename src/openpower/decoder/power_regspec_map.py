"""regspec_decode

functions for the relationship between regspecs and Decode2Execute1Type

these functions encodes the understanding (relationship) between
Regfiles, Computation Units, and the Power ISA Decoder (PowerDecoder2).

based on the regspec, which contains the register file name and register
name, return a tuple of:

* how the decoder should determine whether the Function Unit needs
  access to a given Regport or not
* which Regfile number on that port should be read to get that data
* when it comes to writing: likewise, which Regfile num should be written

Note that some of the port numbering encoding is *unary*.  in the case
of "Full Condition Register", it's a full 8-bit mask of read/write-enables.
This actually matches directly with the XFX field in MTCR, and at
some point that 8-bit mask from the instruction could actually be passed
directly through to full_cr (TODO).

For the INT and CR numbering, these are expressed in binary in the
instruction and need to be converted to unary (1<<read_reg1.data).
Note however that XFX in MTCR is unary-masked!

XER regs are implicitly-encoded (hard-coded) based on whether the
operation has carry or overflow.

FAST regfile is, again, implicitly encoded, back in PowerDecode2, based
on the type of operation (see DecodeB for an example, where fast_out
is set, then carried into read_fast2 in PowerDecode2).

The SPR regfile on the other hand is *binary*-encoded, and, furthermore,
has to be "remapped" to internal SPR Enum indices (see SPRMap in PowerDecode2)
see https://libre-so:.org/3d_gpu/architecture/regfile/ section on regspecs
"""
from nmigen import Const, Signal
from openpower.consts import XERRegsEnum, FastRegsEnum, StateRegsEnum
from openpower.decoder.power_enums import CryIn
from openpower.util import log
from collections import namedtuple

RegDecodeInfo = namedtuple("RedDecodeInfo", ['okflag', 'regport', 'portlen'])

# XXX TODO: these portlen numbers *must* increase / adapt for SVP64.

def regspec_decode_read(m, e, regfile, name):
    """regspec_decode_read
    """

    rd = None

    # INT regfile

    if regfile == 'INT':
        # Int register numbering is *unary* encoded
        if name == 'ra': # RA
            rd = RegDecodeInfo(e.read_reg1.ok, e.read_reg1.data, 5)
        if name == 'rb': # RB
            rd = RegDecodeInfo(e.read_reg2.ok, e.read_reg2.data, 5)
        if name == 'rc': # RS
            rd = RegDecodeInfo(e.read_reg3.ok, e.read_reg3.data, 5)

    # CR regfile

    if regfile == 'CR':
        # CRRegs register numbering is *unary* encoded
        if name == 'full_cr': # full CR (from FXM field)
            rd = RegDecodeInfo(e.do.read_cr_whole.ok,
                               e.do.read_cr_whole.data, 8)
        if name == 'cr_a': # CR A
            rd = RegDecodeInfo(e.read_cr1.ok, 1<<(7-e.read_cr1.data), 8)
        if name == 'cr_b': # CR B
            rd = RegDecodeInfo(e.read_cr2.ok, 1<<(7-e.read_cr2.data), 8)
        if name == 'cr_c': # CR C
            rd = RegDecodeInfo(e.read_cr3.ok, 1<<(7-e.read_cr3.data), 8)

    # XER regfile

    if regfile == 'XER':
        # XERRegsEnum register numbering is *unary* encoded
        SO = 1<<XERRegsEnum.SO
        CA = 1<<XERRegsEnum.CA
        OV = 1<<XERRegsEnum.OV
        if name == 'xer_so':
            # SO needs to be read for overflow *and* for creation
            # of CR0 and also for MFSPR
            rd = RegDecodeInfo(((e.do.oe.oe[0] & e.do.oe.ok) |
                                  (e.xer_in & SO == SO)|
                                  (e.do.rc.rc & e.do.rc.ok)), SO, 3)
        if name == 'xer_ov':
            rd = RegDecodeInfo(((e.do.oe.oe[0] & e.do.oe.ok) |
                                  (e.xer_in & CA == CA)), OV, 3)
        if name == 'xer_ca':
            rd = RegDecodeInfo(((e.do.input_carry == CryIn.CA.value) |
                                  (e.xer_in & OV == OV)), CA, 3)

    # STATE regfile

    if regfile == 'STATE':
        # STATE register numbering is *unary* encoded
        PC = 1<<StateRegsEnum.PC
        MSR = 1<<StateRegsEnum.MSR
        SVSTATE = 1<<StateRegsEnum.SVSTATE
        if name in ['cia', 'nia']:
            # TODO: detect read-conditions
            rd = RegDecodeInfo(Const(1), PC, 3)
        if name == 'msr':
            # TODO: detect read-conditions
            rd = RegDecodeInfo(Const(1), MSR, 3)
        if name == 'svstate':
            # TODO: detect read-conditions
            rd = RegDecodeInfo(Const(1), SVSTATE, 3)

    # FAST regfile

    if regfile == 'FAST':
        # FAST register numbering is *unary* encoded
        if name == 'fast1':
            rd = RegDecodeInfo(e.read_fast1.ok, e.read_fast1.data, 4)
        if name == 'fast2':
            rd = RegDecodeInfo(e.read_fast2.ok, e.read_fast2.data, 4)
        if name == 'fast3':
            rd = RegDecodeInfo(e.read_fast3.ok, e.read_fast3.data, 4)

    # SPR regfile

    if regfile == 'SPR':
        # SPR register numbering is *binary* encoded
        if name == 'spr1':
            rd = RegDecodeInfo(e.read_spr1.ok, e.read_spr1.data, 10)

    assert rd is not None, "regspec not found %s %s" % (regfile, name)

    rname="rd_decode_%s_%s" % (regfile, name)
    ok = Signal(name=rname+"_ok", reset_less=True)
    data = Signal(rd.portlen, name=rname+"_port", reset_less=True)
    m.d.comb += ok.eq(rd.okflag)
    m.d.comb += data.eq(rd.regport)

    return RegDecodeInfo(ok, data, rd.portlen)


def regspec_decode_write(m, e, regfile, name):
    """regspec_decode_write
    """

    #log("regspec_decode_write", regfile, name, e.__class__.__name__)
    wr = None

    # INT regfile

    if regfile == 'INT':
        # Int register numbering is *unary* encoded
        if name == 'o': # RT
            wr = RegDecodeInfo(e.write_reg.ok, e.write_reg.data, 5)
        if name == 'o1': # RA (update mode: LD/ST EA)
            wr = RegDecodeInfo(e.write_ea.ok, e.write_ea.data, 5)

    # CR regfile

    if regfile == 'CR':
        # CRRegs register numbering is *unary* encoded
        # *sigh*.  numbering inverted on part-CRs.  because POWER.
        if name == 'full_cr': # full CR (from FXM field)
            wr = RegDecodeInfo(e.do.write_cr_whole.ok,
                                 e.do.write_cr_whole.data, 8)
        if name == 'cr_a': # CR A
            wr = RegDecodeInfo(e.write_cr.ok,
                               1<<(7-e.write_cr.data), 8)

    # XER regfile

    if regfile == 'XER':
        # XERRegsEnum register numbering is *unary* encoded
        SO = 1<<XERRegsEnum.SO
        CA = 1<<XERRegsEnum.CA
        OV = 1<<XERRegsEnum.OV
        if name == 'xer_so':
            wr = RegDecodeInfo(e.xer_out | (e.do.oe.oe[0] & e.do.oe.ok),
                                    SO, 3) # hmmm
        if name == 'xer_ov':
            wr = RegDecodeInfo(e.xer_out | (e.do.oe.oe[0] & e.do.oe.ok),
                                    OV, 3) # hmmm
        if name == 'xer_ca':
            wr = RegDecodeInfo(e.xer_out | (e.do.output_carry),
                                    CA, 3) # hmmm

    # STATE regfile

    if regfile == 'STATE':
        # STATE register numbering is *unary* encoded
        PC = 1<<StateRegsEnum.PC
        MSR = 1<<StateRegsEnum.MSR
        SVSTATE = 1<<StateRegsEnum.SVSTATE
        if name in ['cia', 'nia']:
            wr = RegDecodeInfo(None, PC, 3) # hmmm
        if name == 'msr':
            wr = RegDecodeInfo(None, MSR, 3) # hmmm
        if name == 'svstate':
            wr = RegDecodeInfo(None, SVSTATE, 3) # hmmm

    # FAST regfile

    if regfile == 'FAST':
        # FAST register numbering is *unary* encoded
        if name == 'fast1':
            wr = RegDecodeInfo(e.write_fast1.ok, e.write_fast1.data, 4)
        if name == 'fast2':
            wr = RegDecodeInfo(e.write_fast2.ok, e.write_fast2.data, 4)
        if name == 'fast3':
            wr = RegDecodeInfo(e.write_fast3.ok, e.write_fast3.data, 4)

    # SPR regfile

    if regfile == 'SPR':
        # SPR register numbering is *binary* encoded
        if name == 'spr1': # SPR1
            wr = RegDecodeInfo(e.write_spr.ok, e.write_spr.data, 10)

    assert wr is not None, "regspec not found %s %s" % (regfile, name)

    rname="wr_decode_%s_%s" % (regfile, name)
    if wr.okflag is not None:
        ok = Signal(name=rname+"_ok", reset_less=True)
        m.d.comb += ok.eq(wr.okflag)
    else:
        # XXX urrrr, really do have to deal with this some time
        ok = None
    data = Signal(wr.portlen, name=rname+"_port", reset_less=True)
    m.d.comb += data.eq(wr.regport)

    return RegDecodeInfo(ok, data, wr.portlen)


def regspec_decode(m, readmode, e, regfile, name):
    if readmode:
        return regspec_decode_read(m, e, regfile, name)
    return regspec_decode_write(m, e, regfile, name)

