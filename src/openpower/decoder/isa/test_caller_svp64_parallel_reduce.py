import operator
import unittest

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isa.remap_preduce_yield import preduce_y
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.sv.trans.svp64 import SVP64Asm


def signcopy(x, y):
    y = abs(y)
    if x < 0:
        return -y
    return y


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_remap1(self):
        """>>> lst = ["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 0, 1, 0, 0, 0, 0",
                       "sv.add *0, *8, *16"
                        ]
                REMAP add RT,RA,RB
        """
        lst = SVP64Asm(["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 0, 1, 0, 0, 0, 0",
                       "sv.add *0, *0, *0"
                        ])
        lst = list(lst)

        gprs = [0] * 64
        vec = [1, 2, 3, 4, 9, 5, 6]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(7):
                val = sim.gpr(i).value
                res.append(val)
                print("i", i, val)
            # confirm that the results are as expected
            expected = preduce_y(vec)
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

    def test_sv_remap2(self):
        """>>> lst = ["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 1, 0, 0, 0, 0, 0", # different order
                       "sv.subf *0, *8, *16"
                        ]
                REMAP sv.subf RT,RA,RB - inverted application of RA/RB
                                         left/right due to subf
        """
        lst = SVP64Asm(["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 1, 0, 0, 0, 0, 0",
                       "sv.subf *0, *0, *0"
                        ])
        lst = list(lst)

        gprs = [0] * 64
        vec = [1, 2, 3, 4, 9, 5, 6]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(7):
                val = sim.gpr(i).value
                res.append(val)
                print("i", i, val)
            # confirm that the results are as expected, mask with 64-bit
            expected = preduce_y(vec, operation=operator.sub)
            for i, v in enumerate(res):
                self.assertEqual(v & 0xffffffffffffffff,
                                 expected[i] & 0xffffffffffffffff)

    def test_sv_remap3(self):
        """>>> lst = ["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 0, 1, 0, 0, 0, 0",
                       "sv.fcpsgn *0, *8, *16"
                        ]
                REMAP sv.subf RT,RA,RB - inverted application of RA/RB
                                         left/right due to subf
        """
        lst = SVP64Asm(["svshape 7, 0, 0, 7, 0",
                        "svremap 31, 0, 1, 0, 0, 0, 0",
                       "sv.fcpsgn *0, *0, *0"
                        ])
        lst = list(lst)

        fprs = [0] * 64
        vec = [-1.0, 2.0, 3.0, -4.0, 9.0, -5.0, 6.0]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            fprs[i] = fp64toselectable(x)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_fprs=fprs)
            print("spr svshape0", sim.spr['SVSHAPE0'])
            print("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print("spr svshape1", sim.spr['SVSHAPE1'])
            print("spr svshape2", sim.spr['SVSHAPE2'])
            print("spr svshape3", sim.spr['SVSHAPE3'])
            # confirm that the results are as expected
            expected = preduce_y(vec, operation=signcopy)
            for i in range(7):
                val = sim.fpr(i).value
                res.append(val)
                print("i", i, float(sim.fpr(i)), vec[i], expected[i])
            for i, v in enumerate(res):
                self.assertEqual(v & 0xffffffffffffffff,
                                 fp64toselectable(expected[i]).value)

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
