from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program

_SHIFT_TEST_RANGE = range(-64, 128, 16)


class BigIntCases(TestAccumulatorBase):
    def case_maddedu(self):
        lst = list(SVP64Asm(["maddedu 3,5,6,7"]))
        gprs = [0] * 32
        gprs[5] = 0x123456789ABCDEF
        gprs[6] = 0xFEDCBA9876543210
        gprs[7] = 0x02468ACE13579BDF
        e = ExpectedState(pc=4, int_regs=gprs)
        e.intregs[3] = (gprs[5] * gprs[6] + gprs[7]) % 2 ** 64
        e.intregs[7] = (gprs[5] * gprs[6] + gprs[7]) >> 64
        self.add_case(Program(lst, False), gprs, expected=e)

    def case_divmod2du(self):
        lst = list(SVP64Asm(["divmod2du 3,5,6,7"]))
        gprs = [0] * 32
        gprs[5] = 0x123456789ABCDEF
        gprs[6] = 0xFEDCBA9876543210
        gprs[7] = 0x02468ACE13579BDF
        e = ExpectedState(pc=4, int_regs=gprs)
        v = gprs[5] | (gprs[7] << 64)
        e.intregs[3] = v // gprs[6]
        e.intregs[7] = v % gprs[6]
        self.add_case(Program(lst, False), gprs, expected=e)

    # FIXME: test more divmod2du special cases

    def case_dsld0(self):
        prog = Program(list(SVP64Asm(["dsld 3,4,5,0"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = (gprs[3] << 64) | gprs[4]
                v <<= sh % 64
                e.intregs[3] = (v >> 64) % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsld1(self):
        prog = Program(list(SVP64Asm(["dsld 3,4,5,1"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = (gprs[4] << 64) | gprs[3]
                v <<= sh % 64
                e.intregs[3] = (v >> 64) % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsld2(self):
        prog = Program(list(SVP64Asm(["dsld 3,4,5,2"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = sh % 2 ** 64
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = 0x02468ACE13579BDF
                e = ExpectedState(pc=4, int_regs=gprs)
                v = (gprs[4] << 64) | gprs[5]
                v <<= sh % 64
                e.intregs[3] = (v >> 64) % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsld3(self):
        prog = Program(list(SVP64Asm(["dsld 3,4,5,3"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = gprs[4]
                v <<= sh % 64
                e.intregs[3] = (v >> 64) % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsrd0(self):
        prog = Program(list(SVP64Asm(["dsrd 3,4,5,0"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = (gprs[3] << 64) | gprs[4]
                v >>= sh % 64
                e.intregs[3] = v % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsrd1(self):
        prog = Program(list(SVP64Asm(["dsrd 3,4,5,1"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = (gprs[4] << 64) | gprs[3]
                v >>= sh % 64
                e.intregs[3] = v % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsrd2(self):
        prog = Program(list(SVP64Asm(["dsrd 3,4,5,2"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = sh % 2 ** 64
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = 0x02468ACE13579BDF
                e = ExpectedState(pc=4, int_regs=gprs)
                v = (gprs[4] << 64) | gprs[5]
                v >>= sh % 64
                e.intregs[3] = v % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsrd3(self):
        prog = Program(list(SVP64Asm(["dsrd 3,4,5,3"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[3] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = gprs[4] << 64
                v >>= sh % 64
                e.intregs[3] = v % 2 ** 64
                self.add_case(prog, gprs, expected=e)
