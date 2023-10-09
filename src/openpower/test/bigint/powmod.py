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
            iyl.append((iy+i, i==3))
            il.append(i)
        for i in range(5):
            iyl.append((iy+i, i==4))
            il.append(i)

    y = [0] * 8 # result y and temp t of same size
    t = [0] * 8 # no need after this to set t[4] to zero
    for iy in range(4):
        for i in range(4): # use t[iy+4] as a 64-bit carry
            t[iy+i], t[iy+4] = maddedu(a[iy], b[i], t[iy+4])
        ca = 0
        for i in range(5): # add vec t to y with 1-bit carry
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

    def __init__(self, enabled=True):
        self.__tracked = {}
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
                del self.__tracked[k]
            else:
                self.__tracked[k] = v

        gprs = [None] * 128
        for name, (start_gpr, size) in self.__tracked.items():
            value = locals_[name]
            for i in range(size):
                assert gprs[start_gpr + i] is None, "overlapping values"
                gprs[start_gpr + i] = (value >> 64 * i) % 2 ** 64

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


def python_divmod_knuth_algorithm_d(n, d, word_size=64, log_regex=False,
                                    on_corner_case=lambda desc: None):
    do_log = _DivModRegsRegexLogger(enabled=log_regex).log

    # switch to names used by Knuth's algorithm D
    u = list(n)  # dividend
    m = len(u)  # length of dividend
    v = list(d)  # divisor
    del d  # less confusing to debug
    n = len(v)  # length of divisor

    assert m >= n, "the dividend's length must be >= the divisor's length"
    assert word_size > 0

    # allocate outputs/temporaries -- before any normalization so
    # the outputs/temporaries can be fixed-length in the assembly version.

    # quotient length from original algorithm is m - n + 1,
    # but that assumes v[-1] != 0 -- since we support smaller divisors the
    # quotient must be larger.
    q = [0] * m  # quotient
    r = [0] * n  # remainder
    vn = [0] * n  # normalized divisor
    un = [0] * (m + 1)  # normalized dividend
    product = [0] * (n + 1)

    # get non-zero length of dividend
    while m > 0 and u[m - 1] == 0:
        m -= 1

    # get non-zero length of divisor
    while n > 0 and v[n - 1] == 0:
        n -= 1

    if n == 0:
        raise ZeroDivisionError

    if n == 1:
        on_corner_case("single-word divisor")
        # Knuth's algorithm D requires the divisor to have length >= 2
        # handle single-word divisors separately
        t = 0
        for i in reversed(range(m)):
            # divmod2du
            t <<= word_size
            t += u[i]
            q[i] = t // v[0]
            t %= v[0]
        r[0] = t
        return q, r

    if m < n:
        # dividend < divisor
        for i in range(m):
            r[i] = u[i]
        return q, r

    # Knuth's algorithm D starts here:

    # Step D1: normalize

    # calculate amount to shift by -- count leading zeros
    s = 0
    while (v[n - 1] << s) >> (word_size - 1) == 0:
        s += 1

    if s != 0:
        on_corner_case("non-zero shift")

    # vn = v << s
    t = 0
    for i in range(n):
        # dsld
        t |= v[i] << s
        vn[i] = t % 2 ** word_size
        t >>= word_size

    # un = u << s
    t = 0
    for i in range(m):
        # dsld
        t |= u[i] << s
        un[i] = t % 2 ** word_size
        t >>= word_size
    un[m] = t

    # Step D2 and Step D7: loop
    for j in range(m - n, -1, -1):
        # Step D3: calculate q̂

        t = un[j + n]
        t <<= word_size
        t += un[j + n - 1]
        if un[j + n] >= vn[n - 1]:
            # division overflows word
            on_corner_case("qhat overflows word")
            qhat = 2 ** word_size - 1
            rhat = t - qhat * vn[n - 1]
        else:
            # divmod2du
            qhat = t // vn[n - 1]
            rhat = t % vn[n - 1]

        while rhat < 2 ** word_size:
            if qhat * vn[n - 2] > (rhat << word_size) + un[j + n - 2]:
                on_corner_case("qhat adjustment")
                qhat -= 1
                rhat += vn[n - 1]
            else:
                break

        # Step D4: multiply and subtract

        t = 0
        for i in range(n):
            # maddedu
            t += vn[i] * qhat
            product[i] = t % 2 ** word_size
            t >>= word_size
        product[n] = t

        t = 1
        for i in range(n + 1):
            # subfe
            not_product = ~product[i] % 2 ** word_size
            t += not_product + un[j + i]
            un[j + i] = t % 2 ** word_size
            t = int(t >= 2 ** word_size)
        need_fixup = not t

        # Step D5: test remainder

        q[j] = qhat
        if need_fixup:

            # Step D6: add back

            on_corner_case("add back")

            q[j] -= 1

            t = 0
            for i in range(n):
                # adde
                t += un[j + i] + vn[i]
                un[j + i] = t % 2 ** word_size
                t = int(t >= 2 ** word_size)
            un[j + n] += t

    # Step D8: un-normalize

    # r = un >> s
    t = 0
    for i in reversed(range(n)):
        # dsrd
        t <<= word_size
        t |= (un[i] << word_size) >> s
        r[i] = t >> word_size
        t %= 2 ** word_size

    return q, r

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
