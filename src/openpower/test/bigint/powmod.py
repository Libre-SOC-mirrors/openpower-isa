# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2023 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

""" modular exponentiation (`pow(x, y, z)`)

related bugs:

 * https://bugs.libre-soc.org/show_bug.cgi?id=1044
"""

from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.test.util import assemble
from nmutil.sim_util import hash_256


MUL_256_X_256_TO_512_ASM = [
    "mul_256_to_512:",
    # a is in r4-7, b is in r8-11
    "setvl 0, 0, 8, 0, 1, 1",  # set VL to 8
    "sv.or *12, *4, *4",  # move args to r12-19
    # a is now in r12-15, b is in r16-19
    "sv.addi *4, 0, 0",  # clear output
    "setvl 0, 0, 4, 0, 1, 1",  # set VL to 4
    "sv.maddedu *4, *12, 16, 8",  # first partial-product a * b[0]
    "addi 24, 0, 0",
    "sv.maddedu *20, *12, 17, 24",  # second partial-product a * b[1]
    "addc 5, 5, 20",
    "sv.adde *6, *6, *21",
    "addi 24, 0, 0",
    "sv.maddedu *20, *12, 18, 24",  # third partial-product a * b[2]
    "addc 6, 6, 20",
    "sv.adde *7, *7, *21",
    "addi 24, 0, 0",
    "sv.maddedu *20, *12, 19, 24",  # final partial-product a * b[3]
    "addc 7, 7, 20",
    "sv.adde *8, *8, *21",
    "bclr 20, 0, 0 # blr",
]


def _python_mul_algorithm(a, b):
    # version of the MUL_256_X_256_TO_512_ASM algorithm using base 100 rather
    # than 2^64, since that's easier to read.
    # run this file in a debugger to see all the intermediate values.
    def maddedu(a, b, c):
        y = a * b + c
        return y % 100, y // 100

    def adde(a, b, c):
        y = a + b + c
        return y % 100, y // 100

    def addc(a, b):
        y = a + b
        return y % 100, y // 100

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


class PowModCases(TestAccumulatorBase):
    def call_case(self, instructions, expected, initial_regs, src_loc_at=0):
        stop_at_pc = 0x10000000
        sprs = {8: stop_at_pc}
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

    # TODO: add 512x256-bit divrem
    # TODO: add 256-bit modular exponentiation


if __name__ == "__main__":
    a = b = 99, 99, 99, 99
    assert _python_mul_algorithm(a, b) == [1, 0, 0, 0, 98, 99, 99, 99]
