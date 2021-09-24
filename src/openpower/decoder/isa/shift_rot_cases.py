from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
import unittest
from openpower.decoder.power_enums import XER_bits
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.test.state import ExpectedState


class ShiftRotTestCase(TestAccumulatorBase):

    def case_0_proof_regression_rlwnm(self):
        lst = ["rlwnm 3, 1, 2, 16, 20"]
        initial_regs = [0] * 32
        #initial_regs[1] =0x7ffdbffb91b906b9
        initial_regs[1] = 0x11faafff1111aa11
        #initial_regs[2] = 31
        initial_regs[2] = 11
        # set expected (intregs, pc, [crregs], so, ov, ca)
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x8800
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_srw_1(self):
        lst = ["sraw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x12345678
        initial_regs[2] = 8
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x123456
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_srw_2(self):
        lst = ["sraw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x82345678  # test the carry
        initial_regs[2] = 8
        e = ExpectedState(initial_regs, 4, ca=3)
        e.intregs[3] = 0xffffffffff823456
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_sld_rb_too_big(self):
        lst = ["sld 3, 1, 4"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        initial_regs[4] = 64  # too big, output should be zero
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x0
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_sld_rb_is_zero(self):
        lst = ["sld 3, 1, 4"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x8000000000000000
        initial_regs[4] = 0  # no shift; output should equal input
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = initial_regs[1]
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_shift_once(self):
        lst = ["slw 3, 1, 4",
               "slw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x80000000
        initial_regs[2] = 0x40
        initial_regs[4] = 0x00
        e = ExpectedState(initial_regs, 8)
        e.intregs[3] = 0x80000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwinm_1(self):
        lst = ["rlwinm 3, 1, 1, 31, 31"]  # Extracts sign bit
        initial_regs = [0] * 32
        initial_regs[1] = 0x8fffffff
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x1
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwinm_2(self):
        lst = ["rlwinm 3, 1, 1, 0, 30"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xf1110001
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xe2220002
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwinm_3(self):
        lst = ["rlwinm 3, 1, 0, 16, 31"]  # Clear high-order 16 bits
        initial_regs = [0] * 32
        initial_regs[1] = 0xebeb1888
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x1888
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwimi_1(self):
        lst = ["rlwimi 3, 1, 31, 0, 0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x1
        initial_regs[3] = 0x7fffffff
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xffffffff
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwimi_2(self):
        lst = ["rlwimi 3, 1, 16, 8, 15"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xcc
        initial_regs[3] = 0x7f00ffff
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x7fccffff
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwnm_1(self):
        lst = ["rlwnm 3, 1, 2, 0, 31"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x111
        initial_regs[2] = 1
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x222
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rlwnm_2(self):
        lst = ["rlwnm 3, 1, 2, 8, 11"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xfebaacda
        initial_regs[2] = 16
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xd00000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rldic_1(self):
        lst = ["rldic 3, 1, 8, 31"]  # Simple rotate and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffff00000111
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x11100
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rldic_2(self):
        lst = ["rldic 3, 1, 0, 51"]  # No rotate and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffff00000fff
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xfff
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rldicl_1(self):
        lst = ["rldicl 3, 1, 8, 44"]  # Simple rotate with left clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffff00000111
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x11101
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rldicl_2(self):
        lst = ["rldicl 3, 1, 32, 47"]  # Rotate right and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x1000dead0000111c
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xdead
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rldicr_1(self):
        lst = ["rldicr 3, 1, 16, 15"]  # Simple rotate with right clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffffe0000111
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xffff000000000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rldicr_2(self):
        lst = ["rldicr 3, 1, 32, 32"]  # Rotate right and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x1000caef0000dead
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xdead00000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_regression_extswsli_1(self):
        lst = [f"extswsli 3, 1, 31"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x2b3c00000000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_regression_extswsli_2(self):
        lst = [f"extswsli 3, 1, 7"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3ffffd7377f19fdd
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0x3bf8cfee80
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_regression_extswsli_3(self):
        lst = [f"extswsli 3, 1, 0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0000010180122900
        e = ExpectedState(initial_regs, 4)
        e.intregs[3] = 0xffffffff80122900
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)
