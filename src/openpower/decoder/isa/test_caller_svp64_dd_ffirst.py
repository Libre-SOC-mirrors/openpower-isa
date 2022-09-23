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
from functools import reduce
import operator


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_addi_ffirst(self):
        lst = SVP64Asm([ "sv.subf./ff=eq *0,8,*0"
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        gprs[8] = 3
        vec = [9, 8, 3, 4]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                                svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                print ("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            for i in range(4):
                expected[i] -= gprs[8]
                if expected[i] == 0:
                    break
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

    def tst_sv_addi_ffirst_vli(self):
        lst = SVP64Asm([ "sv.subf/ff=~RC1/vli *0,8,*0"
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        gprs[8] = 3
        vec = [9, 8, 3, 4]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                                svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                print ("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            for i in range(4):
                expected[i] -= gprs[8]
                if expected[i] == 0:
                    break
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, 3)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

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
