import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.isa.remap_dct_yield import halfrev2, reverse_bits
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm


def write_byte(mem, addr, val):
    addr, offs = (addr // 8)*8, (addr % 8)*8
    mask = (0xff << offs)
    value = mem.get(addr, 0) & ~mask
    value = value | (val << offs)
    mem[addr] = value & 0xffff_ffff_ffff_ffff


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def _check_fpregs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.fpr(i), SelectableInt(expected[i], 64))

    def test_sv_load_store_strncpy(self):
        """>>> lst = [
                    ]

        strncpy using post-increment ld/st, sv.bc, and data-dependent ffirst.
        note that /lf (Load-Fault) mode is not set in this example when it
        should be. however implementing Load-Fault in ISACaller is tricky
        (requires implementing multiple hardware models)
        """
        maxvl = 4
        lst = SVP64Asm(
            [
                "mtspr 9, 3",                   # move r3 to CTR
                "addi 0,0,0",                   # initialise r0 to zero
                # chr-copy loop starts here:
                #   for (i = 0; i < n && src[i] != '\0'; i++)
                #        dest[i] = src[i];
                # VL (and r1) = MIN(CTR,MAXVL=4)
                "setvl 1,0,%d,0,1,1" % maxvl,
                # load VL bytes (update r10 addr)
                "sv.lbzu/pi *16, 1(10)",         # should be /lf here as well
                "sv.cmpi/ff=eq/vli *0,1,*16,0",  # cmp against zero, truncate VL
                # store VL bytes (update r12 addr)
                "sv.stbu/pi *16, 1(12)",
                "sv.bc/all 0, *2, -0x1c",       # test CTR, stop if cmpi failed
                # zeroing loop starts here:
                #   for ( ; i < n; i++)
                #       dest[i] = '\0';
                # VL (and r1) = MIN(CTR,MAXVL=4)
                "setvl 1,0,%d,0,1,1" % maxvl,
                # store VL zeros (update r12 addr)
                "sv.stbu/pi 0, 1(12)",
                "sv.bc 16, *0, -0xc",           # dec CTR by VL, stop at zero
            ]
        )
        lst = list(lst)

        tst_string = "hello\x00bye\x00"
        initial_regs = [0] * 32
        initial_regs[3] = len(tst_string)  # including the zero
        initial_regs[10] = 16  # load address
        initial_regs[12] = 40  # store address

        # some memory with identifying garbage in it
        initial_mem = {16: 0xf0f1_f2f3_f4f5_f6f7,
                       24: 0x4041_4243_4445_4647,
                       40: 0x8081_8283_8485_8687,
                       48: 0x9091_9293_9495_9697,
                       }

        for i, c in enumerate(tst_string):
            write_byte(initial_mem, 16+i, ord(c))

        # now get the expected results: copy the string to the other address,
        # but terminate at first zero (strncpy, duh)
        expected_mem = deepcopy(initial_mem)
        copyzeros = False
        strlen = 0
        for i, c in enumerate(tst_string):
            c = ord(c)
            if not copyzeros:
                write_byte(expected_mem, 40+i, c)
                strlen = i+1
            else:
                write_byte(expected_mem, 40+i, 0)
            if c == 0:
                copyzeros = True

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem,
                                       initial_regs=initial_regs)
            mem = sim.mem.dump(printout=True, asciidump=True)
            #print (mem)
            # contents of memory expected at:
            #    element 0:   r1=0x10, D=24, => EA = 0x10+24*0 = 16 (0x10)
            #    element 1:   r1=0x10, D=24, => EA = 0x10+24*1 = 40 (0x28)
            # therefore, at address 0x10 ==> 0x1234
            # therefore, at address 0x28 ==> 0x1235
            for (k, val) in expected_mem.items():
                print("mem, val", k, hex(val))
            self.assertEqual(mem, list(expected_mem.items()))
            print(sim.gpr(1))
            # reg 10 (the LD EA) is expected to be nearest
            # 16 + strlen, rounded up
            rounded = ((strlen+maxvl-1) // maxvl) * maxvl
            self.assertEqual(sim.gpr(10), SelectableInt(16+rounded, 64))
            # whereas reg 10 (the ST EA) is expected to be 40+strlen
            self.assertEqual(sim.gpr(12), SelectableInt(
                40+len(tst_string), 64))

    def test_sv_load_store_postinc(self):
        """>>> lst = ["addi 20, 0, 0x0010",
                        "addi 3, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stwu/pi *4, 24(20)",
                        "sv.lwu/pi *8, 24(20)"]

        element stride is computed as:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) * i

        load-update with post-increment will do this however:
        for i in range(VL):
            *vector = MEM(RA)
            EA = (RA|0) + EXTS(D)
            RA = EA # update RA *after*

        whereas without post-increment it would be:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) # EA calculated (and used) *BEFORE* load
            *vector = MEM(EA)
            RA = EA # still updated after but it's used before
        """
        lst = SVP64Asm(["addi 20, 0, 0x0010",
                        "addi 22, 0, 0x0010",
                        "addi 3, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stwu/pi *4, 24(22)",  # scalar r22 += 24 on update
                        "sv.lwzu/pi *8, 24(20)"   # scalar r20 += 24 on update
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print(mem)
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
            # reg 20 (the EA) is expected to be the initial 16,
            # plus 2x24 (2 lots of immediates).  16+2*24=64
            self.assertEqual(sim.gpr(20), SelectableInt(64, 64))
            # likewise, reg 22 - for the store - also 16+2*24.
            self.assertEqual(sim.gpr(22), SelectableInt(64, 64))

    def test_sv_load_store_elementstride(self):
        """>>> lst = ["addi 2, 0, 0x0010",
                        "addi 3, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stw/els *4, 16(2)",
                        "sv.lwz/els *8, 16(2)"]

        note: element stride mode is only enabled when RA is a scalar
        and when the immediate is non-zero

        element stride is computed as:
        for i in range(VL):
            EA = (RA|0) + EXTS(D) * i
        """
        lst = SVP64Asm(["addi 2, 0, 0x0010",
                        "addi 3, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stw/els *4, 24(2)",  # scalar r1 + 16 + 24*offs
                        "sv.lwz/els *8, 24(2)"])  # scalar r1 + 16 + 24*offs
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print(mem)
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
                        "sv.stw *8, 8(1)",
                        "sv.lwz *12, 8(1)"]

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
                        "sv.stw *8, 8(1)",  # scalar r1 + 8 + wordlen*offs
                        "sv.lwz *12, 8(1)"])  # scalar r1 + 8 + wordlen*offs
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print("Mem")
            print(mem)
            # contents of memory expected at:
            #    element 0:   r1=0x10, D=8, wordlen=4 => EA = 0x10+8+4*0 = 0x24
            #    element 1:   r1=0x10, D=8, wordlen=4 => EA = 0x10+8+4*8 = 0x28
            # therefore, at address 0x24 ==> 0x1234
            # therefore, at address 0x28 ==> 0x1235
            self.assertEqual(mem, [(24, 0x123500001234)])
            print(sim.gpr(1))
            self.assertEqual(sim.gpr(12), SelectableInt(0x1234, 64))
            self.assertEqual(sim.gpr(13), SelectableInt(0x1235, 64))

    @unittest.skip("deprecated, needs Scalar LDST-shifted")
    def test_sv_load_store_shifted(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "addi 4, 0, 0x101",
                        "addi 5, 0, 0x202",
                        "addi 6, 0, 0x303",
                        "addi 7, 0, 0x404",
                        "sv.stw *4, 0(1)",
                        "sv.lwzsh *12, 4(1), 2"]

        shifted LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * i) << RC
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "addi 4, 0, 0x101",
                        "addi 5, 0, 0x202",
                        "addi 6, 0, 0x303",
                        "addi 7, 0, 0x404",
                        "sv.stw *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "sv.lwzsh *12, 4(1), 2"])  # bit-reversed
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            mem = sim.mem.dump(printout=False)
            print(mem)

            self.assertEqual(mem, [(16, 0x020200000101),
                                   (24, 0x040400000303)])
            print(sim.gpr(1))
            # from STs
            self.assertEqual(sim.gpr(4), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(5), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(6), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(7), SelectableInt(0x404, 64))
            # r1=0x10, RC=0, offs=4: contents of memory expected at:
            #    element 0:   EA = r1 + 0b00*4 => 0x10 + 0b00*4 => 0x10
            #    element 1:   EA = r1 + 0b01*4 => 0x10 + 0b01*4 => 0x18
            #    element 2:   EA = r1 + 0b10*4 => 0x10 + 0b10*4 => 0x14
            #    element 3:   EA = r1 + 0b11*4 => 0x10 + 0b11*4 => 0x1c
            # therefore loaded from (bit-reversed indexing):
            #    r9  => mem[0x10] which was stored from r5
            #    r10 => mem[0x18] which was stored from r6
            #    r11 => mem[0x18] which was stored from r7
            #    r12 => mem[0x1c] which was stored from r8
            self.assertEqual(sim.gpr(12), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(13), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(14), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(15), SelectableInt(0x404, 64))

    @unittest.skip("deprecated, needs Scalar LDST-shifted")
    def test_sv_load_store_shifted_fp(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "addi 4, 0, 0x101",
                        "addi 5, 0, 0x202",
                        "addi 6, 0, 0x303",
                        "addi 7, 0, 0x404",
                        "sv.std *4, 0(1)",
                        "sv.lfdbr *12, 4(1), 2"]

        shifted LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * i) << RC
        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "addi 4, 0, 0x101",
                        "addi 5, 0, 0x202",
                        "addi 6, 0, 0x303",
                        "addi 7, 0, 0x404",
                        "sv.std *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "sv.lfdsh *12, 8(1), 2"])  # shifted
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        fprs = [0] * 32

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            mem = sim.mem.dump(printout=False)
            print(mem)

            self.assertEqual(mem, [(16, 0x101),
                                   (24, 0x202),
                                   (32, 0x303),
                                   (40, 0x404),
                                   ])
            print(sim.gpr(1))
            # from STs
            self.assertEqual(sim.gpr(4), SelectableInt(0x101, 64))
            self.assertEqual(sim.gpr(5), SelectableInt(0x202, 64))
            self.assertEqual(sim.gpr(6), SelectableInt(0x303, 64))
            self.assertEqual(sim.gpr(7), SelectableInt(0x404, 64))
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
            self.assertEqual(sim.fpr(12), SelectableInt(0x101, 64))
            self.assertEqual(sim.fpr(13), SelectableInt(0x202, 64))
            self.assertEqual(sim.fpr(14), SelectableInt(0x303, 64))
            self.assertEqual(sim.fpr(15), SelectableInt(0x404, 64))

    @unittest.skip("deprecated, needs Scalar LDST-shifted")
    def test_sv_load_store_shifted2(self):
        """>>> lst = ["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0004",
                        "addi 3, 0, 0x0002",
                        "sv.stfs *4, 0(1)",
                        "sv.lfssh *12, 4(1), 2"]

        shifted LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * i) << RC

        """
        lst = SVP64Asm(["addi 1, 0, 0x0010",
                        "addi 2, 0, 0x0000",
                        "sv.stfs *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "sv.lfssh *12, 4(1), 2"])  # shifted (by zero, but hey)
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        fprs = [0] * 32
        scalar_a = 1.3
        scalar_b = -2.0
        fprs[4] = fp64toselectable(1.0)
        fprs[5] = fp64toselectable(2.0)
        fprs[6] = fp64toselectable(3.0)
        fprs[7] = fp64toselectable(4.0)

        # expected results, remember that bit-reversed load has been done
        expected_fprs = deepcopy(fprs)
        expected_fprs[12] = fprs[4]  # 0b00 -> 0b00
        expected_fprs[13] = fprs[5]  # 0b10 -> 0b01
        expected_fprs[14] = fprs[6]  # 0b01 -> 0b10
        expected_fprs[15] = fprs[7]  # 0b11 -> 0b11

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            mem = sim.mem.dump(printout=False)
            print("mem dump")
            print(mem)

            print("FPRs")
            sim.fpr.dump()

            # self.assertEqual(mem, [(16, 0x020200000101),
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
                        "sv.stw *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 3, 3, 4, 0, 0",
                        "svremap 1, 1, 2, 0, 0, 0, 0",
                        "sv.lwz *20, 0(1)",
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
                        "sv.stw *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 3, 3, 4, 0, 0",
                        "svremap 1, 1, 2, 0, 0, 0, 0",
                        "sv.lwz *20, 0(1)",
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 12  # VL
        svstate.maxvl = 12  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        regs = [0] * 64

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=regs)
            mem = sim.mem.dump(printout=False)
            print("Mem")
            print(mem)

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
                        "sv.stw *5, 0(1)",
                        "svshape 8, 1, 1, 6, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                        "sv.lwz/els *12, 4(1)"]

        shifted LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * i) << RC

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
                        "sv.stw *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 8, 1, 1, 6, 0",
                        "svremap 1, 0, 0, 0, 0, 0, 0",
                        #"setvl 0, 0, 8, 0, 1, 1",
                        "sv.lwz/els *12, 4(1)",
                        #"sv.lwz *12, 0(1)"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 8  # VL
        svstate.maxvl = 8  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

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
            print("Mem")
            print(mem)

            self.assertEqual(mem, [(16, 0x010200000001),
                                   (24, 0x030400000203),
                                   (32, 0x050600000405),
                                   (40, 0x070800000607)])
            # from STs
            for i in range(len(avi)):
                print("st gpr", i, sim.gpr(i+4), hex(avi[i]))
            for i in range(len(avi)):
                self.assertEqual(sim.gpr(i+4), avi[i])
            # combination of bit-reversed load with a DCT half-swap REMAP
            # schedule
            for i in range(len(avi)):
                print("ld gpr", i, sim.gpr(i+12), hex(av[i]))
            for i in range(len(avi)):
                self.assertEqual(sim.gpr(i+12), av[i])

    def test_sv_load_store_bitreverse_remap_halfswap_idct(self):
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
                        "sv.stw *5, 0(1)",
                        "svshape 8, 1, 1, 6, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                        "sv.lwz/els *12, 4(1)"]

        bitreverse LD is computed as:
        for i in range(VL):
            EA = (RA|0) + (EXTS(D) * LDSTsize * i) << RC

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
                        "sv.stw *4, 0(1)",  # scalar r1 + 0 + wordlen*offs
                        "svshape 8, 1, 1, 14, 0",
                        "svremap 16, 0, 0, 0, 0, 0, 0",
                        #"setvl 0, 0, 8, 0, 1, 1",
                        "sv.lwz/els *12, 4(1)",
                        #"sv.lwz *12, 0(1)"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl = 8  # VL
        svstate.maxvl = 8  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        regs = [0] * 64

        avi = [0x001, 0x102, 0x203, 0x304, 0x405, 0x506, 0x607, 0x708]
        n = len(avi)
        levels = n.bit_length() - 1
        ri = list(range(n))
        ri = [ri[reverse_bits(i, levels)] for i in range(n)]
        av = [avi[ri[i]] for i in range(n)]
        av = halfrev2(av, True)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_regs=regs)
            mem = sim.mem.dump(printout=False)
            print("Mem")
            print(mem)

            self.assertEqual(mem, [(16, 0x010200000001),
                                   (24, 0x030400000203),
                                   (32, 0x050600000405),
                                   (40, 0x070800000607)])
            # from STs
            for i in range(len(avi)):
                print("st gpr", i, sim.gpr(i+4), hex(avi[i]))
            for i in range(len(avi)):
                self.assertEqual(sim.gpr(i+4), avi[i])
            # combination of bit-reversed load with a DCT half-swap REMAP
            # schedule
            for i in range(len(avi)):
                print("ld gpr", i, sim.gpr(i+12), hex(av[i]))
            for i in range(len(avi)):
                self.assertEqual(sim.gpr(i+12), av[i])

    def test_sv_load_dd_ffirst_excl(self):
        """data-dependent fail-first on LD/ST, exclusive (VLi=0)
        """
        lst = SVP64Asm(
            [
                # load VL bytes but test if they are zero and truncate
                "sv.lbz/ff=RC1 *16, 1(10)", # deliberately offset by 1
            ]
        )
        lst = list(lst)

        # SVSTATE (in this case, VL=8)
        svstate = SVP64State()
        svstate.vl = 8  # VL
        svstate.maxvl = 8  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        tst_string = "hel\x00e\x00"
        initial_regs = [0] * 32
        initial_regs[3] = len(tst_string)  # including the zero
        initial_regs[10] = 16  # load address
        initial_regs[12] = 40  # store address
        for i in range(8): # set to garbage
            initial_regs[16+i] = (0xbeef00) + i  # identifying garbage

        # calculate expected regs
        expected_regs = deepcopy(initial_regs)
        for i, c in enumerate(tst_string[1:]): # note the offset 1(10)
            c = ord(c)
            if c == 0: break # strcpy stop at NUL
            expected_regs[16+i] = c

        # some memory with identifying garbage in it
        initial_mem = {16: 0xf0f1_f2f3_f4f5_f6f7,
                       24: 0x4041_4243_4445_4647,
                       40: 0x8081_8283_8485_8687,
                       48: 0x9091_9293_9495_9697,
                       }

        for i, c in enumerate(tst_string):
            write_byte(initial_mem, 16+i, ord(c))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_mem=initial_mem,
                                       initial_regs=initial_regs)
            mem = sim.mem.dump(printout=True, asciidump=True)
            print (mem)
            self.assertEqual(sim.svstate.vl, 2)
            for i in range(len(expected_regs)):
                print ("%i %x %x" % (i, sim.gpr(i).value, expected_regs[i]))
                self.assertEqual(sim.gpr(i), expected_regs[i])

    def test_sv_load_dd_ffirst_incl(self):
        """data-dependent fail-first on LD/ST, inclusive (/vli)
        """
        lst = SVP64Asm(
            [
                # load VL bytes but test if they are zero and truncate
                "sv.lbz/ff=RC1/vli *16, 1(10)", # deliberately offset by 1
            ]
        )
        lst = list(lst)

        # SVSTATE (in this case, VL=8)
        svstate = SVP64State()
        svstate.vl = 8  # VL
        svstate.maxvl = 8  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        tst_string = "hel\x00e\x00"
        initial_regs = [0] * 32
        initial_regs[3] = len(tst_string)  # including the zero
        initial_regs[10] = 16  # load address
        initial_regs[12] = 40  # store address
        for i in range(8): # set to garbage
            initial_regs[16+i] = (0xbeef00) + i  # identifying garbage

        # calculate expected regs
        expected_regs = deepcopy(initial_regs)
        for i, c in enumerate(tst_string[1:]): # note the offset 1(10)
            c = ord(c)
            expected_regs[16+i] = c
            if c == 0: break # strcpy stop at NUL *including* NUL

        # some memory with identifying garbage in it
        initial_mem = {16: 0xf0f1_f2f3_f4f5_f6f7,
                       24: 0x4041_4243_4445_4647,
                       40: 0x8081_8283_8485_8687,
                       48: 0x9091_9293_9495_9697,
                       }

        for i, c in enumerate(tst_string):
            write_byte(initial_mem, 16+i, ord(c))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_mem=initial_mem,
                                       initial_regs=initial_regs)
            mem = sim.mem.dump(printout=True, asciidump=True)
            print (mem)
            self.assertEqual(sim.svstate.vl, 3)
            for i in range(len(expected_regs)):
                print ("%i %x %x" % (i, sim.gpr(i).value, expected_regs[i]))
                self.assertEqual(sim.gpr(i), expected_regs[i])

    def test_sv_load_dd_ffirst_incl(self):
        """data-dependent fail-first on LD/ST, inclusive (/vli)
        performs linked-list walking
        """
        lst = SVP64Asm(
            [
                # load VL bytes but test if they are zero and truncate
                "sv.ld/ff=RC1/vli *17, 8(*16)", # offset 8 to next addr
            ]
        )
        lst = list(lst)

        # SVSTATE (in this case, VL=8)
        svstate = SVP64State()
        svstate.vl = 8  # VL
        svstate.maxvl = 8  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        for i in range(8): # set to garbage
            initial_regs[16+i] = (0xbeef00) + i  # identifying garbage
        initial_regs[16] = 24  # data starting point

        # some memory with addresses to get from.  all locations are offset 8
        initial_mem = { 24: 0xfeed0001, 32: 48, # data @ 24, ptr @ 32+8 -> 48
                        48: 0xfeed0002, 56: 8 , # data @ 48, ptr @ 48+8 -> 8
                        8 : 0xfeed0003, 16: 80, # data @ 16, ptr @ 16+8 -> 80
                        80: 0xfeed0004, 88: 0,  # data @ 80, ptr @ 80+8 -> 0
                      }

        # calculate expected regs
        expected_regs = deepcopy(initial_regs)
        ptr_addr = 24
        i = 0
        while True: # VLI needs break at end
            expected_regs[16+i] = ptr_addr
            print ("expected regs", 16+i, hex(expected_regs[16+i]))
            i += 1
            if ptr_addr == 0: break
            print ("ptr_addr", ptr_addr)
            ptr_addr = initial_mem[ptr_addr+8] # linked-list walk, offset 8

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_mem=initial_mem,
                                       initial_regs=initial_regs)
            mem = sim.mem.dump(printout=True, asciidump=True)
            print (mem)
            self.assertEqual(sim.svstate.vl, 4)
            for i in range(len(expected_regs)):
                print ("%i %x %x" % (i, sim.gpr(i).value, expected_regs[i]))
                self.assertEqual(sim.gpr(i), expected_regs[i])

    def test_sv_load_update_dd_ffirst_incl(self):
        """data-dependent fail-first on LD/ST-with-update, inclusive (/vli)
        performs linked-list walking, and stores the Effective Address
        *behind* where it is picked up (on the next element-iteration).
        """
        lst = SVP64Asm(
            [
                # load VL bytes but test if they are zero and truncate
                "sv.ldu/ff=RC1/vli *17, 8(*16)", # offset 8 to next addr
            ]
        )
        lst = list(lst)

        # SVSTATE (in this case, VL=8)
        svstate = SVP64State()
        svstate.vl = 8  # VL
        svstate.maxvl = 8  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        initial_regs = [0] * 32
        for i in range(8): # set to garbage
            initial_regs[16+i] = (0xbeef00) + i  # identifying garbage
        initial_regs[16] = 24  # data starting point

        # some memory with addresses to get from.  all locations are offset 8
        initial_mem = { 24: 0xfeed0001, 32: 48, # data @ 24, ptr @ 32+8 -> 48
                        48: 0xfeed0002, 56: 8 , # data @ 48, ptr @ 48+8 -> 8
                        8 : 0xfeed0003, 16: 80, # data @ 16, ptr @ 16+8 -> 80
                        80: 0xfeed0004, 88: 0,  # data @ 80, ptr @ 80+8 -> 0
                      }

        # calculate expected regs
        expected_regs = deepcopy(initial_regs)
        i = 0
        while True: # VLI needs break at end
            ptr_addr = expected_regs[16+i]
            newptr_addr = initial_mem[ptr_addr+8] # linked-list walk, offset 8
            expected_regs[17+i] = newptr_addr
            expected_regs[16+i] = ptr_addr+8
            print ("expected regs", 16+i, hex(expected_regs[16+i]))
            i += 1
            print ("ptr_addr", ptr_addr)
            if newptr_addr == 0: break # VLI stop at end

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_mem=initial_mem,
                                       initial_regs=initial_regs)
            mem = sim.mem.dump(printout=True, asciidump=True)
            print (mem)
            self.assertEqual(sim.svstate.vl, 4)
            for i in range(len(expected_regs)):
                print ("%i %x %x" % (i, sim.gpr(i).value, expected_regs[i]))
                self.assertEqual(sim.gpr(i), expected_regs[i])

    def run_tst_program(self, prog, initial_regs=None,
                        svstate=None, initial_fprs=None,
                        initial_mem=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        if initial_fprs is None:
            initial_fprs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate,
                            initial_fprs=initial_fprs,
                            mem=initial_mem)
        print("GPRs")
        simulator.gpr.dump()
        print("FPRs")
        simulator.fpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
