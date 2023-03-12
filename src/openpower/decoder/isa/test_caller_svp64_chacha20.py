"""SVP64 unit test for svindex
svindex SVG,rmm,SVd,ew,yx,mm,sk
"""
import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.caller import SVP64State, set_masked_reg
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.sv.trans.svp64 import SVP64Asm


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
    print("op rotl32", hex(res), hex(v), hex(c))
    return res


def add(a, b):
    res = (a + b) & 0xffffffff
    print("op add", hex(res), hex(a), hex(b))
    return res


def xor(a, b):
    res = a ^ b
    print("op xor", hex(res), hex(a), hex(b))
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


class SVSTATETestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        print("GPR")
        sim.gpr.dump()
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64),
                             "GPR %d %x expected %x" % (i, sim.gpr(i).value, expected[i]))

    def test_1_sv_chacha20_main_rounds(self):
        """chacha20 main rounds

        RA, RB, RS and RT are set up via Indexing to perform the *individual*
        add/xor/rotl32 operations (with elwidth=32)

        the inner loop uses "svstep." which detects src/dst-step reaching
        the end of the loop, setting CR0.eq=1.  no need for an additional
        counter-register-with-a-decrement.  this has the side-effect of
        freeing up CTR for use as a straight decrement-counter.

        both loops are 100% deterministic meaning that there should be
        *ZERO* branch-prediction misses, obviating a need for loop-unrolling.
        """

        nrounds = 2  # should be 10 for full algorithm
        block = 64 # register for block of 16

        isa = SVP64Asm([
            # set up VL=32 vertical-first, and SVSHAPEs 0-2
            # vertical-first, set MAXVL (and r17)
            'setvl 17, 0, 32, 1, 0, 1',
            'svindex 11, 0, 1, 3, 0, 1, 0',  # SVSHAPE0, a
            'svindex 15, 1, 1, 3, 0, 1, 0',  # SVSHAPE1, b
            'svindex 19, 2, 1, 3, 0, 1, 0',  # SVSHAPE2, c
            'svshape2 0, 0, 3, 4, 0, 1',  # SVSHAPE3, shift amount, mod 4
            # establish CTR for outer round count
            'addi 16, 0, %d' % nrounds,     # set number of rounds
            'mtspr 9, 16',                  # set CTR to number of rounds
            # outer loop begins here (standard CTR loop)
            'setvl 17, 17, 32, 1, 1, 0',    # vertical-first, set VL from r17
            # inner loop begins here. add-xor-rotl32 with remap, step, branch
            'svremap 31, 1, 0, 0, 0, 0, 0',  # RA=1, RB=0, RT=0 (0b01011)
            'sv.add/w=32 *%d, *%d, *%d' % (block, block, block),
            'svremap 31, 2, 0, 2, 2, 0, 0',  # RA=2, RB=0, RS=2 (0b00111)
            'sv.xor/w=32 *%d, *%d, *%d' % (block, block, block),
            'svremap 31, 0, 3, 2, 2, 0, 0',  # RA=2, RB=3, RS=2 (0b01110)
            'sv.rldcl/w=32 *%d, *%d, *18, 0' % (block, block),
            'svstep. 16, 1, 0',              # step to next in-regs element
            'bc 6, 3, -0x28',               # svstep. Rc=1 loop-end-condition?
            # inner-loop done: outer loop standard CTR-decrement to setvl again
            'bc 16, 0, -0x30',
        ])
        lst = list(isa)
        print("listing", lst)

        schedule = []
        chacha_idx_schedule(schedule, fn=quarter_round_schedule)

        # initial values in GPR regfile
        initial_regs = [0] * 128

        # offsets for a b c
        for i, (a, b, c, d) in enumerate(schedule):
            print ("chacha20 schedule", i, hex(a), hex(b), hex(c), hex(d))
            set_masked_reg(initial_regs, 22, i, ew_bits=8, value=a)
            set_masked_reg(initial_regs, 30, i, ew_bits=8, value=b)
            set_masked_reg(initial_regs, 38, i, ew_bits=8, value=c)

        # offsets for d (modulo 4 shift amount)
        shifts = [16, 12, 8, 7]  # chacha20 shifts
        for i in range(4):
            set_masked_reg(initial_regs, 18, i, ew_bits=32, value=shifts[i])

        # set up input test vector then pack it into regs
        x = [0] * 16
        for i in range(16):
            x[i] = i << 1
        for i in range(16):
            set_masked_reg(initial_regs, block, i, ew_bits=32, value=x[i])

        # SVSTATE vl=32
        svstate = SVP64State()
        svstate.vl = 32  # VL
        svstate.maxvl = 32  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        # copy before running, compute expected results
        expected_regs = deepcopy(initial_regs)
        expected_regs[16] = 0  # reaches zero
        expected_regs[17] = 32  # gets set to MAXVL
        expected = deepcopy(x)
        for i in range(nrounds):
            chacha_idx_schedule(expected, fn=quarter_round)
        for i in range(16):
            set_masked_reg(expected_regs, block, i, ew_bits=32,
                           value=expected[i])

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate=svstate)

            # print out expected: 16 values @ 32-bit ea -> QTY8 64-bit regs
            for i in range(8):
                RS = sim.gpr(i+block).value
                print("expected", i+block, hex(RS), hex(expected_regs[i+block]))

            print(sim.spr)
            SVSHAPE0 = sim.spr['SVSHAPE0']
            SVSHAPE1 = sim.spr['SVSHAPE1']
            print("SVSTATE after", bin(sim.svstate.asint()))
            print("        vl", bin(sim.svstate.vl))
            print("        mvl", bin(sim.svstate.maxvl))
            print("    srcstep", bin(sim.svstate.srcstep))
            print("    dststep", bin(sim.svstate.dststep))
            print("      RMpst", bin(sim.svstate.RMpst))
            print("       SVme", bin(sim.svstate.SVme))
            print("        mo0", bin(sim.svstate.mo0))
            print("        mo1", bin(sim.svstate.mo1))
            print("        mi0", bin(sim.svstate.mi0))
            print("        mi1", bin(sim.svstate.mi1))
            print("        mi2", bin(sim.svstate.mi2))
            print("STATE0svgpr", hex(SVSHAPE0.svgpr))
            print("STATE0 xdim", SVSHAPE0.xdimsz)
            print("STATE0 ydim", SVSHAPE0.ydimsz)
            print("STATE0 skip", bin(SVSHAPE0.skip))
            print("STATE0  inv", SVSHAPE0.invxyz)
            print("STATE0order", SVSHAPE0.order)
            print(sim.gpr.dump())
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
