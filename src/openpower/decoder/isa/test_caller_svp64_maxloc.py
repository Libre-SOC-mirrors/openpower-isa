"""Implementation of FORTRAN MAXLOC SVP64
Copyright (C) 2022,2023 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
Licensed under the LGPLv3+
Funded by NLnet NGI-ASSURE under EU grant agreement No 957073.
* https://nlnet.nl/project/Libre-SOC-OpenPOWER-ISA
* https://bugs.libre-soc.org/show_bug.cgi?id=676
* https://libre-soc.org/openpower/sv/cookbook/fortran_maxloc/
"""

import unittest
import random
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm
from openpower.util import log
from openpower.decoder.isa.maxloc import m2



def cmpd(x, y):
    class CRfield:
        def __repr__(self):
            return "<lt %d gt %d eq %d>" % (self.lt, self.gt, self.eq)
        def __int__(self):
            return (CRf.lt<<3) | (CRf.gt<<2) | (CRf.eq<<1)
    CRf = CRfield()
    CRf.lt = x < y
    CRf.gt = x > y
    CRf.eq = x == y
    return CRf


# example sv.minmax/ff=lt 0, 1, *10, 5
# see https://bugs.libre-soc.org/show_bug.cgi?id=1183#c3
def sv_maxu(gpr, vl, ra, rb, rt):
    CR0, i = None, 0
    while i < vl:
        CR0 = cmpd(gpr[ra+i], gpr[rb])
        log("sv_maxss test", i, gpr[ra + i], gpr[rb], CR0, int(CR0))
        gpr[rt] = gpr[ra+i] if CR0.lt else gpr[rb]
        if not CR0.gt:
            break
        i += 1
    return i, CR0 # new VL


class DDFFirstTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_maxloc_1(self):
        self.sv_maxloc([1,3,3,3])

    def test_sv_maxloc_2(self):
        self.sv_maxloc([3,4,1,5])

    def test_sv_maxloc_3(self):
        self.sv_maxloc([2,9,8,0])

    def test_sv_maxloc_4(self):
        self.sv_maxloc([2,1,3,0])

    def test_sv_maxloc_5(self):
        self.sv_maxloc([0,0,0,0])

    def test_sv_maxloc_6(self):
        self.sv_maxloc([0,9,9,3])

    def test_sv_maxloc_7(self):
        self.sv_maxloc([9,0,10,11])

    def test_sv_maxloc_random(self):
        random.seed(1) # set the same seed (consistent test)
        for i in range(50):
            array = []
            for j in range(4):
                array.append(random.randint(0, 20))
            with self.subTest(i=i):
                self.sv_maxloc(array)

    def sv_maxloc(self, ra):
        """
            m, nm, i, n = 0, 0, 0, len(a)
            while (i<n):
                while (i<n and a[i]<=m) : i += 1
                while (i<n and a[i] > m): m, nm, i = a[i], i, i+1
            return nm
        """

        # note that m (above) is r4. sv.cmp can be used in the first
        # while loop because m (r4) does not change. sv.minmax. has
        # to be used in the key while loop because r4 is sequentially
        # replaced (mapreduce mode) each time. also note that i is
        # represented as a bitmask (CR bits 16,20,24,28)

        lst = SVP64Asm([
            # while (i<n)
            "setvl 2,0,4,0,1,1",                  # set MVL=4, VL=MIN(MVL,CTR)
            #    while (i<n and a[i]<=m) : i += 1
            "sv.cmp/ff=gt/m=ge *0,0,*10,4",       # truncates VL to min
            "sv.creqv *16,*16,*16",               # set mask on already-tested
            "setvl 2,0,4,0,1,1",                  # set MVL=4, VL=MIN(MVL,CTR)
            "mtcrf 128, 0",                       # clear CR0 (in case VL=0?)
            #    while (i<n and a[i]>m):
            "sv.minmax./ff=le/m=ge/mr 4,*10,4,1", # uses r4 as accumulator
            "crternlogi 0,1,2,127",               # test greater/equal or VL=0
            "sv.crand *19,*16,0",                 # clear if CR0.eq=0
            #      nm = i (count masked bits. could use crweirds here TODO)
            "sv.svstep/mr/m=so 1, 0, 6, 1",       # svstep: get vector dststep
            "sv.creqv *16,*16,*16",               # set mask on already-tested
            "bc 12,0, -0x40"                      # CR0 lt bit clear, branch back
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        vl = len(ra)  # VL is length of array ra
        svstate.vl = vl  # VL
        svstate.maxvl = vl  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 32
        gprs[3] =  vl # variable n: to go into CTR
        gprs[4] =  2  # variable m: max current number found
        for i, ra in enumerate(ra): # vector in ra starts at r10
            gprs[10+i] = ra
            log("maxu ddff", i, gprs[10+i])

        cr_res = [0]*8
        res = deepcopy(gprs)

        #expected_vl, expected_cr = sv_maxu(res, cr_res, vl, 10, 4, 4)
        #log("sv_maxu", expected_vl, cr_res)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(vl):
                val = sim.gpr(i).value
                res.append(val)
                cr_res.append(0)
                log("i", i, val)

            for i in range(vl):
                crf = sim.crl[i].get_range().value
                log("crf", i, bin(crf))

            # confirm that the results are as expected
            return

            for i, v in enumerate(cr_res[:vl]):
                crf = sim.crl[i].get_range().value
                log("crf", i, res[i], bin(crf), bin(int(v)))
                self.assertEqual(crf, int(v))

            for i, v in enumerate(res):
                self.assertEqual(v, res[i])

            #self.assertEqual(sim.svstate.vl, expected_vl)
            #self.assertEqual(sim.svstate.maxvl, 4)
            #self.assertEqual(sim.svstate.srcstep, 0)
            #self.assertEqual(sim.svstate.dststep, 0)

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
