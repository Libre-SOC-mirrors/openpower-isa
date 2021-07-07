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
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isafunctions.double2single import DOUBLE2SINGLE


def transform_radix2(vec, exptable):
    """
    # FFT and convolution test (Python), based on Project Nayuki
    #
    # Copyright (c) 2020 Project Nayuki. (MIT License)
    # https://www.nayuki.io/page/free-small-fft-in-multiple-languages

    """
    # bits of the integer 'val'.
    def reverse_bits(val, width):
        result = 0
        for _ in range(width):
            result = (result << 1) | (val & 1)
            val >>= 1
        return result

    # Initialization
    n = len(vec)
    levels = n.bit_length() - 1

    # Copy with bit-reversed permutation
    #vec = [vec[reverse_bits(i, levels)] for i in range(n)]

    size = 2
    while size <= n:
        halfsize = size // 2
        tablestep = n // size
        for i in range(0, n, size):
            k = 0
            for j in range(i, i + halfsize):
                # exact same actual computation, just embedded in
                # triple-nested for-loops
                jl, jh = j, j+halfsize
                vjh = vec[jh]
                temp1 = vec[jh] * exptable[k]
                temp2 = vec[jl]
                vec[jh] = temp2 - temp1
                vec[jl] = temp2 + temp1
                print ("xform jl jh k", jl, jh, k,
                       "vj vjh ek", temp2, vjh, exptable[k],
                       "t1, t2", temp1, temp2,
                       "v[jh] v[jl]", vec[jh], vec[jl])
                k += tablestep
        size *= 2

    return vec


class FFTTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_remap_fpmadds_fft(self):
        """>>> lst = ["svremap 8, 1, 1, 1",
                      "sv.ffmadds 2.v, 2.v, 2.v, 10.v"
                     ]
            runs a full in-place O(N log2 N) butterfly schedule for
            Discrete Fourier Transform.

            this is the twin "butterfly" mul-add-sub from Cooley-Tukey
            https://en.wikipedia.org/wiki/Cooley%E2%80%93Tukey_FFT_algorithm#Data_reordering,_bit_reversal,_and_in-place_algorithms

            there is the *option* to target a different location (non-in-place)
            just in case.

            SVP64 "REMAP" in Butterfly Mode is applied to a twin +/- FMAC
            (3 inputs, 2 outputs)
        """
        lst = SVP64Asm( ["svremap 8, 1, 1, 1",
                        "sv.ffmadds 0.v, 0.v, 0.v, 8.v"
                        ])
        lst = list(lst)

        # array and coefficients to test
        av = [7.0, -9.8, 3.0, -32.3,
              -2.0, 5.0, -9.8, 31.3] # array 0..7
        coe = [-0.25, 0.5, 3.1, 6.2] # coefficients

        # store in regfile
        fprs = [0] * 32
        for i, c in enumerate(coe):
            fprs[i+8] = fp64toselectable(c)
        for i, a in enumerate(av):
            fprs[i+0] = fp64toselectable(a)

        # set total. err don't know how to calculate how many there are...
        # do it manually for now
        VL = 0
        size = 2
        n = len(av)
        while size <= n:
            halfsize = size // 2
            tablestep = n // size
            for i in range(0, n, size):
                for j in range(i, i + halfsize):
                    VL += 1
            size *= 2

        # SVSTATE (calculated VL)
        svstate = SVP64State()
        svstate.vl[0:7] = VL # VL
        svstate.maxvl[0:7] = VL # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print ("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print ("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])

            # work out the results with the twin mul/add-sub
            res = transform_radix2(av, coe)

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
                err = abs(actual - expected) / expected
                self.assertTrue(err < 1e-7)


    def test_sv_fpmadds_fft(self):
        """>>> lst = ["sv.ffmadds 2.v, 2.v, 2.v, 10.v"
                        ]
            four in-place vector mul-adds, four in-place vector mul-subs

            this is the twin "butterfly" mul-add-sub from Cooley-Tukey
            https://en.wikipedia.org/wiki/Cooley%E2%80%93Tukey_FFT_algorithm#Data_reordering,_bit_reversal,_and_in-place_algorithms

            there is the *option* to target a different location (non-in-place)
            just in case.

            SVP64 "FFT" mode will *automatically* offset FRB and an implicit
            FRS to perform the two multiplies.  one add, one subtract.

            sv.ffmadds FRT, FRA, FRC, FRB  actually does:
                fmadds  FRT   , FRA, FRC, FRA
                fnmsubs FRT+vl, FRA, FRC, FRB+vl
        """
        lst = SVP64Asm(["sv.ffmadds 2.v, 2.v, 2.v, 10.v"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        av = [7.0, -9.8, 2.0, -32.3] # first half of array 0..3
        bv = [-2.0, 2.0, -9.8, 32.3] # second half of array 4..7
        coe = [-1.0, 4.0, 3.1, 6.2]  # coefficients
        res = []
        # work out the results with the twin mul/add-sub
        for i, (a, b, c) in enumerate(zip(av, bv, coe)):
            fprs[i+2] = fp64toselectable(a)
            fprs[i+6] = fp64toselectable(b)
            fprs[i+10] = fp64toselectable(c)
            mul = a * c
            t = b + mul
            u = b - mul
            t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            res.append((t, u))
            print ("FFT", i, "in", a, b, "coeff", c, "mul", mul, "res", t, u)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl[0:7] = 4 # VL
        svstate.maxvl[0:7] = 4 # MAXVL
        print ("SVSTATE", bin(svstate.spr.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            # confirm that the results are as expected
            for i, (t, u) in enumerate(res):
                self.assertEqual(sim.fpr(i+2), t)
                self.assertEqual(sim.fpr(i+6), u)

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
