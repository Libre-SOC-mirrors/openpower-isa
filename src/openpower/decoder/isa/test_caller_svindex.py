"""SVP64 unit test for svindex
svindex SVG,rmm,SVd,ew,yx,mr,sk
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
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64),
            "GPR %d %x expected %x" % (i, sim.gpr(i).value, expected[i]))

    def test_0_sv_index(self):
        """sets VL=10 (via SVSTATE) then does svindex, checks SPRs after
        """
        isa = SVP64Asm(['svindex 1, 15, 5, 0, 0, 0, 0'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 10 # VL
        svstate.maxvl = 10 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        #expected_regs[1] = 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            self._check_regs(sim, expected_regs)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b01111) # same as rmm
            # rmm is 0b01111 which means mi0=0 mi1=1 mi2=2 mo0=3 mo1=0
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 1)
            self.assertEqual(sim.svstate.mi2, 2)
            self.assertEqual(sim.svstate.mo0, 3)
            self.assertEqual(sim.svstate.mo1, 0)
            for i in range(4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 2) # SVG is shifted up by 1

    def test_0_sv_index_add(self):
        """sets VL=6 (via SVSTATE) then does svindex, and an add.

        only RA is re-mapped via Indexing, not RB or RT
        """
        isa = SVP64Asm(['svindex 8, 1, 3, 0, 0, 0, 0',
                        'sv.add *8, *0, *0',
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        idxs = [1, 0, 5, 2, 4, 3] # random enough
        for i in range(6):
            initial_regs[16+i] = idxs[i]
            initial_regs[i] = i

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 6 # VL
        svstate.maxvl = 6 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        for i in range(6):
            RA = initial_regs[16+idxs[i]]
            RB = initial_regs[16+i]
            expected_regs[i+8] = RA+RB
            print ("expected", i, expected_regs[i+8])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            #self._check_regs(sim, expected_regs)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print (sim.gpr.dump())
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b00001) # same as rmm
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 0)
            self.assertEqual(sim.svstate.mo1, 0)
            for i in range(4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 16) # SVG is shifted up by 1

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

