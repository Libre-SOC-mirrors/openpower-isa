from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.isa.test_caller import run_tst
from openpower.sv.trans.svp64 import SVP64Asm
from copy import deepcopy
from openpower.decoder.helpers import fp64toselectable, SINGLE
from openpower.decoder.isafunctions.double2single import DOUBLE2SINGLE


class DCTTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_ffadds_dct(self):
        """>>> lst = ["sv.fdmadds 0.v, 8.v, 0.v, 0.v"
                        ]
            four in-place vector adds, four in-place vector mul-subs

            SVP64 "DCT" mode will *automatically* offset FRB and an implicit
            FRS to perform the two multiplies.  one add, one subtract.

            sv.fdadds FRT, FRA, FRC, FRB  actually does:
                fadds FRT   , FRB, FRA
                fsubs FRT+vl, FRA, FRB+vl
        """
        lst = SVP64Asm(["sv.fdmadds 0.v, 8.v, 0.v, 0.v"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        av = [7.0, -9.8, 2.0, -32.3] # first half of array 0..3
        bv = [-2.0, 2.0, -9.8, 32.3] # second half of array 4..7
        cv = [-1.0, 0.5, 2.3, -3.2]  # coefficients
        res = []
        # work out the results with the twin add-sub
        for i, (a, b, c) in enumerate(zip(av, bv, cv)):
            fprs[i+0] = fp64toselectable(a)
            fprs[i+4] = fp64toselectable(b)
            fprs[i+8] = fp64toselectable(c)
            t = b + a
            u = (b - a) * c
            t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            res.append((t, u))
            print ("FFT", i, "in", a, b, "c", c, "res", t, u)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            # confirm that the results are as expected
            for i, (t, u) in enumerate(res):
                a = float(sim.fpr(i+0))
                b = float(sim.fpr(i+4))
                t = float(t)
                u = float(u)
                print ("FFT", i, "in", a, b, "res", t, u)
            for i, (t, u) in enumerate(res):
                self.assertEqual(sim.fpr(i+2), t)
                self.assertEqual(sim.fpr(i+6), u)

    def tst_sv_remap_fpmadds_dct(self):
        """>>> lst = ["svshape 4, 1, 1, 2, 0",
                     "svremap 31, 1, 0, 2, 0, 1, 0",
                        "sv.ffmadds 0.v, 0.v, 0.v, 8.v"
                     ]
            runs a full in-place O(N log2 N) butterfly schedule for
            DCT

            SVP64 "REMAP" in Butterfly Mode is applied to a twin +/- FMAC
            (3 inputs, 2 outputs)
        """
        lst = SVP64Asm( ["svshape 4, 1, 1, 2, 0",
                         "svremap 31, 1, 0, 2, 0, 1, 0",
                        "sv.ffmadds 0.v, 0.v, 0.v, 8.v"
                        ])
        lst = list(lst)

        # array and coefficients to test
        av = [7.0, -9.8, 3.0, -32.3]
        coe = [-0.25, 0.5, 3.1, 6.2, 0.1, -0.2] # 6 coefficients

        # store in regfile
        fprs = [0] * 32
        for i, c in enumerate(coe):
            fprs[i+8] = fp64toselectable(c)
        for i, a in enumerate(av):
            fprs[i+0] = fp64toselectable(a)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print ("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print ("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])

            return

            # work out the results with the twin mul/add-sub
            res = transform_radix2(av, coe)

            for i, expected in enumerate(res):
                print ("i", i, float(sim.fpr(i)), "expected", expected)
            for i, expected in enumerate(res):
                # convert to Power single
                expected = DOUBLE2SINGLE(fp64toselectable(expected))
                expected = float(expected)
                actual = float(sim.fpr(i))
                # approximate error calculation, good enough test
                # reason: we are comparing FMAC against FMUL-plus-FADD-or-FSUB
                # and the rounding is different
                err = abs(actual - expected) / expected
                self.assertTrue(err < 1e-7)

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
