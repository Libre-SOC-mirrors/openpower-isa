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


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_load_store_elementstride(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 5, 0, 0x1234",
                        "addi 6, 0, 0x1235",
                        "sv.stw/els 5.v, 16(1)",
                        "sv.lwz/els 9.v, 16(1)"]

        note: element stride mode is only enabled when RA is a scalar
        and when the immediate is non-zero

        element stride is computed as:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) * i
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 5, 0, 0x1234",
                        "addi 6, 0, 0x1235",
                        "sv.stw/els 5.v, 24(1)",  # scalar r1 + 16 + 24*offs
                        "sv.lwz/els 9.v, 24(1)"]) # scalar r1 + 16 + 24*offs
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print (mem)
            # contents of memory expected at:
            #    element 0:   r1=0x10, D=24, => EA = 0x10+24*0 = 16 (0x10)
            #    element 1:   r1=0x10, D=24, => EA = 0x10+24*1 = 40 (0x28)
            # therefore, at address 0x10 ==> 0x1234
            # therefore, at address 0x28 ==> 0x1235
            expected_mem = [(16, 0x1234),
                            (40, 0x1235)]
            self.assertEqual(mem, expected_mem)
            print(sim.gpr(1))
            self.assertEqual(sim.gpr(9), SelectableInt(0x1234, 64))
            self.assertEqual(sim.gpr(10), SelectableInt(0x1235, 64))

    def test_sv_load_store_unitstride(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 5, 0, 0x1234",
                        "addi 6, 0, 0x1235",
                        "sv.stw 5.v, 8(1)",
                        "sv.lwz 9.v, 8(1)"]

        note: unit stride mode is only enabled when RA is a scalar.

        unit stride is computed as:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) + LDSTsize * i
        where for stw and lwz, LDSTsize is 4 because it is 32-bit words
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 5, 0, 0x1234",
                        "addi 6, 0, 0x1235",
                        "sv.stw 5.v, 8(1)",  # scalar r1 + 8 + wordlen*offs
                        "sv.lwz 9.v, 8(1)"]) # scalar r1 + 8 + wordlen*offs
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print (mem)
            # contents of memory expected at:
            #    element 0:   r1=0x10, D=8, wordlen=4 => EA = 0x10+8+4*0 = 0x24
            #    element 1:   r1=0x10, D=8, wordlen=4 => EA = 0x10+8+4*8 = 0x28
            # therefore, at address 0x24 ==> 0x1234
            # therefore, at address 0x28 ==> 0x1235
            self.assertEqual(mem, [(24, 0x123500001234)])
            print(sim.gpr(1))
            self.assertEqual(sim.gpr(9), SelectableInt(0x1234, 64))
            self.assertEqual(sim.gpr(10), SelectableInt(0x1235, 64))

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
