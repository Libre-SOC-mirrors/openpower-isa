from openpower.test.common import TestAccumulatorBase, TestCase
from openpower.endian import bigendian
from openpower.simulator.program import Program
import random


class ShiftRotTestCase(TestAccumulatorBase):

    def case_0_proof_regression_rlwnm(self):
        lst = ["rlwnm 3, 1, 2, 16, 20"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x7ffdbffb91b906b9
        initial_regs[2] = 31
        print(initial_regs[1], initial_regs[2])
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_regression_rldicr_0(self):
        lst = ["rldicr. 29, 19, 1, 21"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3f
        initial_regs[19] = 0x00000000ffff8000

        initial_sprs = {'XER': 0xe00c0000}

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs=initial_sprs)

    def case_regression_rldicr_1(self):
        lst = ["rldicr. 29, 19, 1, 21"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3f
        initial_regs[19] = 0x00000000ffff8000

        self.add_case(Program(lst, bigendian), initial_regs)

    def case_shift(self):
        insns = ["slw", "sld", "srw", "srd", "sraw", "srad"]
        for i in range(20):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, 63)
            print(initial_regs[1], initial_regs[2])
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_shift_arith(self):
        lst = ["sraw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = random.randint(0, (1 << 64)-1)
        initial_regs[2] = random.randint(0, 63)
        print(initial_regs[1], initial_regs[2])
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_sld_rb_too_big(self):
        lst = ["sld 3, 1, 4",
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        initial_regs[4] = 64 # too big, output should be zero
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_sld_rb_is_zero(self):
        lst = ["sld 3, 1, 4",
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x8000000000000000
        initial_regs[4] = 0 # no shift; output should equal input
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_shift_once(self):
        lst = ["slw 3, 1, 4",
               "slw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x80000000
        initial_regs[2] = 0x40
        initial_regs[4] = 0x00
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_rlwinm(self):
        for i in range(10):
            mb = random.randint(0, 31)
            me = random.randint(0, 31)
            sh = random.randint(0, 31)
            lst = [f"rlwinm 3, 1, {mb}, {me}, {sh}",
                   #f"rlwinm. 3, 1, {mb}, {me}, {sh}"
                   ]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rlwimi(self):
        lst = ["rlwimi 3, 1, 5, 20, 6"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xdeadbeef
        initial_regs[3] = 0x12345678
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_rlwnm(self):
        lst = ["rlwnm 3, 1, 2, 20, 6"]
        initial_regs = [0] * 32
        initial_regs[1] = random.randint(0, (1 << 64)-1)
        initial_regs[2] = random.randint(0, 63)
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_rldicl(self):
        lst = ["rldicl 3, 1, 5, 20"]
        initial_regs = [0] * 32
        initial_regs[1] = random.randint(0, (1 << 64)-1)
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_rldicr(self):
        lst = ["rldicr 3, 1, 5, 20"]
        initial_regs = [0] * 32
        initial_regs[1] = random.randint(0, (1 << 64)-1)
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_regression_extswsli(self):
        lst = [f"extswsli 3, 1, 34"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_regression_extswsli_2(self):
        lst = [f"extswsli 3, 1, 7"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3ffffd7377f19fdd
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_regression_extswsli_3(self):
        lst = [f"extswsli 3, 1, 0"]
        initial_regs = [0] * 32
        #initial_regs[1] = 0x80000000fb4013e2
        #initial_regs[1] = 0xffffffffffffffff
        #initial_regs[1] = 0x00000000ffffffff
        initial_regs[1] = 0x0000010180122900
        #initial_regs[1] = 0x3ffffd73f7f19fdd
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_extswsli(self):
        for i in range(40):
            sh = random.randint(0, 63)
            lst = [f"extswsli 3, 1, {sh}"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rlc(self):
        insns = ["rldic", "rldicl", "rldicr"]
        for i in range(20):
            choice = random.choice(insns)
            sh = random.randint(0, 63)
            m = random.randint(0, 63)
            lst = [f"{choice} 3, 1, {sh}, {m}"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)
