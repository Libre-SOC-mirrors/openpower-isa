from openpower.simulator.program import Program
from openpower.insndb.dis import load, dump
from openpower.insndb.asm import SVP64Asm
from openpower.insndb.core import Database, Style
from openpower.decoder.power_enums import find_wiki_dir
from openpower.sv import sv_binutils_fptrans
import unittest
import itertools
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
            for i, line in enumerate(dump(insns, style=Style.SHORT)):
                name = expected[i].split(" ")[0]
                with self.subTest("%d:%s" % (i, name)):
                    print("instruction", repr(line), repr(expected[i]))
                    self.assertEqual(expected[i], line,
                                     "instruction does not match "
                                     "'%s' expected '%s'" % (line, expected[i]))


    def test_0_bc(self):
        # hilarious. this should be autogenerated from a sequence
        # of lists of options. it's a lot of frickin options.
        lists = [[None, 'all'],
                 [None, 'm=r3', 'sz', 'snz'], # see below on this one...
                 [None, 'vs', 'vsi', 'vsb', 'vsbi'],
                 [None, 'ctr', 'cti'],
                 [None, 'sl'],
                 [None, 'slu'],
                 [None, 'lru'],
                ]
        expected = []
        for options in itertools.product(*lists): # permutations of list-options
            options = list(filter(lambda x:x, options)) # filter Nones
            # /sz or /snz must have /m=r3 added but then sorted
            if 'sz' in options or 'snz' in options:
                options.append("m=r3")
            options.sort() # otherwise chaos!
            if len(options) != 0:
                options = [''] + options # trick to make a "/" at the front
            print ("option", options)
            # ahhhhhahahaha and sv.bcctr and sv.bcl ahahahahaah....
            option = "sv.bc%s 12,*1,0xc" % "/".join(options)
            expected.append(option)

        self._do_tst(expected)

if __name__ == "__main__":
    unittest.main()

