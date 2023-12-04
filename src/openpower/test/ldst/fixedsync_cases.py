# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2023 Jacob Lifshay <programmerjake@gmail.com>
# Funded by NLnet http://nlnet.nl
""" fixedsync test cases

related bugs:

* https://bugs.libre-soc.org/show_bug.cgi?id=1228
"""

from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.test.util import assemble


class FixedSyncCases(TestAccumulatorBase):
    def case_lxarx_stxcx(self):
        # TODO: test quadword instructions too
        for mnemonic, bit_width in ('b', 8), ('h', 16), ('w', 32), ('d', 64):
            with self.subTest(mnemonic=mnemonic, bit_width=bit_width):
                prog = assemble(["l%sarx 3, 4, 5, 0" % (mnemonic,),
                                "st%scx. 6, 4, 5" % (mnemonic,)])
                gprs = [0] * 32
                gprs[4] = 0x12000
                gprs[5] = 0x340
                gprs[6] = 0xD5C987D5CCD52AF2
                mem_value = 0x6E18_B505_27EA_93B9
                initial_mem = {0x12340: (0x6E18_B505_27EA_93B9, 8)}
                e = ExpectedState(pc=8, int_regs=gprs)
                e.intregs[3] = mem_value % (2 ** bit_width)
                e.crregs[0] = 0x2
                mem_value -= mem_value % (2 ** bit_width)
                mem_value += gprs[6] % (2 ** bit_width)
                e.mem = {
                    0x12340: mem_value,
                }
                self.add_case(prog, initial_regs=gprs,
                              initial_mem=initial_mem, expected=e)

    def case_lxarx_stxcx_different(self):
        # TODO: test quadword instructions too
        for mnemonic, bit_width in ('b', 8), ('h', 16), ('w', 32), ('d', 64):
            with self.subTest(mnemonic=mnemonic, bit_width=bit_width):
                prog = assemble(["l%sarx 3, 4, 5, 0" % (mnemonic,),
                                "st%scx. 6, 0, 5" % (mnemonic,)])
                gprs = [0] * 32
                gprs[4] = 0x12000
                gprs[5] = 0x340
                gprs[6] = 0xD5C987D5CCD52AF2
                mem_value = 0x6E18_B505_27EA_93B9
                initial_mem = {0x12340: (0x6E18_B505_27EA_93B9, 8)}
                e = ExpectedState(pc=8, int_regs=gprs)
                e.intregs[3] = mem_value % (2 ** bit_width)
                e.crregs[0] = 0x0
                e.mem = {
                    0x12340: mem_value,
                }
                self.add_case(prog, initial_regs=gprs,
                              initial_mem=initial_mem, expected=e)

    def case_lxarx_stxcx_stxcx(self):
        # TODO: test quadword instructions too
        for mnemonic, bit_width in ('b', 8), ('h', 16), ('w', 32), ('d', 64):
            with self.subTest(mnemonic=mnemonic, bit_width=bit_width):
                prog = assemble(["l%sarx 3, 4, 5, 0" % (mnemonic,),
                                 "st%scx. 6, 0, 5" % (mnemonic,),
                                 "st%scx. 6, 4, 5" % (mnemonic,)])
                gprs = [0] * 32
                gprs[4] = 0x12000
                gprs[5] = 0x340
                gprs[6] = 0xD5C987D5CCD52AF2
                mem_value = 0x6E18_B505_27EA_93B9
                initial_mem = {0x12340: (0x6E18_B505_27EA_93B9, 8)}
                e = ExpectedState(pc=12, int_regs=gprs)
                e.intregs[3] = mem_value % (2 ** bit_width)
                e.crregs[0] = 0x0
                e.mem = {
                    0x12340: mem_value,
                }
                self.add_case(prog, initial_regs=gprs,
                              initial_mem=initial_mem, expected=e)
