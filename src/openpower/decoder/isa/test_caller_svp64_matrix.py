import operator
import unittest
from functools import reduce

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm


# Pure Python implementation of matrix multiply
# Example values
# x = [[1,2,3],[4,5,6],[7,8,9],[10,11,12]]
# y = [[1,2],[1,2],[3,4]]
def matmult(a, b):
    zip_b = list(zip(*b)) # transpose b matrix
    return [[sum(ele_a*ele_b for ele_a, ele_b in zip(row_a, col_b))
             for col_b in zip_b] for row_a in a]

# Flatten list of lists matrix down to single list
def flatten(l):
    return [item for sublist in l for item in sublist]


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_maddld_remap1(self):
        """perform an integer matrix multiply using maddld
                lst = ["svshape 2, 2, 3, 0, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                       "sv.maddld *0, *8, *16, *0"
                        ]
                REMAP maddld RT, RA, RB, RC
        """
        lst = SVP64Asm(["svshape 2, 2, 3, 0, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                        "sv.maddld *0, *16, *32, *0"
                        ])
        lst = list(lst)

        gprs = [0] * 64
        # 3x2 matrix
        X1 = [[1, 2, 3],
              [3, 4, 5],
              ]
        # 2x3 matrix
        Y1 = [[6, 7],
              [8, 9],
              [10, 11],
              ]

        X = X1
        Y = Y1

        expected = matmult(X, Y)
        expected = flatten(expected)
        print("expected-matrix:")
        print(expected)

        xf = reduce(operator.add, X)
        yf = reduce(operator.add, Y)
        print("flattened X,Y,expected")
        print("\t", xf)
        print("\t", yf)
        print("\t", expected)

        # and create a linear result2, same scheme
        #result1 = [0] * (ydim1*xdim2)

        res = []
        # store GPR x-flattened and y-flattened in GPRs
        for i, x in enumerate(xf):
            gprs[i+16] = x  # X matrix
        for i, y in enumerate(yf):
            gprs[i+32] = y  # Y matrix

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            results = []
            for i in range(4):
                results.append(sim.gpr(i).asint())
            for i in range(4):
                print("maddld-matrix i", i, results[i])
            # confirm that the results are as expected
            self.assertEqual(results, expected)

    def test_sv_remap1(self):
        """>>> lst = ["svshape 2, 2, 3, 0, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                       "sv.fmadds *0, *8, *16, *0"
                        ]
                REMAP fmadds FRT, FRA, FRC, FRB
        """
        lst = SVP64Asm(["svshape 2, 2, 3, 0, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                       "sv.fmadds *0, *16, *32, *0"
                        ])
        lst = list(lst)

        fprs = [0] * 64
        # 3x2 matrix
        X1 = [[1, 2, 3],
              [3, 4, 5],
              ]
        # 2x3 matrix
        Y1 = [[6, 7],
              [8, 9],
              [10, 11],
              ]

        X = X1
        Y = Y1

        xf = reduce(operator.add, X)
        yf = reduce(operator.add, Y)
        print("flattened X,Y")
        print("\t", xf)
        print("\t", yf)

        # and create a linear result2, same scheme
        #result1 = [0] * (ydim1*xdim2)

        res = []
        # store FPs
        for i, x in enumerate(xf):
            fprs[i+16] = fp64toselectable(float(x))  # X matrix
        for i, y in enumerate(yf):
            fprs[i+32] = fp64toselectable(float(y))  # Y matrix
            continue
            # t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            # u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            #res.append((t, u))
            # print ("FFT", i, "in", a, b, "coeff", c, "mul",
            #       mul, "res", t, u)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(4):
                print("ffmadds-matrix i", i, float(sim.fpr(i)))
            # confirm that the results are as expected
            # for i, (t, u) in enumerate(res):
            #    self.assertEqual(sim.fpr(i+2), t)
            #    self.assertEqual(sim.fpr(i+6), u)

    def test_sv_remap2(self):
        """>>> lst = ["svshape 5, 4, 3, 0, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                       "sv.fmadds *0, *8, *16, *0"
                        ]
                REMAP fmadds FRT, FRA, FRC, FRB
        """
        lst = SVP64Asm(["svshape 4, 3, 3, 0, 0",
                        "svremap 31, 1, 2, 3, 0, 0, 0",
                       "sv.fmadds *0, *16, *32, *0"
                        ])
        lst = list(lst)

        # 3x2 matrix
        X1 = [[1, 2, 3],
              [3, 4, 5],
              ]
        # 2x3 matrix
        Y1 = [[6, 7],
              [8, 9],
              [10, 11],
              ]

        # test matrices 2
        # 3x3 matrix
        X2 = [[12, 7, 3],
              [4, 5, 6],
              [7, 8, 9],
              ]
        # 3x4 matrix
        Y2 = [[5, 8, 1, 2],
              [6, 7, 3, 0],
              [4, 5, 9, 1]]

        # test matrices 3
        # 3x4 matrix
        X3 = [[12, 7, 3],
              [4, 5, 6],
              [7, 8, 9],
              [2, 0, 1]]
        # 5x3 matrix
        Y3 = [[5, 8, 1, 2, 3],
              [6, 7, 3, 0, 9],
              [4, 5, 9, 1, 2]]

        X = X2
        Y = Y2

        # get the dimensions of the 2 matrices
        xdim1 = len(X[0])
        ydim1 = len(X)
        xdim2 = len(Y[0])
        ydim2 = len(Y)

        print("xdim2 ydim1 ydim2", xdim2, ydim1, ydim2)

        xf = reduce(operator.add, X)
        yf = reduce(operator.add, Y)
        print("flattened X,Y")
        print("\t", xf)
        print("\t", yf)

        # and create a linear result2, same scheme
        #result1 = [0] * (ydim1*xdim2)

        res = []
        # store FPs
        fprs = [0] * 64
        for i, x in enumerate(xf):
            fprs[i+16] = fp64toselectable(float(x))  # X matrix
        for i, y in enumerate(yf):
            fprs[i+32] = fp64toselectable(float(y))  # Y matrix
            continue
            # t = DOUBLE2SINGLE(fp64toselectable(t)) # convert to Power single
            # u = DOUBLE2SINGLE(fp64toselectable(u)) # from double
            #res.append((t, u))
            # print ("FFT", i, "in", a, b, "coeff", c, "mul",
            #       mul, "res", t, u)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(16):
                print("i", i, float(sim.fpr(i)))
            # confirm that the results are as expected
            # for i, (t, u) in enumerate(res):
            #    self.assertEqual(sim.fpr(i+2), t)
            #    self.assertEqual(sim.fpr(i+6), u)

    def test_sv_remap3_horizontal_or(self):
        """>>> lst = ["svshape 3, 2, 1, 0, 0",
                        "svremap 31, 1, 3, 1, 1, 1, 0",
                        "sv.or *0, *0, *6"
                        ]
                REMAP horizontal-or using "or RA,RS,RB"
                same trick can be applied to do horizontal-add
                or horizontal-multiply.  just remember for multiply
                to pre-load 1 (1.0) into the results first (or any other
                scaling factor).

                sv.or is horribly obscure because RA (the destination)
                actually gets treated as RT by the REMAP subsystem.

                The purpose here is to demonstrate a horizontal mapreduce
                by using/abusing Matrix REMAP (ignoring the B-Matrix entirely)

                if data is laid out in R G B R G B R G B format and
                comprises tuples (R<<16 G<<8 B<<0) then a horizontal-or
                may reduce down to (R<<16) | (G<<8> | (B<<0) on a per-row
                basis.
        """
        # 3x4 matrix of data to be ORed together by row.
        # Add any number of extra rows (up to 6) here (6 because sv.or *0,*0,*6)
        X1 = [[0x1, 0x10, 0x100],  # 0x111
              [0x2, 0x40, 0x300],  # 0x342
              [0x9, 0x70, 0x800],  # 0x879
              [0x3, 0x71, 0x460],  # overlaps (still ORed) - 0x473
              ]

        # get the dimensions of the array
        xdim1 = len(X1[0])
        ydim1 = len(X1)

        lst = SVP64Asm(["svshape %d, %d, 1, 0, 0" % (xdim1, ydim1),
                        # also works:
                        # "svremap 31, 3, 0, 3, 1, 2, 0",
                        # "sv.ternlogi *12, *0, *6, 250" # 0b11111110
                        "svremap 31, 1, 3, 1, 1, 1, 0",
                        "sv.or *0, *0, *6"
                        ])
        lst = list(lst)

        print("xdim1, ydim1", xdim1, ydim1)

        expected = [0] * ydim1
        for i, row in enumerate(X1):
            expected[i] = reduce(operator.or_, row)
            print("\texpected ORed", hex(expected[i]))
        xf = reduce(operator.add, X1)
        print("flattened X")
        print("\t", xf)

        res = []
        # store FPs
        gprs = [0] * 64
        for i, x in enumerate(xf):
            gprs[i+6] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, gprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(ydim1):
                print("i", i, sim.gpr(0+i), hex(expected[i]))
            for i in range(ydim1):
                self.assertEqual(sim.gpr(0+i), SelectableInt(expected[i], 64))

    def run_tst_program(self, prog, initial_regs=None,
                        svstate=None,
                        initial_mem=None,
                        initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                            initial_fprs=initial_fprs,
                            svstate=svstate)

        print("GPRs")
        simulator.gpr.dump()
        print("FPRs")
        simulator.fpr.dump()

        return simulator


if __name__ == "__main__":
    unittest.main()
