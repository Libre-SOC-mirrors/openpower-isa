from openpower.simulator.program import Program
from openpower.sv.trans.pysvp64dis import load, dump
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.decoder.power_insn import Database, Verbosity
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
                    'sv.crand/ff=eq/m=r10 12,2,33',
                    'sv.crand/m=r10 12,2,33',
                    'sv.crand/m=r10/sz 12,2,33',
                    # XXX dz/sz is not the canonical way, must be zz
                    'sv.crand/dz/m=r10/sz 12,2,33', # NOT OK
                    'sv.crand/m=r10/zz 12,2,33',    # SHOULD PASS
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
        lst = []
        for generator in map(dis, entries):
            for line in generator:
                lst.append(line)
        self._do_tst(lst)

    def test_10_vec(self):
        expected = [
                    "sv.add./vec2 *3,*7,*11",
                    "sv.add./vec3 *3,*7,*11",
                    "sv.add./vec4 *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_11_elwidth(self):
        expected = [
                    "sv.add./dw=8 *3,*7,*11",
                    "sv.add./dw=16 *3,*7,*11",
                    "sv.add./dw=32 *3,*7,*11",
                    "sv.add./sw=8 *3,*7,*11",
                    "sv.add./sw=16 *3,*7,*11",
                    "sv.add./sw=32 *3,*7,*11",
                    "sv.add./dw=8/sw=16 *3,*7,*11",
                    "sv.add./dw=16/sw=32 *3,*7,*11",
                    "sv.add./dw=32/sw=8 *3,*7,*11",
                    "sv.add./w=32 *3,*7,*11",
                    "sv.add./w=8 *3,*7,*11",
                    "sv.add./w=16 *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_12_sat(self):
        expected = [
                    "sv.add./satu *3,*7,*11",
                    "sv.add./sats *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_12_mr_r(self):
        expected = [
                    "sv.add./mrr/vec2 *3,*7,*11",
                    "sv.add./mr/vec2 *3,*7,*11",
                    "sv.add./mrr *3,*7,*11",
                    "sv.add./mr *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_13_RC1(self):
        expected = [
                    "sv.add/ff=RC1 *3,*7,*11",
                    "sv.add/pr=RC1 *3,*7,*11",
                    "sv.add/ff=~RC1 *3,*7,*11",
                    "sv.add/pr=~RC1 *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_14_rc1_ff_pr(self):
        expected = [
                    "sv.add./ff=eq *3,*7,*11",
                    "sv.add./ff=ns *3,*7,*11",
                    "sv.add./ff=lt *3,*7,*11",
                    "sv.add./ff=ge *3,*7,*11",
                    "sv.add./ff=le *3,*7,*11",
                    "sv.add./ff=gt *3,*7,*11",
                    "sv.add./ff=ne *3,*7,*11",
                    "sv.add./pr=eq *3,*7,*11",
                    "sv.add./pr=ns *3,*7,*11",
                        ]
        self._do_tst(expected)

    def test_15_predicates(self):
        expected = [
                    "sv.add./m=r3 *3,*7,*11",
                    "sv.add./m=1<<r3 *3,*7,*11",
                    "sv.add./m=~r10 *3,*7,*11",
                    "sv.add./m=so *3,*7,*11",
                    "sv.add./m=ne *3,*7,*11",
                    "sv.add./m=lt *3,*7,*11",
                    "sv.add. *3,*7,*11",
                    "sv.extsw/m=r30 3,7",
                    "sv.extsw/dm=~r30/sm=r30 3,7",
                    "sv.extsw/dm=eq/sm=gt 3,7",
                    "sv.extsw/sm=~r3 3,7",
                    "sv.extsw/dm=r30 3,7",
                        ]
        self._do_tst(expected)

    def test_15_els(self):
        expected = [
                    "sv.stw/els *4,16(2)",
                    "sv.lfs/els *1,256(4)",
                        ]
        self._do_tst(expected)

    def test_16_bc(self):
        """bigger list in test_pysvp64dis_branch.py, this one's "quick"
        """
        expected = [
                    "sv.bc/all 12,*1,0xc",
                    "sv.bc/snz 12,*1,0xc",
                    "sv.bc/m=r3/snz 12,*1,0xc",
                    "sv.bc/m=r3/sz 12,*1,0xc",
                    "sv.bc/all/sl/slu 12,*1,0xc",
                    "sv.bc/all/lru/sl/slu/snz 12,*1,0xc",
                    "sv.bc/all/lru/sl/slu/snz/vs 12,*1,0xc",
                    "sv.bc/all/lru/sl/slu/snz/vsi 12,*1,0xc",
                    "sv.bc/all/lru/sl/slu/snz/vsb 12,*1,0xc",
                    "sv.bc/all/lru/sl/slu/snz/vsbi 12,*1,0xc",
                    "sv.bc/all/ctr/lru/sl/slu/snz 12,*1,0xc",
                    "sv.bc/all/cti/lru/sl/slu/snz 12,*1,0xc",
                    "sv.bc/all/ctr/lru/sl/slu/snz/vsb 12,*1,0xc",
                        ]
        self._do_tst(expected)

    def test_17_vli(self):
        expected = [
                    "sv.add/ff=RC1/vli 3,7,11",
                    "sv.add/ff=~RC1/vli 3,7,11",
                        ]
        self._do_tst(expected)

    def test_18_sea(self):
        expected = [
                    "sv.ldux/sea 5,6,7",
                        ]
        self._do_tst(expected)

    def test_19_ldst_idx_els(self):
        expected = [
                    "sv.stdx/els *4,16,2",
                    "sv.stdx/els/sea *4,16,2",
                    "sv.ldx/els *4,16,2",
                    "sv.ldx/els/sea *4,16,2",
                        ]
        self._do_tst(expected)

    def test_20_cmp(self):
        expected = [
                    "sv.cmp *4,1,*0,1",
                    "sv.cmp/ff=RC1 *4,1,*0,1",
                    "sv.cmp/ff=RC1/vli *4,1,*0,1",
                    "sv.cmp/ff=~RC1 *4,1,*0,1",
                    "sv.cmp/ff=RC1/m=r3/sz *4,1,*0,1",
                    "sv.cmp/dz/ff=RC1/m=r3 *4,1,*0,1",
                    "sv.cmp/dz/ff=RC1/m=r3/sz *4,1,*0,1",
                        ]
        self._do_tst(expected)

    def test_21_addex(self):
        expected = [
                    "addex 5,3,2,0",
                    "sv.addex 5,3,2,0",
                    "sv.addex *5,3,2,0",
                        ]
        self._do_tst(expected)

    def test_22_ld(self):
        expected = [
                    "ld 4,0(5)",
                    "ld 4,16(5)",       # sigh, needs magic-shift (D||0b00)
                    "sv.ld 4,16(5)",    # ditto
                        ]
        self._do_tst(expected)

    def test_23_lq(self):
        expected = [
                    "lq 4,0(5)",
                    "lq 4,16(5)",      # ditto, magic-shift (DQ||0b0000)
                    "lq 4,32(5)",      # ditto
                    "sv.lq 4,16(5)",   # ditto
                        ]
        self._do_tst(expected)

    def test_24_bc(self):
        expected = [
                    "b 0x28",
                    "bc 16,0,-0xb4",
                        ]
        self._do_tst(expected)

    def test_25_stq(self):
        expected = [
                    "stq 4,0(5)",
                    "stq 4,8(5)",
                    "stq 4,16(5)",
                    "sv.stq 4,16(*5)",
                        ]
        self._do_tst(expected)

    def test_26_sv_stq_vector_name(self):
        expected = [
                    "sv.stq *4,16(*5)", # RSp not recognised as "vector" name
                        ]
        self._do_tst(expected)

    def test_27_sc(self):
        expected = [
                    "sc 0",
                    "sc 1",
                    "scv 1",
                    "scv 2",
                        ]
        self._do_tst(expected)

    def test_28_rfid(self):
        expected = [
                    "rfid",
                    "rfscv",
                        ]
        self._do_tst(expected)

    def test_29_postinc(self):
        expected = [
                    "sv.ldu/pi 5,8(2)",
                    "sv.lwzu/pi *6,8(2)",
                    "sv.lwzu/pi *6,24(2)",
                    "sv.stwu/pi *6,24(2)",
                        ]
        self._do_tst(expected)

    def test_29_dsld_dsrd(self):
        expected = [
                    "dsld 5,4,5,3",
                    "dsrd 5,4,5,3",
                    "dsld. 5,4,5,3",
                    "dsrd. 5,4,5,3",
                    "sv.dsld *6,4,5,3",
                    "sv.dsrd *6,4,5,3",
                    "sv.dsld. *6,4,5,3",
                    "sv.dsrd. *6,4,5,3",
                        ]
        self._do_tst(expected)

    def test_30_divmod2du(self):
        expected = [
                    "divmod2du 5,4,5,3",
                        ]
        self._do_tst(expected)


if __name__ == "__main__":
    unittest.main()
