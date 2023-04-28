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
        initial_regs[1] = 0x00000a70
        initial_regs[2] = 0x0000e6b8
        initial_regs[3] = 0x00002d41

        e = ExpectedState(pc=4)
        e.intregs[1] = 0x0000aa85
        e.intregs[2] = 0xffffffffffff643e
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

