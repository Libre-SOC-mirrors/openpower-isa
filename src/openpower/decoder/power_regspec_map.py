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
see https://libre-soc.org/3d_gpu/architecture/regfile/ section on regspecs
"""
from nmigen import Const
from openpower.consts import XERRegsEnum, FastRegsEnum, StateRegsEnum
from openpower.decoder.power_enums import CryIn
from openpower.util import log
from collections import namedtuple

RegDecodeInfo = namedtuple("RedDecodeInfo", ['okflag', 'regport'])

def regspec_decode_read(m, e, regfile, name):
    """regspec_decode_read
    """

    # INT regfile

    if regfile == 'INT':
        # Int register numbering is *unary* encoded
        if name == 'ra': # RA
            return RegDecodeInfo(e.read_reg1.ok, e.read_reg1.data)
        if name == 'rb': # RB
            return RegDecodeInfo(e.read_reg2.ok, e.read_reg2.data)
        if name == 'rc': # RS
            return RegDecodeInfo(e.read_reg3.ok, e.read_reg3.data)

    # CR regfile

    if regfile == 'CR':
        # CRRegs register numbering is *unary* encoded
        if name == 'full_cr': # full CR (from FXM field)
            return RegDecodeInfo(e.do.read_cr_whole.ok, e.do.read_cr_whole.data)
        if name == 'cr_a': # CR A
            return RegDecodeInfo(e.read_cr1.ok, 1<<(7-e.read_cr1.data))
        if name == 'cr_b': # CR B
            return RegDecodeInfo(e.read_cr2.ok, 1<<(7-e.read_cr2.data))
        if name == 'cr_c': # CR C
            return RegDecodeInfo(e.read_cr3.ok, 1<<(7-e.read_cr3.data))

    # XER regfile

    if regfile == 'XER':
        # XERRegsEnum register numbering is *unary* encoded
        SO = 1<<XERRegsEnum.SO
        CA = 1<<XERRegsEnum.CA
        OV = 1<<XERRegsEnum.OV
        if name == 'xer_so':
            # SO needs to be read for overflow *and* for creation
            # of CR0 and also for MFSPR
            return RegDecodeInfo(((e.do.oe.oe[0] & e.do.oe.ok) |
                                  (e.xer_in & SO == SO)|
                                  (e.do.rc.rc & e.do.rc.ok)), SO)
        if name == 'xer_ov':
            return RegDecodeInfo(((e.do.oe.oe[0] & e.do.oe.ok) |
                                  (e.xer_in & CA == CA)), OV)
        if name == 'xer_ca':
            return RegDecodeInfo(((e.do.input_carry == CryIn.CA.value) |
                                  (e.xer_in & OV == OV)), CA)

    # STATE regfile

    if regfile == 'STATE':
        # STATE register numbering is *unary* encoded
        PC = 1<<StateRegsEnum.PC
        MSR = 1<<StateRegsEnum.MSR
        SVSTATE = 1<<StateRegsEnum.SVSTATE
        if name in ['cia', 'nia']:
            return RegDecodeInfo(Const(1),
                                 PC) # TODO: detect read-conditions
        if name == 'msr':
            return RegDecodeInfo(Const(1),
                                 MSR) # TODO: detect read-conditions
        if name == 'svstate':
            return RegDecodeInfo(Const(1),
                                 SVSTATE) # TODO: detect read-conditions

    # FAST regfile

    if regfile == 'FAST':
        # FAST register numbering is *unary* encoded
        if name == 'fast1':
            return RegDecodeInfo(e.read_fast1.ok, e.read_fast1.data)
        if name == 'fast2':
            return RegDecodeInfo(e.read_fast2.ok, e.read_fast2.data)
        if name == 'fast3':
            return RegDecodeInfo(e.read_fast3.ok, e.read_fast3.data)

    # SPR regfile

    if regfile == 'SPR':
        # SPR register numbering is *binary* encoded
        if name == 'spr1':
            return RegDecodeInfo(e.read_spr1.ok, e.read_spr1.data)

    assert False, "regspec not found %s %s" % (regfile, name)


def regspec_decode_write(m, e, regfile, name):
    """regspec_decode_write
    """

    #log("regspec_decode_write", regfile, name, e.__class__.__name__)

    # INT regfile

    if regfile == 'INT':
        # Int register numbering is *unary* encoded
        if name == 'o': # RT
            return RegDecodeInfo(e.write_reg.ok, e.write_reg.data)
        if name == 'o1': # RA (update mode: LD/ST EA)
            return RegDecodeInfo(e.write_ea.ok, e.write_ea.data)

    # CR regfile

    if regfile == 'CR':
        # CRRegs register numbering is *unary* encoded
        # *sigh*.  numbering inverted on part-CRs.  because POWER.
        if name == 'full_cr': # full CR (from FXM field)
            return RegDecodeInfo(e.do.write_cr_whole.ok,
                                 e.do.write_cr_whole.data)
        if name == 'cr_a': # CR A
            return RegDecodeInfo(e.write_cr.ok, (1<<(7-e.write_cr.data))[0:8])

    # XER regfile

    if regfile == 'XER':
        # XERRegsEnum register numbering is *unary* encoded
        SO = 1<<XERRegsEnum.SO
        CA = 1<<XERRegsEnum.CA
        OV = 1<<XERRegsEnum.OV
        if name == 'xer_so':
            return RegDecodeInfo(e.xer_out | (e.do.oe.oe[0] & e.do.oe.ok),
                                    SO) # hmmm
        if name == 'xer_ov':
            return RegDecodeInfo(e.xer_out | (e.do.oe.oe[0] & e.do.oe.ok),
                                    OV) # hmmm
        if name == 'xer_ca':
            return RegDecodeInfo(e.xer_out | (e.do.output_carry),
                                    CA) # hmmm

    # STATE regfile

    if regfile == 'STATE':
        # STATE register numbering is *unary* encoded
        PC = 1<<StateRegsEnum.PC
        MSR = 1<<StateRegsEnum.MSR
        SVSTATE = 1<<StateRegsEnum.SVSTATE
        if name in ['cia', 'nia']:
            return RegDecodeInfo(None, PC) # hmmm
        if name == 'msr':
            return RegDecodeInfo(None, MSR) # hmmm
        if name == 'svstate':
            return RegDecodeInfo(None, SVSTATE) # hmmm

    # FAST regfile

    if regfile == 'FAST':
        # FAST register numbering is *unary* encoded
        if name == 'fast1':
            return RegDecodeInfo(e.write_fast1.ok, e.write_fast1.data)
        if name == 'fast2':
            return RegDecodeInfo(e.write_fast2.ok, e.write_fast2.data)
        if name == 'fast3':
            return RegDecodeInfo(e.write_fast3.ok, e.write_fast3.data)

    # SPR regfile

    if regfile == 'SPR':
        # SPR register numbering is *binary* encoded
        if name == 'spr1': # SPR1
            return RegDecodeInfo(e.write_spr.ok, e.write_spr.data)

    assert False, "regspec not found %s %s" % (regfile, name)


def regspec_decode(m, readmode, e, regfile, name):
    if readmode:
        return regspec_decode_read(m, e, regfile, name)
    return regspec_decode_write(m, e, regfile, name)

