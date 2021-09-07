from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.isa.test_runner import run_tst


class DecoderTestCase(FHDLTestCase):

    def test_0_proof_regression_rlwnm(self):
        lst = ["rlwnm 3, 1, 2, 16, 20"]
        initial_regs = [0] * 32
        #initial_regs[1] =0x7ffdbffb91b906b9
        initial_regs[1] = 0x11faafff1111aa11
        #initial_regs[2] = 31
        initial_regs[2] = 11
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x8800, 64))

    def test_case_srw_1(self):
        lst = ["sraw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x12345678
        initial_regs[2] = 8
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x123456, 64))

    def test_case_srw_2(self):
        lst = ["sraw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x82345678  # test the carry
        initial_regs[2] = 8
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xffffffffff823456, 64))

    def test_case_sld_rb_too_big(self):
        lst = ["sld 3, 1, 4",
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        initial_regs[4] = 64  # too big, output should be zero
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0, 64))

    def test_case_sld_rb_is_zero(self):
        lst = ["sld 3, 1, 4"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x8000000000000000
        initial_regs[4] = 0  # no shift; output should equal input
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(initial_regs[1], 64))

    def test_case_shift_once(self):
        lst = ["slw 3, 1, 4",
               "slw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x80000000
        initial_regs[2] = 0x40
        initial_regs[4] = 0x00
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(1), SelectableInt(initial_regs[1], 64))

    def test_case_rlwinm_1(self):
        lst = ["rlwinm 3, 1, 1, 31, 31"]  # Extracts sign bit
        initial_regs = [0] * 32
        initial_regs[1] = 0x8fffffff
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(1, 64))

    def test_case_rlwinm_2(self):
        lst = ["rlwinm 3, 1, 1, 0, 30"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xf1110001
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xe2220002, 64))

    def test_case_rlwinm_3(self):
        lst = ["rlwinm 3, 1, 0, 16, 31"]  # Clear high-order 16 bits
        initial_regs = [0] * 32
        initial_regs[1] = 0xebeb1888
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x1888, 64))

    def test_case_rlwimi_1(self):
        lst = ["rlwimi 3, 1, 31, 0, 0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x1
        initial_regs[3] = 0x7fffffff
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xffffffff, 64))

    def test_case_rlwimi_2(self):
        lst = ["rlwimi 3, 1, 16, 8, 15"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xcc
        initial_regs[3] = 0x7f00ffff
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x7fccffff, 64))

    def test_case_rlwnm_1(self):
        lst = ["rlwnm 3, 1, 2, 0, 31"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x111
        initial_regs[2] = 1
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x222, 64))

    def test_case_rlwnm_2(self):
        lst = ["rlwnm 3, 1, 2, 8, 11"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xfebaacda
        initial_regs[2] = 16
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xd00000, 64))

    def test_case_rldic_1(self):
        lst = ["rldic 3, 1, 8, 31"]  # Simple rotate and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffff00000111
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x11100, 64))

    def test_case_rldic_2(self):
        lst = ["rldic 3, 1, 0, 51"]  # No rotate and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffff00000fff
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xfff, 64))

    def test_case_rldicl_1(self):
        lst = ["rldicl 3, 1, 8, 44"]  # Simple rotate with left clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffff00000111
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x11101, 64))

    def test_case_rldicl_2(self):
        lst = ["rldicl 3, 1, 32, 47"]  # Rotate right and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x1000dead0000111c
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xdead, 64))

    def test_case_rldicr_1(self):
        lst = ["rldicr 3, 1, 16, 15"]  # Simple rotate with right clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x0100ffffe0000111
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xffff000000000000, 64))

    def test_case_rldicr_2(self):
        lst = ["rldicr 3, 1, 32, 32"]  # Rotate right and clear
        initial_regs = [0] * 32
        initial_regs[1] = 0x1000caef0000dead
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xdead00000000, 64))

    def test_case_regression_extswsli_1(self):
        lst = [f"extswsli 3, 1, 31"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x2b3c00000000, 64))

    def test_case_regression_extswsli_2(self):
        lst = [f"extswsli 3, 1, 7"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3ffffd7377f19fdd
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0x3bf8cfee80, 64))

    def test_case_regression_extswsli_3(self):
        lst = [f"extswsli 3, 1, 0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0000010180122900
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), SelectableInt(0xffffffff80122900, 64))

    def run_tst_program(self, prog, initial_regs=[0] * 32, initial_mem=None):
        simulator = run_tst(prog, initial_regs, mem=initial_mem)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
