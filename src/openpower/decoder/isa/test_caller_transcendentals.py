from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
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
from openpower.decoder.isafunctions.double2single import DOUBLE2SINGLE

import math

class FPTranscendentalsTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected_int, expected_fpr):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))
        for i in range(32):
            self.assertEqual(sim.fpr(i), SelectableInt(expected_fpr[i], 64))

    def test_fp_sins_coss(self):
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
                t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
                u = DOUBLE2SINGLE(fp64toselectable(u)) # convert to Power single

                with self.subTest():
                    sim = self.run_tst_program(program, initial_fprs=fprs)
                    print("FPR 1", sim.fpr(1))
                    print("FPR 2", sim.fpr(2))
                    print("FPR 3", sim.fpr(3))
                    self.assertEqual(sim.fpr(2), SelectableInt(a1, 64))
                    self.assertEqual(sim.fpr(1), SelectableInt(t, 64))
                    self.assertEqual(sim.fpr(3), SelectableInt(u, 64))

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
