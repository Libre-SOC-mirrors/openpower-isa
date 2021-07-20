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
        print ("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_svstep_1(self):
        lst = SVP64Asm(["setvl 0, 0, 10, 1, 1, 1", # actual setvl (VF mode)
                        "setvl 0, 0, 1, 1, 0, 0", # svstep
                        "setvl 0, 0, 1, 1, 0, 0" # svstep
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4) which is going to get erased by setvl
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            self.assertEqual(sim.svstate.srcstep, 2)
            self.assertEqual(sim.svstate.dststep, 2)
            self.assertEqual(sim.svstate.vfirst, 1)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))

    def test_svstep_2(self):
        """tests svstep when it reaches VL
        """
        lst = SVP64Asm(["setvl 0, 0, 2, 1, 1, 1",  # actual setvl (VF mode)
                        "setvl. 0, 0, 1, 1, 0, 0", # svstep (Rc=1)
                        "setvl. 0, 0, 1, 1, 0, 0" # svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate.vfirst))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_svstep_3(self):
        """tests svstep when it *doesn't* reach VL
        """
        lst = SVP64Asm(["setvl 0, 0, 3, 1, 1, 1",  # actual setvl (VF mode)
                        "setvl. 0, 0, 1, 1, 0, 0", # svstep (Rc=1)
                        "setvl. 0, 0, 1, 1, 0, 0" # svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 3)
            self.assertEqual(sim.svstate.maxvl, 3)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 2)
            self.assertEqual(sim.svstate.dststep, 2)
            print("      gpr1", sim.gpr(0))
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)


    def test_setvl_1(self):
        """straight setvl, testing if VL and MVL are over-ridden
        """
        lst = SVP64Asm(["setvl 1, 0, 10, 0, 1, 1",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2), want to see if these get changed
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            self.assertEqual(sim.svstate.vl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            self.assertEqual(sim.svstate.maxvl, 10)
            print("      gpr1", sim.gpr(1))
            self.assertEqual(sim.gpr(1), SelectableInt(10, 64))

    def test_svstep_inner_loop_6(self):
        """tests svstep inner loop, running 6 times, looking for "k"
        """
        lst = SVP64Asm([
                        # set triple butterfly mode with persistent "REMAP"
                        "svshape 8, 1, 1, 1, 1",
                        "svremap 31, 1, 0, 2, 0, 1, 1",
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        #svstate.vl = 2 # VL
        #svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 6)
            self.assertEqual(sim.svstate.dststep, 6)
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_inner_loop_3(self):
        """tests svstep inner loop, running 3 times
        """
        lst = SVP64Asm([
                        # set triple butterfly mode with persistent "REMAP"
                        "svshape 8, 1, 1, 1, 1",
                        "svremap 31, 1, 0, 2, 0, 1, 1",
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0", # svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        #svstate.vl = 2 # VL
        #svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 3)
            self.assertEqual(sim.svstate.dststep, 3)
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 1)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_svstep_inner_loop_4(self):
        """tests svstep inner loop, running 4 times
        """
        lst = SVP64Asm([
                        # set triple butterfly mode with persistent "REMAP"
                        "svshape 8, 1, 1, 1, 1",
                        "svremap 31, 1, 0, 2, 0, 1, 1",
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0",# svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0", # svstep (Rc=1)
                        "setvl. 0, 0, 2, 1, 0, 0", # svstep (Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        #svstate.vl = 2 # VL
        #svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 12)
            self.assertEqual(sim.svstate.maxvl, 12)
            # svstep called twice, didn't reach VL, so srcstep/dststep both 2
            self.assertEqual(sim.svstate.srcstep, 4)
            self.assertEqual(sim.svstate.dststep, 4)
            self.assertEqual(sim.gpr(0), SelectableInt(0, 64))
            self.assertEqual(sim.svstate.vfirst, 1)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 1)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 0)

    def test_sv_add(self):
        """sets VL=2 then adds:
           * 1 = 5 + 9   => 0x5555 = 0x4321+0x1234
           * 2 = 6 + 10  => 0x3334 = 0x2223+0x1111
        """
        isa = SVP64Asm(["setvl 3, 0, 2, 0, 1, 1",
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

    def test_svstep_add_1(self):
        """tests svstep with an add, when it reaches VL
        lst = SVP64Asm(["setvl 3, 0, 2, 1, 1, 1",
                        'sv.add 1.v, 5.v, 9.v',
                        "setvl. 0, 0, 1, 1, 0, 0",
                        'sv.add 1.v, 5.v, 9.v',
                        "setvl. 0, 0, 1, 1, 0, 0"
                        ])
        sequence is as follows:
        * setvl sets VL=2 but also "Vertical First" mode.
          this sets MSR[SVF].
        * first add, which has srcstep/dststep = 0, does add 1,5,9
        * svstep EXPLICITLY walks srcstep/dststep to next element
        * second add, which now has srcstep/dststep = 1, does add 2,6,10
        * svstep EXPLICITLY walks srcstep/dststep to next element,
          which now equals VL.  srcstep and dststep are both set to
          zero, and MSR[SVF] is cleared.
        """
        lst = SVP64Asm(["setvl 3, 0, 2, 1, 1, 1",
                        'sv.add 1.v, 5.v, 9.v',
                        "setvl. 0, 0, 1, 1, 0, 0",  # svstep
                        'sv.add 1.v, 5.v, 9.v',
                        "setvl. 0, 0, 1, 1, 0, 0"  # svstep
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
        expected_regs[1] = 0x5555
        expected_regs[2] = 0x3334
        expected_regs[3] = 2       # setvl places copy of VL here

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

            # check registers as expected
            self._check_regs(sim, expected_regs)

    def test_svstep_add_2(self):
        """tests svstep with a branch.
        lst = SVP64Asm(["setvl 3, 0, 2, 1, 1, 1",
                        'sv.add 1.v, 5.v, 9.v',
                        "setvl. 0, 0, 1, 1, 0, 0",
                        "bc 6, 3, -0xc"
                        ])
        sequence is as follows:
        * setvl sets VL=2 but also "Vertical First" mode.
          this sets MSR[SVF].
        * first time add, which has srcstep/dststep = 0, does add 1,5,9
        * svstep EXPLICITLY walks srcstep/dststep to next element,
          not yet met VL, so CR0.EQ is set to zero
        * branch conditional checks bne on CR0, jumps back TWELVE bytes
          because whilst branch is 32-bit the sv.add is 64-bit
        * second time add, which now has srcstep/dststep = 1, does add 2,6,10
        * svstep walks to next element, meets VL, so:
          - srcstep and dststep set to zero
          - CR0.EQ set to one
          - MSR[SVF] is cleared
        * branch conditional detects CR0.EQ=1 and FAILs the condition,
          therefore loop ends.

        we therefore have an explicit "Vertical-First" system which can
        have **MULTIPLE* instructions inside a loop, running each element 0
        first, then looping back and running all element 1, then all element 2
        etc.
        """
        lst = SVP64Asm(["setvl 3, 0, 2, 1, 1, 1",
                        'sv.add 1.v, 5.v, 9.v',
                        "setvl. 0, 0, 1, 1, 0, 0", # svstep - this is 64-bit!
                        "bc 6, 3, -0xc" # branch to add (64-bit op so -0xc!)
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
        expected_regs[1] = 0x5555
        expected_regs[2] = 0x3334
        expected_regs[3] = 2       # setvl places copy of VL here

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 2)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            # when end reached, vertical mode is exited
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

            # check registers as expected
            self._check_regs(sim, expected_regs)

    def test_svremap(self):
        """svremap, see if values get set
        """
        lst = SVP64Asm(["svremap 11, 0, 1, 2, 3, 3, 1",
                        ])
        lst = list(lst)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program)
            svstate = sim.svstate
            print ("SVREMAP after", bin(svstate.value))
            print ("        men", bin(svstate.SVme))
            print ("        mi0", bin(svstate.mi0))
            print ("        mi1", bin(svstate.mi1))
            print ("        mi2", bin(svstate.mi2))
            print ("        mo0", bin(svstate.mo0))
            print ("        mo1", bin(svstate.mo1))
            print ("    persist", bin(svstate.RMpst))
            self.assertEqual(svstate.SVme, 11)
            self.assertEqual(svstate.mi0, 0)
            self.assertEqual(svstate.mi1, 1)
            self.assertEqual(svstate.mi2, 2)
            self.assertEqual(svstate.mo0, 3)
            self.assertEqual(svstate.mo1, 3)
            self.assertEqual(svstate.RMpst, 1)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

