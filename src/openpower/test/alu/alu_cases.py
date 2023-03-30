import random
from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.power_enums import XER_bits
from openpower.decoder.isa.caller import special_sprs
from openpower.decoder.helpers import exts
from openpower.test.state import ExpectedState
from openpower.util import log
from pathlib import Path
import gzip
import json
import sys
from hashlib import sha256
from functools import lru_cache

# output-for-v0.2.0-7-g95fdd1c.json.gz generated from:
# https://salsa.debian.org/Kazan-team/power-instruction-analyzer/-/commit/95fdd1c4edbd91c0a02b772ba02aa2045101d2b0
# running on POWER9
PIA_OUTPUT_URL = "https://ftp.libre-soc.org/power-instruction-analyzer/output-for-v0.2.0-7-g95fdd1c.json.gz"
PIA_OUTPUT_SHA256 = "2ad50464eb6c9b6bf2dad2ee16b6820a34024bc008ea86818845cf14f7f457ad"
PIA_OUTPUT_PATH = Path(__file__).parent / PIA_OUTPUT_URL.rpartition('/')[2]


def download_pia_output():
    from urllib.request import urlopen
    from shutil import copyfileobj
    with PIA_OUTPUT_PATH.open("wb") as f:
        print(f"downloading {PIA_OUTPUT_URL} to {PIA_OUTPUT_PATH}",
              file=sys.stderr, flush=True)
        with urlopen(PIA_OUTPUT_URL) as response:
            copyfileobj(response, f)


@lru_cache(maxsize=None)
def read_pia_output(filter_fn=lambda _: True):
    tried_download = False
    while True:
        try:
            file_bytes = PIA_OUTPUT_PATH.read_bytes()
            digest = sha256(file_bytes).hexdigest()
            if digest != PIA_OUTPUT_SHA256:
                raise Exception(f"{PIA_OUTPUT_PATH} has wrong hash, expected "
                                f"{PIA_OUTPUT_SHA256} got {digest}")
            file_bytes = gzip.decompress(file_bytes)
            test_cases = json.loads(file_bytes)['test_cases']
            return list(filter(filter_fn, test_cases))
        except:
            if tried_download:
                raise
            pass
        tried_download = True
        download_pia_output()


@lru_cache(maxsize=None)
def get_addmeo_subfmeo_reference_cases():
    return read_pia_output(lambda i: i['instr'] in ("addmeo", "subfmeo"))


def check_addmeo_subfmeo_matches_reference(instr, case_filter, out):
    case_filter = {
        'instr': instr,
        'ra': '0x0', 'ca': False, 'ca32': False,
        'so': False, 'ov': False, 'ov32': False,
        **case_filter
    }
    for case in get_addmeo_subfmeo_reference_cases():
        skip = False
        for k, v in case_filter.items():
            if case[k] != v:
                skip = True
                break
        if skip:
            continue
        reference_outputs = case['native_outputs']
        for k, v in out.items():
            assert reference_outputs[k] == v, (
                f"{instr} outputs don't match reference:\n"
                f"case_filter={case_filter}\nout={out}\n"
                f"reference_outputs={reference_outputs}")
        log(f"PIA reference successfully matched: {case_filter}")
        return True
    log(f"PIA reference not found: {case_filter}")
    return False


class ALUTestCase(TestAccumulatorBase):
    def case_addex(self):
        lst = [f"addex 3, 4, 5, 0"]
        program = Program(lst, bigendian)
        values = (*range(-2, 4), ~1 << 63, (1 << 63) - 1)
        for ra in values:
            ra %= 1 << 64
            for rb in values:
                rb %= 1 << 64
                for ov in (0, 1):
                    with self.subTest(ra=hex(ra), rb=hex(rb), ov=ov):
                        initial_regs = [0] * 32
                        initial_regs[4] = ra
                        initial_regs[5] = rb
                        initial_sprs = {}
                        xer = SelectableInt(0, 64)
                        xer[XER_bits['OV']] = ov
                        initial_sprs[special_sprs['XER']] = xer
                        e = ExpectedState(pc=4)
                        v = ra + rb + ov
                        v32 = (ra % (1 << 32)) + (rb % (1 << 32)) + ov
                        ov = v >> 64
                        ov32 = v32 >> 32
                        e.intregs[3] = v % (1 << 64)
                        e.intregs[4] = ra
                        e.intregs[5] = rb
                        e.ov = (ov32 << 1) | ov
                        self.add_case(program, initial_regs,
                                      initial_sprs=initial_sprs, expected=e)

    def case_nego_(self):
        lst = [f"nego. 3, 4"]
        initial_regs = [0] * 32
        initial_regs[4] = 0
        e = ExpectedState(pc=4)
        e.intregs[3] = 0
        e.intregs[4] = 0
        e.so = 0
        e.ov = 0
        e.crregs[0] = 2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_regression(self):
        lst = [f"add. 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xa709a363416426bd
        e.crregs[0] = 0x8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_regression(self):
        lst = [f"extsw 3, 1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xb6a1fc6c8576af91
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xb6a1fc6c8576af91
        e.intregs[3] = 0xffffffff8576af91
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"subf 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3d7f3f7ca24bac7b
        initial_regs[2] = 0xf6b2ac5e13ee15c2
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x3d7f3f7ca24bac7b
        e.intregs[2] = 0xf6b2ac5e13ee15c2
        e.intregs[3] = 0xb9336ce171a26947
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"subf 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x833652d96c7c0058
        initial_regs[2] = 0x1c27ecff8a086c1a
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x833652d96c7c0058
        e.intregs[2] = 0x1c27ecff8a086c1a
        e.intregs[3] = 0x98f19a261d8c6bc2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"extsb 3, 1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x7f9497aaff900ea0
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x7f9497aaff900ea0
        e.intregs[3] = 0xffffffffffffffa0
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"add 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x2e08ae202742baf8
        initial_regs[2] = 0x86c43ece9efe5baa
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x2e08ae202742baf8
        e.intregs[2] = 0x86c43ece9efe5baa
        e.intregs[3] = 0xb4cceceec64116a2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rand(self):
        insns = ["add", "add.", "subf"]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)

            e = ExpectedState(pc=4)
            e.intregs[1] = initial_regs[1]
            e.intregs[2] = initial_regs[2]
            if choice == "add":
                result = initial_regs[1] + initial_regs[2]
                e.intregs[3] = result & ((2**64)-1)
            elif choice == "add.":
                result = initial_regs[1] + initial_regs[2]
                e.intregs[3] = result & ((2**64)-1)
                eq = 0
                gt = 0
                lt = 0
                if (e.intregs[3] & (1 << 63)) != 0:
                    lt = 1
                elif e.intregs[3] == 0:
                    eq = 1
                else:
                    gt = 1
                e.crregs[0] = (eq << 1) | (gt << 2) | (lt << 3)
            elif choice == "subf":
                result = ~initial_regs[1] + initial_regs[2] + 1
                e.intregs[3] = result & ((2**64)-1)

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_addme_ca_0(self):
        insns = ["addme", "addme.", "addmeo", "addmeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            for value in [0x7ffffffff,
                          0xffff80000]:
                initial_regs = [0] * 32
                initial_regs[16] = value
                initial_sprs = {}
                xer = SelectableInt(0, 64)
                xer[XER_bits['CA']] = 0  # input carry is 0 (see test below)
                initial_sprs[special_sprs['XER']] = xer

                # create expected results.  pc should be 4 (one instruction)
                e = ExpectedState(pc=4)
                # input value should not be modified
                e.intregs[16] = value
                # carry-out should always occur
                e.ca = 0x3
                # create output value
                if value == 0x7ffffffff:
                    e.intregs[6] = 0x7fffffffe
                else:
                    e.intregs[6] = 0xffff7ffff
                # CR version needs an expected CR
                if '.' in choice:
                    e.crregs[0] = 0x4
                self.add_case(Program(lst, bigendian),
                              initial_regs, initial_sprs,
                              expected=e)

    def case_addme_ca_1(self):
        insns = ["addme", "addme.", "addmeo", "addmeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            for value in [0x7ffffffff,  # fails, bug #476
                          0xffff80000]:
                initial_regs = [0] * 32
                initial_regs[16] = value
                initial_sprs = {}
                xer = SelectableInt(0, 64)
                # input carry is 1 (differs from above)
                xer[XER_bits['CA']] = 1
                initial_sprs[special_sprs['XER']] = xer
                e = ExpectedState(pc=4)
                e.intregs[16] = value
                e.ca = 0x3
                if value == 0x7ffffffff:
                    e.intregs[6] = 0x7ffffffff
                else:
                    e.intregs[6] = 0xffff80000
                if '.' in choice:
                    e.crregs[0] = 0x4
                self.add_case(Program(lst, bigendian),
                              initial_regs, initial_sprs, expected=e)

    def case_addme_ca_so_4(self):
        """test of SO being set
        """
        lst = ["addmeo. 6, 16"]
        initial_regs = [0] * 32
        initial_regs[16] = 0x7fffffffffffffff
        initial_sprs = {}
        xer = SelectableInt(0, 64)
        xer[XER_bits['CA']] = 1
        initial_sprs[special_sprs['XER']] = xer
        e = ExpectedState(pc=4)
        e.intregs[16] = 0x7fffffffffffffff
        e.intregs[6] = 0x7fffffffffffffff
        e.ca = 0x3
        e.crregs[0] = 0x4
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs, expected=e)

    def case_addme_ca_so_3(self):
        """bug where SO does not get passed through to CR0
        """
        lst = ["addme. 6, 16"]
        initial_regs = [0] * 32
        initial_regs[16] = 0x7ffffffff
        initial_sprs = {}
        xer = SelectableInt(0, 64)
        xer[XER_bits['CA']] = 1
        xer[XER_bits['SO']] = 1
        initial_sprs[special_sprs['XER']] = xer
        e = ExpectedState(pc=4)
        e.intregs[16] = 0x7ffffffff
        e.intregs[6] = 0x7ffffffff
        e.crregs[0] = 0x5
        e.so = 0x1
        e.ca = 0x3
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs, expected=e)

    def case_addme_subfme_ca_propagation(self):
        for flags in range(1 << 2):
            ca_in = bool(flags & 1)
            is_sub = (flags >> 1) & 1
            if is_sub:
                prog = Program(["subfmeo 3, 4"], bigendian)
            else:
                prog = Program(["addmeo 3, 4"], bigendian)
            for i in range(-2, 3):
                ra = i % 2 ** 64
                with self.subTest(ra=hex(ra), ca=ca_in, is_sub=is_sub):
                    initial_regs = [0] * 32
                    initial_regs[4] = ra
                    initial_sprs = {}
                    xer = SelectableInt(0, 64)
                    xer[XER_bits['CA']] = ca_in
                    initial_sprs[special_sprs['XER']] = xer
                    e = ExpectedState(pc=4)
                    e.intregs[4] = ra
                    rb = 2 ** 64 - 1  # add 0xfff...fff *not* -1
                    expected = ca_in + rb
                    expected32 = ca_in + (rb % 2 ** 32)
                    inv_ra = ra
                    if is_sub:
                        # 64-bit bitwise not
                        inv_ra = ~ra % 2 ** 64
                    expected += inv_ra
                    expected32 += inv_ra % 2 ** 32
                    rt_out = expected % 2 ** 64
                    e.intregs[3] = rt_out
                    ca = bool(expected >> 64)
                    ca32 = bool(expected32 >> 32)
                    e.ca = (ca32 << 1) | ca
                    # use algorithm from microwatt's calc_ov
                    # https://github.com/antonblanchard/microwatt/blob/5c6d57de3056bd08fdc1f656bc8656635a77512b/execute1.vhdl#L284
                    axb = inv_ra ^ rb
                    emsb = (expected >> 63) & 1
                    ov = ca ^ emsb and not (axb >> 63) & 1
                    e32msb = (expected32 >> 31) & 1
                    ov32 = ca32 ^ e32msb and not (axb >> 31) & 1
                    e.ov = (ov32 << 1) | ov
                    check_addmeo_subfmeo_matches_reference(
                        instr='subfmeo' if is_sub else 'addmeo',
                        case_filter={
                            'ra': f'0x{ra:X}', 'ca': ca_in,
                        }, out={
                            'rt': f'0x{rt_out:X}', 'ca': ca,
                            'ca32': ca32, 'ov': ov, 'ov32': ov32,
                        })
                    self.add_case(prog, initial_regs, initial_sprs,
                                  expected=e)

    def case_addze(self):
        insns = ["addze", "addze.", "addzeo", "addzeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            initial_regs = [0] * 32
            initial_regs[16] = 0x00ff00ff00ff0080
            e = ExpectedState(pc=4)
            e.intregs[16] = 0xff00ff00ff0080
            e.intregs[6] = 0xff00ff00ff0080
            if '.' in choice:
                e.crregs[0] = 0x4
            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_addis_nonzero_r0_regression(self):
        lst = [f"addis 3, 0, 1"]
        print(lst)
        initial_regs = [0] * 32
        initial_regs[0] = 5
        e = ExpectedState(initial_regs, pc=4)
        e.intregs[3] = 0x10000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_addis_nonzero_r0(self):
        for i in range(10):
            imm = random.randint(-(1 << 15), (1 << 15)-1)
            lst = [f"addis 3, 0, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[0] = random.randint(0, (1 << 64)-1)
            e = ExpectedState(pc=4)
            e.intregs[0] = initial_regs[0]
            e.intregs[3] = (imm << 16) & ((1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rand_imm(self):
        insns = ["addi", "addis", "subfic"]
        for i in range(10):
            choice = random.choice(insns)
            imm = random.randint(-(1 << 15), (1 << 15)-1)
            lst = [f"{choice} 3, 1, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)

            e = ExpectedState(pc=4)
            e.intregs[1] = initial_regs[1]
            if choice == "addi":
                result = initial_regs[1] + imm
                e.intregs[3] = result & ((2**64)-1)
            elif choice == "addis":
                result = initial_regs[1] + (imm << 16)
                e.intregs[3] = result & ((2**64)-1)
            elif choice == "subfic":
                result = ~initial_regs[1] + imm + 1
                value = (~initial_regs[1]+2**64) + (imm) + 1
                if imm < 0:
                    value += 2**64
                carry_out = value & (1 << 64) != 0
                value = (~initial_regs[1]+2**64 & 0xffff_ffff) + imm + 1
                if imm < 0:
                    value += 2**32
                carry_out32 = value & (1 << 32) != 0
                e.intregs[3] = result & ((2**64)-1)
                e.ca = carry_out | (carry_out32 << 1)

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_adde(self):
        lst = ["adde. 5, 6, 7"]
        for i in range(10):
            initial_regs = [0] * 32
            initial_regs[6] = random.randint(0, (1 << 64)-1)
            initial_regs[7] = random.randint(0, (1 << 64)-1)
            initial_sprs = {}
            xer = SelectableInt(0, 64)
            xer[XER_bits['CA']] = 1
            initial_sprs[special_sprs['XER']] = xer
            # calculate result *including carry* and mask it to 64-bit
            # (if it overflows, we don't care, because this is not addeo)
            result = 1 + initial_regs[6] + initial_regs[7]
            # detect 65th bit as carry-out?
            carry_out = result & (1 << 64) != 0
            carry_out32 = (initial_regs[6] & 0xffff_ffff) + \
                (initial_regs[7] & 0xffff_ffff) & (1 << 32) != 0
            result = result & ((1 << 64)-1)  # round
            eq = 0
            gt = 0
            lt = 0
            if (result & (1 << 63)) != 0:
                lt = 1
            elif result == 0:
                eq = 1
            else:
                gt = 1
            # now construct the state
            e = ExpectedState(pc=4)
            e.intregs[6] = initial_regs[6]  # should be same as initial
            e.intregs[7] = initial_regs[7]  # should be same as initial
            e.intregs[5] = result
            # carry_out goes into bit 0 of ca, carry_out32 into bit 1
            e.ca = carry_out | (carry_out32 << 1)
            # eq goes into bit 1 of CR0, gt into bit 2, lt into bit 3.
            # SO goes into bit 0 but overflow doesn't occur here [we hope]
            e.crregs[0] = (eq << 1) | (gt << 2) | (lt << 3)

            self.add_case(Program(lst, bigendian),
                          initial_regs, initial_sprs, expected=e)

    def case_cmp(self):
        lst = ["subf. 1, 6, 7",
               "cmp cr2, 1, 6, 7"]
        initial_regs = [0] * 32
        initial_regs[6] = 0x10
        initial_regs[7] = 0x05
        e = ExpectedState(pc=8)
        e.intregs[6] = 0x10
        e.intregs[7] = 0x5
        e.intregs[1] = 0xfffffffffffffff5
        e.crregs[0] = 0x8
        e.crregs[2] = 0x4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmp2(self):
        lst = ["cmp cr2, 0, 2, 3"]
        initial_regs = [0] * 32
        initial_regs[2] = 0xffffffffaaaaaaaa
        initial_regs[3] = 0x00000000aaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[2] = 0xffffffffaaaaaaaa
        e.intregs[3] = 0xaaaaaaaa
        e.crregs[2] = 0x2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = ["cmp cr2, 0, 4, 5"]
        initial_regs = [0] * 32
        initial_regs[4] = 0x00000000aaaaaaaa
        initial_regs[5] = 0xffffffffaaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[4] = 0xaaaaaaaa
        e.intregs[5] = 0xffffffffaaaaaaaa
        e.crregs[2] = 0x2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmp3(self):
        lst = ["cmp cr2, 1, 2, 3"]
        initial_regs = [0] * 32
        initial_regs[2] = 0xffffffffaaaaaaaa
        initial_regs[3] = 0x00000000aaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[2] = 0xffffffffaaaaaaaa
        e.intregs[3] = 0xaaaaaaaa
        e.crregs[2] = 0x8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = ["cmp cr2, 1, 4, 5"]
        initial_regs = [0] * 32
        initial_regs[4] = 0x00000000aaaaaaaa
        initial_regs[5] = 0xffffffffaaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[4] = 0xaaaaaaaa
        e.intregs[5] = 0xffffffffaaaaaaaa
        e.crregs[2] = 0x4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmpl_microwatt_0(self):
        """microwatt 1.bin:
           115b8:   40 50 d1 7c     .long 0x7cd15040 # cmpl 6, 0, 17, 10
            register_file.vhdl: Reading GPR 11 000000000001C026
            register_file.vhdl: Reading GPR 0A FEDF3FFF0001C025
            cr_file.vhdl: Reading CR 35055050
            cr_file.vhdl: Writing 35055058 to CR mask 01 35055058
        """

        lst = ["cmpl 6, 0, 17, 10"]
        initial_regs = [0] * 32
        initial_regs[0x11] = 0x1c026
        initial_regs[0xa] = 0xFEDF3FFF0001C025
        XER = 0xe00c0000
        CR = 0x35055050

        e = ExpectedState(pc=4)
        e.intregs[10] = 0xfedf3fff0001c025
        e.intregs[17] = 0x1c026
        e.crregs[0] = 0x3
        e.crregs[1] = 0x5
        e.crregs[3] = 0x5
        e.crregs[4] = 0x5
        e.crregs[6] = 0x5
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_sprs={'XER': XER},
                      initial_cr=CR, expected=e)

    def case_cmpl_microwatt_0_disasm(self):
        """microwatt 1.bin: disassembled version
           115b8:   40 50 d1 7c     .long 0x7cd15040 # cmpl 6, 0, 17, 10
            register_file.vhdl: Reading GPR 11 000000000001C026
            register_file.vhdl: Reading GPR 0A FEDF3FFF0001C025
            cr_file.vhdl: Reading CR 35055050
            cr_file.vhdl: Writing 35055058 to CR mask 01 35055058
        """

        dis = ["cmpl 6, 0, 17, 10"]
        lst = bytes([0x40, 0x50, 0xd1, 0x7c])  # 0x7cd15040
        initial_regs = [0] * 32
        initial_regs[0x11] = 0x1c026
        initial_regs[0xa] = 0xFEDF3FFF0001C025
        XER = 0xe00c0000
        CR = 0x35055050

        e = ExpectedState(pc=4)
        e.intregs[10] = 0xfedf3fff0001c025
        e.intregs[17] = 0x1c026
        e.crregs[0] = 0x3
        e.crregs[1] = 0x5
        e.crregs[3] = 0x5
        e.crregs[4] = 0x5
        e.crregs[6] = 0x5
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_regs,
                      initial_sprs={'XER': XER},
                      initial_cr=CR, expected=e)

    def case_cmplw_microwatt_1(self):
        """microwatt 1.bin:
           10d94:   40 20 96 7c     cmplw   cr1,r22,r4
            gpr: 00000000ffff6dc1 <- r4
            gpr: 0000000000000000 <- r22
        """

        lst = ["cmpl 1, 0, 22, 4"]
        initial_regs = [0] * 32
        initial_regs[4] = 0xffff6dc1
        initial_regs[22] = 0
        XER = 0xe00c0000
        CR = 0x50759999

        e = ExpectedState(pc=4)
        e.intregs[4] = 0xffff6dc1
        e.crregs[0] = 0x5
        e.crregs[1] = 0x9
        e.crregs[2] = 0x7
        e.crregs[3] = 0x5
        e.crregs[4] = 0x9
        e.crregs[5] = 0x9
        e.crregs[6] = 0x9
        e.crregs[7] = 0x9
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_sprs={'XER': XER},
                      initial_cr=CR, expected=e)

    def case_cmpli_microwatt(self):
        """microwatt 1.bin: cmpli
           123ac:   9c 79 8d 2a     cmpli   cr5,0,r13,31132
            gpr: 00000000301fc7a7 <- r13
            cr : 0000000090215393
            xer: so 1 ca 0 32 0 ov 0 32 0

        """

        lst = ["cmpli 5, 0, 13, 31132"]
        initial_regs = [0] * 32
        initial_regs[13] = 0x301fc7a7
        XER = 0xe00c0000
        CR = 0x90215393

        e = ExpectedState(pc=4)
        e.intregs[13] = 0x301fc7a7
        e.crregs[0] = 0x9
        e.crregs[2] = 0x2
        e.crregs[3] = 0x1
        e.crregs[4] = 0x5
        e.crregs[5] = 0x5
        e.crregs[6] = 0x9
        e.crregs[7] = 0x3
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_sprs={'XER': XER},
                      initial_cr=CR, expected=e)

    def case_extsb(self):
        insns = ["extsb", "extsh", "extsw"]
        for i in range(10):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)

            e = ExpectedState(pc=4)
            e.intregs[1] = initial_regs[1]
            if choice == "extsb":
                e.intregs[3] = exts(initial_regs[1], 8) & ((1 << 64)-1)
            elif choice == "extsh":
                e.intregs[3] = exts(initial_regs[1], 16) & ((1 << 64)-1)
            else:
                e.intregs[3] = exts(initial_regs[1], 32) & ((1 << 64)-1)

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmpeqb(self):
        lst = ["cmpeqb cr1, 1, 2"]
        for i in range(20):
            initial_regs = [0] * 32
            initial_regs[1] = i
            initial_regs[2] = 0x0001030507090b0f

            e = ExpectedState(pc=4)
            e.intregs[1] = i
            e.intregs[2] = 0x1030507090b0f
            matlst = [0x00, 0x01, 0x03, 0x05, 0x07, 0x09, 0x0b, 0x0f]
            for j in matlst:
                if j == i:
                    e.crregs[1] = 0x4

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_pia_ca_ov_cases(self):
        wanted_outputs = 'ca', 'ca32', 'ov', 'ov32', 'so'
        # only test one variant of each instr --
        # the variant with Rc=1 OV=1 as much as possible
        wanted_instrs = {
            'addi', 'paddi', 'addis', 'addo.', 'addic.', 'subfo.', 'subfic',
            'addco.', 'subfco.', 'addeo.', 'subfeo.', 'addmeo.', 'subfmeo.',
            'addzeo.', 'subfzeo.', 'addex', 'nego.',
        }
        unary_inputs = {
            '0x0', '0x1', '0x2',
            '0xFFFFFFFFFFFFFFFF', '0xFFFFFFFFFFFFFFFE',
            '0x7FFFFFFFFFFFFFFE', '0x7FFFFFFFFFFFFFFF',
            '0x8000000000000000', '0x8000000000000001',
            '0x123456787FFFFFFE', '0x123456787FFFFFFF',
            '0x1234567880000000', '0x1234567880000001',
        }
        imm_inputs = {
            '0x0', '0x1', '0x2',
            '0xFFFFFFFFFFFFFFFF', '0xFFFFFFFFFFFFFFFE',
            '0xFFFFFFFFFFFF8000', '0xFFFFFFFFFFFF8001',
            '0x7FFE', '0x7FFF', '0x8000', '0x8001',
        }
        binary_inputs32 = {
            '0x0', '0x1', '0x2',
            '0x12345678FFFFFFFF', '0x12345678FFFFFFFE',
            '0x123456787FFFFFFE', '0x123456787FFFFFFF',
            '0x1234567880000000', '0x1234567880000001',
        }
        binary_inputs64 = {
            '0x0', '0x1', '0x2',
            '0xFFFFFFFFFFFFFFFF', '0xFFFFFFFFFFFFFFFE',
            '0x7FFFFFFFFFFFFFFE', '0x7FFFFFFFFFFFFFFF',
            '0x8000000000000000', '0x8000000000000001',
        }

        def matches(case, **kwargs):
            for k, v in kwargs.items():
                if case[k] not in v:
                    return False
            return True

        programs = {}

        for case in read_pia_output():
            instr = case['instr']
            if instr not in wanted_instrs:
                continue
            if not any(i in case['native_outputs'] for i in wanted_outputs):
                continue
            if case.get('so') == True:
                continue
            if case.get('ov32') == True:
                continue
            if case.get('ca32') == True:
                continue
            initial_regs = [0] * 32
            initial_sprs = {}
            xer = SelectableInt(0, 64)
            xer[XER_bits['CA']] = case.get('ca', False)
            xer[XER_bits['OV']] = case.get('ov', False)
            initial_sprs[special_sprs['XER']] = xer
            e = ExpectedState(pc=4)
            e.intregs[3] = int(case['native_outputs']['rt'], 0)
            ca_out = case['native_outputs'].get('ca', False)
            ca32_out = case['native_outputs'].get('ca32', False)
            ov_out = case['native_outputs'].get('ov', False)
            ov32_out = case['native_outputs'].get('ov32', False)
            e.ca = ca_out | (ca32_out << 1)
            e.ov = ov_out | (ov32_out << 1)
            e.so = int(case['native_outputs'].get('so', False))
            if 'rb' in case:  # binary op
                pass32 = matches(case, ra=binary_inputs32, rb=binary_inputs32)
                pass64 = matches(case, ra=binary_inputs64, rb=binary_inputs64)
                if not pass32 and not pass64:
                    continue
                asm = f'{instr} 3, 4, 5'
                if instr == 'addex':
                    asm += ', 0'
                e.intregs[4] = initial_regs[4] = int(case['ra'], 0)
                e.intregs[5] = initial_regs[5] = int(case['rb'], 0)
            elif 'immediate' in case:
                pass32 = matches(case, ra=binary_inputs32,
                                 immediate=imm_inputs)
                pass64 = matches(case, ra=binary_inputs64,
                                 immediate=imm_inputs)
                if not pass32 and not pass64:
                    continue
                immediate = int(case['immediate'], 16)
                if immediate >> 63:
                    immediate -= 1 << 64
                asm = f'{instr} 3, 4, {immediate}'
                e.intregs[4] = initial_regs[4] = int(case['ra'], 0)
            else:  # unary op
                if not matches(case, ra=unary_inputs):
                    continue
                asm = f'{instr} 3, 4'
                e.intregs[4] = initial_regs[4] = int(case['ra'], 0)
            if 'cr0' in case['native_outputs']:
                cr0 = case['native_outputs']['cr0']
                v = cr0['lt'] << 3
                v |= cr0['gt'] << 2
                v |= cr0['eq'] << 1
                v |= cr0['so']
                e.crregs[0] = v
            with self.subTest(case=repr(case)):
                if asm not in programs:
                    programs[asm] = Program([asm], bigendian)
                self.add_case(programs[asm], initial_regs,
                              initial_sprs=initial_sprs, expected=e)
