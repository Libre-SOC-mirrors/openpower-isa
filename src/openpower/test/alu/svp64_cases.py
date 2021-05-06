from openpower.test.common import (TestAccumulatorBase, skip_case)
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State, CRFields
from openpower.sv.trans.svp64 import SVP64Asm


class SVP64ALUTestCase(TestAccumulatorBase):

    def case_1_sv_add(self):
        """>>> lst = ['sv.add 1.v, 5.v, 9.v']

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
            * 2 = 6 + 10  => 0x3334 = 0x2223 + 0x1111
        """
        isa = SVP64Asm(['sv.add 1.v, 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2  # VL
        svstate.maxvl[0:7] = 2  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_2_sv_add_scalar(self):
        """>>> lst = ['sv.add 1, 5, 9']

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
        """
        isa = SVP64Asm(['sv.add 1, 5, 9'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[5] = 0x4321
        svstate = SVP64State()
        # SVSTATE (in this case, VL=1, so everything works as in v3.0B)
        svstate.vl[0:7] = 1  # VL
        svstate.maxvl[0:7] = 1  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_3_sv_check_extra(self):
        """>>> lst = ['sv.add 13.v, 10.v, 7.v']

        adds:
            * 13 = 10 + 7   => 0x4242 = 0x1230 + 0x3012

        This case helps checking the encoding of the Extra field
        It was built so the v3.0b registers are: 3, 2, 1
        and the Extra field is: 101.110.111
        The expected SVP64 register numbers are: 13, 10, 7
        Any mistake in decoding will probably give a different answer
        """
        isa = SVP64Asm(['sv.add 13.v, 10.v, 7.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[7] = 0x3012
        initial_regs[10] = 0x1230
        svstate = SVP64State()
        # SVSTATE (in this case, VL=1, so everything works as in v3.0B)
        svstate.vl[0:7] = 1  # VL
        svstate.maxvl[0:7] = 1  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_4_sv_add_(self):
        """>>> lst = ['sv.add. 1.v, 5.v, 9.v']

        adds when Rc=1:                               TODO CRs higher up
            * 1 = 5 + 9   => 0 = -1+1                 CR0=0b100
            * 2 = 6 + 10  => 0x3334 = 0x2223+0x1111   CR1=0b010
        """
        isa = SVP64Asm(['sv.add. 1.v, 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0xffffffffffffffff
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x1
        initial_regs[6] = 0x2223

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2  # VL
        svstate.maxvl[0:7] = 2  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_5_sv_check_vl_0(self):
        """>>> lst = [
            'sv.add 13.v, 10.v, 7.v',  # skipped, because VL == 0
            'add 1, 5, 9'
        ]

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
        """
        isa = SVP64Asm([
            'sv.add 13.v, 10.v, 7.v',  # skipped, because VL == 0
            'add 1, 5, 9'
        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[5] = 0x4321
        initial_regs[7] = 0x3012
        initial_regs[10] = 0x1230
        svstate = SVP64State()
        # SVSTATE (in this case, VL=0, so vector instructions are skipped)
        svstate.vl[0:7] = 0  # VL
        svstate.maxvl[0:7] = 0  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    # checks that SRCSTEP was reset properly after an SV instruction
    def case_6_sv_add_multiple(self):
        """>>> lst = [
            'sv.add 1.v, 5.v, 9.v',
            'sv.add 13.v, 10.v, 7.v'
        ]

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
            * 2 = 6 + 10  => 0x3334 = 0x2223 + 0x1111
            * 3 = 7 + 11  => 0x4242 = 0x3012 + 0x1230
            * 13 = 10 + 7  => 0x2341 = 0x1111 + 0x1230
            * 14 = 11 + 8  => 0x3012 = 0x3012 + 0x0000
            * 15 = 12 + 9  => 0x1234 = 0x0000 + 0x1234
        """
        isa = SVP64Asm([
            'sv.add 1.v, 5.v, 9.v',
            'sv.add 13.v, 10.v, 7.v'
        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[11] = 0x3012
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        initial_regs[7] = 0x1230
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_7_sv_add_2(self):
        """>>> lst = ['sv.add 1, 5.v, 9.v']

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
        """
        #       r1 is scalar so ENDS EARLY
        isa = SVP64Asm(['sv.add 1, 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2  # VL
        svstate.maxvl[0:7] = 2  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_8_sv_add_3(self):
        """>>> lst = ['sv.add 1.v, 5, 9.v']

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321+0x1234
            * 2 = 5 + 10  => 0x5432 = 0x4321+0x1111
        """
        isa = SVP64Asm(['sv.add 1.v, 5, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2  # VL
        svstate.maxvl[0:7] = 2  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_13_sv_predicated_add(self):
        """>>> lst = [
            'sv.add/m=r30 1.v, 5.v, 9.v',
            'sv.add/m=~r30 13.v, 10.v, 7.v'
        ]

        checks integer predication using mask-invertmask.
        real-world usage would be two different operations
        (a masked-add and an inverted-masked-sub, where the
        mask was set up as part of a parallel If-Then-Else)

        first add:
            * 1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
            * 2 = 0 (skipped)
            * 3 = 7 + 11  => 0x4242 = 0x3012 + 0x1230

        second add:
           * 13 = 0 (skipped)
           * 14 = 11 + 8  => 0xB063 = 0x3012 + 0x8051
           * 15 = 0 (skipped)
        """
        isa = SVP64Asm([
            'sv.add/m=r30 1.v, 5.v, 9.v',
            'sv.add/m=~r30 13.v, 10.v, 7.v'
        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[30] = 0b101  # predicate mask
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[11] = 0x3012
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        initial_regs[7] = 0x1230
        initial_regs[8] = 0x8051
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_14_intpred_all_zeros_all_ones(self):
        """>>> lst = [
            'sv.add/m=r30 1.v, 5.v, 9.v',
            'sv.add/m=~r30 13.v, 10.v, 7.v'
        ]

        checks an instruction with no effect (all mask bits are zeros).
        TODO: check completion time (number of cycles), although honestly
        it is an implementation-specific optimisation to decide to skip
        Vector operations with a fully-zero mask.

        first add:
            * 1 = 0 (skipped)
            * 2 = 0 (skipped)
            * 3 = 0 (skipped)

        second add:
            * 13 = 10 + 7  => 0x2341 = 0x1111 + 0x1230
            * 14 = 11 + 8  => 0xB063 = 0x3012 + 0x8051
            * 15 = 12 + 9  => 0x7736 = 0x6502 + 0x1234
        """
        isa = SVP64Asm([
            'sv.add/m=r30 1.v, 5.v, 9.v',
            'sv.add/m=~r30 13.v, 10.v, 7.v'
        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[30] = 0  # predicate mask
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[11] = 0x3012
        initial_regs[12] = 0x6502
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        initial_regs[7] = 0x1230
        initial_regs[8] = 0x8051
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_18_sv_add_cr_pred(self):
        """>>> lst = ['sv.add/m=ne 1.v, 5.v, 9.v']

        adds, CR predicated mask CR4.eq = 1, CR5.eq = 0, invert (ne)
            * 1 = 5 + 9   => not to be touched (skipped)
            * 2 = 6 + 10  => 0x3334 = 0x2223+0x1111

        expected results:
            * r1 = 0xbeef skipped since CR4 is 1 and test is inverted
            * r2 = 0x3334 CR5 is 0, so this is used
        """
        isa = SVP64Asm(['sv.add/m=ne 1.v, 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[1] = 0xbeef   # not to be altered
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2  # VL
        svstate.maxvl[0:7] = 2  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        # set up CR predicate - CR4.eq=1 and CR5.eq=0
        cr = 0b0010 << ((7-4)*4)  # CR4.eq (we hope)

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate, initial_cr=cr)

