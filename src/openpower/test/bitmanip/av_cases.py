from openpower.sv.trans.svp64 import SVP64Asm
import random
from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.power_enums import XER_bits
from openpower.decoder.isa.caller import special_sprs
from openpower.decoder.helpers import exts
from openpower.test.state import ExpectedState
import unittest


class AVTestCase(TestAccumulatorBase):

    def case_0_maxs(self):
        lst = ["maxs 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xe1e5b9cc9864c4a8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_maxs(self):
        lst = ["maxs 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xe1e5b9cc9864c4a8
        initial_regs[2] = 0xc523e996a8ff6215
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xe1e5b9cc9864c4a8
        e.intregs[2] = 0xc523e996a8ff6215
        e.intregs[3] = 0xe1e5b9cc9864c4a8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_maxs_(self):
        lst = [f"maxs. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xe1e5b9cc9864c4a8
        e.crregs[0] = 0x8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_3_maxs_(self):
        lst = [f"maxs. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0
        e.intregs[3] = 0
        e.crregs[0] = 0x2 # RT is zero
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_4_maxs_(self):
        lst = [f"maxs. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_regs[2] = 0
        e = ExpectedState(pc=4)
        e.intregs[1] = 1
        e.intregs[2] = 0
        e.intregs[3] = 1
        e.crregs[0] = 0x4 # RT is +ve
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_5_maxs_(self):
        """max negative number compared against +ve number
        """
        lst = [f"maxs. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_regs[2] = 0x8000_0000_0000_0000
        e = ExpectedState(pc=4)
        e.intregs[1] = 1
        e.intregs[2] = 0x8000_0000_0000_0000
        e.intregs[3] = 1
        e.crregs[0] = 0x4 # RT is +ve
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_mins(self):
        lst = ["mins 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xc523e996a8ff6215
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_mins_(self):
        lst = [f"mins. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xc523e996a8ff6215
        e.crregs[0] = 0x8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_5_mins_(self):
        """min negative number compared against +ve number
        """
        lst = [f"mins. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_regs[2] = 0x8000_0000_0000_0000
        e = ExpectedState(pc=4)
        e.intregs[1] = 1
        e.intregs[2] = 0x8000_0000_0000_0000
        e.intregs[3] = 0x8000_0000_0000_0000
        e.crregs[0] = 0x8 # RT is -ve
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_maxu(self):
        lst = ["maxu 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xe1e5b9cc9864c4a8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_5_minu_(self):
        """min +ve numbers
        """
        lst = [f"minu. 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_regs[2] = 0x8000_0000_0000_0000
        e = ExpectedState(pc=4)
        e.intregs[1] = 1
        e.intregs[2] = 0x8000_0000_0000_0000
        e.intregs[3] = min(e.intregs[1], e.intregs[2])
        e.crregs[0] = 0x4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_avgadd(self):
        lst = ["avgadd 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xd384d1b1a0b2135f
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_avgadd(self):
        lst = ["avgadd 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6214
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6214
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xd384d1b1a0b2135e
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_avgadd(self):
        lst = ["avgadd 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6213
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6213
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xd384d1b1a0b2135e
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_3_avgadd(self):
        lst = ["avgadd 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        initial_regs[2] = 0xffffffffffffffff
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xffffffffffffffff
        e.intregs[2] = 0xffffffffffffffff
        e.intregs[3] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_absds(self):
        lst = ["absds 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x1
        initial_regs[2] = 0x2
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x1
        e.intregs[2] = 0x2
        e.intregs[3] = 0x1
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_absds(self):
        lst = ["absds 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        initial_regs[2] = 0x2
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xffffffffffffffff
        e.intregs[2] = 0x2
        e.intregs[3] = 0x3
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_absdu(self):
        lst = ["absdu 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x1
        initial_regs[2] = 0x2
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x1
        e.intregs[2] = 0x2
        e.intregs[3] = 0x1
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_absdu(self):
        lst = ["absdu 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        initial_regs[2] = 0x2
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xffffffffffffffff
        e.intregs[2] = 0x2
        e.intregs[3] = 0xfffffffffffffffd
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_absdu(self):
        lst = ["absdu 3, 1, 2"]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x2
        initial_regs[2] = 0xffffffffffffffff
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x2
        e.intregs[2] = 0xffffffffffffffff
        e.intregs[3] = 0xfffffffffffffffd
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_absdacu(self):
        lst = ["absdacu 3, 1, 2",
               "absdacu 3, 4, 5",
        ]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x2
        initial_regs[2] = 0x1
        initial_regs[4] = 0x9
        initial_regs[5] = 0x3
        e = ExpectedState(pc=8)
        e.intregs[1] = 0x2
        e.intregs[2] = 0x1
        e.intregs[3] = 0x7
        e.intregs[4] = 0x9
        e.intregs[5] = 0x3
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_absdacu(self):
        lst = ["absdacu 3, 1, 2",
               "absdacu 3, 4, 5",
        ]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x1
        initial_regs[2] = 0x2
        initial_regs[4] = 0x9
        initial_regs[5] = 0x3
        e = ExpectedState(pc=8)
        e.intregs[1] = 0x1
        e.intregs[2] = 0x2
        e.intregs[3] = 0x7
        e.intregs[4] = 0x9
        e.intregs[5] = 0x3
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_absdacu(self):
        """weird case where there's a negative number
        * -1 is greater than 2 (as an unsigned number)
          therefore difference is (-1)-(2) which is -3
          RT=RT+-3
            =0-3
            =-3
        * 9 is greater than 3
          therefore differences is (9)-(3) which is 6
          RT=RT+6
            =-3+6
            =3
        * answer: RT=3
        """
        lst = ["absdacu 3, 1, 2",
               "absdacu 3, 4, 5",
        ]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x2
        initial_regs[2] = 0xffffffffffffffff
        initial_regs[4] = 0x9
        initial_regs[5] = 0x3
        e = ExpectedState(pc=8)
        e.intregs[1] = 0x2
        e.intregs[2] = 0xffffffffffffffff
        e.intregs[3] = 0x3 # ((-1)-(2)) + ((9)-(3))
        e.intregs[4] = 0x9
        e.intregs[5] = 0x3
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_absdacs(self):
        lst = ["absdacs 3, 1, 2",
               "absdacs 3, 4, 5",
        ]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x2
        initial_regs[2] = 0x1
        initial_regs[4] = 0x9
        initial_regs[5] = 0x3
        e = ExpectedState(pc=8)
        e.intregs[1] = 0x2
        e.intregs[2] = 0x1
        e.intregs[3] = 0x7
        e.intregs[4] = 0x9
        e.intregs[5] = 0x3
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_absdacs(self):
        """unlike the absdacu weird case, the 0xfff is treated as signed
        so (2) < (-1) and the difference is (2--1)=3.  next instruction
        adds 6 more.  answer: 9
        """
        lst = ["absdacs 3, 1, 2",
               "absdacs 3, 4, 5",
        ]
        lst = list(SVP64Asm(lst, bigendian))

        initial_regs = [0] * 32
        initial_regs[1] = 0x2
        initial_regs[2] = 0xffffffffffffffff
        initial_regs[4] = 0x9
        initial_regs[5] = 0x3
        e = ExpectedState(pc=8)
        e.intregs[1] = 0x2
        e.intregs[2] = 0xffffffffffffffff
        e.intregs[3] = 9
        e.intregs[4] = 0x9
        e.intregs[5] = 0x3
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_cprop(self):
        lst = ["cprop 3, 1, 2" ]
        lst = list(SVP64Asm(lst, bigendian))
        last_pc = len(lst)*4
        reg_a = 0b000001
        reg_b = 0b000111
        reg_t = 0b001111

        initial_regs = [0] * 32
        initial_regs[1] = reg_a
        initial_regs[2] = reg_b
        e = ExpectedState(pc=last_pc)
        e.intregs[1] = reg_a
        e.intregs[2] = reg_b
        e.intregs[3] = reg_t
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_cprop(self):
        lst = ["cprop 3, 1, 2" ]
        lst = list(SVP64Asm(lst, bigendian))
        last_pc = len(lst)*4
        reg_a = 0b000010
        reg_b = 0b001111
        reg_t = 0b011100

        initial_regs = [0] * 32
        initial_regs[1] = reg_a
        initial_regs[2] = reg_b
        e = ExpectedState(pc=last_pc)
        e.intregs[1] = reg_a
        e.intregs[2] = reg_b
        e.intregs[3] = reg_t
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_cprop(self):
        lst = ["cprop 3, 1, 2" ]
        lst = list(SVP64Asm(lst, bigendian))
        last_pc = len(lst)*4
        reg_a = 0b000010
        reg_b = 0b001110
        reg_t = 0b011110

        initial_regs = [0] * 32
        initial_regs[1] = reg_a
        initial_regs[2] = reg_b
        e = ExpectedState(pc=last_pc)
        e.intregs[1] = reg_a
        e.intregs[2] = reg_b
        e.intregs[3] = reg_t
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_bmask(self):
        """
        https://git.libre-soc.org/?p=libreriscv.git;a=blob;f=openpower/sv/bmask.py
        https://git.libre-soc.org/?p=libreriscv.git;a=blob;f=openpower/sv/test_bmask.py
        https://git.libre-soc.org/?p=openpower-isa.git;a=blob;f=openpower/isa/av.mdwn;hb=HEAD
        SBF = 0b01010 # set before first
        SOF = 0b01001 # set only first
        SIF = 0b10000 # set including first 10011 also works no idea why yet
        """
        lst = ["bmask 3, 1, 2, 10, 0" ]
        lst = list(SVP64Asm(lst, bigendian))
        last_pc = len(lst)*4
        reg_a = 0b10010100
        reg_b = 0b11000011
        reg_t = 0b01000011

        initial_regs = [0] * 32
        initial_regs[1] = reg_a
        initial_regs[2] = reg_b
        e = ExpectedState(pc=last_pc)
        e.intregs[1] = reg_a
        e.intregs[2] = reg_b
        e.intregs[3] = reg_t
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

