import unittest
from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.test.common import TestAccumulatorBase
import random


class LogicalTestCase(TestAccumulatorBase):

    def case_complement(self):
        insns = ["andc", "orc", "nand", "nor"]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand(self):
        insns = ["and", "or", "xor", "eqv"]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand_(self):
        insns = ["and.", "or.", "xor.", "eqv.", "andc.",
                 "orc.", "nand.", "nor."]
        for XER in [0, 0xe00c0000]:
            for i in range(40):
                choice = random.choice(insns)
                lst = [f"{choice} 3, 1, 2"]
                initial_regs = [0] * 32
                initial_regs[1] = random.randint(0, (1 << 64)-1)
                initial_regs[2] = random.randint(0, (1 << 64)-1)
                self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER})

    def case_rand_imm_so(self):
        insns = ["andi.", "andis."]
        for i in range(1):
            choice = random.choice(insns)
            imm = random.randint(0, (1 << 16)-1)
            lst = [f"{choice} 3, 1, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_sprs = {'XER': 0xe00c0000}

            self.add_case(Program(lst, bigendian), initial_regs,
                          initial_sprs=initial_sprs)

    def case_rand_imm_logical(self):
        insns = ["andi.", "andis.", "ori", "oris", "xori", "xoris"]
        for i in range(10):
            choice = random.choice(insns)
            imm = random.randint(0, (1 << 16)-1)
            lst = [f"{choice} 3, 1, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_cntz(self):
        insns = ["cntlzd", "cnttzd", "cntlzw", "cnttzw"]
        for i in range(100):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_parity(self):
        insns = ["prtyw", "prtyd"]
        for i in range(10):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_popcnt(self):
        insns = ["popcntb", "popcntw", "popcntd"]
        for i in range(10):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_popcnt_edge(self):
        insns = ["popcntb", "popcntw", "popcntd"]
        for choice in insns:
            lst = [f"{choice} 3, 1"]
            initial_regs = [0] * 32
            initial_regs[1] = -1
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_cmpb(self):
        lst = ["cmpb 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xdeadbeefcafec0de
        initial_regs[2] = 0xd0adb0000afec1de
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_bpermd(self):
        lst = ["bpermd 3, 1, 2"]
        for i in range(20):
            initial_regs = [0] * 32
            initial_regs[1] = 1 << random.randint(0, 63)
            initial_regs[2] = 0xdeadbeefcafec0de
            self.add_case(Program(lst, bigendian), initial_regs)

