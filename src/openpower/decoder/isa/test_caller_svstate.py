"""SVP64 unit test for doing strange things to SVSTATE, manually.
"""
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


class SVSTATETestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        print ("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_add(self):
        """sets VL=2 (via SVSTATE) with a manual srcstep/dststep,
            then does a scalar-result add.  the result should be:

                add 1, 6, 10

            because whilst the Vector instruction was moved on by srcstep,
            the Scalar one is NOT moved on.
        """
        isa = SVP64Asm(['sv.add 1, 5.v, 9.v'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # SVSTATE (in this case, VL=3, and src/dststep set ALREADY to 1)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        svstate.srcstep = 1 # srcstep
        svstate.dststep = 1 # srcstep
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            self._check_regs(sim, expected_regs)

    def test_svstep_add_1(self):
        """tests svstep with an add, using scalar adds, when it reaches VL
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        'sv.add 1, 5.v, 9.v',
                        'sv.addi 12.v, 1, 1',
                        "setvl. 0, 0, 1, 1, 0, 0",
                        'sv.add 1, 5.v, 9.v',
                        'sv.addi 12.v, 1, 1',
                        "setvl. 0, 0, 1, 1, 0, 0"
                        ])

        sequence is as follows:

        * setvl sets VL=2 but also "Vertical First" mode.
          this sets SVSTATE[SVF].
        * first add, which has srcstep/dststep = 0, does add 1,5,9
        * first addi, which has srcstep/dststep = 0, does addi 12, 1, #1
        * svstep EXPLICITLY walks srcstep/dststep to next element
        * second add, which now has srcstep/dststep = 1, does add 1,6,10
          (because RT is a *SCALAR*)
        * second addi, which has srcstep/dststep = 1, does addi 13, 1, #1
        * svstep EXPLICITLY walks srcstep/dststep to next element,
          which now equals VL.  srcstep and dststep are both set to
          zero.  CR0.SO is set to 1 because
          it is the end of the looping.

        the first add will write 0x5555 into r1, then the vector-addi
        will add 1 to that and store the result in r12 (0x5556)

        the second add will write 0x3334 into the temp r1, this *stays* there
        obviously, and the second vector-addi will add 1 to the *new* r1 and
        store the result in r13 (0x3335).

        """
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",
                        'sv.add 1, 5.v, 9.v',       # scalar dest (into r1)
                        'sv.addi 12.v, 1, 1',       # scalar src (from r1)
                        "setvl. 0, 0, 1, 1, 0, 0",  # svstep
                        'sv.add 1, 5.v, 9.v',       # again, scalar dest
                        'sv.addi 12.v, 1, 1',       # but vector dest
                        "setvl. 0, 0, 1, 1, 0, 0"  # svstep (end: sets CR0.SO)
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = 0x3334   # last temporary
        expected_regs[12] = 0x5556
        expected_regs[13] = 0x3335

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            print("      msr", bin(sim.msr.value)) # should be zero
            self.assertEqual(sim.msr, SelectableInt(0<<(63-6), 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

            # check registers as expected
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

