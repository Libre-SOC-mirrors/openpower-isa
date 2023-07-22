from nmutil.sim_util import hash_256
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.insndb.asm import SVP64Asm
from openpower.test.common import TestAccumulatorBase, skip_case
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
                              initial_sprs={'XER': XER})

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

    def case_bpermd_morerandom(self):
        lst = ["bpermd 3, 1, 2"]
        for i in range(100):
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_cfuged(self):
        prog = Program(list(SVP64Asm(["cfuged 3,4,5"])), bigendian)
        for case_idx in range(200):
            gprs = [0] * 32
            gprs[4] = hash_256(f"cfuged {case_idx} r4") % 2**64
            gprs[5] = hash_256(f"cfuged {case_idx} r5") % 2**64
            e = ExpectedState(pc=4, int_regs=gprs)
            zeros = []
            ones = []
            for i in range(64):
                bit = 1 << i
                if gprs[5] & bit:
                    ones.append(bool(gprs[4] & bit))
                else:
                    zeros.append(bool(gprs[4] & bit))
            bits = ones + zeros
            e.intregs[3] = 0
            for i, v in enumerate(bits):
                e.intregs[3] |= v << i
            with self.subTest(
                    case_idx=case_idx, RS_in=hex(gprs[4]),
                    RB_in=hex(gprs[5]), expected_RA=hex(e.intregs[3])):
                self.add_case(prog, gprs, expected=e)

    def case_cntlzdm(self):
        prog = Program(list(SVP64Asm(["cntlzdm 3,4,5"])), bigendian)
        for case_idx in range(200):
            gprs = [0] * 32
            gprs[4] = hash_256(f"cntlzdm {case_idx} r4") % 2**64
            gprs[5] = hash_256(f"cntlzdm {case_idx} r5") % 2**64
            e = ExpectedState(pc=4, int_regs=gprs)
            count = 0
            for i in reversed(range(64)):
                bit = 1 << i
                if gprs[5] & bit:
                    if gprs[4] & bit:
                        break
                    count += 1
            e.intregs[3] = count
            with self.subTest(
                    case_idx=case_idx, RS_in=hex(gprs[4]),
                    RB_in=hex(gprs[5]), expected_RA=hex(e.intregs[3])):
                self.add_case(prog, gprs, expected=e)

    def case_cnttzdm(self):
        prog = Program(list(SVP64Asm(["cnttzdm 3,4,5"])), bigendian)
        for case_idx in range(200):
            gprs = [0] * 32
            gprs[4] = hash_256(f"cnttzdm {case_idx} r4") % 2**64
            gprs[5] = hash_256(f"cnttzdm {case_idx} r5") % 2**64
            e = ExpectedState(pc=4, int_regs=gprs)
            count = 0
            for i in range(64):
                bit = 1 << i
                if gprs[5] & bit:
                    if gprs[4] & bit:
                        break
                    count += 1
            e.intregs[3] = count
            with self.subTest(
                    case_idx=case_idx, RS_in=hex(gprs[4]),
                    RB_in=hex(gprs[5]), expected_RA=hex(e.intregs[3])):
                self.add_case(prog, gprs, expected=e)

    def case_pdepd(self):
        prog = Program(list(SVP64Asm(["pdepd 3,4,5"])), bigendian)
        for case_idx in range(200):
            gprs = [0] * 32
            gprs[4] = hash_256(f"pdepd {case_idx} r4") % 2**64
            gprs[5] = hash_256(f"pdepd {case_idx} r5") % 2**64
            e = ExpectedState(pc=4, int_regs=gprs)
            e.intregs[3] = 0
            j = 0
            for i in range(64):
                bit = 1 << i
                if gprs[5] & bit:
                    if gprs[4] & (1 << j):
                        e.intregs[3] |= bit
                    j += 1
            with self.subTest(
                    case_idx=case_idx, RS_in=hex(gprs[4]),
                    RB_in=hex(gprs[5]), expected_RA=hex(e.intregs[3])):
                self.add_case(prog, gprs, expected=e)

    def case_pextd(self):
        prog = Program(list(SVP64Asm(["pextd 3,4,5"])), bigendian)
        for case_idx in range(200):
            gprs = [0] * 32
            gprs[4] = hash_256(f"pextd {case_idx} r4") % 2**64
            gprs[5] = hash_256(f"pextd {case_idx} r5") % 2**64
            e = ExpectedState(pc=4, int_regs=gprs)
            e.intregs[3] = 0
            j = 0
            for i in range(64):
                bit = 1 << i
                if gprs[5] & bit:
                    if gprs[4] & bit:
                        e.intregs[3] |= 1 << j
                    j += 1
            with self.subTest(
                    case_idx=case_idx, RS_in=hex(gprs[4]),
                    RB_in=hex(gprs[5]), expected_RA=hex(e.intregs[3])):
                self.add_case(prog, gprs, expected=e)
