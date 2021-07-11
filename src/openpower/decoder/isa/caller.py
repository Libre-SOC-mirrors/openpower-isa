# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2020, 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Copyright (C) 2020 Michael Nolan
# Funded by NLnet http://nlnet.nl
"""core of the python-based POWER9 simulator

this is part of a cycle-accurate POWER9 simulator.  its primary purpose is
not speed, it is for both learning and educational purposes, as well as
a method of verifying the HDL.

related bugs:

* https://bugs.libre-soc.org/show_bug.cgi?id=424
"""

from nmigen.back.pysim import Settle
from functools import wraps
from copy import copy
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.selectable_int import (FieldSelectableInt, SelectableInt,
                                        selectconcat)
from openpower.decoder.power_enums import (spr_dict, spr_byname, XER_bits,
                                     insns, MicrOp, In1Sel, In2Sel, In3Sel,
                                     OutSel, CROutSel, LDSTMode,
                                     SVP64RMMode, SVP64PredMode,
                                     SVP64PredInt, SVP64PredCR,
                                     SVP64LDSTmode)

from openpower.decoder.power_enums import SVPtype

from openpower.decoder.helpers import (exts, gtu, ltu, undefined, bitrev)
from openpower.consts import PIb, MSRb  # big-endian (PowerISA versions)
from openpower.consts import SVP64CROffs
from openpower.decoder.power_svp64 import SVP64RM, decode_extra

from openpower.decoder.isa.radixmmu import RADIX
from openpower.decoder.isa.mem import Mem, swap_order, MemException
from openpower.decoder.isa.svshape import SVSHAPE

from openpower.util import log

from collections import namedtuple
import math
import sys

instruction_info = namedtuple('instruction_info',
                              'func read_regs uninit_regs write_regs ' +
                              'special_regs op_fields form asmregs')

special_sprs = {
    'LR': 8,
    'CTR': 9,
    'TAR': 815,
    'XER': 1,
    'VRSAVE': 256}


REG_SORT_ORDER = {
    # TODO (lkcl): adjust other registers that should be in a particular order
    # probably CA, CA32, and CR
    "FRT": 0,
    "FRA": 0,
    "FRB": 0,
    "FRC": 0,
    "FRS": 0,
    "RT": 0,
    "RA": 0,
    "RB": 0,
    "RC": 0,
    "RS": 0,
    "CR": 0,
    "LR": 0,
    "CTR": 0,
    "TAR": 0,
    "MSR": 0,
    "SVSTATE": 0,
    "SVSHAPE0": 0,
    "SVSHAPE1": 0,
    "SVSHAPE2": 0,
    "SVSHAPE3": 0,

    "CA": 0,
    "CA32": 0,

    "overflow": 7, # should definitely be last
}

fregs = ['FRA', 'FRB', 'FRC', 'FRS', 'FRT']


def create_args(reglist, extra=None):
    retval = list(OrderedSet(reglist))
    retval.sort(key=lambda reg: REG_SORT_ORDER.get(reg, 0))
    if extra is not None:
        return [extra] + retval
    return retval



class GPR(dict):
    def __init__(self, decoder, isacaller, svstate, regfile):
        dict.__init__(self)
        self.sd = decoder
        self.isacaller = isacaller
        self.svstate = svstate
        for i in range(len(regfile)):
            self[i] = SelectableInt(regfile[i], 64)

    def __call__(self, ridx):
        if isinstance(ridx, SelectableInt):
            ridx = ridx.value
        return self[ridx]

    def set_form(self, form):
        self.form = form

    def __setitem__(self, rnum, value):
        # rnum = rnum.value # only SelectableInt allowed
        log("GPR setitem", rnum, value)
        if isinstance(rnum, SelectableInt):
            rnum = rnum.value
        dict.__setitem__(self, rnum, value)

    def getz(self, rnum):
        # rnum = rnum.value # only SelectableInt allowed
        log("GPR getzero?", rnum)
        if rnum == 0:
            return SelectableInt(0, 64)
        return self[rnum]

    def _get_regnum(self, attr):
        getform = self.sd.sigforms[self.form]
        rnum = getattr(getform, attr)
        return rnum

    def ___getitem__(self, attr):
        """ XXX currently not used
        """
        rnum = self._get_regnum(attr)
        log("GPR getitem", attr, rnum)
        return self.regfile[rnum]

    def dump(self, printout=True):
        res = []
        for i in range(len(self)):
            res.append(self[i].value)
        if printout:
            for i in range(0, len(res), 8):
                s = []
                for j in range(8):
                    s.append("%08x" % res[i+j])
                s = ' '.join(s)
                print("reg", "%2d" % i, s)
        return res


class SPR(dict):
    def __init__(self, dec2, initial_sprs={}):
        self.sd = dec2
        dict.__init__(self)
        for key, v in initial_sprs.items():
            if isinstance(key, SelectableInt):
                key = key.value
            key = special_sprs.get(key, key)
            if isinstance(key, int):
                info = spr_dict[key]
            else:
                info = spr_byname[key]
            if not isinstance(v, SelectableInt):
                v = SelectableInt(v, info.length)
            self[key] = v

    def __getitem__(self, key):
        log("get spr", key)
        log("dict", self.items())
        # if key in special_sprs get the special spr, otherwise return key
        if isinstance(key, SelectableInt):
            key = key.value
        if isinstance(key, int):
            key = spr_dict[key].SPR
        key = special_sprs.get(key, key)
        if key == 'HSRR0':  # HACK!
            key = 'SRR0'
        if key == 'HSRR1':  # HACK!
            key = 'SRR1'
        if key in self:
            res = dict.__getitem__(self, key)
        else:
            if isinstance(key, int):
                info = spr_dict[key]
            else:
                info = spr_byname[key]
            dict.__setitem__(self, key, SelectableInt(0, info.length))
            res = dict.__getitem__(self, key)
        log("spr returning", key, res)
        return res

    def __setitem__(self, key, value):
        if isinstance(key, SelectableInt):
            key = key.value
        if isinstance(key, int):
            key = spr_dict[key].SPR
            log("spr key", key)
        key = special_sprs.get(key, key)
        if key == 'HSRR0':  # HACK!
            self.__setitem__('SRR0', value)
        if key == 'HSRR1':  # HACK!
            self.__setitem__('SRR1', value)
        log("setting spr", key, value)
        dict.__setitem__(self, key, value)

    def __call__(self, ridx):
        return self[ridx]

    def dump(self, printout=True):
        res = []
        keys = list(self.keys())
        #keys.sort()
        for k in keys:
            sprname = spr_dict.get(k, None)
            if sprname is None:
                sprname = k
            else:
                sprname = sprname.SPR
            res.append((sprname, self[k].value))
        if printout:
            for sprname, value in res:
                print("    ", sprname, hex(value))
        return res


class PC:
    def __init__(self, pc_init=0):
        self.CIA = SelectableInt(pc_init, 64)
        self.NIA = self.CIA + SelectableInt(4, 64) # only true for v3.0B!

    def update_nia(self, is_svp64):
        increment = 8 if is_svp64 else 4
        self.NIA = self.CIA + SelectableInt(increment, 64)

    def update(self, namespace, is_svp64):
        """updates the program counter (PC) by 4 if v3.0B mode or 8 if SVP64
        """
        self.CIA = namespace['NIA'].narrow(64)
        self.update_nia(is_svp64)
        namespace['CIA'] = self.CIA
        namespace['NIA'] = self.NIA


# Simple-V: see https://libre-soc.org/openpower/sv
class SVP64State:
    def __init__(self, init=0):
        self.spr = SelectableInt(init, 32)
        # fields of SVSTATE, see https://libre-soc.org/openpower/sv/sprs/
        self.maxvl = FieldSelectableInt(self.spr, tuple(range(0,7)))
        self.vl = FieldSelectableInt(self.spr, tuple(range(7,14)))
        self.srcstep = FieldSelectableInt(self.spr, tuple(range(14,21)))
        self.dststep = FieldSelectableInt(self.spr, tuple(range(21,28)))
        self.subvl = FieldSelectableInt(self.spr, tuple(range(28,30)))
        self.svstep = FieldSelectableInt(self.spr, tuple(range(30,32)))


# SVP64 ReMap field
class SVP64RMFields:
    def __init__(self, init=0):
        self.spr = SelectableInt(init, 24)
        # SVP64 RM fields: see https://libre-soc.org/openpower/sv/svp64/
        self.mmode = FieldSelectableInt(self.spr, [0])
        self.mask = FieldSelectableInt(self.spr, tuple(range(1,4)))
        self.elwidth = FieldSelectableInt(self.spr, tuple(range(4,6)))
        self.ewsrc = FieldSelectableInt(self.spr, tuple(range(6,8)))
        self.subvl = FieldSelectableInt(self.spr, tuple(range(8,10)))
        self.extra = FieldSelectableInt(self.spr, tuple(range(10,19)))
        self.mode = FieldSelectableInt(self.spr, tuple(range(19,24)))
        # these cover the same extra field, split into parts as EXTRA2
        self.extra2 = list(range(4))
        self.extra2[0] = FieldSelectableInt(self.spr, tuple(range(10,12)))
        self.extra2[1] = FieldSelectableInt(self.spr, tuple(range(12,14)))
        self.extra2[2] = FieldSelectableInt(self.spr, tuple(range(14,16)))
        self.extra2[3] = FieldSelectableInt(self.spr, tuple(range(16,18)))
        self.smask = FieldSelectableInt(self.spr, tuple(range(16,19)))
        # and here as well, but EXTRA3
        self.extra3 = list(range(3))
        self.extra3[0] = FieldSelectableInt(self.spr, tuple(range(10,13)))
        self.extra3[1] = FieldSelectableInt(self.spr, tuple(range(13,16)))
        self.extra3[2] = FieldSelectableInt(self.spr, tuple(range(16,19)))


SVP64RM_MMODE_SIZE = len(SVP64RMFields().mmode.br)
SVP64RM_MASK_SIZE = len(SVP64RMFields().mask.br)
SVP64RM_ELWIDTH_SIZE = len(SVP64RMFields().elwidth.br)
SVP64RM_EWSRC_SIZE = len(SVP64RMFields().ewsrc.br)
SVP64RM_SUBVL_SIZE = len(SVP64RMFields().subvl.br)
SVP64RM_EXTRA2_SPEC_SIZE = len(SVP64RMFields().extra2[0].br)
SVP64RM_EXTRA3_SPEC_SIZE = len(SVP64RMFields().extra3[0].br)
SVP64RM_SMASK_SIZE = len(SVP64RMFields().smask.br)
SVP64RM_MODE_SIZE = len(SVP64RMFields().mode.br)


# SVP64 Prefix fields: see https://libre-soc.org/openpower/sv/svp64/
class SVP64PrefixFields:
    def __init__(self):
        self.insn = SelectableInt(0, 32)
        # 6 bit major opcode EXT001, 2 bits "identifying" (7, 9), 24 SV ReMap
        self.major = FieldSelectableInt(self.insn, tuple(range(0,6)))
        self.pid = FieldSelectableInt(self.insn, (7, 9)) # must be 0b11
        rmfields = [6, 8] + list(range(10,32)) # SVP64 24-bit RM (ReMap)
        self.rm = FieldSelectableInt(self.insn, rmfields)


SV64P_MAJOR_SIZE = len(SVP64PrefixFields().major.br)
SV64P_PID_SIZE = len(SVP64PrefixFields().pid.br)
SV64P_RM_SIZE = len(SVP64PrefixFields().rm.br)


# CR register fields
# See PowerISA Version 3.0 B Book 1
# Section 2.3.1 Condition Register pages 30 - 31
class CRFields:
    LT = FL = 0  # negative, less than, floating-point less than
    GT = FG = 1  # positive, greater than, floating-point greater than
    EQ = FE = 2  # equal, floating-point equal
    SO = FU = 3  # summary overflow, floating-point unordered

    def __init__(self, init=0):
        # rev_cr = int('{:016b}'.format(initial_cr)[::-1], 2)
        # self.cr = FieldSelectableInt(self._cr, list(range(32, 64)))
        self.cr = SelectableInt(init, 64)  # underlying reg
        # field-selectable versions of Condition Register TODO check bitranges?
        self.crl = []
        for i in range(8):
            bits = tuple(range(i*4+32, (i+1)*4+32))
            _cr = FieldSelectableInt(self.cr, bits)
            self.crl.append(_cr)

# decode SVP64 predicate integer to reg number and invert
def get_predint(gpr, mask):
    r10 = gpr(10)
    r30 = gpr(30)
    log ("get_predint", mask, SVP64PredInt.ALWAYS.value)
    if mask == SVP64PredInt.ALWAYS.value:
        return 0xffff_ffff_ffff_ffff
    if mask == SVP64PredInt.R3_UNARY.value:
        return 1 << (gpr(3).value & 0b111111)
    if mask == SVP64PredInt.R3.value:
        return gpr(3).value
    if mask == SVP64PredInt.R3_N.value:
        return ~gpr(3).value
    if mask == SVP64PredInt.R10.value:
        return gpr(10).value
    if mask == SVP64PredInt.R10_N.value:
        return ~gpr(10).value
    if mask == SVP64PredInt.R30.value:
        return gpr(30).value
    if mask == SVP64PredInt.R30_N.value:
        return ~gpr(30).value

# decode SVP64 predicate CR to reg number and invert status
def _get_predcr(mask):
    if mask == SVP64PredCR.LT.value:
        return 0, 1
    if mask == SVP64PredCR.GE.value:
        return 0, 0
    if mask == SVP64PredCR.GT.value:
        return 1, 1
    if mask == SVP64PredCR.LE.value:
        return 1, 0
    if mask == SVP64PredCR.EQ.value:
        return 2, 1
    if mask == SVP64PredCR.NE.value:
        return 2, 0
    if mask == SVP64PredCR.SO.value:
        return 3, 1
    if mask == SVP64PredCR.NS.value:
        return 3, 0

# read individual CR fields (0..VL-1), extract the required bit
# and construct the mask
def get_predcr(crl, mask, vl):
    idx, noninv = _get_predcr(mask)
    mask = 0
    for i in range(vl):
        cr = crl[i+SVP64CROffs.CRPred]
        if cr[idx].value == noninv:
            mask |= (1<<i)
    return mask


# TODO, really should just be using PowerDecoder2
def get_pdecode_idx_in(dec2, name):
    op = dec2.dec.op
    in1_sel = yield op.in1_sel
    in2_sel = yield op.in2_sel
    in3_sel = yield op.in3_sel
    # get the IN1/2/3 from the decoder (includes SVP64 remap and isvec)
    in1 = yield dec2.e.read_reg1.data
    in2 = yield dec2.e.read_reg2.data
    in3 = yield dec2.e.read_reg3.data
    in1_isvec = yield dec2.in1_isvec
    in2_isvec = yield dec2.in2_isvec
    in3_isvec = yield dec2.in3_isvec
    log ("get_pdecode_idx_in in1", name, in1_sel, In1Sel.RA.value,
                                     in1, in1_isvec)
    log ("get_pdecode_idx_in in2", name, in2_sel, In2Sel.RB.value,
                                     in2, in2_isvec)
    log ("get_pdecode_idx_in in3", name, in3_sel, In3Sel.RS.value,
                                     in3, in3_isvec)
    log ("get_pdecode_idx_in FRS in3", name, in3_sel, In3Sel.FRS.value,
                                     in3, in3_isvec)
    log ("get_pdecode_idx_in FRB in2", name, in2_sel, In2Sel.FRB.value,
                                     in2, in2_isvec)
    log ("get_pdecode_idx_in FRC in3", name, in3_sel, In3Sel.FRC.value,
                                     in3, in3_isvec)
    # identify which regnames map to in1/2/3
    if name == 'RA':
        if (in1_sel == In1Sel.RA.value or
            (in1_sel == In1Sel.RA_OR_ZERO.value and in1 != 0)):
            return in1, in1_isvec
        if in1_sel == In1Sel.RA_OR_ZERO.value:
            return in1, in1_isvec
    elif name == 'RB':
        if in2_sel == In2Sel.RB.value:
            return in2, in2_isvec
        if in3_sel == In3Sel.RB.value:
            return in3, in3_isvec
    # XXX TODO, RC doesn't exist yet!
    elif name == 'RC':
        assert False, "RC does not exist yet"
    elif name == 'RS':
        if in1_sel == In1Sel.RS.value:
            return in1, in1_isvec
        if in2_sel == In2Sel.RS.value:
            return in2, in2_isvec
        if in3_sel == In3Sel.RS.value:
            return in3, in3_isvec
    elif name == 'FRA':
        if in1_sel == In1Sel.FRA.value:
            return in1, in1_isvec
    elif name == 'FRB':
        if in2_sel == In2Sel.FRB.value:
            return in2, in2_isvec
    elif name == 'FRC':
        if in3_sel == In3Sel.FRC.value:
            return in3, in3_isvec
    elif name == 'FRS':
        if in1_sel == In1Sel.FRS.value:
            return in1, in1_isvec
        if in3_sel == In3Sel.FRS.value:
            return in3, in3_isvec
    return None, False


# TODO, really should just be using PowerDecoder2
def get_pdecode_cr_out(dec2, name):
    op = dec2.dec.op
    out_sel = yield op.cr_out
    out_bitfield = yield dec2.dec_cr_out.cr_bitfield.data
    sv_cr_out = yield op.sv_cr_out
    spec = yield dec2.crout_svdec.spec
    sv_override = yield dec2.dec_cr_out.sv_override
    # get the IN1/2/3 from the decoder (includes SVP64 remap and isvec)
    out = yield dec2.e.write_cr.data
    o_isvec = yield dec2.o_isvec
    log ("get_pdecode_cr_out", out_sel, CROutSel.CR0.value, out, o_isvec)
    log ("    sv_cr_out", sv_cr_out)
    log ("    cr_bf", out_bitfield)
    log ("    spec", spec)
    log ("    override", sv_override)
    # identify which regnames map to out / o2
    if name == 'CR0':
        if out_sel == CROutSel.CR0.value:
            return out, o_isvec
    log ("get_pdecode_cr_out not found", name)
    return None, False


# TODO, really should just be using PowerDecoder2
def get_pdecode_idx_out(dec2, name):
    op = dec2.dec.op
    out_sel = yield op.out_sel
    # get the IN1/2/3 from the decoder (includes SVP64 remap and isvec)
    out = yield dec2.e.write_reg.data
    o_isvec = yield dec2.o_isvec
    # identify which regnames map to out / o2
    if name == 'RA':
        log ("get_pdecode_idx_out", out_sel, OutSel.RA.value, out, o_isvec)
        if out_sel == OutSel.RA.value:
            return out, o_isvec
    elif name == 'RT':
        log ("get_pdecode_idx_out", out_sel, OutSel.RT.value,
                                      OutSel.RT_OR_ZERO.value, out, o_isvec,
                                      dec2.dec.RT)
        if out_sel == OutSel.RT.value:
            return out, o_isvec
    elif name == 'FRA':
        log ("get_pdecode_idx_out", out_sel, OutSel.FRA.value, out, o_isvec)
        if out_sel == OutSel.FRA.value:
            return out, o_isvec
    elif name == 'FRT':
        log ("get_pdecode_idx_out", out_sel, OutSel.FRT.value,
                                      OutSel.FRT.value, out, o_isvec)
        if out_sel == OutSel.FRT.value:
            return out, o_isvec
    log ("get_pdecode_idx_out not found", name, out_sel, out, o_isvec)
    return None, False


# TODO, really should just be using PowerDecoder2
def get_pdecode_idx_out2(dec2, name):
    # check first if register is activated for write
    op = dec2.dec.op
    out_sel = yield op.out_sel
    out = yield dec2.e.write_ea.data
    o_isvec = yield dec2.o2_isvec
    out_ok = yield dec2.e.write_ea.ok
    log ("get_pdecode_idx_out2", name, out_sel, out, out_ok, o_isvec)
    if not out_ok:
        return None, False

    if name == 'RA':
        if hasattr(op, "upd"):
            # update mode LD/ST uses read-reg A also as an output
            upd = yield op.upd
            log ("get_pdecode_idx_out2", upd, LDSTMode.update.value,
                                           out_sel, OutSel.RA.value,
                                           out, o_isvec)
            if upd == LDSTMode.update.value:
                return out, o_isvec
    if name == 'FRS':
        int_op = yield dec2.dec.op.internal_op
        fft_en = yield dec2.use_svp64_fft
        #if int_op == MicrOp.OP_FP_MADD.value and fft_en:
        if fft_en:
            log ("get_pdecode_idx_out2", out_sel, OutSel.FRS.value,
                                           out, o_isvec)
            return out, o_isvec
    return None, False


class ISACaller:
    # decoder2 - an instance of power_decoder2
    # regfile - a list of initial values for the registers
    # initial_{etc} - initial values for SPRs, Condition Register, Mem, MSR
    # respect_pc - tracks the program counter.  requires initial_insns
    def __init__(self, decoder2, regfile, initial_sprs=None, initial_cr=0,
                 initial_mem=None, initial_msr=0,
                 initial_svstate=0,
                 initial_insns=None,
                 fpregfile=None,
                 respect_pc=False,
                 disassembly=None,
                 initial_pc=0,
                 bigendian=False,
                 mmu=False,
                 icachemmu=False):

        self.bigendian = bigendian
        self.halted = False
        self.is_svp64_mode = False
        self.respect_pc = respect_pc
        if initial_sprs is None:
            initial_sprs = {}
        if initial_mem is None:
            initial_mem = {}
        if fpregfile is None:
            fpregfile = [0] * 32
        if initial_insns is None:
            initial_insns = {}
            assert self.respect_pc == False, "instructions required to honor pc"

        log("ISACaller insns", respect_pc, initial_insns, disassembly)
        log("ISACaller initial_msr", initial_msr)

        # "fake program counter" mode (for unit testing)
        self.fake_pc = 0
        disasm_start = 0
        if not respect_pc:
            if isinstance(initial_mem, tuple):
                self.fake_pc = initial_mem[0]
                disasm_start = self.fake_pc
        else:
            disasm_start = initial_pc

        # disassembly: we need this for now (not given from the decoder)
        self.disassembly = {}
        if disassembly:
            for i, code in enumerate(disassembly):
                self.disassembly[i*4 + disasm_start] = code

        # set up registers, instruction memory, data memory, PC, SPRs, MSR, CR
        self.svp64rm = SVP64RM()
        if initial_svstate is None:
            initial_svstate = 0
        if isinstance(initial_svstate, int):
            initial_svstate = SVP64State(initial_svstate)
        # SVSTATE, MSR and PC
        self.svstate = initial_svstate
        self.msr = SelectableInt(initial_msr, 64)  # underlying reg
        self.pc = PC()
        # GPR FPR SPR registers
        self.gpr = GPR(decoder2, self, self.svstate, regfile)
        self.fpr = GPR(decoder2, self, self.svstate, fpregfile)
        self.spr = SPR(decoder2, initial_sprs) # initialise SPRs before MMU

        # set up 4 dummy SVSHAPEs if they aren't already set up
        for i in range(4):
            sname = 'SVSHAPE%d' % i
            if sname not in self.spr:
                self.spr[sname] = SVSHAPE(0)
            else:
                # make sure it's an SVSHAPE
                val = self.spr[sname].value
                self.spr[sname] = SVSHAPE(val)
        self.last_op_svshape = False

        # "raw" memory
        self.mem = Mem(row_bytes=8, initial_mem=initial_mem)
        self.imem = Mem(row_bytes=4, initial_mem=initial_insns)
        # MMU mode, redirect underlying Mem through RADIX
        if mmu:
            self.mem = RADIX(self.mem, self)
            if icachemmu:
                self.imem = RADIX(self.imem, self)

        # TODO, needed here:
        # FPR (same as GPR except for FP nums)
        # 4.2.2 p124 FPSCR (definitely "separate" - not in SPR)
        #            note that mffs, mcrfs, mtfsf "manage" this FPSCR
        # 2.3.1 CR (and sub-fields CR0..CR6 - CR0 SO comes from XER.SO)
        #         note that mfocrf, mfcr, mtcr, mtocrf, mcrxrx "manage" CRs
        #         -- Done
        # 2.3.2 LR   (actually SPR #8) -- Done
        # 2.3.3 CTR  (actually SPR #9) -- Done
        # 2.3.4 TAR  (actually SPR #815)
        # 3.2.2 p45 XER  (actually SPR #1) -- Done
        # 3.2.3 p46 p232 VRSAVE (actually SPR #256)

        # create CR then allow portions of it to be "selectable" (below)
        self.cr_fields = CRFields(initial_cr)
        self.cr = self.cr_fields.cr

        # "undefined", just set to variable-bit-width int (use exts "max")
        #self.undefined = SelectableInt(0, 256)  # TODO, not hard-code 256!

        self.namespace = {}
        self.namespace.update(self.spr)
        self.namespace.update({'GPR': self.gpr,
                               'FPR': self.fpr,
                               'MEM': self.mem,
                               'SPR': self.spr,
                               'memassign': self.memassign,
                               'NIA': self.pc.NIA,
                               'CIA': self.pc.CIA,
                               'SVSTATE': self.svstate.spr,
                               'SVSHAPE0': self.spr['SVSHAPE0'],
                               'SVSHAPE1': self.spr['SVSHAPE1'],
                               'SVSHAPE2': self.spr['SVSHAPE2'],
                               'SVSHAPE3': self.spr['SVSHAPE3'],
                               'CR': self.cr,
                               'MSR': self.msr,
                               'undefined': undefined,
                               'mode_is_64bit': True,
                               'SO': XER_bits['SO']
                               })

        # update pc to requested start point
        self.set_pc(initial_pc)

        # field-selectable versions of Condition Register
        self.crl = self.cr_fields.crl
        for i in range(8):
            self.namespace["CR%d" % i] = self.crl[i]

        self.decoder = decoder2.dec
        self.dec2 = decoder2

    def call_trap(self, trap_addr, trap_bit):
        """calls TRAP and sets up NIA to the new execution location.
        next instruction will begin at trap_addr.
        """
        self.TRAP(trap_addr, trap_bit)
        self.namespace['NIA'] = self.trap_nia
        self.pc.update(self.namespace, self.is_svp64_mode)

    def TRAP(self, trap_addr=0x700, trap_bit=PIb.TRAP):
        """TRAP> saves PC, MSR (and TODO SVSTATE), and updates MSR

        TRAP function is callable from inside the pseudocode itself,
        hence the default arguments.  when calling from inside ISACaller
        it is best to use call_trap()
        """
        log("TRAP:", hex(trap_addr), hex(self.namespace['MSR'].value))
        # store CIA(+4?) in SRR0, set NIA to 0x700
        # store MSR in SRR1, set MSR to um errr something, have to check spec
        # store SVSTATE (if enabled) in SVSRR0
        self.spr['SRR0'].value = self.pc.CIA.value
        self.spr['SRR1'].value = self.namespace['MSR'].value
        if self.is_svp64_mode:
            self.spr['SVSRR0'] = self.namespace['SVSTATE'].value
        self.trap_nia = SelectableInt(trap_addr, 64)
        self.spr['SRR1'][trap_bit] = 1  # change *copy* of MSR in SRR1

        # set exception bits.  TODO: this should, based on the address
        # in figure 66 p1065 V3.0B and the table figure 65 p1063 set these
        # bits appropriately.  however it turns out that *for now* in all
        # cases (all trap_addrs) the exact same thing is needed.
        self.msr[MSRb.IR] = 0
        self.msr[MSRb.DR] = 0
        self.msr[MSRb.FE0] = 0
        self.msr[MSRb.FE1] = 0
        self.msr[MSRb.EE] = 0
        self.msr[MSRb.RI] = 0
        self.msr[MSRb.SF] = 1
        self.msr[MSRb.TM] = 0
        self.msr[MSRb.VEC] = 0
        self.msr[MSRb.VSX] = 0
        self.msr[MSRb.PR] = 0
        self.msr[MSRb.FP] = 0
        self.msr[MSRb.PMM] = 0
        self.msr[MSRb.TEs] = 0
        self.msr[MSRb.TEe] = 0
        self.msr[MSRb.UND] = 0
        self.msr[MSRb.LE] = 1

    def memassign(self, ea, sz, val):
        self.mem.memassign(ea, sz, val)

    def prep_namespace(self, formname, op_fields):
        # TODO: get field names from form in decoder*1* (not decoder2)
        # decoder2 is hand-created, and decoder1.sigform is auto-generated
        # from spec
        # then "yield" fields only from op_fields rather than hard-coded
        # list, here.
        fields = self.decoder.sigforms[formname]
        for name in op_fields:
            if name == 'spr':
                sig = getattr(fields, name.upper())
            else:
                sig = getattr(fields, name)
            val = yield sig
            # these are all opcode fields involved in index-selection of CR,
            # and need to do "standard" arithmetic.  CR[BA+32] for example
            # would, if using SelectableInt, only be 5-bit.
            if name in ['BF', 'BFA', 'BC', 'BA', 'BB', 'BT', 'BI']:
                self.namespace[name] = val
            else:
                self.namespace[name] = SelectableInt(val, sig.width)

        self.namespace['XER'] = self.spr['XER']
        self.namespace['CA'] = self.spr['XER'][XER_bits['CA']].value
        self.namespace['CA32'] = self.spr['XER'][XER_bits['CA32']].value

        # add some SVSTATE convenience variables
        vl = self.svstate.vl.asint(msb0=True)
        srcstep = self.svstate.srcstep.asint(msb0=True)
        self.namespace['VL'] = vl
        self.namespace['srcstep'] = srcstep

    def handle_carry_(self, inputs, outputs, already_done):
        inv_a = yield self.dec2.e.do.invert_in
        if inv_a:
            inputs[0] = ~inputs[0]

        imm_ok = yield self.dec2.e.do.imm_data.ok
        if imm_ok:
            imm = yield self.dec2.e.do.imm_data.data
            inputs.append(SelectableInt(imm, 64))
        assert len(outputs) >= 1
        log("outputs", repr(outputs))
        if isinstance(outputs, list) or isinstance(outputs, tuple):
            output = outputs[0]
        else:
            output = outputs
        gts = []
        for x in inputs:
            log("gt input", x, output)
            gt = (gtu(x, output))
            gts.append(gt)
        log(gts)
        cy = 1 if any(gts) else 0
        log("CA", cy, gts)
        if not (1 & already_done):
            self.spr['XER'][XER_bits['CA']] = cy

        log("inputs", already_done, inputs)
        # 32 bit carry
        # ARGH... different for OP_ADD... *sigh*...
        op = yield self.dec2.e.do.insn_type
        if op == MicrOp.OP_ADD.value:
            res32 = (output.value & (1 << 32)) != 0
            a32 = (inputs[0].value & (1 << 32)) != 0
            if len(inputs) >= 2:
                b32 = (inputs[1].value & (1 << 32)) != 0
            else:
                b32 = False
            cy32 = res32 ^ a32 ^ b32
            log("CA32 ADD", cy32)
        else:
            gts = []
            for x in inputs:
                log("input", x, output)
                log("     x[32:64]", x, x[32:64])
                log("     o[32:64]", output, output[32:64])
                gt = (gtu(x[32:64], output[32:64])) == SelectableInt(1, 1)
                gts.append(gt)
            cy32 = 1 if any(gts) else 0
            log("CA32", cy32, gts)
        if not (2 & already_done):
            self.spr['XER'][XER_bits['CA32']] = cy32

    def handle_overflow(self, inputs, outputs, div_overflow):
        if hasattr(self.dec2.e.do, "invert_in"):
            inv_a = yield self.dec2.e.do.invert_in
            if inv_a:
                inputs[0] = ~inputs[0]

        imm_ok = yield self.dec2.e.do.imm_data.ok
        if imm_ok:
            imm = yield self.dec2.e.do.imm_data.data
            inputs.append(SelectableInt(imm, 64))
        assert len(outputs) >= 1
        log("handle_overflow", inputs, outputs, div_overflow)
        if len(inputs) < 2 and div_overflow is None:
            return

        # div overflow is different: it's returned by the pseudo-code
        # because it's more complex than can be done by analysing the output
        if div_overflow is not None:
            ov, ov32 = div_overflow, div_overflow
        # arithmetic overflow can be done by analysing the input and output
        elif len(inputs) >= 2:
            output = outputs[0]

            # OV (64-bit)
            input_sgn = [exts(x.value, x.bits) < 0 for x in inputs]
            output_sgn = exts(output.value, output.bits) < 0
            ov = 1 if input_sgn[0] == input_sgn[1] and \
                output_sgn != input_sgn[0] else 0

            # OV (32-bit)
            input32_sgn = [exts(x.value, 32) < 0 for x in inputs]
            output32_sgn = exts(output.value, 32) < 0
            ov32 = 1 if input32_sgn[0] == input32_sgn[1] and \
                output32_sgn != input32_sgn[0] else 0

        self.spr['XER'][XER_bits['OV']] = ov
        self.spr['XER'][XER_bits['OV32']] = ov32
        so = self.spr['XER'][XER_bits['SO']]
        so = so | ov
        self.spr['XER'][XER_bits['SO']] = so

    def handle_comparison(self, outputs, cr_idx=0):
        out = outputs[0]
        assert isinstance(out, SelectableInt), \
            "out zero not a SelectableInt %s" % repr(outputs)
        log("handle_comparison", out.bits, hex(out.value))
        # TODO - XXX *processor* in 32-bit mode
        # https://bugs.libre-soc.org/show_bug.cgi?id=424
        # if is_32bit:
        #    o32 = exts(out.value, 32)
        #    print ("handle_comparison exts 32 bit", hex(o32))
        out = exts(out.value, out.bits)
        log("handle_comparison exts", hex(out))
        zero = SelectableInt(out == 0, 1)
        positive = SelectableInt(out > 0, 1)
        negative = SelectableInt(out < 0, 1)
        SO = self.spr['XER'][XER_bits['SO']]
        log("handle_comparison SO", SO)
        cr_field = selectconcat(negative, positive, zero, SO)
        self.crl[cr_idx].eq(cr_field)

    def set_pc(self, pc_val):
        self.namespace['NIA'] = SelectableInt(pc_val, 64)
        self.pc.update(self.namespace, self.is_svp64_mode)

    def get_next_insn(self):
        """check instruction
        """
        if self.respect_pc:
            pc = self.pc.CIA.value
        else:
            pc = self.fake_pc
        ins = self.imem.ld(pc, 4, False, True, instr_fetch=True)
        if ins is None:
            raise KeyError("no instruction at 0x%x" % pc)
        return pc, ins

    def setup_one(self):
        """set up one instruction
        """
        pc, insn = self.get_next_insn()
        yield from self.setup_next_insn(pc, insn)

    def setup_next_insn(self, pc, ins):
        """set up next instruction
        """
        self._pc = pc
        log("setup: 0x%x 0x%x %s" % (pc, ins & 0xffffffff, bin(ins)))
        log("CIA NIA", self.respect_pc, self.pc.CIA.value, self.pc.NIA.value)

        yield self.dec2.sv_rm.eq(0)
        yield self.dec2.dec.raw_opcode_in.eq(ins & 0xffffffff)
        yield self.dec2.dec.bigendian.eq(self.bigendian)
        yield self.dec2.state.msr.eq(self.msr.value)
        yield self.dec2.state.pc.eq(pc)
        if self.svstate is not None:
            yield self.dec2.state.svstate.eq(self.svstate.spr.value)

        # SVP64.  first, check if the opcode is EXT001, and SVP64 id bits set
        yield Settle()
        opcode = yield self.dec2.dec.opcode_in
        pfx = SVP64PrefixFields() # TODO should probably use SVP64PrefixDecoder
        pfx.insn.value = opcode
        major = pfx.major.asint(msb0=True) # MSB0 inversion
        log ("prefix test: opcode:", major, bin(major),
                pfx.insn[7] == 0b1, pfx.insn[9] == 0b1)
        self.is_svp64_mode = ((major == 0b000001) and
                              pfx.insn[7].value == 0b1 and
                              pfx.insn[9].value == 0b1)
        self.pc.update_nia(self.is_svp64_mode)
        yield self.dec2.is_svp64_mode.eq(self.is_svp64_mode) # set SVP64 decode
        self.namespace['NIA'] = self.pc.NIA
        self.namespace['SVSTATE'] = self.svstate.spr
        if not self.is_svp64_mode:
            return

        # in SVP64 mode.  decode/print out svp64 prefix, get v3.0B instruction
        log ("svp64.rm", bin(pfx.rm.asint(msb0=True)))
        log ("    svstate.vl", self.svstate.vl.asint(msb0=True))
        log ("    svstate.mvl", self.svstate.maxvl.asint(msb0=True))
        sv_rm = pfx.rm.asint(msb0=True)
        ins = self.imem.ld(pc+4, 4, False, True, instr_fetch=True)
        log("     svsetup: 0x%x 0x%x %s" % (pc+4, ins & 0xffffffff, bin(ins)))
        yield self.dec2.dec.raw_opcode_in.eq(ins & 0xffffffff) # v3.0B suffix
        yield self.dec2.sv_rm.eq(sv_rm)                        # svp64 prefix
        yield Settle()

    def execute_one(self):
        """execute one instruction
        """
        # get the disassembly code for this instruction
        if self.is_svp64_mode:
            if not self.disassembly:
                code = yield from self.get_assembly_name()
            else:
                code = self.disassembly[self._pc+4]
            log("    svp64 sim-execute", hex(self._pc), code)
        else:
            if not self.disassembly:
                code = yield from self.get_assembly_name()
            else:
                code = self.disassembly[self._pc]
            log("sim-execute", hex(self._pc), code)
        opname = code.split(' ')[0]
        try:
            yield from self.call(opname)         # execute the instruction
        except MemException as e:                # check for memory errors
            if e.args[0] != 'unaligned':         # only doing aligned at the mo
                raise e                          # ... re-raise
            # run a Trap but set DAR first
            print ("memory unaligned exception, DAR", e.dar)
            self.spr['DAR'] = SelectableInt(e.dar, 64)
            self.call_trap(0x600, PIb.PRIV)                # 0x600, privileged
            return

        # don't use this except in special circumstances
        if not self.respect_pc:
            self.fake_pc += 4

        log("execute one, CIA NIA", self.pc.CIA.value, self.pc.NIA.value)

    def get_assembly_name(self):
        # TODO, asmregs is from the spec, e.g. add RT,RA,RB
        # see http://bugs.libre-riscv.org/show_bug.cgi?id=282
        dec_insn = yield self.dec2.e.do.insn
        insn_1_11 = yield self.dec2.e.do.insn[1:11]
        asmcode = yield self.dec2.dec.op.asmcode
        int_op = yield self.dec2.dec.op.internal_op
        log("get assembly name asmcode", asmcode, int_op,
                            hex(dec_insn), bin(insn_1_11))
        asmop = insns.get(asmcode, None)

        # sigh reconstruct the assembly instruction name
        if hasattr(self.dec2.e.do, "oe"):
            ov_en = yield self.dec2.e.do.oe.oe
            ov_ok = yield self.dec2.e.do.oe.ok
        else:
            ov_en = False
            ov_ok = False
        if hasattr(self.dec2.e.do, "rc"):
            rc_en = yield self.dec2.e.do.rc.rc
            rc_ok = yield self.dec2.e.do.rc.ok
        else:
            rc_en = False
            rc_ok = False
        # grrrr have to special-case MUL op (see DecodeOE)
        log("ov %d en %d rc %d en %d op %d" %
              (ov_ok, ov_en, rc_ok, rc_en, int_op))
        if int_op in [MicrOp.OP_MUL_H64.value, MicrOp.OP_MUL_H32.value]:
            log("mul op")
            if rc_en & rc_ok:
                asmop += "."
        else:
            if not asmop.endswith("."):  # don't add "." to "andis."
                if rc_en & rc_ok:
                    asmop += "."
        if hasattr(self.dec2.e.do, "lk"):
            lk = yield self.dec2.e.do.lk
            if lk:
                asmop += "l"
        log("int_op", int_op)
        if int_op in [MicrOp.OP_B.value, MicrOp.OP_BC.value]:
            AA = yield self.dec2.dec.fields.FormI.AA[0:-1]
            log("AA", AA)
            if AA:
                asmop += "a"
        spr_msb = yield from self.get_spr_msb()
        if int_op == MicrOp.OP_MFCR.value:
            if spr_msb:
                asmop = 'mfocrf'
            else:
                asmop = 'mfcr'
        # XXX TODO: for whatever weird reason this doesn't work
        # https://bugs.libre-soc.org/show_bug.cgi?id=390
        if int_op == MicrOp.OP_MTCRF.value:
            if spr_msb:
                asmop = 'mtocrf'
            else:
                asmop = 'mtcrf'
        return asmop

    def get_spr_msb(self):
        dec_insn = yield self.dec2.e.do.insn
        return dec_insn & (1 << 20) != 0  # sigh - XFF.spr[-1]?

    def call(self, name):
        """call(opcode) - the primary execution point for instructions
        """
        self.last_st_addr = None # reset the last known store address
        self.last_ld_addr = None # etc.

        name = name.strip()  # remove spaces if not already done so
        if self.halted:
            log("halted - not executing", name)
            return

        # TODO, asmregs is from the spec, e.g. add RT,RA,RB
        # see http://bugs.libre-riscv.org/show_bug.cgi?id=282
        asmop = yield from self.get_assembly_name()
        log("call", name, asmop)

        # check privileged
        int_op = yield self.dec2.dec.op.internal_op
        spr_msb = yield from self.get_spr_msb()

        instr_is_privileged = False
        if int_op in [MicrOp.OP_ATTN.value,
                      MicrOp.OP_MFMSR.value,
                      MicrOp.OP_MTMSR.value,
                      MicrOp.OP_MTMSRD.value,
                      # TODO: OP_TLBIE
                      MicrOp.OP_RFID.value]:
            instr_is_privileged = True
        if int_op in [MicrOp.OP_MFSPR.value,
                      MicrOp.OP_MTSPR.value] and spr_msb:
            instr_is_privileged = True

        log("is priv", instr_is_privileged, hex(self.msr.value),
              self.msr[MSRb.PR])
        # check MSR priv bit and whether op is privileged: if so, throw trap
        if instr_is_privileged and self.msr[MSRb.PR] == 1:
            self.call_trap(0x700, PIb.PRIV)
            return

        # check halted condition
        if name == 'attn':
            self.halted = True
            return

        # check illegal instruction
        illegal = False
        if name not in ['mtcrf', 'mtocrf']:
            illegal = name != asmop

        # sigh deal with setvl not being supported by binutils (.long)
        if asmop.startswith('setvl'):
            illegal = False
            name = 'setvl'

        # and svshape not being supported by binutils (.long)
        if asmop.startswith('svshape'):
            illegal = False
            name = 'svshape'

        # sigh also deal with ffmadds not being supported by binutils (.long)
        if asmop == 'ffmadds':
            illegal = False
            name = 'ffmadds'

        # and ffadds not being supported by binutils (.long)
        if asmop == 'ffadds':
            illegal = False
            name = 'ffadds'

        if illegal:
            print("illegal", name, asmop)
            self.call_trap(0x700, PIb.ILLEG)
            print("name %s != %s - calling ILLEGAL trap, PC: %x" %
                  (name, asmop, self.pc.CIA.value))
            return

        # this is for setvl "Vertical" mode: if set true,
        # srcstep/dststep is explicitly advanced
        self.allow_next_step_inc = False

        # nop has to be supported, we could let the actual op calculate
        # but PowerDecoder has a pattern for nop
        if name is 'nop':
            self.update_pc_next()
            return

        info = self.instrs[name]
        yield from self.prep_namespace(info.form, info.op_fields)

        # preserve order of register names
        input_names = create_args(list(info.read_regs) +
                                  list(info.uninit_regs))
        log(input_names)

        # get SVP64 entry for the current instruction
        sv_rm = self.svp64rm.instrs.get(name)
        if sv_rm is not None:
            dest_cr, src_cr, src_byname, dest_byname = decode_extra(sv_rm)
        else:
            dest_cr, src_cr, src_byname, dest_byname = False, False, {}, {}
        log ("sv rm", sv_rm, dest_cr, src_cr, src_byname, dest_byname)

        # see if srcstep/dststep need skipping over masked-out predicate bits
        if self.is_svp64_mode:
            yield from self.svstate_pre_inc()
            pre = yield from self.update_new_svstate_steps()
            if pre:
                self.svp64_reset_loop()
                self.update_nia()
                self.update_pc_next()
                return
            srcstep, dststep = self.new_srcstep, self.new_dststep
            pred_dst_zero = self.pred_dst_zero
            pred_src_zero = self.pred_src_zero
            vl = self.svstate.vl.asint(msb0=True)

        # VL=0 in SVP64 mode means "do nothing: skip instruction"
        if self.is_svp64_mode and vl == 0:
            self.pc.update(self.namespace, self.is_svp64_mode)
            log("SVP64: VL=0, end of call", self.namespace['CIA'],
                                       self.namespace['NIA'])
            return

        # for when SVSHAPE is active, a very bad hack here (to be replaced)
        # using pre-arranged schedule.  all of this is awful but it is a
        # start.  next job will be to put the proper activation in place
        yield self.dec2.remap_active.eq(1 if self.last_op_svshape else 0)
        yield Settle()
        if self.is_svp64_mode and self.last_op_svshape:
            # get four SVSHAPEs. here we are hard-coding
            # SVSHAPE0 to FRT, SVSHAPE1 to FRA, SVSHAPE2 to FRC and
            # SVSHAPE3 to FRB, assuming "fmadd FRT, FRA, FRC, FRB."
            SVSHAPE0 = self.spr['SVSHAPE0']
            SVSHAPE1 = self.spr['SVSHAPE1']
            SVSHAPE2 = self.spr['SVSHAPE2']
            SVSHAPE3 = self.spr['SVSHAPE3']
            for i in range(4):
                sname = 'SVSHAPE%d' % i
                shape = self.spr[sname]
                print (sname, bin(shape.value))
                print ("    lims", shape.lims)
                print ("    mode", shape.mode)
                print ("    skip", shape.skip)

            remaps = [(SVSHAPE0, SVSHAPE0.get_iterator()),
                      (SVSHAPE1, SVSHAPE1.get_iterator()),
                      (SVSHAPE2, SVSHAPE2.get_iterator()),
                      (SVSHAPE3, SVSHAPE3.get_iterator()),
                     ]
            rremaps = []
            for i, (shape, remap) in enumerate(remaps):
                # zero is "disabled"
                if shape.value == 0x0:
                    continue
                # XXX hardcoded! pick dststep for out (i==0) else srcstep
                if shape.mode == 0b00: # multiply mode
                    step = dststep if (i == 0) else srcstep
                if shape.mode == 0b01: # FFT butterfly mode
                    step = srcstep # XXX HACK - for now only use srcstep
                # this is terrible.  O(N^2) looking for the match. but hey.
                for idx, remap_idx in enumerate(remap):
                    if idx == step:
                        break
                # multiply mode
                if shape.mode == 0b00:
                    if i == 0:
                        yield self.dec2.o_step.eq(remap_idx)   # RT
                        yield self.dec2.o2_step.eq(remap_idx)  # EA
                    elif i == 1:
                        yield self.dec2.in1_step.eq(remap_idx) # RA
                    elif i == 2:
                        yield self.dec2.in3_step.eq(remap_idx) # RB
                    elif i == 3:
                        yield self.dec2.in2_step.eq(remap_idx) # RC
                # FFT butterfly mode
                if shape.mode == 0b01:
                    if i == 0:
                        yield self.dec2.o_step.eq(remap_idx)   # RT
                        yield self.dec2.in2_step.eq(remap_idx) # RB
                    elif i == 1:
                        yield self.dec2.in1_step.eq(remap_idx) # RA
                        yield self.dec2.o2_step.eq(remap_idx)  # EA (FRS)
                    elif i == 2:
                        yield self.dec2.in3_step.eq(remap_idx) # RC
                    elif i == 3:
                        pass # no SVSHAPE3
                rremaps.append((shape.mode, i, idx, remap_idx)) # debug printing
            for x in rremaps:
                print ("shape remap", x)
        # after that, settle down (combinatorial) to let Vector reg numbers
        # work themselves out
        yield Settle()
        remap_active = yield self.dec2.remap_active
        print ("remap active", remap_active)

        # main input registers (RT, RA ...)
        inputs = []
        for name in input_names:
            # using PowerDecoder2, first, find the decoder index.
            # (mapping name RA RB RC RS to in1, in2, in3)
            regnum, is_vec = yield from get_pdecode_idx_in(self.dec2, name)
            if regnum is None:
                # doing this is not part of svp64, it's because output
                # registers, to be modified, need to be in the namespace.
                regnum, is_vec = yield from get_pdecode_idx_out(self.dec2, name)
            if regnum is None:
                regnum, is_vec = yield from get_pdecode_idx_out2(self.dec2,
                                                                 name)

            # in case getting the register number is needed, _RA, _RB
            regname = "_" + name
            self.namespace[regname] = regnum
            if not self.is_svp64_mode or not pred_src_zero:
                log('reading reg %s %s' % (name, str(regnum)), is_vec)
                if name in fregs:
                    reg_val = self.fpr(regnum)
                elif name is not None:
                    reg_val = self.gpr(regnum)
            else:
                log('zero input reg %s %s' % (name, str(regnum)), is_vec)
                reg_val = 0
            inputs.append(reg_val)
        # arrrrgh, awful hack, to get _RT into namespace
        if asmop == 'setvl':
            regname = "_RT"
            RT = yield self.dec2.dec.RT
            self.namespace[regname] = SelectableInt(RT, 5)

        # in SVP64 mode for LD/ST work out immediate
        # XXX TODO: replace_ds for DS-Form rather than D-Form.
        # use info.form to detect
        replace_d = False # update / replace constant in pseudocode
        if self.is_svp64_mode:
            ldstmode = yield self.dec2.rm_dec.ldstmode
            # bitreverse mode reads SVD (or SVDS - TODO)
            # *BUT*... because this is "overloading" of LD operations,
            # it gets *STORED* into D (or DS, TODO)
            if ldstmode == SVP64LDSTmode.BITREVERSE.value:
                imm = yield self.dec2.dec.fields.FormSVD.SVD[0:11]
                imm = exts(imm, 11) # sign-extend to integer
                print ("bitrev SVD", imm)
                replace_d = True
            else:
                imm = yield self.dec2.dec.fields.FormD.D[0:16]
                imm = exts(imm, 16) # sign-extend to integer
            # get the right step. LD is from srcstep, ST is dststep
            op = yield self.dec2.e.do.insn_type
            offsmul = 0
            if op == MicrOp.OP_LOAD.value:
                offsmul = srcstep
                log("D-field src", imm, offsmul)
            elif op == MicrOp.OP_STORE.value:
                offsmul = dststep
                log("D-field dst", imm, offsmul)
            # bit-reverse mode
            if ldstmode == SVP64LDSTmode.BITREVERSE.value:
                # manually look up RC, sigh
                RC = yield self.dec2.dec.RC[0:5]
                RC = self.gpr(RC)
                log ("RC", RC.value, "imm", imm, "offs", bin(offsmul),
                     "rev", bin(bitrev(offsmul, vl)))
                imm = SelectableInt((imm * bitrev(offsmul, vl)) << RC.value, 32)
            # Unit-Strided LD/ST adds offset*width to immediate
            elif ldstmode == SVP64LDSTmode.UNITSTRIDE.value:
                ldst_len = yield self.dec2.e.do.data_len
                imm = SelectableInt(imm + offsmul * ldst_len, 32)
                replace_d = True
            # Element-strided multiplies the immediate by element step
            elif ldstmode == SVP64LDSTmode.ELSTRIDE.value:
                imm = SelectableInt(imm * offsmul, 32)
                replace_d = True
            ldst_ra_vec = yield self.dec2.rm_dec.ldst_ra_vec
            ldst_imz_in = yield self.dec2.rm_dec.ldst_imz_in
            log("LDSTmode", ldstmode, SVP64LDSTmode.BITREVERSE.value,
                            offsmul, imm, ldst_ra_vec, ldst_imz_in)
        # new replacement D
        if replace_d:
            self.namespace['D'] = imm

        # "special" registers
        for special in info.special_regs:
            if special in special_sprs:
                inputs.append(self.spr[special])
            else:
                inputs.append(self.namespace[special])

        # clear trap (trap) NIA
        self.trap_nia = None

        # execute actual instruction here (finally)
        log("inputs", inputs)
        results = info.func(self, *inputs)
        log("results", results)

        # "inject" decorator takes namespace from function locals: we need to
        # overwrite NIA being overwritten (sigh)
        if self.trap_nia is not None:
            self.namespace['NIA'] = self.trap_nia

        log("after func", self.namespace['CIA'], self.namespace['NIA'])

        # check if op was a LD/ST so that debugging can check the
        # address
        if int_op in [MicrOp.OP_STORE.value,
                     ]:
            self.last_st_addr = self.mem.last_st_addr
        if int_op in [MicrOp.OP_LOAD.value,
                     ]:
            self.last_ld_addr = self.mem.last_ld_addr
        log ("op", int_op, MicrOp.OP_STORE.value, MicrOp.OP_LOAD.value,
                   self.last_st_addr, self.last_ld_addr)

        # detect if CA/CA32 already in outputs (sra*, basically)
        already_done = 0
        if info.write_regs:
            output_names = create_args(info.write_regs)
            for name in output_names:
                if name == 'CA':
                    already_done |= 1
                if name == 'CA32':
                    already_done |= 2

        log("carry already done?", bin(already_done))
        if hasattr(self.dec2.e.do, "output_carry"):
            carry_en = yield self.dec2.e.do.output_carry
        else:
            carry_en = False
        if carry_en:
            yield from self.handle_carry_(inputs, results, already_done)

        if not self.is_svp64_mode: # yeah just no. not in parallel processing
            # detect if overflow was in return result
            overflow = None
            if info.write_regs:
                for name, output in zip(output_names, results):
                    if name == 'overflow':
                        overflow = output

            if hasattr(self.dec2.e.do, "oe"):
                ov_en = yield self.dec2.e.do.oe.oe
                ov_ok = yield self.dec2.e.do.oe.ok
            else:
                ov_en = False
                ov_ok = False
            log("internal overflow", overflow, ov_en, ov_ok)
            if ov_en & ov_ok:
                yield from self.handle_overflow(inputs, results, overflow)

        # only do SVP64 dest predicated Rc=1 if dest-pred is not enabled
        rc_en = False
        if not self.is_svp64_mode or not pred_dst_zero:
            if hasattr(self.dec2.e.do, "rc"):
                rc_en = yield self.dec2.e.do.rc.rc
        if rc_en:
            regnum, is_vec = yield from get_pdecode_cr_out(self.dec2, "CR0")
            self.handle_comparison(results, regnum)

        # any modified return results?
        if info.write_regs:
            for name, output in zip(output_names, results):
                if name == 'overflow':  # ignore, done already (above)
                    continue
                if isinstance(output, int):
                    output = SelectableInt(output, 256)
                if name in ['CA', 'CA32']:
                    if carry_en:
                        log("writing %s to XER" % name, output)
                        self.spr['XER'][XER_bits[name]] = output.value
                    else:
                        log("NOT writing %s to XER" % name, output)
                elif name in info.special_regs:
                    log('writing special %s' % name, output, special_sprs)
                    if name in special_sprs:
                        self.spr[name] = output
                    else:
                        self.namespace[name].eq(output)
                    if name == 'MSR':
                        log('msr written', hex(self.msr.value))
                else:
                    regnum, is_vec = yield from get_pdecode_idx_out(self.dec2,
                                                name)
                    if regnum is None:
                        regnum, is_vec = yield from get_pdecode_idx_out2(
                                                    self.dec2, name)
                    if regnum is None:
                        # temporary hack for not having 2nd output
                        regnum = yield getattr(self.decoder, name)
                        is_vec = False
                    if self.is_svp64_mode and pred_dst_zero:
                        log('zeroing reg %d %s' % (regnum, str(output)),
                                                     is_vec)
                        output = SelectableInt(0, 256)
                    else:
                        if name in fregs:
                            ftype = 'fpr'
                        else:
                            ftype = 'gpr'
                        log('writing %s %s %s' % (regnum, ftype, str(output)),
                                                     is_vec)
                    if output.bits > 64:
                        output = SelectableInt(output.value, 64)
                    if name in fregs:
                        self.fpr[regnum] = output
                    else:
                        self.gpr[regnum] = output

        # check if it is the SVSTATE.src/dest step that needs incrementing
        # this is our Sub-Program-Counter loop from 0 to VL-1
        pre = False
        post = False
        if self.allow_next_step_inc:
            log("SVSTATE_NEXT: inc requested")
            yield from self.svstate_pre_inc()
            pre = yield from self.update_new_svstate_steps()
            if pre:
                # reset at end of loop including exit Vertical Mode
                log ("SVSTATE_NEXT: end of loop, reset")
                self.svp64_reset_loop()
                self.msr[MSRb.SVF] = 0
                self.update_nia()
                if rc_en:
                    results = [SelectableInt(0, 64)]
                    self.handle_comparison(results) # CR0
            else:
                log ("SVSTATE_NEXT: post-inc")
                srcstep, dststep = self.new_srcstep, self.new_dststep
                vl = self.svstate.vl.asint(msb0=True)
                end_src = srcstep == vl-1
                end_dst = dststep == vl-1
                if not end_src:
                    self.svstate.srcstep += SelectableInt(1, 7)
                if not end_dst:
                    self.svstate.dststep += SelectableInt(1, 7)
                self.namespace['SVSTATE'] = self.svstate.spr
                # set CR0 (if Rc=1) based on end
                if rc_en:
                    srcstep = self.svstate.srcstep.asint(msb0=True)
                    dststep = self.svstate.srcstep.asint(msb0=True)
                    endtest = 0 if (end_src or end_dst) else 1
                    results = [SelectableInt(endtest, 64)]
                    self.handle_comparison(results) # CR0
                if end_src or end_dst:
                    # reset at end of loop including exit Vertical Mode
                    log ("SVSTATE_NEXT: after increments, reset")
                    self.svp64_reset_loop()
                    self.msr[MSRb.SVF] = 0

        elif self.is_svp64_mode:
            yield from self.svstate_post_inc()
        else:
            # XXX only in non-SVP64 mode!
            # record state of whether the current operation was an svshape,
            # to be able to know if it should apply in the next instruction.
            # also (if going to use this instruction) should disable ability
            # to interrupt in between. sigh.
            self.last_op_svshape = asmop == 'svshape'

        self.update_pc_next()

    def SVSTATE_NEXT(self):
        """explicitly moves srcstep/dststep on to next element, for
        "Vertical-First" mode.  this function is called from
        setvl pseudo-code, as a pseudo-op "svstep"
        """
        log("SVSTATE_NEXT")
        self.allow_next_step_inc = True

    def svstate_pre_inc(self):
        """check if srcstep/dststep need to skip over masked-out predicate bits
        """
        # get SVSTATE VL (oh and print out some debug stuff)
        vl = self.svstate.vl.asint(msb0=True)
        srcstep = self.svstate.srcstep.asint(msb0=True)
        dststep = self.svstate.dststep.asint(msb0=True)
        sv_a_nz = yield self.dec2.sv_a_nz
        fft_mode = yield self.dec2.use_svp64_fft
        in1 = yield self.dec2.e.read_reg1.data
        log ("SVP64: VL, srcstep, dststep, sv_a_nz, in1 fft",
                vl, srcstep, dststep, sv_a_nz, in1, fft_mode)

        # get predicate mask
        srcmask = dstmask = 0xffff_ffff_ffff_ffff

        pmode = yield self.dec2.rm_dec.predmode
        reverse_gear = yield self.dec2.rm_dec.reverse_gear
        sv_ptype = yield self.dec2.dec.op.SV_Ptype
        srcpred = yield self.dec2.rm_dec.srcpred
        dstpred = yield self.dec2.rm_dec.dstpred
        pred_src_zero = yield self.dec2.rm_dec.pred_sz
        pred_dst_zero = yield self.dec2.rm_dec.pred_dz
        if pmode == SVP64PredMode.INT.value:
            srcmask = dstmask = get_predint(self.gpr, dstpred)
            if sv_ptype == SVPtype.P2.value:
                srcmask = get_predint(self.gpr, srcpred)
        elif pmode == SVP64PredMode.CR.value:
            srcmask = dstmask = get_predcr(self.crl, dstpred, vl)
            if sv_ptype == SVPtype.P2.value:
                srcmask = get_predcr(self.crl, srcpred, vl)
        log ("    pmode", pmode)
        log ("    reverse", reverse_gear)
        log ("    ptype", sv_ptype)
        log ("    srcpred", bin(srcpred))
        log ("    dstpred", bin(dstpred))
        log ("    srcmask", bin(srcmask))
        log ("    dstmask", bin(dstmask))
        log ("    pred_sz", bin(pred_src_zero))
        log ("    pred_dz", bin(pred_dst_zero))

        # okaaay, so here we simply advance srcstep (TODO dststep)
        # until the predicate mask has a "1" bit... or we run out of VL
        # let srcstep==VL be the indicator to move to next instruction
        if not pred_src_zero:
            while (((1<<srcstep) & srcmask) == 0) and (srcstep != vl):
                log ("      skip", bin(1<<srcstep))
                srcstep += 1
        # same for dststep
        if not pred_dst_zero:
            while (((1<<dststep) & dstmask) == 0) and (dststep != vl):
                log ("      skip", bin(1<<dststep))
                dststep += 1

        # now work out if the relevant mask bits require zeroing
        if pred_dst_zero:
            pred_dst_zero = ((1<<dststep) & dstmask) == 0
        if pred_src_zero:
            pred_src_zero = ((1<<srcstep) & srcmask) == 0

        # store new srcstep / dststep
        self.new_srcstep, self.new_dststep = srcstep, dststep
        self.pred_dst_zero, self.pred_src_zero = pred_dst_zero, pred_src_zero
        log ("    new srcstep", srcstep)
        log ("    new dststep", dststep)

    def update_new_svstate_steps(self):
        srcstep, dststep = self.new_srcstep, self.new_dststep

        # update SVSTATE with new srcstep
        self.svstate.srcstep[0:7] = srcstep
        self.svstate.dststep[0:7] = dststep
        self.namespace['SVSTATE'] = self.svstate.spr
        yield self.dec2.state.svstate.eq(self.svstate.spr.value)
        yield Settle() # let decoder update
        srcstep = self.svstate.srcstep.asint(msb0=True)
        dststep = self.svstate.dststep.asint(msb0=True)
        vl = self.svstate.vl.asint(msb0=True)
        log ("    srcstep", srcstep)
        log ("    dststep", dststep)

        # check if end reached (we let srcstep overrun, above)
        # nothing needs doing (TODO zeroing): just do next instruction
        return srcstep == vl or dststep == vl

    def svstate_post_inc(self, vf=0):
        # check if SV "Vertical First" mode is enabled
        log ("    SV Vertical First", vf, self.msr[MSRb.SVF].value)
        if not vf and self.msr[MSRb.SVF].value == 1:
            self.update_nia()
            return True

        # check if it is the SVSTATE.src/dest step that needs incrementing
        # this is our Sub-Program-Counter loop from 0 to VL-1
        # XXX twin predication TODO
        vl = self.svstate.vl.asint(msb0=True)
        mvl = self.svstate.maxvl.asint(msb0=True)
        srcstep = self.svstate.srcstep.asint(msb0=True)
        dststep = self.svstate.dststep.asint(msb0=True)
        rm_mode = yield self.dec2.rm_dec.mode
        reverse_gear = yield self.dec2.rm_dec.reverse_gear
        sv_ptype = yield self.dec2.dec.op.SV_Ptype
        out_vec = not (yield self.dec2.no_out_vec)
        in_vec = not (yield self.dec2.no_in_vec)
        log ("    svstate.vl", vl)
        log ("    svstate.mvl", mvl)
        log ("    svstate.srcstep", srcstep)
        log ("    svstate.dststep", dststep)
        log ("    mode", rm_mode)
        log ("    reverse", reverse_gear)
        log ("    out_vec", out_vec)
        log ("    in_vec", in_vec)
        log ("    sv_ptype", sv_ptype, sv_ptype == SVPtype.P2.value)
        # check if srcstep needs incrementing by one, stop PC advancing
        # svp64 loop can end early if the dest is scalar for single-pred
        # but for 2-pred both src/dest have to be checked.
        # XXX this might not be true! it may just be LD/ST
        if sv_ptype == SVPtype.P2.value:
            svp64_is_vector = (out_vec or in_vec)
        else:
            svp64_is_vector = out_vec
        if svp64_is_vector and srcstep != vl-1 and dststep != vl-1:
            self.svstate.srcstep += SelectableInt(1, 7)
            self.svstate.dststep += SelectableInt(1, 7)
            self.pc.NIA.value = self.pc.CIA.value
            self.namespace['NIA'] = self.pc.NIA
            self.namespace['SVSTATE'] = self.svstate.spr
            log("end of sub-pc call", self.namespace['CIA'],
                                 self.namespace['NIA'])
            return False # DO NOT allow PC update whilst Sub-PC loop running

        # reset loop to zero and update NIA
        self.svp64_reset_loop()
        self.update_nia()

        return True

    def update_pc_next(self):
        # UPDATE program counter
        self.pc.update(self.namespace, self.is_svp64_mode)
        self.svstate.spr = self.namespace['SVSTATE']
        log("end of call", self.namespace['CIA'],
                             self.namespace['NIA'],
                             self.namespace['SVSTATE'])

    def svp64_reset_loop(self):
        self.svstate.srcstep[0:7] = 0
        self.svstate.dststep[0:7] = 0
        log ("    svstate.srcstep loop end (PC to update)")
        self.namespace['SVSTATE'] = self.svstate.spr

    def update_nia(self):
        self.pc.update_nia(self.is_svp64_mode)
        self.namespace['NIA'] = self.pc.NIA

def inject():
    """Decorator factory.

    this decorator will "inject" variables into the function's namespace,
    from the *dictionary* in self.namespace.  it therefore becomes possible
    to make it look like a whole stack of variables which would otherwise
    need "self." inserted in front of them (*and* for those variables to be
    added to the instance) "appear" in the function.

    "self.namespace['SI']" for example becomes accessible as just "SI" but
    *only* inside the function, when decorated.
    """
    def variable_injector(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            try:
                func_globals = func.__globals__  # Python 2.6+
            except AttributeError:
                func_globals = func.func_globals  # Earlier versions.

            context = args[0].namespace  # variables to be injected
            saved_values = func_globals.copy()  # Shallow copy of dict.
            func_globals.update(context)
            result = func(*args, **kwargs)
            log("globals after", func_globals['CIA'], func_globals['NIA'])
            log("args[0]", args[0].namespace['CIA'],
                  args[0].namespace['NIA'],
                  args[0].namespace['SVSTATE'])
            args[0].namespace = func_globals
            #exec (func.__code__, func_globals)

            # finally:
            #    func_globals = saved_values  # Undo changes.

            return result

        return decorator

    return variable_injector


