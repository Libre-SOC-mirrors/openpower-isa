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

    def test_sv_add_scalar_reduce(self):
        """>>> lst = ['sv.add/mr 1, 5.v, 1'
                       ]
        note: there are 2 adds (VL=2) but *three values involved*
        adds:
            * 1 starts at 0x0101
            * 1 = 5 + 1  => 0x101 + 0x202 => 0x303
            * 1 = 6 + 1  => 0x303 + 0x404 => 0x707
        """
        isa = SVP64Asm(['sv.add/mr 1, 5.v, 1'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[1] = 0x0101
        initial_regs[5] = 0x0202
        initial_regs[6] = 0x0404
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))
        # copy before running, then compute answers
        expected_regs = deepcopy(initial_regs)
        # r1 = r1 + r5 + r6
        expected_regs[1] = (initial_regs[1] + initial_regs[5] +
                            initial_regs[6])  # 0x0707

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs,
                                                svstate=svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_add_prefix_sum(self):
        """>>> lst = ['sv.add/mr 2.v, 2.v, 1.v'
                       ]
            adds performed - not in reverse
            * 2 = 2 + 1  => 1 + 2  =>  3
            * 3 = 3 + 2  => 3 + 3  =>  6
            * 4 = 4 + 3  => 4 + 6  =>  10

            pascal's triangle!
        """
        isa = SVP64Asm(['sv.add/mr 2.v, 2.v, 1.v'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[1] = 0x1
        initial_regs[2] = 0x2
        initial_regs[3] = 0x3
        initial_regs[4] = 0x4
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 3 # VL
        svstate.maxvl[0:7] = 3 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))
        # copy before running, then compute answers
        expected_regs = deepcopy(initial_regs)
        for i in range(3):
            print ("%d += %d" % (2+i, 1+i))
            expected_regs[2+i] += expected_regs[1+i]
        for i in range(5):
            print ("expected", i, expected_regs[i])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs,
                                                svstate=svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_add_prefix_sum_reverse(self):
        """>>> lst = ['sv.add/mrr 2.v, 2.v, 1.v'
                       ]
            adds performed - *in reverse order*
            * 4 = 4 + 3  => 1 + 2  =>  3
            * 3 = 3 + 2  => 3 + 2  =>  5
            * 2 = 2 + 1  => 3 + 4  =>  7
        """
        isa = SVP64Asm(['sv.add/mrr 2.v, 2.v, 1.v'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[1] = 0x4
        initial_regs[2] = 0x3
        initial_regs[3] = 0x2
        initial_regs[4] = 0x1
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 3 # VL
        svstate.maxvl[0:7] = 3 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))
        # copy before running, then compute answers
        expected_regs = deepcopy(initial_regs)
        for i in range(3):
            j = 2-i
            print ("%d += %d" % (2+j, 1+j))
            expected_regs[2+j] += expected_regs[1+j]
        for i in range(5):
            print ("expected", i, expected_regs[i])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs,
                                                svstate=svstate)
            self._check_regs(sim, expected_regs)

    def test_fp_muls_reduce(self):
        """>>> lst = ["sv.fmuls/mr 1, 2.v, 1",
                     ]
        note that VL=3 but *four values are involved*
        answer should be 7.0 * -9.8 * -9.8 * 2.0 = 1344.56

        * FPR 1 starts at 7.0
        * FPR 1 multiplied by FPR 2, -9.8
        * FPR 1 multiplied by FPR 3, -9.8
        * FPR 1 multiplied by FPR 4, 2.0
        """
        isa = SVP64Asm(["sv.fmuls/mr 1, 2.v, 1",
                     ])
        lst = list(isa)
        print ("listing", lst)

        fprs = [0] * 32
        fprs[1] = 0x401C000000000000  # 7.0
        fprs[2] = 0xC02399999999999A  # -9.8
        fprs[3] = 0xC02399999999999A  # -9.8
        fprs[4] = 0x4000000000000000  # 2.0

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 3 # VL
        svstate.maxvl[0:7] = 3 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                                initial_fprs=fprs)
            # answer should be 7.0 * -9.8 * -9.8 * 2.0 = 1344.56
            self.assertEqual(sim.fpr(1), SelectableInt(0x4095023d60000000, 64))
            # these should not have been changed
            self.assertEqual(sim.fpr(2), SelectableInt(0xC02399999999999A, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0xC02399999999999A, 64))
            self.assertEqual(sim.fpr(4), SelectableInt(0x4000000000000000, 64))

    def test_sv_fpmadds(self):
        """>>> lst = ["sv.fmadds/mr 6, 2.v, 4.v, 6"
                        ]
                this example uses f6 as a multiply-accumulate-sum mapreduce
        """
        lst = SVP64Asm(["sv.fmadds/mr 6, 2.v, 4.v, 6"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        fprs[2] = 0x401C000000000000  # 7.0
        fprs[3] = 0xC02399999999999A  # -9.8
        fprs[4] = 0x4000000000000000  # 2.0
        fprs[5] = 0xC040266660000000 # -32.3
        fprs[6] = 0x4000000000000000  # 2.0

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            self.assertEqual(sim.fpr(6), SelectableInt(0x4074c8a3c0000000, 64))

    def run_tst_program(self, prog, initial_regs=None, svstate=None,
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
