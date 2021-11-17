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
