# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl

# sigh this entire module is a laborious mess. it really should be
# auto-generated from the insndb/types.py database but a technique
# for doing so (similar to python HTML/XML-node-walking) is needed

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
from openpower.decoder.power_enums import (SVP64RMMode, Function, SVPType,
                                    SVMode,
                                    SVP64PredMode, SVP64Sat, SVP64LDSTmode,
                                    SVP64BCPredMode, SVP64BCVLSETMode,
                                    SVP64BCGate, SVP64BCCTRMode,
                                    SVP64Width
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
        ('sv_saturate', SVP64Sat),
        ('sv_ldstmode', SVP64LDSTmode),
        ('SV_Ptype', SVPType),
        ('SV_mode', SVMode),
        #('sv_RC1', 1),
    ]

"""RM Mode
there are five Mode variants, two for LD/ST, one for Branch-Conditional,
and one for everything else
https://libre-soc.org/openpower/sv/svp64/
https://libre-soc.org/openpower/sv/ldst/
https://libre-soc.org/openpower/sv/branches/
https://libre-soc.org/openpower/sv/crops/

LD/ST immed:

| 0 | 1 |  2  |  3   4  |  description               |
|---|---| --- |---------|--------------------------- |
|els| 0 | PI  |  zz LF | simple mode                |
|VLi| 1 | inv | CR-bit  | ffirst CR sel             |

LD/ST indexed:

| 0 | 1 |  2  |  3   4  |  description               |
|---|---| --- |---------|--------------------------- |
|els| 0 | PI  |  zz SEA | simple mode        |
|VLi| 1 | inv | CR-bit  | ffirst CR sel        |

Arithmetic:

| 0-1    |  2  |  3   4  |  description                     |
| ------ | --- |---------|----------------------------------|
| 0   0  |   0 |  dz  sz | simple mode                      |
| 0   0  |   1 |  RG  0  | scalar reduce mode (mapreduce)   |
| 0   0  |   1 |  /   1  | reserved                         |
| 1   0  |   N | dz   sz |  sat mode: N=0/1 u/s             |
| VLi 1  | inv | CR-bit  | Rc=1: ffirst CR sel              |
| VLi 1  | inv | zz RC1  | Rc=0: ffirst z/nonz              |

CROps:

|6 | 7 |19:20|21 | 22:23   |  description     |
|--|---|-----|---|---------|------------------|
|/ | / |0  0 |RG | dz  sz  | simple mode                      |
|/ | / |1  0 |RG | dz  sz  | scalar reduce mode (mapreduce) |
|zz|SNZ|VLI 1|inv|  CR-bit | Ffirst 3-bit mode      |
|/ |SNZ|VLI 1|inv|  dz sz  | Ffirst 5-bit mode (implies CR-bit from result) |

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
        self.sv_mode = Signal(SVMode) # BRANCH/LDST_IMM/CROP etc.
        self.svp64_vf_in = Signal()  # Vertical-First Mode
        self.ptype_in = Signal(SVPType)
        self.rc_in = Signal()
        self.cr_5bit_in = Signal()  # if CR field was 5-bit
        self.cr_2bit_in = Signal()  # bottom 2 bits of CR field
        self.ldst_ra_vec = Signal() # set when RA is vec, indicate Index mode
        self.ldst_imz_in = Signal() # set when LD/ST immediate is zero
        self.ldst_postinc = Signal() # set when LD/ST immediate post-inc set
        self.ldst_ffirst = Signal() # set when LD/ST immediate fail-first set

        ##### outputs #####

        # main mode (normal, reduce, saturate, ffirst, pred-result, branch)
        self.mode = Signal(SVP64RMMode)

        # Branch Conditional Modes
        self.bc_vlset = Signal(SVP64BCVLSETMode) # Branch-Conditional VLSET
        self.bc_ctrtest = Signal(SVP64BCCTRMode) # Branch-Conditional CTR-Test
        self.bc_pred = Signal(SVP64BCPredMode) # BC predicate mode
        self.bc_vsb = Signal()                 # BC VLSET-branch (like BO[1])
        self.bc_gate = Signal(SVP64BCGate)     # BC ALL or ANY gate
        self.bc_lru  = Signal()                # BC Link Register Update

        # predication
        self.predmode = Signal(SVP64PredMode)
        self.srcpred = Signal(3) # source predicate
        self.dstpred = Signal(3) # destination predicate
        self.pred_sz = Signal(1) # predicate source zeroing
        self.pred_dz = Signal(1) # predicate dest zeroing

        # Modes n stuff
        self.ew_src = Signal(SVP64Width) # source elwidth
        self.ew_dst = Signal(SVP64Width) # dest elwidth
        self.subvl= Signal(2) # subvl
        self.saturate = Signal(SVP64Sat)
        self.RC1 = Signal()
        self.vli = Signal()
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
        is_cr = Signal()
        is_ldstimm = Signal()
        comb += is_ldst.eq(self.fn_in == Function.LDST)
        comb += is_bc.eq(self.fn_in == Function.BRANCH) # XXX TODO use SV Mode
        comb += is_cr.eq(self.sv_mode == SVMode.CROP.value)
        comb += is_ldstimm.eq(self.sv_mode == SVMode.LDST_IMM.value)
        mode2 = sel(m, mode, SVP64MODE.MOD2)
        cr = sel(m, mode, SVP64MODE.CR)

        #####################
        # Branch-Conditional decoding
        #####################
        with m.If(is_bc):
            # Counter-Test Mode.
            with m.If(mode[SVP64MODE.BC_CTRTEST]):
                with m.If(self.rm_in.ewsrc[1]):
                    comb += self.bc_ctrtest.eq(SVP64BCCTRMode.TEST_INV)
                with m.Else():
                    comb += self.bc_ctrtest.eq(SVP64BCCTRMode.TEST)

            # BC Mode ALL or ANY (Great-Big-AND-gate or Great-Big-OR-gate)
            comb += self.bc_gate.eq(self.rm_in.elwidth[1])
            # Link-Register Update
            comb += self.bc_lru.eq(self.rm_in.elwidth[0])
            comb += self.bc_vsb.eq(self.rm_in.ewsrc[0])

        #####################
        # CRops decoding
        #####################
        with m.Elif(is_cr):
            with m.Switch(mode2):
                with m.Case(0, 2): # needs further decoding (LDST no mapreduce)
                    with m.If(mode[SVP64MODE.REDUCE]):
                        comb += self.mode.eq(SVP64RMMode.MAPREDUCE)
                    with m.Else():
                        comb += self.mode.eq(SVP64RMMode.NORMAL)
                with m.Case(1,3):
                    comb += self.mode.eq(SVP64RMMode.FFIRST) # fail-first

            # extract failfirst
            with m.If(self.mode == SVP64RMMode.FFIRST): # fail-first
                comb += self.inv.eq(mode[SVP64MODE.INV])
                comb += self.vli.eq(mode[SVP64MODE.VLI])
                with m.If(self.cr_5bit_in):
                    comb += self.cr_sel.eq(0b10) # EQ bit index is implicit
                with m.Else():
                    comb += self.cr_sel.eq(cr)

        #####################
        # LDST decoding (both Idx and Imm - should be separate)
        #####################
        with m.Elif(is_ldst):
            with m.Switch(mode2):
                with m.Case(0, 2): # needs further decoding (LDST no mapreduce)
                    comb += self.mode.eq(SVP64RMMode.NORMAL)
                    comb += self.ldst_postinc.eq(mode[SVP64MODE.LDI_PI])
                    comb += self.ldst_ffirst.eq(mode[SVP64MODE.LDI_FF])
                with m.Case(1, 3):
                    comb += self.mode.eq(SVP64RMMode.FFIRST) # ffirst

            # extract zeroing
            with m.If(is_ldst & ~is_ldstimm): # LDST-Indexed
                with m.Switch(mode2):
                    with m.Case(0,2):
                            # sz/dz only when mode2[0] = 0
                            comb += self.pred_sz.eq(mode[SVP64MODE.DZ])
                            comb += self.pred_dz.eq(mode[SVP64MODE.DZ])

            with m.Elif(is_ldstimm): # LDST-Immediate
                with m.Switch(mode2):
                    with m.Case(0,2):  # simple mode
                        # use zz
                        comb += self.pred_sz.eq(mode[SVP64MODE.ZZ])
                        comb += self.pred_dz.eq(mode[SVP64MODE.ZZ])

            # extract failfirst
            with m.If(self.mode == SVP64RMMode.FFIRST): # fail-first
                comb += self.inv.eq(mode[SVP64MODE.INV])
                with m.If(is_ldst):
                    comb += self.vli.eq(mode[SVP64MODE.LDST_VLI])
                with m.If(self.rc_in):
                    comb += self.cr_sel.eq(cr)
                with m.Else():
                    # only when Rc=0
                    comb += self.RC1.eq(mode[SVP64MODE.RC1])
                    with m.If(~is_ldst):
                        comb += self.vli.eq(mode[SVP64MODE.VLI])
                    comb += self.cr_sel.eq(0b10) # EQ bit index is implicit

            # extract saturate
            with m.Switch(mode2):
                with m.Case(2):
                    with m.If(mode[SVP64MODE.N]):
                        comb += self.saturate.eq(SVP64Sat.UNSIGNED)
                    with m.Else():
                        comb += self.saturate.eq(SVP64Sat.SIGNED)
                with m.Default():
                    comb += self.saturate.eq(SVP64Sat.NONE)

            # do elwidth/elwidth_src extract
            comb += self.ew_src.eq(self.rm_in.ewsrc)
            comb += self.ew_dst.eq(self.rm_in.elwidth)
            comb += self.subvl.eq(self.rm_in.subvl)

            # extract els (element strided mode bit)
            # see https://libre-soc.org/openpower/sv/ldst/
            els = Signal()
            with m.Switch(mode2):
                with m.Case(0, 2):
                    comb += els.eq(mode[SVP64MODE.LDST_ELS])
                with m.Case(1, 3):
                    with m.If(self.rc_in):
                        comb += els.eq(mode[SVP64MODE.ELS_FFIRST_PRED])

            # RA is vectorised
            with m.If(self.ldst_ra_vec):
                comb += self.ldstmode.eq(SVP64LDSTmode.INDEXED)
            # not element-strided, therefore unit...
            with m.Elif(~els):
                comb += self.ldstmode.eq(SVP64LDSTmode.UNITSTRIDE)
            # but if the LD/ST immediate is zero, allow cache-inhibited
            # loads from same location, therefore don't do element-striding
            with m.Elif(~self.ldst_imz_in):
                comb += self.ldstmode.eq(SVP64LDSTmode.ELSTRIDE)

        ######################
        # arith decoding
        ######################
        with m.Else():
            with m.Switch(mode2):
                with m.Case(0): # needs further decoding (LDST no mapreduce)
                    with m.If(mode[SVP64MODE.REDUCE]):
                        comb += self.mode.eq(SVP64RMMode.MAPREDUCE)
                    with m.Else():
                        comb += self.mode.eq(SVP64RMMode.NORMAL)
                with m.Case(1,3):
                    comb += self.mode.eq(SVP64RMMode.FFIRST) # ffirst
                with m.Case(2):
                    comb += self.mode.eq(SVP64RMMode.SATURATE) # saturate

            # extract "reverse gear" for mapreduce mode
            with m.If((~is_ldst) &                     # not for LD/ST
                        (mode2 == 0) &                 # first 2 bits == 0
                        mode[SVP64MODE.REDUCE] &       # bit 2 == 1
                       (~mode[SVP64MODE.MOD3])):       # bit 3 == 0
                comb += self.reverse_gear.eq(mode[SVP64MODE.RG]) # finally whew

            # extract zeroing
            with m.Switch(mode2):
                with m.Case(0):
                    # normal-mode only active in simple mode
                    with m.If(~mode[SVP64MODE.REDUCE]): # bit 2 is zero?
                        comb += self.pred_sz.eq(mode[SVP64MODE.SZ])
                        comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                with m.Case(2):
                    # sat-mode all good...
                    comb += self.pred_sz.eq(mode[SVP64MODE.SZ])
                    comb += self.pred_dz.eq(mode[SVP64MODE.DZ])
                with m.Case(3):
                    # predicate-result has ZZ
                    with m.If(self.rc_in):
                        comb += self.pred_sz.eq(mode[SVP64MODE.ZZ])
                        comb += self.pred_dz.eq(mode[SVP64MODE.ZZ])

            # extract failfirst
            with m.If(self.mode == SVP64RMMode.FFIRST): # fail-first
                comb += self.inv.eq(mode[SVP64MODE.INV])
                with m.If(self.rc_in):
                    comb += self.cr_sel.eq(cr)
                with m.Else():
                    # only when Rc=0
                    comb += self.RC1.eq(mode[SVP64MODE.RC1])
                    with m.If(~is_ldst):
                        comb += self.vli.eq(mode[SVP64MODE.VLI])
                    comb += self.cr_sel.eq(0b10) # EQ bit index is implicit

            # extract saturate
            with m.Switch(mode2):
                with m.Case(2):
                    with m.If(mode[SVP64MODE.N]):
                        comb += self.saturate.eq(SVP64Sat.UNSIGNED)
                    with m.Else():
                        comb += self.saturate.eq(SVP64Sat.SIGNED)
                with m.Default():
                    comb += self.saturate.eq(SVP64Sat.NONE)

            # do elwidth/elwidth_src extract
            comb += self.ew_src.eq(self.rm_in.ewsrc)
            comb += self.ew_dst.eq(self.rm_in.elwidth)
            comb += self.subvl.eq(self.rm_in.subvl)

        ######################
        # Common fields (not many, sigh)
        ######################

        # extract src/dest predicate.  use EXTRA3.MASK because EXTRA2.MASK
        # is in exactly the same bits
        srcmask = sel(m, self.rm_in.extra, EXTRA3.MASK)
        dstmask = self.rm_in.mask
        with m.If(self.ptype_in == SVPType.P2):
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

        return m

