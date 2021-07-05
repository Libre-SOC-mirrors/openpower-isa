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
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.consts import SVP64CROffs
from copy import deepcopy
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isafunctions.double2single import DOUBLE2SINGLE

class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_remap(self):
        """>>> lst = ["svremap 2, 2, 3, 0"
                        ]
        """
        lst = SVP64Asm(["svremap 2, 2, 3, 0"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        if False:
            av = [7.0, -9.8, 2.0, -32.3] # first half of array 0..3
            bv = [-2.0, 2.0, -9.8, 32.3] # second half of array 4..7
            coe = [-1.0, 4.0, 3.1, 6.2]  # coefficients
            res = []
            # work out the results with the twin mul/add-sub
            for i, (a, b, c) in enumerate(zip(av, bv, coe)):
                fprs[i+2] = fp64toselectable(a)
                fprs[i+6] = fp64toselectable(b)
                fprs[i+10] = fp64toselectable(c)
                mul = a * c
                t = a + mul
                u = b - mul
                t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
                u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
                res.append((t, u))
                print ("FFT", i, "in", a, b, "coeff", c, "mul",
                       mul, "res", t, u)

        # SVSTATE (in this case, VL=12, to cover all of matrix)
        svstate = SVP64State()
        svstate.vl[0:7] = 12 # VL
        svstate.maxvl[0:7] = 12 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])
            # confirm that the results are as expected
            #for i, (t, u) in enumerate(res):
            #    self.assertEqual(sim.fpr(i+2), t)
            #    self.assertEqual(sim.fpr(i+6), u)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None,
                              initial_mem=None,
                              initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                                                initial_fprs=initial_fprs,
                                                svstate=svstate)

        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()

        return simulator


if __name__ == "__main__":
    unittest.main()
