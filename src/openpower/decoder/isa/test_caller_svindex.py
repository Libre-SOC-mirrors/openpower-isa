"""SVP64 unit test for svindex
svindex SVG,rmm,SVd,ew,yx,mm,sk
"""
from nmigen import Module, Signal
from nmigen.sim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, SVP64State, CRFields
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA
from openpower.decoder.isa.test_caller import Register, run_tst
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.consts import SVP64CROffs
from copy import deepcopy


def set_masked_reg(regs, base, offs, ew_bits, value):
    # rrrright.  start by breaking down into row/col, based on elwidth
    gpr_offs = offs // (64//ew_bits)
    gpr_col = offs % (64//ew_bits)
    # compute the mask based on ew_bits
    mask = (1<<ew_bits)-1
    # now select the 64-bit register, but get its value (easier)
    val = regs[base+gpr_offs]
    # now mask out the bit we don't want
    val = val & ~(mask << (gpr_col*ew_bits))
    # then wipe the bit we don't want from the value
    value = value & mask
    # OR the new value in, shifted up
    val |= value << (gpr_col*ew_bits)
    regs[base+gpr_offs] = val

def rotl32(v, c):
    c = c & 0x1f
    return ((v << c) & 0xffffffff) | v >> (32 - c)


class SVSTATETestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        print ("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64),
            "GPR %d %x expected %x" % (i, sim.gpr(i).value, expected[i]))

    def test_0_sv_index(self):
        """sets VL=10 (via SVSTATE) then does svindex mm=0, checks SPRs after
        """
        isa = SVP64Asm(['svindex 1, 15, 5, 0, 0, 0, 0'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 10 # VL
        svstate.maxvl = 10 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        #expected_regs[1] = 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            self._check_regs(sim, expected_regs)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print ("STATE0 xdim", SVSHAPE0.xdimsz)
            print ("STATE0 ydim", SVSHAPE0.ydimsz)
            print ("STATE0 skip", bin(SVSHAPE0.skip))
            print ("STATE0  inv", SVSHAPE0.invxyz)
            print ("STATE0order", SVSHAPE0.order)
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b01111) # same as rmm
            # rmm is 0b01111 which means mi0=0 mi1=1 mi2=2 mo0=3 mo1=0
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 1)
            self.assertEqual(sim.svstate.mi2, 2)
            self.assertEqual(sim.svstate.mo0, 3)
            self.assertEqual(sim.svstate.mo1, 0)
            for i in range(4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 2) # SVG is shifted up by 1

    def test_1_sv_index(self):
        """sets VL=10 (via SVSTATE) then does svindex mm=1, checks SPRs after
        """
        # rmm: bits 0-2 (MSB0) are 0b011 and bits 3-4 are 0b10.
        #      therefore rmm is 0b011 || 0b10 --> 0b01110 -> 14
        isa = SVP64Asm(['svindex 1, 14, 5, 0, 0, 1, 0'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 10 # VL
        svstate.maxvl = 10 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        #expected_regs[1] = 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)
            self._check_regs(sim, expected_regs)

            print (sim.spr)
            SVSHAPE2 = sim.spr['SVSHAPE2']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE2svgpr", hex(SVSHAPE2.svgpr))
            print ("STATE2 xdim", SVSHAPE2.xdimsz)
            print ("STATE2 ydim", SVSHAPE2.ydimsz)
            print ("STATE2 skip", bin(SVSHAPE2.skip))
            print ("STATE2  inv", SVSHAPE2.invxyz)
            print ("STATE2order", SVSHAPE2.order)
            self.assertEqual(sim.svstate.RMpst, 1) # mm=1 so persist=1
            # rmm is 0b01110 which means mo0 = 2
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 2)
            self.assertEqual(sim.svstate.mo1, 0)
            # and mo0 should be activated
            self.assertEqual(sim.svstate.SVme, 0b01000)
            # now check the SVSHAPEs. 2 was the one targetted
            self.assertEqual(SVSHAPE2.svgpr, 2) # SVG is shifted up by 1
            self.assertEqual(SVSHAPE2.xdimsz, 5)  # SHAPE2 xdim set to 5
            self.assertEqual(SVSHAPE2.ydimsz, 1)  # SHAPE2 ydim 1
            # all others must be zero
            for i in [0,1,3]:
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.asint(), 0) # all others zero

    def test_0_sv_index_add(self):
        """sets VL=6 (via SVSTATE) then does svindex, and an add.

        only RA is re-mapped via Indexing, not RB or RT
        """
        isa = SVP64Asm(['svindex 8, 1, 1, 0, 0, 0, 0',
                        'sv.add *8, *0, *0',
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        idxs = [1, 0, 5, 2, 4, 3] # random enough
        for i in range(6):
            initial_regs[16+i] = idxs[i]
            initial_regs[i] = i

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 6 # VL
        svstate.maxvl = 6 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        for i in range(6):
            RA = initial_regs[0+idxs[i]]
            RB = initial_regs[0+i]
            expected_regs[i+8] = RA+RB
            print ("expected", i, expected_regs[i+8])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print (sim.gpr.dump())
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b00001) # same as rmm
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 0)
            self.assertEqual(sim.svstate.mo1, 0)
            self.assertEqual(SVSHAPE0.svgpr, 16) # SVG is shifted up by 1
            for i in range(1,4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 0)
            self._check_regs(sim, expected_regs)

    def test_1_sv_index_add(self):
        """sets VL=6 (via SVSTATE) then does modulo 3 svindex, and an add.

        only RA is re-mapped via Indexing, not RB or RT
        """
        isa = SVP64Asm(['svindex 8, 1, 3, 0, 0, 0, 0',
                        'sv.add *8, *0, *0',
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        idxs = [1, 0, 5, 2, 4, 3] # random enough
        for i in range(6):
            initial_regs[16+i] = idxs[i]
            initial_regs[i] = i

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 6 # VL
        svstate.maxvl = 6 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        for i in range(6):
            RA = initial_regs[0+idxs[i%3]] # modulo 3 but still indexed
            RB = initial_regs[0+i]
            expected_regs[i+8] = RA+RB
            print ("expected", i, expected_regs[i+8])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print ("STATE0 xdim", SVSHAPE0.xdimsz)
            print ("STATE0 ydim", SVSHAPE0.ydimsz)
            print ("STATE0 skip", bin(SVSHAPE0.skip))
            print ("STATE0  inv", SVSHAPE0.invxyz)
            print ("STATE0order", SVSHAPE0.order)
            print (sim.gpr.dump())
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b00001) # same as rmm
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 0)
            self.assertEqual(sim.svstate.mo1, 0)
            self.assertEqual(SVSHAPE0.svgpr, 16) # SVG is shifted up by 1
            for i in range(1,4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 0)
            self._check_regs(sim, expected_regs)

    def test_2_sv_index_add(self):
        """sets VL=6 (via SVSTATE) then does 2D remapped svindex, and an add.

        dim=3,yx=1
        only RA is re-mapped via Indexing, not RB or RT
        """
        isa = SVP64Asm(['svindex 8, 1, 3, 0, 1, 0, 0',
                        'sv.add *8, *0, *0',
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        idxs = [1, 0, 5, 2, 4, 3] # random enough
        for i in range(6):
            initial_regs[16+i] = idxs[i]
            initial_regs[i] = i

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 6 # VL
        svstate.maxvl = 6 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        for i in range(6):
            xi = i % 3
            yi = i // 3
            remap = yi+xi*2
            RA = initial_regs[0+idxs[remap]] # modulo 3 but still indexed
            RB = initial_regs[0+i]
            expected_regs[i+8] = RA+RB
            print ("expected", i, expected_regs[i+8])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print ("STATE0 xdim", SVSHAPE0.xdimsz)
            print ("STATE0 ydim", SVSHAPE0.ydimsz)
            print ("STATE0 skip", bin(SVSHAPE0.skip))
            print ("STATE0  inv", SVSHAPE0.invxyz)
            print ("STATE0order", SVSHAPE0.order)
            print (sim.gpr.dump())
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b00001) # same as rmm
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 0)
            self.assertEqual(sim.svstate.mo1, 0)
            self.assertEqual(SVSHAPE0.svgpr, 16) # SVG is shifted up by 1
            for i in range(1,4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 0)
            self._check_regs(sim, expected_regs)

    def test_3_sv_index_add_elwidth(self):
        """sets VL=6 (via SVSTATE) then does svindex with elwidth=8, and an add.

        only RA is re-mapped via Indexing, not RB or RT
        """
        isa = SVP64Asm(['svindex 8, 1, 1, 3, 0, 0, 0',
                        'sv.add *8, *0, *0',
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        idxs = [1, 0, 5, 2, 4, 3] # random enough
        for i in range(6):
            # 8-bit indices starting at reg 16
            set_masked_reg(initial_regs, 16, i, ew_bits=8, value=idxs[i])
            initial_regs[i] = i

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 6 # VL
        svstate.maxvl = 6 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running
        expected_regs = deepcopy(initial_regs)
        for i in range(6):
            RA = initial_regs[0+idxs[i]]
            RB = initial_regs[0+i]
            expected_regs[i+8] = RA+RB
            print ("expected", i, expected_regs[i+8])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print (sim.gpr.dump())
            self.assertEqual(sim.svstate.RMpst, 0) # mm=0 so persist=0
            self.assertEqual(sim.svstate.SVme, 0b00001) # same as rmm
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 0)
            self.assertEqual(sim.svstate.mi2, 0)
            self.assertEqual(sim.svstate.mo0, 0)
            self.assertEqual(sim.svstate.mo1, 0)
            self.assertEqual(SVSHAPE0.svgpr, 16) # SVG is shifted up by 1
            for i in range(1,4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 0)
            self._check_regs(sim, expected_regs)

    def test_1_sv_index_rot32(self):
        """sets VL=8 (via SVSTATE) then does modulo 4 svindex, and a rotate.

        RA is re-mapped via Indexing,
        RB is re-mapped via different Indexing,
        """
        isa = SVP64Asm([
                        'svindex 14, 5, 4, 3, 0, 1, 0', # SVSHAPE1, RB, mod 4
                        'svindex 12, 8, 1, 3, 0, 1, 0', # SVSHAPE0, RS
                        'sv.rlwnm *8, *0, *16, 0, 31',
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 128
        idxs = [1, 0, 5, 2, 4, 3, 7, 6] # random enough
        for i in range(8):
            set_masked_reg(initial_regs, 24, i, ew_bits=8, value=idxs[i])
            initial_regs[i] = i
        shifts = [16, 12, 8, 7] # chacha20 shifts
        idxs2 = [1, 2, 3, 0] # cycle order (for fun)
        for i in range(4):
            set_masked_reg(initial_regs, 28, i, ew_bits=8, value=idxs2[i])
            initial_regs[16+i] = shifts[i]

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 8 # VL
        svstate.maxvl = 8 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running, compute expected results
        expected_regs = deepcopy(initial_regs)
        for i in range(8):
            RS = initial_regs[0+idxs[i%8]]
            RB = initial_regs[16+idxs2[i%4]]
            expected_regs[i+8] = rotl32(RS, RB)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            # print out expected regs
            for i in range(8):
                RS = initial_regs[0+idxs[i%8]]
                RB = initial_regs[16+idxs2[i%4]]
                print ("expected", i, hex(RS), hex(RB), hex(expected_regs[i+8]))

            print (sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            SVSHAPE1 = sim.spr['SVSHAPE1']
            print ("SVSTATE after", bin(sim.svstate.asint()))
            print ("        vl", bin(sim.svstate.vl))
            print ("        mvl", bin(sim.svstate.maxvl))
            print ("    srcstep", bin(sim.svstate.srcstep))
            print ("    dststep", bin(sim.svstate.dststep))
            print ("      RMpst", bin(sim.svstate.RMpst))
            print ("       SVme", bin(sim.svstate.SVme))
            print ("        mo0", bin(sim.svstate.mo0))
            print ("        mo1", bin(sim.svstate.mo1))
            print ("        mi0", bin(sim.svstate.mi0))
            print ("        mi1", bin(sim.svstate.mi1))
            print ("        mi2", bin(sim.svstate.mi2))
            print ("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print ("STATE0 xdim", SVSHAPE0.xdimsz)
            print ("STATE0 ydim", SVSHAPE0.ydimsz)
            print ("STATE0 skip", bin(SVSHAPE0.skip))
            print ("STATE0  inv", SVSHAPE0.invxyz)
            print ("STATE0order", SVSHAPE0.order)
            print (sim.gpr.dump())
            self._check_regs(sim, expected_regs)
            self.assertEqual(sim.svstate.RMpst, 1) # mm=1 so persist=1
            self.assertEqual(sim.svstate.SVme, 0b10010) # RS and RB active
            # rmm is 0b00001 which means mi0=0 and all others inactive (0)
            self.assertEqual(sim.svstate.mi0, 0) # RS
            self.assertEqual(sim.svstate.mi1, 1) # RB
            self.assertEqual(sim.svstate.mi2, 0) # ignore
            self.assertEqual(sim.svstate.mo0, 0) # ignore
            self.assertEqual(sim.svstate.mo1, 0) # ignore
            self.assertEqual(SVSHAPE0.svgpr, 24) # SVG is shifted up by 1
            self.assertEqual(SVSHAPE1.svgpr, 28) # SVG is shifted up by 1
            for i in range(2,4):
                shape = sim.spr['SVSHAPE%d' % i]
                self.assertEqual(shape.svgpr, 0)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

