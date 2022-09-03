"""SVP64 unit test for svshape2
svshape2 offs,yx,rmm,SVd,sk,mm
"""
from nmigen import Module, Signal
from nmigen.sim import Simulator, Delay, Settle
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
        print("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64),
                             "GPR %d %x expected %x" % (i, sim.gpr(i).value, expected[i]))

    def test_0_sv_shape2(self):
        """sets VL=10 (via SVSTATE) then does svshape mm=0, checks SPRs after
        """
        isa = SVP64Asm(['svshape2 12, 1, 15, 5, 0, 0'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 10  # VL
        svstate.maxvl = 10  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        #expected_regs[1] = 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            self._check_regs(sim, expected_regs)

            print(sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("      RMpst", bin(sim.svstate.RMpst))
            print("       SVme", bin(sim.svstate.SVme))
            print("        mo0", bin(sim.svstate.mo0))
            print("        mo1", bin(sim.svstate.mo1))
            print("        mi0", bin(sim.svstate.mi0))
            print("        mi1", bin(sim.svstate.mi1))
            print("        mi2", bin(sim.svstate.mi2))
            print("STATE0     ", SVSHAPE0)
            print("STATE0 offs", SVSHAPE0.offset)
            print("STATE0 xdim", SVSHAPE0.xdimsz)
            print("STATE0 ydim", SVSHAPE0.ydimsz)
            print("STATE0 skip", bin(SVSHAPE0.skip))
            print("STATE0  inv", SVSHAPE0.invxyz)
            print("STATE0order", SVSHAPE0.order)
            self.assertEqual(SVSHAPE0.xdimsz, 5)  # set
            self.assertEqual(SVSHAPE0.ydimsz, 2)  # calculated from MVL/xdimsz
            self.assertEqual(SVSHAPE0.skip, 0)   # no skip
            # (no inversion possible)
            self.assertEqual(SVSHAPE0.invxyz, [0, 0, 0])
            self.assertEqual(SVSHAPE0.offset, 12)
            self.assertEqual(SVSHAPE0.order, (1, 0, 2))  # y,x(,z)
            self.assertEqual(sim.svstate.RMpst, 0)  # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b01111)  # same as rmm
            # rmm is 0b01111 which means mi0=0 mi1=1 mi2=2 mo0=3 mo1=0
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 1)
            self.assertEqual(sim.svstate.mi2, 2)
            self.assertEqual(sim.svstate.mo0, 3)
            self.assertEqual(sim.svstate.mo1, 0)

    def test_1_sv_offset2_add(self):
        """sets VL=6 (via SVSTATE) then does modulo 3 svindex, and an add.

        only RA is re-mapped via svshape2, not RB or RT, but an offset of
        1 is included on RA.

        whilst this does not look useful for sv.add because it is EXTRA3
        encoded, it *is* a useful demo for anything EXTRA2-encoded which
        only has even-numbered GPR/FPR vector register accessibility.
        set the offset to compensate for EXTRA2 being so restricted.
        """
        # set some parameters here with comments
        offs = 1 # an offset of 1
        mod = 3  # modulo 3 on the range
        VL = 6   # RB will go 0..5 but RA will go 1 2 3 1 2 3
        isa = SVP64Asm(['svshape2 %d, 0, 1, %d, 0, 0' % (offs, mod),
                        'sv.add *8, *0, *0',
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        for i in range(VL):
            initial_regs[i] = i

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = VL  # VL
        svstate.maxvl = VL  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        # copy before running and compute the expected results
        expected_regs = deepcopy(initial_regs)
        for i in range(VL):
            RA = initial_regs[offs+(i % mod)]  # modulo but also offset
            RB = initial_regs[0+i]             # RB is not re-mapped
            expected_regs[i+8] = RA+RB
            print("expected", i, expected_regs[i+8])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            print(sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            SVSHAPE1 = sim.spr['SVSHAPE1']
            SVSHAPE2 = sim.spr['SVSHAPE2']
            SVSHAPE3 = sim.spr['SVSHAPE3']
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("      RMpst", bin(sim.svstate.RMpst))
            print("       SVme", bin(sim.svstate.SVme))
            print("        mo0", bin(sim.svstate.mo0))
            print("        mo1", bin(sim.svstate.mo1))
            print("        mi0", bin(sim.svstate.mi0))
            print("        mi1", bin(sim.svstate.mi1))
            print("        mi2", bin(sim.svstate.mi2))
            print("STATE0     ", SVSHAPE0)
            print("STATE0 offs", SVSHAPE0.offset)
            print("STATE0 xdim", SVSHAPE0.xdimsz)
            print("STATE0 ydim", SVSHAPE0.ydimsz)
            print("STATE0 skip", bin(SVSHAPE0.skip))
            print("STATE0  inv", SVSHAPE0.invxyz)
            print("STATE0order", SVSHAPE0.order)
            print(sim.gpr.dump())
            self.assertEqual(SVSHAPE0.xdimsz, 3)  # set
            self.assertEqual(SVSHAPE0.ydimsz, 1)  # calculated from MVL/xdimsz
            self.assertEqual(SVSHAPE0.skip, 0)   # no skip
            # (no inversion possible)
            self.assertEqual(SVSHAPE0.invxyz, [0, 0, 0])
            self.assertEqual(SVSHAPE0.offset, 1)
            self.assertEqual(SVSHAPE0.order, (0, 1, 2))  # x,y(,z)
            self.assertEqual(sim.svstate.RMpst, 0)  # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b00001)  # same as rmm
            # SVSHAPE1-3 zero
            self.assertEqual(SVSHAPE1, 0)
            self.assertEqual(SVSHAPE2, 0)
            self.assertEqual(SVSHAPE3, 0)
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 0)
            self.assertEqual(sim.svstate.mo1, 0)
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
