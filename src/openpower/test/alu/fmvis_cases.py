from openpower.insndb.asm import SVP64Asm
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
        lst = SVP64Asm(["fmvis 5, 0x4000", # 2.0
                        "fmvis 6, 0x4048", # 3.125
                        "fmvis 7, 0x3E80", # 0.25
                        "fmvis 8, 0xc048", # -3.125
                       ])
        lst = list(lst)

        expected_fprs = [0] * 32 
        expected_fprs[5] = 0x4000000000000000 # 2.0 in FP64 form
        expected_fprs[6] = 0x4009000000000000 # 3.125 in FP64 form
        expected_fprs[7] = 0x3FD0000000000000 # 0.25 in FP64 form
        expected_fprs[8] = 0xC009000000000000 # -3.125 in FP64 form
        e = ExpectedState(pc=0x10, # 4 instructions so 4x4=0x10
                          fp_regs=expected_fprs) # expected results
        self.add_case(Program(lst, bigendian), expected=e)

    def case_1_fishmv(self):

        lst = SVP64Asm(["fmvis  3, 0x4049",  # 1st half of 3.14159 in FP32 form
                        "fishmv 3, 0x0FD0",  # 2nd half of 3.14159 in FP32 form
                        "fmvis  4, 0x3F80",  # 1st half of 1.00195 in FP32 form
                        "fishmv 4, 0x4000",  # 2nd half of 1.00195 in FP32 form
                        "fmvis  5, 0xC049",  # 1st half of -3.14159 in FP32 form
                        "fishmv 5, 0x0FD0",  # 2nd half of -3.14159 in FP32 form
                        "fmvis  6, 0x89AB",  # 1st half of 0x89ABCDEF in FP32 form
                        "fishmv 6, 0xCDEF",  # 2nd half of 0x89ABCDEF in FP32 form
                       ])
        lst = list(lst)

        expected_fprs = [0] * 32
        expected_fprs[3] = 0x400921fa00000000 # 3.14159 in FP64 form
        expected_fprs[4] = 0x3ff0080000000000 # 1.00195 in FP64 form
        expected_fprs[5] = 0xC00921fa00000000 # -3.14159 in FP64 form
        expected_fprs[6] = 0xB93579BDE0000000 # converted value in FP64 form
        e = ExpectedState(pc=0x20, fp_regs=expected_fprs)
        self.add_case(Program(lst, bigendian), expected=e)
