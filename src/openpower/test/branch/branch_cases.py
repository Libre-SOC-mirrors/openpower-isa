from openpower.decoder.isa.caller import special_sprs
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.endian import bigendian

from openpower.test.common import TestAccumulatorBase
import random


class BranchTestCase(TestAccumulatorBase):

    def case_0_regression_unconditional(self):
        for i in range(2):
            imm = random.randrange(-1 << 23, (1 << 23)-1) * 4
            lst = [f"bl {imm}"]
            initial_regs = [0] * 32
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_unconditional(self):
        choices = ["b", "ba", "bl", "bla"]
        for i in range(20):
            choice = random.choice(choices)
            imm = random.randrange(-1 << 23, (1 << 23)-1) * 4
            lst = [f"{choice} {imm}"]
            initial_regs = [0] * 32
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_bc_cr(self):
        for i in range(20):
            bc = random.randrange(-1 << 13, (1 << 13)-1) * 4
            bo = random.choice([0b01100, 0b00100, 0b10100])
            bi = random.randrange(0, 31)
            cr = random.randrange(0, (1 << 32)-1)
            lst = [f"bc {bo}, {bi}, {bc}"]
            initial_regs = [0] * 32
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_bc_ctr(self):
        for i in range(20):
            bc = random.randrange(-1 << 13, (1 << 13)-1) * 4
            bo = random.choice([0, 2, 8, 10, 16, 18])
            bi = random.randrange(0, 31)
            cr = random.randrange(0, (1 << 32)-1)
            ctr = random.randint(0, (1 << 32)-1)
            lst = [f"bc {bo}, {bi}, {bc}"]
            initial_sprs = {9: SelectableInt(ctr, 64)}
            self.add_case(Program(lst, bigendian),
                          initial_sprs=initial_sprs,
                          initial_cr=cr)

    def case_bc_ctr_regression(self):
        bc = 13116
        bo = 8
        bi = 6
        cr = 0x100983
        ctr = 0x420abd56
        lst = [f"bc {bo}, {bi}, {bc}"]
        initial_sprs = {9: SelectableInt(ctr, 64)}
        self.add_case(Program(lst, bigendian),
                      initial_sprs=initial_sprs,
                      initial_cr=cr)

    def case_bc_reg(self):
        # XXX: bcctr and bcctrl time out (irony: they're counters)
        choices = ["bclr", "bclrl", "bcctr", "bcctrl", "bctar", "bctarl"]
        for insn in choices:
            for i in range(20):
                bh = random.randrange(0, 3)
                bo = random.choice([4, 12])
                bi = random.randrange(0, 31)
                cr = random.randrange(0, (1 << 32)-1)
                ctr = random.randint(0, (1 << 32)-1)
                lr = random.randint(0, (1 << 64)-1) & ~3
                tar = random.randint(0, (1 << 64)-1) & ~3
                lst = [f"{insn} {bo}, {bi}, {bh}"]
                initial_sprs = {9: SelectableInt(ctr, 64),
                                8: SelectableInt(lr, 64),
                                815: SelectableInt(tar, 64)}
                self.add_case(Program(lst, bigendian),
                              initial_sprs=initial_sprs,
                              initial_cr=cr)

    def case_bc_microwatt_1_regression(self):
        """bc found to be testing ctr rather than (ctr-1)
        11fb4:   08 00 49 40     bc      2,4*cr2+gt,0x11fbc
        cr_file.vhdl:83:13:@136835ns:(report note): Reading CR 33209703
        """
        lst = ["bc 2, 9, 8"]
        initial_regs = [0] * 32
        cr = 0x33209703
        self.add_case(Program(lst, bigendian), initial_regs,
                              initial_cr=cr)

    def case_bc_microwatt_2_regression(self):
        """modified version, set CTR=1 so that it hits zero in BC
        """
        lst = ["bc 2, 9, 8"]
        initial_regs = [0] * 32
        cr = 0x33209703
        ctr = 1
        initial_sprs = {9: SelectableInt(ctr, 64),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                              initial_sprs=initial_sprs,
                              initial_cr=cr)

