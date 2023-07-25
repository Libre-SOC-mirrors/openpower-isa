from openpower.insndb.asm import SVP64Asm
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.test.state import ExpectedState
from nmutil.sim_util import hash_256
import math
from fractions import Fraction


class MADDRSTestCase(TestAccumulatorBase):
    def case_0_maddrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,11,0",
                        "maddrs 1,10,12,0",
                        "msubrs 2,10,12,0"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[10] = 0x0000e6b8
        initial_regs[11] = 0x00002d41
        initial_regs[12] = 0x00000d00

        e = ExpectedState(pc=12)
        e.intregs[1] = 0x3658c869
        e.intregs[2] = 0xffffffffcd583ef9
        e.intregs[10] = 0x0000e6b8
        e.intregs[11] = 0x00002d41
        e.intregs[12] = 0x00000d00
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_maddrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,11,0",
                        "maddrs 1,10,12,14",
                        "msubrs 2,10,12,14"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[10] = 0x0000e6b8
        initial_regs[11] = 0x00002d41
        initial_regs[12] = 0x00000d00

        e = ExpectedState(pc=12)
        e.intregs[1] = 0x0000d963
        e.intregs[2] = 0xffffffffffff3561
        e.intregs[10] = 0x0000e6b8
        e.intregs[11] = 0x00002d41
        e.intregs[12] = 0x00000d00
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def maddrs_many_helper(self, width, shift, prog, case_idx, isaddrs):
        # if {'width': width, 'shift': shift, 'case_idx': case_idx} \
        #         != {'width': 8, 'shift': 1, 'case_idx': 0}:
        #     return  # for debugging
        gprs = [0] * 32
        # make some reproducible random inputs
        k = f"maddrs {width} {shift} {case_idx}"
        gprs[10] = hash_256(k + " r10") % 2**64
        gprs[20] = hash_256(k + " r20") % 2**64
        gprs[30] = hash_256(k + " r30") % 2**64

        svstate = SVP64State()
        svstate.vl = 64 // width  # one full 64-bit register
        svstate.maxvl = 64 // width

        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[10] = 0
        for i in range(svstate.vl):
            # extract elements
            rt = (gprs[10] >> (i * width)) % 2 ** width
            ra = (gprs[20] >> (i * width)) % 2 ** width
            rb = (gprs[30] >> (i * width)) % 2 ** width
            if rt >= 2 ** (width - 1):
                rt -= 2 ** width  # sign extend rt
            if ra >= 2 ** (width - 1):
                ra -= 2 ** width  # sign extend ra
            if rb >= 2 ** (width - 1):
                rb -= 2 ** width  # sign extend rb
            prod = rb * ra
            if (isaddrs):
                rt += prod
            else:
                rt -= prod
            factor = Fraction(1, 2 ** shift)  # shr factor
            round_up = Fraction(1, 2)
            # round & shr
            rt = math.floor(rt * factor + round_up)
            # insert elements
            e.intregs[10] |= (rt % 2 ** width) << (width * i)

        with self.subTest(
            width=width, shift=shift, case_idx=case_idx,
            RT_in=hex(gprs[10]), RA_in=hex(gprs[20]), RB_in=hex(gprs[30]),
            expected_RT=hex(e.intregs[10])):
            self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_maddrs_many(self):
        for width in 8, 16, 32, 64:
            shift_end = min(32, width)
            for shift in range(0, shift_end, shift_end // 8):
                w = "" if width == 64 else f"/w={width}"
                prog = Program(list(SVP64Asm([
                    f"sv.maddrs{w} *10,*20,*30,{shift}",
                ])), bigendian)

                for case_idx in range(25):
                    self.maddrs_many_helper(width, shift, prog, case_idx, 1)

    def case_msubrs_many(self):
        for width in 8, 16, 32, 64:
            shift_end = min(32, width)
            for shift in range(0, shift_end, shift_end // 8):
                w = "" if width == 64 else f"/w={width}"
                prog = Program(list(SVP64Asm([
                    f"sv.msubrs{w} *10,*20,*30,{shift}",
                ])), bigendian)

                for case_idx in range(25):
                    self.maddrs_many_helper(width, shift, prog, case_idx, 0)
