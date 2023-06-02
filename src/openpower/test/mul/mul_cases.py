from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.test.state import ExpectedState
from openpower.insndb.asm import SVP64Asm
from openpower.decoder.isa.caller import SVP64State
from copy import deepcopy
import random


class MulTestCases2Arg(TestAccumulatorBase):

    def case_kestrel_regression_0(self):
        lst = ["mulhd r30,r9,r30"]
        initial_regs = [0] * 32
        initial_regs[30] = 0x20c49ba5e353f7cf
        initial_regs[9] = 0x1f40
        e = ExpectedState(initial_regs, 4)
        e.intregs[30] = 0x400
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_0_mullw(self):
        lst = [f"mullw 3, 1, 2"]
        initial_regs = [0] * 32
        #initial_regs[1] = 0xffffffffffffffff
        #initial_regs[2] = 0xffffffffffffffff
        initial_regs[1] = 0x2ffffffff
        initial_regs[2] = 0x2
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_1_mullwo_(self):
        lst = [f"mullwo. 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3b34b06f
        initial_regs[2] = 0xfdeba998
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_2_mullwo(self):
        lst = [f"mullwo 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffa988  # -5678
        initial_regs[2] = 0xffffffffffffedcc  # -1234
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_3_mullw(self):
        lst = ["mullw 3, 1, 2",
               "mullw 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x6
        initial_regs[2] = 0xe
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_4_mullw_rand(self):
        for i in range(40):
            lst = ["mullw 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_4_mullw_nonrand(self):
        for i in range(40):
            lst = ["mullw 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = i+1
            initial_regs[2] = i+20
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_mulhw__regression_1(self):
        lst = ["mulhw. 3, 1, 2"
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x7745b36eca6646fa
        initial_regs[2] = 0x47dfba3a63834ba2
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand_mul_lh(self):
        insns = ["mulhw", "mulhw.", "mulhwu", "mulhwu."]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand_mullw(self):
        insns = ["mullw", "mullw.", "mullwo", "mullwo."]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand_mulld(self):
        insns = ["mulld", "mulld.", "mulldo", "mulldo."]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_mulli(self):

        for i in range(40):
            imm = random.randint(-1 << 15, (1 << 15) - 1)
            ra = random.randint(0, (1 << 64) - 1)
            l = [f"mulli 0, 1, {imm}"]
            # use "with" so as to close the files used
            with Program(l, bigendian) as prog:
                initial_regs = [0] * 32
                initial_regs[1] = ra
                self.add_case(prog, initial_regs)

    def case_rand_mulhd(self):
        insns = ["mulhd", "mulhd."]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand_mulhdu(self):
        insns = ["mulhdu", "mulhdu."]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_0_mullhw_regression(self):
        lst = [f"mulhwu 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x4000000000000000
        initial_regs[2] = 0x0000000000000002
        self.add_case(Program(lst, bigendian), initial_regs)


class MulTestCases3Arg(TestAccumulatorBase):
    # TODO add test case for these 3 operand cases (madd
    # needs to be implemented)
    # "maddhd","maddhdu","maddld"
    @skip_case("madd not implemented")
    def case_maddld(self):
        lst = ["maddld 1, 2, 3, 4"]
        initial_regs = [0] * 32
        initial_regs[2] = 0x3
        initial_regs[3] = 0x4
        initial_regs[4] = 0x5
        self.add_case(Program(lst, bigendian), initial_regs)


class SVP64MAdd(TestAccumulatorBase):
    # TODO add test case for these 3 operand cases (madd
    # needs to be implemented)
    # "maddhd","maddhdu","maddld"
    def case_sv_maddld(self):
        #                     muladdlo RT = RA * RB + RC
        lst = list(SVP64Asm(["sv.maddld *4, *8, *12, 16"]))
        initial_regs = [0] * 32
        initial_regs[8:16] = range(1, 17)
        initial_regs[16] = 0x10000
        svstate = SVP64State()
        svstate.vl = 4
        svstate.maxvl = 4
        expected_regs = deepcopy(initial_regs)
        r16 = initial_regs[16]
        for i in range(4):
            # mul-and-add-lo is: RT = RA*RB+RC. RC (16) is scalar, RA/RB vector
            res = initial_regs[8+i] * initial_regs[12+i] + r16
            expected_regs[4+i] = res & 0xffff_ffff_ffff_ffff
        e = ExpectedState(expected_regs, 8)
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate,
                      expected=e)

    def case_sv_maddld_mapreduce(self):
        """test of using maddld in "mapreduce" mode (sum-of-products)
        for this to work, RT must be the same reg as RC: r4 is chosen.
        normally without /mr the fact that RT is scalar would *stop*
        the looping at the first (scalar) write to RT.

        "/mr" *disables* that and relies on the hardware to issue
        multiple "maddld" operations, performing the usual NECESSARY
        Register Hazard Dependency Checking *as if* this was an ACTUAL
        sequence of four *scalar* maddld inline operations:

        maddld 4,8,12,4 maddld 4,9,13,4 maddld 4,10,14,4 maddld 4,11,15,4
        """
        #                     muladdlo RT = RA * RB + RC
        lst = list(SVP64Asm(["sv.maddld/mr 4, *8, *12, 4"]))
        initial_regs = [0] * 32
        initial_regs[4] = 0x10000
        initial_regs[8:16] = range(1, 17)
        svstate = SVP64State()
        svstate.vl = 4
        svstate.maxvl = 4
        # calculate expected results (multiply-and-accumulate
        expected_regs = deepcopy(initial_regs)
        accumulator = initial_regs[4]
        for i in range(4):
            # mul-and-add-lo is: RT = RA*RB+RC. RT and RC scalar, RA/RB vector
            accumulator += initial_regs[8+i] * initial_regs[12+i]
            accumulator &= 0xffff_ffff_ffff_ffff # truncate hi-bits
        expected_regs[4] = accumulator
        e = ExpectedState(expected_regs, 8)
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate,
                      expected=e)
