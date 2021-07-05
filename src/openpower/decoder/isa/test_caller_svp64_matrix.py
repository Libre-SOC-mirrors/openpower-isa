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
from functools import reduce
import operator


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_remap(self):
        """>>> lst = ["svremap 2, 2, 3, 0",
                       "sv.fmadds 0.v, 8.v, 16.v, 0.v"
                        ]
                REMAP fmadds FRT, FRA, FRC, FRB
        """
        lst = SVP64Asm(["svremap 2, 2, 3, 0",
                       "sv.fmadds 0.v, 8.v, 16.v, 0.v"
                        ])
        lst = list(lst)

        fprs = [0] * 64
        # 3x2 matrix
        X1 = [[1, 2, 3],
              [3, 4, 5],
             ]
        # 2x3 matrix
        Y1 = [[6, 7],
              [8, 9],
              [10, 11],
             ]

        X = X1
        Y = Y1

        xf = reduce(operator.add, X)
        yf = reduce(operator.add, Y)
        print ("flattened X,Y")
        print ("\t", xf)
        print ("\t", yf)

        # and create a linear result2, same scheme
        #result2 = [0] * (ydim1*xdim2)


        res = []
        # store FPs
        for i, (x, y) in enumerate(zip(xf, yf)):
            fprs[i+8] = fp64toselectable(float(x))  # X matrix
            fprs[i+16] = fp64toselectable(float(y)) # Y matrix
            continue
            #t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            #u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            #res.append((t, u))
            #print ("FFT", i, "in", a, b, "coeff", c, "mul",
            #       mul, "res", t, u)

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
            for i in range(4):
                print ("i", i, float(sim.fpr(i)))
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
