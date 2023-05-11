import unittest
from openpower.decoder.fp_working_format import (
    BFPState, SelectableMSB0Fraction)
from fractions import Fraction
import math


class TestSelectableMSB0Fraction(unittest.TestCase):
    def test_repr(self):
        def check(v, pos, neg):
            v = Fraction(v)
            with self.subTest(v=f"{v.numerator:#x} / {v.denominator:#x}",
                              pos=pos, neg=neg):
                pos = f"SelectableMSB0Fraction({pos})"
                neg = f"SelectableMSB0Fraction({neg})"
                self.assertEqual(repr(SelectableMSB0Fraction(v)), pos)
                self.assertEqual(repr(SelectableMSB0Fraction(-v)), neg)
        check(0, "0x0.0", "0x0.0")
        check(1, "0x1.0", "0x...ffff.0 (-0x1)")
        check(0x2, "0x2.0", "0x...fffe.0 (-0x2)")
        check(0x4, "0x4.0", "0x...fffc.0 (-0x4)")
        check(0x8, "0x8.0", "0x...fff8.0 (-0x8)")
        check(0x10, "0x10.0", "0x...fff0.0 (-0x10)")
        check(0x100, "0x100.0", "0x...ff00.0 (-0x100)")
        check(0x1000, "0x1000.0", "0x...f000.0 (-0x1 * 2**12)")
        check(0x10000,
              "0x...0000.0 (0x1 * 2**16)", "0x...0000.0 (-0x1 * 2**16)")
        check(0x100000,
              "0x...0000.0 (0x1 * 2**20)", "0x...0000.0 (-0x1 * 2**20)")
        check(0x1000000,
              "0x...0000.0 (0x1 * 2**24)", "0x...0000.0 (-0x1 * 2**24)")
        check(Fraction(1, 1 << 1), "0x0.8", "0x...ffff.8 (-0x1 / 0x2)")
        check(Fraction(1, 1 << 2), "0x0.4", "0x...ffff.c (-0x1 / 0x4)")
        check(Fraction(1, 1 << 3), "0x0.2", "0x...ffff.e (-0x1 / 0x8)")
        check(Fraction(1, 1 << 4), "0x0.1", "0x...ffff.f (-0x1 / 0x10)")
        check(Fraction(1, 1 << 8), "0x0.01", "0x...ffff.ff (-0x1 / 0x100)")
        check(Fraction(1, 1 << 12), "0x0.001", "0x...ffff.fff (-0x1 * 2**-12)")
        check(Fraction(1, 1 << 16),
              "0x0.0001", "0x...ffff.ffff (-0x1 * 2**-16)")
        check(Fraction(1, 1 << 20),
              "0x0.0000_1", "0x...ffff.ffff_f (-0x1 * 2**-20)")
        check(Fraction(1, 1 << 24),
              "0x0.0000_01", "0x...ffff.ffff_ff (-0x1 * 2**-24)")
        check(Fraction(1, 1 << 28),
              "0x0.0000_001", "0x...ffff.ffff_fff (-0x1 * 2**-28)")
        check(Fraction(1, 1 << 32),
              "0x0.0000_0001", "0x...ffff.ffff_ffff (-0x1 * 2**-32)")
        check(Fraction(1, 1 << 36),
              "0x0.0000_0000_1", "0x...ffff.ffff_ffff_f (-0x1 * 2**-36)")
        check(Fraction(1, 1 << 40),
              "0x0.0000_0000_01", "0x...ffff.ffff_ffff_ff (-0x1 * 2**-40)")
        check(Fraction(1, 1 << 44),
              "0x0.0000_0000_001", "0x...ffff.ffff_ffff_fff (-0x1 * 2**-44)")
        check(Fraction(1, 1 << 48),
              "0x0.0000_0000_0001", "0x...ffff.ffff_ffff_ffff (-0x1 * 2**-48)")
        check(Fraction(1, 1 << 52),
              "0x0.0000_0000_0000_1",
              "0x...ffff.ffff_ffff_ffff_f (-0x1 * 2**-52)")
        check(Fraction(1, 1 << 56),
              "0x0.0000_0000_0000_01",
              "0x...ffff.ffff_ffff_ffff_ff (-0x1 * 2**-56)")
        check(Fraction(1, 1 << 60),
              "0x0.0000_0000_0000_001",
              "0x...ffff.ffff_ffff_ffff_fff (-0x1 * 2**-60)")
        check(Fraction(1, 1 << 64),
              "0x0.0000_0000_0000_0001",
              "0x...ffff.ffff_ffff_ffff_ffff (-0x1 * 2**-64)")
        check(Fraction(1, 1 << 68),
              "0x0.0000_0000_0000_0000_1",
              "0x...ffff.ffff_ffff_ffff_ffff_f (-0x1 * 2**-68)")
        check(Fraction(1, 1 << 72),
              "0x0.0000_0000_0000_0000_0... (0x1 * 2**-72)",
              "0x...ffff.ffff_ffff_ffff_ffff_f... (-0x1 * 2**-72)")
        check(Fraction(1, 1 << 76),
              "0x0.0000_0000_0000_0000_0... (0x1 * 2**-76)",
              "0x...ffff.ffff_ffff_ffff_ffff_f... (-0x1 * 2**-76)")
        check(Fraction(1, 3),
              "0x0.5555_5555_5555_5555_5... (0x1 / 0x3)",
              "0x...ffff.aaaa_aaaa_aaaa_aaaa_a... (-0x1 / 0x3)")
        check(Fraction(1, 5),
              "0x0.3333_3333_3333_3333_3... (0x1 / 0x5)",
              "0x...ffff.cccc_cccc_cccc_cccc_c... (-0x1 / 0x5)")
        check(Fraction(1, 7),
              "0x0.2492_4924_9249_2492_4... (0x1 / 0x7)",
              "0x...ffff.db6d_b6db_6db6_db6d_b... (-0x1 / 0x7)")
        check(Fraction(1234, 4567),
              "0x0.452b_c745_e653_bec0_b... (0x4d2 / 0x11d7)",
              "0x...ffff.bad4_38ba_19ac_413f_4... (-0x4d2 / 0x11d7)")
        check(Fraction(0x123456789abcdef, 0x1234567),
              "0x...0079.0000_3840_001a_9640_0... "
              "(0x123456789abcdef / 0x1234567)",
              "0x...ff86.ffff_c7bf_ffe5_69bf_f... "
              "(-0x123456789abcdef / 0x1234567)")
        # decent approximation to math.tau
        check(Fraction(312689, 49766),
              "0x6.487e_d511_4b5c_560c_d... (0x4c571 / 0xc266)",
              "0x...fff9.b781_2aee_b4a3_a9f3_2... (-0x4c571 / 0xc266)")
        check(Fraction(0xface0000, 0xffff),
              "0xface.face_face_face_face_f... (0x539a0000 / 0x5555)",
              "0x...0531.0531_0531_0531_0531_0... (-0x539a0000 / 0x5555)")

    def test_ops(self):
        inputs = [1, 4, 6, Fraction(1, 2), Fraction(1, 3), Fraction(2, 3)]
        inputs.extend([-i for i in inputs])
        inputs.append(0)
        for a in inputs:
            for b in inputs:
                with self.subTest(a=a, b=b):
                    af = SelectableMSB0Fraction(a)
                    bf = SelectableMSB0Fraction(b)
                    self.assertEqual(af.value, a)
                    self.assertEqual((+af).value, a)
                    self.assertEqual((-af).value, -a)
                    self.assertEqual(math.floor(af).value, math.floor(a))
                    self.assertEqual(math.ceil(af).value, math.ceil(a))
                    self.assertEqual(math.trunc(af).value, math.trunc(a))
                    self.assertEqual(round(af).value, round(a))
                    self.assertEqual((af + bf).value, a + b)
                    self.assertEqual((af - bf).value, a - b)
                    self.assertEqual((af * bf).value, a * b)
                    self.assertEqual(af == bf, a == b)
                    self.assertEqual(af != bf, a != b)
                    self.assertEqual(af < bf, a < b)
                    self.assertEqual(af <= bf, a <= b)
                    self.assertEqual(af > bf, a > b)
                    self.assertEqual(af >= bf, a >= b)
                    if b != 0:
                        self.assertEqual((af / bf).value, a / Fraction(b))
                        self.assertEqual((af // bf).value, a // b)
                        self.assertEqual((af % bf).value, a % b)
                    if isinstance(b, int):
                        if b >= 0:
                            pow2_b = Fraction(1 << b)
                        else:
                            pow2_b = Fraction(1, 1 << -b)
                        self.assertEqual((af << b).value, a * pow2_b)
                        self.assertEqual((af >> b).value, a / pow2_b)

    def slice_helper(self, v, start, length):
        f = SelectableMSB0Fraction(v)
        if length > 0:
            expected = v
            # expected is 0b...XX.XXXmybitsXXX... where mybits is what we want
            expected *= 1 << start
            # expected is 0b...XXm.ybitsXXX...
            expected *= 1 << (length - 1)
            # expected is 0b...XXmybits.XX...
            expected = math.floor(expected)
            # expected is 0b...XXmybits
            expected %= 1 << length
            # expected is 0bmybits
        else:
            expected = 0
        with self.subTest(expected=hex(expected), f=str(f)):
            self.assertEqual(hex(expected), hex(int(f[start:start+length])))
            if length == 1:
                self.assertEqual(hex(expected), hex(int(f[start])))
        for replace in (0x5555, 0xffff, 0xaaaa, 0):
            expected = v
            # expected is 0b...XX.XXXoldbitsYY...
            # where oldbits is what we want to replace with newbits
            if length > 0:
                expected *= 1 << start
                # expected is 0b...XXo.ldbitsYYY...
                expected *= 1 << (length - 1)
                # expected is 0b...XXoldbits.YY...
                fraction = expected - math.floor(expected)
                # fraction is 0b.YYY...
                expected = math.floor(expected)
                # expected is 0b...XXoldbits
                expected -= expected % (1 << length)
                # expected is 0b...XX0000000
                expected |= replace % (1 << length)
                # expected is 0b...XXnewbits
                expected += fraction
                # expected is 0b...XXnewbits.YY...
                expected /= 1 << (length - 1)
                # expected is 0b...XXn.ewbitsYYY...
                expected /= 1 << start
                # expected is 0b...XX.XXXnewbitsYY...
            expected = SelectableMSB0Fraction(expected)
            with self.subTest(expected=str(expected),
                              replace=hex(replace)):
                f = SelectableMSB0Fraction(v)
                f[start:start+length] = replace
                self.assertEqual(f, expected)
                if length == 1:
                    f = SelectableMSB0Fraction(v)
                    f[start] = replace
                    self.assertEqual(f, expected)

    def test_slice(self):
        for v in [Fraction(0xface0000, 0xffff), Fraction(0x1230000, 0xffff)]:
            for start in range(0, 17):
                for length in reversed(range(0, 17)):
                    with self.subTest(v=v, start=start, length=length):
                        self.slice_helper(v, start, length)


if __name__ == "__main__":
    unittest.main()
