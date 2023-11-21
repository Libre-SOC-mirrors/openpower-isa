"""Implementation of chacha20 core in SVP64
Copyright (C) 2022,2023 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
Licensed under the LGPLv3+
Funded by NLnet NGI-ASSURE under EU grant agreement No 957073.
* https://nlnet.nl/project/LibreSOC-GigabitRouter/
* https://bugs.libre-soc.org/show_bug.cgi?id=965
* https://libre-soc.org/openpower/sv/cookbook/pospopcount/
"""

import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
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



class PosPopCountTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

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
