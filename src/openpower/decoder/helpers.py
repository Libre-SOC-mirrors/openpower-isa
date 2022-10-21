import unittest
import struct
import sys
from openpower.decoder.selectable_int import (SelectableInt, onebit,
                                              selectconcat)
from nmutil.divmod import trunc_divs, trunc_rems
from operator import floordiv, mod
from openpower.decoder.selectable_int import selectltu as ltu
from openpower.decoder.selectable_int import selectgtu as gtu
from openpower.decoder.selectable_int import check_extsign

from openpower.util import log
import math

trunc_div = floordiv
trunc_rem = mod
DIVS = trunc_divs
MODS = trunc_rems

"""
Links:
* https://bugs.libre-soc.org/show_bug.cgi?id=324 - add trunc_div and trunc_rem
* https://bugs.libre-soc.org/show_bug.cgi?id=671#c38 - RANGE (and bugfixes)
"""


def RANGE(start, end):
    if start > end:
        # reverse direction
        # auto-subtract-one (sigh) due to python range
        return range(start, end-1, -1)
    # auto-add-one (sigh) due to python range
    return range(start, end+1)


def exts(value, bits):
    sign = 1 << (bits - 1)
    return (value & (sign - 1)) - (value & sign)


def EXTS(value):
    """ extends sign bit out from current MSB to all 256 bits
    """
    log("EXTS", value, type(value))
    assert isinstance(value, SelectableInt)
    return SelectableInt(exts(value.value, value.bits) & ((1 << 256)-1), 256)


def EXTS64(value):
    """ extends sign bit out from current MSB to 64 bits
    """
    assert isinstance(value, SelectableInt)
    return SelectableInt(exts(value.value, value.bits) & ((1 << 64)-1), 64)


def EXTS128(value):
    """ extends sign bit out from current MSB to 128 bits
    """
    assert isinstance(value, SelectableInt)
    return SelectableInt(exts(value.value, value.bits) & ((1 << 128)-1), 128)


# signed version of MUL
def MULS(a, b):
    if isinstance(b, int):
        b = SelectableInt(b, self.bits)
    b = check_extsign(a, b)
    a_s = a.value & (1 << (a.bits-1)) != 0
    b_s = b.value & (1 << (b.bits-1)) != 0
    result = abs(a) * abs(b)
    log("MULS", result, a_s, b_s)
    if a_s == b_s:
        return result
    return -result


# XXX should this explicitly extend from 32 to 64?
def EXTZ64(value):
    if isinstance(value, SelectableInt):
        value = value.value
    return SelectableInt(value & ((1 << 32)-1), 64)


def rotl(value, bits, wordlen):
    if isinstance(bits, SelectableInt):
        bits = bits.value
    mask = (1 << wordlen) - 1
    bits = bits & (wordlen - 1)
    return ((value << bits) | (value >> (wordlen-bits))) & mask


def SHL64(value, bits, wordlen=64):
    if isinstance(bits, SelectableInt):
        bits = bits.value
    mask = (1 << wordlen) - 1
    bits = bits & (wordlen - 1)
    return SelectableInt((value << bits) & mask, 64)


def ne(a, b):
    return onebit(a != b)


def eq(a, b):
    return onebit(a == b)


def gt(a, b):
    return onebit(a > b)


def ge(a, b):
    return onebit(a >= b)


def lt(a, b):
    return onebit(a < b)


def le(a, b):
    return onebit(a <= b)


def length(a):
    return len(a)


def undefined(v):
    """ function that, for Power spec purposes, returns undefined bits of
        the same shape as the input bits.  however, for purposes of matching
        POWER9's behavior returns the input bits unchanged.  this effectively
        "marks" (tags) locations in the v3.0B spec that need to be submitted
        for clarification.
    """
    return v


def SINGLE(FRS):
    """convert incoming FRS into 32-bit word.  v3.0B p144 section 4.6.3
    """
    # result - WORD - start off all zeros
    WORD = SelectableInt(0, 32)

    e = FRS[1:12]
    m = FRS[12:64]
    s = FRS[0]

    log("SINGLE", FRS)
    log("s e m", s.value, e.value, m.value)

    # No Denormalization Required (includes Zero / Infinity / NaN)
    if e.value > 896 or FRS[1:64].value == 0:
        log("nodenorm", FRS[0:2].value, hex(FRS[5:35].value))
        WORD[0:2] = FRS[0:2]
        WORD[2:32] = FRS[5:35]

    # Denormalization Required
    if e.value >= 874 and e.value <= 896:
        sign = FRS[0]
        exp = e.value - 1023
        frac = selectconcat(SelectableInt(1, 1), FRS[12:64])
        log("exp, fract", exp, hex(frac.value))
        # denormalize operand
        while exp < -126:
            frac[0:53] = selectconcat(SelectableInt(0, 1), frac[0:52])
            exp = exp + 1
        WORD[0] = sign
        WORD[1:9] = SelectableInt(0, 8)
        WORD[9:32] = frac[1:24]
    # else WORD = undefined # return zeros

    log("WORD", WORD)

    return WORD

# XXX NOTE: these are very quick hacked functions for utterly basic
# FP support


def signinv(res, sign):
    if sign == 1:
        return res
    if sign == 0:
        return 0.0
    if sign == -1:
        return -res


def fp32toselectable(flt):
    """convert FP number to 32 bit SelectableInt
    """
    b = struct.pack("<f", flt)
    val = int.from_bytes(b, byteorder='little', signed=False)
    return SelectableInt(val, 32)


def fp64toselectable(flt):
    """convert FP number to 64 bit SelectableInt
    """
    b = struct.pack("<d", flt)
    val = int.from_bytes(b, byteorder='little', signed=False)
    return SelectableInt(val, 64)


def _minmag(a, b):
    if abs(a) < abs(b):
        return a
    if abs(a) > abs(b):
        return b
    return min(a, b)


def _maxmag(a, b):
    if abs(a) < abs(b):
        return b
    if abs(a) > abs(b):
        return a
    return max(a, b)


class ISAFPHelpers:
    # bfp32/64_OP naming mirrors that in the Power ISA spec.

    def bfp64_ATAN2PI(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(math.atan2(float(a), float(b)) / math.pi)

    def bfp32_ATAN2PI(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(math.atan2(float(a), float(b)) / math.pi)

    def bfp64_ATAN2(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(math.atan2(float(a), float(b)))

    def bfp32_ATAN2(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(math.atan2(float(a), float(b)))

    def bfp64_HYPOT(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(math.hypot(float(a), float(b)))

    def bfp32_HYPOT(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(math.hypot(float(a), float(b)))

    def bfp64_MINNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(min(float(a), float(b)))

    def bfp32_MINNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(min(float(a), float(b)))

    def bfp64_MIN19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(min(float(a), float(b)))

    def bfp32_MIN19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(min(float(a), float(b)))

    def bfp64_MINNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(min(float(a), float(b)))

    def bfp32_MINNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(min(float(a), float(b)))

    def bfp64_MINC(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(min(float(a), float(b)))

    def bfp32_MINC(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(min(float(a), float(b)))

    def bfp64_MAXNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(max(float(a), float(b)))

    def bfp32_MAXNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(max(float(a), float(b)))

    def bfp64_MAX19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(max(float(a), float(b)))

    def bfp32_MAX19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(max(float(a), float(b)))

    def bfp64_MAXNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(max(float(a), float(b)))

    def bfp32_MAXNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(max(float(a), float(b)))

    def bfp64_MAXC(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(max(float(a), float(b)))

    def bfp32_MAXC(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(max(float(a), float(b)))

    def bfp64_MINMAGNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_minmag(float(a), float(b)))

    def bfp32_MINMAGNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_minmag(float(a), float(b)))

    def bfp64_MAXMAGNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_maxmag(float(a), float(b)))

    def bfp32_MAXMAGNUM08(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_maxmag(float(a), float(b)))

    def bfp64_MOD(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(math.fmod(float(a), float(b)))

    def bfp32_MOD(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(math.fmod(float(a), float(b)))

    def bfp64_MINMAG19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_minmag(float(a), float(b)))

    def bfp32_MINMAG19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_minmag(float(a), float(b)))

    def bfp64_MAXMAG19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_maxmag(float(a), float(b)))

    def bfp32_MAXMAG19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_maxmag(float(a), float(b)))

    def bfp64_MINMAGNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_minmag(float(a), float(b)))

    def bfp32_MINMAGNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_minmag(float(a), float(b)))

    def bfp64_MAXMAGNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_maxmag(float(a), float(b)))

    def bfp32_MAXMAGNUM19(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_maxmag(float(a), float(b)))

    def bfp64_REMAINDER(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(math.remainder(float(a), float(b)))

    def bfp32_REMAINDER(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(math.remainder(float(a), float(b)))

    def bfp64_POWR(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(pow(float(a), float(b)))

    def bfp32_POWR(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(pow(float(a), float(b)))

    def bfp64_POW(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(pow(float(a), float(b)))

    def bfp32_POW(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(pow(float(a), float(b)))

    def bfp64_MINMAGC(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_minmag(float(a), float(b)))

    def bfp32_MINMAGC(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_minmag(float(a), float(b)))

    def bfp64_MAXMAGC(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(_maxmag(float(a), float(b)))

    def bfp32_MAXMAGC(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(_maxmag(float(a), float(b)))

    def bfp64_POWN(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(pow(float(a), int(b)))

    def bfp32_POWN(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(pow(float(a), int(b)))

    def bfp64_ROOTN(self, a, b):
        # FIXME: use proper implementation
        return fp64toselectable(pow(float(a), 1 / int(b)))

    def bfp32_ROOTN(self, a, b):
        # FIXME: use proper implementation
        return fp32toselectable(pow(float(a), 1 / int(b)))

    def bfp64_CBRT(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(pow(float(v), 1 / 3))

    def bfp32_CBRT(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(pow(float(v), 1 / 3))

    def bfp64_SINPI(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.sin(float(v) * math.pi))

    def bfp32_SINPI(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.sin(float(v) * math.pi))

    def bfp64_ASINPI(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.asin(float(v)) / math.pi)

    def bfp32_ASINPI(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.asin(float(v)) / math.pi)

    def bfp64_COSPI(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.cos(float(v) * math.pi))

    def bfp32_COSPI(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.cos(float(v) * math.pi))

    def bfp64_TANPI(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.tan(float(v) * math.pi))

    def bfp32_TANPI(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.tan(float(v) * math.pi))

    def bfp64_ACOSPI(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.acos(float(v)) / math.pi)

    def bfp32_ACOSPI(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.acos(float(v)) / math.pi)

    def bfp64_ATANPI(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.atan(float(v)) / math.pi)

    def bfp32_ATANPI(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.atan(float(v)) / math.pi)

    def bfp64_RSQRT(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(1 / math.sqrt(float(v)))

    def bfp32_RSQRT(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(1 / math.sqrt(float(v)))

    def bfp64_SIN(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.sin(float(v)))

    def bfp32_SIN(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.sin(float(v)))

    def bfp64_ASIN(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.asin(float(v)))

    def bfp32_ASIN(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.asin(float(v)))

    def bfp64_COS(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.cos(float(v)))

    def bfp32_COS(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.cos(float(v)))

    def bfp64_TAN(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.tan(float(v)))

    def bfp32_TAN(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.tan(float(v)))

    def bfp64_ACOS(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.acos(float(v)))

    def bfp32_ACOS(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.acos(float(v)))

    def bfp64_ATAN(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.atan(float(v)))

    def bfp32_ATAN(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.atan(float(v)))

    def bfp64_RECIP(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(1 / float(v))

    def bfp32_RECIP(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(1 / float(v))

    def bfp64_SINH(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.sinh(float(v)))

    def bfp32_SINH(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.sinh(float(v)))

    def bfp64_ASINH(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.asinh(float(v)))

    def bfp32_ASINH(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.asinh(float(v)))

    def bfp64_COSH(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.cosh(float(v)))

    def bfp32_COSH(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.cosh(float(v)))

    def bfp64_TANH(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.tanh(float(v)))

    def bfp32_TANH(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.tanh(float(v)))

    def bfp64_ACOSH(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.acosh(float(v)))

    def bfp32_ACOSH(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.acosh(float(v)))

    def bfp64_ATANH(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.atanh(float(v)))

    def bfp32_ATANH(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.atanh(float(v)))

    def bfp64_EXP2M1(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(pow(2, float(v)) - 1)

    def bfp32_EXP2M1(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(pow(2, float(v)) - 1)

    def bfp64_LOG2P1(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.log2(float(v) + 1))

    def bfp32_LOG2P1(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.log2(float(v) + 1))

    def bfp64_EXPM1(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.expm1(float(v)))

    def bfp32_EXPM1(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.expm1(float(v)))

    def bfp64_LOGP1(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.log1p(float(v)))

    def bfp32_LOGP1(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.log1p(float(v)))

    def bfp64_EXP10M1(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(pow(10, float(v)) - 1)

    def bfp32_EXP10M1(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(pow(10, float(v)) - 1)

    def bfp64_LOG10P1(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.log10(float(v) + 1))

    def bfp32_LOG10P1(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.log10(float(v) + 1))

    def bfp64_EXP2(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(pow(2, float(v)))

    def bfp32_EXP2(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(pow(2, float(v)))

    def bfp64_LOG2(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.log2(float(v)))

    def bfp32_LOG2(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.log2(float(v)))

    def bfp64_EXP(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.exp(float(v)))

    def bfp32_EXP(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.exp(float(v)))

    def bfp64_LOG(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.log(float(v)))

    def bfp32_LOG(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.log(float(v)))

    def bfp64_EXP10(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(pow(10, float(v)))

    def bfp32_EXP10(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(pow(10, float(v)))

    def bfp64_LOG10(self, v):
        # FIXME: use proper implementation
        return fp64toselectable(math.log10(float(v)))

    def bfp32_LOG10(self, v):
        # FIXME: use proper implementation
        return fp32toselectable(math.log10(float(v)))

    def FPADD32(self, FRA, FRB):
        # return FPADD64(FRA, FRB)
        #FRA = DOUBLE(SINGLE(FRA))
        #FRB = DOUBLE(SINGLE(FRB))
        result = float(FRA) + float(FRB)
        cvt = fp64toselectable(result)
        cvt = self.DOUBLE2SINGLE(cvt)
        log("FPADD32", FRA, FRB, float(FRA), "+", float(FRB), "=", result, cvt)
        return cvt

    def FPSUB32(self, FRA, FRB):
        # return FPSUB64(FRA, FRB)
        #FRA = DOUBLE(SINGLE(FRA))
        #FRB = DOUBLE(SINGLE(FRB))
        result = float(FRA) - float(FRB)
        cvt = fp64toselectable(result)
        cvt = self.DOUBLE2SINGLE(cvt)
        log("FPSUB32", FRA, FRB, float(FRA), "-", float(FRB), "=", result, cvt)
        return cvt

    def FPMUL32(self, FRA, FRB, sign=1):
        # return FPMUL64(FRA, FRB)
        FRA = self.DOUBLE(SINGLE(FRA))
        FRB = self.DOUBLE(SINGLE(FRB))
        result = signinv(float(FRA) * float(FRB), sign)
        log("FPMUL32", FRA, FRB, float(FRA), float(FRB), result, sign)
        cvt = fp64toselectable(result)
        cvt = self.DOUBLE2SINGLE(cvt)
        log("      cvt", cvt)
        return cvt

    def FPMULADD32(self, FRA, FRC, FRB, mulsign, addsign):
        # return FPMUL64(FRA, FRB)
        #FRA = DOUBLE(SINGLE(FRA))
        #FRB = DOUBLE(SINGLE(FRB))
        if addsign == 1:
            if mulsign == 1:
                result = float(FRA) * float(FRC) + float(FRB)  # fmadds
            elif mulsign == -1:
                result = -(float(FRA) * float(FRC) - float(FRB))  # fnmsubs
        elif addsign == -1:
            if mulsign == 1:
                result = float(FRA) * float(FRC) - float(FRB)  # fmsubs
            elif mulsign == -1:
                result = -(float(FRA) * float(FRC) + float(FRB))  # fnmadds
        elif addsign == 0:
            result = 0.0
        log("FPMULADD32 FRA FRC FRB", FRA, FRC, FRB)
        log("      FRA", float(FRA))
        log("      FRC", float(FRC))
        log("      FRB", float(FRB))
        log("      (FRA*FRC)+FRB=", mulsign, addsign, result)
        cvt = fp64toselectable(result)
        cvt = self.DOUBLE2SINGLE(cvt)
        log("      cvt", cvt)
        return cvt

    def FPDIV32(self, FRA, FRB, sign=1):
        # return FPDIV64(FRA, FRB)
        #FRA = DOUBLE(SINGLE(FRA))
        #FRB = DOUBLE(SINGLE(FRB))
        result = signinv(float(FRA) / float(FRB), sign)
        cvt = fp64toselectable(result)
        cvt = self.DOUBLE2SINGLE(cvt)
        log("FPDIV32", FRA, FRB, result, cvt)
        return cvt


def FPADD64(FRA, FRB):
    result = float(FRA) + float(FRB)
    cvt = fp64toselectable(result)
    log("FPADD64", FRA, FRB, result, cvt)
    return cvt


def FPSUB64(FRA, FRB):
    result = float(FRA) - float(FRB)
    cvt = fp64toselectable(result)
    log("FPSUB64", FRA, FRB, result, cvt)
    return cvt


def FPMUL64(FRA, FRB, sign=1):
    result = signinv(float(FRA) * float(FRB), sign)
    cvt = fp64toselectable(result)
    log("FPMUL64", FRA, FRB, result, cvt, sign)
    return cvt


def FPDIV64(FRA, FRB, sign=1):
    result = signinv(float(FRA) / float(FRB), sign)
    cvt = fp64toselectable(result)
    log("FPDIV64", FRA, FRB, result, cvt, sign)
    return cvt


def bitrev(val, VL):
    """Returns the integer whose value is the reverse of the lowest
    'width' bits of the integer 'val'
    """
    result = 0
    width = VL.bit_length()-1
    for _ in range(width):
        result = (result << 1) | (val & 1)
        val >>= 1
    return result


def log2(val):
    """return the base-2 logarithm of `val`. Only works for powers of 2."""
    if isinstance(val, SelectableInt):
        val = val.value
    retval = val.bit_length() - 1
    assert val == 2 ** retval, "value is not a power of 2"
    return retval


class ISACallerHelper:
    def __init__(self, XLEN):
        self.__XLEN = XLEN

    @property
    def XLEN(self):
        return self.__XLEN

    def XLCASTS(self, value):
        return SelectableInt(exts(value.value, self.XLEN), self.XLEN)

    def XLCASTU(self, value):
        # SelectableInt already takes care of masking out the bits
        return SelectableInt(value.value, self.XLEN)

    def EXTSXL(self, value, bits):
        return SelectableInt(exts(value.value, bits), self.XLEN)

    def DOUBLE2SINGLE(self, FRS):
        """ DOUBLE2SINGLE has been renamed to FRSP since it is the
            implementation of the frsp instruction.
            use SINGLE() or FRSP() instead, or just use struct.pack/unpack
        """
        FPSCR = {
            'UE': SelectableInt(0, 1),
            'OE': SelectableInt(0, 1),
            'RN': SelectableInt(0, 2),  # round to nearest, ties to even
            'XX': SelectableInt(0, 1),
        }
        FRT, FPSCR = self.FRSP(FRS, FPSCR)
        return FRT

    def ROTL32(self, value, bits):
        if isinstance(bits, SelectableInt):
            bits = bits.value
        if isinstance(value, SelectableInt):
            value = SelectableInt(value.value, self.XLEN)
        value = value | (value << (self.XLEN//2))
        value = rotl(value, bits, self.XLEN)
        return value

    def ROTL64(self, value, bits):
        return rotl(value, bits, self.XLEN)

    def MASK32(self, x, y):
        if isinstance(x, SelectableInt):
            x = x.value
        if isinstance(y, SelectableInt):
            y = y.value
        return self.MASK(x+(self.XLEN//2), y+(self.XLEN//2))

    def MASK(self, x, y, lim=None):
        if lim is None:
            lim = self.XLEN
        if isinstance(x, SelectableInt):
            x = x.value
        if isinstance(y, SelectableInt):
            y = y.value
        if x < y:
            x = lim-x
            y = (lim-1)-y
            mask_a = ((1 << x) - 1) & ((1 << lim) - 1)
            mask_b = ((1 << y) - 1) & ((1 << lim) - 1)
        elif x == y:
            return 1 << ((lim-1)-x)
        else:
            x = lim-x
            y = (lim-1)-y
            mask_a = ((1 << x) - 1) & ((1 << lim) - 1)
            mask_b = (~((1 << y) - 1)) & ((1 << lim) - 1)
        return mask_a ^ mask_b

    def __getattr__(self, attr):
        """workaround for getting function out of the global namespace
        within this module, as a way to get functions being transitioned
        to Helper classes within ISACaller (and therefore pseudocode)
        """
        try:
            return globals()[attr]
        except KeyError:
            raise AttributeError(attr)


# For these tests I tried to find power instructions that would let me
# isolate each of these helper operations. So for instance, when I was
# testing the MASK() function, I chose rlwinm and rldicl because if I
# set the shift equal to 0 and passed in a value of all ones, the
# result I got would be exactly the same as the output of MASK()

class HelperTests(unittest.TestCase, ISACallerHelper):
    def __init__(self, *args, **kwargs):
        ISACallerHelper.__init__(self, 64) # TODO: dynamic (64/32/16/8)
        unittest.TestCase.__init__(self, *args, **kwargs)

    def test_MASK(self):
        # Verified using rlwinm, rldicl, rldicr in qemu
        # li 1, -1
        # rlwinm reg, 1, 0, 5, 15
        self.assertHex(self.MASK(5+32, 15+32), 0x7ff0000)
        # rlwinm reg, 1, 0, 15, 5
        self.assertHex(self.MASK(15+32, 5+32), 0xfffffffffc01ffff)
        self.assertHex(self.MASK(30+32, 2+32), 0xffffffffe0000003)
        # rldicl reg, 1, 0, 37
        self.assertHex(self.MASK(37, 63), 0x7ffffff)
        self.assertHex(self.MASK(10, 63), 0x3fffffffffffff)
        self.assertHex(self.MASK(58, 63), 0x3f)
        # rldicr reg, 1, 0, 37
        self.assertHex(self.MASK(0, 37), 0xfffffffffc000000)
        self.assertHex(self.MASK(0, 10), 0xffe0000000000000)
        self.assertHex(self.MASK(0, 58), 0xffffffffffffffe0)

        # li 2, 5
        # slw 1, 1, 2
        self.assertHex(self.MASK(32, 63-5), 0xffffffe0)

        self.assertHex(self.MASK(32, 33), 0xc0000000)
        self.assertHex(self.MASK(32, 32), 0x80000000)
        self.assertHex(self.MASK(33, 33), 0x40000000)

    def test_ROTL64(self):
        # r1 = 0xdeadbeef12345678
        value = 0xdeadbeef12345678

        # rldicl reg, 1, 10, 0
        self.assertHex(self.ROTL64(value, 10), 0xb6fbbc48d159e37a)
        # rldicl reg, 1, 35, 0
        self.assertHex(self.ROTL64(value, 35), 0x91a2b3c6f56df778)
        self.assertHex(self.ROTL64(value, 58), 0xe37ab6fbbc48d159)
        self.assertHex(self.ROTL64(value, 22), 0xbbc48d159e37ab6f)

    def test_ROTL32(self):
        # r1 = 0xdeadbeef
        value = SelectableInt(0xdeadbeef, self.XLEN)

        # rlwinm reg, 1, 10, 0, 31
        self.assertHex(self.ROTL32(value, 10), 0xb6fbbf7a)
        # rlwinm reg, 1, 17, 0, 31
        self.assertHex(self.ROTL32(value, 17), 0x7ddfbd5b)
        self.assertHex(self.ROTL32(value, 25), 0xdfbd5b7d)
        self.assertHex(self.ROTL32(value, 30), 0xf7ab6fbb)

    def test_EXTS64(self):
        value_a = SelectableInt(0xdeadbeef, 32)  # r1
        value_b = SelectableInt(0x73123456, 32)  # r2
        value_c = SelectableInt(0x80000000, 32)  # r3

        # extswsli reg, 1, 0
        self.assertHex(self.EXTS64(value_a), 0xffffffffdeadbeef)
        # extswsli reg, 2, 0
        self.assertHex(self.EXTS64(value_b), SelectableInt(value_b.value, 64))
        # extswsli reg, 3, 0
        self.assertHex(self.EXTS64(value_c), 0xffffffff80000000)

    def test_FPADD32(self):
        value_a = SelectableInt(0x4014000000000000, 64)  # 5.0
        value_b = SelectableInt(0x403B4CCCCCCCCCCD, 64)  # 27.3
        result = FPADD32(value_a, value_b)
        self.assertHex(0x4040266666666666, result)

    def assertHex(self, a, b):
        a_val = a
        if isinstance(a, SelectableInt):
            a_val = a.value
        b_val = b
        if isinstance(b, SelectableInt):
            b_val = b.value
        msg = "{:x} != {:x}".format(a_val, b_val)
        return self.assertEqual(a, b, msg)



if __name__ == '__main__':
    log(SelectableInt.__bases__)
    unittest.main()
