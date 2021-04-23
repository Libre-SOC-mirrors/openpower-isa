import unittest
from nmutil.formaltest import FHDLTestCase
from openpower.simulator.program import Program
from openpower.simulator.qemu import run_program
from openpower.test.common import TestCase
from openpower.simulator.test_sim import DecoderBase
from openpower.endian import bigendian



class MulTestCases(FHDLTestCase):
    test_data = []

    def __init__(self, name="div"):
        super().__init__(name)
        self.test_name = name

    def tst_mullw(self):
        lst = ["addi 1, 0, 0x5678",
               "addi 2, 0, 0x1234",
               "mullw 3, 1, 2"]
        self.run_tst_program(Program(lst, bigendian), [3])

    def test_mullwo(self):
        lst = ["addi 1, 0, 0x5678",
               "neg 1, 1",
               "addi 2, 0, 0x1234",
               "neg 2, 2",
               "mullwo 3, 1, 2"]
        self.run_tst_program(Program(lst, bigendian), [3])

    def run_tst_program(self, prog, initial_regs=None, initial_sprs=None,
                                    initial_mem=None):
        initial_regs = [0] * 32
        tc = TestCase(prog, self.test_name, initial_regs, initial_sprs, 0,
                                            initial_mem, 0)
        self.test_data.append(tc)


class MulDecoderTestCase(DecoderBase, MulTestCases):
    pass


if __name__ == "__main__":
    unittest.main()
