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

    def test_sv_fpmadds(self):
        """>>> lst = ["sv.ffmadds 12.v, 2.v, 4.v, 12.v"
                        ]
            two vector mul-adds, two vector mul-subs
            * fp12 = fp2 * fp4 + f12 = 7.0 * -2.0 + 2.0 = -12.0
            * fp13 = fp3 * fp5 + f13 = (-9.8 * 2.0) + -32.3 = -51.9
            * fp14 = -(fp2 * fp4) + f14 = -(7.0 * -2.0) + 2.0 = -16.0
            * fp15 = -(fp3 * fp5) + f15 = -(-9.8 * 2) + -32.3 = -12.7
        """
        lst = SVP64Asm(["sv.ffmadds 12.v, 2.v, 4.v, 12.v"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        fprs[2] = 0x401C000000000000  # 7.0
        fprs[3] = 0xC02399999999999A  # -9.8
        fprs[4] = 0x4000000000000000  # 2.0
        fprs[5] = 0xC040266660000000 # -32.3
        fprs[6] = 0x4000000000000000  # 2.0
        fprs[7] = 0x4000000000000000  # 2.0
        fprs[12] = 0xc000000000000000  # -2.0
        fprs[13] = 0x4000000000000000  # 2.0
        fprs[14] = 0xC02399999999999A  # -9.8
        fprs[15] = 0xC040266660000000 # -32.3

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            self.assertEqual(sim.fpr(12), SelectableInt(0xC028000000000000, 64))
            self.assertEqual(sim.fpr(13), SelectableInt(0xC049F33320000000, 64))
            self.assertEqual(sim.fpr(14), SelectableInt(0x4030000000000000, 64))
            self.assertEqual(sim.fpr(15), SelectableInt(0xc029666640000000, 64))

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
