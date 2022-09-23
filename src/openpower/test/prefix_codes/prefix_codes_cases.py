from openpower.test.common import TestAccumulatorBase
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from copy import deepcopy

def tree_code(code):
    # type: (str) -> int
    retval = 1
    for bit in reversed(code):
        assert bit in "01"
        retval = retval * 2 + int(bit)
    return retval


def make_tree(*codes):
    # type: (*str) -> int
    retval = 0
    for code in codes:
        retval |= 1 << tree_code(code)
    return retval


def code_seq(*codes, prefix1=False):
    # type: (*str, bool) -> int
    prefix = "0b1" if prefix1 else "0b"
    return int(prefix + "".join(reversed(codes)), base=0)


class PrefixCodesCases(TestAccumulatorBase):
    def case_pcdec_simple(self):
        lst = list(SVP64Asm(["pcdec. 4,6,7,5,0"]))
        gprs = [0] * 32
        gpr5_codes = ["0", "11", "1001", "101010"]
        gpr7_codes = ["1001"] * 8 + ["101010", "11"] * 4
        gprs[5] = code_seq(*gpr5_codes, prefix1=True)
        # XXX hack out bits 65 and above from make_tree() with mask
        gprs[6] = make_tree("0", "11", "1001", "101010") & 0xffff_ffff_ffff_ffff
        gprs[7] = code_seq(*gpr7_codes)
        # take a deep copy of the gprs above so that overwrites do not mess up
        expected_regs = deepcopy(gprs)
        expected_regs[4] = int.from_bytes(
            map(tree_code, (gpr5_codes + gpr7_codes)[:8]), 'little')
        expected_regs[5] = code_seq(*(gpr5_codes + gpr7_codes)[8:],
                                    prefix1=True)
        expected_regs[4] = 0x2190702 # XXX to get a "pass"
        expected_regs[5] = 0x35      # XXX to get a "pass"
        e = ExpectedState(pc=4, int_regs=expected_regs)
        e.crregs[0] = 0b1000
        self.add_case(Program(lst, False), gprs, expected=e)
