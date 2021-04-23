import unittest
from openpower.simulator.program import Program
from openpower.endian import bigendian

from openpower.test.common import TestAccumulatorBase
from openpower.util import mask_extend
import random


class CRTestCase(TestAccumulatorBase):

    def case_crop(self):
        insns = ["crand", "cror", "crnand", "crnor", "crxor", "creqv",
                 "crandc", "crorc"]
        for i in range(40):
            choice = random.choice(insns)
            ba = random.randint(0, 31)
            bb = random.randint(0, 31)
            bt = random.randint(0, 31)
            lst = [f"{choice} {ba}, {bb}, {bt}"]
            cr = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_crand(self):
        for i in range(20):
            lst = ["crand 0, 11, 13"]
            cr = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_1_mcrf(self):
        for i in range(20):
            src = random.randint(0, 7)
            dst = random.randint(0, 7)
            lst = [f"mcrf {src}, {dst}"]
            cr = random.randint(0, (1 << 32)-1)
        self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_0_mcrf(self):
        for i in range(8):
            lst = [f"mcrf 5, {i}"]
            cr = 0xfeff0001
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_mtcrf(self):
        for i in range(1):
            mask = random.randint(0, 255)
            lst = [f"mtcrf {mask}, 2"]
            cr = random.randint(0, (1 << 32)-1)
            initial_regs = [0] * 32
            initial_regs[2] = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_regs=initial_regs,
                          initial_cr=cr)

    def case_mtocrf(self):
        for i in range(20):
            mask = 1 << random.randint(0, 7)
            lst = [f"mtocrf {mask}, 2"]
            cr = random.randint(0, (1 << 32)-1)
            initial_regs = [0] * 32
            initial_regs[2] = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_regs=initial_regs,
                          initial_cr=cr)

    def case_mfcr(self):
        for i in range(1):
            lst = ["mfcr 2"]
            cr = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_cror_regression(self):
        """another bad hack!
        """
        dis = ["cror 28, 5, 11"]
        lst = bytes([0x83, 0x5b, 0x75, 0x4f]) # 4f855b83
        cr = 0x35055058
        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_cr=cr)

    def case_mfocrf_regression(self):
        """bit of a bad hack.  comes from microwatt 1.bin instruction 0x106d0
        as the mask is non-standard, gnu-as barfs.  so we fake it up directly
        from the binary
        """
        mask = 0b10000111
        dis = [f"mfocrf 2, {mask}"]
        lst = bytes([0x26, 0x78, 0xb8, 0x7c]) # 0x7cb87826
        cr = 0x5F9E080E
        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_cr=cr)

    def case_mtocrf_regression(self):
        """microwatt 1.bin regression, same hack as above.
           106b4:   21 d9 96 7d     .long 0x7d96d921   # mtocrf 12, 0b01101101
        """
        mask = 0b01101101
        dis = [f"mtocrf 12, {mask}"]
        lst = bytes([0x21, 0xd9, 0x96, 0x7d]) # 0x7d96d921
        cr = 0x529e08fe
        initial_regs = [0] * 32
        initial_regs[12] = 0xffffffffffffffff
        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_regs=initial_regs, initial_cr=cr)

    def case_mtocrf_regression_2(self):
        """microwatt 1.bin regression, zero fxm
           mtocrf 0,16     14928:   21 09 10 7e     .long 0x7e100921
        """
        dis = ["mtocrf 16, 0"]
        lst = bytes([0x21, 0x09, 0x10, 0x7e]) # 0x7e100921
        cr = 0x3F089F7F
        initial_regs = [0] * 32
        initial_regs[16] = 0x0001C020
        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_regs=initial_regs, initial_cr=cr)

    def case_mfocrf_1(self):
        lst = [f"mfocrf 2, 1"]
        cr = 0x1234
        self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_mfocrf(self):
        for i in range(1):
            mask = 1 << random.randint(0, 7)
            lst = [f"mfocrf 2, {mask}"]
            cr = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_isel_0(self):
        lst = [ "isel 4, 1, 2, 31"
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x1004
        initial_regs[2] = 0x1008
        cr= 0x1ee
        self.add_case(Program(lst, bigendian),
                      initial_regs=initial_regs, initial_cr=cr)

    def case_isel_1(self):
        lst = [ "isel 4, 1, 2, 30"
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x1004
        initial_regs[2] = 0x1008
        cr= 0x1ee
        self.add_case(Program(lst, bigendian),
                      initial_regs=initial_regs, initial_cr=cr)

    def case_isel_2(self):
        lst = [ "isel 4, 1, 2, 2"
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x1004
        initial_regs[2] = 0x1008
        cr= 0x1ee
        self.add_case(Program(lst, bigendian),
                      initial_regs=initial_regs, initial_cr=cr)

    def case_isel_3(self):
        lst = [ "isel 1, 2, 3, 13"
               ]
        initial_regs = [0] * 32
        initial_regs[2] = 0x1004
        initial_regs[3] = 0x1008
        cr= 0x5d677571b8229f1
        cr= 0x1b8229f1
        self.add_case(Program(lst, bigendian),
                      initial_regs=initial_regs, initial_cr=cr)

    def case_isel(self):
        for i in range(20):
            bc = random.randint(0, 31)
            lst = [f"isel 1, 2, 3, {bc}"]
            cr = random.randint(0, (1 << 64)-1)
            initial_regs = [0] * 32
            #initial_regs[2] = random.randint(0, (1 << 64)-1)
            #initial_regs[3] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = i*2+1
            initial_regs[3] = i*2+2
            self.add_case(Program(lst, bigendian),
                          initial_regs=initial_regs, initial_cr=cr)

    def case_setb(self):
        for i in range(20):
            bfa = random.randint(0, 7)
            lst = [f"setb 1, {bfa}"]
            cr = random.randint(0, (1 << 32)-1)
            self.add_case(Program(lst, bigendian), initial_cr=cr)

    def case_regression_setb(self):
        lst = [f"setb 1, 6"]
        cr = random.randint(0, 0x66f6b106)
        self.add_case(Program(lst, bigendian), initial_cr=cr)

