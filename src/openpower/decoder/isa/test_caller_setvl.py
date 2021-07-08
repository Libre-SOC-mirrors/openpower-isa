from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, SVP64State, CRFields
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA
from openpower.decoder.isa.test_caller import Register, run_tst
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.consts import SVP64CROffs
from copy import deepcopy

class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_svstep_1(self):
        lst = SVP64Asm(["setvl 0, 0, 9, 1, 1, 1",
                        "setvl 0, 0, 0, 1, 0, 0",
                        "setvl 0, 0, 0, 1, 0, 0"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4) which is going to get erased by setvl
        svstate = SVP64State()
        svstate.vl[0:7] = 4 # VL
        svstate.maxvl[0:7] = 4 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.spr.asint()))
            print ("        vl", bin(sim.svstate.vl.asint(True)))
            print ("        mvl", bin(sim.svstate.maxvl.asint(True)))
            print ("    srcstep", bin(sim.svstate.srcstep.asint(True)))
            print ("    dststep", bin(sim.svstate.dststep.asint(True)))
            self.assertEqual(sim.svstate.vl.asint(True), 10)
            self.assertEqual(sim.svstate.maxvl.asint(True), 10)
            self.assertEqual(sim.svstate.srcstep.asint(True), 2)
            self.assertEqual(sim.svstate.dststep.asint(True), 2)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            print("      msr", bin(sim.msr.value))
            self.assertEqual(sim.msr, SelectableInt(1<<(63-6), 64))

    def test_svstep_2(self):
        """tests svstep when it reaches VL
        """
        lst = SVP64Asm(["setvl 0, 0, 1, 1, 1, 1",
                        "setvl. 0, 0, 0, 1, 0, 0",
                        "setvl. 0, 0, 0, 1, 0, 0"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.spr.asint()))
            print ("        vl", bin(sim.svstate.vl.asint(True)))
            print ("        mvl", bin(sim.svstate.maxvl.asint(True)))
            print ("    srcstep", bin(sim.svstate.srcstep.asint(True)))
            print ("    dststep", bin(sim.svstate.dststep.asint(True)))
            self.assertEqual(sim.svstate.vl.asint(True), 2)
            self.assertEqual(sim.svstate.maxvl.asint(True), 2)
            self.assertEqual(sim.svstate.srcstep.asint(True), 0)
            self.assertEqual(sim.svstate.dststep.asint(True), 0)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            print("      msr", bin(sim.msr.value))
            self.assertEqual(sim.msr, SelectableInt(1<<(63-6), 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 1)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_3(self):
        """tests svstep when it *doesn't* reach VL
        """
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        "setvl. 0, 0, 0, 1, 0, 0",
                        "setvl. 0, 0, 0, 1, 0, 0"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.spr.asint()))
            print ("        vl", bin(sim.svstate.vl.asint(True)))
            print ("        mvl", bin(sim.svstate.maxvl.asint(True)))
            print ("    srcstep", bin(sim.svstate.srcstep.asint(True)))
            print ("    dststep", bin(sim.svstate.dststep.asint(True)))
            self.assertEqual(sim.svstate.vl.asint(True), 3)
            self.assertEqual(sim.svstate.maxvl.asint(True), 3)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep.asint(True), 2)
            self.assertEqual(sim.svstate.dststep.asint(True), 2)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            print("      msr", bin(sim.msr.value))
            self.assertEqual(sim.msr, SelectableInt(1<<(63-6), 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)


    def test_setvl_1(self):
        lst = SVP64Asm(["setvl 1, 0, 9, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.spr.asint()))
            print ("        vl", bin(sim.svstate.vl.asint(True)))
            print ("        mvl", bin(sim.svstate.maxvl.asint(True)))
            self.assertEqual(sim.svstate.vl.asint(True), 10)
            self.assertEqual(sim.svstate.maxvl.asint(True), 10)
            self.assertEqual(sim.svstate.maxvl.asint(True), 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(10, 64))


    def test_sv_add(self):
        # sets VL=2 then adds:
        #       1 = 5 + 9   => 0x5555 = 0x4321+0x1234
        #       2 = 6 + 10  => 0x3334 = 0x2223+0x1111
        isa = SVP64Asm(["setvl 3, 0, 1, 0, 1, 1",
                        'sv.add 1.v, 5.v, 9.v'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = 0x5555
        expected_regs[2] = 0x3334
        expected_regs[3] = 2       # setvl places copy of VL here

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self._check_regs(sim, expected_regs)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

