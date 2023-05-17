from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.fpscr import FPSCRState
import struct
import math


class FMvFCvtCases(TestAccumulatorBase):
    def js_toint(self, inp, expected, test_title="", inp_bits=None):
        inp = float(inp)
        if inp_bits is None:
            inp_bits = struct.unpack("<Q", struct.pack("<d", inp))[0]
        expected %= 2 ** 64
        with self.subTest(inp=inp.hex(), inp_bits=hex(inp_bits),
                          expected=hex(expected), test_title=test_title):
            lst = list(SVP64Asm(["fcvttg 3,0,5,0"]))
            gprs = [0] * 32
            fprs = [0] * 32
            fprs[0] = inp_bits
            e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
            e.intregs[3] = expected
            fpscr = FPSCRState()
            if math.isnan(inp) and (inp_bits & 2 ** 51) == 0:  # SNaN
                fpscr.VXSNAN = 1
                fpscr.FX = 1

            if not math.isfinite(inp) or not (
                    -0x8000_0000 <= math.trunc(inp) <= 0x7fff_ffff):
                fpscr.VXCVI = 1
                fpscr.FX = 1
            elif math.trunc(inp) != inp:  # inexact
                fpscr.XX = 1
                fpscr.FX = 1
                fpscr.FI = 1
            fpscr.FPRF = 0  # undefined value we happen to pick
            fpscr.FR = 0  # trunc never increments
            with self.subTest(expected_VXSNAN=fpscr.VXSNAN,
                              expected_VXCVI=fpscr.VXCVI,
                              expected_XX=fpscr.XX,
                              expected_FI=fpscr.FI):
                e.fpscr = int(fpscr)
                self.add_case(
                    Program(lst, False), gprs, fpregs=fprs, expected=e)

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

        self.js_toint(math.inf, 0, "Inf")
        self.js_toint(-math.inf, 0, "-Inf")
        self.js_toint(math.nan, 0, "NaN")
        self.js_toint(math.nan, 0, "SNaN", inp_bits=0x7ff0_0000_0000_0001)
        self.js_toint(0.0, 0, "zero")
        self.js_toint(-0.0, 0, "-zero")
        self.js_toint(min_value, 0)
        self.js_toint(-min_value, 0)
        self.js_toint(0.1, 0)
        self.js_toint(-0.1, 0)
        self.js_toint(1, 1, "one")
        self.js_toint(1.1, 1, "onepointone")
        self.js_toint(-1, -1, "-one")
        self.js_toint(0.6, 0, "truncate positive (0.6)")
        self.js_toint(1.6, 1, "truncate positive (1.6)")
        self.js_toint(-0.6, 0, "truncate negative (-0.6)")
        self.js_toint(-1.6, -1, "truncate negative (-1.6)")
        self.js_toint(2147483647, 2147483647)
        self.js_toint(2147483648, -2147483648)
        self.js_toint(2147483649, -2147483647)
        self.js_toint(4294967295, -1)
        self.js_toint(4294967296, 0)
        self.js_toint(4294967297, 1)
        self.js_toint(-2147483647, -2147483647)
        self.js_toint(-2147483648, -2147483648)
        self.js_toint(-2147483649, 2147483647)
        self.js_toint(-4294967295, 1)
        self.js_toint(-4294967296, 0)
        self.js_toint(-4294967297, -1)
        self.js_toint(2147483648.25, -2147483648)
        self.js_toint(2147483648.5, -2147483648)
        self.js_toint(2147483648.75, -2147483648)
        self.js_toint(4294967295.25, -1)
        self.js_toint(4294967295.5, -1)
        self.js_toint(4294967295.75, -1)
        self.js_toint(3000000000.25, -1294967296)
        self.js_toint(3000000000.5, -1294967296)
        self.js_toint(3000000000.75, -1294967296)
        self.js_toint(-2147483648.25, -2147483648)
        self.js_toint(-2147483648.5, -2147483648)
        self.js_toint(-2147483648.75, -2147483648)
        self.js_toint(-4294967295.25, 1)
        self.js_toint(-4294967295.5, 1)
        self.js_toint(-4294967295.75, 1)
        self.js_toint(-3000000000.25, 1294967296)
        self.js_toint(-3000000000.5, 1294967296)
        self.js_toint(-3000000000.75, 1294967296)
        base = pow(2, 64)
        self.js_toint(base + 0, 0)
        self.js_toint(base + 1117, 0)
        self.js_toint(base + 2234, 4096)
        self.js_toint(base + 3351, 4096)
        self.js_toint(base + 4468, 4096)
        self.js_toint(base + 5585, 4096)
        self.js_toint(base + 6702, 8192)
        self.js_toint(base + 7819, 8192)
        self.js_toint(base + 8936, 8192)
        self.js_toint(base + 10053, 8192)
        self.js_toint(base + 11170, 12288)
        self.js_toint(base + 12287, 12288)
        self.js_toint(base + 13404, 12288)
        self.js_toint(base + 14521, 16384)
        self.js_toint(base + 15638, 16384)
        self.js_toint(base + 16755, 16384)
        self.js_toint(base + 17872, 16384)
        self.js_toint(base + 18989, 20480)
        self.js_toint(base + 20106, 20480)
        self.js_toint(base + 21223, 20480)
        self.js_toint(base + 22340, 20480)
        self.js_toint(base + 23457, 24576)
        self.js_toint(base + 24574, 24576)
        self.js_toint(base + 25691, 24576)
        self.js_toint(base + 26808, 28672)
        self.js_toint(base + 27925, 28672)
        self.js_toint(base + 29042, 28672)
        self.js_toint(base + 30159, 28672)
        self.js_toint(base + 31276, 32768)
        # bignum is (2 ^ 53 - 1) * 2 ^ 31 - highest number with bit 31 set.
        bignum = pow(2, 84) - pow(2, 31)
        self.js_toint(bignum, -pow(2, 31))
        self.js_toint(-bignum, -pow(2, 31))
        self.js_toint(2 * bignum, 0)
        self.js_toint(-(2 * bignum), 0)
        self.js_toint(bignum - pow(2, 31), 0)
        self.js_toint(-(bignum - pow(2, 31)), 0)
        # max_fraction is largest number below 1.
        max_fraction = (1 - pow(2, -53))
        self.js_toint(max_fraction, 0)
        self.js_toint(-max_fraction, 0)


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
