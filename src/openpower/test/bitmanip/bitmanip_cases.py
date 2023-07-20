from openpower.insndb.asm import SVP64Asm
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.test.state import ExpectedState
from nmutil.sim_util import hash_256
import struct


class BitManipTestCase(TestAccumulatorBase):
    def do_case_ternlogi(self, rc, rt, ra, rb, imm):
        rc_dot = "." if rc else ""
        lst = [f"ternlogi{rc_dot} 3, 4, 5, {imm}"]
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
        if rc:
            if expected & 2 ** 63:  # sign extend
                expected -= 2 ** 64
            eq = expected == 0
            gt = expected > 0
            lt = expected < 0
            e.crregs[0] = (eq << 1) | (gt << 2) | (lt << 3)
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def do_case_grev(self, w, is_imm, ra, rb):
        bits = 32 if w else 64
        masked_rb = rb % bits
        if is_imm:
            lst = [f"grev{'w' if w else ''}i. 3, 4, {masked_rb}"]
        else:
            lst = [f"grev{'w' if w else ''}. 3, 4, 5"]
        initial_regs = [0] * 32
        ra %= 2 ** 64
        rb %= 2 ** 64
        initial_regs[4] = ra
        initial_regs[5] = rb
        lst = list(SVP64Asm(lst, bigendian))
        e = ExpectedState(pc=4)
        expected = 0
        for i in range(bits):
            dest_bit = i ^ masked_rb
            if ra & 2 ** i:
                expected |= 2 ** dest_bit
        e.intregs[3] = expected
        e.intregs[4] = ra
        e.intregs[5] = rb
        if expected & 2 ** 63:  # sign extend
            expected -= 2 ** 64
        eq = expected == 0
        gt = expected > 0
        lt = expected < 0
        e.crregs[0] = (eq << 1) | (gt << 2) | (lt << 3)
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_ternlogi_0(self):
        self.do_case_ternlogi(False,
                              0x8000_0000_FFFF_0000,
                              0x8000_0000_FF00_FF00,
                              0x8000_0000_F0F0_F0F0, 0x80)
        self.do_case_ternlogi(True,
                              0x8000_0000_FFFF_0000,
                              0x8000_0000_FF00_FF00,
                              0x8000_0000_F0F0_F0F0, 0x80)

    def case_ternlogi_FF(self):
        self.do_case_ternlogi(False, 0, 0, 0, 0xFF)
        self.do_case_ternlogi(True, 0, 0, 0, 0xFF)

    def case_ternlogi_random(self):
        for i in range(100):
            rc = bool(hash_256(f"ternlogi rc {i}") & 1)
            imm = hash_256(f"ternlogi imm {i}") & 0xFF
            rt = hash_256(f"ternlogi rt {i}") % 2 ** 64
            ra = hash_256(f"ternlogi ra {i}") % 2 ** 64
            rb = hash_256(f"ternlogi rb {i}") % 2 ** 64
            self.do_case_ternlogi(rc, rt, ra, rb, imm)

    @skip_case("invalid, replaced by grevlut")
    def case_grev_random(self):
        for i in range(100):
            w = hash_256(f"grev w {i}") & 1
            is_imm = hash_256(f"grev is_imm {i}") & 1
            ra = hash_256(f"grev ra {i}") % 2 ** 64
            rb = hash_256(f"grev rb {i}") % 2 ** 64
            self.do_case_grev(w, is_imm, ra, rb)

    @skip_case("invalid, replaced by grevlut")
    def case_grevi_1(self):
        self.do_case_grev(False, True, 14361919363078703450,
                          8396479064514513069)

    @skip_case("invalid, replaced by grevlut")
    def case_grevi_2(self):
        self.do_case_grev(True, True, 397097147229333315, 8326716970539357702)

    @skip_case("invalid, replaced by grevlut")
    def case_grevi_3(self):
        self.do_case_grev(True, True, 0xFFFF_FFFF_0000_0000, 6)

    def case_byterev(self):
        """ brh/brw/brd """
        for pack_str, mnemonic in ("HHHH", "brh"), ("LL", "brw"), ("Q", "brd"):
            prog = Program(list(SVP64Asm([f"{mnemonic} 3,4"])), bigendian)
            for RS in 0x0123456789ABCDEF, 0xFEDCBA9876543210:
                chunks = struct.unpack("<" + pack_str, struct.pack("<Q", RS))
                expected = struct.unpack(
                    "<Q", struct.pack(">" + pack_str, *chunks))[0]
                with self.subTest(
                    mnemonic=mnemonic, RS=hex(RS), expected=hex(expected),
                ):
                    gprs = [0] * 32
                    gprs[4] = RS
                    e = ExpectedState(pc=4, int_regs=gprs)
                    e.intregs[3] = expected
                    self.add_case(prog, gprs, expected=e)
