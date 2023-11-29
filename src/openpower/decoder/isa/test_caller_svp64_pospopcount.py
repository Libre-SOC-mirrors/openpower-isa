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

    def test_sv_pospopcount(self):
        """positional popcount
        """
        lst = SVP64Asm(
            [
                "mtspr 9, 3",               # move r3 to CTR
                # VL = MIN(CTR,MAXVL=8), Rc=1 (CR0 set if CTR ends)
                "setvl 3,0,8,0,1,1",        # set MVL=8, VL=CTR and CR0 (Rc=1)
                # load VL bytes (update r4 addr) but compressed (dw=8)
                "addi 6, 0, 0",             # initialise r6 to zero
                "sv.lbzu/pi/dw=8 *6, 1(4)", # should be /lf here as well
                # gather performs the transpose (which gets us to positional..)
                "gbbd 8,6",
                # now those bits have been turned around, popcount and sum them
                "setvl 0,0,8,0,1,1",        # set MVL=VL=8
                "sv.popcntd/sw=8 *24,*8",   # do the (now transposed) popcount
                "sv.add *16,*16,*24",       # and accumulate in results
                # branch back if still CTR
                "sv.bc/all 16, *0, -0x28", # CTR mode, reduce VL by CTR
            ]
        )
        lst = list(lst)

        tst_array = [23,19,25,189,76,255,32,191,67,205,0,39,107]
        #tst_array = [1,2,3,4,5,6,7,8,9,10,11,12,13]
        #tst_array = [254] * 10
        #tst_array = [1,2,3,4,5,6,7,8,9,10,11,12,13]
        #tst_array = [1,2,3,4,5,6,7,8,9,10,11,12,13]
        #tst_array = [1,2,3,4,5,6,7,8,9]
        #tst_array = list(range(240))
        initial_regs = [0] * 64
        initial_regs[3] = len(tst_array)
        initial_regs[4] = 256-8  # load address

        # some memory with identifying garbage in it
        initial_mem = {16: 0xf0f1_f2f3_f4f5_f6f7,
                       24: 0x4041_4243_4445_4647,
                       40: 0x8081_8283_8485_8687,
                       48: 0x9091_9293_9495_9697,
                       248: 0xffff_aaaa_cccc_eeee,
                       256: 0xa0a1_a2a3_a4a5_a6a7,
                       }

        # overwrite the garbage with the test data
        for i, c in enumerate(tst_array):
            write_byte(initial_mem, initial_regs[4]+i, c)

        for i, c in enumerate(tst_array):
            print ("array", i, bin(c), c)

        # now get the expected results: do a simple pospopcount
        expected = [0]*8
        for c in tst_array:
            for j in range(8):
                expected[j] += (c >> j) & 1

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem,
                                       initial_regs=initial_regs)
            mem = sim.mem.dump(printout=True, asciidump=True)
            print (mem)
            # contents of memory expected at:
            #    element 0:   r1=0x10, D=24, => EA = 0x10+24*0 = 16 (0x10)
            #    element 1:   r1=0x10, D=24, => EA = 0x10+24*1 = 40 (0x28)
            # therefore, at address 0x10 ==> 0x1234
            # therefore, at address 0x28 ==> 0x1235
            for (k, val) in enumerate(expected):
                print("idx, count, reg", k, val, sim.gpr(k+16).value)
            for (k, val) in enumerate(expected):
                self.assertEqual(val, sim.gpr(k+16))

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
        return simulator


if __name__ == "__main__":
    unittest.main()
