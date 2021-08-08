# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl
"""SVP64 RM (Remap) Record.

https://libre-soc.org/openpower/sv/svp64/

| Field Name  | Field bits | Description                            |
|-------------|------------|----------------------------------------|
| MASKMODE    | `0`        | Execution (predication) Mask Kind      |
| MASK        | `1:3`      | Execution Mask                         |
| ELWIDTH     | `4:5`      | Element Width                          |
| ELWIDTH_SRC | `6:7`      | Element Width for Source               |
| SUBVL       | `8:9`      | Sub-vector length                      |
| EXTRA       | `10:18`    | context-dependent extra                |
| MODE        | `19:23`    | changes Vector behaviour               |
"""

from nmigen import Elaboratable, Module, Signal, Const
from openpower.decoder.power_enums import (SVP64RMMode, Function, SVPtype,
                                    SVP64PredMode, SVP64sat, SVP64LDSTmode,
                                    SVP64BCPredMode, SVP64BCVLSETMode,
                                    SVP64BCGate, SVP64BCStep,
                                    )
from openpower.consts import EXTRA3, SVP64MODE
from openpower.sv.svp64 import SVP64Rec
from nmutil.util import sel

# a list of fields which need to be added to input records in order
# pass on vital information needed by each pipeline.
# make sure to keep these the same as SVP64RMModeDecode, in fact,
# TODO, make SVP64RMModeDecode *use* this as a Record!
sv_input_record_layout = [
        ('sv_pred_sz', 1), # predicate source zeroing
        ('sv_pred_dz', 1), # predicate dest zeroing
        ('sv_saturate', SVP64sat),
        ('sv_ldstmode', SVP64LDSTmode),
        ('SV_Ptype', SVPtype),
        #('sv_RC1', 1),
    ]

"""RM Mode
there are four Mode variants, two for LD/ST, one for Branch-Conditional,
and one for everything else
https://libre-soc.org/openpower/sv/svp64/
https://libre-soc.org/openpower/sv/ldst/
https://libre-soc.org/openpower/sv/branches/

LD/ST immed:
00	0	dz els	normal mode (with element-stride)
00	1	dz rsvd	bit-reversed mode
01	inv	CR-bit	Rc=1: ffirst CR sel
01	inv	els RC1	Rc=0: ffirst z/nonz
10	N	dz els	sat mode: N=0/1 u/s
11	inv	CR-bit	Rc=1: pred-result CR sel
11	inv	els RC1	Rc=0: pred-result z/nonz

LD/ST indexed:
00	0	sz dz	normal mode
00	1	rsvd	reserved
01	inv	CR-bit	Rc=1: ffirst CR sel
01	inv	dz RC1	Rc=0: ffirst z/nonz
10	N	sz dz	sat mode: N=0/1 u/s
11	inv	CR-bit	Rc=1: pred-result CR sel
11	inv	dz RC1	Rc=0: pred-result z/nonz

Arithmetic:
00	0	sz dz	normal mode
00	1	dz CRM	reduce mode (mapreduce), SUBVL=1
00	1	SVM CRM	subvector reduce mode, SUBVL>1
01	inv	CR-bit	Rc=1: ffirst CR sel
01	inv	dz RC1	Rc=0: ffirst z/nonz
10	N	sz dz	sat mode: N=0/1 u/s
11	inv	CR-bit	Rc=1: pred-result CR sel
11	inv	dz RC1	Rc=0: pred-result z/nonz

Branch Conditional:
note that additional BC modes are in *other bits*, specifically
the element-width fields: SVP64Rec.ewsrc and SVP64Rec.elwidth

elwidth   ewsrc    mode
4   5     6   7    19 20    21  22  23
ALL LRu   /   /     0  0	/ 	SNZ sz	normal mode
ALL LRu   /   VSb   0  1	VLI	SNZ sz	       VLSET mode
ALL LRu   BRc /     1  0	/ 	SNZ sz	svstep       mode
ALL LRu   BRc VSb   1  1	VLI	SNZ sz	svstep VLSET mode
"""


class SVP64RMModeDecode(Elaboratable):
    def __init__(self, name=None):
        ##### inputs #####
        self.rm_in = SVP64Rec(name=name)
        self.fn_in = Signal(Function) # LD/ST and Branch is different
        self.svp64_vf_in = Signal()  # Vertical-First Mode
        self.ptype_in = Signal(SVPtype)
        self.rc_in = Signal()
        self.ldst_ra_vec = Signal() # set when RA is vec, indicate Index mode
        self.ldst_imz_in = Signal() # set when LD/ST immediate is zero

        ##### outputs #####

        # main mode (normal, reduce, saturate, ffirst, pred-result, branch)
        self.mode = Signal(SVP64RMMode)

        # Branch Conditional Modes
        self.bc_vlset = Signal(SVP64BCVLSETMode) # Branch-Conditional VLSET
        self.bc_step = Signal(SVP64BCStep)   # Branch-Conditional svstep mode
        self.bc_pred = Signal(SVP64BCPredMode) # BC predicate mode
        self.bc_gate = Signal(SVP64BCGate)     # BC ALL or ANY gate
        self.bc_lru  = Signal()                # BC Link Register Update

        # predication
        self.predmode = Signal(SVP64PredMode)
        self.srcpred = Signal(3) # source predicate
        self.dstpred = Signal(3) # destination predicate
        self.pred_sz = Signal(1) # predicate source zeroing
        self.pred_dz = Signal(1) # predicate dest zeroing

        self.saturate = Signal(SVP64sat)
        self.RC1 = Signal()
        self.cr_sel = Signal(2)  # bit of CR to test (index 0-3)
        self.inv = Signal(1)     # and whether it's inverted (like branch BO)
        self.map_evm = Signal(1)
        self.map_crm = Signal(1)
        self.reverse_gear = Signal(1)  # elements to go VL-1..0
        self.ldstmode = Signal(SVP64LDSTmode) # LD/ST Mode (strided type)

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        mode = self.rm_in.mode

        # decode pieces of mode
        is_ldst = Signal()
        is_bc = Signal()
        comb += is_ldst.eq(self.fn_in == Function.LDST)
        comb += is_bc.eq(self.fn_in == Function.BRANCH)
        mode2 = sel(m, mode, SVP64MODE.MOD2)

        with m.If(is_bc):
            # Branch-Conditional is completely different
            # svstep mode
            with m.If(mode2[0]):
                with m.If(self.rm_in.ewsrc[0]):
                    comb += self.bc_step.eq(SVP64BCStep.STEP_RC)
                with m.Else():
                    comb += self.bc_step.eq(SVP64BCStep.STEP)
            # VLSET mode
            with m.If(mode2[1]):
                with m.If(self.rm_in.ewsrc[1]):
                    comb += self.bc_step.eq(SVP64BCVLSETMode.VL_INCL)
                with m.Else():
                    comb += self.bc_step.eq(SVP64BCVLSETMode.VL_EXCL)
            # BC Mode ALL or ANY (Great-Big-AND-gate or Great-Big-OR-gate)
            comb += self.bc_gate.eq(self.rm_in.elwidth[0])
            # Link-Register Update
            comb += self.bc_lru.eq(self.rm_in.elwidth[1])
        with m.Else():
            # combined arith / ldst decoding due to similarity
            with m.Switch(mode2):
                with m.Case(0): # needs further decoding (LDST no mapreduce)
                    with m.If(is_ldst):
                        comb += self.mode.eq(SVP64RMMode.NORMAL)
                    with m.Elif(mode[SVP64MODE.REDUCE]):
                        comb += self.mode.eq(SVP64RMMode.MAPREDUCE)
                    with m.Else():
                        comb += self.mode.eq(SVP64RMMode.NORMAL)
                with m.Case(1):
                    comb += self.mode.eq(SVP64RMMode.FFIRST) # fail-first
                with m.Case(2):
                    comb += self.mode.eq(SVP64RMMode.SATURATE) # saturate
                with m.Case(3):
                    comb += self.mode.eq(SVP64RMMode.PREDRES) # pred result

            # extract "reverse gear" for mapreduce mode
            with m.If((~is_ldst) &                     # not for LD/ST
                        (mode2 == 0) &                 # first 2 bits == 0
                        mode[SVP64MODE.REDUCE] &       # bit 2 == 1
                       (~mode[SVP64MODE.PARALLEL])):   # not parallel mapreduce
                comb += self.reverse_gear.eq(mode[SVP64MODE.RG]) # finally whew

            # extract zeroing
            with m.Switch(mode2):
                with m.Case(0): # needs further decoding (LDST no mapreduce)
                    with m.If(is_ldst):
                        # XXX TODO, work out which of these is most
                        # appropriate set both? or just the one?
                        # or one if LD, the other if ST?
                        comb += self.pred_sz.eq(mode[SVP64MODE.DZ])
                        comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                    with m.Elif(mode[SVP64MODE.REDUCE]):
                        with m.If(self.rm_in.subvl == Const(0, 2)): # no SUBVL
                            comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                    with m.Else():
                        comb += self.pred_sz.eq(mode[SVP64MODE.SZ])
                        comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                with m.Case(1, 3):
                    with m.If(is_ldst):
                        with m.If(~self.ldst_ra_vec):
                            comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                    with m.Elif(self.rc_in):
                        comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                with m.Case(2):
                    with m.If(is_ldst & ~self.ldst_ra_vec):
                        comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                    with m.Else():
                        comb += self.pred_sz.eq(mode[SVP64MODE.SZ])
                        comb += self.pred_dz.eq(mode[SVP64MODE.DZ])

            # extract saturate
            with m.Switch(mode2):
                with m.Case(2):
                    with m.If(mode[SVP64MODE.N]):
                        comb += self.saturate.eq(SVP64sat.UNSIGNED)
                    with m.Else():
                        comb += self.saturate.eq(SVP64sat.SIGNED)
                with m.Default():
                    comb += self.saturate.eq(SVP64sat.NONE)

            # extract els (element strided mode bit)
            # see https://libre-soc.org/openpower/sv/ldst/
            els = Signal()
            with m.If(is_ldst):
                with m.Switch(mode2):
                    with m.Case(0):
                        comb += els.eq(mode[SVP64MODE.ELS_NORMAL])
                    with m.Case(2):
                        comb += els.eq(mode[SVP64MODE.ELS_SAT])
                    with m.Case(1, 3):
                        with m.If(self.rc_in):
                            comb += els.eq(mode[SVP64MODE.ELS_FFIRST_PRED])

                # Shifted Mode
                with m.If(mode[SVP64MODE.LDST_SHIFT]):
                    comb += self.ldstmode.eq(SVP64LDSTmode.SHIFT)
                # RA is vectorised
                with m.Elif(self.ldst_ra_vec):
                    comb += self.ldstmode.eq(SVP64LDSTmode.INDEXED)
                # not element-strided, therefore unit...
                with m.Elif(~els):
                    comb += self.ldstmode.eq(SVP64LDSTmode.UNITSTRIDE)
                # but if the LD/ST immediate is zero, allow cache-inhibited
                # loads from same location, therefore don't do element-striding
                with m.Elif(~self.ldst_imz_in):
                    comb += self.ldstmode.eq(SVP64LDSTmode.ELSTRIDE)

        # extract src/dest predicate.  use EXTRA3.MASK because EXTRA2.MASK
        # is in exactly the same bits
        srcmask = sel(m, self.rm_in.extra, EXTRA3.MASK)
        dstmask = self.rm_in.mask
        with m.If(self.ptype_in == SVPtype.P2):
            comb += self.srcpred.eq(srcmask)
        with m.Else():
            comb += self.srcpred.eq(dstmask)
        comb += self.dstpred.eq(dstmask)

        # identify predicate mode
        with m.If(self.rm_in.mmode == 1):
            comb += self.predmode.eq(SVP64PredMode.CR) # CR Predicate
        with m.Elif((self.srcpred == 0) & (self.dstpred == 0)):
            comb += self.predmode.eq(SVP64PredMode.ALWAYS) # No predicate
        with m.Else():
            comb += self.predmode.eq(SVP64PredMode.INT) # non-zero src: INT

        # TODO: detect zeroing mode, saturation mode, a few more.

        return m

