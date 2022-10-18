from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State

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


class SVP64BigIntCases(TestAccumulatorBase):
    def case_sv_bigint_add(self):
        """performs a carry-rollover-vector-add aka "big integer vector add"
        this is remarkably simple, each sv.adde uses and produces a CA which
        goes into the next sv.adde.  arbitrary size is possible (1024+) as
        is looping using the CA bit from one sv.adde on another batch to do
        unlimited-size biginteger add.

        r19/r18: 0x0000_0000_0000_0001 0xffff_ffff_ffff_ffff +
        r21/r20: 0x8000_0000_0000_0000 0x0000_0000_0000_0001 =
        r17/r16: 0x8000_0000_0000_0002 0x0000_0000_0000_0000
        """
        prog = Program(list(SVP64Asm(["sv.adde *16, *18, *20"])), False)
        gprs = [0] * 32
        gprs[18] = 0xffff_ffff_ffff_ffff
        gprs[19] = 0x0000_0000_0000_0001
        gprs[20] = 0x0000_0000_0000_0001
        gprs[21] = 0x8000_0000_0000_0000
        svstate = SVP64State()
        svstate.vl = 2
        svstate.maxvl = 2
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[16] = 0x0000_0000_0000_0000
        e.intregs[17] = 0x8000_0000_0000_0002
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_shift_right_by_scalar(self):
        """performs a bigint shift-right by scalar.

        r18                   r17                   r16                      r3
        0x0000_0000_5000_0002 0x8000_8000_8000_8001 0xffff_ffff_ffff_ffff >> 4
        0x0000_0000_0500_0000 0x2800_0800_0800_0800 0x1fff_ffff_ffff_ffff
        """
        prog = Program(list(SVP64Asm(["sv.dsrd *16,*17,3,1"])), False)
        gprs = [0] * 32
        gprs[16] = 0xffff_ffff_ffff_ffff
        gprs[17] = 0x8000_8000_8000_8001
        gprs[18] = 0x0000_0000_5000_0002
        gprs[3] = 4
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[16] = 0x1fff_ffff_ffff_ffff
        e.intregs[17] = 0x2800_0800_0800_0800
        e.intregs[18] = 0x0000_0000_0500_0000
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_shift_left_by_scalar(self):
        """performs a bigint shift-left by scalar.

        because the result is moved down by one register there is no need
        for reverse-gear.

        r18 is *not* modified (contains its original value).
        r18                   r17                   r16                      r3
        0x0000_0000_0001_0002 0x3fff_ffff_ffff_ffff 0x4000_0000_0000_0001 << 4
        r17                   r16                   r15
        0x0000_0000_0010_0023 0xffff_ffff_ffff_fff4 0x0000_0000_0000_0010
        """
        prog = Program(list(SVP64Asm(["sv.dsld *15,*16,3,1"])), False)
        gprs = [0] * 32
        gprs[15] = 0
        gprs[16] = 0x4000_0000_0000_0001
        gprs[17] = 0x3fff_ffff_ffff_ffff
        gprs[18] = 0x0000_0000_0001_0002
        gprs[3] = 4
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[15] = 0x0000_0000_0000_0010
        e.intregs[16] = 0xffff_ffff_ffff_fff4
        e.intregs[17] = 0x0000_0000_0010_0023
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_mul_by_scalar(self):
        """performs a carry-rollover-vector-mul-with-add with a scalar,
        using "RC" as a 64-bit carry in/out.  matched with the
        sv.divmod2du below

        r18                   r17                   r16
        0x1234_0000_5678_0000 0x9ABC_0000_DEF0_0000 0x1357_0000_9BDF_0000 *
        r3 (scalar factor)                                       0x1_0001 +
        r4 (carry in)                                              0xFEDC =
        r18                   r17                   r16
        0x1234_5678_5678_9ABC 0x9ABC_DEF0_DEF0_1357 0x1357_9BDF_9BDF_FEDC
        r4 (carry out)                                             0x1234
        """
        prog = Program(list(SVP64Asm(["sv.maddedu *16,*16,3,4"])), False)
        gprs = [0] * 32
        gprs[16] = 0x1357_0000_9BDF_0000        # vector...
        gprs[17] = 0x9ABC_0000_DEF0_0000        # ...
        gprs[18] = 0x1234_0000_5678_0000        # ... input
        gprs[3] = 0x1_0001                      # scalar multiplier
        gprs[4] = 0xFEDC                        # 64-bit carry-in
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[16] = 0x1357_9BDF_9BDF_FEDC  # vector...
        e.intregs[17] = 0x9ABC_DEF0_DEF0_1357  # ...
        e.intregs[18] = 0x1234_5678_5678_9ABC  # ... result
        e.intregs[4] = 0x1234                  # 64-bit carry-out
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_scalar_maddedu(self):
        prog = Program(list(SVP64Asm(["sv.maddedu 6,5,3,4"])), False)
        gprs = [0] * 32
        gprs[5] = 0x1357_0000_9BDF_0000        # scalar input
        gprs[3] = 0x1_0001                      # scalar multiplier
        gprs[4] = 0xFEDC                        # 64-bit carry-in
        svstate = SVP64State()
        svstate.vl = 16  # detect writing to RT+MAXVL or RT+1 rather than RC
        svstate.maxvl = 16
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[6] = 0x1357_9BDF_9BDF_FEDC  # scalar output
        e.intregs[4] = 0x1357                  # 64-bit carry-out
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_div_by_scalar(self):
        """performs a carry-rollover-vector-divmod with a scalar,
        using "RC" as a 64-bit carry.  matched with the sv.maddedu
        above it is effectively the scalar-vector inverse

        r18                   r17                   r16
        0x1234_5678_5678_9ABC 0x9ABC_DEF0_DEF0_1357 0x1357_9BDF_9BDF_FEDC /
        r3 (scalar factor)                                       0x1_0001 +
        r4 (carry in at top-end)                            0x1234 << 192 =
        r18                   r17                   r16
        0x1234_0000_5678_0000 0x9ABC_0000_DEF0_0000 0x1357_0000_9BDF_0000 *
        r4 (carry out i.e. scalar remainder)                       0xFEDC 
        """
        prog = Program(list(SVP64Asm(["sv.divmod2du/mrr *16,*16,3,4"])), False)
        gprs = [0] * 32
        gprs[16] = 0x1357_9BDF_9BDF_FEDC  # vector...
        gprs[17] = 0x9ABC_DEF0_DEF0_1357  # ...
        gprs[18] = 0x1234_5678_5678_9ABC  # ... input
        gprs[3] = 0x1_0001                      # scalar multiplier
        gprs[4] = 0x1234                  # 64-bit carry-in
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[16] = 0x1357_0000_9BDF_0000        # vector...
        e.intregs[17] = 0x9ABC_0000_DEF0_0000        # ...
        e.intregs[18] = 0x1234_0000_5678_0000        # ... result
        e.intregs[4] = 0xFEDC                        # 64-bit carry-out
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)
