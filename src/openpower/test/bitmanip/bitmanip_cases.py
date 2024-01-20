from openpower.insndb.asm import SVP64Asm
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.test.state import ExpectedState
from nmutil.sim_util import hash_256
from openpower.decoder.isa.caller import SVP64State, CRFields
from openpower.util import log
import struct
import itertools

def bmatflip(ra):
    result = 0
    for j in range(8):
        for k in range(8):
            b = (ra >> (63-k*8-j)) & 1
            result |= b << (63-j*8-k)
    return result


class BitManipTestCase(TestAccumulatorBase):
    def case_gbbd(self):
        lst = ["gbbd 0, 1"]
        lst = list(SVP64Asm(lst, bigendian))
        initial_regs = [0] * 32
        initial_regs[1] = 0x9231_5897_2083_ffff
        e = ExpectedState(pc=4)
        e.intregs[0] = bmatflip(initial_regs[1])
        e.intregs[1] = initial_regs[1]
        log("case_gbbd", bin(initial_regs[1]), bin(e.intregs[0]))
        log("hex", hex(initial_regs[1]), hex(e.intregs[0]))

        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def do_case_crternlogi(self, bf, bfa, bfb, imm, mask):
        lst = [f"crternlogi 3,4,5,%d,%d" % (imm, mask)]
        # set up CR
        bf %= 2 ** 4
        bfa %= 2 ** 4
        bfb %= 2 ** 4
        cr = CRFields()
        cr.crl[3][0:4] = bf
        cr.crl[4][0:4]  = bfa
        cr.crl[5][0:4]  = bfb
        initial_cr = cr.cr.asint()
        print("initial cr", bin(initial_cr), bf, bfa, bfb)
        print("mask tli", bin(mask), bin(imm))

        lst = list(SVP64Asm(lst, bigendian))
        e = ExpectedState(pc=4)
        expected = bf&~mask # start at BF, mask overwrites masked bits only
        checks = (bfb, bfa, bf) # LUT positions 1<<0=bfb 1<<1=bfa 1<<2=bf
        for i in range(4):
            lut_index = 0
            for j, check in enumerate(checks):
                if check & (1<<i):
                    lut_index |= 1<<j
            maskbit = (mask >> i) & 0b1
            if (imm & (1<<lut_index)) and maskbit:
                expected |= 1<<i
        e.crregs[3] = expected
        e.crregs[4] = bfa
        e.crregs[5] = bfb
        self.add_case(Program(lst, bigendian), initial_regs=None, expected=e,
                                       initial_cr=initial_cr)

    def case_crternlogi_0(self):
        self.do_case_crternlogi(0b1111,
                                0b1100,
                                0b1010,
                                0x80, 0b1111)

    def case_crternlogi_random(self):
        for i in range(100):
            rc = bool(hash_256(f"crternlogi rc {i}") & 1)
            imm = hash_256(f"crternlogi imm {i}") & 0xFF
            bf = hash_256(f"crternlogi bf {i}") % 2 ** 4
            bfa = hash_256(f"crternlogi bfa {i}") % 2 ** 4
            bfb = hash_256(f"crternlogi bfb {i}") % 2 ** 4
            msk = hash_256(f"crternlogi msk {i}") % 2 ** 4
            self.do_case_crternlogi(bf, bfa, bfb, imm, msk)

    def do_case_crbinlog(self, bf, bfa, bfb, mask):
        lst = ["crbinlog 3,4,5,%d" % mask]
        # set up CR
        bf %= 2 ** 4
        bfa %= 2 ** 4
        bfb %= 2 ** 4
        cr = CRFields()
        cr.crl[3][0:4] = bf
        cr.crl[4][0:4]  = bfa
        cr.crl[5][0:4]  = bfb
        lut = bfb
        initial_cr = cr.cr.asint()
        print("initial cr", bin(initial_cr), bf, bfa, bfb)
        print("mask lut2", bin(mask), bin(lut))

        lst = list(SVP64Asm(lst, bigendian))
        e = ExpectedState(pc=4)
        expected = bf&~mask # start at BF, mask overwrites masked bits only
        checks = (bfa, bf) # LUT positions 1<<0=bfa 1<<1=bf
        for i in range(4):
            lut_index = 0
            for j, check in enumerate(checks):
                if check & (1<<i):
                    lut_index |= 1<<j
            maskbit = (mask >> i) & 0b1
            if (lut & (1<<lut_index)) and maskbit:
                expected |= 1<<i
        e.crregs[3] = expected
        e.crregs[4] = bfa
        e.crregs[5] = bfb
        self.add_case(Program(lst, bigendian), initial_regs=None, expected=e,
                                       initial_cr=initial_cr)

    def case_crbinlog_0(self):
        self.do_case_crbinlog(0b1111,
                              0b1100,
                              0x8, 0b1111)

    def case_crbinlog_random(self):
        for i in range(100):
            bf = hash_256(f"crbinlog bf {i}") % 2 ** 4
            bfa = hash_256(f"crbinlog bfa {i}") % 2 ** 4
            bfb = hash_256(f"crbinlog bfb {i}") % 2 ** 4
            msk = hash_256(f"crbinlog msk {i}") % 2 ** 4
            self.do_case_crbinlog(bf, bfa, bfb, msk)

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

    def do_case_binlog(self, ra, rb, rc, nh):
        lst = ["binlog 3, 4, 5, 6, %d" % nh]
        initial_regs = [0] * 32
        initial_regs[4] = ra
        initial_regs[5] = rb
        initial_regs[6] = rc
        lut = rc & 0b11111111 # one of two 4-bit LUTs is in 1st 8 bits
        if nh == 1: # top half (bits 4-7... sigh MSB 56-59) else 0-3 (60-63)
            lut = lut >> 4
        lut = lut & 0b1111
        lst = list(SVP64Asm(lst, bigendian))
        e = ExpectedState(pc=4)
        expected = 0
        for i in range(64):
            lut_index = 0
            if rb & 2 ** i:
                lut_index |= 2 ** 0
            if ra & 2 ** i:
                lut_index |= 2 ** 1
            if lut & 2 ** lut_index:
                expected |= 2 ** i
        e.intregs[3] = expected
        e.intregs[4] = ra
        e.intregs[5] = rb
        e.intregs[6] = rc
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_binlog_0(self):
        self.do_case_binlog(0x8000_0000_FFFF_0000,
                            0x8000_0000_FF00_FF00,
                            0x8, 1)
        self.do_case_binlog(0x8000_0000_FFFF_0000,
                            0x8000_0000_FF00_FF00,
                            0x8, 0)

    def case_binlog_random(self):
        for i in range(100):
            ra = hash_256(f"binlog ra {i}") % 2 ** 64
            rb = hash_256(f"binlog rb {i}") % 2 ** 64
            rc = hash_256(f"binlog rc {i}") % 2 ** 8
            nh = hash_256(f"binlog nh {i}") & 0b1
            self.do_case_binlog(ra, rb, rc, nh)

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

    @skip_case("grev removed -- leaving code for later use in grevlut")
    def case_grev_random(self):
        for i in range(100):
            w = hash_256(f"grev w {i}") & 1
            is_imm = hash_256(f"grev is_imm {i}") & 1
            ra = hash_256(f"grev ra {i}") % 2 ** 64
            rb = hash_256(f"grev rb {i}") % 2 ** 64
            self.do_case_grev(w, is_imm, ra, rb)

    @skip_case("grev removed -- leaving code for later use in grevlut")
    def case_grevi_1(self):
        self.do_case_grev(False, True, 14361919363078703450,
                          8396479064514513069)

    @skip_case("grev removed -- leaving code for later use in grevlut")
    def case_grevi_2(self):
        self.do_case_grev(True, True, 397097147229333315, 8326716970539357702)

    @skip_case("grev removed -- leaving code for later use in grevlut")
    def case_grevi_3(self):
        self.do_case_grev(True, True, 0xFFFF_FFFF_0000_0000, 6)

    def case_byterev(self):
        """ brh/brw/brd """
        options = (("HHHH", "brh"), ("LL", "brw"), ("Q", "brd"))
        values = (0x0123456789ABCDEF, 0xFEDCBA9876543210)
        for RS, (pack_str, mnemonic) in itertools.product(values, options):
            prog = Program(list(SVP64Asm(["%s 3,4" % mnemonic])), bigendian)
            chunks = struct.unpack("<" + pack_str, struct.pack("<Q", RS))
            res = struct.unpack("<Q", struct.pack(">" + pack_str, *chunks))[0]
            with self.subTest(mnemonic=mnemonic, RS=hex(RS), expected=hex(res)):
                gprs = [0] * 32
                gprs[4] = RS
                e = ExpectedState(pc=4, int_regs=gprs)
                e.intregs[3] = res
                self.add_case(prog, gprs, expected=e)

    def case_sv_byterev(self):
        """ sv.brh/brw/brd """
        options = (("HHHH", "brh"), ("LL", "brw"), ("Q", "brd"))
        values = range(10)
        for idx, (pack_str, mnemonic) in itertools.product(values, options):
            listing = list(SVP64Asm(["sv.%s *10,*20" % mnemonic]))
            prog = Program(listing, bigendian)
            VL = 5
            svstate = SVP64State()
            svstate.vl = VL
            svstate.maxvl = VL
            gprs = [0] * 128
            for elidx in range(VL):
                k = "sv.%s %d %d r20" % (mnemonic, idx, elidx)
                gprs[20 + elidx] = hash_256(k) % 2**64
            e = ExpectedState(pc=8, int_regs=gprs)
            for elidx in range(VL):
                packed = struct.pack("<Q", gprs[20 + elidx])
                chunks = struct.unpack( "<" + pack_str, packed)
                packed = struct.pack(">" + pack_str, *chunks)
                res = struct.unpack("<Q", packed)[0]
                e.intregs[10 + elidx] = res
            RS = [hex(gprs[20 + i]) for i in range(VL)],
            res =[hex(e.intregs[10 + i]) for i in range(VL)]
            with self.subTest(case_idx=idx, RS_in=RS, expected_RA=res):
                self.add_case(prog, gprs, expected=e, initial_svstate=svstate)
