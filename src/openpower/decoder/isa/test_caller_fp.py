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

    def test_fp_mv(self):
        """>>> lst = ["fmr 1, 2",
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
                     ]
        """
        lst = ["fabs 3, 1",
               "fabs 4, 2",
                     ]

        fprs = [0] * 32
        fprs[1] = 0xC040266660000000
        fprs[2] = 0x4040266660000000

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print("FPR 1", sim.fpr(1))
            print("FPR 2", sim.fpr(2))
            print("FPR 3", sim.fpr(3))
            print("FPR 4", sim.fpr(4))
            self.assertEqual(sim.fpr(1), SelectableInt(0xC040266660000000, 64))
            self.assertEqual(sim.fpr(2), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(3), SelectableInt(0x4040266660000000, 64))
            self.assertEqual(sim.fpr(4), SelectableInt(0x4040266660000000, 64))

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
