from openpower.test.common import TestAccumulatorBase
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.test.state import ExpectedState
from openpower.simulator.program import Program


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
