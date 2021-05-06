from openpower.test.common import (TestAccumulatorBase, skip_case)
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State, CRFields
from openpower.sv.trans.svp64 import SVP64Asm


class SVP64ALUTestCase(TestAccumulatorBase):

    def case_1_sv_add(self):
        """lst = ['sv.add 1.v, 5.v, 9.v']
        adds:
           1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
           2 = 6 + 10  => 0x3334 = 0x2223 + 0x1111
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
        """lst = ['sv.add 1, 5, 9']
        adds:
           1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
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
        """lst = ['sv.add 13.v, 10.v, 7.v']
        adds:
            13 = 10 + 7   => 0x4242 = 0x1230 + 0x3012

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
        """lst = ['sv.add. 1.v, 5.v, 9.v']
        adds when Rc=1:                               TODO CRs higher up
            1 = 5 + 9   => 0 = -1+1                 CR0=0b100
            2 = 6 + 10  => 0x3334 = 0x2223+0x1111   CR1=0b010
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
        """lst = [
            'sv.add 13.v, 10.v, 7.v',  # skipped, because VL == 0
            'add 1, 5, 9'
        ]
        adds:
            1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
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
        """lst = [
            'sv.add 1.v, 5.v, 9.v',
            'sv.add 13.v, 10.v, 7.v'
        ]
        adds:
            1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
            2 = 6 + 10  => 0x3334 = 0x2223 + 0x1111
            3 = 7 + 11  => 0x4242 = 0x3012 + 0x1230
            13 = 10 + 7  => 0x2341 = 0x1111 + 0x1230
            14 = 11 + 8  => 0x3012 = 0x3012 + 0x0000
            15 = 12 + 9  => 0x1234 = 0x0000 + 0x1234
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
        """lst = ['sv.add 1, 5.v, 9.v']
        adds:
            1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
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
        """lst = ['sv.add 1.v, 5, 9.v']
        adds:
            1 = 5 + 9   => 0x5555 = 0x4321+0x1234
            2 = 5 + 10  => 0x5432 = 0x4321+0x1111
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

    def case_9_sv_extsw_intpred(self):
        """lst = ['sv.extsb/sm=~r3/dm=r3 5.v, 9.v']

        extsb, integer twin-pred mask: source is ~r3 (0b01), dest r3 (0b10)
        works as follows, where any zeros indicate "skip element"
        - sources are 9 and 10
        - dests are 5 and 6
        - source mask says "pick first element from source (5)
        - dest mask says "pick *second* element from dest (10)

        therefore the operation that's carried out is:
             GPR(10) = extsb(GPR(5))

        this is a type of back-to-back VREDUCE and VEXPAND but it applies
        to *operations*, not just MVs like in traditional Vector ISAs
        ascii graphic:

           reg num                 0 1 2 3 4 5 6 7 8 9 10
           predicate src ~r3=0b01                    Y N
                                                     |
                                               +-----+
                                               |
           predicate dest r3=0b10            N Y

        expected results:
        r5 = 0x0                   dest r3 is 0b10: skip
        r6 = 0xffff_ffff_ffff_ff91 2nd bit of r3 is 1
        """
        isa = SVP64Asm(['sv.extsb/sm=~r3/dm=r3 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 0b10   # predicate mask
        initial_regs[9] = 0x91   # source ~r3 is 0b01 so this will be used
        initial_regs[10] = 0x90  # this gets skipped
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2  # VL
        svstate.maxvl[0:7] = 2  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_10_intpred_vcompress(self):
        """lst = ['sv.extsb/sm=r3 5.v, 9.v']

           reg num                 0 1 2 3 4 5 6 7 8 9 10 11
           predicate src r3=0b101                     Y  N  Y
                                                     |     |
                                             +-------+     |
                                             | +-----------+
                                             | |
           predicate dest always             Y Y Y

        expected results:
        r5 = 0xffff_ffff_ffff_ff90 (from r9)
        r6 = 0xffff_ffff_ffff_ff92 (from r11)
        r7 = 0x0 (VL loop runs out before we can use it)
        """
        isa = SVP64Asm(['sv.extsb/sm=r3 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 0b101  # predicate mask
        initial_regs[9] = 0x90   # source r3 is 0b101 so this will be used
        initial_regs[10] = 0x91  # this gets skipped
        initial_regs[11] = 0x92  # source r3 is 0b101 so this will be used
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_11_intpred_vexpand(self):
        """lst = ['sv.extsb/dm=r3 5.v, 9.v']

        reg num                  0 1 2 3 4 5 6 7 8 9 10 11
        predicate src always                       Y  Y  Y
                                                   |  |
                                           +-------+  |
                                           |   +------+
                                           |   |
        predicate dest r3=0b101            Y N Y

        expected results:
        r5 = 0xffff_ffff_ffff_ff90 1st bit of r3 is 1
        r6 = 0x0                   skip
        r7 = 0xffff_ffff_ffff_ff91 3nd bit of r3 is 1
        """
        isa = SVP64Asm(['sv.extsb/dm=r3 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 0b101  # predicate mask
        initial_regs[9] = 0x90   # source is "always", so this will be used
        initial_regs[10] = 0x91  # likewise
        initial_regs[11] = 0x92  # the VL loop runs out before we can use it
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_12_sv_twinpred(self):
        """lst = ['sv.extsb/sm=r3/dm=~r3 5.v, 9.v']

        reg num        0 1 2 3 4 5 6 7 8 9 10 11
        predicate src r3=0b101                     Y  N  Y
                                                   |
                                             +-----+
                                             |
        predicate dest ~r3=0b010           N Y N

        expected results:
        r5 = 0x0                   dest ~r3 is 0b010: skip
        r6 = 0xffff_ffff_ffff_ff90 2nd bit of ~r3 is 1
        r7 = 0x0                   dest ~r3 is 0b010: skip
        """
        isa = SVP64Asm(['sv.extsb/sm=r3/dm=~r3 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 0b101  # predicate mask
        initial_regs[9] = 0x90   # source r3 is 0b101 so this will be used
        initial_regs[10] = 0x91  # this gets skipped
        initial_regs[11] = 0x92  # VL loop runs out before we can use it
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_13_sv_predicated_add(self):
        """lst = [
            'sv.add/m=r30 1.v, 5.v, 9.v',
            'sv.add/m=~r30 13.v, 10.v, 7.v'
        ]

        checks integer predication using mask-invertmask.
        real-world usage would be two different operations
        (a masked-add and an inverted-masked-sub, where the
        mask was set up as part of a parallel If-Then-Else)

        first add:
            1 = 5 + 9   => 0x5555 = 0x4321 + 0x1234
            2 = 0 (skipped)
            3 = 7 + 11  => 0x4242 = 0x3012 + 0x1230

        second add:
           13 = 0 (skipped)
           14 = 11 + 8  => 0xB063 = 0x3012 + 0x8051
           15 = 0 (skipped)
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
        """lst = [
            'sv.add/m=r30 1.v, 5.v, 9.v',
            'sv.add/m=~r30 13.v, 10.v, 7.v'
        ]

        checks an instruction with no effect (all mask bits are zeros).
        TODO: check completion time (number of cycles), although honestly
        it is an implementation-specific optimisation to decide to skip
        Vector operations with a fully-zero mask.

        first add:
            1 = 0 (skipped)
            2 = 0 (skipped)
            3 = 0 (skipped)

        second add:
           13 = 10 + 7  => 0x2341 = 0x1111 + 0x1230
           14 = 11 + 8  => 0xB063 = 0x3012 + 0x8051
           15 = 12 + 9  => 0x7736 = 0x6502 + 0x1234
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

    def case_15_intpred_reentrant(self):
        """lst = ['sv.extsb/sm=r3/dm=~r3 5.v, 9.v']

        checks that we are able to resume in the middle of a VL loop,
        after an interrupt, or after the user has updated src/dst step
        let's assume the user has prepared src/dst step before running this
        vector instruction.  this is legal but unusual: normally it would
        be an interrupt return that would have non-zero step values

        note to hardware implementors: inside the hardware,
        make sure to skip mask bits before the initial step,
        to save clock cycles. or not. your choice.

        reg num        0 1 2 3 4 5 6 7 8 9 10 11 12
        srcstep=1                           v
        src r3=0b0101                    Y  N  Y  N
                                         :     |
                                   + - - +     |
                                   :   +-------+
                                   :   |
        dest ~r3=0b1010          N Y N Y
        dststep=2                    ^

        expected results:
        r5 = 0x0  # skip
        r6 = 0x0  # dststep starts at 3, so this gets skipped
        r7 = 0x0  # skip
        r8 = 0xffff_ffff_ffff_ff92  # this will be used
        """
        isa = SVP64Asm(['sv.extsb/sm=r3/dm=~r3 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 0b0101  # mask
        initial_regs[9] = 0x90   # srcstep starts at 2, so this gets skipped
        initial_regs[10] = 0x91  # skip
        initial_regs[11] = 0x92  # this will be used
        initial_regs[12] = 0x93  # skip

        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl[0:7] = 4  # VL
        svstate.maxvl[0:7] = 4  # MAXVL
        # set src/dest step on the middle of the loop
        svstate.srcstep[0:7] = 1
        svstate.dststep[0:7] = 2
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_16_shift_one_by_r3_dest(self):
        """lst = ['sv.extsb/dm=1<<r3/sm=r30 5.v, 9.v']

        one option for predicate masks is a single-bit set: 1<<r3.
        lots of opportunity for hardware optimisation, it effectively
        allows dynamic indexing of the register file

        reg num        0 1 2 3 4 5 6 7 8 9 10 11
        src r30=0b100                    N  N  Y
                                               |
                                   +-----------+
                                   |
        dest r3=1: 1<<r3=0b010   N Y N

        expected results:
        r5 = 0x0                    skipped
        r6 = 0xffff_ffff_ffff_ff92  r3 is 1, so this is used
        r7 = 0x0                    skipped
        """
        isa = SVP64Asm(['sv.extsb/dm=1<<r3/sm=r30 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 1  # dest mask = 1<<r3 = 0b010
        initial_regs[30] = 0b100  # source mask
        initial_regs[9] = 0x90   # skipped
        initial_regs[10] = 0x91  # skipped
        initial_regs[11] = 0x92  # 3rd bit of r30 is 1
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_17_shift_one_by_r3_source(self):
        """lst = ['sv.extsb/sm=1<<r3/dm=r30 5.v, 9.v']

        reg num        0 1 2 3 4 5 6 7 8 9 10 11
        src r3=2: 1<<r3=0b100            N  N  Y
                                               |
                                   +-----------+
                                   |
        dest r30=0b010           N Y N

        expected results:
        r5 = 0x0                    skipped
        r6 = 0xffff_ffff_ffff_ff92  2nd bit of r30 is 1
        r7 = 0x0                    skipped
        """
        isa = SVP64Asm(['sv.extsb/sm=1<<r3/dm=r30 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 2  # source mask = 1<<r3 = 0b100
        initial_regs[30] = 0b010  # dest mask
        initial_regs[9] = 0x90   # skipped
        initial_regs[10] = 0x91  # skipped
        initial_regs[11] = 0x92  # r3 is 2, so this will be used
        # SVSTATE (in this case, VL=3)
        svstate = SVP64State()
        svstate.vl[0:7] = 3  # VL
        svstate.maxvl[0:7] = 3  # MAXVL
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

    def case_18_sv_add_cr_pred(self):
        """lst = ['sv.add/m=ne 1.v, 5.v, 9.v']

        adds, CR predicated mask CR4.eq = 1, CR5.eq = 0, invert (ne)
            1 = 5 + 9   => not to be touched (skipped)
            2 = 6 + 10  => 0x3334 = 0x2223+0x1111

        expected results:
        r1 = 0xbeef skipped since CR4 is 1 and test is inverted
        r2 = 0x3334 CR5 is 0, so this is used
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

    def case_19_crpred_reentrant(self):
        """lst = ['sv.extsb/sm=eq/dm=lt 5.v, 9.v']

        checks reentrant CR predication.  note that the source CR-mask
        and destination CR-mask use *different bits* of the CR fields,
        despite both predicates starting from the same CR field number.
        cr4.lt is zero, cr7.lt is zero AND
        cr5.eq is zero, cr6.eq is zero.

        reg num        0 1 2 3 4 5 6 7 8 9 10 11 12
        srcstep=1                           v
        src cr4.eq=1                     Y  N  Y  N
            cr6.eq=1                     :     |
                                   + - - +     |
                                   :   +-------+
        dest cr5.lt=1              :   |
             cr7.lt=1            N Y N Y
        dststep=2                    ^

        expected results:
        r5 = 0x0  skip
        r6 = 0x0  dststep starts at 3, so this gets skipped
        r7 = 0x0  skip
        r8 = 0xffff_ffff_ffff_ff92  this will be used
        """
        isa = SVP64Asm(['sv.extsb/sm=eq/dm=lt 5.v, 9.v'])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x90  # srcstep starts at 2, so this gets skipped
        initial_regs[10] = 0x91  # skip
        initial_regs[11] = 0x92  # this will be used
        initial_regs[12] = 0x93  # skip

        cr = CRFields()
        # set up CR predicate
        # CR4.eq=1 and CR6.eq=1
        cr.crl[4][CRFields.EQ] = 1
        cr.crl[5][CRFields.EQ] = 0
        cr.crl[6][CRFields.EQ] = 1
        cr.crl[7][CRFields.EQ] = 0
        # CR5.lt=1 and CR7.lt=1
        cr.crl[4][CRFields.LT] = 0
        cr.crl[5][CRFields.LT] = 1
        cr.crl[6][CRFields.LT] = 0
        cr.crl[7][CRFields.LT] = 1
        # SVSTATE (in this case, VL=4)
        svstate = SVP64State()
        svstate.vl[0:7] = 4  # VL
        svstate.maxvl[0:7] = 4  # MAXVL
        # set src/dest step on the middle of the loop
        svstate.srcstep[0:7] = 1
        svstate.dststep[0:7] = 2
        print("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate, initial_cr=cr.cr.asint())
