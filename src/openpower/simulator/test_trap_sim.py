from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_enums import (Function, MicrOp,
                                     In1Sel, In2Sel, In3Sel,
                                     OutSel, RC, LdstLen, CryIn,
                                     single_bit_flags, Form, SPR,
                                     get_signal_name, get_csv)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.simulator.qemu import run_program
from openpower.decoder.isa.all import ISA
from openpower.test.common import TestCase
from openpower.simulator.test_sim import DecoderBase
from openpower.endian import bigendian #XXX HACK!


class TrapSimTestCases(FHDLTestCase):
    test_data = []

    def __init__(self, name="div"):
        super().__init__(name)
        self.test_name = name

    def test_0_not_twi(self):
        lst = ["addi 1, 0, 0x5678",
               "twi  4, 1, 0x5677",
               ]
        with Program(lst, bigendian) as program:
            self.run_tst_program(program, [1])

    def test_1_twi_eq(self):
        lst = ["addi 1, 0, 0x5678",
               "twi  4, 1, 0x5678",
               ]
        with Program(lst, bigendian) as program:
            self.run_tst_program(program, [1])

    def run_tst_program(self, prog, initial_regs=None, initial_sprs=None,
                                    initial_mem=None):
        initial_regs = [0] * 32
        tc = TestCase(prog, self.test_name, initial_regs, initial_sprs, 0,
                                            initial_mem, 0)
        self.test_data.append(tc)


class TrapDecoderTestCase(DecoderBase, TrapSimTestCases):
    pass


if __name__ == "__main__":
    unittest.main()
