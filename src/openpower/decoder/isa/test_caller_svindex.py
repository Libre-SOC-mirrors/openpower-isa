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


# originally from https://github.com/pts/chacha20
def quarter_round_schedule(x, a, b, c, d):
    """collate list of reg-offsets for use with svindex/svremap
    """
    #x[a] = (x[a] + x[b]) & 0xffffffff
    #x[d] = x[d] ^ x[a]
    #x[d] = rotate(x[d], 16)
    x.append((a, b, d, 16))

    #x[c] = (x[c] + x[d]) & 0xffffffff
    #x[b] = x[b] ^ x[c]
    #x[b] = rotate(x[b], 12)
    x.append((c, d, b, 12))

    #x[a] = (x[a] + x[b]) & 0xffffffff
    #x[d] = x[d] ^ x[a]
    #x[d] = rotate(x[d], 8)
    x.append((a, b, d, 8))

    #x[c] = (x[c] + x[d]) & 0xffffffff
    #x[b] = x[b] ^ x[c]
    #x[b] = rotate(x[b], 7)
    x.append((c, d, b, 7))


def rotl32(v, c):
    c = c & 0x1f
    res = ((v << c) & 0xffffffff) | v >> (32 - c)
    print ("op rotl32", hex(res), hex(v), hex(c))
    return res


def add(a, b):
    res = (a + b) & 0xffffffff
    print ("op add", hex(res), hex(a), hex(b))
    return res


def xor(a, b):
    res = a ^ b
    print ("op xor", hex(res), hex(a), hex(b))
    return res


def sthth_round(x, a, b, d, rot):
    x[a] = add(x[a], x[b])
    x[d] = xor(x[d], x[a])
    x[d] = rotl32(x[d], rot)

def quarter_round(x, a, b, c, d):
    """collate list of reg-offsets for use with svindex/svremap
    """
    sthth_round(x, a, b, d, 16)
    sthth_round(x, c, d, b, 12)
    sthth_round(x, a, b, d, 8)
    sthth_round(x, c, d, b, 7)


def chacha_idx_schedule(x, fn=quarter_round_schedule):
    fn(x, 0, 4,  8, 12)
    fn(x, 1, 5,  9, 13)
    fn(x, 2, 6, 10, 14)
    fn(x, 3, 7, 11, 15)
    fn(x, 0, 5, 10, 15)
    fn(x, 1, 6, 11, 12)
    fn(x, 2, 7,  8, 13)
    fn(x, 3, 4,  9, 14)


def get_masked_reg(regs, base, offs, ew_bits):
    # rrrright.  start by breaking down into row/col, based on elwidth
    gpr_offs = offs // (64//ew_bits)
    gpr_col = offs % (64//ew_bits)
    # compute the mask based on ew_bits
    mask = (1<<ew_bits)-1
    # now select the 64-bit register, but get its value (easier)
    val = regs[base+gpr_offs]
    # now mask out the bit we don't want
    val = val & ~(mask << (gpr_col*ew_bits))
    # then return the bits we want, shifted down
    return val >> (gpr_col*ew_bits)


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

        svremap RT=0,RA=1,RB=0
        add r0, r1, r0            RT, RA, RB
        svremap RS=2,RA=2,RB=0    # RB stays = 0
        xor r2, r2, r0            RA, RS, RB
        svremap RS=2,RA=2,RB=3    # RA stays = 2
        rlwnm r2, r2, r3, 0, 31   rlwnm RA,RS,RB,MB,ME (Rc=0)
        """
        isa = SVP64Asm([
            # set up VL=32 vertical-first, and SVSHAPEs 0-2
            'setvl 17, 17, 32, 1, 1, 1',     # vertical-first
            'svindex 11, 0, 1, 3, 0, 1, 0', # SVSHAPE0, a
            'svindex 15, 1, 1, 3, 0, 1, 0', # SVSHAPE1, b
            'svindex 19, 2, 1, 3, 0, 1, 0', # SVSHAPE2, c
            'svindex 21, 3, 4, 3, 0, 1, 0', # SVSHAPE3, shift amount, mod 4
            # inner loop begins here. add-xor-rotl32 with remap, step, branch
            'svremap 31, 1, 0, 0, 0, 0, 0', # RA=1, RB=0, RT=0 (0b01011)
            'sv.add/w=32 *0, *0, *0',
            'svremap 31, 2, 0, 2, 2, 0, 0', # RA=2, RB=0, RS=2 (0b00111)
            'sv.xor/w=32 *0, *0, *0',
            'svremap 31, 0, 3, 2, 2, 0, 0', # RA=2, RB=3, RS=2 (0b01110)
            'sv.rlwnm/w=32 *0, *0, *18, 0, 31',
            'svstep. 17, 1, 0',              # step to next
            'bc 6, 3, -0x28',               # VF loop
                       ])
        lst = list(isa)
        print ("listing", lst)

        schedule = []
        chacha_idx_schedule(schedule, fn=quarter_round_schedule)

        # initial values in GPR regfile
        initial_regs = [0] * 128

        # offsets for a b c
        for i, (a,b,c,d) in enumerate(schedule):
            set_masked_reg(initial_regs, 22, i, ew_bits=8, value=a)
            set_masked_reg(initial_regs, 30, i, ew_bits=8, value=b)
            set_masked_reg(initial_regs, 38, i, ew_bits=8, value=c)

        # offsets for d (modulo 4 shift amount)
        shifts = [16, 12, 8, 7] # chacha20 shifts
        idxs2 = [0, 1, 2, 3] # cycle order (for fun)
        for i in range(4):
            set_masked_reg(initial_regs, 42, i, ew_bits=8, value=idxs2[i])
            set_masked_reg(initial_regs, 18, i, ew_bits=32, value=shifts[i])

        initial_regs[17] = 32 # VL=2
        x = [0] * 16
        for i in range(16):
            x[i] = i<<1
        for i in range(16):
            set_masked_reg(initial_regs, 0, i, ew_bits=32, value=x[i])

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 32 # VL
        svstate.maxvl = 32 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        # copy before running, compute expected results
        expected_regs = deepcopy(initial_regs)
        expected_regs[17] = 0 # reaches zero
        expected = deepcopy(x)
        chacha_idx_schedule(expected, fn=quarter_round)
        for i in range(16):
            set_masked_reg(expected_regs, 0, i, ew_bits=32, value=expected[i])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            # print out expected regs
            for i in range(8):
                RS = sim.gpr(i).value
                print ("expected", i, hex(RS), hex(expected_regs[i]))

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
            self.assertEqual(sim.svstate.RMpst, 0)
            self.assertEqual(sim.svstate.SVme, 0b11111)
            self.assertEqual(sim.svstate.mi0, 0)
            self.assertEqual(sim.svstate.mi1, 3)
            self.assertEqual(sim.svstate.mi2, 2)
            self.assertEqual(sim.svstate.mo0, 2)
            self.assertEqual(sim.svstate.mo1, 0)
            self.assertEqual(SVSHAPE0.svgpr, 22)
            self.assertEqual(SVSHAPE1.svgpr, 30)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()

