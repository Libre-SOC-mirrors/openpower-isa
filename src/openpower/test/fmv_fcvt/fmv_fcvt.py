from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.fpscr import FPSCRState
import struct
import math
import functools


@functools.lru_cache()
def _cached_program(*instrs):
    return Program(list(SVP64Asm(list(instrs))), bigendian=False)


def bitcast_int_to_fp(bits, bfp32):
    if bfp32:
        return struct.unpack("<f", struct.pack("<L", bits))[0]
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


def bitcast_fp_to_int(fp, bfp32):
    if bfp32:
        return struct.unpack("<L", struct.pack("<f", fp))[0]
    return struct.unpack("<Q", struct.pack("<d", fp))[0]


def fp_bits_add(fp, amount, bfp32=False):
    """add `amount` to the IEEE 754 bits representing `fp`"""
    return bitcast_int_to_fp(amount + bitcast_fp_to_int(fp, bfp32), bfp32)


def round_even(v):
    """round v to the nearest integer, with ties rounding to the even integer
    """
    v = float(v)
    return int(v - math.remainder(v, 1.0))


def do_round(v, round_mode):
    if round_mode == 0:
        return round_even(v)
    if round_mode == 1:
        return math.trunc(v)
    if round_mode == 2:
        return math.ceil(v)
    if round_mode == 3:
        return math.floor(v)
    assert False, "invalid round_mode"


class FMvFCvtCases(TestAccumulatorBase):
    def toint_helper(self, *, inp, expected=None, test_title="", inp_bits=None,
                     signed=True, _32bit=True, CVM, RN, VE):
        if CVM & 1:
            round_mode = 1  # trunc
        else:
            round_mode = RN
        max_v = 2 ** 64 - 1
        if _32bit:
            max_v >>= 32
        min_v = 0
        if signed:
            max_v >>= 1
            min_v = ~max_v
        inp = float(inp)
        if inp_bits is None:
            inp_bits = struct.unpack("<Q", struct.pack("<d", inp))[0]
        if expected is None:
            if CVM >> 1 == 0:  # openpower semantics
                if math.isnan(inp):
                    expected = min_v
                elif inp > max_v:
                    expected = max_v
                elif inp < min_v:
                    expected = min_v
                else:
                    expected = do_round(inp, round_mode)
            elif CVM >> 1 == 1:  # saturating semantics
                if math.isnan(inp):
                    expected = 0
                elif inp > max_v:
                    expected = max_v
                elif inp < min_v:
                    expected = min_v
                else:
                    expected = do_round(inp, round_mode)
            elif CVM >> 1 == 2:  # js semantics
                if math.isfinite(inp):
                    expected = do_round(inp, round_mode)
                else:
                    expected = 0
                if _32bit:
                    expected %= 2 ** 32
                    if signed and expected >> 31:
                        expected -= 2 ** 32
        expected %= 2 ** 64
        IT = (not signed) + (not _32bit) * 2
        with self.subTest(inp=inp.hex(), inp_bits=hex(inp_bits),
                          test_title=test_title,
                          signed=signed, _32bit=_32bit, CVM=CVM, RN=RN, VE=VE):
            lst = [f"fcvttgo. 3,0,{CVM},{IT}"]
            gprs = [0] * 32
            fprs = [0] * 32
            fprs[0] = inp_bits
            gprs[3] = 0xabcdef9876543210
            initial_fpscr = FPSCRState()
            initial_fpscr.RN = RN
            initial_fpscr.VE = VE
            e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
            fpscr = FPSCRState(initial_fpscr)
            if math.isnan(inp) and (inp_bits & 2 ** 51) == 0:  # SNaN
                fpscr.VXSNAN = 1
                fpscr.FX = 1
            overflow = True
            if math.isfinite(inp):
                overflow = not (min_v <= do_round(inp, round_mode) <= max_v)
            if overflow:
                fpscr.VXCVI = 1
                fpscr.FX = 1
                e.so = 1
                e.ov = 0b11
            elif do_round(inp, round_mode) != inp:  # inexact
                fpscr.XX = 1
                fpscr.FX = 1
                fpscr.FI = 1
            fpscr.FPRF = 0  # undefined value we happen to pick
            if not overflow:
                fpscr.FR = abs(do_round(inp, round_mode)) > abs(inp)
            if overflow and fpscr.VE:
                # FIXME: #1087 proposes to change pseudocode of fcvt* to
                # always write output, this implements reading RT when output
                # isn't written, which is terrible
                # https://bugs.libre-soc.org/show_bug.cgi?id=1087#c21
                expected = e.intregs[3]
            lt = bool(expected & (1 << 63))
            gt = not lt and expected != 0
            eq = expected == 0
            e.crregs[0] = (lt << 3) | (gt << 2) | (eq << 1) | e.so
            e.intregs[3] = expected
            with self.subTest(expected_VXSNAN=fpscr.VXSNAN,
                              expected_VXCVI=fpscr.VXCVI,
                              expected_XX=fpscr.XX,
                              expected_FI=fpscr.FI,
                              expected=hex(expected)):
                e.fpscr = int(fpscr)
                self.add_case(
                    _cached_program(*lst), gprs, fpregs=fprs, expected=e,
                    initial_fpscr=int(initial_fpscr))

    def toint(self, inp, expected=None, test_title="", inp_bits=None,
              signed=True, _32bit=True):
        for CVM in range(6):
            for RN in range(1 if CVM & 1 else 4):
                for VE in range(2):
                    self.toint_helper(
                        inp=inp, expected=expected if CVM == 5 else None,
                        test_title=test_title, inp_bits=inp_bits,
                        signed=signed, _32bit=_32bit, CVM=CVM, RN=RN, VE=VE)

    def case_js_toint32(self):
        min_value = pow(2, -1074)
        # test cases from:
        # https://chromium.googlesource.com/v8/v8.git/+/d94dfc2b01f988566aa410ce871588cf23b1285d/test/mjsunit/toint32.js
        # Copyright 2008 the V8 project authors. All rights reserved.
        # Redistribution and use in source and binary forms, with or without
        # modification, are permitted provided that the following conditions are
        # met:
        #
        #     * Redistributions of source code must retain the above copyright
        #       notice, this list of conditions and the following disclaimer.
        #     * Redistributions in binary form must reproduce the above
        #       copyright notice, this list of conditions and the following
        #       disclaimer in the documentation and/or other materials provided
        #       with the distribution.
        #     * Neither the name of Google Inc. nor the names of its
        #       contributors may be used to endorse or promote products derived
        #       from this software without specific prior written permission.
        #
        # THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
        # "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
        # LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
        # A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
        # OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
        # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
        # LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
        # DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
        # THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
        # (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
        # OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

        self.toint(math.inf, 0, "Inf")
        self.toint(-math.inf, 0, "-Inf")
        self.toint(math.nan, 0, "NaN")
        self.toint(math.nan, 0, "SNaN", inp_bits=0x7ff0_0000_0000_0001)
        self.toint(0.0, 0, "zero")
        self.toint(-0.0, 0, "-zero")
        self.toint(min_value, 0)
        self.toint(-min_value, 0)
        self.toint(0.1, 0)
        self.toint(-0.1, 0)
        self.toint(1, 1, "one")
        self.toint(1.1, 1, "onepointone")
        self.toint(-1, -1, "-one")
        self.toint(0.6, 0, "truncate positive (0.6)")
        self.toint(1.6, 1, "truncate positive (1.6)")
        self.toint(-0.6, 0, "truncate negative (-0.6)")
        self.toint(-1.6, -1, "truncate negative (-1.6)")
        self.toint(2147483647, 2147483647)
        self.toint(2147483648, -2147483648)
        self.toint(2147483649, -2147483647)
        self.toint(4294967295, -1)
        self.toint(4294967296, 0)
        self.toint(4294967297, 1)
        self.toint(-2147483647, -2147483647)
        self.toint(-2147483648, -2147483648)
        self.toint(-2147483649, 2147483647)
        self.toint(-4294967295, 1)
        self.toint(-4294967296, 0)
        self.toint(-4294967297, -1)
        self.toint(2147483648.25, -2147483648)
        self.toint(2147483648.5, -2147483648)
        self.toint(2147483648.75, -2147483648)
        self.toint(4294967295.25, -1)
        self.toint(4294967295.5, -1)
        self.toint(4294967295.75, -1)
        self.toint(3000000000.25, -1294967296)
        self.toint(3000000000.5, -1294967296)
        self.toint(3000000000.75, -1294967296)
        self.toint(-2147483648.25, -2147483648)
        self.toint(-2147483648.5, -2147483648)
        self.toint(-2147483648.75, -2147483648)
        self.toint(-4294967295.25, 1)
        self.toint(-4294967295.5, 1)
        self.toint(-4294967295.75, 1)
        self.toint(-3000000000.25, 1294967296)
        self.toint(-3000000000.5, 1294967296)
        self.toint(-3000000000.75, 1294967296)
        base = pow(2, 64)
        self.toint(base + 0, 0)
        self.toint(base + 1117, 0)
        self.toint(base + 2234, 4096)
        self.toint(base + 3351, 4096)
        self.toint(base + 4468, 4096)
        self.toint(base + 5585, 4096)
        self.toint(base + 6702, 8192)
        self.toint(base + 7819, 8192)
        self.toint(base + 8936, 8192)
        self.toint(base + 10053, 8192)
        self.toint(base + 11170, 12288)
        self.toint(base + 12287, 12288)
        self.toint(base + 13404, 12288)
        self.toint(base + 14521, 16384)
        self.toint(base + 15638, 16384)
        self.toint(base + 16755, 16384)
        self.toint(base + 17872, 16384)
        self.toint(base + 18989, 20480)
        self.toint(base + 20106, 20480)
        self.toint(base + 21223, 20480)
        self.toint(base + 22340, 20480)
        self.toint(base + 23457, 24576)
        self.toint(base + 24574, 24576)
        self.toint(base + 25691, 24576)
        self.toint(base + 26808, 28672)
        self.toint(base + 27925, 28672)
        self.toint(base + 29042, 28672)
        self.toint(base + 30159, 28672)
        self.toint(base + 31276, 32768)
        # bignum is (2 ^ 53 - 1) * 2 ^ 31 - highest number with bit 31 set.
        bignum = pow(2, 84) - pow(2, 31)
        self.toint(bignum, -pow(2, 31))
        self.toint(-bignum, -pow(2, 31))
        self.toint(2 * bignum, 0)
        self.toint(-(2 * bignum), 0)
        self.toint(bignum - pow(2, 31), 0)
        self.toint(-(bignum - pow(2, 31)), 0)
        # max_fraction is largest number below 1.
        max_fraction = (1 - pow(2, -53))
        self.toint(max_fraction, 0)
        self.toint(-max_fraction, 0)

    def case_js_touint32(self):
        min_value = pow(2, -1074)
        # test cases from:
        # https://chromium.googlesource.com/v8/v8.git/+/d94dfc2b01f988566aa410ce871588cf23b1285d/test/mjsunit/touint32.js
        # with identical copyright notice as in case_js_toint32
        self.toint(0, 0, "0", signed=False)
        self.toint(-0, 0, "-0", signed=False)
        self.toint(math.inf, 0, "Infinity", signed=False)
        self.toint(-math.inf, 0, "-Infinity", signed=False)
        self.toint(math.nan, 0, "NaN", signed=False)
        self.toint(math.nan, 0, "SNaN", inp_bits=0x7ff0_0000_0000_0001,
                   signed=False)
        self.toint(min_value, 0, "MIN", signed=False)
        self.toint(-min_value, 0, "-MIN", signed=False)
        self.toint(0.1, 0, "0.1", signed=False)
        self.toint(-0.1, 0, "-0.1", signed=False)
        self.toint(1, 1, "1", signed=False)
        self.toint(1.1, 1, "1.1", signed=False)
        self.toint(-1, 4294967295, "-1", signed=False)
        self.toint(-1.1, 4294967295, "-1.1", signed=False)
        self.toint(2147483647, 2147483647, "2147483647", signed=False)
        self.toint(2147483648, 2147483648, "2147483648", signed=False)
        self.toint(2147483649, 2147483649, "2147483649", signed=False)
        self.toint(4294967295, 4294967295, "4294967295", signed=False)
        self.toint(4294967296, 0, "4294967296", signed=False)
        self.toint(4294967297, 1, "4294967297", signed=False)
        self.toint(-2147483647, 2147483649, "-2147483647", signed=False)
        self.toint(-2147483648, 2147483648, "-2147483648", signed=False)
        self.toint(-2147483649, 2147483647, "-2147483649", signed=False)
        self.toint(-4294967295, 1, "-4294967295", signed=False)
        self.toint(-4294967296, 0, "-4294967296", signed=False)
        self.toint(-4294967297, 4294967295, "-4294967297", signed=False)

    def case_js_toint64(self):
        # 64-bit equivalent of javascript's toint32
        min_value = pow(2, -1074)
        # test cases derived from:
        # https://chromium.googlesource.com/v8/v8.git/+/d94dfc2b01f988566aa410ce871588cf23b1285d/test/mjsunit/toint32.js
        # with identical copyright notice as in case_js_toint32

        self.toint(math.inf, 0, "Inf", _32bit=False)
        self.toint(-math.inf, 0, "-Inf", _32bit=False)
        self.toint(math.nan, 0, "NaN", _32bit=False)
        self.toint(math.nan, 0, "SNaN",
                   inp_bits=0x7ff0_0000_0000_0001, _32bit=False)
        self.toint(0.0, 0, "zero", _32bit=False)
        self.toint(-0.0, 0, "-zero", _32bit=False)
        self.toint(min_value, 0, _32bit=False)
        self.toint(-min_value, 0, _32bit=False)
        self.toint(0.1, 0, _32bit=False)
        self.toint(-0.1, 0, _32bit=False)
        self.toint(1, 1, "one", _32bit=False)
        self.toint(1.1, 1, "onepointone", _32bit=False)
        self.toint(-1, -1, "-one", _32bit=False)
        self.toint(0.6, 0, "truncate positive (0.6)", _32bit=False)
        self.toint(1.6, 1, "truncate positive (1.6)", _32bit=False)
        self.toint(-0.6, 0, "truncate negative (-0.6)", _32bit=False)
        self.toint(-1.6, -1, "truncate negative (-1.6)", _32bit=False)
        self.toint(fp_bits_add(2**63, -1), _32bit=False)
        self.toint(2**63, _32bit=False)
        self.toint(fp_bits_add(2**63, 1), _32bit=False)
        self.toint(fp_bits_add(2**64, -1), _32bit=False)
        self.toint(2**64, 0, _32bit=False)
        self.toint(fp_bits_add(2**64, 1), _32bit=False)
        self.toint(-fp_bits_add(2**63, -1), _32bit=False)
        self.toint(-(2**63), _32bit=False)
        self.toint(-fp_bits_add(2**63, 1), _32bit=False)
        self.toint(-fp_bits_add(2**64, -1), _32bit=False)
        self.toint(-(2**64), 0, _32bit=False)
        self.toint(-fp_bits_add(2**64, 1), _32bit=False)
        self.toint(2147483648.25, _32bit=False)
        self.toint(2147483648.5, _32bit=False)
        self.toint(2147483648.75, _32bit=False)
        self.toint(4294967295.25, _32bit=False)
        self.toint(4294967295.5, _32bit=False)
        self.toint(4294967295.75, _32bit=False)
        self.toint(3000000000.25, _32bit=False)
        self.toint(3000000000.5, _32bit=False)
        self.toint(3000000000.75, _32bit=False)
        self.toint(-2147483648.25, _32bit=False)
        self.toint(-2147483648.5, _32bit=False)
        self.toint(-2147483648.75, _32bit=False)
        self.toint(-4294967295.25, _32bit=False)
        self.toint(-4294967295.5, _32bit=False)
        self.toint(-4294967295.75, _32bit=False)
        self.toint(-3000000000.25, _32bit=False)
        self.toint(-3000000000.5, _32bit=False)
        self.toint(-3000000000.75, _32bit=False)
        base = pow(2, 64)
        self.toint(base + 0, _32bit=False)
        self.toint(base + 1117, _32bit=False)
        self.toint(base + 2234, _32bit=False)
        self.toint(base + 3351, _32bit=False)
        self.toint(base + 4468, _32bit=False)
        self.toint(base + 5585, _32bit=False)
        self.toint(base + 6702, _32bit=False)
        self.toint(base + 7819, _32bit=False)
        self.toint(base + 8936, _32bit=False)
        self.toint(base + 10053, _32bit=False)
        self.toint(base + 11170, _32bit=False)
        self.toint(base + 12287, _32bit=False)
        self.toint(base + 13404, _32bit=False)
        self.toint(base + 14521, _32bit=False)
        self.toint(base + 15638, _32bit=False)
        self.toint(base + 16755, _32bit=False)
        self.toint(base + 17872, _32bit=False)
        self.toint(base + 18989, _32bit=False)
        self.toint(base + 20106, _32bit=False)
        self.toint(base + 21223, _32bit=False)
        self.toint(base + 22340, _32bit=False)
        self.toint(base + 23457, _32bit=False)
        self.toint(base + 24574, _32bit=False)
        self.toint(base + 25691, _32bit=False)
        self.toint(base + 26808, _32bit=False)
        self.toint(base + 27925, _32bit=False)
        self.toint(base + 29042, _32bit=False)
        self.toint(base + 30159, _32bit=False)
        self.toint(base + 31276, _32bit=False)
        # bignum is (2 ^ 53 - 1) * 2 ^ 31 - highest number with bit 31 set.
        bignum = pow(2, 84) - pow(2, 31)
        self.toint(bignum, _32bit=False)
        self.toint(-bignum, _32bit=False)
        self.toint(2 * bignum, _32bit=False)
        self.toint(-(2 * bignum), _32bit=False)
        self.toint(bignum - pow(2, 31), _32bit=False)
        self.toint(-(bignum - pow(2, 31)), _32bit=False)
        # max_fraction is largest number below 1.
        max_fraction = (1 - pow(2, -53))
        self.toint(max_fraction, 0, _32bit=False)
        self.toint(-max_fraction, 0, _32bit=False)

    def case_js_touint64(self):
        # 64-bit equivalent of javascript's touint32
        min_value = pow(2, -1074)
        # test cases derived from:
        # https://chromium.googlesource.com/v8/v8.git/+/d94dfc2b01f988566aa410ce871588cf23b1285d/test/mjsunit/touint32.js
        # with identical copyright notice as in case_js_toint32
        self.toint(0, 0, "0", signed=False, _32bit=False)
        self.toint(-0, 0, "-0", signed=False, _32bit=False)
        self.toint(math.inf, 0, "Infinity", signed=False, _32bit=False)
        self.toint(-math.inf, 0, "-Infinity", signed=False, _32bit=False)
        self.toint(math.nan, 0, "NaN", signed=False, _32bit=False)
        self.toint(math.nan, 0, "SNaN", inp_bits=0x7ff0_0000_0000_0001,
                   signed=False, _32bit=False)
        self.toint(min_value, 0, "MIN", signed=False, _32bit=False)
        self.toint(-min_value, 0, "-MIN", signed=False, _32bit=False)
        self.toint(0.1, 0, "0.1", signed=False, _32bit=False)
        self.toint(-0.1, 0, "-0.1", signed=False, _32bit=False)
        self.toint(1, 1, "1", signed=False, _32bit=False)
        self.toint(1.1, 1, "1.1", signed=False, _32bit=False)
        self.toint(-1, 2**64 - 1, "-1", signed=False, _32bit=False)
        self.toint(-1.1, 2**64 - 1, "-1.1", signed=False, _32bit=False)
        self.toint(fp_bits_add(2**63, -1), signed=False, _32bit=False)
        self.toint(2**63, signed=False, _32bit=False)
        self.toint(fp_bits_add(2**63, 1), signed=False, _32bit=False)
        self.toint(fp_bits_add(2**64, -1), signed=False, _32bit=False)
        self.toint(2**64, 0, signed=False, _32bit=False)
        self.toint(fp_bits_add(2**64, 1), signed=False, _32bit=False)
        self.toint(-fp_bits_add(2**63, -1), signed=False, _32bit=False)
        self.toint(-(2**63), signed=False, _32bit=False)
        self.toint(-fp_bits_add(2**63, 1), signed=False, _32bit=False)
        self.toint(-fp_bits_add(2**64, -1), signed=False, _32bit=False)
        self.toint(-(2**64), 0, signed=False, _32bit=False)
        self.toint(-fp_bits_add(2**64, 1), signed=False, _32bit=False)

    @skip_case("FIXME: WIP")
    def fcvtfg_one(self, inp, bfp32, IT, Rc, RN):
        inp %= 2 ** 64
        inp_width = 64 if IT & 0b10 else 32
        inp_value = inp % 2 ** inp_width
        if IT & 0b1 == 0:
            # signed
            if inp_value >> (inp_width - 1):
                # negative
                inp_value -= 2 ** inp_width
        # cast to nearby f32/f64
        inp_fp = fp_bits_add(inp_value, 0, bfp32=bfp32)
        if inp_fp == inp_value:  # exact conversion -- no rounding necessary
            expected_fp = inp_fp
            expected_bits = bitcast_fp_to_int(expected_fp, bfp32=False)
        else:
            # get the fp value on either side of the exact value.
            # we need to get several values and select 2 because int -> fp
            # conversion in fp_bits_add could be off by a bit due to
            # rounding/double-rounding.
            # we can ignore weirdness around infinity because input values
            # can't get big enough to convert to infinity for bfp32/64.
            # we can ignore weirdness around zero because small integers
            # always convert exactly, and therefore don't reach this
            # `else` block.
            fp_values = sorted(
                fp_bits_add(inp_value, i, bfp32=bfp32) for i in range(-2, 3))
            while fp_values[-2] > inp_value:
                fp_values.pop()
            prev_fp = fp_values[-2]
            next_fp = fp_values[-1]
            # if fp values are big enough to not be exact, they are always
            # integers.
            prev_int = int(prev_fp)
            next_int = int(next_fp)
            prev_fp_is_even = bitcast_fp_to_int(prev_fp, bfp32=bfp32) & 1 == 0
            halfway = 2 * inp_value == prev_int + next_int
            next_is_closer = 2 * inp_value > prev_int + next_int
            if RN == 0:
                # round to nearest
                use_prev = (halfway and prev_fp_is_even) or not next_is_closer
            elif RN == 1:
                # trunc
                use_prev = abs(prev_int) < abs(next_int)
            elif RN == 2:
                # ceil
                use_prev = False
            else:
                assert RN == 3, "invalid RN"
                # floor
                use_prev = True
            if use_prev:
                expected_fp = prev_fp
            else:
                expected_fp = next_fp
        expected_bits = bitcast_fp_to_int(expected_fp, bfp32=False)
        initial_fpscr = FPSCRState()
        initial_fpscr.RN = RN
        fpscr = FPSCRState(initial_fpscr)
        if expected_fp != inp_value:
            fpscr.XX = 1
            fpscr.FX = 1
            fpscr.FI = 1
            fpscr.FR = abs(expected_fp) > abs(inp_value)
        if expected_fp < 0:
            fpscr.FPRF = "- Normal Number"
        elif expected_fp > 0:
            fpscr.FPRF = "+ Normal Number"
        else:
            # integer conversion never gives -0.0
            fpscr.FPRF = "+ Zero"
        if inp_width == 32 and not bfp32:
            # defined to not modify FPSCR since the conversion is always exact
            fpscr = FPSCRState(initial_fpscr)
        cr1 = int(fpscr.FX) << 3
        cr1 |= int(fpscr.FEX) << 2
        cr1 |= int(fpscr.VX) << 1
        cr1 |= int(fpscr.OX)
        with self.subTest(
            inp=hex(inp), bfp32=bfp32, IT=IT, Rc=Rc, RN=RN,
            expected_fp=expected_fp.hex(), expected_bits=hex(expected_bits),
            XX=fpscr.XX, FR=fpscr.FR, FPRF=bin(int(fpscr.FPRF)), CR1=bin(cr1),
        ):
            s = "s" if bfp32 else ""
            rc_str = "." if Rc else ""
            lst = [f"fcvtfg{s}{rc_str} 0,3,{IT}"]
            gprs = [0] * 32
            fprs = [0] * 32
            gprs[3] = inp
            e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
            e.crregs[1] = cr1
            e.fpregs[0] = expected_bits
            e.fpscr = int(fpscr)
            self.add_case(
                _cached_program(*lst), gprs, fpregs=fprs, expected=e,
                initial_fpscr=int(initial_fpscr))

    def fcvtfg(self, inp):
        for bfp32 in (False, True):
            for IT in range(4):
                for Rc in (False, True):
                    for RN in range(4):
                        self.fcvtfg_one(inp, bfp32, IT, Rc, RN)

    def case_fcvtfg(self):
        inp_values = {0}
        for sh in (0, 22, 23, 24, 31, 52, 53, 54, 63):
            for offset in range(-2, 3):
                for offset_sh in range(64):
                    v = 1 << sh
                    v += offset << offset_sh
                    v %= 2 ** 64
                    inp_values.add(v)
        for i in sorted(inp_values):
            self.fcvtfg(i)


class SVP64FMvFCvtCases(TestAccumulatorBase):
    @skip_case("FIXME: rewrite to fmv/fcvt tests")
    def case_sv_fmaxmag19(self):
        lst = list(SVP64Asm(["sv.fmaxmag19 *32,*64,*96"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        r = range(svstate.vl)
        for i, rev_i in zip(r, reversed(r)):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i))[0]
            fprs[96 + i] = struct.unpack("<Q", struct.pack("<d", rev_i))[0]
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x403f000000000000
        e.fpregs[33] = 0x403e000000000000
        e.fpregs[34] = 0x403d000000000000
        e.fpregs[35] = 0x403c000000000000
        e.fpregs[36] = 0x403b000000000000
        e.fpregs[37] = 0x403a000000000000
        e.fpregs[38] = 0x4039000000000000
        e.fpregs[39] = 0x4038000000000000
        e.fpregs[40] = 0x4037000000000000
        e.fpregs[41] = 0x4036000000000000
        e.fpregs[42] = 0x4035000000000000
        e.fpregs[43] = 0x4034000000000000
        e.fpregs[44] = 0x4033000000000000
        e.fpregs[45] = 0x4032000000000000
        e.fpregs[46] = 0x4031000000000000
        e.fpregs[47] = 0x4030000000000000
        e.fpregs[48] = 0x4030000000000000
        e.fpregs[49] = 0x4031000000000000
        e.fpregs[50] = 0x4032000000000000
        e.fpregs[51] = 0x4033000000000000
        e.fpregs[52] = 0x4034000000000000
        e.fpregs[53] = 0x4035000000000000
        e.fpregs[54] = 0x4036000000000000
        e.fpregs[55] = 0x4037000000000000
        e.fpregs[56] = 0x4038000000000000
        e.fpregs[57] = 0x4039000000000000
        e.fpregs[58] = 0x403a000000000000
        e.fpregs[59] = 0x403b000000000000
        e.fpregs[60] = 0x403c000000000000
        e.fpregs[61] = 0x403d000000000000
        e.fpregs[62] = 0x403e000000000000
        e.fpregs[63] = 0x403f000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)
