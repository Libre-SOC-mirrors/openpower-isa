from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.insndb.asm import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.fpscr import FPSCRState
from openpower.consts import MSR
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
            lst = [f"cffpro. 3,0,{CVM},{IT}"]
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
                e.pc = 0x700
                e.sprs['SRR0'] = 0  # insn is at address 0
                e.sprs['SRR1'] = e.msr | (1 << (63 - 43))
                e.msr = 0x9000000000000001
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

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def _ctfpr_fpscr(RN, set_XX, FR, FPRF, fpscr_unmodified):
        """ cached FPSCR computation for ctfpr_one since that part is slow """
        initial_fpscr = FPSCRState()
        initial_fpscr.RN = RN
        fpscr = FPSCRState(initial_fpscr)
        if set_XX:
            fpscr.XX = 1
            fpscr.FX = 1
            fpscr.FI = 1
            fpscr.FR = FR
        fpscr.FPRF = FPRF
        if fpscr_unmodified:
            fpscr = FPSCRState(initial_fpscr)
        return initial_fpscr, fpscr

    def ctfpr_one(self, inp, bfp32, IT, Rc, RN):
        if (dict(inp=hex(inp), bfp32=bfp32, IT=IT, Rc=Rc, RN=RN) !=
                {'inp': '0x80001000', 'bfp32': True, 'IT': 3, 'Rc': True, 'RN': 0}):
            return  # FIXME: just for debugging
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
            prev_is_closer = 2 * inp_value < prev_int + next_int
            if RN == 0:
                # round to nearest
                use_prev = (halfway and prev_fp_is_even) or prev_is_closer
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
        set_XX = FR = False
        if expected_fp != inp_value:
            set_XX = True
            FR = abs(expected_fp) > abs(inp_value)
        if expected_fp < 0:
            FPRF = "- Normal Number"
        elif expected_fp > 0:
            FPRF = "+ Normal Number"
        else:
            # integer conversion never gives -0.0
            FPRF = "+ Zero"

        # defined to not modify FPSCR since the conversion is always exact
        fpscr_unmodified = inp_width == 32 and not bfp32

        initial_fpscr, fpscr = self._ctfpr_fpscr(
            RN=RN, set_XX=set_XX, FR=FR, FPRF=FPRF,
            fpscr_unmodified=fpscr_unmodified)
        if Rc:
            cr1 = int(fpscr.FX) << 3
            cr1 |= int(fpscr.FEX) << 2
            cr1 |= int(fpscr.VX) << 1
            cr1 |= int(fpscr.OX)
        else:
            cr1 = 0
        with self.subTest(
            inp=hex(inp), bfp32=bfp32, IT=IT, Rc=Rc, RN=RN,
            expected_fp=expected_fp.hex(), expected_bits=hex(expected_bits),
            XX=fpscr.XX, FR=fpscr.FR, FPRF=bin(int(fpscr.FPRF)), CR1=bin(cr1),
        ):
            s = "s" if bfp32 else ""
            rc_str = "." if Rc else ""
            lst = [f"ctfpr{s}{rc_str} 0,3,{IT}"]
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

    def ctfpr(self, inp):
        for bfp32 in (False, True):
            for IT in range(4):
                for Rc in (False, True):
                    for RN in range(4):
                        self.ctfpr_one(inp, bfp32, IT, Rc, RN)

    def case_ctfpr(self):
        inp_values = {0}
        for sh in (0, 22, 23, 24, 31, 52, 53, 54, 63):
            for offset in range(-2, 3):
                for offset_sh in range(64):
                    v = 1 << sh
                    v += offset << offset_sh
                    v %= 2 ** 64
                    inp_values.add(v)
        for i in sorted(inp_values):
            self.ctfpr(i)

    def fmv(self, gpr_bits, bfp32, Rc):
        if bfp32:
            gpr_bits %= 2 ** 32
            if gpr_bits & 0x7f80_0000 == 0x7f80_0000:  # inf or nan
                fpr_bits = (gpr_bits & 0x8000_0000) << 32
                fpr_bits |= 0x7ff0_0000_0000_0000
                fpr_bits |= (gpr_bits & 0x7f_ffff) << 29
            else:
                fpr_bits = bitcast_fp_to_int(bitcast_int_to_fp(
                    gpr_bits, bfp32=True), bfp32=False)
        else:
            gpr_bits %= 2 ** 64
            fpr_bits = gpr_bits
        with self.subTest(gpr_bits=hex(gpr_bits), fpr_bits=hex(fpr_bits),
                          bfp32=bfp32, Rc=Rc):
            s = "s" if bfp32 else ""
            rc_str = "." if Rc else ""
            tg_p = _cached_program(f"mffpr{s}{rc_str} 3, 0")
            # mtfpr[s]. doesn't exist since Rc=1 is basically useless due to
            # fmv* not changing any FPSCR bits
            fg_p = _cached_program(f"mtfpr{s} 0, 3")
            tg_gprs = [0] * 32
            fg_gprs = [0] * 32
            tg_fprs = [0] * 32
            fg_fprs = [0] * 32
            tg_fprs[0] = fpr_bits
            fg_gprs[3] = gpr_bits
            tg_e = ExpectedState(pc=4, int_regs=tg_gprs, fp_regs=tg_fprs)
            fg_e = ExpectedState(pc=4, int_regs=fg_gprs, fp_regs=fg_fprs)
            tg_lt = bool(gpr_bits & (1 << 63))
            tg_gt = not tg_lt and gpr_bits != 0
            tg_eq = gpr_bits == 0
            if Rc:
                tg_e.crregs[0] = (
                    (tg_lt << 3) | (tg_gt << 2) | (tg_eq << 1) | tg_e.so)
            fg_e.fpregs[0] = fpr_bits
            tg_e.intregs[3] = gpr_bits
            self.add_case(fg_p, fg_gprs, fpregs=fg_fprs, expected=fg_e)
            self.add_case(tg_p, tg_gprs, fpregs=tg_fprs, expected=tg_e)

    def case_fmv(self):
        inp_values = {0}
        for sh in (0, 22, 23, 24, 31, 52, 53, 54, 63):
            for offset in range(-2, 3):
                for offset_sh in range(64):
                    v = 1 << sh
                    v += offset << offset_sh
                    v %= 2 ** 64
                    inp_values.add(v)
        for i in sorted(inp_values):
            for bfp32 in (False, True):
                for Rc in (False, True):
                    self.fmv(i, bfp32, Rc)


class SVP64FMvFCvtCases(TestAccumulatorBase):
    def case_sv_mtfpr(self):
        lst = list(SVP64Asm(["sv.mtfpr *3, *3"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        gprs[3] = 0xa2f77210b3759b72  # -3.0762581375623643e-140
        gprs[4] = 0xbb6c6f98d5f1165  # 3.106739523264776e-252
        gprs[5] = 0x4d94f81cb94383fe  # 5.520783182773991e+65
        gprs[6] = 0xbabd64f913a550c0  # -9.497851164560019e-26
        gprs[7] = 0x946ee3df50c8b3c9  # -2.9362479271656598e-210
        gprs[8] = 0xc04c4950eeac2bf8  # -56.57278235823463
        gprs[9] = 0x94aadc76d0641448  # -4.0852462310367517e-209
        gprs[10] = 0x183ff479cd3c162a  # 7.0039231684450285e-192
        gprs[11] = 0xa07f1f2626c68dad  # -3.7138570072369393e-152
        gprs[12] = 0xc8f3eeb4b229348f  # -2.778177315415125e+43
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xa2f77210b3759b72  # -3.0762581375623643e-140
        e.fpregs[4] = 0xbb6c6f98d5f1165  # 3.106739523264776e-252
        e.fpregs[5] = 0x4d94f81cb94383fe  # 5.520783182773991e+65
        e.fpregs[6] = 0xbabd64f913a550c0  # -9.497851164560019e-26
        e.fpregs[7] = 0x946ee3df50c8b3c9  # -2.9362479271656598e-210
        e.fpregs[8] = 0xc04c4950eeac2bf8  # -56.57278235823463
        e.fpregs[9] = 0x94aadc76d0641448  # -4.0852462310367517e-209
        e.fpregs[10] = 0x183ff479cd3c162a  # 7.0039231684450285e-192
        e.fpregs[11] = 0xa07f1f2626c68dad  # -3.7138570072369393e-152
        e.fpregs[12] = 0xc8f3eeb4b229348f  # -2.778177315415125e+43
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_mffpr(self):
        lst = list(SVP64Asm(["sv.mffpr *3, *3"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        fprs[3] = 0x4a467f81df2c49c2  # 6.576194817283066e+49
        fprs[4] = 0xad9e2a873ed027e4  # -5.923533316236948e-89
        fprs[5] = 0xd5e965376a6c56b6  # -7.28053270057725e+105
        fprs[6] = 0xa58d0a3abb7d83e3  # -8.378916175016297e-128
        fprs[7] = 0x22a5d28a80cebc2  # 3.1493721884183893e-298
        fprs[8] = 0xcf0249c06893a97c  # -4.039032746538712e+72
        fprs[9] = 0x58bfa28e7438dce1  # 3.1909937185457982e+119
        fprs[10] = 0x8e4cb0a3d0022bc6  # -8.605260192425176e-240
        fprs[11] = 0xdff979f581d80ae5  # -2.134891937663687e+154
        fprs[12] = 0x4b45b570cd46b00b  # 4.158570794713441e+54
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.intregs[3] = 0x4a467f81df2c49c2  # 6.576194817283066e+49
        e.intregs[4] = 0xad9e2a873ed027e4  # -5.923533316236948e-89
        e.intregs[5] = 0xd5e965376a6c56b6  # -7.28053270057725e+105
        e.intregs[6] = 0xa58d0a3abb7d83e3  # -8.378916175016297e-128
        e.intregs[7] = 0x22a5d28a80cebc2  # 3.1493721884183893e-298
        e.intregs[8] = 0xcf0249c06893a97c  # -4.039032746538712e+72
        e.intregs[9] = 0x58bfa28e7438dce1  # 3.1909937185457982e+119
        e.intregs[10] = 0x8e4cb0a3d0022bc6  # -8.605260192425176e-240
        e.intregs[11] = 0xdff979f581d80ae5  # -2.134891937663687e+154
        e.intregs[12] = 0x4b45b570cd46b00b  # 4.158570794713441e+54
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_mtfprs(self):
        lst = list(SVP64Asm(["sv.mtfprs *3, *3"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        gprs[3] = 0x3388bdb0b2a9e320  # 0x3388bdb0 || -1.9777473880822072e-08
        gprs[4] = 0x8719509941543782  # 0x87195099 || 13.263551712036133
        gprs[5] = 0xaae3fe31cd28d549  # 0xaae3fe31 || -177034384.0
        gprs[6] = 0xcc89e2fc3834d36e  # 0xcc89e2fc || 4.3112253479193896e-05
        gprs[7] = 0xf2ae167344013f0  # 0xf2ae167 || 1.7888646652863827e-07
        gprs[8] = 0x6ea3c0a2a2f641ea  # 0x6ea3c0a2 || -6.674822283613962e-18
        gprs[9] = 0x4645527fdab1ee2f  # 0x4645527f || -2.5041478254329856e+16
        gprs[10] = 0x6aa03fc062dcbe1e  # 0x6aa03fc0 || 2.0359915416663045e+21
        gprs[11] = 0x489c6f48871f0169  # 0x489c6f48 || -1.196224492164401e-34
        gprs[12] = 0x6a92d0d40070bb60  # 0x6a92d0d4 || 1.0352793054431749e-38
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xbe553c6400000000  # -1.9777473880822072e-08
        e.fpregs[4] = 0x402a86f040000000  # 13.263551712036133
        e.fpregs[5] = 0xc1a51aa920000000  # -177034384.0
        e.fpregs[6] = 0x3f069a6dc0000000  # 4.3112253479193896e-05
        e.fpregs[7] = 0x3e88027e00000000  # 1.7888646652863827e-07
        e.fpregs[8] = 0xbc5ec83d40000000  # -6.674822283613962e-18
        e.fpregs[9] = 0xc3563dc5e0000000  # -2.5041478254329856e+16
        e.fpregs[10] = 0x445b97c3c0000000  # 2.0359915416663045e+21
        e.fpregs[11] = 0xb8e3e02d20000000  # -1.196224492164401e-34
        e.fpregs[12] = 0x380c2ed800000000  # 1.0352793054431749e-38
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_mffprs(self):
        lst = list(SVP64Asm(["sv.mffprs *3, *3"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        fprs[3] = 0xb848c47620000000  # f64 -1.4556985522680637e-37
        fprs[4] = 0x3d6e75f2a0000000  # f64 8.657461141210743e-13
        fprs[5] = 0x47b89e7a80000000  # f64 3.272433939766293e+37
        fprs[6] = 0xc02ef02820000000  # f64 -15.469056129455566
        fprs[7] = 0xc619b3dc00000000  # f64 -5.090919608237361e+29
        fprs[8] = 0xc794867ba0000000  # f64 -6.820708776907309e+36
        fprs[9] = 0x3f49827860000000  # f64 0.0007784927147440612
        fprs[10] = 0xbaf7107e40000000  # f64 -1.1924028985020467e-24
        fprs[11] = 0x43aa3150a0000000  # f64 9.43689183484969e+17
        fprs[12] = 0xbed08ab060000000  # f64 -3.943861429434037e-06
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.intregs[3] = 0x824623b1  # f32 -1.4556985522680637e-37
        e.intregs[4] = 0x2b73af95  # f32 8.657461141210743e-13
        e.intregs[5] = 0x7dc4f3d4  # f32 3.272433939766293e+37
        e.intregs[6] = 0xc1778141  # f32 -15.469056129455566
        e.intregs[7] = 0xf0cd9ee0  # f32 -5.090919608237361e+29
        e.intregs[8] = 0xfca433dd  # f32 -6.820708776907309e+36
        e.intregs[9] = 0x3a4c13c3  # f32 0.0007784927147440612
        e.intregs[10] = 0x97b883f2  # f32 -1.1924028985020467e-24
        e.intregs[11] = 0x5d518a85  # f32 9.43689183484969e+17
        e.intregs[12] = 0xb6845583  # f32 -3.943861429434037e-06
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_ctfpr(self):
        lst = list(SVP64Asm(["sv.ctfpr *3, *3, 0"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        gprs[3] = 0xa2f77210b3759b72  # 0xa2f77210 || -1284138126
        gprs[4] = 0xbb6c6f98d5f1165  # 0xbb6c6f9 || -1923149467
        gprs[5] = 0x4d94f81cb94383fe  # 0x4d94f81c || -1186757634
        gprs[6] = 0xbabd64f913a550c0  # 0xbabd64f9 || 329601216
        gprs[7] = 0x946ee3df50c8b3c9  # 0x946ee3df || 1355330505
        gprs[8] = 0xc04c4950eeac2bf8  # 0xc04c4950 || -290706440
        gprs[9] = 0x94aadc76d0641448  # 0x94aadc76 || -798747576
        gprs[10] = 0x183ff479cd3c162a  # 0x183ff479 || -851700182
        gprs[11] = 0xa07f1f2626c68dad  # 0xa07f1f26 || 650546605
        gprs[12] = 0xc8f3eeb4b229348f  # 0xc8f3eeb4 || -1305922417
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xc1d3229923800000  # f64 -1284138126.0
        e.fpregs[4] = 0xc1dca83ba6c00000  # f64 -1923149467.0
        e.fpregs[5] = 0xc1d1af1f00800000  # f64 -1186757634.0
        e.fpregs[6] = 0x41b3a550c0000000  # f64 329601216.0
        e.fpregs[7] = 0x41d4322cf2400000  # f64 1355330505.0
        e.fpregs[8] = 0xc1b153d408000000  # f64 -290706440.0
        e.fpregs[9] = 0xc1c7cdf5dc000000  # f64 -798747576.0
        e.fpregs[10] = 0xc1c961f4eb000000  # f64 -851700182.0
        e.fpregs[11] = 0x41c36346d6800000  # f64 650546605.0
        e.fpregs[12] = 0xc1d375b2dc400000  # f64 -1305922417.0
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_cffpr_js(self):
        lst = list(SVP64Asm(["sv.cffpr *3, *3, 5, 0"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        fprs[3] = 0xc11b409582aac6c2  # f64 -446501.37760458526
        fprs[4] = 0x40311164f59f97ba  # f64 17.067946769202287
        fprs[5] = 0x4179786c25161402  # f64 26707650.317890175
        fprs[6] = 0x77a2d30d30aedc37  # f64 1.9423512004394842e+268
        fprs[7] = 0xfcc691390ace2fbe  # f64 -1.1260170101142855e+293
        fprs[8] = 0xc145328877d66458  # f64 -2778384.9362302236
        fprs[9] = 0xc0e6c2048e0540f9  # f64 -46608.14233648958
        fprs[10] = 0xc1497c2a90a71511  # f64 -3340373.130098947
        fprs[11] = 0x2aaabda57b592051  # f64 3.731006400911987e-103
        fprs[12] = 0x40839fff57931a98  # f64 627.9996787540904
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.intregs[3] = 0xfffffffffff92fdb  # -446501
        e.intregs[4] = 0x11  # 17
        e.intregs[5] = 0x19786c2  # 26707650
        e.intregs[6] = 0
        e.intregs[7] = 0
        e.intregs[8] = 0xffffffffffd59af0  # -2778384
        e.intregs[9] = 0xffffffffffff49f0  # -46608
        e.intregs[10] = 0xffffffffffcd07ab  # -3340373
        e.intregs[11] = 0
        e.intregs[12] = 0x273  # 627
        e.fpscr = 0xa2020100
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_cffpr_sat(self):
        lst = list(SVP64Asm(["sv.cffpr *3, *3, 3, 0"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        fprs[3] = 0x41d6317a0c07f8c2  # f64 1489365040.124558
        fprs[4] = 0xc12fca9889a15f42  # f64 -1041740.2688092964
        fprs[5] = 0x2d7709c8cb530878  # f64 1.1309677587699661e-89
        fprs[6] = 0x4c653162f75415d0  # f64 1.0642407361512732e+60
        fprs[7] = 0xc106f58246849979  # f64 -188080.28443260098
        fprs[8] = 0x3fc86e10067c6b85  # f64 0.1908588439626692
        fprs[9] = 0xc04998b922650ff1  # f64 -51.19314985212976
        fprs[10] = 0xc0bf8d2648f0d00b  # f64 -8077.149550486366
        fprs[11] = 0xcac1f352558671c8  # f64 -1.3432140136107625e+52
        fprs[12] = 0xc1799318e724a0a8  # f64 -26816910.446442276
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.intregs[3] = 0x58c5e830  # 1489365040
        e.intregs[4] = 0xfffffffffff01ab4  # -1041740
        e.intregs[5] = 0
        e.intregs[6] = 0x7fffffff  # 2147483647
        e.intregs[7] = 0xfffffffffffd2150  # -188080
        e.intregs[8] = 0
        e.intregs[9] = 0xffffffffffffffcd  # -51
        e.intregs[10] = 0xffffffffffffe073  # -8077
        e.intregs[11] = 0xffffffff80000000  # -2147483648
        e.intregs[12] = 0xfffffffffe66ce72  # -26816910
        e.fpscr = 0xa2020100
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_ctfprs(self):
        lst = list(SVP64Asm(["sv.ctfprs *3, *3, 0"]))
        gprs = [0] * 32
        fprs = [0] * 32
        svstate = SVP64State()
        svstate.vl = 10
        svstate.maxvl = 10
        gprs[3] = 0x3388bdb0b2a9e320  # 0x3388bdb0 || -1297489120
        gprs[4] = 0x8719509941543782  # 0x87195099 || 1096038274
        gprs[5] = 0xaae3fe31cd28d549  # 0xaae3fe31 || -852961975
        gprs[6] = 0xcc89e2fc3834d36e  # 0xcc89e2fc || 942986094
        gprs[7] = 0xf2ae167344013f0  # 0xf2ae167 || 876614640
        gprs[8] = 0x6ea3c0a2a2f641ea  # 0x6ea3c0a2 || -1560919574
        gprs[9] = 0x4645527fdab1ee2f  # 0x4645527f || -625873361
        gprs[10] = 0x6aa03fc062dcbe1e  # 0x6aa03fc0 || 1658633758
        gprs[11] = 0x489c6f48871f0169  # 0x489c6f48 || -2028011159
        gprs[12] = 0x6a92d0d40070bb60  # 0x6a92d0d4 || 7388000
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xc1d3558740000000  # f64 -1297489152.0
        e.fpregs[4] = 0x41d0550de0000000  # f64 1096038272.0
        e.fpregs[5] = 0xc1c96b9560000000  # f64 -852961984.0
        e.fpregs[6] = 0x41cc1a69c0000000  # f64 942986112.0
        e.fpregs[7] = 0x41ca200a00000000  # f64 876614656.0
        e.fpregs[8] = 0xc1d7426f80000000  # f64 -1560919552.0
        e.fpregs[9] = 0xc1c2a708e0000000  # f64 -625873344.0
        e.fpregs[10] = 0x41d8b72f80000000  # f64 1658633728.0
        e.fpregs[11] = 0xc1de383fa0000000  # f64 -2028011136.0
        e.fpregs[12] = 0x415c2ed800000000  # f64 7388000.0
        e.fpscr = 0x82004000
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)
