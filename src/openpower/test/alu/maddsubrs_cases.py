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

class MADDSUBRSTestCase(TestAccumulatorBase):

    def case_0_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,2,14,3"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[2] = 0x0000e6b8
        initial_regs[3] = 0x00002d41

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x0000aa86
        e.intregs[2] = 0xffffffffffff643e
        e.intregs[3] = 0x00002d41
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_1_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,2,0,3"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x00000a71
        initial_regs[2] = 0x0000e6b8
        initial_regs[3] = 0x00002d41

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x2aa17069
        e.intregs[2] = 0xffffffffd90f96f9
        e.intregs[3] = 0x00002d41
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,2,2,3"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x100000000
        initial_regs[2] = 0x000000003
        initial_regs[3] = 0x10000000

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x40000000c000000;
        e.intregs[2] = 0x3fffffff4000000;
        e.intregs[3] = 0x10000000;
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_3_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,2,16,3"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x100000000
        initial_regs[2] = 0x000000003
        initial_regs[3] = 0x10000000

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x100000003000;
        e.intregs[2] = 0x0fffffffd000;
        e.intregs[3] = 0x10000000;
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_3_maddsubrs(self):
        isa = SVP64Asm(["maddsubrs 1,2,1,3"])
        lst = list(isa)

        initial_regs = [0] * 32
        initial_regs[1] = 0x100000000
        initial_regs[2] = 0x000000003
        initial_regs[3] = 0xff0000000

        e = ExpectedState(pc=4)
        e.intregs[1] = 0xf8000017e8000000;
        e.intregs[2] = 0xf7ffffe818000000;
        e.intregs[3] = 0xff0000000;
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)
