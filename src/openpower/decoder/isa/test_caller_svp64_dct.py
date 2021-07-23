from nmigen import Module, Signal
from nmigen.back.pysim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.isa.test_caller import run_tst
from openpower.sv.trans.svp64 import SVP64Asm
from copy import deepcopy
from openpower.decoder.helpers import fp64toselectable, SINGLE
from openpower.decoder.isafunctions.double2single import DOUBLE2SINGLE
from openpower.decoder.isa.remap_dct_yield import (halfrev2, reverse_bits,
                                         iterate_dct_inner_butterfly_indices)


def transform_inner_radix2(vec, ctable):

    # Initialization
    n = len(vec)
    print ()
    print ("transform2", n)
    levels = n.bit_length() - 1

    # reference (read/write) the in-place data in *reverse-bit-order*
    ri = list(range(n))
    ri = [ri[reverse_bits(i, levels)] for i in range(n)]

    # and pretend we LDed data in half-swapped *and* bit-reversed order as well
    # TODO: merge these two
    vec = halfrev2(vec, False)
    vec = [vec[ri[i]] for i in range(n)]

    ################
    # INNER butterfly
    ################
    xdim = n
    ydim = 0
    zdim = 0

    # set up an SVSHAPE
    class SVSHAPE:
        pass
    # j schedule
    SVSHAPE0 = SVSHAPE()
    SVSHAPE0.lims = [xdim, ydim, zdim]
    SVSHAPE0.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE0.mode = 0b01
    SVSHAPE0.submode2 = 0b01
    SVSHAPE0.skip = 0b00
    SVSHAPE0.offset = 0       # experiment with different offset, here
    SVSHAPE0.invxyz = [1,0,0] # inversion if desired
    # j+halfstep schedule
    SVSHAPE1 = SVSHAPE()
    SVSHAPE1.lims = [xdim, ydim, zdim]
    SVSHAPE1.order = [0,1,2]  # experiment with different permutations, here
    SVSHAPE1.mode = 0b01
    SVSHAPE1.submode2 = 0b01
    SVSHAPE1.skip = 0b01
    SVSHAPE1.offset = 0       # experiment with different offset, here
    SVSHAPE1.invxyz = [1,0,0] # inversion if desired

    # enumerate over the iterator function, getting new indices
    i0 = iterate_dct_inner_butterfly_indices(SVSHAPE0)
    i1 = iterate_dct_inner_butterfly_indices(SVSHAPE1)
    for k, ((jl, jle), (jh, jhe)) in enumerate(zip(i0, i1)):
        t1, t2 = vec[jl], vec[jh]
        coeff = ctable[k]
        vec[jl] = t1 + t2
        vec[jh] = (t1 - t2) * (1.0/coeff)
        print ("coeff", "ci", k,
                "jl", jl, "jh", jh,
               "i/n", (k+0.5), 1.0/coeff,
                "t1, t2", t1, t2, "res", vec[jl], vec[jh],
                "end", bin(jle), bin(jhe))
        if jle == 0b111: # all loops end
            break

    return vec


class DCTTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_ffadds_dct(self):
        """>>> lst = ["sv.fdmadds 0.v, 0.v, 0.v, 8.v"
                        ]
            four in-place vector adds, four in-place vector mul-subs

            SVP64 "DCT" mode will *automatically* offset FRB and an implicit
            FRS to perform the two multiplies.  one add, one subtract.

            sv.fdadds FRT, FRA, FRC, FRB  actually does:
                fadds FRT   , FRB, FRA
                fsubs FRT+vl, FRA, FRB+vl
        """
        lst = SVP64Asm(["sv.fdmadds 0.v, 0.v, 0.v, 8.v"
                        ])
        lst = list(lst)

        # cheat here with these values, they're selected so that
        # rounding errors do not occur. sigh.
        fprs = [0] * 32
        av = [7.0, -0.8, 2.0, -2.3] # first half of array 0..3
        bv = [-2.0, 2.0, -0.8, 1.4] # second half of array 4..7
        cv = [-1.0, 0.5, 2.5, -0.25]  # coefficients
        res = []
        # work out the results with the twin add-sub
        for i, (a, b, c) in enumerate(zip(av, bv, cv)):
            fprs[i+0] = fp64toselectable(a)
            fprs[i+4] = fp64toselectable(b)
            fprs[i+8] = fp64toselectable(c)
            # this isn't quite a perfect replication of the
            # FP32 mul-add-sub.  better really to use FPMUL32, FPADD32
            # and FPSUB32 directly to be honest.
            t = a + b
            diff = (a - b)
            diff = DOUBLE2SINGLE(fp64toselectable(diff)) # FP32 round
            diff = float(diff)
            u = diff * c
            tc = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            uc = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            res.append((uc, tc))
            print ("DCT", i, "in", a, b, "c", c, "res", t, u)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            # confirm that the results are as expected
            for i, (t, u) in enumerate(res):
                a = float(sim.fpr(i+0))
                b = float(sim.fpr(i+4))
                t = float(t)
                u = float(u)
                print ("DCT", i, "in", a, b, "res", t, u)
            for i, (t, u) in enumerate(res):
                self.assertEqual(sim.fpr(i+0), t)
                self.assertEqual(sim.fpr(i+4), u)

    def test_sv_remap_fpmadds_dct_4(self):
        """>>> lst = ["svshape 4, 1, 1, 2, 0",
                     "svremap 27, 1, 0, 2, 0, 1, 0",
                        "sv.fdmadds 0.v, 0.v, 0.v, 8.v"
                     ]
            runs a full in-place 4-long O(N log2 N) inner butterfly schedule
            for DCT

            SVP64 "REMAP" in Butterfly Mode is applied to a twin +/- FMAC
            (3 inputs, 2 outputs)

            Note that the coefficient (FRC) is not on a "schedule", it
            is straight Vectorised (0123...) because DCT coefficients
            cannot be shared between butterfly layers (due to +0.5)
        """
        lst = SVP64Asm( ["svshape 4, 1, 1, 2, 0",
                         "svremap 27, 1, 0, 2, 0, 1, 0",
                         "sv.fdmadds 0.v, 0.v, 0.v, 8.v"
                        ])
        lst = list(lst)

        # array and coefficients to test
        n = 4
        av = [7.0, -9.8, 3.0, -32.3]
        coe = [-0.25, 0.5, 3.1, 6.2] # 4 coefficients

        levels = n.bit_length() - 1
        ri = list(range(n))
        ri = [ri[reverse_bits(i, levels)] for i in range(n)]
        avi = [7.0, -0.8, 2.0, -2.3] # first half of array 0..3
        av = halfrev2(avi, False)
        av = [av[ri[i]] for i in range(n)]

        # store in regfile
        fprs = [0] * 32
        for i, c in enumerate(coe):
            fprs[i+8] = fp64toselectable(1.0 / c) # invert
        for i, a in enumerate(av):
            fprs[i+0] = fp64toselectable(a)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print ("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print ("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])

            # work out the results with the twin mul/add-sub
            res = transform_inner_radix2(avi, coe)

            for i, expected in enumerate(res):
                print ("i", i, float(sim.fpr(i)), "expected", expected)
            for i, expected in enumerate(res):
                # convert to Power single
                expected = DOUBLE2SINGLE(fp64toselectable(expected))
                expected = float(expected)
                actual = float(sim.fpr(i))
                # approximate error calculation, good enough test
                # reason: we are comparing FMAC against FMUL-plus-FADD-or-FSUB
                # and the rounding is different
                err = abs((actual - expected) / expected)
                print ("err", i, err)
                self.assertTrue(err < 1e-6)

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None,
                              initial_mem=None,
                              initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                                                initial_fprs=initial_fprs,
                                                svstate=svstate)

        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()

        return simulator


if __name__ == "__main__":
    unittest.main()
