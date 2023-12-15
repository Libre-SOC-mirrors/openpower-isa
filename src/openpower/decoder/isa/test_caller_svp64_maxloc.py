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



# example sv.cmpi/ff=lt 0, 1, *10, 5
# see https://bugs.libre-soc.org/show_bug.cgi?id=1183#c3
def sv_maxu(gpr, CR, vl, ra, rb, rt):
    i = 0
    while i < vl:
        CR[0] = cmpd(gpr[ra+i], gpr[rb])
        log("sv_maxss test", i, gpr[ra + i], gpr[rb], CR[0], int(CR[0]))
        gpr[rt] = gpr[ra+i] if CR[0].lt else gpr[rb]
        if not CR[0].gt:
            break
        i += 1
    return i # new VL


class DDFFirstTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_maxloc_1(self):
        self.sv_maxloc([1,2,3,4])

    def tst_sv_maxloc_2(self):
        self.sv_maxloc([3,4,1,0])

    def tst_sv_maxloc_3(self):
        self.sv_maxloc([2,9,8,0])

    def tst_sv_maxloc_4(self):
        self.sv_maxloc([2,1,3,0])

    def sv_maxloc(self, ra):
        lst = SVP64Asm(["sv.minmax./ff=le 4, *10, 4, 1" # scalar RB=RT
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        vl = len(ra)  # VL is length of array ra
        svstate.vl = vl  # VL
        svstate.maxvl = vl  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 32
        gprs[4] =  rb # (RT&RB) accumulator in r4
        for i, ra in enumerate(ra): # vector in ra starts at r10
            gprs[10+i] = ra
            log("maxu ddff", i, gprs[10+i])

        cr_res = [0]*8
        res = deepcopy(gprs)

        expected_vl = sv_maxu(res, cr_res, vl, 10, 4, 4)
        log("sv_maxu", expected_vl, cr_res)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                cr_res.append(0)
                log("i", i, val)
            # confirm that the results are as expected

            for i, v in enumerate(cr_res[:vl]):
                crf = sim.crl[i].get_range().value
                log("crf", i, res[i], bin(crf), bin(int(v)))
                self.assertEqual(crf, int(v))

            for i, v in enumerate(res):
                self.assertEqual(v, res[i])

            self.assertEqual(sim.svstate.vl, expected_vl)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

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
