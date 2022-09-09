from openpower.simulator.program import Program
from openpower.sv.trans.pysvp64dis import load, dump
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.decoder.power_insn import Verbosity
import unittest
import sys

class SVSTATETestCase(unittest.TestCase):

    def test_0_addi(self):
        expected = ['addi 1,5,2',
                        ]
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
            for i, line in enumerate(dump(insns, verbose=False, short=True)):
                print("instruction", repr(line), repr(expected[i]))
                self.assertEqual(expected[i], line,
                                 "instruction %i do not match "
                                 "'%s' expected '%s'" % (i, line, expected[i]))

    def test_1_svshape2(self):
        expected = [
                    'svshape2 12,1,15,5,0,0'
                        ]
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
                print("instruction", repr(line), repr(expected[i]))
                self.assertEqual(expected[i], line,
                                 "instruction %i do not match "
                                 "'%s' expected '%s'" % (i, line, expected[i]))

if __name__ == "__main__":
    unittest.main()

