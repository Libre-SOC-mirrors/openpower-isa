from openpower.simulator.program import Program
from openpower.sv.trans.pysvp64dis import load, dump
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.decoder.power_insn import Database, Verbosity
from openpower.decoder.power_enums import find_wiki_dir
from openpower.sv import sv_binutils_fptrans
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
                with self.subTest("%d:%s" % (i, name)):
                    print("instruction", repr(line), repr(expected[i]))
                    self.assertEqual(expected[i], line,
                                     "instruction does not match "
                                     "'%s' expected '%s'" % (line, expected[i]))


    def test_0_add(self):
        expected = ['addi 1,5,2',
                    'add 1,5,2',
                    'add. 1,5,2',
                    'addo 1,5,2',
                    'addo. 1,5,2',
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
                    'sv.isel 12,2,3,*99',
                        ]
        self._do_tst(expected)

    def test_4_sv_crand(self):
        expected = [
                    'sv.crand *16,*2,*33',
                    'sv.crand 12,2,33',
                        ]
        self._do_tst(expected)

    def test_5_setvl(self):
        expected = [
                    "setvl 5,4,5,0,1,1",
                    "setvl. 5,4,5,0,1,1",
                        ]
        self._do_tst(expected)

    def test_6_sv_setvl(self):
        expected = [
                    "sv.setvl 5,4,5,0,1,1",
                    "sv.setvl 63,35,5,0,1,1",
                        ]
        self._do_tst(expected)

    def test_7_batch(self):
        "these come from https://bugs.libre-soc.org/show_bug.cgi?id=917#c25"
        expected = [
                    "addi 2,2,0",
                    "addis 9,2,0",
                    "addi 9,9,0",
                    "rlwinm 7,7,2,0,29",
                    "mulli 0,7,31",
                    "add 10,6,0",
                    "setvl 0,0,8,1,1,0",
                    "addi 16,4,124",
                    "lfiwax 0,0,5",
                    "addi 5,3,64",
                    "sv.lfs *32,256(4)",
                    "sv.lfs *40,256(5)",
                    "sv.fmuls *32,*32,*40",
                    "sv.fadds 0,*32,0",
                    "addi 5,3,192",
                    "addi 4,4,128",
                    "sv.lfs *32,256(4)",
                    "sv.lfs *40,256(5)",
                    "sv.fmuls *32,*32,*40",
                    "sv.fsubs 0,0,*32",
                    "addi 4,4,-128",
                    "stfs 0,0(6)",
                    "add 6,6,7",
                    "addi 4,4,4",
                    "addi 0,0,15",
                    "mtspr 288,0",
                    "addi 8,0,4",
                    "lfiwax 0,0,9",
                    "lfiwax 1,0,9",
                    "addi 5,3,64",
                    "add 5,5,8",
                    "sv.lfs *32,256(5)",
                    "sv.lfs *40,256(4)",
                    "sv.lfs *48,256(16)",
                    "sv.fmuls *40,*32,*40",
                    "sv.fadds 0,0,*40",
                    "sv.fmuls *32,*32,*48",
                    "sv.fsubs 1,1,*32",
                    "addi 5,3,192",
                    "subf 5,8,5",
                    "addi 4,4,128",
                    "addi 16,16,128",
                    "sv.lfs *32,256(5)",
                    "sv.lfs *40,256(4)",
                    "sv.lfs *48,256(16)",
                    "sv.fmuls *40,*32,*40",
                    "sv.fsubs 0,0,*40",
                    "sv.fmuls *32,*32,*48",
                    "sv.fsubs 1,1,*32",
                    "addi 4,4,-128",
                    "addi 16,16,-128",
                    "stfs 0,0(6)",
                    "add 6,6,7",
                    "stfs 1,0(10)",
                    "subf 10,7,10",
                    "addi 8,8,4",
                    "addi 4,4,4",
                    "addi 16,16,-4",
                    "bc 16,0,-0xb4",
                    "addi 5,3,128",
                    "addi 4,4,128",
                    "lfiwax 0,0,9",
                    "sv.lfs *32,256(4)",
                    "sv.lfs *40,256(5)",
                    "sv.fmuls *32,*32,*40",
                    "sv.fsubs 0,0,*32",
                    "stfs 0,0(6)",
                    "bclr 20,0,0",
                        ]
        self._do_tst(expected)

    def test_8_madd(self):
        expected = [
                    "maddhd 5,4,5,3",
                    "maddhdu 5,4,5,3",
                    "maddld 5,4,5,3",
                        ]
        self._do_tst(expected)

    def test_9_fptrans(self):
        "enumerates a list of fptrans instruction disassembly entries"
        db = Database(find_wiki_dir())
        entries = sorted(sv_binutils_fptrans.collect(db))
        dis = lambda entry: sv_binutils_fptrans.dis(entry, binutils=False)
        self._do_tst(list(map(dis, entries)))

    def test_10_vec(self):
        expected = [
                    "sv.add./vec2 *3,*7,*11",
                    "sv.add./vec3 *3,*7,*11",
                    "sv.add./vec4 *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_11_elwidth(self):
        expected = [
                    "sv.add./ew=8 *3,*7,*11",
                    "sv.add./ew=16 *3,*7,*11",
                    "sv.add./ew=32 *3,*7,*11",
                        ]
        self._do_tst(expected)

if __name__ == "__main__":
    unittest.main()

