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
