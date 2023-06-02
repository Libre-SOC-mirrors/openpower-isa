from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.insndb.asm import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.helpers import exts


_MASK32 = ((2 ** 32) - 1)
_MASK64 = ((2 ** 64) - 1)


class ShiftAddCases(TestAccumulatorBase):

    def case_sadd(self):
        for SH in range(4):
            with self.subTest(SH=SH):
                insn = ("sadd 3,4,5,%d" % SH)
                prog = Program(list(SVP64Asm([insn])), False)
                gprs = [0] * 32
                gprs[3] = 0x01234567890abcde
                RA = gprs[4] = 0xf00dcafedeadbeef
                RB = gprs[5] = 0xabadbabedefec8ed
                RT = ((((RB << (SH+1)) & _MASK64) + RA) & _MASK64)
                e = ExpectedState(pc=4, int_regs=gprs)
                e.intregs[3] = RT
                self.add_case(prog, gprs, expected=e)

    def case_saddw(self):
        for SH in range(4):
            with self.subTest(SH=SH):
                insn = ("saddw 3,4,5,%d" % SH)
                prog = Program(list(SVP64Asm([insn])), False)
                gprs = [0] * 32
                gprs[3] = 0x01234567890abcde
                RA = gprs[4] = 0xf00dcafedeadbeef
                RB = gprs[5] = 0xabadbabedefec8ed
                RB_i32 = RB & _MASK32
                if RB_i32 >> 31:
                    RB_i32 -= 1 << 32
                RT = ((((RB_i32 << (SH+1)) & _MASK64) + RA) & _MASK64)
                e = ExpectedState(pc=4, int_regs=gprs)
                e.intregs[3] = RT
                self.add_case(prog, gprs, expected=e)

    def case_sadduw(self):
        for SH in range(4):
            with self.subTest(SH=SH):
                insn = ("sadduw 3,4,5,%d" % SH)
                prog = Program(list(SVP64Asm([insn])), False)
                gprs = [0] * 32
                gprs[3] = 0x01234567890abcde
                RA = gprs[4] = 0xf00dcafedeadbeef
                RB = gprs[5] = 0xabadbabedefec8ed
                RT = (((((RB & _MASK32) << (SH+1)) & _MASK64) + RA) & _MASK64)
                e = ExpectedState(pc=4, int_regs=gprs)
                e.intregs[3] = RT
                self.add_case(prog, gprs, expected=e)

