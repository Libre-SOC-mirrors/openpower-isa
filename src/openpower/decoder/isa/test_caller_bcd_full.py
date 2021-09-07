from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.isa.test_runner import run_tst
import power_instruction_analyzer as pia
from hashlib import sha256


class BCDFullTestCase(FHDLTestCase):
    """test full arbitrary bit patterns, including invalid BCD (not
    supported by above reference code), against power-instruction-analyzer"""

    TEST_INDEX_COUNT = 8
    pdecode2 = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if BCDFullTestCase.pdecode2 is None:
            pdecode = create_pdecode()
            BCDFullTestCase.pdecode2 = PowerDecode2(pdecode)

    def hash(self, v):
        return int.from_bytes(
            sha256(bytes(str(v), encoding='ascii')).digest(),
            byteorder='little'
        )

    def addg6s_tst_cases(self):
        mask = (1 << 64) - 1
        for i in range(1024):
            v = self.hash(i)
            yield (v & mask, (v >> 64) & mask)

    def bcd_dpd_tst_cases(self):
        mask = (1 << 64) - 1
        limit = 1 << 12
        for i in range(limit):
            v = self.hash(i)
            v &= mask  # mask to 64-bits
            # replace lower bits with `i` to ensure we cover all patterns
            v &= ~(limit - 1)
            v |= i
            yield (v,)

    def run_cases(self, test_index, test_cases, instr, arg_in_count):
        pia_func = getattr(pia, instr.replace('.', '_'))
        lst = []
        for i in range(0, 32, arg_in_count):
            input_args = ', '.join(str(i + j)
                                   for j in range(arg_in_count))
            lst.append(f"{instr} {i}, {input_args}")
        with Program(lst, bigendian=False) as program:
            pass
        test_cases = list(test_cases)
        outer_start_index = test_index \
            * len(test_cases) // self.TEST_INDEX_COUNT
        outer_end_index = (test_index + 1) \
            * len(test_cases) // self.TEST_INDEX_COUNT
        for outer_index in range(outer_start_index, outer_end_index, len(lst)):
            inner_start_index = outer_index
            inner_end_index = min(outer_end_index,
                                  inner_start_index + len(lst))
            inner_range = range(inner_start_index, inner_end_index)
            initial_regs = [0 for i in range(32)]
            expected_outputs = initial_regs.copy()
            reg_num = 0
            for i in inner_range:
                for j in range(arg_in_count):
                    v = test_cases[i][j]
                    initial_regs[reg_num + j] = v
                    expected_outputs[reg_num + j] = v
                inputs = pia.InstructionInput(ra=test_cases[i][0])
                if 1 < arg_in_count:
                    inputs.rb = test_cases[i][1]
                outputs = pia_func(inputs)
                expected_outputs[reg_num] = outputs.rt
                reg_num += arg_in_count
            with self.subTest(inner_range=inner_range):
                sim = run_tst(program, initial_regs, pdecode2=self.pdecode2)
                for reg_num in range(32):
                    with self.subTest(reg_num=reg_num):
                        self.assertEqual(sim.gpr(reg_num),
                                         SelectableInt(expected_outputs[reg_num], 64))
        pass

    def tst_addg6s(self, test_index):
        self.run_cases(test_index, self.addg6s_tst_cases(), 'addg6s', 2)

    def tst_cdtbcd(self, test_index):
        self.run_cases(test_index, self.bcd_dpd_tst_cases(), 'cdtbcd', 1)

    def tst_cbcdtd(self, test_index):
        self.run_cases(test_index, self.bcd_dpd_tst_cases(), 'cbcdtd', 1)


for i in range(BCDFullTestCase.TEST_INDEX_COUNT):
    for j in 'addg6s', 'cdtbcd', 'cbcdtd':
        def tst_fn(self):
            getattr(self, f"tst_{j}")(i)
        setattr(BCDFullTestCase, f"test_{j}_{i}", tst_fn)

if __name__ == "__main__":
    unittest.main()
