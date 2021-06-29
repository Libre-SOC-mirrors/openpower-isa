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

    def test_sv_load_store_bitreverse(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "addi 5, 0, 0x101",
                        "addi 6, 0, 0x202",
                        "addi 7, 0, 0x303",
                        "addi 8, 0, 0x404",
                        "sv.stw 5.v, 0(1)",
                        "sv.lwzbr 9.v, 4(1), 2"]

        note: bitreverse mode is... odd.  it's the butterfly generator
        from Cooley-Tukey FFT:
        https://en.wikipedia.org/wiki/Cooley%E2%80%93Tukey_FFT_algorithm#Data_reordering,_bit_reversal,_and_in-place_algorithms

        bitreverse LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * bitreverse(i, VL)) << RC

        bitreversal of 0 1 2 3 in binary 0b00 0b01 0b10 0b11
        produces       0 2 1 3 in binary 0b00 0b10 0b01 0b11

        and thus creates the butterfly needed for one iteration of FFT.
        the RC (shift) is to be able to offset the LDs by Radix-2 spans
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "addi 5, 0, 0x101",
                        "addi 6, 0, 0x202",
                        "addi 7, 0, 0x303",
                        "addi 8, 0, 0x404",
                        "sv.stw 5.v, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "sv.lwzbr 9.v, 4(1), 2"]) # bit-reversed
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl[0:7] = 4 # VL
        svstate.maxvl[0:7] = 4 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print (mem)

            self.assertEqual(mem, [(16, 0x020200000101),
                                   (24, 0x040400000303)])
            print(sim.gpr(1))
            # from STs
            self.assertEqual(sim.gpr(5), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(6), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(7), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(8), SelectableInt(0x404, 64))
            # r1=0x10, RC=0, offs=4: contents of memory expected at:
            #    element 0:   EA = r1 + bitrev(0b00)*4 => 0x10 + 0b00*4 => 0x10
            #    element 1:   EA = r1 + bitrev(0b01)*4 => 0x10 + 0b10*4 => 0x18
            #    element 2:   EA = r1 + bitrev(0b10)*4 => 0x10 + 0b01*4 => 0x14
            #    element 3:   EA = r1 + bitrev(0b11)*4 => 0x10 + 0b10*4 => 0x1c
            # therefore loaded from (bit-reversed indexing):
            #    r9  => mem[0x10] which was stored from r5
            #    r10 => mem[0x18] which was stored from r6
            #    r11 => mem[0x18] which was stored from r7
            #    r12 => mem[0x1c] which was stored from r8
            self.assertEqual(sim.gpr(9), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(10), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(11), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(12), SelectableInt(0x404, 64))

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
