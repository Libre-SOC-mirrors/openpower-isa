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

    def cse_0_maxs(self):
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

    def cse_1_maxs(self):
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

    def cse_2_maxs_(self):
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

    def cse_3_maxs_(self):
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

    def cse_4_maxs_(self):
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

