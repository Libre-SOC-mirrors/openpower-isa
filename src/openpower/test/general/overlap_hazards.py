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

    def cse_div_add_overlap_3(self):
        lst = ["divd 3, 1, 2",
               "mullw 5, 7, 6", # 2*4=6, overwritten later by add
               "addi 5, 5, 2",  # add 2 to 6 = 8
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
