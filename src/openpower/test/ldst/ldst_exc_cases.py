from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.test.common import TestAccumulatorBase


class LDSTExceptionTestCase(TestAccumulatorBase):

    def case_1_load_misalign(self):
        lst = ["ldx 3, 1, 0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xFFFFFFFFFFFFFFFF # deliberately misaligned
        initial_regs[2] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

