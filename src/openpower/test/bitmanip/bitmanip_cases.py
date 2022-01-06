from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.test.state import ExpectedState
from nmutil.sim_util import hash_256


class BitManipTestCase(TestAccumulatorBase):
    def do_case_ternlogi(self, rt, ra, rb, imm):
        lst = [f"ternlogi 3, 4, 5, {imm}"]
        initial_regs = [0] * 32
        rt %= 2 ** 64
        ra %= 2 ** 64
        rb %= 2 ** 64
        initial_regs[3] = rt
        initial_regs[4] = ra
        initial_regs[5] = rb
        lst = list(SVP64Asm(lst, bigendian))
        e = ExpectedState(pc=4)
        expected = 0
        for i in range(64):
            lut_index = 0
            if rb & 2 ** i:
                lut_index |= 2 ** 0
            if ra & 2 ** i:
                lut_index |= 2 ** 1
            if rt & 2 ** i:
                lut_index |= 2 ** 2
            if imm & 2 ** lut_index:
                expected |= 2 ** i
        e.intregs[3] = expected
        e.intregs[4] = ra
        e.intregs[5] = rb
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_ternlogi_0(self):
        self.do_case_ternlogi(0x8000_0000_FFFF_0000,
                              0x8000_0000_FF00_FF00,
                              0x8000_0000_F0F0_F0F0, 0x80)

    def case_ternlogi_FF(self):
        self.do_case_ternlogi(0, 0, 0, 0xFF)

    def case_ternlogi_random(self):
        for i in range(100):
            imm = hash_256(f"ternlogi imm {i}") & 0xFF
            rt = hash_256(f"ternlogi rt {i}") % 2 ** 64
            ra = hash_256(f"ternlogi ra {i}") % 2 ** 64
            rb = hash_256(f"ternlogi rb {i}") % 2 ** 64
            self.do_case_ternlogi(rt, ra, rb, imm)
