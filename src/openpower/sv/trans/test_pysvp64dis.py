from openpower.simulator.program import Program
from openpower.sv.trans.pysvp64dis import load, dump
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.decoder.power_insn import Verbosity
import unittest
import sys

class SVSTATETestCase(unittest.TestCase):

    def _do_tst(self, expected):
        isa = SVP64Asm(expected)
        lst = list(isa)
        with Program(lst, bigendian=False) as program:
            print ("ops", program._instructions)
            program.binfile.seek(0)
            insns = load(program.binfile)
            #for insn in insns:
                #print ("insn", insn)
            insns = list(insns)
            print ("insns", insns)
            for i, line in enumerate(dump(insns, verbosity=Verbosity.SHORT)):
                name = expected[i].split(" ")[0]
                with self.subTest(name):
                    print("instruction", repr(line), repr(expected[i]))
                    self.assertEqual(expected[i], line,
                                     "instruction does not match "
                                     "'%s' expected '%s'" % (line, expected[i]))


    def test_0_addi(self):
        expected = ['addi 1,5,2',
                        ]
        self._do_tst(expected)

    def test_1_svshape2(self):
        expected = [
                    'svshape2 12,1,15,5,0,0'
                        ]
        self._do_tst(expected)

    def test_2_d_custom_op(self):
        expected = [
                    'fishmv 12,2',
                    'fmvis 12,97',
                    'addpcis 12,5',
                        ]
        self._do_tst(expected)

    def test_3_sv_isel(self):
        expected = [
                    'sv.isel 12,2,3,33',
                    'sv.isel 12,2,3,*33',
                    'sv.isel 12,2,3,*483',
                    'sv.isel 12,2,3,63',
                        ]
        self._do_tst(expected)

    def test_4_sv_crand(self):
        expected = [
                    'sv.crand *16,*2,*33',
                    'sv.crand 12,2,33',
                        ]
        self._do_tst(expected)

if __name__ == "__main__":
    unittest.main()

