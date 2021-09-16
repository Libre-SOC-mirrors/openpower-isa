from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.power_decoder import create_pdecode
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.isa.test_runner import run_tst
from hashlib import sha256
from textwrap import dedent


def mock_pia():
    class InstructionInput:
        def __init__(self, ra=None, rb=None, rc=None, immediate=None, carry=None, overflow=None):
            self.ra = ra
            self.rb = rb
            self.rc = rc
            self.immediate = immediate
            self.carry = carry
            self.overflow = overflow

    class InstructionOutput:
        def __init__(self, rt=None, overflow=None, carry=None, cr0=None, cr1=None, cr2=None,
                     cr3=None, cr4=None, cr5=None, cr6=None, cr7=None):
            self.rt = rt
            self.overflow = overflow
            self.carry = carry
            self.cr0 = cr0
            self.cr1 = cr1
            self.cr2 = cr2
            self.cr3 = cr3
            self.cr4 = cr4
            self.cr5 = cr5
            self.cr6 = cr6
            self.cr7 = cr7

    def pack_bits(*bits):
        retval = 0
        for bit in bits:
            retval <<= 1
            if bit:
                retval |= 1
        return retval

    def unpack_bits(bits, count):
        return tuple(((bits >> i) & 1) != 0
                     for i in reversed(range(count)))

    def dpd_to_bcd(dpd):
        # expressions taken from PowerISA v2.07B section B.2 (page 697 (728))
        p, q, r, s, t, u, v, w, x, y = unpack_bits(dpd, 10)
        a = (not s and v and w) or (t and v and w and s) or (v and w and not x)
        b = (p and s and x and not t) or (p and not w) or (p and not v)
        c = (q and s and x and not t) or (q and not w) or (q and not v)
        d = r
        e = (v and not w and x) or (
            s and v and w and x) or (not t and v and x and w)
        f = (p and t and v and w and x and not s) or (
            s and not x and v) or (s and not v)
        g = (q and t and w and v and x and not s) or (
            t and not x and v) or (t and not v)
        h = u
        i = (t and v and w and x) or (
            s and v and w and x) or (v and not w and not x)
        j = (p and not s and not t and w and v) or (s and v and not w and x) or (
            p and w and not x and v) or (w and not v)
        k = (q and not s and not t and v and w) or (t and v and not w and x) or (
            q and v and w and not x) or (x and not v)
        m = y
        return pack_bits(a, b, c, d, e, f, g, h, i, j, k, m)

    def bcd_to_dpd(bcd):
        # expressions taken from PowerISA v2.07B section B.1 (page 697 (728))
        a, b, c, d, e, f, g, h, i, j, k, m = unpack_bits(bcd, 12)
        p = (f and a and i and not e) or (j and a and not i) or (b and not a)
        q = (g and a and i and not e) or (k and a and not i) or (c and not a)
        r = d
        s = (j and not a and e and not i) or (f and not i and not e) or (
            f and not a and not e) or (e and i)
        t = (k and not a and e and not i) or (g and not i and not e) or (
            g and not a and not e) or (a and i)
        u = h
        v = a or e or i
        w = (not e and j and not i) or (e and i) or a
        x = (not a and k and not i) or (a and i) or e
        y = m
        return pack_bits(p, q, r, s, t, u, v, w, x, y)

    class pia:
        @staticmethod
        def cdtbcd(inputs):
            ra = inputs.ra & ((1 << 64) - 1)
            rt = 0
            rt |= dpd_to_bcd(ra & 0x3FF)
            rt |= dpd_to_bcd((ra >> 10) & 0x3FF) << 12
            rt |= dpd_to_bcd((ra >> 32) & 0x3FF) << 32
            rt |= dpd_to_bcd((ra >> 42) & 0x3FF) << 44
            return InstructionOutput(rt=rt)

        @staticmethod
        def cbcdtd(inputs):
            ra = inputs.ra & ((1 << 64) - 1)
            rt = 0
            rt |= bcd_to_dpd(ra & 0xFFF)
            rt |= bcd_to_dpd((ra >> 12) & 0xFFF) << 10
            rt |= bcd_to_dpd((ra >> 32) & 0xFFF) << 32
            rt |= bcd_to_dpd((ra >> 44) & 0xFFF) << 42
            return InstructionOutput(rt=rt)

        @staticmethod
        def addg6s(inputs):
            ra = inputs.ra & ((1 << 64) - 1)
            rb = inputs.rb & ((1 << 64) - 1)
            sum = ra + rb
            need_sixes = ((~sum >> 4) ^ (ra >> 4) ^ (
                rb >> 4)) & 0x1111_1111_1111_1111
            rt = 6 * need_sixes
            return InstructionOutput(rt=rt)

    pia.InstructionInput = InstructionInput
    pia.InstructionOutput = InstructionOutput
    return pia


MOCK_PIA = True  # until pia is ported to python
if MOCK_PIA:
    pia = mock_pia()
else:
    import power_instruction_analyzer as pia


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
        exec(dedent(f"""
            def tst_{j}_{i}(self):
                self.tst_{j}({i})
            BCDFullTestCase.test_{j}_{i} = tst_{j}_{i}
        """))

if __name__ == "__main__":
    unittest.main()
