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


DIVMOD_512x256_TO_256x256_ASM = (
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


def python_divmod_algorithm(n, d, width=256, log_regex=False):
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
        for i in range(10):
            n = hash_256(f"divmod256 input n msb {i}")
            n <<= 256
            n |= hash_256(f"divmod256 input n lsb {i}")
            d = hash_256(f"divmod256 input d {i}")
            if i == 0:
                # use known values:
                n = 2 ** (256 - 1)
                d = 1
            elif i == 1:
                # use known values:
                n = 2 ** (512 - 1) - 1
                d = 2 ** 256 - 1
            if d == 0:
                d = 1
            if n >= d << 256:
                n -= d << 256
            yield (n, d)

    def case_divmod_512x256_to_256x256(self):
        for n, d in self.divmod_512x256_to_256x256_test_inputs():
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

                self.call_case(DIVMOD_512x256_TO_256x256_ASM, e, initial_regs)

    # TODO: add 256-bit modular exponentiation


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
