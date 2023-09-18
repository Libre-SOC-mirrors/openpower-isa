from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.insndb.asm import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.helpers import exts

_SHIFT_TEST_RANGE = list(range(-64, 128, 16)) + [1, 63]
_MASK32 = ((2 ** 32) - 1)
_MASK64 = ((2 ** 64) - 1)


def cr_calc(val, ov):
    XLEN=64
    msb = (val & (1<<(XLEN-1))) != 0
    lsbs = (val & ~(1<<(XLEN-1))) != 0
    crf = 0
    if val == 0:           # zero
        crf |= 0b010
    elif lsbs and not msb: # positive
        crf |= 0b100
    elif lsbs and msb: # negative
        crf |= 0b1000
    if ov:
        crf |= 0b0001
    return crf


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

    def case_maddedus(self):
        lst = list(SVP64Asm(["maddedus 3,5,6,7"]))
        gprs = [0] * 32
        gprs[5] = 0x8123456789ABCDEF
        gprs[6] = 0xFEDCBA9876543210
        gprs[7] = 0x82468ACE13579BDF
        e = ExpectedState(pc=4, int_regs=gprs)
        v = gprs[5] * exts(gprs[6], 64) + exts(gprs[7], 64)
        e.intregs[3] = v % 2 ** 64
        e.intregs[7] = (v >> 64) % 2 ** 64
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

    def case_dsld0_(self):
        prog = Program(list(SVP64Asm(["dsld. 3,4,5,6"])), False)
        for vals in [(0x0000_0000_0000_0000, 0, 0x0000_0000_0000_0000),
                     (0x8000_0000_0000_0000, 1, 0x0000_0000_0000_0000),
                     (0xffff_ffff_ffff_ffff, 1, 0x0000_0000_0000_0001),
                     (0x0fff_ffff_ffff_fff0, 1, 0x8000_0000_0000_0001),
                     (0xdfff_ffff_ffff_ffff, 1, 0x8000_0000_0000_0000),
                    ]:
            (ra, rb, rc) = vals
            with self.subTest(ra=ra, rb=rb, rc=rc):
                gprs = [0] * 32
                gprs[4] = ra
                gprs[5] = rb
                gprs[6] = rc
                e = ExpectedState(pc=4, int_regs=gprs, crregs=8)
                v = ra
                v <<= rb % 64
                mask = (1 << (rb % 64))-1
                v |= rc & mask
                e.intregs[3] = v % 2 ** 64
                e.intregs[6] = (v >> 64) % 2 ** 64
                e.crregs[0] = cr_calc(e.intregs[3], ov=e.intregs[6] != 0)
                self.add_case(prog, gprs, expected=e)

    def case_dsld0(self):
        prog = Program(list(SVP64Asm(["dsld 3,4,5,6"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[6] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                v = gprs[4]
                v <<= sh % 64
                mask = (1 << (sh % 64))-1
                v |= gprs[6] & mask
                e.intregs[3] = v % 2 ** 64
                e.intregs[6] = (v >> 64) % 2 ** 64
                self.add_case(prog, gprs, expected=e)

    def case_dsrd0(self):
        prog = Program(list(SVP64Asm(["dsrd 3,4,5,6"])), False)
        for sh in _SHIFT_TEST_RANGE:
            with self.subTest(sh=sh):
                gprs = [0] * 32
                gprs[6] = 0x123456789ABCDEF
                gprs[4] = 0xFEDCBA9876543210
                gprs[5] = sh % 2 ** 64
                e = ExpectedState(pc=4, int_regs=gprs)
                # XXX the function here should be extracted to a library,
                # see poly1305_donna.py
                v = (gprs[4] << 64)
                v >>= sh % 64
                mask = ~((2 ** 64 - 1) >> (sh % 64))
                v |= (gprs[6] & mask) << 64
                print("case_dsrd0", hex(mask), sh, hex(v))
                e.intregs[3] = (v >> 64) % 2 ** 64
                e.intregs[6] = v % 2 ** 64
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

        r5 starts off (as the carry-in) at 0x9000_0000_0000_0000

        r18                   r17                   r16                      r3
        0x0000_0000_5000_0002 0x8000_8000_8000_8001 0xffff_ffff_ffff_ffff >> 4
        0x0000_0000_0500_0000 0x2800_0800_0800_0800 0x1fff_ffff_ffff_ffff

        with the 4-bit part that drops out of the 4 LSBs of r16 ending up
        in r0
        """
        prog = Program(list(SVP64Asm(["sv.dsrd/mrr *16,*16,3,5"])), False)
        gprs = [0] * 32
        gprs[5] = 0x9000_0000_0000_0000
        gprs[16] = 0xffff_ffff_ffff_ffff
        gprs[17] = 0x8000_8000_8000_8001
        gprs[18] = 0x0000_0000_5000_0002
        gprs[3] = 4
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[5] = 0xf000_0000_0000_0000   # remainder (shifted out of 16)
        e.intregs[16] = 0x1fff_ffff_ffff_ffff
        e.intregs[17] = 0x2800_0800_0800_0800
        e.intregs[18] = 0x9000_0000_0500_0000  # initial r0 into top
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_shift_left_by_scalar(self):
        """performs a bigint shift-left by scalar.

        because the result is moved down by one register there is no need
        for reverse-gear.

        r5 starts off as the carry-in: 0x0000_0000_0000_000a

        r18                   r17                   r16                      r3
        0x9000_0000_0001_0002 0x3fff_ffff_ffff_ffff 0x4000_0000_0000_0001 << 4
        r18                   r17                   r16
        0x0000_0000_0010_0023 0xffff_ffff_ffff_fff4 0x0000_0000_0000_0010

        with the top 4 bits of r18 being pushed into the LSBs of r14
        """
        prog = Program(list(SVP64Asm(["sv.dsld *16,*16,3,5"])), False)
        gprs = [0] * 32
        gprs[5] = 0x0000_0000_0000_000a
        gprs[16] = 0x4000_0000_0000_0001
        gprs[17] = 0x3fff_ffff_ffff_ffff
        gprs[18] = 0x9000_0000_0001_0002
        gprs[3] = 4
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[5] = 9
        e.intregs[16] = 0x0000_0000_0000_001a
        e.intregs[17] = 0xffff_ffff_ffff_fff4
        e.intregs[18] = 0x0000_0000_0010_0023
        self.add_case(prog, gprs, expected=e, initial_svstate=svstate)

    def case_sv_bigint_shift_left_then_back(self):
        """performs a bigint shift-right then a shift-left, should
        get the same results... but doesn't.  reason: the carry-in
        compared to carry-out is shifted to the opposite end
        """
        prog = Program(list(SVP64Asm(["sv.dsrd/mrr *16,*16,3,5",
                                      "sv.dsld *16,*16,3,5"])), False)
        gprs = [0] * 32
        gprs[5] = 0x9000_0000_0000_0000
        gprs[16] = 0xffff_ffff_ffff_ffff
        gprs[17] = 0x8000_8000_8000_8001
        gprs[18] = 0x0000_0000_5000_0002
        gprs[3] = 4
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=16, int_regs=gprs)
        e.intregs[5] = 0x0000_0000_0000_0009
        e.intregs[16] = 0xffff_ffff_ffff_fff0
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

    def case_sv_unsigned_bigint_mul_by_signed_scalar(self):
        """performs a carry-rollover-vector-mul-with-add with a scalar,
        using "RC" as a 64-bit carry in/out.
        outputs are negative of sv.maddedu test.

        r18                   r17                   r16
        0x1234_0000_5678_0000 0x9ABC_0000_DEF0_0000 0x1357_0000_9BDF_0000 *
        r3 (scalar factor)                                      -0x1_0001 +
        r4 (carry in)                                             -0xFEDC =
        -0x1234_1234_5678_5678_9ABC_9ABC_DEF0_DEF0_1357_1357_9BDF_9BDF_FEDC =
        r18                   r17                   r16
        0xEDCB_A987_A987_6543 0x6543_210F_210F_ECA8 0xECA8_6420_6420_0124
        r4 (carry out)                              0xFFFF_FFFF_FFFF_EDCB
        """
        prog = Program(list(SVP64Asm(["sv.maddedus *16,*16,3,4"])), False)
        gprs = [0] * 32
        gprs[16] = 0x1357_0000_9BDF_0000        # vector...
        gprs[17] = 0x9ABC_0000_DEF0_0000        # ...
        gprs[18] = 0x1234_0000_5678_0000        # ... input
        gprs[3] = -0x1_0001 % 2 ** 64           # scalar multiplier
        gprs[4] = -0xFEDC % 2 ** 64             # 64-bit carry-in
        svstate = SVP64State()
        svstate.vl = 3
        svstate.maxvl = 3
        e = ExpectedState(pc=8, int_regs=gprs)
        e.intregs[16] = 0xECA8_6420_6420_0124  # vector...
        e.intregs[17] = 0x6543_210F_210F_ECA8  # ...
        e.intregs[18] = 0xEDCB_A987_A987_6543  # ... result
        e.intregs[4] = 0xFFFF_FFFF_FFFF_EDCB   # 64-bit carry-out
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
