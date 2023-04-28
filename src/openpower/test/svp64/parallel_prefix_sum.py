import itertools
import operator
from openpower.simulator.program import Program
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.test.common import TestAccumulatorBase, skip_case
from nmutil.prefix_sum import prefix_sum, prefix_sum_ops


class ParallelPrefixSumCases(TestAccumulatorBase):
    def case_prefix_sum(self):
        inp = 0x1, 0x2, 0x4, 0x8, 0x10, 0x20, 0x40, 0x80
        expected = prefix_sum(inp, fn=operator.add, work_efficient=True)
        assert expected == [0x1, 0x3, 0x7, 0xF, 0x1F, 0x3F, 0x7F, 0xFF]
        gprs = [0] * 32
        for i, v in enumerate(inp):
            gprs[i + 10] = v
        len_inp = len(inp)
        prog = Program(list(SVP64Asm([
            # setup SVSHAPE[01] and VL/MAXVL for prefix-sum
            f"svshape {len_inp}, 3, 1, 0x7, 0",
            # activate SVSHAPE0 (prefix-sum lhs) for RA
            # activate SVSHAPE1 (prefix-sum rhs) for RT and RB
            "svremap 0o13, 0, 1, 0, 1, 0, 0",
            "sv.add *10, *10, *10",
        ])), False)
        e = ExpectedState(pc=0x10, int_regs=gprs)
        for i, v in enumerate(expected):
            e.intregs[i + 10] = v
        self.add_case(prog, gprs, expected=e)

    def case_scan_sub(self):
        inp = list(range(8))
        expected = prefix_sum(inp, fn=operator.sub, work_efficient=True)
        assert expected == [0, -1, -3, 0, -4, 1, -5, 0]
        expected = [i % 2 ** 64 for i in expected]  # cast to u64
        gprs = [0] * 32
        for i, v in enumerate(inp):
            gprs[i + 10] = v
        len_inp = len(inp)
        prog = Program(list(SVP64Asm([
            # setup SVSHAPE[01] and VL/MAXVL for prefix-sum
            f"svshape {len_inp}, 3, 1, 0x7, 0",
            # note subf has RA/RB reversed from normal sub
            # activate SVSHAPE0 (prefix-sum lhs) for RB (not RA)
            # activate SVSHAPE1 (prefix-sum rhs) for RT and RA (not RB)
            "svremap 0o13, 1, 0, 0, 1, 0, 0",
            "sv.subf *10, *10, *10",
        ])), False)
        e = ExpectedState(pc=0x10, int_regs=gprs)
        for i, v in enumerate(expected):
            e.intregs[i + 10] = v
        self.add_case(prog, gprs, expected=e)
