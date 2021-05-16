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
from copy import deepcopy


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected_int, expected_fpr):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))
        for i in range(32):
            self.assertEqual(sim.fpr(i), SelectableInt(expected_fpr[i], 64))

    def test_fpload(self):
        """>>> lst = ["lfsx 1, 0, 0",
                     ]
        """
        lst = ["lfsx 1, 0, 0",
                     ]
        initial_mem = {0x0000: (0x42013333, 8),
                       0x0008: (0x42026666, 8),
                       0x0020: (0x1828384822324252, 8),
                        }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem)
            print("FPR 1", sim.fpr(1))
            self.assertEqual(sim.fpr(1), SelectableInt(0x4040266660000000, 64))

    def test_fp_single_ldst(self):
        """>>> lst = ["lfsx 1, 1, 0",   # load fp 1 from mem location 0
                      "stfsu 1, 16(1)", # store fp 1 into mem 0x10, update RA
                      "lfsu 2, 0(1)",   # re-load from UPDATED r1
                     ]
        """
        lst = ["lfsx 1, 1, 0",
               "stfsu 1, 16(1)",
               "lfs 2, 0(1)",
                     ]
        initial_mem = {0x0000: (0x42013333, 8),
                       0x0008: (0x42026666, 8),
                       0x0020: (0x1828384822324252, 8),
                        }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem)
            print("FPR 1", sim.fpr(1))
            print("FPR 2", sim.fpr(2))
            print("GPR 1", sim.gpr(1)) # should be 0x10 due to update
            self.assertEqual(sim.gpr(1), SelectableInt(0x10, 64))
            self.assertEqual(sim.fpr(1), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))

    def test_fp_mv(self):
        """>>> lst = ["fmr 1, 2",
                     ]
        """
        lst = ["fmr 1, 2",
                     ]

        fprs = [0] * 32
        fprs[2] = 0x4040266660000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print("FPR 1", sim.fpr(1))
            print("FPR 2", sim.fpr(2))
            self.assertEqual(sim.fpr(1), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))

    def test_fp_neg(self):
        """>>> lst = ["fneg 1, 2",
                     ]
        """
        lst = ["fneg 1, 2",
                     ]

        fprs = [0] * 32
        fprs[2] = 0x4040266660000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print("FPR 1", sim.fpr(1))
            print("FPR 2", sim.fpr(2))
            self.assertEqual(sim.fpr(1), SelectableInt(0xC040266660000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))

    def test_fp_abs(self):
        """>>> lst = ["fabs 3, 1",
                      "fabs 4, 2",
                      "fnabs 5, 1",
                      "fnabs 6, 2",
                     ]
        """
        lst = ["fabs 3, 1",
               "fabs 4, 2",
               "fnabs 5, 1",
               "fnabs 6, 2",
                     ]

        fprs = [0] * 32
        fprs[1] = 0xC040266660000000
        fprs[2] = 0x4040266660000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0xC040266660000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(4), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(5), SelectableInt(0xC040266660000000, 64))
            self.assertEqual(sim.fpr(6), SelectableInt(0xC040266660000000, 64))

    def test_fp_sgn(self):
        """>>> lst = ["fcpsgn 3, 1, 2",
                      "fcpsgn 4, 2, 1",
                     ]
        """
        lst = ["fcpsgn 3, 1, 2",
               "fcpsgn 4, 2, 1",
                     ]

        fprs = [0] * 32
        fprs[1] = 0xC040266660000001 # 1 in LSB, 1 in MSB
        fprs[2] = 0x4040266660000000 # 0 in LSB, 0 in MSB

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0xC040266660000001, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))
            # 1 in MSB comes from reg 1, 0 in LSB comes from reg 2
            self.assertEqual(sim.fpr(3), SelectableInt(0xC040266660000000, 64))
            # 0 in MSB comes from reg 2, 1 in LSB comes from reg 1
            self.assertEqual(sim.fpr(4), SelectableInt(0x4040266660000001, 64))

    def test_fp_adds(self):
        """>>> lst = ["fadds 3, 1, 2",
                     ]
        """
        lst = ["fadds 3, 1, 2", # -32.3 + 32.3 = 0
                     ]

        fprs = [0] * 32
        fprs[1] = 0xC040266660000000
        fprs[2] = 0x4040266660000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0xC040266660000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0, 64))

    def test_fp_add(self):
        """>>> lst = ["fadd 3, 1, 2",
                     ]
        """
        lst = ["fadd 3, 1, 2", # 7.0 + -9.8 = -2.8
                     ]

        fprs = [0] * 32
        fprs[1] = 0x401C000000000000  # 7.0
        fprs[2] = 0xC02399999999999A  # -9.8

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0x401C000000000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0xC02399999999999A, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0xC006666666666668, 64))

    def test_fp_mul(self):
        """>>> lst = ["fmul 3, 1, 2",
                     ]
        """
        lst = ["fmul 3, 1, 2", # 7.0 * -9.8 = -68.6
                     ]

        fprs = [0] * 32
        fprs[1] = 0x401C000000000000  # 7.0
        fprs[2] = 0xC02399999999999A  # -9.8

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0x401C000000000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0xC02399999999999A, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0xC051266666666667, 64))

    def test_fp_fcfids(self):
        """>>> lst = ["fcfids 1, 2",
               lst = ["fcfids 3, 4",
                     ]
        """
        lst = ["fcfids 1, 2",
               "fcfids 3, 4",
                     ]

        fprs = [0] * 32
        fprs[2] = 7
        fprs[4] = -32

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0x401C000000000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(7, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0xC040000000000000, 64))
            self.assertEqual(sim.fpr(4), SelectableInt(-32, 64))

    def run_tst_program(self, prog, initial_regs=None,
                              initial_mem=None,
                              initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                                  initial_fprs=initial_fprs)
        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
