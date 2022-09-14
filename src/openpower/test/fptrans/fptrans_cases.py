from openpower.test.common import TestAccumulatorBase
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
import struct


# FIXME: output values are just what my computer produces for the current
# simulator, they are probably not all correct.


class FPTransCases(TestAccumulatorBase):
    def case_fatan2s(self):
        lst = list(SVP64Asm(["fatan2s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb60000000  # pi/4 as f32 as f64
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2s_(self):
        lst = list(SVP64Asm(["fatan2s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb60000000  # pi/4 as f32 as f64
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2(self):
        lst = list(SVP64Asm(["fatan2 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb54442d18
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2_(self):
        lst = list(SVP64Asm(["fatan2. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb54442d18
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2pis(self):
        lst = list(SVP64Asm(["fatan2pis 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2pis_(self):
        lst = list(SVP64Asm(["fatan2pis. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2pi(self):
        lst = list(SVP64Asm(["fatan2pi 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan2pi_(self):
        lst = list(SVP64Asm(["fatan2pi. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpows(self):
        lst = list(SVP64Asm(["fpows 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpows_(self):
        lst = list(SVP64Asm(["fpows. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpow(self):
        lst = list(SVP64Asm(["fpow 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpow_(self):
        lst = list(SVP64Asm(["fpow. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpowns(self):
        lst = list(SVP64Asm(["fpowns 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpowns_(self):
        lst = list(SVP64Asm(["fpowns. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpown(self):
        lst = list(SVP64Asm(["fpown 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpown_(self):
        lst = list(SVP64Asm(["fpown. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpowrs(self):
        lst = list(SVP64Asm(["fpowrs 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpowrs_(self):
        lst = list(SVP64Asm(["fpowrs. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpowr(self):
        lst = list(SVP64Asm(["fpowr 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fpowr_(self):
        lst = list(SVP64Asm(["fpowr. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frootns(self):
        lst = list(SVP64Asm(["frootns 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frootns_(self):
        lst = list(SVP64Asm(["frootns. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frootn(self):
        lst = list(SVP64Asm(["frootn 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frootn_(self):
        lst = list(SVP64Asm(["frootn. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        gprs[5] = 3
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fhypots(self):
        lst = list(SVP64Asm(["fhypots 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff6a09e60000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fhypots_(self):
        lst = list(SVP64Asm(["fhypots. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff6a09e60000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fhypot(self):
        lst = list(SVP64Asm(["fhypot 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff6a09e667f3bcd
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fhypot_(self):
        lst = list(SVP64Asm(["fhypot. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff6a09e667f3bcd
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frsqrts(self):
        lst = list(SVP64Asm(["frsqrts 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frsqrts_(self):
        lst = list(SVP64Asm(["frsqrts. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frsqrt(self):
        lst = list(SVP64Asm(["frsqrt 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frsqrt_(self):
        lst = list(SVP64Asm(["frsqrt. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcbrts(self):
        lst = list(SVP64Asm(["fcbrts 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcbrts_(self):
        lst = list(SVP64Asm(["fcbrts. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcbrt(self):
        lst = list(SVP64Asm(["fcbrt 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcbrt_(self):
        lst = list(SVP64Asm(["fcbrt. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frecips(self):
        lst = list(SVP64Asm(["frecips 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frecips_(self):
        lst = list(SVP64Asm(["frecips. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frecip(self):
        lst = list(SVP64Asm(["frecip 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_frecip_(self):
        lst = list(SVP64Asm(["frecip. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2m1s(self):
        lst = list(SVP64Asm(["fexp2m1s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2m1s_(self):
        lst = list(SVP64Asm(["fexp2m1s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2m1(self):
        lst = list(SVP64Asm(["fexp2m1 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2m1_(self):
        lst = list(SVP64Asm(["fexp2m1. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2p1s(self):
        lst = list(SVP64Asm(["flog2p1s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2p1s_(self):
        lst = list(SVP64Asm(["flog2p1s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2p1(self):
        lst = list(SVP64Asm(["flog2p1 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2p1_(self):
        lst = list(SVP64Asm(["flog2p1. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2s(self):
        lst = list(SVP64Asm(["fexp2s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4000000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2s_(self):
        lst = list(SVP64Asm(["fexp2s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4000000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2(self):
        lst = list(SVP64Asm(["fexp2 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4000000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp2_(self):
        lst = list(SVP64Asm(["fexp2. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4000000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2s(self):
        lst = list(SVP64Asm(["flog2s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2s_(self):
        lst = list(SVP64Asm(["flog2s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2(self):
        lst = list(SVP64Asm(["flog2 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog2_(self):
        lst = list(SVP64Asm(["flog2. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexpm1s(self):
        lst = list(SVP64Asm(["fexpm1s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ffb7e1520000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexpm1s_(self):
        lst = list(SVP64Asm(["fexpm1s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ffb7e1520000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexpm1(self):
        lst = list(SVP64Asm(["fexpm1 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ffb7e151628aed2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexpm1_(self):
        lst = list(SVP64Asm(["fexpm1. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ffb7e151628aed2
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flogp1s(self):
        lst = list(SVP64Asm(["flogp1s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe62e4300000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flogp1s_(self):
        lst = list(SVP64Asm(["flogp1s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe62e4300000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flogp1(self):
        lst = list(SVP64Asm(["flogp1 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe62e42fefa39ef
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flogp1_(self):
        lst = list(SVP64Asm(["flogp1. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe62e42fefa39ef
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexps(self):
        lst = list(SVP64Asm(["fexps 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4005bf0a80000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexps_(self):
        lst = list(SVP64Asm(["fexps. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4005bf0a80000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp(self):
        lst = list(SVP64Asm(["fexp 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4005bf0a8b145769
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp_(self):
        lst = list(SVP64Asm(["fexp. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4005bf0a8b145769
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flogs(self):
        lst = list(SVP64Asm(["flogs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flogs_(self):
        lst = list(SVP64Asm(["flogs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog(self):
        lst = list(SVP64Asm(["flog 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog_(self):
        lst = list(SVP64Asm(["flog. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10m1s(self):
        lst = list(SVP64Asm(["fexp10m1s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4022000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10m1s_(self):
        lst = list(SVP64Asm(["fexp10m1s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4022000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10m1(self):
        lst = list(SVP64Asm(["fexp10m1 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4022000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10m1_(self):
        lst = list(SVP64Asm(["fexp10m1. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4022000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10p1s(self):
        lst = list(SVP64Asm(["flog10p1s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd3441360000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10p1s_(self):
        lst = list(SVP64Asm(["flog10p1s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd3441360000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10p1(self):
        lst = list(SVP64Asm(["flog10p1 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd34413509f79ff
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10p1_(self):
        lst = list(SVP64Asm(["flog10p1. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd34413509f79ff
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10s(self):
        lst = list(SVP64Asm(["fexp10s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4024000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10s_(self):
        lst = list(SVP64Asm(["fexp10s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4024000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10(self):
        lst = list(SVP64Asm(["fexp10 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4024000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fexp10_(self):
        lst = list(SVP64Asm(["fexp10. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x4024000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10s(self):
        lst = list(SVP64Asm(["flog10s 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10s_(self):
        lst = list(SVP64Asm(["flog10s. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10(self):
        lst = list(SVP64Asm(["flog10 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_flog10_(self):
        lst = list(SVP64Asm(["flog10. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsins(self):
        lst = list(SVP64Asm(["fsins 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3feaed5480000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsins_(self):
        lst = list(SVP64Asm(["fsins. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3feaed5480000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsin(self):
        lst = list(SVP64Asm(["fsin 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3feaed548f090cee
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsin_(self):
        lst = list(SVP64Asm(["fsin. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3feaed548f090cee
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcoss(self):
        lst = list(SVP64Asm(["fcoss 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe14a2800000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcoss_(self):
        lst = list(SVP64Asm(["fcoss. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe14a2800000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcos(self):
        lst = list(SVP64Asm(["fcos 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe14a280fb5068c
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcos_(self):
        lst = list(SVP64Asm(["fcos. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe14a280fb5068c
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftans(self):
        lst = list(SVP64Asm(["ftans 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8eb2460000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftans_(self):
        lst = list(SVP64Asm(["ftans. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8eb2460000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftan(self):
        lst = list(SVP64Asm(["ftan 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8eb245cbee3a6
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftan_(self):
        lst = list(SVP64Asm(["ftan. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8eb245cbee3a6
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasins(self):
        lst = list(SVP64Asm(["fasins 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff921fb60000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasins_(self):
        lst = list(SVP64Asm(["fasins. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff921fb60000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasin(self):
        lst = list(SVP64Asm(["fasin 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff921fb54442d18
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasin_(self):
        lst = list(SVP64Asm(["fasin. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff921fb54442d18
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facoss(self):
        lst = list(SVP64Asm(["facoss 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facoss_(self):
        lst = list(SVP64Asm(["facoss. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facos(self):
        lst = list(SVP64Asm(["facos 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facos_(self):
        lst = list(SVP64Asm(["facos. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatans(self):
        lst = list(SVP64Asm(["fatans 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb60000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatans_(self):
        lst = list(SVP64Asm(["fatans. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb60000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan(self):
        lst = list(SVP64Asm(["fatan 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb54442d18
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatan_(self):
        lst = list(SVP64Asm(["fatan. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe921fb54442d18
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinpis(self):
        lst = list(SVP64Asm(["fsinpis 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinpis_(self):
        lst = list(SVP64Asm(["fsinpis. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinpi(self):
        lst = list(SVP64Asm(["fsinpi 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinpi_(self):
        lst = list(SVP64Asm(["fsinpi. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcospis(self):
        lst = list(SVP64Asm(["fcospis 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xbff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcospis_(self):
        lst = list(SVP64Asm(["fcospis. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xbff0000000000000
        e.crregs[1] = 0x8
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcospi(self):
        lst = list(SVP64Asm(["fcospi 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xbff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcospi_(self):
        lst = list(SVP64Asm(["fcospi. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0xbff0000000000000
        e.crregs[1] = 0x8
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanpis(self):
        lst = list(SVP64Asm(["ftanpis 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fc0000000000000  # 0.125
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fda8279a0000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanpis_(self):
        lst = list(SVP64Asm(["ftanpis. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fc0000000000000  # 0.125
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fda8279a0000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanpi(self):
        lst = list(SVP64Asm(["ftanpi 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fc0000000000000  # 0.125
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fda827999fcef32
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanpi_(self):
        lst = list(SVP64Asm(["ftanpi. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fc0000000000000  # 0.125
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fda827999fcef32
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinpis(self):
        lst = list(SVP64Asm(["fasinpis 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinpis_(self):
        lst = list(SVP64Asm(["fasinpis. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinpi(self):
        lst = list(SVP64Asm(["fasinpi 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinpi_(self):
        lst = list(SVP64Asm(["fasinpi. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facospis(self):
        lst = list(SVP64Asm(["facospis 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facospis_(self):
        lst = list(SVP64Asm(["facospis. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facospi(self):
        lst = list(SVP64Asm(["facospi 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facospi_(self):
        lst = list(SVP64Asm(["facospi. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanpis(self):
        lst = list(SVP64Asm(["fatanpis 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanpis_(self):
        lst = list(SVP64Asm(["fatanpis. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanpi(self):
        lst = list(SVP64Asm(["fatanpi 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanpi_(self):
        lst = list(SVP64Asm(["fatanpi. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fd0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinhs(self):
        lst = list(SVP64Asm(["fsinhs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff2cd9fc0000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinhs_(self):
        lst = list(SVP64Asm(["fsinhs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff2cd9fc0000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinh(self):
        lst = list(SVP64Asm(["fsinh 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff2cd9fc44eb982
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fsinh_(self):
        lst = list(SVP64Asm(["fsinh. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff2cd9fc44eb982
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcoshs(self):
        lst = list(SVP64Asm(["fcoshs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8b07560000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcoshs_(self):
        lst = list(SVP64Asm(["fcoshs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8b07560000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcosh(self):
        lst = list(SVP64Asm(["fcosh 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8b07551d9f550
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fcosh_(self):
        lst = list(SVP64Asm(["fcosh. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff8b07551d9f550
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanhs(self):
        lst = list(SVP64Asm(["ftanhs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe85efac0000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanhs_(self):
        lst = list(SVP64Asm(["ftanhs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe85efac0000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanh(self):
        lst = list(SVP64Asm(["ftanh 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe85efab514f394
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_ftanh_(self):
        lst = list(SVP64Asm(["ftanh. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe85efab514f394
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinhs(self):
        lst = list(SVP64Asm(["fasinhs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fec343660000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinhs_(self):
        lst = list(SVP64Asm(["fasinhs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fec343660000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinh(self):
        lst = list(SVP64Asm(["fasinh 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fec34366179d427
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fasinh_(self):
        lst = list(SVP64Asm(["fasinh. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fec34366179d427
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facoshs(self):
        lst = list(SVP64Asm(["facoshs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facoshs_(self):
        lst = list(SVP64Asm(["facoshs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facosh(self):
        lst = list(SVP64Asm(["facosh 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_facosh_(self):
        lst = list(SVP64Asm(["facosh. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanhs(self):
        lst = list(SVP64Asm(["fatanhs 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe193ea80000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanhs_(self):
        lst = list(SVP64Asm(["fatanhs. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe193ea80000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanh(self):
        lst = list(SVP64Asm(["fatanh 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe193ea7aad030a
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fatanh_(self):
        lst = list(SVP64Asm(["fatanh. 3,4"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3fe0000000000000  # 0.5
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3fe193ea7aad030a
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum08s(self):
        lst = list(SVP64Asm(["fminnum08s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum08s_(self):
        lst = list(SVP64Asm(["fminnum08s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum08(self):
        lst = list(SVP64Asm(["fminnum08 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum08_(self):
        lst = list(SVP64Asm(["fminnum08. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum08s(self):
        lst = list(SVP64Asm(["fmaxnum08s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum08s_(self):
        lst = list(SVP64Asm(["fmaxnum08s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum08(self):
        lst = list(SVP64Asm(["fmaxnum08 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum08_(self):
        lst = list(SVP64Asm(["fmaxnum08. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmin19s(self):
        lst = list(SVP64Asm(["fmin19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmin19s_(self):
        lst = list(SVP64Asm(["fmin19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmin19(self):
        lst = list(SVP64Asm(["fmin19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmin19_(self):
        lst = list(SVP64Asm(["fmin19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmax19s(self):
        lst = list(SVP64Asm(["fmax19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmax19s_(self):
        lst = list(SVP64Asm(["fmax19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmax19(self):
        lst = list(SVP64Asm(["fmax19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmax19_(self):
        lst = list(SVP64Asm(["fmax19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum19s(self):
        lst = list(SVP64Asm(["fminnum19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum19s_(self):
        lst = list(SVP64Asm(["fminnum19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum19(self):
        lst = list(SVP64Asm(["fminnum19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminnum19_(self):
        lst = list(SVP64Asm(["fminnum19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum19s(self):
        lst = list(SVP64Asm(["fmaxnum19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum19s_(self):
        lst = list(SVP64Asm(["fmaxnum19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum19(self):
        lst = list(SVP64Asm(["fmaxnum19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxnum19_(self):
        lst = list(SVP64Asm(["fmaxnum19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmincs(self):
        lst = list(SVP64Asm(["fmincs 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmincs_(self):
        lst = list(SVP64Asm(["fmincs. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminc(self):
        lst = list(SVP64Asm(["fminc 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminc_(self):
        lst = list(SVP64Asm(["fminc. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxcs(self):
        lst = list(SVP64Asm(["fmaxcs 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxcs_(self):
        lst = list(SVP64Asm(["fmaxcs. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxc(self):
        lst = list(SVP64Asm(["fmaxc 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxc_(self):
        lst = list(SVP64Asm(["fmaxc. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum08s(self):
        lst = list(SVP64Asm(["fminmagnum08s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum08s_(self):
        lst = list(SVP64Asm(["fminmagnum08s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum08(self):
        lst = list(SVP64Asm(["fminmagnum08 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum08_(self):
        lst = list(SVP64Asm(["fminmagnum08. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum08s(self):
        lst = list(SVP64Asm(["fmaxmagnum08s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum08s_(self):
        lst = list(SVP64Asm(["fmaxmagnum08s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum08(self):
        lst = list(SVP64Asm(["fmaxmagnum08 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum08_(self):
        lst = list(SVP64Asm(["fmaxmagnum08. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmag19s(self):
        lst = list(SVP64Asm(["fminmag19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmag19s_(self):
        lst = list(SVP64Asm(["fminmag19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmag19(self):
        lst = list(SVP64Asm(["fminmag19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmag19_(self):
        lst = list(SVP64Asm(["fminmag19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmag19s(self):
        lst = list(SVP64Asm(["fmaxmag19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmag19s_(self):
        lst = list(SVP64Asm(["fmaxmag19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmag19(self):
        lst = list(SVP64Asm(["fmaxmag19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmag19_(self):
        lst = list(SVP64Asm(["fmaxmag19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum19s(self):
        lst = list(SVP64Asm(["fminmagnum19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum19s_(self):
        lst = list(SVP64Asm(["fminmagnum19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum19(self):
        lst = list(SVP64Asm(["fminmagnum19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagnum19_(self):
        lst = list(SVP64Asm(["fminmagnum19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum19s(self):
        lst = list(SVP64Asm(["fmaxmagnum19s 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum19s_(self):
        lst = list(SVP64Asm(["fmaxmagnum19s. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum19(self):
        lst = list(SVP64Asm(["fmaxmagnum19 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagnum19_(self):
        lst = list(SVP64Asm(["fmaxmagnum19. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagcs(self):
        lst = list(SVP64Asm(["fminmagcs 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagcs_(self):
        lst = list(SVP64Asm(["fminmagcs. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagc(self):
        lst = list(SVP64Asm(["fminmagc 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fminmagc_(self):
        lst = list(SVP64Asm(["fminmagc. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagcs(self):
        lst = list(SVP64Asm(["fmaxmagcs 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagcs_(self):
        lst = list(SVP64Asm(["fmaxmagcs. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagc(self):
        lst = list(SVP64Asm(["fmaxmagc 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmaxmagc_(self):
        lst = list(SVP64Asm(["fmaxmagc. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x3ff0000000000000
        e.crregs[1] = 0x4
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmods(self):
        lst = list(SVP64Asm(["fmods 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmods_(self):
        lst = list(SVP64Asm(["fmods. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmod(self):
        lst = list(SVP64Asm(["fmod 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fmod_(self):
        lst = list(SVP64Asm(["fmod. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fremainders(self):
        lst = list(SVP64Asm(["fremainders 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fremainders_(self):
        lst = list(SVP64Asm(["fremainders. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fremainder(self):
        lst = list(SVP64Asm(["fremainder 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)

    def case_fremainder_(self):
        lst = list(SVP64Asm(["fremainder. 3,4,5"]))
        gprs = [0] * 32
        fprs = [0] * 32
        fprs[4] = 0x3ff0000000000000  # 1.0
        fprs[5] = 0x3ff0000000000000  # 1.0
        e = ExpectedState(pc=4, int_regs=gprs, fp_regs=fprs)
        e.fpregs[3] = 0x0
        e.crregs[1] = 0x2
        self.add_case(Program(lst, False), gprs, fpregs=fprs, expected=e)


class SVP64FPTransCases(TestAccumulatorBase):
    def case_sv_fatan2pi(self):
        lst = list(SVP64Asm(["sv.fatan2pi *32,*64,*96"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        r = range(svstate.vl)
        for i, rev_i in zip(r, reversed(r)):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i))[0]
            fprs[96 + i] = struct.unpack("<Q", struct.pack("<d", rev_i))[0]
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x0
        e.fpregs[33] = 0x3f85b8cf3bae0f6f
        e.fpregs[34] = 0x3f96719808aca26c
        e.fpregs[35] = 0x3fa1652c7df3f5c4
        e.fpregs[36] = 0x3fa7f854e2212de9
        e.fpregs[37] = 0x3faef699518cc00c
        e.fpregs[38] = 0x3fb331a583506fb4
        e.fpregs[39] = 0x3fb72028ecef9844
        e.fpregs[40] = 0x3fbb46dd1ce460e0
        e.fpregs[41] = 0x3fbfa49f4f32b679
        e.fpregs[42] = 0x3fc21b75e3b0004e
        e.fpregs[43] = 0x3fc47cd84e0cb544
        e.fpregs[44] = 0x3fc6f39a0b860052
        e.fpregs[45] = 0x3fc97c0bade66a98
        e.fpregs[46] = 0x3fcc11bdf5480ae5
        e.fpregs[47] = 0x3fceafa71eebf23b
        e.fpregs[48] = 0x3fd0a82c708a06e3
        e.fpregs[49] = 0x3fd1f721055bfa8d
        e.fpregs[50] = 0x3fd341fa290ccab4
        e.fpregs[51] = 0x3fd48632fa3cffd8
        e.fpregs[52] = 0x3fd5c193d8f9a55f
        e.fpregs[53] = 0x3fd6f2450e27ffd9
        e.fpregs[54] = 0x3fd816d82c335262
        e.fpregs[55] = 0x3fd92e48b8c6e7c8
        e.fpregs[56] = 0x3fda37f5c4c419ef
        e.fpregs[57] = 0x3fdb33969f2be413
        e.fpregs[58] = 0x3fdc212cd5ce67ff
        e.fpregs[59] = 0x3fdd00f563bbda43
        e.fpregs[60] = 0x3fddd35a70418148
        e.fpregs[61] = 0x3fde98e67f7535d9
        e.fpregs[62] = 0x3fdf523986228f84
        e.fpregs[63] = 0x3fe0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_fpown(self):
        lst = list(SVP64Asm(["sv.fpown *32,*64,*96"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        r = range(svstate.vl)
        for i, rev_i in zip(r, reversed(r)):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i))[0]
            gprs[96 + i] = rev_i
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x0
        e.fpregs[33] = 0x3ff0000000000000
        e.fpregs[34] = 0x41c0000000000000
        e.fpregs[35] = 0x42b4ce6b167f3100
        e.fpregs[36] = 0x4350000000000000
        e.fpregs[37] = 0x43b4adf4b7320335
        e.fpregs[38] = 0x43f8a8cac5546000
        e.fpregs[39] = 0x4424c57285ccad29
        e.fpregs[40] = 0x4440000000000000
        e.fpregs[41] = 0x444ab13886ff818c
        e.fpregs[42] = 0x444b1ae4d6e2ef50
        e.fpregs[43] = 0x44423c240e01248b
        e.fpregs[44] = 0x443151acf6c00000
        e.fpregs[45] = 0x44186287733beda8
        e.fpregs[46] = 0x43fa727064cdd0e0
        e.fpregs[47] = 0x43d6c9eb264f7e5e
        e.fpregs[48] = 0x43b0000000000000
        e.fpregs[49] = 0x4382b195ede100df
        e.fpregs[50] = 0x43527e9813ff4800
        e.fpregs[51] = 0x431f73fe261ba8c4
        e.fpregs[52] = 0x42e74876e8000000
        e.fpregs[53] = 0x42ae572cc2de3200
        e.fpregs[54] = 0x4271916da5600000
        e.fpregs[55] = 0x42323bb2ce410000
        e.fpregs[56] = 0x41f1160000000000
        e.fpregs[57] = 0x41ad1a94a2000000
        e.fpregs[58] = 0x4166a97400000000
        e.fpregs[59] = 0x412037e200000000
        e.fpregs[60] = 0x40d5700000000000
        e.fpregs[61] = 0x408a480000000000
        e.fpregs[62] = 0x403e000000000000
        e.fpregs[63] = 0x3ff0000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_frootn(self):
        lst = list(SVP64Asm(["sv.frootn *32,*64,*96"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        r = range(svstate.vl)
        for i, rev_i in zip(r, reversed(r)):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i))[0]
            gprs[96 + i] = rev_i + 1
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x0
        e.fpregs[33] = 0x3ff0000000000000
        e.fpregs[34] = 0x3ff05fbd4d5b4d5a
        e.fpregs[35] = 0x3ff09e2569889351
        e.fpregs[36] = 0x3ff0cfe6317120a2
        e.fpregs[37] = 0x3ff0fb94d925b492
        e.fpregs[38] = 0x3ff124397bbd71d1
        e.fpregs[39] = 0x3ff14b8dd4dbe8ef
        e.fpregs[40] = 0x3ff172b83c7d517b
        e.fpregs[41] = 0x3ff19a98e90823cd
        e.fpregs[42] = 0x3ff1c3f003e174f7
        e.fpregs[43] = 0x3ff1ef73c93abb21
        e.fpregs[44] = 0x3ff21ddfeba4e8fd
        e.fpregs[45] = 0x3ff250029ab74d74
        e.fpregs[46] = 0x3ff286c9c55d5e76
        e.fpregs[47] = 0x3ff2c352ac749326
        e.fpregs[48] = 0x3ff306fe0a31b715
        e.fpregs[49] = 0x3ff3538be101623e
        e.fpregs[50] = 0x3ff3ab43a7d494dc
        e.fpregs[51] = 0x3ff41130952e3b5e
        e.fpregs[52] = 0x3ff4897f7b709b03
        e.fpregs[53] = 0x3ff51a16addd4cea
        e.fpregs[54] = 0x3ff5cb96ce4d114c
        e.fpregs[55] = 0x3ff6ab23d0cbc00b
        e.fpregs[56] = 0x3ff7cdc62dc660be
        e.fpregs[57] = 0x3ff957533ae6a7d2
        e.fpregs[58] = 0x3ffb89fed8923714
        e.fpregs[59] = 0x3ffeee504bc32425
        e.fpregs[60] = 0x40026711a672020b
        e.fpregs[61] = 0x4008941ad80a2b83
        e.fpregs[62] = 0x4015e8add236a58f
        e.fpregs[63] = 0x403f000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_fsinpi(self):
        lst = list(SVP64Asm(["sv.fsinpi *32,*64"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        for i in range(svstate.vl):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i / 4))[0]
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x0
        e.fpregs[33] = 0x3fe6a09e667f3bcc
        e.fpregs[34] = 0x3ff0000000000000
        e.fpregs[35] = 0x3fe6a09e667f3bcd
        e.fpregs[36] = 0x3ca1a62633145c07
        e.fpregs[37] = 0xbfe6a09e667f3bcc
        e.fpregs[38] = 0xbff0000000000000
        e.fpregs[39] = 0xbfe6a09e667f3bce
        e.fpregs[40] = 0xbcb1a62633145c07
        e.fpregs[41] = 0x3fe6a09e667f3bcb
        e.fpregs[42] = 0x3ff0000000000000
        e.fpregs[43] = 0x3fe6a09e667f3bd4
        e.fpregs[44] = 0x3cba79394c9e8a0a
        e.fpregs[45] = 0xbfe6a09e667f3bd0
        e.fpregs[46] = 0xbff0000000000000
        e.fpregs[47] = 0xbfe6a09e667f3bd5
        e.fpregs[48] = 0xbcc1a62633145c07
        e.fpregs[49] = 0x3fe6a09e667f3bcf
        e.fpregs[50] = 0x3ff0000000000000
        e.fpregs[51] = 0x3fe6a09e667f3bd6
        e.fpregs[52] = 0x3cc60fafbfd97309
        e.fpregs[53] = 0xbfe6a09e667f3bce
        e.fpregs[54] = 0xbff0000000000000
        e.fpregs[55] = 0xbfe6a09e667f3bd7
        e.fpregs[56] = 0xbcca79394c9e8a0a
        e.fpregs[57] = 0x3fe6a09e667f3bcd
        e.fpregs[58] = 0x3ff0000000000000
        e.fpregs[59] = 0x3fe6a09e667f3bd7
        e.fpregs[60] = 0x3ccee2c2d963a10c
        e.fpregs[61] = 0xbfe6a09e667f3bcd
        e.fpregs[62] = 0xbff0000000000000
        e.fpregs[63] = 0xbfe6a09e667f3bd8
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_fminc(self):
        lst = list(SVP64Asm(["sv.fminc *32,*64,*96"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        r = range(svstate.vl)
        for i, rev_i in zip(r, reversed(r)):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i))[0]
            fprs[96 + i] = struct.unpack("<Q", struct.pack("<d", rev_i))[0]
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x0
        e.fpregs[33] = 0x3ff0000000000000
        e.fpregs[34] = 0x4000000000000000
        e.fpregs[35] = 0x4008000000000000
        e.fpregs[36] = 0x4010000000000000
        e.fpregs[37] = 0x4014000000000000
        e.fpregs[38] = 0x4018000000000000
        e.fpregs[39] = 0x401c000000000000
        e.fpregs[40] = 0x4020000000000000
        e.fpregs[41] = 0x4022000000000000
        e.fpregs[42] = 0x4024000000000000
        e.fpregs[43] = 0x4026000000000000
        e.fpregs[44] = 0x4028000000000000
        e.fpregs[45] = 0x402a000000000000
        e.fpregs[46] = 0x402c000000000000
        e.fpregs[47] = 0x402e000000000000
        e.fpregs[48] = 0x402e000000000000
        e.fpregs[49] = 0x402c000000000000
        e.fpregs[50] = 0x402a000000000000
        e.fpregs[51] = 0x4028000000000000
        e.fpregs[52] = 0x4026000000000000
        e.fpregs[53] = 0x4024000000000000
        e.fpregs[54] = 0x4022000000000000
        e.fpregs[55] = 0x4020000000000000
        e.fpregs[56] = 0x401c000000000000
        e.fpregs[57] = 0x4018000000000000
        e.fpregs[58] = 0x4014000000000000
        e.fpregs[59] = 0x4010000000000000
        e.fpregs[60] = 0x4008000000000000
        e.fpregs[61] = 0x4000000000000000
        e.fpregs[62] = 0x3ff0000000000000
        e.fpregs[63] = 0x0
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)

    def case_sv_fmaxmag19(self):
        lst = list(SVP64Asm(["sv.fmaxmag19 *32,*64,*96"]))
        gprs = [0] * 128
        fprs = [0] * 128
        svstate = SVP64State()
        svstate.vl = 32
        svstate.maxvl = 32
        r = range(svstate.vl)
        for i, rev_i in zip(r, reversed(r)):
            fprs[64 + i] = struct.unpack("<Q", struct.pack("<d", i))[0]
            fprs[96 + i] = struct.unpack("<Q", struct.pack("<d", rev_i))[0]
        e = ExpectedState(pc=8, int_regs=gprs, fp_regs=fprs)
        e.fpregs[32] = 0x403f000000000000
        e.fpregs[33] = 0x403e000000000000
        e.fpregs[34] = 0x403d000000000000
        e.fpregs[35] = 0x403c000000000000
        e.fpregs[36] = 0x403b000000000000
        e.fpregs[37] = 0x403a000000000000
        e.fpregs[38] = 0x4039000000000000
        e.fpregs[39] = 0x4038000000000000
        e.fpregs[40] = 0x4037000000000000
        e.fpregs[41] = 0x4036000000000000
        e.fpregs[42] = 0x4035000000000000
        e.fpregs[43] = 0x4034000000000000
        e.fpregs[44] = 0x4033000000000000
        e.fpregs[45] = 0x4032000000000000
        e.fpregs[46] = 0x4031000000000000
        e.fpregs[47] = 0x4030000000000000
        e.fpregs[48] = 0x4030000000000000
        e.fpregs[49] = 0x4031000000000000
        e.fpregs[50] = 0x4032000000000000
        e.fpregs[51] = 0x4033000000000000
        e.fpregs[52] = 0x4034000000000000
        e.fpregs[53] = 0x4035000000000000
        e.fpregs[54] = 0x4036000000000000
        e.fpregs[55] = 0x4037000000000000
        e.fpregs[56] = 0x4038000000000000
        e.fpregs[57] = 0x4039000000000000
        e.fpregs[58] = 0x403a000000000000
        e.fpregs[59] = 0x403b000000000000
        e.fpregs[60] = 0x403c000000000000
        e.fpregs[61] = 0x403d000000000000
        e.fpregs[62] = 0x403e000000000000
        e.fpregs[63] = 0x403f000000000000
        self.add_case(Program(lst, False), gprs, fpregs=fprs,
                      initial_svstate=svstate, expected=e)
