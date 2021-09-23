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

    def test_fpload_imm(self):
        """>>> lst = ["lfs 1, 8(1)",
                     ]
        """
        lst = ["lfs 1, 8(1)",
                     ]
        initial_mem = {0x0000: (0x42013333, 8),
                       0x0008: (0x42026666, 8),
                       0x0020: (0x1828384822324252, 8),
                        }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem)
            print("FPR 1", sim.fpr(1))
            self.assertEqual(sim.fpr(1), SelectableInt(0x40404cccc0000000, 64))

    def test_fpload2(self):
        """>>> lst = ["lfsx 1, 0, 0",
                     ]
        """
        lst = ["lfsx 1, 0, 0",
                     ]
        initial_mem = {0x0000: (0xac000000, 8),
                       0x0020: (0x1828384822324252, 8),
                        }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem)
            print("FPR 1", sim.fpr(1))
            self.assertEqual(sim.fpr(1), SelectableInt(0xbd80000000000000, 64))

    def test_fp_single_ldst(self):
        """>>> lst = ["lfsx 1, 1, 0",   # load fp 1 from mem location 0
                      "stfsu 1, 16(1)", # store fp 1 into mem 0x10, update RA
                      "lfs 2, 0(1)",   # re-load from UPDATED r1
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

    def test_fp_single_ldst_update_idx(self):
        """>>> lst = ["lfsx 1, 0, 0",   # load fp 1 from mem location 0
                      "stfsux 1, 2, 1", # store fp 1 into mem 0x10, update RA
                      "lfs 2, 0(2)",   # re-load from UPDATED r2
                     ]
        """
        lst = ["lfsx 1, 0, 0",
               "stfsux 1, 2, 1",
               "lfs 2, 0(2)",
                     ]
        initial_mem = {0x0000: (0x42013333, 8),
                       0x0008: (0x42026666, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        # create an offset of 0x10 (2+3)
        initial_regs = [0]*32
        initial_regs[1] = 0x4
        initial_regs[2] = 0xc

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=initial_regs,
                                                initial_mem=initial_mem)
            print("FPR 1", sim.fpr(1))
            print("FPR 2", sim.fpr(2))
            print("GPR 1", sim.gpr(1)) # should be 0x4
            print("GPR 2", sim.gpr(2)) # should be 0x10 due to update
            print("mem dump")
            print(sim.mem.dump())
            self.assertEqual(sim.gpr(1), SelectableInt(0x4, 64))
            self.assertEqual(sim.gpr(2), SelectableInt(0x10, 64))
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

    def test_fp_subs(self):
        """>>> lst = ["fsubs 3, 1, 2",
                     ]
        """
        lst = ["fsubs 3, 1, 2", # 0 - -32.3 = 32.3
                     ]

        fprs = [0] * 32
        fprs[1] = 0x0
        fprs[2] = 0xC040266660000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0x0, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0xC040266660000000, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0x4040266660000000, 64))

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

    def test_fp_muls(self):
        """>>> lst = ["fmuls 3, 1, 2",
                     ]
        """
        lst = ["fmuls 3, 1, 2", # 7.0 * -9.8 = -68.6
               "fmuls 29,12,8", # test
                     ]

        fprs = [0] * 32
        fprs[1] = 0x401C000000000000  # 7.0
        fprs[2] = 0xC02399999999999A  # -9.8

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(1), SelectableInt(0x401C000000000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0xC02399999999999A, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0xc051266640000000, 64))

    def test_fp_muls3(self):
        """>>> lst = ["fmuls 3, 1, 2",
                     ]
        """
        lst = ["fmuls 3, 1, 2", #
                     ]

        fprs = [0] * 32
        fprs[1] = 0xbfb0ab5100000000
        fprs[2] = 0xbdca000000000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(3), SelectableInt(0x3d8b1663a0000000, 64))

    def test_fp_muls4(self):
        """>>> lst = ["fmuls 3, 1, 2",
                     ]
        """
        lst = ["fmuls 3, 1, 2", #
                     ]

        fprs = [0] * 32
        fprs[1] = 0xbe724e2000000000 # negative number
        fprs[2] = 0x0                # times zero

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            # result should be -ve zero not +ve zero
            self.assertEqual(sim.fpr(3), SelectableInt(0x8000000000000000, 64))

    def test_fp_muls5(self):
        """>>> lst = ["fmuls 3, 1, 2",
                     ]
        """
        lst = ["fmuls 3, 1, 2", #
                     ]

        fprs = [0] * 32
        fprs[1] = 0xbfb0ab5100000000
        fprs[2] = 0xbdca000000000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(3), SelectableInt(0x3d8b1663a0000000, 64))

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

    def test_fp_madd1(self):
        """>>> lst = ["fmadds 3, 1, 2, 4",
                     ]
        """
        lst = ["fmadds 3, 1, 2, 4", # 7.0 * -9.8 + 2 = -66.6
                     ]

        fprs = [0] * 32
        fprs[1] = 0x401C000000000000  # 7.0
        fprs[2] = 0xC02399999999999A  # -9.8
        fprs[4] = 0x4000000000000000  # 2.0

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(3), SelectableInt(0xC050A66660000000, 64))

    def test_fp_msub1(self):
        """>>> lst = ["fmsubs 3, 1, 2, 4",
                     ]
        """
        lst = ["fmsubs 3, 1, 2, 4", # 7.0 * -9.8 + 2 = -70.6
                     ]

        fprs = [0] * 32
        fprs[1] = 0x401C000000000000  # 7.0
        fprs[2] = 0xC02399999999999A  # -9.8
        fprs[4] = 0x4000000000000000  # 2.0

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            self.assertEqual(sim.fpr(3), SelectableInt(0xc051a66660000000, 64))

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
