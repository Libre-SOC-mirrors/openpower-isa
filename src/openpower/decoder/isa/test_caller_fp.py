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
        """>>> lst = ["lfsx 1, 0, 0x0008",
                     ]
        """
        lst = ["lfsx 1, 0, 0x0008",
                     ]
        initial_mem = {0x0000: (0x4040266666666666, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_mem=initial_mem)
            print(sim.fpr(1))
            self.assertEqual(sim.fpr(1), SelectableInt(0x4040266666666666, 64))

    def run_tst_program(self, prog, initial_regs=None,
                              initial_mem=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem)
        simulator.gpr.dump()
        simulator.fpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
