import unittest
from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.test.common import TestAccumulatorBase
import random


class MulTestCases2Arg(TestAccumulatorBase):
    def case_all(self):
        instrs = ["mulhw",
                  "mulhw.", "mullw",
                  "mullw.", "mullwo",
                  "mullwo.", "mulhwu",
                  "mulhwu.", "mulld",
                  "mulld.", "mulldo",
                  "mulldo.", "mulhd",
                  "mulhd.", "mulhdu",
                  "mulhdu."]

        test_values = [
            0x0,
            0x1,
            0x2,
            0xFFFF_FFFF_FFFF_FFFF,
            0xFFFF_FFFF_FFFF_FFFE,
            0x7FFF_FFFF_FFFF_FFFF,
            0x8000_0000_0000_0000,
            0x1234_5678_0000_0000,
            0x1234_5678_8000_0000,
            0x1234_5678_FFFF_FFFF,
            0x1234_5678_7FFF_FFFF,
            0xffffffff,
            0x7fffffff,
            0x80000000,
            0xfffffffe,
            0xfffffffd
        ]

        for instr in instrs:
            l = [f"{instr} 3, 1, 2"]
            # use "with" so as to close the files used
            with Program(l, bigendian) as prog:
                for ra in test_values:
                    for rb in test_values:
                        initial_regs = [0] * 32
                        initial_regs[1] = ra
                        initial_regs[2] = rb
                        self.add_case(prog, initial_regs)

    def case_all_rb_randint(self):
        instrs = ["mulhw",
                  "mulhw.", "mullw",
                  "mullw.", "mullwo",
                  "mullwo.", "mulhwu",
                  "mulhwu.", "mulld",
                  "mulld.", "mulldo",
                  "mulldo.", "mulhd",
                  "mulhd.", "mulhdu",
                  "mulhdu."]

        test_values = [
            0x0,
            0x1,
            0x2,
            0xFFFF_FFFF_FFFF_FFFF,
            0xFFFF_FFFF_FFFF_FFFE,
            0x7FFF_FFFF_FFFF_FFFF,
            0x8000_0000_0000_0000,
            0x1234_5678_0000_0000,
            0x1234_5678_8000_0000,
            0x1234_5678_FFFF_FFFF,
            0x1234_5678_7FFF_FFFF,
            0xffffffff,
            0x7fffffff,
            0x80000000,
            0xfffffffe,
            0xfffffffd
        ]

        for instr in instrs:
            l = [f"{instr} 3, 1, 2"]
            # use "with" so as to close the files used
            with Program(l, bigendian) as prog:
                for ra in test_values:
                    initial_regs = [0] * 32
                    initial_regs[1] = ra
                    initial_regs[2] = random.randint(0, (1 << 64)-1)
                    self.add_case(prog, initial_regs)

    def case_all_rb_close_to_ov(self):
        instrs = ["mulhw",
                  "mulhw.", "mullw",
                  "mullw.", "mullwo",
                  "mullwo.", "mulhwu",
                  "mulhwu.", "mulld",
                  "mulld.", "mulldo",
                  "mulldo.", "mulhd",
                  "mulhd.", "mulhdu",
                  "mulhdu."]

        test_values = [
            0x0,
            0x1,
            0x2,
            0xFFFF_FFFF_FFFF_FFFF,
            0xFFFF_FFFF_FFFF_FFFE,
            0x7FFF_FFFF_FFFF_FFFF,
            0x8000_0000_0000_0000,
            0x1234_5678_0000_0000,
            0x1234_5678_8000_0000,
            0x1234_5678_FFFF_FFFF,
            0x1234_5678_7FFF_FFFF,
            0xffffffff,
            0x7fffffff,
            0x80000000,
            0xfffffffe,
            0xfffffffd
        ]

        for instr in instrs:
            l = [f"{instr} 3, 1, 2"]
            # use "with" so as to close the files used
            with Program(l, bigendian) as prog:
                for i in range(20):
                    x = 0x7fffffff + random.randint((-1 << 31), (1 << 31) - 1)
                    ra = random.randint(0, (1 << 32)-1)
                    rb = x // ra

                    initial_regs = [0] * 32
                    initial_regs[1] = ra
                    initial_regs[2] = rb
                    self.add_case(prog, initial_regs)

    def case_mulli(self):

        imm_values = [-32768, -32767, -32766, -2, -1, 0, 1, 2, 32766, 32767]

        ra_values = [
            0x0,
            0x1,
            0x2,
            0xFFFF_FFFF_FFFF_FFFF,
            0xFFFF_FFFF_FFFF_FFFE,
            0x7FFF_FFFF_FFFF_FFFF,
            0x8000_0000_0000_0000,
            0x1234_5678_0000_0000,
            0x1234_5678_8000_0000,
            0x1234_5678_FFFF_FFFF,
            0x1234_5678_7FFF_FFFF,
            0xffffffff,
            0x7fffffff,
            0x80000000,
            0xfffffffe,
            0xfffffffd
        ]

        for i in range(20):
            imm_values.append(random.randint(-1 << 15, (1 << 15) - 1))

        for i in range(14):
            ra_values.append(random.randint(0, (1 << 64) - 1))

        for imm in imm_values:
            l = [f"mulli 0, 1, {imm}"]
            # use "with" so as to close the files used
            with Program(l, bigendian) as prog:
                for ra in ra_values:
                    initial_regs = [0] * 32
                    initial_regs[1] = ra
                    self.add_case(prog, initial_regs)


MUL_3_ARG_TEST_VALUES = [
    0x0,
    0x1,
    0x2,
    0xFFFF_FFFF_FFFF_FFFF,
    0xFFFF_FFFF_FFFF_FFFE,
    0x7FFF_FFFF_FFFF_FFFF,
    0x8000_0000_0000_0000,
    0x1234_5678_0000_0000,
    0x1234_5678_8000_0000,
    0x1234_5678_FFFF_FFFF,
    0x1234_5678_7FFF_FFFF,
    0xffffffff,
    0x7fffffff,
    0x80000000,
    0xfffffffe,
    0xfffffffd
]


class MulTestCases3Arg(TestAccumulatorBase):
    def __init__(self, subtest_index):
        self.subtest_index = subtest_index
        super().__init__()

    def case_all(self):
        instrs = ["maddhd", "maddhdu", "maddld"]

        for instr in instrs:
            l = [f"{instr} 1, 2, 3, 4"]
            ra = MUL_3_ARG_TEST_VALUES[self.subtest_index]
            for rb in MUL_3_ARG_TEST_VALUES:
                for rc in MUL_3_ARG_TEST_VALUES:
                    initial_regs = [0] * 32
                    initial_regs[2] = ra
                    initial_regs[3] = rb
                    initial_regs[4] = rc
                    # use "with" so as to close the files used
                    with Program(l, bigendian) as prog:
                        self.add_case(prog, initial_regs)


