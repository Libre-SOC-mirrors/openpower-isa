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

class FMVISTestCase(TestAccumulatorBase):

    def case_0_fmvis(self):
        lst = SVP64Asm(["fmvis 5, 0x4000",
                        "fmvis 6, 0x2122",
                        "fmvis 7, 0x3E80",
                       ])
        lst = list(lst)

        expected_fprs = [0] * 32
        expected_fprs[5] = 0x40000000
        expected_fprs[6] = 0x21220000
        expected_fprs[7] = 0x3E800000
        self.add_case(Program(lst, bigendian), expected_fprs)
