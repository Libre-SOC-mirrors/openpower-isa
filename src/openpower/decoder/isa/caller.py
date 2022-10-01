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

import re
from nmigen.sim import Settle, Delay
from functools import wraps
from copy import copy, deepcopy
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.selectable_int import (
    FieldSelectableInt,
    SelectableInt,
    selectconcat,
)
from openpower.decoder.power_insn import SVP64Instruction
from openpower.decoder.power_enums import (spr_dict, spr_byname, XER_bits,
                                           insns, MicrOp,
                                           In1Sel, In2Sel, In3Sel,
                                           OutSel, CRInSel, CROutSel, LDSTMode,
                                           SVP64RMMode, SVP64PredMode,
                                           SVP64PredInt, SVP64PredCR,
                                           SVP64LDSTmode, FPTRANS_INSNS)

from openpower.decoder.power_enums import SVPtype

from openpower.decoder.helpers import (exts, gtu, ltu, undefined,
                                       ISACallerHelper, ISAFPHelpers)
from openpower.consts import PIb, MSRb  # big-endian (PowerISA versions)
from openpower.consts import (SVP64MODE, SVP64MODEb,
                              SVP64CROffs,
                              )
from openpower.decoder.power_svp64 import SVP64RM, decode_extra

from openpower.decoder.isa.radixmmu import RADIX
from openpower.decoder.isa.mem import Mem, swap_order, MemException
from openpower.decoder.isa.svshape import SVSHAPE
from openpower.decoder.isa.svstate import SVP64State


from openpower.util import LogKind, log

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


# rrright.  this is here basically because the compiler pywriter returns
# results in a specific priority order.  to make sure regs match up they
# need partial sorting. sigh.
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
    "BI": 0,
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

    "overflow": 7,  # should definitely be last
    "CR0": 8,       # likewise
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
        # keys.sort()
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
        self.NIA = self.CIA + SelectableInt(4, 64)  # only true for v3.0B!

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
    r3 = gpr(3)
    r10 = gpr(10)
    r30 = gpr(30)
    log("get_predint", mask, SVP64PredInt.ALWAYS.value)
    if mask == SVP64PredInt.ALWAYS.value:
        return 0xffff_ffff_ffff_ffff  # 64 bits of 1
    if mask == SVP64PredInt.R3_UNARY.value:
        return 1 << (r3.value & 0b111111)
    if mask == SVP64PredInt.R3.value:
        return r3.value
    if mask == SVP64PredInt.R3_N.value:
        return ~r3.value
    if mask == SVP64PredInt.R10.value:
        return r10.value
    if mask == SVP64PredInt.R10_N.value:
        return ~r10.value
    if mask == SVP64PredInt.R30.value:
        return r30.value
    if mask == SVP64PredInt.R30_N.value:
        return ~r30.value


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
            mask |= (1 << i)
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
    log("get_pdecode_idx_in in1", name, in1_sel, In1Sel.RA.value,
        in1, in1_isvec)
    log("get_pdecode_idx_in in2", name, in2_sel, In2Sel.RB.value,
        in2, in2_isvec)
    log("get_pdecode_idx_in in3", name, in3_sel, In3Sel.RS.value,
        in3, in3_isvec)
    log("get_pdecode_idx_in FRS in3", name, in3_sel, In3Sel.FRS.value,
        in3, in3_isvec)
    log("get_pdecode_idx_in FRB in2", name, in2_sel, In2Sel.FRB.value,
        in2, in2_isvec)
    log("get_pdecode_idx_in FRC in3", name, in3_sel, In3Sel.FRC.value,
        in3, in3_isvec)
    # identify which regnames map to in1/2/3
    if name == 'RA' or name == 'RA_OR_ZERO':
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
        if in3_sel == In3Sel.RC.value:
            return in3, in3_isvec
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
def get_pdecode_cr_in(dec2, name):
    op = dec2.dec.op
    in_sel = yield op.cr_in
    in_bitfield = yield dec2.dec_cr_in.cr_bitfield.data
    sv_cr_in = yield op.sv_cr_in
    spec = yield dec2.crin_svdec.spec
    sv_override = yield dec2.dec_cr_in.sv_override
    # get the IN1/2/3 from the decoder (includes SVP64 remap and isvec)
    in1 = yield dec2.e.read_cr1.data
    cr_isvec = yield dec2.cr_in_isvec
    log("get_pdecode_cr_in", in_sel, CROutSel.CR0.value, in1, cr_isvec)
    log("    sv_cr_in", sv_cr_in)
    log("    cr_bf", in_bitfield)
    log("    spec", spec)
    log("    override", sv_override)
    # identify which regnames map to in / o2
    if name == 'BI':
        if in_sel == CRInSel.BI.value:
            return in1, cr_isvec
    log("get_pdecode_cr_in not found", name)
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
    log("get_pdecode_cr_out", out_sel, CROutSel.CR0.value, out, o_isvec)
    log("    sv_cr_out", sv_cr_out)
    log("    cr_bf", out_bitfield)
    log("    spec", spec)
    log("    override", sv_override)
    # identify which regnames map to out / o2
    if name == 'CR0':
        if out_sel == CROutSel.CR0.value:
            return out, o_isvec
    if name == 'CR1':  # these are not actually calculated correctly
        if out_sel == CROutSel.CR1.value:
            return out, o_isvec
    log("get_pdecode_cr_out not found", name)
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
        log("get_pdecode_idx_out", out_sel, OutSel.RA.value, out, o_isvec)
        if out_sel == OutSel.RA.value:
            return out, o_isvec
    elif name == 'RT':
        log("get_pdecode_idx_out", out_sel, OutSel.RT.value,
            OutSel.RT_OR_ZERO.value, out, o_isvec,
            dec2.dec.RT)
        if out_sel == OutSel.RT.value:
            return out, o_isvec
        if out_sel == OutSel.RT_OR_ZERO.value and out != 0:
            return out, o_isvec
    elif name == 'RT_OR_ZERO':
        log("get_pdecode_idx_out", out_sel, OutSel.RT.value,
            OutSel.RT_OR_ZERO.value, out, o_isvec,
            dec2.dec.RT)
        if out_sel == OutSel.RT_OR_ZERO.value:
            return out, o_isvec
    elif name == 'FRA':
        log("get_pdecode_idx_out", out_sel, OutSel.FRA.value, out, o_isvec)
        if out_sel == OutSel.FRA.value:
            return out, o_isvec
    elif name == 'FRT':
        log("get_pdecode_idx_out", out_sel, OutSel.FRT.value,
            OutSel.FRT.value, out, o_isvec)
        if out_sel == OutSel.FRT.value:
            return out, o_isvec
    log("get_pdecode_idx_out not found", name, out_sel, out, o_isvec)
    return None, False


# TODO, really should just be using PowerDecoder2
def get_pdecode_idx_out2(dec2, name):
    # check first if register is activated for write
    op = dec2.dec.op
    out_sel = yield op.out_sel
    out = yield dec2.e.write_ea.data
    o_isvec = yield dec2.o2_isvec
    out_ok = yield dec2.e.write_ea.ok
    log("get_pdecode_idx_out2", name, out_sel, out, out_ok, o_isvec)
    if not out_ok:
        return None, False

    if name == 'RA':
        if hasattr(op, "upd"):
            # update mode LD/ST uses read-reg A also as an output
            upd = yield op.upd
            log("get_pdecode_idx_out2", upd, LDSTMode.update.value,
                out_sel, OutSel.RA.value,
                out, o_isvec)
            if upd == LDSTMode.update.value:
                return out, o_isvec
    if name == 'RS':
        fft_en = yield dec2.implicit_rs
        if fft_en:
            log("get_pdecode_idx_out2", out_sel, OutSel.RS.value,
                out, o_isvec)
            return out, o_isvec
    if name == 'FRS':
        fft_en = yield dec2.implicit_rs
        if fft_en:
            log("get_pdecode_idx_out2", out_sel, OutSel.FRS.value,
                out, o_isvec)
            return out, o_isvec
    return None, False


class StepLoop:
    """deals with svstate looping.
    """

    def __init__(self, svstate):
        self.svstate = svstate
        self.new_iterators()

    def new_iterators(self):
        self.src_it = self.src_iterator()
        self.dst_it = self.dst_iterator()
        self.loopend = False
        self.new_srcstep = 0
        self.new_dststep = 0
        self.new_ssubstep = 0
        self.new_dsubstep = 0
        self.pred_dst_zero = 0
        self.pred_src_zero = 0
 
    def src_iterator(self):
        """source-stepping iterator
        """
        pack = self.svstate.pack

        # source step
        if pack:
            # pack advances subvl in *outer* loop
            while True:  # outer subvl loop
                while True:  # inner vl loop
                    vl = self.svstate.vl
                    subvl = self.subvl
                    srcmask = self.srcmask
                    srcstep = self.svstate.srcstep
                    pred_src_zero = ((1 << srcstep) & srcmask) != 0
                    if self.pred_sz or pred_src_zero:
                        self.pred_src_zero = not pred_src_zero
                        log("    advance src", srcstep, vl,
                            self.svstate.ssubstep, subvl)
                        # yield actual substep/srcstep
                        yield (self.svstate.ssubstep, srcstep)
                    # the way yield works these could have been modified.
                    vl = self.svstate.vl
                    subvl = self.subvl
                    srcstep = self.svstate.srcstep
                    log("    advance src check", srcstep, vl,
                        self.svstate.ssubstep, subvl, srcstep == vl-1,
                        self.svstate.ssubstep == subvl)
                    if srcstep == vl-1:  # end-point
                        self.svstate.srcstep = SelectableInt(0, 7)  # reset
                        if self.svstate.ssubstep == subvl:  # end-point
                            log("    advance pack stop")
                            return
                        break # exit inner loop
                    self.svstate.srcstep += SelectableInt(1, 7)  # advance ss
                subvl = self.subvl
                if self.svstate.ssubstep == subvl:  # end-point
                    self.svstate.ssubstep = SelectableInt(0, 2)  # reset
                    log("    advance pack stop")
                    return
                self.svstate.ssubstep += SelectableInt(1, 2)

        else:
            # these cannot be done as for-loops because SVSTATE may change
            # (srcstep/substep may be modified, interrupted, subvl/vl change)
            # but they *can* be done as while-loops as long as every SVSTATE
            # "thing" is re-read every single time a yield gives indices
            while True:  # outer vl loop
                while True:  # inner subvl loop
                    vl = self.svstate.vl
                    subvl = self.subvl
                    srcmask = self.srcmask
                    srcstep = self.svstate.srcstep
                    pred_src_zero = ((1 << srcstep) & srcmask) != 0
                    if self.pred_sz or pred_src_zero:
                        self.pred_src_zero = not pred_src_zero
                        log("    advance src", srcstep, vl,
                            self.svstate.ssubstep, subvl)
                        # yield actual substep/srcstep
                        yield (self.svstate.ssubstep, srcstep)
                    if self.svstate.ssubstep == subvl:  # end-point
                        self.svstate.ssubstep = SelectableInt(0, 2)  # reset
                        break # exit inner loop
                    self.svstate.ssubstep += SelectableInt(1, 2)
                vl = self.svstate.vl
                if srcstep == vl-1:  # end-point
                    self.svstate.srcstep = SelectableInt(0, 7)  # reset
                    self.loopend = True
                    return
                self.svstate.srcstep += SelectableInt(1, 7)  # advance srcstep

    def dst_iterator(self):
        """dest-stepping iterator
        """
        unpack = self.svstate.unpack

        # dest step
        if unpack:
            # pack advances subvl in *outer* loop
            while True:  # outer subvl loop
                while True:  # inner vl loop
                    vl = self.svstate.vl
                    subvl = self.subvl
                    dstmask = self.dstmask
                    dststep = self.svstate.dststep
                    pred_dst_zero = ((1 << dststep) & dstmask) != 0
                    if self.pred_dz or pred_dst_zero:
                        self.pred_dst_zero = not pred_dst_zero
                        log("    advance dst", dststep, vl,
                            self.svstate.dsubstep, subvl)
                        # yield actual substep/dststep
                        yield (self.svstate.dsubstep, dststep)
                    # the way yield works these could have been modified.
                    vl = self.svstate.vl
                    dststep = self.svstate.dststep
                    log("    advance dst check", dststep, vl,
                        self.svstate.ssubstep, subvl)
                    if dststep == vl-1:  # end-point
                        self.svstate.dststep = SelectableInt(0, 7)  # reset
                        if self.svstate.dsubstep == subvl:  # end-point
                            log("    advance unpack stop")
                            return
                        break
                    self.svstate.dststep += SelectableInt(1, 7)  # advance ds
                subvl = self.subvl
                if self.svstate.dsubstep == subvl:  # end-point
                    self.svstate.dsubstep = SelectableInt(0, 2)  # reset
                    log("    advance unpack stop")
                    return
                self.svstate.dsubstep += SelectableInt(1, 2)
        else:
            # these cannot be done as for-loops because SVSTATE may change
            # (dststep/substep may be modified, interrupted, subvl/vl change)
            # but they *can* be done as while-loops as long as every SVSTATE
            # "thing" is re-read every single time a yield gives indices
            while True:  # outer vl loop
                while True:  # inner subvl loop
                    subvl = self.subvl
                    dstmask = self.dstmask
                    dststep = self.svstate.dststep
                    pred_dst_zero = ((1 << dststep) & dstmask) != 0
                    if self.pred_dz or pred_dst_zero:
                        self.pred_dst_zero = not pred_dst_zero
                        log("    advance dst", dststep, self.svstate.vl,
                            self.svstate.dsubstep, subvl)
                        # yield actual substep/dststep
                        yield (self.svstate.dsubstep, dststep)
                    if self.svstate.dsubstep == subvl:  # end-point
                        self.svstate.dsubstep = SelectableInt(0, 2)  # reset
                        break
                    self.svstate.dsubstep += SelectableInt(1, 2)
                subvl = self.subvl
                vl = self.svstate.vl
                if dststep == vl-1:  # end-point
                    self.svstate.dststep = SelectableInt(0, 7)  # reset
                    return
                self.svstate.dststep += SelectableInt(1, 7)  # advance dststep

    def src_iterate(self):
        """source-stepping iterator
        """
        subvl = self.subvl
        vl = self.svstate.vl
        pack = self.svstate.pack
        unpack = self.svstate.unpack
        ssubstep = self.svstate.ssubstep
        end_ssub = ssubstep == subvl
        end_src = self.svstate.srcstep == vl-1
        log("    pack/unpack/subvl", pack, unpack, subvl,
            "end", end_src,
            "sub", end_ssub)
        # first source step
        srcstep = self.svstate.srcstep
        srcmask = self.srcmask
        if pack:
            # pack advances subvl in *outer* loop
            while True:
                assert srcstep <= vl-1
                end_src = srcstep == vl-1
                if end_src:
                    if end_ssub:
                        self.loopend = True
                    else:
                        self.svstate.ssubstep += SelectableInt(1, 2)
                    srcstep = 0  # reset
                    break
                else:
                    srcstep += 1  # advance srcstep
                    if not self.srcstep_skip:
                        break
                    if ((1 << srcstep) & srcmask) != 0:
                        break
                    else:
                        log("      sskip", bin(srcmask), bin(1 << srcstep))
        else:
            # advance subvl in *inner* loop
            if end_ssub:
                while True:
                    assert srcstep <= vl-1
                    end_src = srcstep == vl-1
                    if end_src:  # end-point
                        self.loopend = True
                        srcstep = 0
                        break
                    else:
                        srcstep += 1
                    if not self.srcstep_skip:
                        break
                    if ((1 << srcstep) & srcmask) != 0:
                        break
                    else:
                        log("      sskip", bin(srcmask), bin(1 << srcstep))
                self.svstate.ssubstep = SelectableInt(0, 2)  # reset
            else:
                # advance ssubstep
                self.svstate.ssubstep += SelectableInt(1, 2)

        self.svstate.srcstep = SelectableInt(srcstep, 7)
        log("    advance src", self.svstate.srcstep, self.svstate.ssubstep,
                               self.loopend)

    def dst_iterate(self):
        """dest step iterator
        """
        vl = self.svstate.vl
        subvl = self.subvl
        pack = self.svstate.pack
        unpack = self.svstate.unpack
        dsubstep = self.svstate.dsubstep
        end_dsub = dsubstep == subvl
        dststep = self.svstate.dststep
        end_dst = dststep == vl-1
        dstmask = self.dstmask
        log("    pack/unpack/subvl", pack, unpack, subvl,
            "end", end_dst,
            "sub", end_dsub)
        # now dest step
        if unpack:
            # unpack advances subvl in *outer* loop
            while True:
                assert dststep <= vl-1
                end_dst = dststep == vl-1
                if end_dst:
                    if end_dsub:
                        self.loopend = True
                    else:
                        self.svstate.dsubstep += SelectableInt(1, 2)
                    dststep = 0  # reset
                    break
                else:
                    dststep += 1  # advance dststep
                    if not self.dststep_skip:
                        break
                    if ((1 << dststep) & dstmask) != 0:
                        break
                    else:
                        log("      dskip", bin(dstmask), bin(1 << dststep))
        else:
            # advance subvl in *inner* loop
            if end_dsub:
                while True:
                    assert dststep <= vl-1
                    end_dst = dststep == vl-1
                    if end_dst:  # end-point
                        self.loopend = True
                        dststep = 0
                        break
                    else:
                        dststep += 1
                    if not self.dststep_skip:
                        break
                    if ((1 << dststep) & dstmask) != 0:
                        break
                    else:
                        log("      dskip", bin(dstmask), bin(1 << dststep))
                self.svstate.dsubstep = SelectableInt(0, 2)  # reset
            else:
                # advance ssubstep
                self.svstate.dsubstep += SelectableInt(1, 2)

        self.svstate.dststep = SelectableInt(dststep, 7)
        log("    advance dst", self.svstate.dststep, self.svstate.dsubstep,
                               self.loopend)

    def at_loopend(self):
        """tells if this is the last possible element.  uses the cached values
        for src/dst-step and sub-steps
        """
        subvl = self.subvl
        vl = self.svstate.vl
        srcstep, dststep = self.new_srcstep, self.new_dststep
        ssubstep, dsubstep = self.new_ssubstep, self.new_dsubstep
        end_ssub = ssubstep == subvl
        end_dsub = dsubstep == subvl
        if srcstep == vl-1 and end_ssub:
            return True
        if dststep == vl-1 and end_dsub:
            return True
        return False

    def advance_svstate_steps(self):
        """ advance sub/steps. note that Pack/Unpack *INVERTS* the order.
        TODO when Pack/Unpack is set, substep becomes the *outer* loop
        """
        self.subvl = yield self.dec2.rm_dec.rm_in.subvl
        if self.loopend: # huhn??
            return
        self.src_iterate()
        self.dst_iterate()

    def read_src_mask(self):
        """read/update pred_sz and src mask
        """
        # get SVSTATE VL (oh and print out some debug stuff)
        vl = self.svstate.vl
        srcstep = self.svstate.srcstep
        ssubstep = self.svstate.ssubstep

        # get predicate mask (all 64 bits)
        srcmask = 0xffff_ffff_ffff_ffff

        pmode = yield self.dec2.rm_dec.predmode
        sv_ptype = yield self.dec2.dec.op.SV_Ptype
        srcpred = yield self.dec2.rm_dec.srcpred
        dstpred = yield self.dec2.rm_dec.dstpred
        pred_sz = yield self.dec2.rm_dec.pred_sz
        if pmode == SVP64PredMode.INT.value:
            srcmask = dstmask = get_predint(self.gpr, dstpred)
            if sv_ptype == SVPtype.P2.value:
                srcmask = get_predint(self.gpr, srcpred)
        elif pmode == SVP64PredMode.CR.value:
            srcmask = dstmask = get_predcr(self.crl, dstpred, vl)
            if sv_ptype == SVPtype.P2.value:
                srcmask = get_predcr(self.crl, srcpred, vl)
        # work out if the ssubsteps are completed
        ssubstart = ssubstep == 0
        log("    pmode", pmode)
        log("    ptype", sv_ptype)
        log("    srcpred", bin(srcpred))
        log("    srcmask", bin(srcmask))
        log("    pred_sz", bin(pred_sz))
        log("    ssubstart", ssubstart)

        # store all that above
        self.srcstep_skip = False
        self.srcmask = srcmask
        self.pred_sz = pred_sz
        self.new_ssubstep = ssubstep
        log("    new ssubstep", ssubstep)
        # until the predicate mask has a "1" bit... or we run out of VL
        # let srcstep==VL be the indicator to move to next instruction
        if not pred_sz:
            self.srcstep_skip = True

    def read_dst_mask(self):
        """same as read_src_mask - check and record everything needed
        """
        # get SVSTATE VL (oh and print out some debug stuff)
        # yield Delay(1e-10)  # make changes visible
        vl = self.svstate.vl
        dststep = self.svstate.dststep
        dsubstep = self.svstate.dsubstep

        # get predicate mask (all 64 bits)
        dstmask = 0xffff_ffff_ffff_ffff

        pmode = yield self.dec2.rm_dec.predmode
        reverse_gear = yield self.dec2.rm_dec.reverse_gear
        sv_ptype = yield self.dec2.dec.op.SV_Ptype
        dstpred = yield self.dec2.rm_dec.dstpred
        pred_dz = yield self.dec2.rm_dec.pred_dz
        if pmode == SVP64PredMode.INT.value:
            dstmask = get_predint(self.gpr, dstpred)
        elif pmode == SVP64PredMode.CR.value:
            dstmask = get_predcr(self.crl, dstpred, vl)
        # work out if the ssubsteps are completed
        dsubstart = dsubstep == 0
        log("    pmode", pmode)
        log("    ptype", sv_ptype)
        log("    dstpred", bin(dstpred))
        log("    dstmask", bin(dstmask))
        log("    pred_dz", bin(pred_dz))
        log("    dsubstart", dsubstart)

        self.dststep_skip = False
        self.dstmask = dstmask
        self.pred_dz = pred_dz
        self.new_dsubstep = dsubstep
        log("    new dsubstep", dsubstep)
        if not pred_dz:
            self.dststep_skip = True

    def svstate_pre_inc(self):
        """check if srcstep/dststep need to skip over masked-out predicate bits
        note that this is not supposed to do anything to substep,
        it is purely for skipping masked-out bits
        """

        self.subvl = yield self.dec2.rm_dec.rm_in.subvl
        yield from self.read_src_mask()
        yield from self.read_dst_mask()

        self.skip_src()
        self.skip_dst()

    def skip_src(self):

        srcstep = self.svstate.srcstep
        srcmask = self.srcmask
        pred_src_zero = self.pred_sz
        vl = self.svstate.vl
        # srcstep-skipping opportunity identified
        if self.srcstep_skip:
            # cannot do this with sv.bc - XXX TODO
            if srcmask == 0:
                self.loopend = True
            while (((1 << srcstep) & srcmask) == 0) and (srcstep != vl):
                log("      sskip", bin(1 << srcstep))
                srcstep += 1

        # now work out if the relevant mask bits require zeroing
        if pred_src_zero:
            pred_src_zero = ((1 << srcstep) & srcmask) == 0

        # store new srcstep / dststep
        self.new_srcstep = srcstep
        self.pred_src_zero = pred_src_zero
        log("    new srcstep", srcstep)

    def skip_dst(self):
        # dststep-skipping opportunity identified
        dststep = self.svstate.dststep
        dstmask = self.dstmask
        pred_dst_zero = self.pred_dz
        vl = self.svstate.vl
        if self.dststep_skip:
            # cannot do this with sv.bc - XXX TODO
            if dstmask == 0:
                self.loopend = True
            while (((1 << dststep) & dstmask) == 0) and (dststep != vl):
                log("      dskip", bin(1 << dststep))
                dststep += 1

        # now work out if the relevant mask bits require zeroing
        if pred_dst_zero:
            pred_dst_zero = ((1 << dststep) & dstmask) == 0

        # store new srcstep / dststep
        self.new_dststep = dststep
        self.pred_dst_zero = pred_dst_zero
        log("    new dststep", dststep)


class ISACaller(ISACallerHelper, ISAFPHelpers, StepLoop):
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
        StepLoop.__init__(self, initial_svstate)
        self.msr = SelectableInt(initial_msr, 64)  # underlying reg
        self.pc = PC()
        # GPR FPR SPR registers
        initial_sprs = deepcopy(initial_sprs)  # so as not to get modified
        self.gpr = GPR(decoder2, self, self.svstate, regfile)
        self.fpr = GPR(decoder2, self, self.svstate, fpregfile)
        self.spr = SPR(decoder2, initial_sprs)  # initialise SPRs before MMU

        # set up 4 dummy SVSHAPEs if they aren't already set up
        for i in range(4):
            sname = 'SVSHAPE%d' % i
            val = self.spr.get(sname, 0)
            # make sure it's an SVSHAPE
            self.spr[sname] = SVSHAPE(val, self.gpr)
        self.last_op_svshape = False

        # "raw" memory
        self.mem = Mem(row_bytes=8, initial_mem=initial_mem)
        self.mem.log_fancy(kind=LogKind.InstrInOuts)
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
        # self.undefined = SelectableInt(0, 256)  # TODO, not hard-code 256!

        self.namespace = {}
        self.namespace.update(self.spr)
        self.namespace.update({'GPR': self.gpr,
                               'FPR': self.fpr,
                               'MEM': self.mem,
                               'SPR': self.spr,
                               'memassign': self.memassign,
                               'NIA': self.pc.NIA,
                               'CIA': self.pc.CIA,
                               'SVSTATE': self.svstate,
                               'SVSHAPE0': self.spr['SVSHAPE0'],
                               'SVSHAPE1': self.spr['SVSHAPE1'],
                               'SVSHAPE2': self.spr['SVSHAPE2'],
                               'SVSHAPE3': self.spr['SVSHAPE3'],
                               'CR': self.cr,
                               'MSR': self.msr,
                               'undefined': undefined,
                               'mode_is_64bit': True,
                               'SO': XER_bits['SO'],
                               'XLEN': 64  # elwidth overrides, later
                               })

        # update pc to requested start point
        self.set_pc(initial_pc)

        # field-selectable versions of Condition Register
        self.crl = self.cr_fields.crl
        for i in range(8):
            self.namespace["CR%d" % i] = self.crl[i]

        self.decoder = decoder2.dec
        self.dec2 = decoder2

        super().__init__(XLEN=self.namespace["XLEN"])

    @property
    def XLEN(self):
        return self.namespace["XLEN"]

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
        # https://bugs.libre-soc.org/show_bug.cgi?id=859
        kaivb = self.spr['KAIVB'].value
        msr = self.namespace['MSR'].value
        log("TRAP:", hex(trap_addr), hex(msr), "kaivb", hex(kaivb))
        # store CIA(+4?) in SRR0, set NIA to 0x700
        # store MSR in SRR1, set MSR to um errr something, have to check spec
        # store SVSTATE (if enabled) in SVSRR0
        self.spr['SRR0'].value = self.pc.CIA.value
        self.spr['SRR1'].value = msr
        if self.is_svp64_mode:
            self.spr['SVSRR0'] = self.namespace['SVSTATE'].value
        self.trap_nia = SelectableInt(trap_addr | (kaivb & ~0x1fff), 64)
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

    def prep_namespace(self, insn_name, formname, op_fields):
        # TODO: get field names from form in decoder*1* (not decoder2)
        # decoder2 is hand-created, and decoder1.sigform is auto-generated
        # from spec
        # then "yield" fields only from op_fields rather than hard-coded
        # list, here.
        fields = self.decoder.sigforms[formname]
        log("prep_namespace", formname, op_fields, insn_name)
        for name in op_fields:
            # CR immediates. deal with separately.  needs modifying
            # pseudocode
            if self.is_svp64_mode and name in ['BI']:  # TODO, more CRs
                # BI is a 5-bit, must reconstruct the value
                regnum, is_vec = yield from get_pdecode_cr_in(self.dec2, name)
                sig = getattr(fields, name)
                val = yield sig
                # low 2 LSBs (CR field selector) remain same, CR num extended
                assert regnum <= 7, "sigh, TODO, 128 CR fields"
                val = (val & 0b11) | (regnum << 2)
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
        vl = self.svstate.vl
        srcstep = self.svstate.srcstep
        self.namespace['VL'] = vl
        self.namespace['srcstep'] = srcstep

        # sv.bc* need some extra fields
        if self.is_svp64_mode and insn_name.startswith("sv.bc"):
            # blegh grab bits manually
            mode = yield self.dec2.rm_dec.rm_in.mode
            mode = SelectableInt(mode, 5) # convert to SelectableInt before test
            bc_vlset = mode[SVP64MODEb.BC_VLSET] != 0
            bc_vli = mode[SVP64MODEb.BC_VLI] != 0
            bc_snz = mode[SVP64MODEb.BC_SNZ] != 0
            bc_vsb = yield self.dec2.rm_dec.bc_vsb
            bc_lru = yield self.dec2.rm_dec.bc_lru
            bc_gate = yield self.dec2.rm_dec.bc_gate
            sz = yield self.dec2.rm_dec.pred_sz
            self.namespace['mode'] = SelectableInt(mode, 5)
            self.namespace['ALL'] = SelectableInt(bc_gate, 1)
            self.namespace['VSb'] = SelectableInt(bc_vsb, 1)
            self.namespace['LRu'] = SelectableInt(bc_lru, 1)
            self.namespace['VLSET'] = SelectableInt(bc_vlset, 1)
            self.namespace['VLI'] = SelectableInt(bc_vli, 1)
            self.namespace['sz'] = SelectableInt(sz, 1)
            self.namespace['SNZ'] = SelectableInt(bc_snz, 1)

    def handle_carry_(self, inputs, output, ca, ca32):
        inv_a = yield self.dec2.e.do.invert_in
        if inv_a:
            inputs[0] = ~inputs[0]

        imm_ok = yield self.dec2.e.do.imm_data.ok
        if imm_ok:
            imm = yield self.dec2.e.do.imm_data.data
            inputs.append(SelectableInt(imm, 64))
        gts = []
        for x in inputs:
            log("gt input", x, output)
            gt = (gtu(x, output))
            gts.append(gt)
        log(gts)
        cy = 1 if any(gts) else 0
        log("CA", cy, gts)
        if ca is None: # already written
            self.spr['XER'][XER_bits['CA']] = cy

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
        if ca32 is None: # already written
            self.spr['XER'][XER_bits['CA32']] = cy32

    def handle_overflow(self, inputs, output, div_overflow):
        if hasattr(self.dec2.e.do, "invert_in"):
            inv_a = yield self.dec2.e.do.invert_in
            if inv_a:
                inputs[0] = ~inputs[0]

        imm_ok = yield self.dec2.e.do.imm_data.ok
        if imm_ok:
            imm = yield self.dec2.e.do.imm_data.data
            inputs.append(SelectableInt(imm, 64))
        log("handle_overflow", inputs, output, div_overflow)
        if len(inputs) < 2 and div_overflow is None:
            return

        # div overflow is different: it's returned by the pseudo-code
        # because it's more complex than can be done by analysing the output
        if div_overflow is not None:
            ov, ov32 = div_overflow, div_overflow
        # arithmetic overflow can be done by analysing the input and output
        elif len(inputs) >= 2:
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

        # now update XER OV/OV32/SO
        so = self.spr['XER'][XER_bits['SO']]
        new_so = so | ov  # sticky overflow ORs in old with new
        self.spr['XER'][XER_bits['OV']] = ov
        self.spr['XER'][XER_bits['OV32']] = ov32
        self.spr['XER'][XER_bits['SO']] = new_so
        log("    set overflow", ov, ov32, so, new_so)

    def handle_comparison(self, out, cr_idx=0, overflow=None, no_so=False):
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
        # create the three main CR flags, EQ GT LT
        zero = SelectableInt(out == 0, 1)
        positive = SelectableInt(out > 0, 1)
        negative = SelectableInt(out < 0, 1)
        # get (or not) XER.SO.  for setvl this is important *not* to read SO
        if no_so:
            SO = SelectableInt(1, 0)
        else:
            SO = self.spr['XER'][XER_bits['SO']]
        log("handle_comparison SO overflow", SO, overflow)
        # alternative overflow checking (setvl mainly at the moment)
        if overflow is not None and overflow == 1:
            SO = SelectableInt(1, 1)
        # create the four CR field values and set the required CR field
        cr_field = selectconcat(negative, positive, zero, SO)
        log("handle_comparison cr_field", self.cr, cr_idx, cr_field)
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
            yield self.dec2.state.svstate.eq(self.svstate.value)

        # SVP64.  first, check if the opcode is EXT001, and SVP64 id bits set
        yield Settle()
        opcode = yield self.dec2.dec.opcode_in
        opcode = SelectableInt(value=opcode, bits=32)
        pfx = SVP64Instruction.Prefix(opcode)
        log("prefix test: opcode:", pfx.po, bin(pfx.po), pfx.id)
        self.is_svp64_mode = bool((pfx.po == 0b000001) and (pfx.id == 0b11))
        self.pc.update_nia(self.is_svp64_mode)
        # set SVP64 decode
        yield self.dec2.is_svp64_mode.eq(self.is_svp64_mode)
        self.namespace['NIA'] = self.pc.NIA
        self.namespace['SVSTATE'] = self.svstate
        if not self.is_svp64_mode:
            return

        # in SVP64 mode.  decode/print out svp64 prefix, get v3.0B instruction
        log("svp64.rm", bin(pfx.rm))
        log("    svstate.vl", self.svstate.vl)
        log("    svstate.mvl", self.svstate.maxvl)
        ins = self.imem.ld(pc+4, 4, False, True, instr_fetch=True)
        log("     svsetup: 0x%x 0x%x %s" % (pc+4, ins & 0xffffffff, bin(ins)))
        yield self.dec2.dec.raw_opcode_in.eq(ins & 0xffffffff)  # v3.0B suffix
        yield self.dec2.sv_rm.eq(int(pfx.rm))                   # svp64 prefix
        yield Settle()

    def execute_one(self):
        """execute one instruction
        """
        # get the disassembly code for this instruction
        if not self.disassembly:
            code = yield from self.get_assembly_name()
        else:
            offs, dbg = 0, ""
            if self.is_svp64_mode:
               offs, dbg = 4, "svp64 "
            code = self.disassembly[self._pc+offs]
            log("    %s sim-execute" % dbg, hex(self._pc), code)
        opname = code.split(' ')[0]
        try:
            yield from self.call(opname)         # execute the instruction
        except MemException as e:                # check for memory errors
            if e.args[0] == 'unaligned':         # alignment error
               # run a Trap but set DAR first
                print("memory unaligned exception, DAR", e.dar)
                self.spr['DAR'] = SelectableInt(e.dar, 64)
                self.call_trap(0x600, PIb.PRIV)    # 0x600, privileged
                return
            elif e.args[0] == 'invalid':         # invalid
               # run a Trap but set DAR first
                log("RADIX MMU memory invalid error, mode %s" % e.mode)
                if e.mode == 'EXECUTE':
                    # XXX TODO: must set a few bits in SRR1,
                    # see microwatt loadstore1.vhdl
                    # if m_in.segerr = '0' then
                    #     v.srr1(47 - 33) := m_in.invalid;
                    #     v.srr1(47 - 35) := m_in.perm_error; -- noexec fault
                    #     v.srr1(47 - 44) := m_in.badtree;
                    #     v.srr1(47 - 45) := m_in.rc_error;
                    #     v.intr_vec := 16#400#;
                    # else
                    #     v.intr_vec := 16#480#;
                    self.call_trap(0x400, PIb.PRIV)    # 0x400, privileged
                else:
                    self.call_trap(0x300, PIb.PRIV)    # 0x300, privileged
                return
            # not supported yet:
            raise e                          # ... re-raise

        # don't use this except in special circumstances
        if not self.respect_pc:
            self.fake_pc += 4

        log("execute one, CIA NIA", hex(self.pc.CIA.value),
            hex(self.pc.NIA.value))

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
        # annoying: ignore rc_ok if RC1 is set (for creating *assembly name*)
        RC1 = yield self.dec2.rm_dec.RC1
        if RC1:
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

    def reset_remaps(self):
        self.remap_loopends = [0] * 4
        self.remap_idxs = [0, 1, 2, 3]

    def get_remap_indices(self):
        """WARNING, this function stores remap_idxs and remap_loopends
        in the class for later use.  this to avoid problems with yield
        """
        # go through all iterators in lock-step, advance to next remap_idx
        srcstep, dststep, ssubstep, dsubstep = self.get_src_dststeps()
        # get four SVSHAPEs. here we are hard-coding
        self.reset_remaps()
        SVSHAPE0 = self.spr['SVSHAPE0']
        SVSHAPE1 = self.spr['SVSHAPE1']
        SVSHAPE2 = self.spr['SVSHAPE2']
        SVSHAPE3 = self.spr['SVSHAPE3']
        # set up the iterators
        remaps = [(SVSHAPE0, SVSHAPE0.get_iterator()),
                  (SVSHAPE1, SVSHAPE1.get_iterator()),
                  (SVSHAPE2, SVSHAPE2.get_iterator()),
                  (SVSHAPE3, SVSHAPE3.get_iterator()),
                  ]

        dbg = []
        for i, (shape, remap) in enumerate(remaps):
            # zero is "disabled"
            if shape.value == 0x0:
                self.remap_idxs[i] = 0
            # pick src or dststep depending on reg num (0-2=in, 3-4=out)
            step = dststep if (i in [3, 4]) else srcstep
            # this is terrible.  O(N^2) looking for the match. but hey.
            for idx, (remap_idx, loopends) in enumerate(remap):
                if idx == step:
                    break
            self.remap_idxs[i] = remap_idx
            self.remap_loopends[i] = loopends
            dbg.append((i, step, remap_idx, loopends))
        for (i, step, remap_idx, loopends) in dbg:
            log("SVSHAPE %d idx, end" % i, step, remap_idx, bin(loopends))
        return remaps

    def get_spr_msb(self):
        dec_insn = yield self.dec2.e.do.insn
        return dec_insn & (1 << 20) != 0  # sigh - XFF.spr[-1]?

    def call(self, name):
        """call(opcode) - the primary execution point for instructions
        """
        self.last_st_addr = None  # reset the last known store address
        self.last_ld_addr = None  # etc.

        ins_name = name.strip()  # remove spaces if not already done so
        if self.halted:
            log("halted - not executing", ins_name)
            return

        # TODO, asmregs is from the spec, e.g. add RT,RA,RB
        # see http://bugs.libre-riscv.org/show_bug.cgi?id=282
        asmop = yield from self.get_assembly_name()
        log("call", ins_name, asmop)

        # sv.setvl is *not* a loop-function. sigh
        log("is_svp64_mode", self.is_svp64_mode, asmop)

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
        if ins_name == 'attn':
            self.halted = True
            return

        # check illegal instruction
        illegal = False
        if ins_name not in ['mtcrf', 'mtocrf']:
            illegal = ins_name != asmop

        # list of instructions not being supported by binutils (.long)
        dotstrp = asmop[:-1] if asmop[-1] == '.' else asmop
        if dotstrp in [*FPTRANS_INSNS,
                       'ffmadds', 'fdmadds', 'ffadds',
                       'mins', 'maxs', 'minu', 'maxu',
                       'setvl', 'svindex', 'svremap', 'svstep',
                       'svshape', 'svshape2',
                       'grev', 'ternlogi', 'bmask', 'cprop',
                       'absdu', 'absds', 'absdacs', 'absdacu', 'avgadd',
                       'fmvis', 'fishmv', 'pcdec', "maddedu", "divmod2du",
                       "dsld", "dsrd",
                       ]:
            illegal = False
            ins_name = dotstrp

        # branch-conditional redirects to sv.bc
        if asmop.startswith('bc') and self.is_svp64_mode:
            ins_name = 'sv.%s' % ins_name

        log("   post-processed name", dotstrp, ins_name, asmop)

        # illegal instructions call TRAP at 0x700
        if illegal:
            print("illegal", ins_name, asmop)
            self.call_trap(0x700, PIb.ILLEG)
            print("name %s != %s - calling ILLEGAL trap, PC: %x" %
                  (ins_name, asmop, self.pc.CIA.value))
            return

        # this is for setvl "Vertical" mode: if set true,
        # srcstep/dststep is explicitly advanced. mode says which SVSTATE to
        # test for Rc=1 end condition.  3 bits of all 3 loops are put into CR0
        self.allow_next_step_inc = False
        self.svstate_next_mode = 0

        # nop has to be supported, we could let the actual op calculate
        # but PowerDecoder has a pattern for nop
        if ins_name == 'nop':
            self.update_pc_next()
            return

        # look up instruction in ISA.instrs, prepare namespace
        if ins_name == 'pcdec': # grrrr yes there are others ("stbcx." etc.)
            info = self.instrs[ins_name+"."]
        else:
            info = self.instrs[ins_name]
        yield from self.prep_namespace(ins_name, info.form, info.op_fields)

        # preserve order of register names
        input_names = create_args(list(info.read_regs) +
                                  list(info.uninit_regs))
        log("input names", input_names)

        # get SVP64 entry for the current instruction
        sv_rm = self.svp64rm.instrs.get(ins_name)
        if sv_rm is not None:
            dest_cr, src_cr, src_byname, dest_byname = decode_extra(sv_rm)
        else:
            dest_cr, src_cr, src_byname, dest_byname = False, False, {}, {}
        log("sv rm", sv_rm, dest_cr, src_cr, src_byname, dest_byname)

        # see if srcstep/dststep need skipping over masked-out predicate bits
        self.reset_remaps()
        if (self.is_svp64_mode or ins_name in ['svstep', 'svremap']):
            yield from self.svstate_pre_inc()
        if self.is_svp64_mode:
            pre = yield from self.update_new_svstate_steps()
            if pre:
                self.svp64_reset_loop()
                self.update_nia()
                self.update_pc_next()
                return
            srcstep, dststep, ssubstep, dsubstep = self.get_src_dststeps()
            pred_dst_zero = self.pred_dst_zero
            pred_src_zero = self.pred_src_zero
            vl = self.svstate.vl
            subvl = yield self.dec2.rm_dec.rm_in.subvl

        # VL=0 in SVP64 mode means "do nothing: skip instruction"
        if self.is_svp64_mode and vl == 0:
            self.pc.update(self.namespace, self.is_svp64_mode)
            log("SVP64: VL=0, end of call", self.namespace['CIA'],
                self.namespace['NIA'], kind=LogKind.InstrInOuts)
            return

        # for when SVREMAP is active, using pre-arranged schedule.
        # note: modifying PowerDecoder2 needs to "settle"
        remap_en = self.svstate.SVme
        persist = self.svstate.RMpst
        active = (persist or self.last_op_svshape) and remap_en != 0
        if self.is_svp64_mode:
            yield self.dec2.remap_active.eq(remap_en if active else 0)
        yield Settle()
        if persist or self.last_op_svshape:
            remaps = self.get_remap_indices()
        if self.is_svp64_mode and (persist or self.last_op_svshape):
            yield from self.remap_set_steps(remaps)
        # after that, settle down (combinatorial) to let Vector reg numbers
        # work themselves out
        yield Settle()
        if self.is_svp64_mode:
            remap_active = yield self.dec2.remap_active
        else:
            remap_active = False
        log("remap active", bin(remap_active))

        # main input registers (RT, RA ...)
        inputs = []
        for name in input_names:
            log("name", name)
            regval = (yield from self.get_input(name))
            log("regval", regval)
            inputs.append(regval)

        # arrrrgh, awful hack, to get _RT into namespace
        if ins_name in ['setvl', 'svstep']:
            regname = "_RT"
            RT = yield self.dec2.dec.RT
            self.namespace[regname] = SelectableInt(RT, 5)
            if RT == 0:
                self.namespace["RT"] = SelectableInt(0, 5)
            regnum, is_vec = yield from get_pdecode_idx_out(self.dec2, "RT")
            log('hack input reg %s %s' % (name, str(regnum)), is_vec)

        # in SVP64 mode for LD/ST work out immediate
        # XXX TODO: replace_ds for DS-Form rather than D-Form.
        # use info.form to detect
        if self.is_svp64_mode:
            yield from self.check_replace_d(info, remap_active)

        # "special" registers
        for special in info.special_regs:
            if special in special_sprs:
                inputs.append(self.spr[special])
            else:
                inputs.append(self.namespace[special])

        # clear trap (trap) NIA
        self.trap_nia = None

        # check if this was an sv.bc* and create an indicator that
        # this is the last check to be made as a loop.  combined with
        # the ALL/ANY mode we can early-exit
        if self.is_svp64_mode and ins_name.startswith("sv.bc"):
            no_in_vec = yield self.dec2.no_in_vec  # BI is scalar
            end_loop = no_in_vec or srcstep == vl-1 or dststep == vl-1
            self.namespace['end_loop'] = SelectableInt(end_loop, 1)

        # execute actual instruction here (finally)
        log("inputs", inputs)
        results = info.func(self, *inputs)
        output_names = create_args(info.write_regs)
        outs = {}
        for out, n in zip(results or [], output_names):
            outs[n] = out
        log("results", outs)

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
        log("op", int_op, MicrOp.OP_STORE.value, MicrOp.OP_LOAD.value,
            self.last_st_addr, self.last_ld_addr)

        # detect if CA/CA32 already in outputs (sra*, basically)
        ca = outs.get("CA")
        ca32 = outs.get("CA32 ")

        log("carry already done?", ca, ca32, output_names)
        carry_en = yield self.dec2.e.do.output_carry
        if carry_en:
            yield from self.handle_carry_(inputs, results[0], ca, ca32)

        # get outout named "overflow" and "CR0"
        overflow = outs.get('overflow')
        cr0 = outs.get('CR0')

        if not self.is_svp64_mode:  # yeah just no. not in parallel processing
            # detect if overflow was in return result
            ov_en = yield self.dec2.e.do.oe.oe
            ov_ok = yield self.dec2.e.do.oe.ok
            log("internal overflow", ins_name, overflow, "en?", ov_en, ov_ok)
            if ov_en & ov_ok:
                yield from self.handle_overflow(inputs, results[0], overflow)

        # only do SVP64 dest predicated Rc=1 if dest-pred is not enabled
        rc_en = False
        if not self.is_svp64_mode or not pred_dst_zero:
            if hasattr(self.dec2.e.do, "rc"):
                rc_en = yield self.dec2.e.do.rc.rc
        # don't do Rc=1 for svstep it is handled explicitly.
        # XXX TODO: now that CR0 is supported, sort out svstep's pseudocode
        # to write directly to CR0 instead of in ISACaller. hooyahh.
        if rc_en and ins_name not in ['svstep']:
            yield from self.do_rc_ov(ins_name, results[0], overflow, cr0)

        # check failfirst
        ffirst_hit = False
        if self.is_svp64_mode:
            ffirst_hit = (yield from self.check_ffirst(rc_en, srcstep))

        # any modified return results?
        yield from self.do_outregs_nia(asmop, ins_name, info, outs,
                                       carry_en, rc_en, ffirst_hit)

    def check_ffirst(self, rc_en, srcstep):
        """fail-first mode: checks a bit of Rc Vector, truncates VL
        """
        rm_mode = yield self.dec2.rm_dec.mode
        ff_inv = yield self.dec2.rm_dec.inv
        cr_bit = yield self.dec2.rm_dec.cr_sel
        RC1 = yield self.dec2.rm_dec.RC1
        vli = yield self.dec2.rm_dec.vli # VL inclusive if truncated
        log(" ff rm_mode", rc_en, rm_mode, SVP64RMMode.FFIRST.value)
        log("        inv", ff_inv)
        log("        RC1", RC1)
        log("        vli", vli)
        log("     cr_bit", cr_bit)
        if not rc_en or rm_mode != SVP64RMMode.FFIRST.value:
            return False
        # get the CR vevtor, do BO-test
        regnum, is_vec = yield from get_pdecode_cr_out(self.dec2, "CR0")
        crtest = self.crl[regnum]
        ffirst_hit = crtest[cr_bit] != ff_inv
        log("cr test", regnum, int(crtest), crtest, cr_bit, ff_inv)
        log("cr test?", ffirst_hit)
        if not ffirst_hit:
            return False
        # Fail-first activated, truncate VL
        vli = SelectableInt(int(vli), 7)
        self.svstate.vl = srcstep + vli
        yield self.dec2.state.svstate.eq(self.svstate.value)
        yield Settle()  # let decoder update
        return True

    def do_rc_ov(self, ins_name, result, overflow, cr0):
        if ins_name.startswith("f"):
            rc_reg = "CR1"  # not calculated correctly yet (not FP compares)
        else:
            rc_reg = "CR0"
        regnum, is_vec = yield from get_pdecode_cr_out(self.dec2, rc_reg)
        # hang on... for `setvl` actually you want to test SVSTATE.VL
        is_setvl = ins_name in ('svstep', 'setvl')
        if is_setvl:
            result = SelectableInt(result.vl, 64)
        else:
            overflow = None  # do not override overflow except in setvl

        # if there was not an explicit CR0 in the pseudocode, do implicit Rc=1
        if cr0 is None:
            self.handle_comparison(result, regnum, overflow, no_so=is_setvl)
        else:
            # otherwise we just blat CR0 into the required regnum
            log("explicit rc0", cr0)
            self.crl[regnum].eq(cr0)

    def do_outregs_nia(self, asmop, ins_name, info, outs,
                       carry_en, rc_en, ffirst_hit):
        # write out any regs for this instruction
        for name, output in outs.items():
            yield from self.check_write(info, name, output, carry_en)

        if ffirst_hit:
            self.svp64_reset_loop()
            nia_update = True
        else:
            # check advancement of src/dst/sub-steps and if PC needs updating
            nia_update = (yield from self.check_step_increment(rc_en,
                                                           asmop, ins_name))
        if nia_update:
            self.update_pc_next()

    def check_replace_d(self, info, remap_active):
        replace_d = False  # update / replace constant in pseudocode
        ldstmode = yield self.dec2.rm_dec.ldstmode
        vl = self.svstate.vl
        subvl = yield self.dec2.rm_dec.rm_in.subvl
        srcstep, dststep = self.new_srcstep, self.new_dststep
        ssubstep, dsubstep = self.new_ssubstep, self.new_dsubstep
        if info.form == 'DS':
            # DS-Form, multiply by 4 then knock 2 bits off after
            imm = yield self.dec2.dec.fields.FormDS.DS[0:14] * 4
        else:
            imm = yield self.dec2.dec.fields.FormD.D[0:16]
        imm = exts(imm, 16)  # sign-extend to integer
        # get the right step. LD is from srcstep, ST is dststep
        op = yield self.dec2.e.do.insn_type
        offsmul = 0
        if op == MicrOp.OP_LOAD.value:
            if remap_active:
                offsmul = yield self.dec2.in1_step
                log("D-field REMAP src", imm, offsmul)
            else:
                offsmul = (srcstep * (subvl+1)) + ssubstep
                log("D-field src", imm, offsmul)
        elif op == MicrOp.OP_STORE.value:
            # XXX NOTE! no bit-reversed STORE! this should not ever be used
            offsmul = (dststep * (subvl+1)) + dsubstep
            log("D-field dst", imm, offsmul)
        # Unit-Strided LD/ST adds offset*width to immediate
        if ldstmode == SVP64LDSTmode.UNITSTRIDE.value:
            ldst_len = yield self.dec2.e.do.data_len
            imm = SelectableInt(imm + offsmul * ldst_len, 32)
            replace_d = True
        # Element-strided multiplies the immediate by element step
        elif ldstmode == SVP64LDSTmode.ELSTRIDE.value:
            imm = SelectableInt(imm * offsmul, 32)
            replace_d = True
        if replace_d:
            ldst_ra_vec = yield self.dec2.rm_dec.ldst_ra_vec
            ldst_imz_in = yield self.dec2.rm_dec.ldst_imz_in
            log("LDSTmode", SVP64LDSTmode(ldstmode),
                offsmul, imm, ldst_ra_vec, ldst_imz_in)
        # new replacement D... errr.. DS
        if replace_d:
            if info.form == 'DS':
                # TODO: assert 2 LSBs are zero?
                log("DS-Form, TODO, assert 2 LSBs zero?", bin(imm.value))
                imm.value = imm.value >> 2
                self.namespace['DS'] = imm
            else:
                self.namespace['D'] = imm

    def get_input(self, name):
        # using PowerDecoder2, first, find the decoder index.
        # (mapping name RA RB RC RS to in1, in2, in3)
        regnum, is_vec = yield from get_pdecode_idx_in(self.dec2, name)
        if regnum is None:
            # doing this is not part of svp64, it's because output
            # registers, to be modified, need to be in the namespace.
            regnum, is_vec = yield from get_pdecode_idx_out(self.dec2, name)
        if regnum is None:
            regnum, is_vec = yield from get_pdecode_idx_out2(self.dec2, name)

        # in case getting the register number is needed, _RA, _RB
        regname = "_" + name
        self.namespace[regname] = regnum
        if not self.is_svp64_mode or not self.pred_src_zero:
            log('reading reg %s %s' % (name, str(regnum)), is_vec)
            if name in fregs:
                reg_val = SelectableInt(self.fpr(regnum))
                log("read reg %d: 0x%x" % (regnum, reg_val.value))
            elif name is not None:
                reg_val = SelectableInt(self.gpr(regnum))
                log("read reg %d: 0x%x" % (regnum, reg_val.value))
        else:
            log('zero input reg %s %s' % (name, str(regnum)), is_vec)
            reg_val = 0
        return reg_val

    def remap_set_steps(self, remaps):
        """remap_set_steps sets up the in1/2/3 and out1/2 steps.
        they work in concert with PowerDecoder2 at the moment,
        there is no HDL implementation of REMAP.  therefore this
        function, because ISACaller still uses PowerDecoder2,
        will *explicitly* write the dec2.XX_step values. this has
        to get sorted out.
        """
        # just some convenient debug info
        for i in range(4):
            sname = 'SVSHAPE%d' % i
            shape = self.spr[sname]
            log(sname, bin(shape.value))
            log("    lims", shape.lims)
            log("    mode", shape.mode)
            log("    skip", shape.skip)

        # set up the list of steps to remap
        mi0 = self.svstate.mi0
        mi1 = self.svstate.mi1
        mi2 = self.svstate.mi2
        mo0 = self.svstate.mo0
        mo1 = self.svstate.mo1
        steps = [(self.dec2.in1_step, mi0),  # RA
                 (self.dec2.in2_step, mi1),  # RB
                 (self.dec2.in3_step, mi2),  # RC
                 (self.dec2.o_step, mo0),   # RT
                 (self.dec2.o2_step, mo1),   # EA
                 ]
        remap_idxs = self.remap_idxs
        rremaps = []
        # now cross-index the required SHAPE for each of 3-in 2-out regs
        rnames = ['RA', 'RB', 'RC', 'RT', 'EA']
        for i, (dstep, shape_idx) in enumerate(steps):
            (shape, remap) = remaps[shape_idx]
            remap_idx = remap_idxs[shape_idx]
            # zero is "disabled"
            if shape.value == 0x0:
                continue
            # now set the actual requested step to the current index
            yield dstep.eq(remap_idx)

            # debug printout info
            rremaps.append((shape.mode, i, rnames[i], shape_idx, remap_idx))
        for x in rremaps:
            log("shape remap", x)

    def check_write(self, info, name, output, carry_en):
        if name == 'overflow':  # ignore, done already (above)
            return
        if name == 'CR0':  # ignore, done already (above)
            return
        if isinstance(output, int):
            output = SelectableInt(output, 256)
        # write carry flafs
        if name in ['CA', 'CA32']:
            if carry_en:
                log("writing %s to XER" % name, output)
                log("write XER %s 0x%x" % (name, output.value))
                self.spr['XER'][XER_bits[name]] = output.value
            else:
                log("NOT writing %s to XER" % name, output)
            return
        # write special SPRs
        if name in info.special_regs:
            log('writing special %s' % name, output, special_sprs)
            log("write reg %s 0x%x" % (name, output.value))
            if name in special_sprs:
                self.spr[name] = output
            else:
                self.namespace[name].eq(output)
            if name == 'MSR':
                log('msr written', hex(self.msr.value))
            return
        # find out1/out2 PR/FPR
        regnum, is_vec = yield from get_pdecode_idx_out(self.dec2, name)
        if regnum is None:
            regnum, is_vec = yield from get_pdecode_idx_out2(self.dec2, name)
        if regnum is None:
            # temporary hack for not having 2nd output
            regnum = yield getattr(self.decoder, name)
            is_vec = False
        # convenient debug prefix
        if name in fregs:
            reg_prefix = 'f'
        else:
            reg_prefix = 'r'
        # check zeroing due to predicate bit being zero
        if self.is_svp64_mode and self.pred_dst_zero:
            log('zeroing reg %d %s' % (regnum, str(output)), is_vec)
            output = SelectableInt(0, 256)
        log("write reg %s%d 0x%x" % (reg_prefix, regnum, output.value),
            kind=LogKind.InstrInOuts)
        # zero-extend tov64 bit begore storing (should use EXT oh well)
        if output.bits > 64:
            output = SelectableInt(output.value, 64)
        if name in fregs:
            self.fpr[regnum] = output
        else:
            self.gpr[regnum] = output

    def check_step_increment(self, rc_en, asmop, ins_name):
        # check if it is the SVSTATE.src/dest step that needs incrementing
        # this is our Sub-Program-Counter loop from 0 to VL-1
        if not self.allow_next_step_inc:
            if self.is_svp64_mode:
                return (yield from self.svstate_post_inc(ins_name))

            # XXX only in non-SVP64 mode!
            # record state of whether the current operation was an svshape,
            # OR svindex!
            # to be able to know if it should apply in the next instruction.
            # also (if going to use this instruction) should disable ability
            # to interrupt in between. sigh.
            self.last_op_svshape = asmop in ['svremap', 'svindex',
                                             'svshape2']
            return True

        pre = False
        post = False
        nia_update = True
        log("SVSTATE_NEXT: inc requested, mode",
            self.svstate_next_mode, self.allow_next_step_inc)
        yield from self.svstate_pre_inc()
        pre = yield from self.update_new_svstate_steps()
        if pre:
            # reset at end of loop including exit Vertical Mode
            log("SVSTATE_NEXT: end of loop, reset")
            self.svp64_reset_loop()
            self.svstate.vfirst = 0
            self.update_nia()
            if not rc_en:
                return True
            self.handle_comparison(SelectableInt(0, 64))  # CR0
            return True
        if self.allow_next_step_inc == 2:
            log("SVSTATE_NEXT: read")
            nia_update = (yield from self.svstate_post_inc(ins_name))
        else:
            log("SVSTATE_NEXT: post-inc")
        # use actual (cached) src/dst-step here to check end
        remaps = self.get_remap_indices()
        remap_idxs = self.remap_idxs
        vl = self.svstate.vl
        subvl = yield self.dec2.rm_dec.rm_in.subvl
        if self.allow_next_step_inc != 2:
            yield from self.advance_svstate_steps()
        #self.namespace['SVSTATE'] = self.svstate.spr
        # set CR0 (if Rc=1) based on end
        endtest = 1 if self.at_loopend() else 0
        if rc_en:
            #results = [SelectableInt(endtest, 64)]
            # self.handle_comparison(results) # CR0

            # see if svstep was requested, if so, which SVSTATE
            endings = 0b111
            if self.svstate_next_mode > 0:
                shape_idx = self.svstate_next_mode.value-1
                endings = self.remap_loopends[shape_idx]
            cr_field = SelectableInt((~endings) << 1 | endtest, 4)
            log("svstep Rc=1, CR0", cr_field, endtest)
            self.crl[0].eq(cr_field)  # CR0
        if endtest:
            # reset at end of loop including exit Vertical Mode
            log("SVSTATE_NEXT: after increments, reset")
            self.svp64_reset_loop()
            self.svstate.vfirst = 0
        return nia_update

    def SVSTATE_NEXT(self, mode, submode):
        """explicitly moves srcstep/dststep on to next element, for
        "Vertical-First" mode.  this function is called from
        setvl pseudo-code, as a pseudo-op "svstep"

        WARNING: this function uses information that was created EARLIER
        due to it being in the middle of a yield, but this function is
        *NOT* called from yield (it's called from compiled pseudocode).
        """
        self.allow_next_step_inc = submode.value + 1
        log("SVSTATE_NEXT mode", mode, submode, self.allow_next_step_inc)
        self.svstate_next_mode = mode
        if self.svstate_next_mode > 0 and self.svstate_next_mode < 5:
            shape_idx = self.svstate_next_mode.value-1
            return SelectableInt(self.remap_idxs[shape_idx], 7)
        if self.svstate_next_mode == 5:
            self.svstate_next_mode = 0
            return SelectableInt(self.svstate.srcstep, 7)
        if self.svstate_next_mode == 6:
            self.svstate_next_mode = 0
            return SelectableInt(self.svstate.dststep, 7)
        if self.svstate_next_mode == 7:
            self.svstate_next_mode = 0
            return SelectableInt(self.svstate.ssubstep, 7)
        if self.svstate_next_mode == 8:
            self.svstate_next_mode = 0
            return SelectableInt(self.svstate.dsubstep, 7)
        return SelectableInt(0, 7)

    def get_src_dststeps(self):
        """gets srcstep, dststep, and ssubstep, dsubstep
        """
        return (self.new_srcstep, self.new_dststep,
                self.new_ssubstep, self.new_dsubstep)

    def update_svstate_namespace(self, overwrite_svstate=True):
        if overwrite_svstate:
            # note, do not get the bit-reversed srcstep here!
            srcstep, dststep = self.new_srcstep, self.new_dststep
            ssubstep, dsubstep = self.new_ssubstep, self.new_dsubstep

            # update SVSTATE with new srcstep
            self.svstate.srcstep = srcstep
            self.svstate.dststep = dststep
            self.svstate.ssubstep = ssubstep
            self.svstate.dsubstep = dsubstep
        self.namespace['SVSTATE'] = self.svstate
        yield self.dec2.state.svstate.eq(self.svstate.value)
        yield Settle()  # let decoder update

    def update_new_svstate_steps(self, overwrite_svstate=True):
        yield from self.update_svstate_namespace(overwrite_svstate)
        srcstep = self.svstate.srcstep
        dststep = self.svstate.dststep
        ssubstep = self.svstate.ssubstep
        dsubstep = self.svstate.dsubstep
        pack = self.svstate.pack
        unpack = self.svstate.unpack
        vl = self.svstate.vl
        subvl = yield self.dec2.rm_dec.rm_in.subvl
        rm_mode = yield self.dec2.rm_dec.mode
        ff_inv = yield self.dec2.rm_dec.inv
        cr_bit = yield self.dec2.rm_dec.cr_sel
        log("    srcstep", srcstep)
        log("    dststep", dststep)
        log("        pack", pack)
        log("      unpack", unpack)
        log("    ssubstep", ssubstep)
        log("    dsubstep", dsubstep)
        log("         vl", vl)
        log("      subvl", subvl)
        log("    rm_mode", rm_mode)
        log("        inv", ff_inv)
        log("     cr_bit", cr_bit)

        # check if end reached (we let srcstep overrun, above)
        # nothing needs doing (TODO zeroing): just do next instruction
        if self.loopend:
            return True
        return ((ssubstep == subvl and srcstep == vl) or
                (dsubstep == subvl and dststep == vl))

    def svstate_post_inc(self, insn_name, vf=0):
        # check if SV "Vertical First" mode is enabled
        vfirst = self.svstate.vfirst
        log("    SV Vertical First", vf, vfirst)
        if not vf and vfirst == 1:
            self.update_nia()
            return True

        # check if it is the SVSTATE.src/dest step that needs incrementing
        # this is our Sub-Program-Counter loop from 0 to VL-1
        # XXX twin predication TODO
        vl = self.svstate.vl
        subvl = yield self.dec2.rm_dec.rm_in.subvl
        mvl = self.svstate.maxvl
        srcstep = self.svstate.srcstep
        dststep = self.svstate.dststep
        ssubstep = self.svstate.ssubstep
        dsubstep = self.svstate.dsubstep
        pack = self.svstate.pack
        unpack = self.svstate.unpack
        rm_mode = yield self.dec2.rm_dec.mode
        reverse_gear = yield self.dec2.rm_dec.reverse_gear
        sv_ptype = yield self.dec2.dec.op.SV_Ptype
        out_vec = not (yield self.dec2.no_out_vec)
        in_vec = not (yield self.dec2.no_in_vec)
        log("    svstate.vl", vl)
        log("    svstate.mvl", mvl)
        log("         rm.subvl", subvl)
        log("    svstate.srcstep", srcstep)
        log("    svstate.dststep", dststep)
        log("    svstate.ssubstep", ssubstep)
        log("    svstate.dsubstep", dsubstep)
        log("    svstate.pack", pack)
        log("    svstate.unpack", unpack)
        log("    mode", rm_mode)
        log("    reverse", reverse_gear)
        log("    out_vec", out_vec)
        log("    in_vec", in_vec)
        log("    sv_ptype", sv_ptype, sv_ptype == SVPtype.P2.value)
        # check if this was an sv.bc* and if so did it succeed
        if self.is_svp64_mode and insn_name.startswith("sv.bc"):
            end_loop = self.namespace['end_loop']
            log("branch %s end_loop" % insn_name, end_loop)
            if end_loop.value:
                self.svp64_reset_loop()
                self.update_pc_next()
                return False
        # check if srcstep needs incrementing by one, stop PC advancing
        # but for 2-pred both src/dest have to be checked.
        # XXX this might not be true! it may just be LD/ST
        if sv_ptype == SVPtype.P2.value:
            svp64_is_vector = (out_vec or in_vec)
        else:
            svp64_is_vector = out_vec
        # loops end at the first "hit" (source or dest)
        yield from self.advance_svstate_steps()
        loopend = self.loopend
        log("loopend", svp64_is_vector, loopend)
        if not svp64_is_vector or loopend:
            # reset loop to zero and update NIA
            self.svp64_reset_loop()
            self.update_nia()

            return True

        # still looping, advance and update NIA
        self.namespace['SVSTATE'] = self.svstate

        # not an SVP64 branch, so fix PC (NIA==CIA) for next loop
        # (by default, NIA is CIA+4 if v3.0B or CIA+8 if SVP64)
        # this way we keep repeating the same instruction (with new steps)
        self.pc.NIA.value = self.pc.CIA.value
        self.namespace['NIA'] = self.pc.NIA
        log("end of sub-pc call", self.namespace['CIA'], self.namespace['NIA'])
        return False  # DO NOT allow PC update whilst Sub-PC loop running

    def update_pc_next(self):
        # UPDATE program counter
        self.pc.update(self.namespace, self.is_svp64_mode)
        #self.svstate.spr = self.namespace['SVSTATE']
        log("end of call", self.namespace['CIA'],
            self.namespace['NIA'],
            self.namespace['SVSTATE'])

    def svp64_reset_loop(self):
        self.svstate.srcstep = 0
        self.svstate.dststep = 0
        self.svstate.ssubstep = 0
        self.svstate.dsubstep = 0
        self.loopend = False
        log("    svstate.srcstep loop end (PC to update)")
        self.namespace['SVSTATE'] = self.svstate

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
            log("globals before", context.keys())
            func_globals.update(context)
            result = func(*args, **kwargs)
            log("globals after", func_globals['CIA'], func_globals['NIA'])
            log("args[0]", args[0].namespace['CIA'],
                args[0].namespace['NIA'],
                args[0].namespace['SVSTATE'])
            if 'end_loop' in func_globals:
                log("args[0] end_loop", func_globals['end_loop'])
            args[0].namespace = func_globals
            #exec (func.__code__, func_globals)

            # finally:
            #    func_globals = saved_values  # Undo changes.

            return result

        return decorator

    return variable_injector
