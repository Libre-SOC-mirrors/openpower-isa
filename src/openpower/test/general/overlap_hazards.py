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
               ]
        initial_regs = [0] * 32
        initial_regs[5] = 8
        e = ExpectedState(pc=4)
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

    def case_div_add_overlap_5(self):
        lst = ["divd 3, 1, 2",  # r3 = 8//2      r3=4
               "mullw 5, 7, 6", # r5 = 2*4       r5=8
               "addi 5, 5, 2",  # r5 = 8+2       r5=10   - waits for MUL
               "divd 4, 5, 6",  # r4 = 10//2     r4=5    - delays the MUL
               "mullw 4, 4, 2", # r4 = 2*4       r5=8    - MUL waits for DIV
               "add 5, 3, 4"]   # r5 = 4+5       r5=9    - add waits for MUL
        initial_regs = [0] * 32
        initial_regs[1] = 8
        initial_regs[2] = 2
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=24)
        e.intregs[1] = 8
        e.intregs[2] = 2
        e.intregs[3] = 4 # 8 divided by 2 == 4
        e.intregs[4] = 10 # 10 divided by 2 == 5, times 2 == 10
        e.intregs[5] = 14 # 4 plus 10 == 14
        e.intregs[6] = 2
        e.intregs[7] = 4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_self_overlap_and_waw_6(self):
        """also serves a secondary purpose of demonstrating a 2-operand
        instruction followed by a 1-operand.
        """
        lst = ["mullw 5, 7, 6", # r5 = 2*4       r5=8
               "addi 1, 8, 2",  # r5 = 8+2       r5=2
               ]
        initial_regs = [0] * 32
        initial_regs[2] = 2
        initial_regs[3] = 4
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=8)
        e.intregs[1] = 2 # 2 + 0 = 2
        e.intregs[2] = 2
        e.intregs[3] = 4
        e.intregs[5] = 8 # 2*4 = 8
        e.intregs[6] = 2
        e.intregs[7] = 4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_regression_1(self):
        lst = ["mullw 5, 7, 6", # r5 = 2*4       r5=8
               "addi 9, 5, 2",  # r9 = 8+2       r9=10
               "divd 4, 9, 6",  # r4 = 10//2     r4=5
               ]   # r5 = 4+5       r5=9
        initial_regs = [0] * 32
        initial_regs[1] = 8
        initial_regs[2] = 2
        initial_regs[6] = 2
        initial_regs[7] = 4
        e = ExpectedState(pc=12)
        e.intregs[1] = 8
        e.intregs[2] = 2
        e.intregs[4] = 5 # 10 divided by 2 == 5
        e.intregs[5] = 8 # 4 times 2 == 8
        e.intregs[6] = 2
        e.intregs[7] = 4
        e.intregs[9] = 10 # 8+2 == 10
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)


class RandomHazardTestCase(TestAccumulatorBase):

    def case_random(self):
        selection_1 = ['mulli', 'addi']
        selection_2 = ['mullw', 'add']
        rrange = 8
        n_ops = 20
        lst = []
        for i in range(n_ops):
            if random.randint(0, 1) == 0:
                select = selection_1[random.randint(0, len(selection_1)-1)]
                dst = random.randint(0, rrange)
                reg1 = random.randint(0, rrange)
                imm = random.randint(-20, +20)
                insn = "%s %d, %d, %d" % (select, dst, reg1, imm)
            else:
                select = selection_2[random.randint(0, len(selection_2)-1)]
                dst = random.randint(0, rrange)
                reg1 = random.randint(0, rrange)
                reg2 = random.randint(0, rrange)
                insn = "%s %d, %d, %d" % (select, dst, reg1, reg2)
            lst.append(insn)
        initial_regs = [0] * 32
        for i in range(rrange):
            initial_regs[i] = random.randint(-20, +20)
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_twin_addi_regression(self):
        """twin addi instruction with double-dependencies.
        useful for testing ReservationStations
        """
        lst = ['addi 1,8,14',
               'addi 3,0,5',
               'mulli 1,3,-11'
              ]
        initial_regs = [0] * 32
        for i in range(10):
            initial_regs[i] = i
        self.add_case(Program(lst, bigendian), initial_regs)

