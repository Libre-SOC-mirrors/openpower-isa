from openpower.test.common import (TestAccumulatorBase, skip_case)
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State, CRFields
from openpower.sv.trans.svp64 import SVP64Asm


class SVP64LogicalTestCase(TestAccumulatorBase):

    def case_9_sv_extsw_intpred(self):
        """>>> lst = ['sv.extsb/sm=~r3/dm=r3 5.v, 9.v']

        extsb, integer twin-pred mask: source is ~r3 (0b01), dest r3 (0b10)
        works as follows, where any zeros indicate "skip element"

            * sources are 9 and 10
            * dests are 5 and 6
            * source mask says "pick first element from source (5)
            * dest mask says "pick *second* element from dest (10)

        therefore the operation that's carried out is::

             GPR(10) = extsb(GPR(5))

        this is a type of back-to-back VREDUCE and VEXPAND but it applies
        to *operations*, not just MVs like in traditional Vector ISAs
        ascii graphic::

            reg num                 0 1 2 3 4 5 6 7 8 9 10
            predicate src ~r3=0b01                    Y N
                                                      |
                                                +-----+
                                                |
            predicate dest r3=0b10            N Y

        expected results:
            * r5 = 0x0                   dest r3 is 0b10: skip
            * r6 = 0xffff_ffff_ffff_ff91 2nd bit of r3 is 1
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
        """>>> lst = ['sv.extsb/sm=r3 5.v, 9.v']

        ascii graphic::

            reg num                 0 1 2 3 4 5 6 7 8 9 10 11
            predicate src r3=0b101                    Y  N  Y
                                                      |     |
                                              +-------+     |
                                              | +-----------+
                                              | |
            predicate dest always             Y Y Y

        expected results:
            * r5 = 0xffff_ffff_ffff_ff90 (from r9)
            * r6 = 0xffff_ffff_ffff_ff92 (from r11)
            * r7 = 0x0 (VL loop runs out before we can use it)
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
        """>>> lst = ['sv.extsb/dm=r3 5.v, 9.v']

        ascii graphic::

            reg num                  0 1 2 3 4 5 6 7 8 9 10 11
            predicate src always                       Y  Y  Y
                                                       |  |
                                               +-------+  |
                                               |   +------+
                                               |   |
            predicate dest r3=0b101            Y N Y

        expected results:
            * r5 = 0xffff_ffff_ffff_ff90 1st bit of r3 is 1
            * r6 = 0x0                   skip
            * r7 = 0xffff_ffff_ffff_ff91 3nd bit of r3 is 1
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
        """>>> lst = ['sv.extsb/sm=r3/dm=~r3 5.v, 9.v']

        ascii graphic::

            reg num        0 1 2 3 4 5 6 7 8 9 10 11
            predicate src r3=0b101                     Y  N  Y
                                                       |
                                                 +-----+
                                                 |
            predicate dest ~r3=0b010           N Y N

        expected results:
            * r5 = 0x0                   dest ~r3 is 0b010: skip
            * r6 = 0xffff_ffff_ffff_ff90 2nd bit of ~r3 is 1
            * r7 = 0x0                   dest ~r3 is 0b010: skip
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

    def case_15_intpred_reentrant(self):
        """>>> lst = ['sv.extsb/sm=r3/dm=~r3 5.v, 9.v']

        checks that we are able to resume in the middle of a VL loop,
        after an interrupt, or after the user has updated src/dst step
        let's assume the user has prepared src/dst step before running this
        vector instruction.  this is legal but unusual: normally it would
        be an interrupt return that would have non-zero step values

        note to hardware implementors: inside the hardware,
        make sure to skip mask bits before the initial step,
        to save clock cycles. or not. your choice.

        ascii graphic::

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
            * r5 = 0x0  # skip
            * r6 = 0x0  # dststep starts at 3, so this gets skipped
            * r7 = 0x0  # skip
            * r8 = 0xffff_ffff_ffff_ff92  # this will be used
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
        """>>> lst = ['sv.extsb/dm=1<<r3/sm=r30 5.v, 9.v']

        one option for predicate masks is a single-bit set: 1<<r3.
        lots of opportunity for hardware optimisation, it effectively
        allows dynamic indexing of the register file

        ascii graphic::

            reg num        0 1 2 3 4 5 6 7 8 9 10 11
            src r30=0b100                    N  N  Y
                                                   |
                                       +-----------+
                                       |
            dest r3=1: 1<<r3=0b010   N Y N

        expected results:
            * r5 = 0x0                    skipped
            * r6 = 0xffff_ffff_ffff_ff92  r3 is 1, so this is used
            * r7 = 0x0                    skipped
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
        """>>> lst = ['sv.extsb/sm=1<<r3/dm=r30 5.v, 9.v']

        ascii graphic::

            reg num        0 1 2 3 4 5 6 7 8 9 10 11
            src r3=2: 1<<r3=0b100            N  N  Y
                                                   |
                                       +-----------+
                                       |
            dest r30=0b010           N Y N

        expected results:
            * r5 = 0x0                    skipped
            * r6 = 0xffff_ffff_ffff_ff92  2nd bit of r30 is 1
            * r7 = 0x0                    skipped
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

    def case_19_crpred_reentrant(self):
        """>>> lst = ['sv.extsb/sm=eq/dm=lt 5.v, 9.v']

        checks reentrant CR predication.  note that the source CR-mask
        and destination CR-mask use *different bits* of the CR fields,
        despite both predicates starting from the same CR field number.

            * cr4.lt is zero, cr7.lt is zero AND
            * cr5.eq is zero, cr6.eq is zero.

        ascii graphic::

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
            * r5 = 0x0  skip
            * r6 = 0x0  dststep starts at 3, so this gets skipped
            * r7 = 0x0  skip
            * r8 = 0xffff_ffff_ffff_ff92  this will be used
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

    def case_sv_extsw_intpred_dz(self):
        """>>> lst = ['sv.extsb/dm=r3/dz 5.v, 9.v']

        extsb, integer twin-pred mask: dest is r3 (0b01), zeroing on dest.
        this test will put a zero into the element where its corresponding
        predicate dest mask bit is also zero.
        """
        isa = SVP64Asm(['sv.extsb/dm=r3/dz 5.v, 9.v'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[3] = 0b01   # predicate mask (dest)
        initial_regs[5] = 0xfeed # going to be overwritten
        initial_regs[6] = 0xbeef # going to be overwritten (with zero)
        initial_regs[9] = 0x91   # dest r3 is 0b01 so this will be used
        initial_regs[10] = 0x90  # this gets read but the output gets zero'd
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 2 # VL
        svstate.maxvl[0:7] = 2 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_svstate=svstate)

