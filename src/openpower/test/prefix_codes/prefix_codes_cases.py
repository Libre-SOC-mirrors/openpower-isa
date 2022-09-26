from openpower.test.common import TestAccumulatorBase
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program


def tree_code(code):
    # type: (str) -> int
    retval = 1
    for bit in code:
        assert bit in "01"
        retval = retval * 2 + int(bit)
    assert retval < 64, "code too long"
    return retval


def make_tree(*codes):
    # type: (*str) -> int
    retval = 0
    for code in sorted(codes, key=len):
        for i in range(len(code)):
            assert retval & (1 << tree_code(code[:i])) == 0, \
                f"conflicting code: {code} conflicts with {code[:i]}"
        retval |= 1 << tree_code(code)
    return retval


def reference_pcdec(supported_codes, input_bits, max_count):
    # type: (set[str], str, int) -> tuple[list[str], bool]
    assert input_bits.lstrip("01") == "", "input_bits must be binary bits"
    retval = []
    current_code = ""
    overflow = False
    for bit in input_bits:
        current_code += bit
        if len(current_code) > 6:
            overflow = True
            break
        if current_code in supported_codes:
            retval.append(current_code)
            current_code = ""
            if len(retval) >= max_count:
                break
    return retval, overflow


CODE_2 = "0"
CODE_7 = "11"
CODE_19 = "1001"
CODE_35 = "10101"
CODE_37 = "10111"
CODES = {CODE_2, CODE_7, CODE_19, CODE_35, CODE_37}


class PrefixCodesCases(TestAccumulatorBase):
    def check_pcdec(self, supported_codes, input_bits, src_loc_at=0):
        # type: (set[str], str, int) -> None
        original_input_bits = input_bits
        input_bits = input_bits.replace("_", "")
        assert input_bits.lstrip("01") == "", "input_bits must be binary bits"
        assert len(input_bits) < 128, "input_bits too long"
        decoded, expected_SO = reference_pcdec(
            supported_codes, input_bits, max_count=8)
        expected_EQ = len(decoded) == 0
        expected_RT = int.from_bytes(
            [int("1" + code, 2) for code in decoded], 'little')
        decoded_bits_len = len("".join(decoded))
        expected_ra_used = False
        RB_val = make_tree(*supported_codes)
        rev_input_bits = input_bits[::-1]
        RA_val = 0
        RA = 0
        expected_RS = None
        if len(input_bits) >= 64:
            RA_val = int(rev_input_bits[:64], 2)
            RA = 7
            rev_input_bits = rev_input_bits[64:]
            expected_ra_used = decoded_bits_len > len(rev_input_bits)
            if expected_ra_used:
                expected_RS = (RA_val + 2 ** 64) >> decoded_bits_len
        RC_val = int("1" + rev_input_bits, 2)
        if expected_RS is None:
            expected_RS = RC_val >> decoded_bits_len
        lst = list(SVP64Asm([f"pcdec. 4,{RA},6,5,0"]))
        gprs = [0] * 32
        gprs[6] = RB_val
        if RA:
            gprs[RA] = RA_val
        gprs[5] = RC_val
        e = ExpectedState(pc=4, int_regs=gprs)
        e.intregs[4] = expected_RT
        e.intregs[5] = expected_RS
        e.crregs[0] = expected_ra_used * 8 + expected_EQ * 2 + expected_SO
        with self.subTest(supported_codes=supported_codes,
                          input_bits=original_input_bits):
            self.add_case(Program(lst, False), gprs, expected=e,
                          src_loc_at=src_loc_at + 1)

    def case_pcdec_empty(self):
        self.check_pcdec({CODE_2}, "")

    def case_pcdec_only_one_code(self):
        self.check_pcdec({CODE_37}, CODE_37)

    def case_pcdec_short_seq(self):
        self.check_pcdec(CODES, "_".join([CODE_2, CODE_19, CODE_35]))

    def case_pcdec_medium_seq(self):
        self.check_pcdec(CODES, "0_11_1001_10101_10111_10111_10101_1001_11_0")

    def case_pcdec_long_seq(self):
        self.check_pcdec(CODES,
                         "0_11_1001_10101_10111_10111_10101_1001_11_0"
                         + CODE_37 * 6)

    def case_pcdec_invalid_code_at_start(self):
        self.check_pcdec(CODES, "_".join(["1000", CODE_35]))

    def case_pcdec_invalid_code_after_3(self):
        self.check_pcdec(CODES, "_".join(
            [CODE_2, CODE_19, CODE_35, "1000", CODE_35]))

    def case_pcdec_invalid_code_after_8(self):
        self.check_pcdec(CODES, "_".join(
            [CODE_2, CODE_19, *([CODE_35] * 6), "1000", CODE_35]))

    def case_pcdec_invalid_code_in_rb(self):
        self.check_pcdec(CODES, "_".join(
            [CODE_2, CODE_19, "1000", *([CODE_19] * 15)]))

    def case_pcdec_overlong_code(self):
        self.check_pcdec(CODES, "_".join([CODE_2, CODE_19, "10000000"]))
