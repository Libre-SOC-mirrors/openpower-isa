import functools
import itertools
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from typing import Iterable


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


CODE_2 = "0"
CODE_7 = "11"
CODE_19 = "1001"
CODE_35 = "10101"
CODE_37 = "10111"
CODES = {CODE_2, CODE_7, CODE_19, CODE_35, CODE_37}


@functools.lru_cache()
def _cached_program(*instrs):
    return Program(list(SVP64Asm(list(instrs))), bigendian=False)


def _code_sort_key(supported_code):
    # type: (str) -> tuple[int, str]
    return len(supported_code), supported_code


class PrefixCodesCases(TestAccumulatorBase):
    def check_pcdec(self, supported_codes, input_bits, mode, src_loc_at=0):
        # type: (Iterable[str], str, int, int) -> None
        supported_codes = sorted(supported_codes, key=_code_sort_key)
        assert len(supported_codes) <= 32
        original_input_bits = input_bits
        input_bits = input_bits.replace("_", "")
        assert input_bits.lstrip("01") == "", "input_bits must be binary bits"
        assert len(input_bits) < 128, "input_bits too long"
        found = False
        hit_end = False
        tree_index = 1
        compressed_index = 0
        used_bits = 0
        for bit_len in range(1, 7):
            cur_input_bits = input_bits[:bit_len]
            if bit_len > len(input_bits):
                hit_end = True
                compressed_index = 0
                for i, code in enumerate(supported_codes):
                    if _code_sort_key(code) < _code_sort_key(cur_input_bits):
                        compressed_index = i + 1
                    else:
                        break
                break
            tree_index *= 2
            if cur_input_bits[-1] == "1":
                tree_index += 1
            if bit_len < 6:
                try:
                    compressed_index = supported_codes.index(cur_input_bits)
                    found = True
                    used_bits = bit_len
                    break
                except ValueError:
                    pass
            else:
                compressed_index = tree_index - 64 + len(supported_codes)
                used_bits = bit_len
        if mode == 0:
            expected_RT = tree_index
            if not found:
                used_bits = 0
        elif mode == 1:
            expected_RT = tree_index
            if hit_end:
                used_bits = 0
        elif mode == 2:
            expected_RT = compressed_index
            if not found:
                used_bits = 0
                expected_RT = tree_index
        else:
            assert mode == 3
            expected_RT = compressed_index
            if hit_end:
                used_bits = 0
        expected_ra_used = False
        RB_val = make_tree(*supported_codes) | mode
        rev_input_bits = input_bits[::-1]
        RA_val = 0
        RA = 0
        expected_RS = None
        if len(input_bits) >= 64:
            RA_val = int(rev_input_bits[:64], 2)
            RA = 7
            rev_input_bits = rev_input_bits[64:]
            expected_ra_used = used_bits > len(rev_input_bits)
            if expected_ra_used:
                expected_RS = (RA_val + 2 ** 64) >> (used_bits
                                                     - len(rev_input_bits))
        RC_val = int("1" + rev_input_bits, 2)
        if expected_RS is None:
            expected_RS = RC_val >> used_bits
        lst = [f"pcdec. 4,{RA},6,5"]
        gprs = [0] * 32
        gprs[6] = RB_val
        if RA:
            gprs[RA] = RA_val
        gprs[5] = RC_val
        e = ExpectedState(pc=4, int_regs=gprs)
        e.intregs[4] = expected_RT
        e.intregs[5] = expected_RS
        e.crregs[0] = (expected_ra_used * 8 + (tree_index >= 64) * 4
                       + found * 2 + hit_end)
        with self.subTest(supported_codes=supported_codes,
                          input_bits=original_input_bits, mode=mode):
            self.add_case(_cached_program(*lst), gprs, expected=e,
                          src_loc_at=src_loc_at + 1)

    def case_pcdec_empty(self):
        for mode in range(4):
            self.check_pcdec({CODE_2}, "", mode)

    def case_pcdec_only_one_code(self):
        for mode in range(4):
            self.check_pcdec({CODE_37}, CODE_37, mode)

    def case_pcdec_short_seq(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join([CODE_2, CODE_19, CODE_35]), mode)

    def case_pcdec_medium_seq(self):
        for mode in range(4):
            self.check_pcdec(
                CODES, "0_11_1001_10101_10111_10111_10101_1001_11_0", mode)

    def case_pcdec_long_seq(self):
        for mode in range(4):
            self.check_pcdec(CODES,
                             "0_11_1001_10101_10111_10111_10101_1001_11_0"
                             + CODE_37 * 6, mode)

    def case_pcdec_invalid_code_at_start(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join(["1000", CODE_35]), mode)

    def case_pcdec_invalid_code_after_3(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join(
                [CODE_2, CODE_19, CODE_35, "1000", CODE_35]), mode)

    def case_pcdec_invalid_code_after_8(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join(
                [CODE_2, CODE_19, *([CODE_35] * 6), "1000", CODE_35]), mode)

    def case_pcdec_invalid_code_in_rb(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join(
                [CODE_2, CODE_19, "1000", *([CODE_19] * 15)]), mode)

    def case_pcdec_overlong_code(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join(
                [CODE_2, CODE_19, "10000000"]), mode)

    def case_pcdec_incomplete_code(self):
        for mode in range(4):
            self.check_pcdec(CODES, "_".join([CODE_19[:-1]]), mode)

    def case_rest(self):
        for mode in range(4):
            for repeat in range(8):
                for bits in itertools.product("01", repeat=repeat):
                    self.check_pcdec(CODES, "".join(bits), mode)
                    # 60 so we cover both less and more than 64 bits
                    self.check_pcdec(CODES, "".join(bits) + "0" * 60, mode)
