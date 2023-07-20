from openpower.insndb.asm import SVP64Asm
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.test.state import ExpectedState
from nmutil.sim_util import hash_256
import math
from fractions import Fraction


class MADDSUBRSTestCase(TestAccumulatorBase):
    def case_0_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,14,11"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[10] = 0x0000e6b8
        initial_regs[11] = 0x00002d41

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x0000aa86
        e.intregs[2] = 0xffffffffffff643e
        e.intregs[10] = 0x0000e6b8
        e.intregs[11] = 0x00002d41
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,0,11"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[10] = 0x0000e6b8
        initial_regs[11] = 0x00002d41

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x2aa17069
        e.intregs[2] = 0xffffffffd90f96f9
        e.intregs[10] = 0x0000e6b8
        e.intregs[11] = 0x00002d41
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,2,11"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x100000000
        initial_regs[10] = 0x000000003
        initial_regs[11] = 0x10000000

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x40000000c000000
        e.intregs[2] = 0x3fffffff4000000
        e.intregs[10] = 0x00000003
        e.intregs[11] = 0x10000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_3_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,16,11"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x100000000
        initial_regs[10] = 0x000000003
        initial_regs[11] = 0x10000000

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x100000003000
        e.intregs[2] = 0x0fffffffd000
        e.intregs[10] = 0x00000003
        e.intregs[11] = 0x10000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_4_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,1,11"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x100000000
        initial_regs[10] = 0x000000003
        initial_regs[11] = 0xff0000000

        e = ExpectedState(pc=4)
        e.intregs[1] = 0xf8000017e8000000
        e.intregs[2] = 0xf7ffffe818000000
        e.intregs[10] = 0x000000003
        e.intregs[11] = 0xff0000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_maddsubrs_16bit_s14(self):
        p = Program(list(SVP64Asm([
            "sv.maddsubrs/w=16 *10,*20,14,*30",
        ])), bigendian)

        initial_regs = [0] * 32

        # use somewhat reasonable i16 values since we're working in
        # 2.14-bit fixed-point

        initial_regs[10] = 0x1000_2000_3000_4000  # 0x0.4, 0x0.8, 0x0.c, 0x1.0

        # 0x0.48d0, -0x0.0490, 0x0.d158, -0x0.48d4
        initial_regs[20] = 0x1234_fedc_3456_edcb
        cospi_16_64 = 11585  # from libvpx -- 0x0.b504 ~ 0.70709 ~ cos(pi/4)
        initial_regs[30] = cospi_16_64 * 0x1_0001_0001_0001  # splat 4x

        svstate = SVP64State()
        svstate.vl = 4
        svstate.maxvl = 4

        e = ExpectedState(pc=8, int_regs=initial_regs)
        e.intregs[10] = 0
        e.intregs[11] = 0
        for i in range(svstate.vl):
            rt = (initial_regs[10] >> (i * 16)) & 0xFFFF  # extract element
            rt -= (rt & 0x8000) << 1  # sign extend rt
            ra = (initial_regs[20] >> (i * 16)) & 0xFFFF
            ra -= (ra & 0x8000) << 1  # sign extend ra
            rb = (initial_regs[30] >> (i * 16)) & 0xFFFF
            rb -= (rb & 0x8000) << 1  # sign extend rb
            s = rt + ra
            d = rt - ra
            # f64 is big enough to represent all relevant values exactly,
            # so we can use float
            rt = math.floor((s * rb) / (2 ** 14) + 0.5)  # mul & round & shr
            rs = math.floor((d * rb) / (2 ** 14) + 0.5)
            e.intregs[10] |= (rt & 0xFFFF) << (16 * i)  # insert element
            e.intregs[11] |= (rs & 0xFFFF) << (16 * i)

        # asserts so you can read the expected values
        assert e.intregs[10] == 0x182f_15d2_46f2_2061
        assert e.intregs[11] == 0xfe71_176f_fcef_3a21

        self.add_case(p, initial_regs, expected=e, initial_svstate=svstate)

    def maddsubrs_many_helper(self, width, shift, prog, case_idx):
        # if {'width': width, 'shift': shift, 'case_idx': case_idx} \
        #         != {'width': 8, 'shift': 1, 'case_idx': 0}:
        #     return  # for debugging
        gprs = [0] * 32
        # make some reproducible random inputs
        k = f"maddsubrs {width} {shift} {case_idx}"
        gprs[10] = hash_256(k + " r10") % 2**64
        gprs[20] = hash_256(k + " r20") % 2**64
        gprs[30] = hash_256(k + " r30") % 2**64

        svstate = SVP64State()
        svstate.vl = 64 // width  # one full 64-bit register
        svstate.maxvl = 64 // width

        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[10] = 0
        e.intregs[11] = 0
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
            s = rt + ra
            d = rt - ra
            factor = Fraction(1, 2 ** shift)  # shr factor
            round_up = Fraction(1, 2)
            # mul & round & shr
            rt = math.floor((s * rb) * factor + round_up)
            rs = math.floor((d * rb) * factor + round_up)
            # insert elements
            e.intregs[10] |= (rt % 2 ** width) << (width * i)
            e.intregs[11] |= (rs % 2 ** width) << (width * i)

        with self.subTest(
            width=width, shift=shift, case_idx=case_idx,
            RT_in=hex(gprs[10]), RA_in=hex(gprs[20]), RB_in=hex(gprs[30]),
            expected_RT=hex(e.intregs[10]), expected_RS=hex(e.intregs[11]),
        ):
            self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_maddsubrs_many(self):
        for width in 8, 16, 32, 64:
            shift_end = min(32, width)
            for shift in range(0, shift_end, shift_end // 8):
                w = "" if width == 64 else f"/w={width}"
                prog = Program(list(SVP64Asm([
                    f"sv.maddsubrs{w} *10,*20,{shift},*30",
                ])), bigendian)

                for case_idx in range(25):
                    self.maddsubrs_many_helper(width, shift, prog, case_idx)

    def case_0_maddrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,0,11",
                        "maddrs 1,10,0,12"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[10] = 0x0000e6b8
        initial_regs[11] = 0x00002d41
        initial_regs[12] = 0x00000d00

        e = ExpectedState(pc=8)
        e.intregs[1] = 0x3658c869
        e.intregs[2] = 0xffffffffcd583ef9
        e.intregs[10] = 0x0000e6b8
        e.intregs[11] = 0x00002d41
        e.intregs[12] = 0x00000d00
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_maddrs(self):
        isa = SVP64Asm(["maddsubrs 1,10,0,11",
                        "maddrs 1,10,14,12"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[10] = 0x0000e6b8
        initial_regs[11] = 0x00002d41
        initial_regs[12] = 0x00000d00

        e = ExpectedState(pc=8)
        e.intregs[1] = 0x0000d963
        e.intregs[2] = 0xffffffffffff3561
        e.intregs[10] = 0x0000e6b8
        e.intregs[11] = 0x00002d41
        e.intregs[12] = 0x00000d00
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def maddrs_many_helper(self, width, shift, prog, case_idx):
        # if {'width': width, 'shift': shift, 'case_idx': case_idx} \
        #         != {'width': 8, 'shift': 1, 'case_idx': 0}:
        #     return  # for debugging
        gprs = [0] * 32
        # make some reproducible random inputs
        k = f"maddrs {width} {shift} {case_idx}"
        gprs[10] = hash_256(k + " r10") % 2**64
        gprs[11] = hash_256(k + " r11") % 2**64
        gprs[20] = hash_256(k + " r20") % 2**64
        gprs[30] = hash_256(k + " r30") % 2**64

        svstate = SVP64State()
        svstate.vl = 64 // width  # one full 64-bit register
        svstate.maxvl = 64 // width

        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[10] = 0
        e.intregs[11] = 0
        for i in range(svstate.vl):
            # extract elements
            rt = (gprs[10] >> (i * width)) % 2 ** width
            rs = (gprs[11] >> (i * width)) % 2 ** width
            ra = (gprs[20] >> (i * width)) % 2 ** width
            rb = (gprs[30] >> (i * width)) % 2 ** width
            if rt >= 2 ** (width - 1):
                rt -= 2 ** width  # sign extend rt
            if rs >= 2 ** (width - 1):
                rs -= 2 ** width  # sign extend rs
            if ra >= 2 ** (width - 1):
                ra -= 2 ** width  # sign extend ra
            if rb >= 2 ** (width - 1):
                rb -= 2 ** width  # sign extend rb
            prod = rb * ra
            rt += prod
            rs -= prod
            factor = Fraction(1, 2 ** shift)  # shr factor
            round_up = Fraction(1, 2)
            # round & shr
            rt = math.floor(rt * factor + round_up)
            rs = math.floor(rs * factor + round_up)
            # insert elements
            e.intregs[10] |= (rt % 2 ** width) << (width * i)
            e.intregs[11] |= (rs % 2 ** width) << (width * i)

        with self.subTest(
            width=width, shift=shift, case_idx=case_idx,
            RT_in=hex(gprs[10]), RS_in=hex(gprs[11]),
            RA_in=hex(gprs[20]), RB_in=hex(gprs[30]),
            expected_RT=hex(e.intregs[10]), expected_RS=hex(e.intregs[11]),
        ):
            self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_maddrs_many(self):
        for width in 8, 16, 32, 64:
            shift_end = min(32, width)
            for shift in range(0, shift_end, shift_end // 8):
                w = "" if width == 64 else f"/w={width}"
                prog = Program(list(SVP64Asm([
                    f"sv.maddrs{w} *10,*20,{shift},*30",
                ])), bigendian)

                for case_idx in range(25):
                    self.maddrs_many_helper(width, shift, prog, case_idx)
