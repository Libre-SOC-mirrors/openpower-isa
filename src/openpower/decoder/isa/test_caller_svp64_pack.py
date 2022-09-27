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

class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        print ("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_svstep_pack(self):
        """tests pack mode
        """
        lst = SVP64Asm(["setvl 0, 0, 4, 0, 1, 1",
                        "svstep 0, 15, 0",  # set dst-pack
                        "sv.svstep./vec2 *0, 5, 1", # svstep get vector srcstep
                        "sv.svstep./vec2 *8, 6, 1", # svstep get vector dststep
                        "sv.svstep./vec2 *16, 7, 1", # svstep get src substep
                        "sv.svstep./vec2 *24, 8, 1", # svstep get dst substep
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
            sim.gpr.dump()
            self.assertEqual(sim.svstate.vl, 4)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            for j in range(2):
                for i in range(4):
                    offs = j*4+i
                    skew = i*2+j
                    self.assertEqual(sim.gpr(0+offs), SelectableInt(i, 64))
                    self.assertEqual(sim.gpr(8+skew), SelectableInt(i, 64))
                    self.assertEqual(sim.gpr(16+offs), SelectableInt(j, 64))
                    self.assertEqual(sim.gpr(24+skew), SelectableInt(j, 64))
            self.assertEqual(sim.svstate.vfirst, 0)
            CR0 = sim.crl[0]
            print("      CR0", bin(CR0.get_range().value))
            self.assertEqual(CR0[CRFields.EQ], 0)
            self.assertEqual(CR0[CRFields.LT], 0)
            self.assertEqual(CR0[CRFields.GT], 0)
            self.assertEqual(CR0[CRFields.SO], 1)

    def test_svstep_unpack(self):
        """tests unpack mode
        oh ha ha very funny,  cannot use sv.srcstep on unpack:
        the dest indices are themselves put *into*
        the vector output in the order of their own values.
        """
        lst = SVP64Asm(["setvl 0, 0, 4, 0, 1, 1",
                        "svstep 0, 14, 0",  # set src-pack
                        "sv.ori/vec2 *0, *32, 0", # copy 01234567 to new order
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        #svstate.vl = 2 # VL
        #svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        initial_regs = [0]*64
        for i in range(8):
            initial_regs[32+i] = i

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            sim.gpr.dump()
            self.assertEqual(sim.svstate.vl, 4)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            for j in range(2):
                for i in range(4):
                    offs = j*4+i
                    skew = i*2+j
                    self.assertEqual(sim.gpr(0+skew), SelectableInt(offs, 64))

    def test_svstep_pack2(self):
        """tests pack mode
        """
        lst = SVP64Asm(["setvl 0, 0, 4, 0, 1, 1",
                        "svstep 0, 15, 0",  # set dst-pack
                        "sv.ori/vec2 *0, *32, 0", # copy 01234567 to new order
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        #svstate.vl = 2 # VL
        #svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        initial_regs = [0]*64
        for i in range(8):
            initial_regs[32+i] = i

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            sim.gpr.dump()
            self.assertEqual(sim.svstate.vl, 4)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)
            for j in range(2):
                for i in range(4):
                    offs = j*4+i
                    skew = i*2+j
                    self.assertEqual(sim.gpr(0+offs), SelectableInt(skew, 64))

    def test_svstep_predicate_pack(self):
        """tests pack mode with a predicate
        """
        lst = SVP64Asm(["setvl 0, 0, 4, 0, 1, 1",
                        "svstep 0, 15, 0",  # set dst-pack
                        "sv.ori/vec2/m=r3 *8, *16, 0",
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        #svstate.vl = 2 # VL
        #svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        mask = 0b0110
        initial_regs = [0xffffffff]*64
        initial_regs[3] = mask
        for i in range(8):
            initial_regs[16+i] = i

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("     vfirst", bin(sim.svstate. vfirst))
            sim.gpr.dump()
            self.assertEqual(sim.svstate.vl, 4)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

            # sigh, in sz=0 mode you end up skipping.  have to
            # take that into account, extracting the expected values
            to_expect = []
            for j in range(2):
                for i in range(4):
                    offs = j*4+i
                    skew = i*2+j
                    if mask & (1<<(skew>>1)):
                        to_expect.append(skew)

            print ("expected", to_expect)
            for j in range(2):
                for i in range(4):
                    offs = j*4+i
                    skew = i*2+j
                    if mask & (1<<(offs>>1)):
                        expected = SelectableInt(to_expect.pop(0), 64)
                    else:
                        expected = SelectableInt(0xffffffff, 64)
                    print ("checking", hex(expected.value), "at", offs)
                    self.assertEqual(sim.gpr(8+offs), expected)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None,
                              initial_sprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate,
                              initial_sprs=initial_sprs)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

