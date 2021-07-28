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
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isa.remap_dct_yield import (halfrev2, reverse_bits,
                                                  )
from copy import deepcopy


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def _check_fpregs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.fpr(i), SelectableInt(expected[i], 64))

    def test_sv_load_store_elementstride(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stw/els 4.v, 16(1)",
                        "sv.lwz/els 8.v, 16(1)"]

        note: element stride mode is only enabled when RA is a scalar
        and when the immediate is non-zero

        element stride is computed as:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) * i
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stw/els 4.v, 24(1)",  # scalar r1 + 16 + 24*offs
                        "sv.lwz/els 8.v, 24(1)"]) # scalar r1 + 16 + 24*offs
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

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
            self.assertEqual(sim.gpr(8), SelectableInt(0x1234, 64))
            self.assertEqual(sim.gpr(9), SelectableInt(0x1235, 64))

    def test_sv_load_store_unitstride(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 5, 0, 0x1234",
                        "addi 6, 0, 0x1235",
                        "sv.stw 8.v, 8(1)",
                        "sv.lwz 12.v, 8(1)"]

        note: unit stride mode is only enabled when RA is a scalar.

        unit stride is computed as:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) + LDSTsize * i
        where for stw and lwz, LDSTsize is 4 because it is 32-bit words
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0008",
                        "addi 8, 0, 0x1234",
                        "addi 9, 0, 0x1235",
                        "sv.stw 8.v, 8(1)",  # scalar r1 + 8 + wordlen*offs
                        "sv.lwz 12.v, 8(1)"]) # scalar r1 + 8 + wordlen*offs
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print ("Mem")
            print (mem)
            # contents of memory expected at:
            #    element 0:   r1=0x10, D=8, wordlen=4 => EA = 0x10+8+4*0 = 0x24
            #    element 1:   r1=0x10, D=8, wordlen=4 => EA = 0x10+8+4*8 = 0x28
            # therefore, at address 0x24 ==> 0x1234
            # therefore, at address 0x28 ==> 0x1235
            self.assertEqual(mem, [(24, 0x123500001234)])
            print(sim.gpr(1))
            self.assertEqual(sim.gpr(12), SelectableInt(0x1234, 64))
            self.assertEqual(sim.gpr(13), SelectableInt(0x1235, 64))

    def test_sv_load_store_bitreverse(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "addi 5, 0, 0x101",
                        "addi 6, 0, 0x202",
                        "addi 7, 0, 0x303",
                        "addi 8, 0, 0x404",
                        "sv.stw 5.v, 0(1)",
                        "sv.lwzbr 12.v, 4(1), 2"]

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
                        "sv.lwzbr 12.v, 4(1), 2"]) # bit-reversed
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

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
            self.assertEqual(sim.gpr(12), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(13), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(14), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(15), SelectableInt(0x404, 64))

    def test_sv_load_store_bitreverse2(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "sv.stfs 4.v, 0(1)",
                        "sv.lfsbr 12.v, 4(1), 2"]

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
                        "sv.stfs 4.v, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "sv.lfsbr 12.v, 4(1), 2"]) # bit-reversed
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        fprs = [0] * 32
        scalar_a = 1.3
        scalar_b = -2.0
        fprs[4] = fp64toselectable(1.0)
        fprs[5] = fp64toselectable(2.0)
        fprs[6] = fp64toselectable(3.0)
        fprs[7] = fp64toselectable(4.0)

        # expected results, remember that bit-reversed load has been done
        expected_fprs = deepcopy(fprs)
        expected_fprs[12] = fprs[4] # 0b00 -> 0b00
        expected_fprs[13] = fprs[6] # 0b01 -> 0b10
        expected_fprs[14] = fprs[5] # 0b10 -> 0b01
        expected_fprs[15] = fprs[7] # 0b11 -> 0b11

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                                initial_fprs=fprs)
            mem = sim.mem.dump(printout=False)
            print ("mem dump")
            print (mem)

            print ("FPRs")
            sim.fpr.dump()

            #self.assertEqual(mem, [(16, 0x020200000101),
            #                       (24, 0x040400000303)])
            self._check_fpregs(sim, expected_fprs)

    def test_sv_load_store_remap_matrix(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "addi 5, 0, 0x101",
                        "addi 6, 0, 0x202",
                        "addi 7, 0, 0x303",
                        "addi 8, 0, 0x404",
                        "sv.stw 4.v, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 3, 3, 4, 0, 0",
                        "svremap 1, 1, 2, 0, 0, 0, 0, 1",
                        "sv.lwz 20.v, 0(1)",
                        ]

        REMAPed a LD operation via a Matrix Multiply Schedule,
        which is set up as 3x4 result
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "addi 4, 0, 0x101",
                        "addi 5, 0, 0x202",
                        "addi 6, 0, 0x303",
                        "addi 7, 0, 0x404",
                        "addi 8, 0, 0x505",
                        "addi 9, 0, 0x606",
                        "addi 10, 0, 0x707",
                        "addi 11, 0, 0x808",
                        "addi 12, 0, 0x909",
                        "addi 13, 0, 0xa0a",
                        "addi 14, 0, 0xb0b",
                        "addi 15, 0, 0xc0c",
                        "addi 16, 0, 0xd0d",
                        "addi 17, 0, 0xe0e",
                        "addi 18, 0, 0xf0f",
                        "sv.stw 4.v, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 3, 3, 4, 0, 0",
                        "svremap 1, 1, 2, 0, 0, 0, 0, 1",
                        "sv.lwz 20.v, 0(1)",
                        #"sv.lwzbr 12.v, 4(1), 2", # bit-reversed
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 12 # VL
        svstate.maxvl = 12 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        regs = [0] * 64

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                                initial_regs=regs)
            mem = sim.mem.dump(printout=False)
            print ("Mem")
            print (mem)

            self.assertEqual(mem, [(16, 0x020200000101),
                                   (24, 0x040400000303),
                                   (32, 0x060600000505),
                                   (40, 0x080800000707),
                                   (48, 0x0a0a00000909),
                                   (56, 0x0c0c00000b0b)])
            print(sim.gpr(1))
            # from STs
            self.assertEqual(sim.gpr(4), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(5), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(6), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(7), SelectableInt(0x404, 64))
            self.assertEqual(sim.gpr(8), SelectableInt(0x505, 64))
            self.assertEqual(sim.gpr(9), SelectableInt(0x606, 64))
            self.assertEqual(sim.gpr(10), SelectableInt(0x707, 64))
            self.assertEqual(sim.gpr(11), SelectableInt(0x808, 64))
            # combination of bit-reversed load with a Matrix REMAP
            # schedule
            for i in range(3):
                self.assertEqual(sim.gpr(20+i), SelectableInt(0x101, 64))
                self.assertEqual(sim.gpr(23+i), SelectableInt(0x505, 64))
                self.assertEqual(sim.gpr(26+i), SelectableInt(0x909, 64))
                self.assertEqual(sim.gpr(29+i), SelectableInt(0x202, 64))

    def test_sv_load_store_bitreverse_remap_halfswap(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "addi 4, 0, 0x101",
                        "addi 5, 0, 0x202",
                        "addi 6, 0, 0x303",
                        "addi 7, 0, 0x404",
                        "addi 8, 0, 0x505",
                        "addi 9, 0, 0x606",
                        "addi 10, 0, 0x707",
                        "addi 11, 0, 0x808",
                        "sv.stw 5.v, 0(1)",
                        "svshape 8, 1, 1, 6, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0, 0",
                        "sv.lwzbr 12.v, 4(1), 2"]

        bitreverse LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * bitreverse(i, VL)) << RC

        bitreversal of 0 1 2 3 in binary 0b00 0b01 0b10 0b11
        produces       0 2 1 3 in binary 0b00 0b10 0b01 0b11

        and thus creates the butterfly needed for one iteration of FFT.
        the RC (shift) is to be able to offset the LDs by Radix-2 spans

        on top of the bit-reversal is a REMAP for half-swaps for DCT
        in-place.
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "addi 4, 0, 0x001",
                        "addi 5, 0, 0x102",
                        "addi 6, 0, 0x203",
                        "addi 7, 0, 0x304",
                        "addi 8, 0, 0x405",
                        "addi 9, 0, 0x506",
                        "addi 10, 0, 0x607",
                        "addi 11, 0, 0x708",
                        "sv.stw 4.v, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 8, 1, 1, 6, 0",
                        "svremap 1, 0, 0, 0, 0, 0, 0, 1",
                        #"setvl 0, 0, 8, 0, 1, 1",
                        "sv.lwzbr 12.v, 4(1), 2",  # bit-reversed
                        #"sv.lwz 12.v, 0(1)"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 8 # VL
        svstate.maxvl = 8 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        regs = [0] * 64

        avi = [0x001, 0x102, 0x203, 0x304, 0x405, 0x506, 0x607, 0x708]
        n = len(avi)
        levels = n.bit_length() - 1
        ri = list(range(n))
        ri = [ri[reverse_bits(i, levels)] for i in range(n)]
        av = halfrev2(avi, False)
        av = [av[ri[i]] for i in range(n)]

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                                initial_regs=regs)
            mem = sim.mem.dump(printout=False)
            print ("Mem")
            print (mem)

            self.assertEqual(mem, [(16, 0x010200000001),
                                   (24, 0x030400000203),
                                   (32, 0x050600000405),
                                   (40, 0x070800000607)])
            # from STs
            for i in range(len(avi)):
                print ("st gpr", i, sim.gpr(i+4), hex(avi[i]))
                self.assertEqual(sim.gpr(i+4), avi[i])
            self.assertEqual(sim.gpr(5), SelectableInt(0x102, 64))
            self.assertEqual(sim.gpr(6), SelectableInt(0x203, 64))
            self.assertEqual(sim.gpr(7), SelectableInt(0x304, 64))
            self.assertEqual(sim.gpr(8), SelectableInt(0x405, 64))
            self.assertEqual(sim.gpr(9), SelectableInt(0x506, 64))
            self.assertEqual(sim.gpr(10), SelectableInt(0x607, 64))
            self.assertEqual(sim.gpr(11), SelectableInt(0x708, 64))
            # combination of bit-reversed load with a DCT half-swap REMAP
            # schedule
            for i in range(len(avi)):
                print ("ld gpr", i, sim.gpr(i+12), hex(av[i]))
                self.assertEqual(sim.gpr(i+12), av[i])

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None, initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        if initial_fprs is None:
            initial_fprs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate,
                                  initial_fprs=initial_fprs)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
