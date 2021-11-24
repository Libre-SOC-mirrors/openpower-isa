import random
from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.power_enums import XER_bits
from openpower.decoder.isa.caller import special_sprs
from openpower.test.state import ExpectedState
import unittest


class HazardTestCase(TestAccumulatorBase):

    def case_div_add_overlap(self):
        lst = ["divd 3, 1, 2",
               "add 5, 3, 4"]
        initial_regs = [0] * 32
        initial_regs[1] = 6
        initial_regs[2] = 2
        initial_regs[4] = 4
        e = ExpectedState(pc=8)
        e.intregs[1] = 6
        e.intregs[2] = 2
        e.intregs[3] = 3 # 6 divided by 2 == 3
        e.intregs[4] = 4
        e.intregs[5] = 7 # 3 plus 4 == 7
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_div_add_overlap2(self):
        lst = ["divd 3, 1, 2",
               "mullw 5, 7, 6", # 2*4=8, overwritten later by add
               "divd 4, 5, 6",
               "add 5, 3, 4"]
        initial_regs = [0] * 32
        initial_regs[1] = 6
        initial_regs[2] = 2
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=16)
        e.intregs[1] = 6
        e.intregs[2] = 2
        e.intregs[3] = 3 # 6 divided by 2 == 3
        e.intregs[4] = 4 # 8 divided by 2 == 4
        e.intregs[5] = 7 # 3 plus 4 == 7
        e.intregs[6] = 2
        e.intregs[7] = 4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_div_add_overlap_write_after_write_1(self):
        lst = ["divd 3, 1, 2",
               "add 3, 7, 6", # 2+4=6, overwrites divd
               "add 5, 3, 2"  # 3+6=8
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 6
        initial_regs[2] = 2
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=12)
        e.intregs[1] = 6
        e.intregs[2] = 2
        e.intregs[3] = 6 # 2 plus 4 == 6, overwriting div
        e.intregs[5] = 8 # 3 plus 6 == 8
        e.intregs[6] = 2
        e.intregs[7] = 4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_div_add_overlap_3(self):
        lst = ["divd 3, 1, 2",  # r3 = 8//2      r3=4
               "mullw 5, 7, 6", # r5 = 2*4       r5=8
               "addi 9, 5, 2",  # r9 = 8+2       r9=10
               "divd 4, 9, 6",  # r4 = 10//2     r4=5
               "add 5, 3, 4"]   # r5 = 4+5       r5=9
        initial_regs = [0] * 32
        initial_regs[1] = 8
        initial_regs[2] = 2
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=20)
        e.intregs[1] = 8
        e.intregs[2] = 2
        e.intregs[3] = 4 # 8 divided by 2 == 4
        e.intregs[4] = 5 # 10 divided by 2 == 5
        e.intregs[5] = 9 # 4 plus 5 == 9
        e.intregs[6] = 2
        e.intregs[7] = 4
        e.intregs[9] = 10 # 8+2 == 10
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_add_self_overlap_1(self):
        lst = ["addi 5, 5, 2",  # r5 = 8+2       r5=10
               "divd 4, 5, 6",  # r4 = 10//2     r4=5
               "add 5, 3, 4"]   # r5 = 4+5       r5=9
        initial_regs = [0] * 32
        initial_regs[5] = 8
        e = ExpectedState(pc=20)
        e.intregs[5] = 10 # 8 plus immediate of 2 = 10
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_div_add_overlap_4(self):
        lst = ["divd 3, 1, 2",  # r3 = 8//2      r3=4
               "mullw 5, 7, 6", # r5 = 2*4       r5=8
               "addi 5, 5, 2",  # r5 = 8+2       r5=10
               "divd 4, 5, 6",  # r4 = 10//2     r4=5
               "add 5, 3, 4"]   # r5 = 4+5       r5=9
        initial_regs = [0] * 32
        initial_regs[1] = 8
        initial_regs[2] = 2
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=20)
        e.intregs[1] = 8
        e.intregs[2] = 2
        e.intregs[3] = 4 # 8 divided by 2 == 4
        e.intregs[4] = 5 # 10 divided by 2 == 5
        e.intregs[5] = 9 # 4 plus 5 == 9
        e.intregs[6] = 2
        e.intregs[7] = 4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)
