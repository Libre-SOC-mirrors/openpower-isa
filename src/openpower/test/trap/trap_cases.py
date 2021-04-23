from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.consts import MSR

from openpower.test.common import TestAccumulatorBase
import random


class TrapTestCase(TestAccumulatorBase):

    def case_0_hrfid(self):
        lst = ["hrfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'HSRR0': 0x12345678, 'HSRR1': 0x5678}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_1_rfid(self):
        lst = ["rfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_0_trap_eq_imm(self):
        insns = ["twi", "tdi"]
        for i in range(2):
            choice = random.choice(insns)
            lst = [f"{choice} 4, 1, %d" % i]  # TO=4: trap equal
            initial_regs = [0] * 32
            initial_regs[1] = 1
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_0_trap_eq(self):
        insns = ["tw", "td"]
        for i in range(2):
            choice = insns[i]
            lst = [f"{choice} 4, 1, 2"]  # TO=4: trap equal
            initial_regs = [0] * 32
            initial_regs[1] = 1
            initial_regs[2] = 1
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_3_mtmsr_0(self):
        lst = ["mtmsr 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_3_mtmsr_1(self):
        lst = ["mtmsr 1,1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_4_mtmsrd_0(self):
        lst = ["mtmsrd 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_5_mtmsrd_1(self):
        lst = ["mtmsrd 1,1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_6_mtmsr_priv_0(self):
        lst = ["mtmsr 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        msr = 1 << MSR.PR  # set in "problem state"
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=msr)

    def case_7_rfid_priv_0(self):
        lst = ["rfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678}
        msr = 1 << MSR.PR  # set in "problem state"
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      initial_msr=msr)

    def case_8_mfmsr(self):
        lst = ["mfmsr 1"]
        initial_regs = [0] * 32
        msr = (~(1 << MSR.PR)) & 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=msr)

    def case_9_mfmsr_priv(self):
        lst = ["mfmsr 1"]
        initial_regs = [0] * 32
        msr = 1 << MSR.PR  # set in "problem state"
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=msr)

    def case_999_illegal(self):
        # ok, um this is a bit of a cheat: use an instruction we know
        # is not implemented by either ISACaller or the core
        lst = ["tbegin.",
               "mtmsr 1,1"]  # should not get executed
        initial_regs = [0] * 32
        self.add_case(Program(lst, bigendian), initial_regs)

