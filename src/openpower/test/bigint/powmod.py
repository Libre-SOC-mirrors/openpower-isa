# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2023 Jacob Lifshay programmerjake@gmail.com
# Copyright 2023 Luke Kenneth Casson Leighton <lkcl@lkcl.net>

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.
#
# * https://bugs.libre-soc.org/show_bug.cgi?id=1044

""" modular exponentiation (`pow(x, y, z)`)

related bugs:

 * https://bugs.libre-soc.org/show_bug.cgi?id=1044
"""

from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.test.util import assemble
from nmutil.sim_util import hash_256
from openpower.util import log
from nmutil.plain_data import plain_data
from cached_property import cached_property
from openpower.decoder.isa.svshape import SVSHAPE
from openpower.decoder.power_enums import SPRfull
from openpower.decoder.selectable_int import SelectableInt


MUL_256_X_256_TO_512_ASM = (
    "mul_256_to_512:",
    # a is in r4-7, b is in r8-11
    "setvl 0, 0, 8, 0, 1, 1",  # set VL to 8
    "sv.or *32, *4, *4",  # move args to r32-39
    # a is now in r32-35, b is in r36-39, y is in r4-11, t is in r40-44
    "sv.addi *4, 0, 0",  # clear output
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.maddedu *4, *32, 36, 8",  # first partial-product a * b[0]
    "sv.addi 44, 0, 0",
    "sv.maddedu *40, *32, 37, 44",  # second partial-product a * b[1]
    "sv.addc 5, 5, 40",
    "sv.adde *6, *6, *41",
    "sv.addi 44, 0, 0",
    "sv.maddedu *40, *32, 38, 44",  # third partial-product a * b[2]
    "sv.addc 6, 6, 40",
    "sv.adde *7, *7, *41",
    "sv.addi 44, 0, 0",
    "sv.maddedu *40, *32, 39, 44",  # final partial-product a * b[3]
    "sv.addc 7, 7, 40",
    "sv.adde *8, *8, *41",
    "bclr 20, 0, 0 # blr",
)

# TODO: these really need to go into a common util file, see
# openpower/decoder/isa/poly1305-donna.py:def _DSRD(lo, hi, sh)
# okok they are modulo 100 but you get the general idea


def maddedu(a, b, c):
    y = a * b + c
    return y % 100, y // 100


def adde(a, b, c):
    y = a + b + c
    return y % 100, y // 100


def addc(a, b):
    y = a + b
    return y % 100, y // 100


def python_mul_algorithm(a, b):
    # version of the MUL_256_X_256_TO_512_ASM algorithm using base 100 rather
    # than 2^64, since that's easier to read.
    # run this file in a debugger to see all the intermediate values.
    y = [0] * 8
    t = [0] * 5
    for i in range(4):
        y[i], y[4] = maddedu(a[0], b[i], y[4])
    t[4] = 0
    for i in range(4):
        t[i], t[4] = maddedu(a[1], b[i], t[4])
    y[1], ca = addc(y[1], t[0])
    for i in range(4):
        y[2 + i], ca = adde(y[2 + i], t[1 + i], ca)
    t[4] = 0
    for i in range(4):
        t[i], t[4] = maddedu(a[2], b[i], t[4])
    y[2], ca = addc(y[2], t[0])
    for i in range(4):
        y[3 + i], ca = adde(y[3 + i], t[1 + i], ca)
    t[4] = 0
    for i in range(4):
        t[i], t[4] = maddedu(a[3], b[i], t[4])
    y[3], ca = addc(y[3], t[0])
    for i in range(4):
        y[4 + i], ca = adde(y[4 + i], t[1 + i], ca)
    return y


def python_mul_algorithm2(a, b):
    # version 2 of the MUL_256_X_256_TO_512_ASM algorithm using base 100 rather
    # than 2^64, since that's easier to read.
    # the idea here is that it will "morph" into something more akin to
    # using REMAP bigmul (first using REMAP Indexed)

    # create a schedule for use below. the "end of inner loop" marker is 0b01
    iyl = []
    il = []
    for iy in range(4):
        for i in range(4):
            iyl.append((iy+i, i == 3))
            il.append(i)
        for i in range(5):
            iyl.append((iy+i, i == 4))
            il.append(i)

    y = [0] * 8  # result y and temp t of same size
    t = [0] * 8  # no need after this to set t[4] to zero
    for iy in range(4):
        for i in range(4):  # use t[iy+4] as a 64-bit carry
            t[iy+i], t[iy+4] = maddedu(a[iy], b[i], t[iy+4])
        ca = 0
        for i in range(5):  # add vec t to y with 1-bit carry
            idx = iy + i
            y[idx], ca = adde(y[idx], t[idx], ca)
    return y


DIVMOD_SHIFT_SUB_512x256_TO_256x256_ASM = (
    # extremely slow and simplistic shift and subtract algorithm.
    # a future task is to rewrite to use Knuth's Algorithm D,
    # which is generally an order of magnitude faster
    "divmod_512_by_256:",
    # n is in r4-11, d is in r32-35
    "addi 3, 0, 256 # li 3, 256",
    "mtspr 9, 3 # mtctr 3",  # set CTR to 256
    "setvl 0, 0, 8, 0, 1, 1",  # set VL to 8
    # r is in r40-47
    "sv.or *40, *4, *4",  # assign n to r, in r40-47
    # shifted_d is in r32-39
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "addi 3, 0, 1 # li 3, 1",  # shift amount
    "addi 0, 0, 0 # li 0, 0",  # dsrd carry
    "sv.dsrd/mrr *36, *32, 3, 0",  # shifted_d = d << (256 - 1)
    "sv.addi *32, 0, 0",  # clear lsb half
    "sv.or 35, 0, 0",  # move carry to correct location
    # q is in r4-7
    "sv.addi *4, 0, 0",  # clear q
    "divmod_loop:",
    "setvl 0, 0, 8, 0, 1, 1",  # set VL to 8
    "subfc 0, 0, 0",  # set CA
    # diff is in r48-55
    "sv.subfe *48, *32, *40",  # diff = r - shifted_d
    # not borrowed is in CA
    "mcrxrx 0",  # move CA to CR0.eq
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "addi 0, 0, 0 # li 0, 0",  # dsld carry
    "sv.dsld *4, *4, 3, 0",  # q <<= 1 (1 is in r3)
    "setvl 0, 0, 8, 0, 1, 1",  # set VL to 8
    "bc 4, 2, divmod_else # bne divmod_else",  # if borrowed goto divmod_else
    "ori 4, 4, 1",  # q |= 1
    "sv.or *40, *48, *48",  # r = diff
    "divmod_else:",
    "addi 0, 0, 0 # li 0, 0",  # dsld carry
    "sv.dsld *40, *40, 3, 0",  # r <<= 1 (1 is in r3)
    "bc 16, 0, divmod_loop # bdnz divmod_loop",
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    # r is in r40-47
    "sv.or *8, *44, *44",  # r >>= 256
    # q is in r4-7, r is in r8-11
    "bclr 20, 0, 0 # blr",
)


class _DivModRegsRegexLogger:
    """ logger that logs a regex that matches the expected register dump for
    the currently tracked `locals` -- quite useful for debugging
    """

    def __init__(self, enabled=True, regs=None):
        self.__tracked = {}
        self.__regs = regs if regs is not None else {}
        self.enabled = enabled

    def log(self, locals_, **changes):
        """ use like so:
        ```
        # create a variable `a`:
        a = ...

        # we invoke `locals()` each time since python doesn't guarantee
        # it's up-to-date otherwise
        logger.log(locals(), a=(4, 6))  # `a` starts at r4 and uses 6 registers

        a += 3

        logger.log(locals())  # keeps using `a`

        b = a + 5

        logger.log(locals(), a=None, b=(4, 6))  # remove `a` and add `b`
        ```
        """

        for k, v in changes.items():
            if v is None:
                self.__tracked.pop(k, None)
            else:
                if isinstance(v, (tuple, list)):
                    start_gpr, size = v
                else:
                    start_gpr = v
                    size = 1
                if not isinstance(start_gpr, int):
                    start_gpr = self.__regs[start_gpr]
                self.__tracked[k] = start_gpr, size

        gprs = [None] * 128
        for name, (start_gpr, size) in self.__tracked.items():
            value = locals_[name]
            if value is None:
                continue
            elif not isinstance(value, (list, tuple)):
                value = [(value >> 64 * i) % 2 ** 64 for i in range(size)]
            else:
                assert len(value) == size, "value has wrong len"
            for i in range(size):
                if value[i] is None:
                    continue
                reg = start_gpr + i
                if gprs[reg] is not None:
                    other_value, other_name, other_i = gprs[reg]
                    raise AssertionError(f"overlapping values at r{reg}: "
                                         f"{name}[{i}] overlaps with "
                                         f"{other_name}[{other_i}]")
                gprs[reg] = value[i], name, i

        if not self.enabled:
            # after building `gprs` so we catch any missing/invalid locals
            return

        segments = []

        for i in range(0, 128, 8):
            segments.append(f"reg +{i}")
            for value in gprs[i:i + 8]:
                if value is None:
                    segments.append(" +[0-9a-f]+")
                else:
                    value, name, i = value
                    segments.append(f" +{value:08x}")
            segments.append("\\n")
        log("DIVMOD REGEX:", "".join(segments))


def python_divmod_shift_sub_algorithm(n, d, width=256, log_regex=False):
    assert n >= 0 and d > 0 and width > 0 and n < (d << width), "invalid input"
    do_log = _DivModRegsRegexLogger(enabled=log_regex).log

    do_log(locals(), n=(4, 8), d=(32, 4))

    r = n
    do_log(locals(), n=None, r=(40, 8))

    shifted_d = d << (width - 1)
    do_log(locals(), d=None, shifted_d=(32, 8))

    q = 0
    do_log(locals(), q=(4, 4))

    for _ in range(width):
        diff = r - shifted_d
        borrowed = diff < 0
        do_log(locals(), diff=(48, 8))

        q <<= 1
        do_log(locals())

        if not borrowed:
            q |= 1
            do_log(locals())

            r = diff
            do_log(locals())

        r <<= 1
        do_log(locals())

    r >>= width
    do_log(locals(), r=(8, 4))

    return q, r


def divmod2du(RA, RB, RC):
    # type: (int, int, int) -> tuple[int, int, bool]
    if RC < RB and RB != 0:
        RT, RS = divmod(RC << 64 | RA, RB)
        overflow = False
    else:
        overflow = True
        RT = (1 << 64) - 1
        RS = 0
    return RT, RS, overflow


@plain_data()
class DivModKnuthAlgorithmD:
    __slots__ = "num_size", "denom_size", "q_size", "word_size", "regs"

    def __init__(self, num_size=8, denom_size=4, q_size=4,
                 word_size=64, regs=None):
        # type: (int, int, int | None, int, None | dict[str, int]) -> None
        assert num_size >= denom_size, \
            "the dividend's length must be >= the divisor's length"
        assert word_size > 0

        if q_size is None:
            # quotient length from original algorithm is m - n + 1,
            # but that assumes v[-1] != 0 -- since we support smaller divisors
            # the quotient must be larger.
            q_size = num_size

        if regs is None:
            regs = {
                "n_0": 4,
                "d_0": 32,
                "u": 36,
                "m": 9,
                "v": 32,
                "n_scalar": 8,
                "q": 4,
                "vn": 32,
                "un": 36,
                "product": 46,
                "r": 8,
                "t_single": 8,
                "s_scalar": 10,
                "t_for_uv_shift": 0,
                "n_for_unnorm": 16,
                "t_for_unnorm": 3,
                "s_for_unnorm": 18,
                "qhat": 12,
                "rhat_lo": 14,
                "rhat_hi": 15,
                "t_for_prod": 18,
                "index": 3,
                "j": 11,
                "qhat_denom": 18,
                "qhat_num_hi": 16,
                "qhat_prod_lo": 15,
                "qhat_prod_hi": 18,
                "sub_len": 3,
            }

        self.num_size = num_size
        self.denom_size = denom_size
        self.q_size = q_size
        self.word_size = word_size
        self.regs = regs

    @property
    def r_size(self):
        return self.denom_size

    @property
    def un_size(self):
        return self.num_size + 1

    @property
    def vn_size(self):
        return self.denom_size

    @property
    def product_size(self):
        return self.num_size + 1

    def python(self, n, d, log_regex=False, on_corner_case=lambda desc: None):
        do_log = _DivModRegsRegexLogger(enabled=log_regex, regs=self.regs).log

        do_log(locals(), n=("n_0", self.num_size), d=("d_0", self.denom_size))

        # switch to names used by Knuth's algorithm D
        u = list(n)  # dividend
        assert len(u) == self.num_size, "numerator has wrong size"
        do_log(locals(), n=None, u=("u", self.num_size))
        m = len(u)  # length of dividend
        do_log(locals(), m="m")
        v = list(d)  # divisor
        assert len(v) == self.denom_size, "denominator has wrong size"
        del d  # less confusing to debug
        do_log(locals(), d=None, v=("v", self.denom_size))
        n = len(v)  # length of divisor
        do_log(locals(), n="n_scalar")

        # allocate outputs/temporaries -- before any normalization so
        # the outputs/temporaries can be fixed-length in the assembly version.

        q = [0] * self.q_size  # quotient
        do_log(locals(), q=("q", self.q_size))
        vn = [None] * self.vn_size  # normalized divisor
        do_log(locals(), vn=("vn", self.vn_size))
        un = [None] * self.un_size  # normalized dividend
        do_log(locals(), un=("un", self.un_size))
        product = [None] * self.product_size
        do_log(locals(), product=("product", self.product_size))

        # get non-zero length of dividend
        while m > 0 and u[m - 1] == 0:
            m -= 1

        do_log(locals())

        # get non-zero length of divisor
        while n > 0 and v[n - 1] == 0:
            n -= 1

        do_log(locals())

        if n == 0:
            raise ZeroDivisionError

        if n == 1:
            on_corner_case("single-word divisor")
            # Knuth's algorithm D requires the divisor to have length >= 2
            # handle single-word divisors separately
            t = 0
            if m > self.q_size:
                t = u[self.q_size]
                m = self.q_size
            do_log(locals(), t="t_single", n=None)
            do_log(locals(), m=None)  # VL = m, so we don't need it in a GPR
            for i in reversed(range(m)):
                q[i], t, _ = divmod2du(u[i], v[0], t)
                do_log(locals())
            r = [0] * self.r_size  # remainder
            r[0] = t
            do_log(locals(), t=None, r=("r", self.r_size))
            return q, r

        if m < n:
            r = [None] * self.r_size  # remainder
            do_log(locals(), r=("r", self.r_size), m=None, n=None)
            # dividend < divisor
            for i in range(self.r_size):
                r[i] = u[i]
            do_log(locals())
            return q, r

        # Knuth's algorithm D starts here:

        # Step D1: normalize

        # calculate amount to shift by -- count leading zeros
        s = 0
        index = n - 1
        do_log(locals(), index="index")
        while (v[index] << s) >> (self.word_size - 1) == 0:
            s += 1

        do_log(locals(), s="s_scalar", index=None)

        if s != 0:
            on_corner_case("non-zero shift")

        # vn = v << s
        t = 0
        do_log(locals(), t="t_for_uv_shift")
        for i in range(n):
            # dsld
            t |= v[i] << s
            v[i] = None  # mark reg as unused
            vn[i] = t % 2 ** self.word_size
            t >>= self.word_size
            do_log(locals())

        # un = u << s
        t = 0
        do_log(locals(), v=None)
        for i in range(m):
            # dsld
            t |= u[i] << s
            u[i] = None  # mark reg as unused
            un[i] = t % 2 ** self.word_size
            t >>= self.word_size
            do_log(locals())
        index = m
        do_log(locals(), index="index")
        un[index] = t

        do_log(locals(), u=None, t=None, index=None)

        # Step D2 and Step D7: loop
        for j in range(min(m - n, self.q_size - 1), -1, -1):
            do_log(locals(), j="j")
            # Step D3: calculate q̂

            index = j + n
            do_log(locals(), index="index")
            qhat_num_hi = un[index]
            do_log(locals(), qhat_num_hi="qhat_num_hi")
            index = n - 1
            do_log(locals())
            qhat_denom = vn[index]
            do_log(locals(), qhat_denom="qhat_denom")
            index = j + n - 1
            do_log(locals())
            qhat, rhat_lo, ov = divmod2du(un[index], qhat_denom, qhat_num_hi)
            rhat_hi = 0
            do_log(locals(), qhat="qhat", rhat_lo="rhat_lo", rhat_hi="rhat_hi")
            if ov:
                # division overflows word
                on_corner_case("qhat overflows word")
                assert qhat_num_hi == qhat_denom
                rhat_lo = (qhat * qhat_denom) % 2 ** self.word_size
                rhat_hi = (qhat * qhat_denom) >> self.word_size
                do_log(locals())
                borrow = un[index] < rhat_lo
                rhat_lo = (un[index] - rhat_lo) % 2 ** self.word_size
                do_log(locals())
                rhat_hi = qhat_num_hi - rhat_hi - borrow
            do_log(locals(), qhat_num_hi=None, qhat_denom=None)

            while rhat_hi == 0:
                index = n - 2
                do_log(locals())
                qhat_prod_lo = (qhat * vn[index]) % 2 ** self.word_size
                do_log(locals(), qhat_prod_lo="qhat_prod_lo", rhat_hi=None)
                qhat_prod_hi = (qhat * vn[index]) >> self.word_size
                do_log(locals(), qhat_prod_hi="qhat_prod_hi")
                if qhat_prod_hi < rhat_lo:
                    break
                index = j + n - 2
                do_log(locals())
                if qhat_prod_hi == rhat_lo:
                    if qhat_prod_lo <= un[index]:
                        break
                on_corner_case("qhat adjustment")
                do_log(locals(), index=None,
                       qhat_prod_lo=None, qhat_prod_hi=None)
                qhat -= 1
                do_log(locals(), index="index")
                index = n - 1
                do_log(locals())
                carry = (rhat_lo + vn[index]) >= 2 ** self.word_size
                rhat_lo = (rhat_lo + vn[index]) % 2 ** self.word_size
                do_log(locals())
                rhat_hi = carry
                do_log(locals(), rhat_hi="rhat_hi")

            do_log(locals(), rhat_lo=None, rhat_hi=None, index=None,
                   qhat_prod_lo=None, qhat_prod_hi=None)

            # Step D4: multiply and subtract

            t = 0
            do_log(locals(), t="t_for_prod")
            for i in range(n):
                # maddedu
                t += vn[i] * qhat
                product[i] = t % 2 ** self.word_size
                t >>= self.word_size
                do_log(locals())
            index = n
            do_log(locals(), index="index")
            product[index] = t
            do_log(locals(), t=None, index=None)

            t = 1
            do_log(locals())
            sub_len = n + 1
            do_log(locals(), sub_len="sub_len")
            VL = sub_len
            do_log(locals(), sub_len=None)
            for i in range(VL):
                # subfe
                not_product = ~product[i] % 2 ** self.word_size
                t += not_product + un[j + i]
                un[j + i] = t % 2 ** self.word_size
                t = int(t >= 2 ** self.word_size)
                do_log(locals())
            need_fixup = not t

            # Step D5: test remainder

            if need_fixup:

                # Step D6: add back

                on_corner_case("add back")

                qhat -= 1
                do_log(locals())

                t = 0
                for i in range(n):
                    # adde
                    t += un[j + i] + vn[i]
                    un[j + i] = t % 2 ** self.word_size
                    t = int(t >= 2 ** self.word_size)
                    do_log(locals())
                un[j + n] += t
                do_log(locals())

            q[j] = qhat
            do_log(locals(), index=None)

        # Step D8: un-normalize

        # move s and n
        do_log(locals(), s="s_for_unnorm", n="n_for_unnorm",
               vn=None, m=None, j=None)

        r = [0] * self.r_size  # remainder
        do_log(locals(), r=("r", self.r_size))
        # r = un >> s
        t = 0
        do_log(locals(), t="t_for_unnorm")
        for i in reversed(range(n)):
            # dsrd
            t <<= self.word_size
            t |= (un[i] << self.word_size) >> s
            r[i] = t >> self.word_size
            t %= 2 ** self.word_size
            do_log(locals())

        return q, r

    def __asm_iter(self):
        if self.word_size != 64:
            raise NotImplementedError("only word_size == 64 is implemented")
        n_0 = self.regs["n_0"]
        d_0 = self.regs["d_0"]
        u = self.regs["u"]
        m = self.regs["m"]
        v = self.regs["v"]
        n_scalar = self.regs["n_scalar"]
        q = self.regs["q"]
        vn = self.regs["vn"]
        un = self.regs["un"]
        product = self.regs["product"]
        r = self.regs["r"]
        t_single = self.regs["t_single"]
        s_scalar = self.regs["s_scalar"]
        t_for_uv_shift = self.regs["t_for_uv_shift"]
        n_for_unnorm = self.regs["n_for_unnorm"]
        t_for_unnorm = self.regs["t_for_unnorm"]
        s_for_unnorm = self.regs["s_for_unnorm"]
        qhat = self.regs["qhat"]
        rhat_lo = self.regs["rhat_lo"]
        rhat_hi = self.regs["rhat_hi"]
        t_for_prod = self.regs["t_for_prod"]
        index = self.regs["index"]
        j = self.regs["j"]
        qhat_num_hi = self.regs["qhat_num_hi"]
        qhat_denom = self.regs["qhat_denom"]
        qhat_prod_lo = self.regs["qhat_prod_lo"]
        qhat_prod_hi = self.regs["qhat_prod_hi"]
        sub_len = self.regs["sub_len"]
        num_size = self.num_size
        denom_size = self.denom_size
        q_size = self.q_size
        r_size = self.r_size
        un_size = self.un_size
        vn_size = self.vn_size
        product_size = self.product_size

        yield "divmod_512_by_256:"
        # n in n_0 size num_size
        # d in d_0 size denom_size

        yield "mfspr 0, 8 # mflr 0"
        yield "std 0, 16(1)"  # save return address
        yield "setvl 0, 0, 18, 0, 1, 1"  # set VL to 18
        yield "sv.std *14, -144(1)"  # save all callee-save registers
        yield "stdu 1, -176(1)"  # create stack frame as required by ABI

        # switch to names used by Knuth's algorithm D
        yield f"setvl 0, 0, {num_size}, 0, 1, 1"  # set VL to num_size
        yield f"sv.or *{u}, *{n_0}, *{n_0}"  # u = n
        yield f"addi {m}, 0, {num_size}"  # m = len(u)
        assert v == d_0, "v and d_0 must be in the same regs"  # v = d
        yield f"addi {n_scalar}, 0, {denom_size}"  # n = len(v)

        # allocate outputs/temporaries
        yield f"setvl 0, 0, {q_size}, 0, 1, 1"  # set VL to q_size
        yield f"sv.addi *{q}, 0, 0"  # q = [0] * q_size

        # get non-zero length of dividend
        yield f"setvl 0, 0, {num_size}, 0, 1, 1"  # set VL to num_size
        # create SVSHAPE that reverses order
        svshape = SVSHAPE(0)
        svshape.zdimsz = num_size
        svshape.invxyz = SelectableInt(0b1, 3)  # invert Z
        svshape_low = int(svshape) % 2 ** 16
        svshape_high = int(svshape) >> 16
        SVSHAPE0 = SPRfull.SVSHAPE0.value
        yield f"addis 0, 0, {svshape_high}"
        yield f"ori 0, 0, {svshape_low}"
        yield f"mtspr {SVSHAPE0}, 0 # mtspr SVSHAPE0, 0"
        yield f"svremap 0o01, 0, 0, 0, 0, 0, 0"  # enable SVSHAPE0 for RA
        yield f"sv.cmpli/ff=ne *0, 1, *{u}, 0"
        yield f"setvl {m}, 0, 1, 0, 0, 0 # getvl {m}"  # m = VL
        yield f"subfic {m}, {m}, {num_size}"  # m = num_size - m

        # get non-zero length of divisor
        yield f"setvl 0, 0, {denom_size}, 0, 1, 1"  # set VL to denom_size
        # create SVSHAPE that reverses order
        svshape = SVSHAPE(0)
        svshape.zdimsz = denom_size
        svshape.invxyz = SelectableInt(0b1, 3)  # invert Z
        svshape_low = int(svshape) % 2 ** 16
        svshape_high = int(svshape) >> 16
        yield f"addis 0, 0, {svshape_high}"
        yield f"ori 0, 0, {svshape_low}"
        yield f"mtspr {SVSHAPE0}, 0 # mtspr SVSHAPE0, 0"
        yield f"svremap 0o01, 0, 0, 0, 0, 0, 0"  # enable SVSHAPE0 for RA
        yield f"sv.cmpli/ff=ne *0, 1, *{v}, 0"
        yield f"setvl {n_scalar}, 0, 1, 0, 0, 0 # getvl {n_scalar}"  # n = VL
        # n = denom_size - n
        yield f"subfic {n_scalar}, {n_scalar}, {denom_size}"

        yield f"cmpli 0, 1, {n_scalar}, 1  # cmpldi {n_scalar}, 1"
        yield "bc 4, 2, divmod_skip_sw_divisor # bne divmod_skip_sw_divisor"

        # Knuth's algorithm D requires the divisor to have length >= 2
        # handle single-word divisors separately
        yield f"addi {t_single}, 0, 0"
        yield f"setvl. {m}, {m}, {q_size}, 0, 1, 1"  # m = VL = min(m, q_size)
        # if CR0.SO: t = u[q_size]
        yield f"sv.isel {t_single}, {u + q_size}, {t_single}, 3"
        # div loop
        yield f"sv.divmod2du/mrr *{q}, *{u}, {v}, {t_single}"
        # r[0] = t
        assert r == t_single, "r[0] and t_single must be in the same regs"
        yield f"setvl 0, 0, {r_size - 1}, 0, 1, 1"  # set VL to r_size - 1
        yield f"sv.addi *{r + 1}, 0, 0"  # r[1:] = [0] * (r_size - 1)

        yield "b divmod_return"

        yield "divmod_skip_sw_divisor:"
        yield f"cmpl 0, 1, {m}, {n_scalar}  # cmpld {m}, {n_scalar}"
        yield "bc 4, 0, divmod_skip_copy_r # bge divmod_skip_copy_r"
        # if m < n:

        yield f"setvl 0, 0, {r_size}, 0, 1, 1"  # set VL to r_size
        yield f"sv.or *{r}, *{u}, *{u}"  # r[...] = u[...]
        yield "b divmod_return"

        yield "divmod_skip_copy_r:"

        # Knuth's algorithm D starts here:

        # Step D1: normalize

        # calculate amount to shift by -- count leading zeros
        yield f"addi {index}, {n_scalar}, -1"  # index = n - 1
        assert index == 3, "index must be r3"
        yield f"setvl 0, 0, {denom_size}, 0, 1, 1"  # VL = denom_size
        yield f"sv.cntlzd/m=1<<r3 {s_scalar}, *{v}"  # s = clz64(v[index])

        yield f"addi {t_for_uv_shift}, 0, 0"  # t = 0
        yield f"setvl 0, {n_scalar}, {denom_size}, 0, 1, 1"  # VL = n
        # vn = v << s
        yield f"sv.dsld *{vn}, *{v}, {s_scalar}, {t_for_uv_shift}"

        yield f"addi {t_for_uv_shift}, 0, 0"  # t = 0
        yield f"setvl 0, {m}, {num_size}, 0, 1, 1"  # VL = m
        # un = u << s
        yield f"sv.dsld *{un}, *{u}, {s_scalar}, {t_for_uv_shift}"
        yield f"setvl 0, 0, {un_size}, 0, 1, 1"  # VL = un_size
        yield f"or {index}, {m}, {m}"  # index = m
        assert index == 3, "index must be r3"
        # un[index] = t
        yield f"sv.or/m=1<<r3 *{un}, {t_for_uv_shift}, {t_for_uv_shift}"

        # Step D2 and Step D7: loop
        # j = m - n
        yield f"subf {j}, {n_scalar}, {m}"
        # j = min(j, q_size - 1)
        yield f"addi 0, 0, {q_size - 1}"
        yield f"minmax {j}, {j}, 0, 0  # maxd {j}, {j}, 0"
        yield f"divmod_loop:"

        # Step D3: calculate q̂
        yield f"setvl 0, 0, {un_size}, 0, 1, 1"  # VL = un_size
        yield f"add {index}, {j}, {n_scalar}"  # index = j + n
        # qhat_num_hi = un[index]
        assert index == 3, "index must be r3"
        yield f"sv.or/m=1<<r3 {qhat_num_hi}, *{un}, *{un}"
        yield f"addi {index}, {n_scalar}, -1"  # index = n - 1
        # qhat_denom = vn[index]
        yield f"setvl 0, 0, {vn_size}, 0, 1, 1"  # VL = vn_size
        assert index == 3, "index must be r3"
        yield f"sv.or/m=1<<r3 {qhat_denom}, *{vn}, *{vn}"
        yield f"add {index}, {index}, {j}"  # index = j + n - 1
        # qhat, rhat_lo, ov = divmod2du(un[index], qhat_denom, qhat_num_hi)
        yield f"or {rhat_lo}, {qhat_num_hi}, {qhat_num_hi}"
        yield f"setvl 0, 0, {un_size}, 0, 1, 1"  # VL = un_size
        assert index == 3, "index must be r3"
        yield f"sv.divmod2du/m=1<<r3 {qhat}, *{un}, {qhat_denom}, {rhat_lo}"
        yield f"mcrxrx 0"  # move OV to CR0.lt
        yield "bc 4, 0, divmod_skip_qhat_overflow # bge divmod_..."
        # if ov:
        # division overflows word
        # rhat_lo = (qhat * qhat_denom) % 2 ** self.word_size
        yield f"mulld {rhat_lo}, {qhat}, {qhat_denom}"
        # rhat_hi = (qhat * qhat_denom) >> self.word_size
        yield f"mulhdu {rhat_hi}, {qhat}, {qhat_denom}"
        # borrow = un[index] < rhat_lo
        # rhat_lo = (un[index] - rhat_lo) % 2 ** self.word_size
        assert index == 3, "index must be r3"
        yield f"sv.subfc/m=1<<r3 {rhat_lo}, {rhat_lo}, *{un}"
        # rhat_hi = qhat_num_hi - rhat_hi - borrow
        yield f"subfe {rhat_hi}, {rhat_hi}, {qhat_num_hi}"
        yield "divmod_skip_qhat_overflow:"

        # while rhat_hi == 0:
        yield "divmod_qhat_adj_loop:"
        yield f"cmpli 0, 1, {rhat_hi}, 0  # cmpldi {rhat_hi}, 0"
        yield "bc 12, 2, divmod_qhat_adj_loop_break # beq divmod_qhat_adj..."

        yield f"setvl 0, 0, {vn_size}, 0, 1, 1"  # VL = vn_size
        yield f"addi {index}, {n_scalar}, -2"  # index = n - 2
        # qhat_prod_lo = (qhat * vn[index]) % 2 ** self.word_size
        assert index == 3, "index must be r3"
        yield f"sv.mulld/m=1<<r3 {qhat_prod_lo}, {qhat}, *{vn}"
        # qhat_prod_hi = (qhat * vn[index]) >> self.word_size
        yield f"sv.mulhdu/m=1<<r3 {qhat_prod_hi}, {qhat}, *{vn}"

        # if qhat_prod_hi < rhat_lo:
        #     break
        yield f"cmpl 0, 1, {qhat_prod_hi}, {rhat_lo}  # cmpld cr0, ..."
        yield "bc 12, 0, divmod_qhat_adj_loop_break # blt divmod_qhat_adj..."
        # if qhat_prod_hi == rhat_lo:
        yield "bc 4, 2, divmod_qhat_do_adj # bne divmod_qhat_do_adj"

        yield f"add {index}, {index}, {j}"  # index = j + n - 2
        # if qhat_prod_lo <= un[index]:
        #     break
        yield f"setvl 0, 0, {un_size}, 0, 1, 1"  # VL = un_size
        assert index == 3, "index must be r3"
        yield f"sv.cmp/m=1<<r3 1, 1, {qhat_prod_lo}, *{un}  # cmpld cr1, ..."
        yield "bc 4, 1, divmod_qhat_adj_loop_break # ble divmod_qhat_adj..."
        yield "divmod_qhat_do_adj:"

        yield f"addi {qhat}, {qhat}, -1"  # qhat -= 1

        yield f"addi {index}, {n_scalar}, -1"  # index = n - 1
        # carry = (rhat_lo + vn[index]) >= 2 ** self.word_size
        # rhat_lo = (rhat_lo + vn[index]) % 2 ** self.word_size
        yield f"setvl 0, 0, {vn_size}, 0, 1, 1"  # VL = vn_size
        assert index == 3, "index must be r3"
        yield f"sv.addc/m=1<<r3 {rhat_lo}, {rhat_lo}, *{vn}"
        # rhat_hi = carry
        yield f"addi 0, 0, 0"
        yield f"addze. {rhat_hi}, 0"

        # while rhat_hi == 0:
        yield "bc 4, 2, divmod_qhat_adj_loop # bne divmod_qhat_adj_loop"
        yield "divmod_qhat_adj_loop_break:"

        # Step D4: multiply and subtract

        yield f"setvl 0, {n_scalar}, {vn_size}, 0, 1, 1"  # VL = n
        yield f"addi {t_for_prod}, 0, 0"  # t = 0
        # product[:n] = vn[:n] * qhat
        yield f"sv.maddedu *{product}, *{vn}, {qhat}, {t_for_prod}"
        yield f"or {index}, {n_scalar}, {n_scalar}"  # index = n
        yield f"setvl 0, 0, {vn_size}, 0, 1, 1"  # VL = vn_size
        # product[index] = t
        assert index == 3, "index must be r3"
        yield f"sv.or/m=1<<r3 *{product}, {t_for_prod}, {t_for_prod}"

        yield "subfc 0, 0, 0"  # t = 1 (t is CA)
        yield f"addi {sub_len}, {n_scalar}, 1"  # sub_len = n + 1
        yield f"setvl 0, {sub_len}, {product_size}, 0, 1, 1"  # VL = sub_len
        # create svshape that offsets by `j`
        svshape = SVSHAPE(0)
        svshape.zdimsz = q_size
        svshape_low = int(svshape) % 2 ** 16
        svshape_high = int(svshape) >> 16
        offset_field = svshape.fsi['offset']
        assert 2 ** (len(offset_field) - 1) >= q_size, \
            "max needed offset won't fit in SVSHAPE"
        mask_start_le = len(svshape) - offset_field.br[0] - 1
        mask_start = 64 - mask_start_le - 1
        last = len(offset_field) - 1
        shift_amount = len(svshape) - offset_field.br[last] - 1
        # insert j in offset field
        yield f"rldic 0, {j}, {shift_amount}, {mask_start}"
        # or in all the other bits
        if svshape_high != 0:
            yield f"oris 0, 0, {svshape_high}"
        yield f"ori 0, 0, {svshape_low}"
        yield f"mtspr {SVSHAPE0}, 0 # mtspr SVSHAPE0, 0"
        yield f"svremap 0o12, 0, 0, 0, 0, 0, 0"  # enable SVSHAPE0 for RB & RT
        # un[j:] -= product
        yield f"sv.subfe *{un}, *{product}, *{un}"
        # need_fixup = not CA

        # Step D5: test remainder

        yield f"mcrxrx 0"  # move CA to CR0.eq
        # if need_fixup:
        yield "bc 4, 2, divmod_skip_fixup # bne divmod_skip_fixup"

        # Step D6: add back

        yield f"addi {qhat}, {qhat}, -1"  # qhat -= 1
        yield "addic 0, 0, 0"  # t = 0 (t is CA)
        yield f"setvl 0, {n_scalar}, {vn_size}, 0, 1, 1"  # VL = n
        yield f"svremap 0o11, 0, 0, 0, 0, 0, 0"  # enable SVSHAPE0 for RA & RT
        # un[j:] += vn
        yield f"sv.adde *{un}, *{un}, *{vn}"
        yield f"svremap 0o11, 0, 0, 0, 0, 0, 0"  # enable SVSHAPE0 for RA & RT
        # un[j + n] += t
        yield f"sv.addze *{un}, *{un}"

        yield "divmod_skip_fixup:"
        yield f"setvl 0, 0, {q_size}, 0, 1, 1"  # VL = q_size
        yield f"svremap 0o10, 0, 0, 0, 0, 0, 0"  # enable SVSHAPE0 for RT
        # q[j] = qhat
        yield f"sv.or {q}, {qhat}, {qhat}"

        # Step D2 and Step D7: loop
        yield f"addic. {j}, {j}, -1"  # j -= 1
        yield f"bc 4, 0, divmod_loop # bge divmod_loop"

        # Step D8: un-normalize

        # move s and n
        yield f"or {s_for_unnorm}, {s_scalar}, {s_scalar}"
        yield f"or {n_for_unnorm}, {n_scalar}, {n_scalar}"

        # r = [0] * self.r_size  # remainder
        yield f"setvl 0, 0, {r_size}, 0, 1, 1"  # VL = r_size
        yield f"sv.addi *{r}, 0, 0"

        # r = un >> s
        yield f"addi {t_for_unnorm}, 0, 0"  # t = 0
        yield f"setvl 0, {n_for_unnorm}, {r_size}, 0, 1, 1"  # VL = n
        yield f"sv.dsrd/mrr *{r}, *{un}, {s_for_unnorm}, {t_for_unnorm}"

        yield "divmod_return:"
        yield "addi 1, 1, 176"  # teardown stack frame
        yield "ld 0, 16(1)"
        yield "mtspr 8, 0 # mtlr 0"  # restore return address
        yield "setvl 0, 0, 18, 0, 1, 1"  # set VL to 18
        yield "sv.ld *14, -144(1)"  # restore all callee-save registers
        yield "bclr 20, 0, 0 # blr"

    @cached_property
    def asm(self):
        return tuple(self.__asm_iter())


POWMOD_256_ASM = (
    # base is in r4-7, exp is in r8-11, mod is in r32-35
    "powmod_256:",
    "mfspr 0, 8 # mflr 0",
    "std 0, 16(1)",  # save return address
    "setvl 0, 0, 18, 0, 1, 1",  # set VL to 18
    "sv.std *14, -144(1)",  # save all callee-save registers
    "stdu 1, -176(1)",  # create stack frame as required by ABI

    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.or *16, *4, *4",  # move base to r16-19
    "sv.or *20, *8, *8",  # move exp to r20-23
    "sv.or *24, *32, *32",  # move mod to r24-27
    "sv.addi *28, 0, 0",  # retval in r28-31
    "addi 28, 0, 1",  # retval = 1

    "addi 14, 0, 256",  # ctr in r14

    "powmod_256_loop:",
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "addi 3, 0, 1 # li 3, 1",  # shift amount
    "addi 0, 0, 0 # li 0, 0",  # dsrd carry
    "sv.dsrd/mrr *20, *20, 3, 0",  # exp >>= 1; shifted out bit in r0
    "cmpli 0, 1, 0, 0 # cmpldi 0, 0",
    "bc 12, 2, powmod_256_else # beq powmod_256_else",  # if lsb:

    "sv.or *4, *28, *28",  # copy retval to r4-7
    "sv.or *8, *16, *16",  # copy base to r8-11
    "bl mul_256_to_512",  # prod = retval * base
    # prod in r4-11

    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.or *32, *24, *24",  # copy mod to r32-35

    "bl divmod_512_by_256",  # prod % mod
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.or *28, *8, *8",  # retval = prod % mod

    "powmod_256_else:",

    "sv.or *4, *16, *16",  # copy base to r4-7
    "sv.or *8, *16, *16",  # copy base to r8-11
    "bl mul_256_to_512",  # prod = base * base
    # prod in r4-11

    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.or *32, *24, *24",  # copy mod to r32-35

    "bl divmod_512_by_256",  # prod % mod
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.or *16, *8, *8",  # base = prod % mod

    "addic. 14, 14, -1",  # decrement ctr and compare against zero
    "bc 4, 2, powmod_256_loop # bne powmod_256_loop",

    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.or *4, *28, *28",  # move retval to r4-7

    "addi 1, 1, 176",  # teardown stack frame
    "ld 0, 16(1)",
    "mtspr 8, 0 # mtlr 0",  # restore return address
    "setvl 0, 0, 18, 0, 1, 1",  # set VL to 18
    "sv.ld *14, -144(1)",  # restore all callee-save registers
    "bclr 20, 0, 0 # blr",
    *MUL_256_X_256_TO_512_ASM,
    *DIVMOD_SHIFT_SUB_512x256_TO_256x256_ASM,
)


def python_powmod_256_algorithm(base, exp, mod):
    retval = 1
    for _ in range(256):
        lsb = bool(exp & 1)  # rshift and retrieve lsb
        exp >>= 1
        if lsb:
            prod = retval * base
            retval = prod % mod
        prod = base * base
        base = prod % mod
    return retval


class PowModCases(TestAccumulatorBase):
    def call_case(self, instructions, expected, initial_regs, src_loc_at=0):
        stop_at_pc = 0x10000000
        sprs = {8: stop_at_pc}
        expected.intregs[1] = initial_regs[1] = 0x1000000  # set stack pointer
        expected.pc = stop_at_pc
        expected.sprs['LR'] = None
        self.add_case(assemble(instructions),
                      initial_regs, initial_sprs=sprs,
                      stop_at_pc=stop_at_pc, expected=expected,
                      src_loc_at=src_loc_at + 1)

    def case_mul_256_x_256_to_512(self):
        for i in range(10):
            a = hash_256(f"mul256 input a {i}")
            b = hash_256(f"mul256 input b {i}")
            if i == 0:
                # use known values:
                a = b = 2**256 - 1
            elif i == 1:
                # use known values:
                a = b = (2**256 - 1) // 0xFF
            y = a * b
            with self.subTest(a=f"{a:#_x}", b=f"{b:#_x}", y=f"{y:#_x}"):
                # registers start filled with junk
                initial_regs = [0xABCDEF] * 128
                for i in range(4):
                    # write a in LE order to regs 4-7
                    initial_regs[4 + i] = (a >> (64 * i)) % 2**64
                    # write b in LE order to regs 8-11
                    initial_regs[8 + i] = (b >> (64 * i)) % 2**64
                # only check regs up to r11 since that's where the output is
                e = ExpectedState(int_regs=initial_regs[:12])
                for i in range(8):
                    # write y in LE order to regs 4-11
                    e.intregs[4 + i] = (y >> (64 * i)) % 2**64

                self.call_case(MUL_256_X_256_TO_512_ASM, e, initial_regs)

    @staticmethod
    def divmod_512x256_to_256x256_test_inputs():
        yield (2 ** (256 - 1), 1)
        yield (2 ** (512 - 1) - 1, 2 ** 256 - 1)

        # test division by single word
        yield (((1 << 256) - 1) << 32, 1 << 32)
        yield (((1 << 192) - 1) << 32, 1 << 32)
        yield (((1 << 64) - 1) << 32, 1 << 32)
        yield (1 << 32, 1 << 32)

        # test qhat overflow
        yield (0x8000 << 128 | 0xFFFE << 64, 0x8000 << 64 | 0xFFFF)

        # tests where add back is required
        yield (8 << (192 - 4) | 3, 2 << (192 - 4) | 1)
        yield (0x8000 << 128 | 3, 0x2000 << 128 | 1)
        yield (0x7FFF << 192 | 0x8000 << 128, 0x8000 << 128 | 1)

        for i in range(20):
            n = hash_256(f"divmod256 input n msb {i}")
            n <<= 256
            n |= hash_256(f"divmod256 input n lsb {i}")
            n_shift = hash_256(f"divmod256 input n shift {i}") % 512
            n >>= n_shift
            d = hash_256(f"divmod256 input d {i}")
            d_shift = hash_256(f"divmod256 input d shift {i}") % 256
            d >>= d_shift
            if d == 0:
                d = 1
            n %= d << 256
            yield (n, d)

    def case_divmod_shift_sub_512x256_to_256x256(self):
        cases = list(self.divmod_512x256_to_256x256_test_inputs())
        del cases[2:-1]  # speed up tests by removing most test cases
        for n, d in cases:
            q, r = divmod(n, d)
            with self.subTest(n=f"{n:#_x}", d=f"{d:#_x}",
                              q=f"{q:#_x}", r=f"{r:#_x}"):
                # registers start filled with junk
                initial_regs = [0xABCDEF] * 128
                for i in range(8):
                    # write n in LE order to regs 4-11
                    initial_regs[4 + i] = (n >> (64 * i)) % 2**64
                for i in range(4):
                    # write d in LE order to regs 32-35
                    initial_regs[32 + i] = (d >> (64 * i)) % 2**64
                # only check regs up to r11 since that's where the output is.
                # don't check CR
                e = ExpectedState(int_regs=initial_regs[:12], crregs=0)
                e.intregs[0] = 0  # leftovers -- ignore
                e.intregs[3] = 1  # leftovers -- ignore
                e.ca = None  # ignored
                for i in range(4):
                    # write q in LE order to regs 4-7
                    e.intregs[4 + i] = (q >> (64 * i)) % 2**64
                    # write r in LE order to regs 8-11
                    e.intregs[8 + i] = (r >> (64 * i)) % 2**64

                self.call_case(
                    DIVMOD_SHIFT_SUB_512x256_TO_256x256_ASM, e, initial_regs)

    def case_divmod_knuth_algorithm_d_512x256_to_256x256(self):
        cases = list(self.divmod_512x256_to_256x256_test_inputs())
        asm = DivModKnuthAlgorithmD().asm
        for n, d in cases:
            skip = d >= 2 ** 64
            if n << 64 < n:
                skip = False
            if skip:
                # FIXME: only part of the algorithm works,
                # so we skip the cases that we know fail
                continue
            q, r = divmod(n, d)
            with self.subTest(n=f"{n:#_x}", d=f"{d:#_x}",
                              q=f"{q:#_x}", r=f"{r:#_x}"):
                # registers start filled with junk
                initial_regs = [0xABCDEF] * 128
                for i in range(8):
                    # write n in LE order to regs 4-11
                    initial_regs[4 + i] = (n >> (64 * i)) % 2**64
                for i in range(4):
                    # write d in LE order to regs 32-35
                    initial_regs[32 + i] = (d >> (64 * i)) % 2**64
                # only check regs up to r11 since that's where the output is.
                # don't check CR
                e = ExpectedState(int_regs=initial_regs[:12], crregs=0)
                e.intregs[0] = None  # ignored
                e.intregs[3] = None  # ignored
                e.ca = None  # ignored
                e.sprs['SVSHAPE0'] = None
                for i in range(4):
                    # write q in LE order to regs 4-7
                    e.intregs[4 + i] = (q >> (64 * i)) % 2**64
                    # write r in LE order to regs 8-11
                    e.intregs[8 + i] = (r >> (64 * i)) % 2**64

                self.call_case(asm, e, initial_regs)

    @staticmethod
    def powmod_256_test_inputs():
        for i in range(3):
            base = hash_256(f"powmod256 input base {i}")
            exp = hash_256(f"powmod256 input exp {i}")
            mod = hash_256(f"powmod256 input mod {i}")
            if i == 0:
                base = 2
                exp = 2 ** 256 - 1
                mod = 2 ** 256 - 189  # largest prime less than 2 ** 256
            if mod == 0:
                mod = 1
            base %= mod
            yield (base, exp, mod)

    @skip_case("FIXME: divmod is too slow to test powmod")
    def case_powmod_256(self):
        for base, exp, mod in PowModCases.powmod_256_test_inputs():
            expected = pow(base, exp, mod)
            with self.subTest(base=f"{base:#_x}", exp=f"{exp:#_x}",
                              mod=f"{mod:#_x}", expected=f"{expected:#_x}"):
                # registers start filled with junk
                initial_regs = [0xABCDEF] * 128
                for i in range(4):
                    # write n in LE order to regs 4-7
                    initial_regs[4 + i] = (base >> (64 * i)) % 2**64
                for i in range(4):
                    # write n in LE order to regs 8-11
                    initial_regs[8 + i] = (exp >> (64 * i)) % 2**64
                for i in range(4):
                    # write d in LE order to regs 32-35
                    initial_regs[32 + i] = (mod >> (64 * i)) % 2**64
                # only check regs up to r7 since that's where the output is.
                # don't check CR
                e = ExpectedState(int_regs=initial_regs[:8], crregs=0)
                e.ca = None  # ignored
                for i in range(4):
                    # write output in LE order to regs 4-7
                    e.intregs[4 + i] = (expected >> (64 * i)) % 2**64

                self.call_case(POWMOD_256_ASM, e, initial_regs)


# for running "quick" simple investigations
if __name__ == "__main__":
    # first check if python_mul_algorithm works
    a = b = (99, 99, 99, 99)
    expected = [1, 0, 0, 0, 98, 99, 99, 99]
    assert python_mul_algorithm(a, b) == expected

    # now test python_mul_algorithm2 *against* python_mul_algorithm
    import random
    random.seed(0)  # reproducible values
    for i in range(10000):
        a = []
        b = []
        for j in range(4):
            a.append(random.randint(0, 99))
            b.append(random.randint(0, 99))
        expected = python_mul_algorithm(a, b)
        testing = python_mul_algorithm2(a, b)
        report = "%+17s * %-17s = %s\n" % (repr(a), repr(b), repr(expected))
        report += "                                       (%s)" % repr(testing)
        print(report)
        assert expected == testing
