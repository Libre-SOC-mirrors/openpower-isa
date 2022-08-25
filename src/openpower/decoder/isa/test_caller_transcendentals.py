from nmigen import Module, Signal
from nmigen.sim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, SVP64State
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA
from openpower.decoder.isa.test_caller import Register, run_tst
from copy import deepcopy
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isafunctions.double2single import ISACallerFnHelper

# really bad hack.  need to access the DOUBLE2SINGLE function auto-generated
# from pseudo-code.
fph = ISACallerFnHelper(XLEN=64)


import math

class FPTranscendentalsTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected_int, expected_fpr):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))
        for i in range(32):
            self.assertEqual(sim.fpr(i), SelectableInt(expected_fpr[i], 64))

    def tst_fp_sins_coss(self):
        """>>> lst = ["fsins 1, 2",
                      "fcoss 3, 2",
                     ]
        """
        lst = SVP64Asm(["fsins 1, 2",
                        "fcoss 3, 2",
                     ])
        lst = list(lst)

        with Program(lst, bigendian=False) as program:
            fprs = [0] * 32
            for i in range(-8, 9):
                a = math.pi * (i / 8.0) * 2.0
                fprs[2] = fp64toselectable(a)
                t = math.sin(a)
                u = math.cos(a)
                a1 = fp64toselectable(a) # convert to Power single
                t = fph.DOUBLE2SINGLE(fp64toselectable(t)) # to Power single
                u = fph.DOUBLE2SINGLE(fp64toselectable(u)) # to Power single

                with self.subTest():
                    sim = self.run_tst_program(program, initial_fprs=fprs)
                    print("FPR 1", sim.fpr(1))
                    print("FPR 2", sim.fpr(2))
                    print("FPR 3", sim.fpr(3))
                    self.assertEqual(sim.fpr(2), SelectableInt(a1, 64))
                    self.assertEqual(sim.fpr(1), SelectableInt(t, 64))
                    self.assertEqual(sim.fpr(3), SelectableInt(u, 64))

    def test_fp_coss_cvt(self):
        """>>> lst = [
                      "fcoss 3, 2",
                     ]

        this is a base / proving-ground for the more complex SVP64
        variant in test_caller_svp64_dct.py:
        test_sv_remap_dct_cos_precompute_8
        """
        lst = SVP64Asm(["std 1, 0(0)",
                        "lfd 0, 0(0)",
                        "fcfids 0, 0",
                        "fadds 0, 0, 3", # plus 0.5
                        "fmuls 0, 0, 1", # times PI
                        "fdivs 0, 0, 2", # div 4.0
                        "fcoss 4, 0",
                     ])
        lst = list(lst)

        with Program(lst, bigendian=False) as program:
            gprs = [0] * 32
            fprs = [0] * 32
            # constants
            fprs[3] = fp64toselectable(0.5)     # 0.5
            fprs[1] = fp64toselectable(math.pi) # pi
            fprs[2] = fp64toselectable(4.0)     # 4.0
            #for i in range(-8, 9):
            for i in range(7, 8):
                a = math.pi * ((i+0.5) / 4.0)
                gprs[1] = i
                a1 = fph.DOUBLE2SINGLE(fp64toselectable(a)) # to Power single
                a = float(a1)
                u = math.cos(a)
                u = fph.DOUBLE2SINGLE(fp64toselectable(u)) # to Power single

                with self.subTest():
                    sim = self.run_tst_program(program, gprs, initial_fprs=fprs)
                    print("FPR 0", sim.fpr(0), float(sim.fpr(0)))
                    print("FPR 1", sim.fpr(1), float(sim.fpr(1)))
                    print("FPR 2", sim.fpr(2), float(sim.fpr(2)))
                    print("FPR 3", sim.fpr(3), float(sim.fpr(3)))
                    print("FPR 4", sim.fpr(4), float(sim.fpr(4)))
                    # sign should not do this, but hey
                    actual_r = float(sim.fpr(0))
                    expected_r = float(a1)
                    err = abs(actual_r - expected_r ) / expected_r
                    self.assertTrue(err < 1e-6)
                    actual_r = float(sim.fpr(4))
                    expected_r = float(u)
                    err = abs(actual_r - expected_r ) / expected_r
                    self.assertTrue(err < 1e-6)

    def run_tst_program(self, prog, initial_regs=None,
                              initial_mem=None,
                              initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                                  initial_fprs=initial_fprs)
        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
