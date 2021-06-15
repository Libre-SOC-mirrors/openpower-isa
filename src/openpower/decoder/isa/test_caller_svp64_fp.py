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

    def test_sv_fpload(self):
        """>>> lst = ["sv.lfsx 2.v, 0, 0.v"
                        ]
        """
        lst = SVP64Asm(["sv.lfsx 2.v, 0, 0.v"
                        ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        # memory addresses 0x0000 and 0x0008
        initial_mem = {0x0000: (0x42013333, 8), # 32.3
                       0x0008: (0xC0200000, 8), # -2.5
                        }

        # and RB will move on from 0 for first iteration to 1 in 2nd
        # therefore we must point GPR(0) at initial mem 0x0000
        # and GPR(1) at initial mem 0x0008
        initial_regs = [0] * 32
        initial_regs[0] = 0x0000 # points at memory address 0x0000 (element 0)
        initial_regs[1] = 0x0008 # points at memory address 0x0008 (element 1)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs,
                                                svstate=svstate,
                                                initial_mem=initial_mem)
            print(sim.fpr(2))
            print(sim.fpr(3))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0xC004000000000000, 64))

    def test_fp_single_ldst(self):
        """>>> lst = ["sv.lfsx 0.v, 0, 4.v",   # load fp 1/2 from mem 0/8
                      "sv.stfsu 0.v, 16(4.v)", # store fp 1/2, update RA *twice*
                      "sv.lfs 3.v, 0(4.v)",   # re-load from UPDATED r4/r5
                     ]

        This is quite an involved (deceptively simple looking) test.
        The sv.stfsu is creating a *Vector* of Effective Addresses, and
        consequently is updating (writing) a *Vector* of EAs into the GPR.

        Walkthrough:

        1) sv.lfsx 0.v, 0, 4.v    VL=2 so there are *two* lfsx operations
                lfsx 0, 0, 4      loads from MEM[GPR(4)], stores in FPR(0)
                lfsx 1, 0, 5      loads from MEM[GPR(5)], stores in FPR(1)

        2) sv.stfsu 0.v, 16(4.v)  again, VL=2 so there are two ST-FP-update ops
                stfsu 0, 16(4)    EA=GPR(4)+16, FPR(0) to MEM[EA], EA to GPR(4)
                stfsu 1, 16(5)    EA=GPR(5)+16, FPR(0) to MEM[EA], EA to GPR(5)

           note that there are **TWO** FP writes to memory, and **TWO**
           writes of the calculated Effective Address to GPR, in regs 4 and 5
           GPRs 4 and 5 are *overwritten*.

        3) sv.lfs 3.v, 0(4.v)     VL=2, so two immediate-LDs
                lfs 3, 0(4)       EA=GPR(4)+0, FPR(3) = MEM[EA]
                lfs 4, 0(5)       EA=GPR(5)+0, FPR(4) = MEM[EA]

           here we have loaded from the *overwritten* GPRs 4 and 5.

        strictly speaking this unit test should also verify the contents
        of the memory locations 0x10 and 0x18, which should contain the
        single-precision FP numbers in the bottom 4 bytes.  TODO
        """
        lst = SVP64Asm(["sv.lfsx 0.v, 0, 4.v",
                        "sv.stfsu 0.v, 16(4.v)",
                        "sv.lfs 3.v, 0(4.v)",
                     ])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        # memory addresses 0x0000 and 0x0008
        initial_mem = {0x0000: (0x42013333, 8), # 32.3
                       0x0008: (0xC0200000, 8), # -2.5
                       0x0020: (0x1828384822324252, 8),
                        }

        # and RB will move on from 0 for first iteration to 1 in 2nd
        # therefore we must point GPR(4) at initial mem 0x0000
        # and GPR(5) at initial mem 0x0008
        initial_regs = [0] * 32
        initial_regs[4] = 0x0000 # points at memory address 0x0000 (element 0)
        initial_regs[5] = 0x0008 # points at memory address 0x0008 (element 1)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs,
                                                svstate=svstate,
                                                initial_mem=initial_mem)
            print("FPR 1", sim.fpr(0))
            print("FPR 2", sim.fpr(1))
            print("GPR 1", sim.gpr(4)) # should be 0x10 due to update
            print("GPR 2", sim.gpr(5)) # should be 0x18 due to update
            self.assertEqual(sim.gpr(4), SelectableInt(0x10, 64))
            self.assertEqual(sim.gpr(5), SelectableInt(0x18, 64))
            self.assertEqual(sim.fpr(0), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(1), SelectableInt(0xC004000000000000, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(4), SelectableInt(0xC004000000000000, 64))

    def test_sv_fpadd(self):
        """>>> lst = ["sv.fadds 6.v, 2.v, 4.v"
                        ]
        """
        lst = SVP64Asm(["sv.fadds 6.v, 2.v, 4.v"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        fprs[2] = 0xC040266660000000 # -32.3
        fprs[3] = 0xC040266660000000 # -32.3
        fprs[4] = 0x4040266660000000 # +32.3
        fprs[5] = 0xC040266660000000 # -32.3

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            self.assertEqual(sim.fpr(6), SelectableInt(0x0, 64))
            self.assertEqual(sim.fpr(7), SelectableInt(0xc050266660000000, 64))

    def test_sv_fpmadds(self):
        """>>> lst = ["sv.fmadds 6.v, 2.v, 4.v, 8"
                        ]
            two vector mul-adds with a scalar in f8
            * fp6 = fp2 * fp4 + f8 = 7.0 * 2.0 - 2.0 = 12.0
            * fp7 = fp3 * fp5 + f8 = 7.0 * 2.0 - 2.0 = 12.0
        """
        lst = SVP64Asm(["sv.fmadds 6.v, 2.v, 4.v, 8"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        fprs[2] = 0x401C000000000000  # 7.0
        fprs[3] = 0xC02399999999999A  # -9.8
        fprs[4] = 0x4000000000000000  # 2.0
        fprs[5] = 0xC040266660000000 # -32.3
        fprs[6] = 0x4000000000000000  # 2.0
        fprs[7] = 0x4000000000000000  # 2.0
        fprs[8] = 0xc000000000000000  # -2.0

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            self.assertEqual(sim.fpr(6), SelectableInt(0x4028000000000000, 64))
            self.assertEqual(sim.fpr(7), SelectableInt(0x4073a8a3c0000000, 64))

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None,
                              initial_mem=None,
                              initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                                                initial_fprs=initial_fprs,
                                                svstate=svstate)

        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()

        return simulator


if __name__ == "__main__":
    unittest.main()
