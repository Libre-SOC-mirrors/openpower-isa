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


def transform_radix2_complex(vec_r, vec_i, cos_r, sin_i):
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
    n = len(vec_r)
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

                print ("xform jl jh k", jl, jh, k,
                        "vr h l", vec_r[jh], vec_r[jl],
                        "vi h l", vec_i[jh], vec_i[jl])
                print ("    cr k", cos_r[k], "si k", sin_i[k])
                mul1_r =  vec_r[jh] * cos_r[k]
                mul2_r = vec_i[jh] * sin_i[k]
                tpre =  mul1_r + mul2_r
                print ("        vec_r[jh] * cos_r[k]", mul1_r)
                print ("        vec_i[jh] * sin_i[k]", mul2_r)
                print ("    tpre", tpre)
                mul1_i = vec_r[jh] * sin_i[k]
                mul2_i = vec_i[jh] * cos_r[k]
                tpim = -mul1_i + mul2_i
                print ("        vec_r[jh] * sin_i[k]", mul1_i)
                print ("        vec_i[jh] * cos_r[k]", mul2_i)
                print ("    tpim", tpim)
                vec_r[jh] = vec_r[jl] - tpre
                vec_i[jh] = vec_i[jl] - tpim
                vec_r[jl] += tpre
                vec_i[jl] += tpim

                print ("    xform jl jh k", jl, jh, k,
                        "\n       vr h l", vec_r[jh], vec_r[jl],
                        "\n       vi h l", vec_i[jh], vec_i[jl])
                k += tablestep
        size *= 2

    return vec_r, vec_i


class FFTTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_remap_fpmadds_fft(self):
        """>>> lst = ["svshape 8, 1, 1, 1, 0",
                     "svremap 31, 1, 0, 2, 0, 1",
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
        lst = SVP64Asm( ["svshape 8, 1, 1, 1, 0",
                         "svremap 31, 1, 0, 2, 0, 1",
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

    def test_sv_remap_fpmadds_fft_svstep(self):
        """>>> lst = SVP64Asm( [
                            "svshape 8, 1, 1, 1, 1",
                             "svremap 31, 1, 0, 2, 0, 1",
                            "sv.ffmadds 0.v, 0.v, 0.v, 8.v",
                            "setvl. 0, 0, 1, 1, 0, 0",
                            "bc 4, 2, -16"
                            ])
            runs a full in-place O(N log2 N) butterfly schedule for
            Discrete Fourier Transform.  this version however uses
            SVP64 "Vertical-First" Mode and so needs an explicit
            branch, testing CR0.

            SVP64 "REMAP" in Butterfly Mode is applied to a twin +/- FMAC
            (3 inputs, 2 outputs)
        """
        lst = SVP64Asm( [
                        "svshape 8, 1, 1, 1, 1",
                         "svremap 31, 1, 0, 2, 0, 1",
                        "sv.ffmadds 0.v, 0.v, 0.v, 8.v",
                        "setvl. 0, 0, 1, 1, 0, 0",
                        "bc 4, 2, -16"
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
        svstate.vl = VL # VL
        svstate.maxvl = VL # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

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

    def test_sv_remap_fpmadds_fft_svstep_scalar_temp(self):
        """>>> lst = SVP64Asm( [
                        "svshape 8, 1, 1, 1, 1",
                         # RA: jh (S1) RB: n/a RC: k (S2) RT: scalar EA: n/a
                         "svremap 5, 1, 0, 2, 0, 0",
                         "sv.fmuls 24, 0.v, 8.v",
                         # RA: scal RB: jl (S0) RC: n/a RT: jl (S0) EA: jh (S1)
                         "svremap 26, 0, 0, 0, 0, 1",
                        "sv.ffadds 0.v, 24, 0.v",
                        "setvl. 0, 0, 1, 1, 0, 0",
                        "bc 4, 2, -28"
                            ])

            runs a full in-place O(N log2 N) butterfly schedule for
            Discrete Fourier Transform.  also uses "Vertical First"
            but also uses temporary scalars and ffadds rather than
            sv.ffmadds.

            this represents an incremental step towards complex FFT

            SVP64 "REMAP" in Butterfly Mode is applied to two instructions:

            * single fmuls FRT, FRA, FRC
            * twin in-place ffadds +/- ADD/SUB (2 inputs, 2 outputs)
              (FRS is implicit / hidden in ff* operations)

            multiply:                         # sv.fmuls FRT, FRA, FRC
                temp1 = vec[jh] * exptable[k]
                temp2 = vec[jl]
            twin-add:                         # sv.ffadds FRT(/FRS), FRA, FRB
                vec[jh] = temp2 - temp1
                vec[jl] = temp2 + temp1
        """
        lst = SVP64Asm( [
                        "svshape 8, 1, 1, 1, 1",
                         # RA: jh (S1) RB: n/a RC: k (S2) RT: scalar EA: n/a
                         "svremap 5, 1, 0, 2, 0, 0",
                         "sv.fmuls 24, 0.v, 8.v",
                         # RA: scal RB: jl (S0) RC: n/a RT: jl (S0) EA: jh (S1)
                         "svremap 26, 0, 0, 0, 0, 1",
                        "sv.ffadds 0.v, 24, 0.v",
                        "setvl. 0, 0, 1, 1, 0, 0",
                        "bc 4, 2, -28"
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
        svstate.vl = VL # VL
        svstate.maxvl = VL # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

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
        svstate.vl = 4 # VL
        svstate.maxvl = 4 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_fprs=fprs)
            # confirm that the results are as expected
            for i, (t, u) in enumerate(res):
                self.assertEqual(sim.fpr(i+2), t)
                self.assertEqual(sim.fpr(i+6), u)

    def test_sv_ffadds_fft(self):
        """>>> lst = ["sv.ffadds 2.v, 2.v, 2.v"
                        ]
            four in-place vector adds, four in-place vector subs

            SVP64 "FFT" mode will *automatically* offset FRB and an implicit
            FRS to perform the two multiplies.  one add, one subtract.

            sv.ffadds FRT, FRA, FRB  actually does:
                fadds FRT   , FRB, FRA
                fsubs FRT+vl, FRA, FRB+vl
        """
        lst = SVP64Asm(["sv.ffadds 2.v, 2.v, 2.v"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        av = [7.0, -9.8, 2.0, -32.3] # first half of array 0..3
        bv = [-2.0, 2.0, -9.8, 32.3] # second half of array 4..7
        res = []
        # work out the results with the twin add-sub
        for i, (a, b) in enumerate(zip(av, bv)):
            fprs[i+2] = fp64toselectable(a)
            fprs[i+6] = fp64toselectable(b)
            t = b + a
            u = b - a
            t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            res.append((t, u))
            print ("FFT", i, "in", a, b, "res", t, u)

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
                a = float(sim.fpr(i+2))
                b = float(sim.fpr(i+6))
                t = float(t)
                u = float(u)
                print ("FFT", i, "in", a, b, "res", t, u)
            for i, (t, u) in enumerate(res):
                self.assertEqual(sim.fpr(i+2), t)
                self.assertEqual(sim.fpr(i+6), u)

    def test_sv_remap_fpmadds_fft_svstep_complex(self):
        """
            runs a full in-place O(N log2 N) butterfly schedule for
            Discrete Fourier Transform.  this version however uses
            SVP64 "Vertical-First" Mode and so needs an explicit
            branch, testing CR0.

            SVP64 "REMAP" in Butterfly Mode is applied to a twin +/- FMAC
            (3 inputs, 2 outputs)

            complex calculation (FFT):

                tpre =  vec_r[jh] * cos_r[k] + vec_i[jh] * sin_i[k]
                vec_r[jh] = vec_r[jl] - tpre
                vec_r[jl] += tpre

                tpim = -vec_r[jh] * sin_i[k] + vec_i[jh] * cos_r[k]
                vec_i[jh] = vec_i[jl] - tpim
                vec_i[jl] += tpim

            real-only calculation (DFT):

                temp1 = vec[jh] * exptable[k]
                temp2 = vec[jl]
                vec[jh] = temp2 - temp1
                vec[jl] = temp2 + temp1
        """
        lst = SVP64Asm( [
                        # set triple butterfly mode
                        "svshape 8, 1, 1, 1, 1",
                        # tpre
                        "svremap 5, 1, 0, 2, 0, 0",
                        "sv.fmuls 24, 0.v, 16.v",    # mul1_r = r*cos_r
                        "svremap 5, 1, 0, 2, 0, 0",
                        "sv.fmadds 24, 8.v, 20.v, 24", # mul2_r = i*sin_i
                                                     # tpre = mul1_r + mul2_r
                        # tpim
                         "svremap 5, 1, 0, 2, 0, 0",
                        "sv.fmuls 26, 0.v, 20.v",    # mul1_i = r*sin_i
                         "svremap 5, 1, 0, 2, 0, 0",
                        "sv.fmsubs 26, 8.v, 16.v, 26", # mul2_i = i*cos_r
                                                     # tpim = mul2_i - mul1_i
                        # vec_r jh/jl
                         "svremap 26, 0, 0, 0, 0, 1",
                        "sv.ffadds 0.v, 24, 0.v",    # vh/vl +/- tpre
                        # vec_i jh/jl
                         "svremap 26, 0, 0, 0, 0, 1",
                        "sv.ffadds 8.v, 26, 8.v",    # vh/vl +- tpim

                        # svstep loop
                        "setvl. 0, 0, 1, 1, 0, 0",
                        "bc 4, 2, -76"
                        ])
        lst = list(lst)

        # array and coefficients to test
        ar = [7.0, -9.8, 3.0, -32.3,
              -2.0, 5.0, -9.8, 31.3] # array 0..7 real
        ai = [1.0, -1.8, 3.0, 19.3,
              4.0, -2.0, -0.8, 1.3] # array 0..7 imaginary
        coer = [-0.25, 0.5, 3.1, 6.2] # coefficients real
        coei = [0.21, -0.1, 1.1, -4.0] # coefficients imaginary

        # store in regfile
        fprs = [0] * 64
        for i, a in enumerate(ar):
            fprs[i+0] = fp64toselectable(a)
        for i, a in enumerate(ai):
            fprs[i+8] = fp64toselectable(a)
        for i, cr in enumerate(coer):
            fprs[i+16] = fp64toselectable(cr)
        for i, ci in enumerate(coei):
            fprs[i+20] = fp64toselectable(ci)

        # set total. err don't know how to calculate how many there are...
        # do it manually for now
        VL = 0
        size = 2
        n = len(ar)
        while size <= n:
            halfsize = size // 2
            tablestep = n // size
            for i in range(0, n, size):
                for j in range(i, i + halfsize):
                    VL += 1
            size *= 2

        # SVSTATE (calculated VL)
        svstate = SVP64State()
        svstate.vl = VL # VL
        svstate.maxvl = VL # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

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

            # work out the results with the twin mul/add-sub, explicit
            # complex numbers
            res_r, res_i = transform_radix2_complex(ar, ai, coer, coei)

            for i, (expected_r, expected_i) in enumerate(zip(res_r, res_i)):
                print ("i", i, float(sim.fpr(i)), float(sim.fpr(i+8)),
                       "expected_r", expected_r,
                       "expected_i", expected_i)
            for i, (expected_r, expected_i) in enumerate(zip(res_r, res_i)):
                # convert to Power single
                expected_r = DOUBLE2SINGLE(fp64toselectable(expected_r ))
                expected_r = float(expected_r)
                actual_r = float(sim.fpr(i))
                # approximate error calculation, good enough test
                # reason: we are comparing FMAC against FMUL-plus-FADD-or-FSUB
                # and the rounding is different
                err = abs(actual_r - expected_r ) / expected_r
                self.assertTrue(err < 1e-6)
                # convert to Power single
                expected_i = DOUBLE2SINGLE(fp64toselectable(expected_i ))
                expected_i = float(expected_i)
                actual_i = float(sim.fpr(i+8))
                # approximate error calculation, good enough test
                # reason: we are comparing FMAC against FMUL-plus-FADD-or-FSUB
                # and the rounding is different
                err = abs(actual_i - expected_i ) / expected_i
                self.assertTrue(err < 1e-6)

    def test_sv_ffadds_fft_scalar(self):
        """>>> lst = ["sv.ffadds 2.v, 12, 13"
                        ]
            four in-place vector adds and subs, but done with a scalar
            pair (fp12, fp13)
        """
        lst = SVP64Asm(["sv.ffadds 2.v, 12, 13"
                        ])
        lst = list(lst)

        fprs = [0] * 32
        scalar_a = 1.3
        scalar_b = -2.0
        fprs[12] = fp64toselectable(scalar_a)
        fprs[13] = fp64toselectable(scalar_b)
        res = []
        # work out the results with the twin add-sub
        for i in range(4):
            t = scalar_b + scalar_a
            u = scalar_b - scalar_a
            t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            res.append((t, u))
            print ("FFT", i, "res", t, u)

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
                a = float(sim.fpr(i+2))
                b = float(sim.fpr(i+6))
                t = float(t)
                u = float(u)
                print ("FFT", i, "in", a, b, "res", t, u)
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
