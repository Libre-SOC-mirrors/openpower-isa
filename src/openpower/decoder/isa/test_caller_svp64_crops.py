"""Implementation of FORTRAN MAXLOC SVP64
Copyright (C) 2022,2023 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
Licensed under the LGPLv3+
Funded by NLnet NGI-ASSURE under EU grant agreement No 957073.
* https://nlnet.nl/project/Libre-SOC-OpenPOWER-ISA
* https://bugs.libre-soc.org/show_bug.cgi?id=676
* https://libre-soc.org/openpower/sv/cookbook/fortran_maxloc/
"""

import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm
from openpower.util import log
from openpower.decoder.isa.maxloc import m2


class CRfield:
    def __init__(self, value=0):
        self.lt = (value>>3) & 0b1
        self.gt = (value>>2) & 0b1
        self.eq = (value>>1) & 0b1
    def __repr__(self):
        return "<lt %d gt %d eq %d>" % (self.lt, self.gt, self.eq)
    def __int__(self):
        return (self.lt<<3) | (self.gt<<2) | (self.eq<<1)


class CR_Ops_TestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_creqv_1(self):
        self.sv_creqv([0b11,0b100])

    def tst_sv_maxloc_2(self):
        self.sv_maxloc([3,4,1,5])

    def tst_sv_maxloc_3(self):
        self.sv_maxloc([2,9,8,0])

    def tst_sv_maxloc_4(self):
        self.sv_maxloc([2,1,3,0])

    def sv_creqv(self, ra):
        """
        """

        lst = SVP64Asm([
                "sv.creqv *19,*16,*16",
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        vl = 2
        svstate.vl = vl  # VL
        svstate.maxvl = vl  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 32

        crs = []
        cr_res = []
        cr = 0
        for idx, crf in enumerate(ra):
            crs .append(CRfield(crf))
            cr |= crf << ((7-idx)*4)
        res = deepcopy(gprs)

        #expected_vl, expected_cr = sv_maxu(res, cr_res, vl, 10, 4, 4)
        #log("sv_maxu", expected_vl, cr_res)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       initial_cr=cr,
                                       svstate=svstate)
            for i in range(8):
                crf = sim.crl[i].get_range().value
                log("crf", i, bin(crf))

            # confirm that the results are as expected
            return

            for i, v in enumerate(cr_res[:vl]):
                crf = sim.crl[i].get_range().value
                log("crf", i, res[i], bin(crf), bin(int(v)))
                self.assertEqual(crf, int(v))

    def run_tst_program(self, prog, initial_regs=None,
                        svstate=None,
                        initial_mem=None,
                        initial_cr=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                            initial_cr=initial_cr,
                            svstate=svstate)

        print("GPRs")
        simulator.gpr.dump()
        print("FPRs")
        simulator.fpr.dump()

        return simulator


if __name__ == "__main__":
    unittest.main()
