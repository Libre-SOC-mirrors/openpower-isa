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
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.consts import SVP64CROffs
from copy import deepcopy
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isa.remap_preduce_yield import preduce_y
from functools import reduce
import operator


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def tst_sv_remap1(self):
        """>>> lst = ["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 0, 1, 0, 0, 0, 0",
                       "sv.add *0, *8, *16"
                        ]
                REMAP add RT,RA,RB
        """
        lst = SVP64Asm(["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 0, 1, 0, 0, 0, 0",
                       "sv.add *0, *0, *0"
                        ])
        lst = list(lst)

        gprs = [0] * 64
        vec = [1, 2, 3, 4, 9, 5, 6]

        # and create a linear result2, same scheme
        #result1 = [0] * (ydim1*xdim2)


        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs)
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print ("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print ("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(7):
                val = sim.gpr(i).value
                res.append(val)
                print ("i", i, val)
            # confirm that the results are as expected
            expected = preduce_y(vec)
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])


    def test_sv_remap2(self):
        """>>> lst = ["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 1, 0, 0, 0, 0, 0", # different order
                       "sv.subf *0, *8, *16"
                        ]
                REMAP sv.subf RT,RA,RB - inverted application of RA/RB
                                         left/right due to subf
        """
        lst = SVP64Asm(["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 1, 0, 0, 0, 0, 0",
                       "sv.subf *0, *0, *0"
                        ])
        lst = list(lst)

        gprs = [0] * 64
        vec = [1, 2, 3, 4, 9, 5, 6]

        # and create a linear result2, same scheme
        #result1 = [0] * (ydim1*xdim2)


        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs)
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print ("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print ("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(7):
                val = sim.gpr(i).value
                res.append(val)
                print ("i", i, val)
            # confirm that the results are as expected, mask with 64-bit
            expected = preduce_y(vec, operation=operator.sub)
            for i, v in enumerate(res):
                self.assertEqual(v&0xffffffffffffffff,
                                 expected[i]&0xffffffffffffffff)

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
