import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm
from openpower.util import log

def cmpd(x, y):
    class CRfield:
        def __repr__(self):
            return "<lt %d gt %d eq %d>" % (self.lt, self.gt, self.eq)
    CRf = CRfield()
    CRf.lt = x < y
    CRf.gt = x > y
    CRf.eq = x == y
    return CRf


# example sv.cmpi/ff=lt 0, 1, *10, 5
# see https://bugs.libre-soc.org/show_bug.cgi?id=1183#c3
def sv_cmpi(gpr, CR, vl, ra, si):
    i = 0
    while i < vl:
        CR[i] = cmpd(gpr[ra + i], si)
        log("sv_cmpi test", i, gpr[ra + i], si, CR[i], CR[i].lt)
        if CR[i].lt:
            break
        i += 1
    return i # new VL


class DDFFirstTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_1(self):
        lst = SVP64Asm(["sv.cmpi/ff=lt 0, 1, *10, 5"
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        vl = 3  # VL
        svstate.vl = vl  # VL
        svstate.maxvl = vl  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 32
        gprs[10] = 7
        gprs[11] = 5
        gprs[12] = 12

        res = []
        cr_res = [0]*8

        newvl = sv_cmpi(gprs, cr_res, vl, 10, 5)
        log("sv_cmpi", newvl, cr_res)
        
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                cr_res.append(0)
                print("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            expected_vl = 0
            for i in range(4):
                # calculate expected result and expected CR field
                result = vec[i] - gprs[8]
                crf = ((result==0)<<1) | ((result > 0)<<2) | ((result < 0) << 3)
                cr_res[i] = crf
                if result <= 0:
                    break
                # VLi=0 - test comes FIRST!
                expected[i] = result
                # only write out if successful
                expected_vl += 1

            for i, v in enumerate(cr_res):
                crf = sim.crl[i].get_range().value
                print ("crf", i, res[i], bin(crf), bin(v))
                self.assertEqual(crf, v)

            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, expected_vl)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

    def test_sv_addi_ffirst_le(self):
        lst = SVP64Asm(["sv.subf./ff=le *0,8,*0"
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        gprs[8] = 3
        vec = [9, 8, 3, 4]

        res = []
        cr_res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                cr_res.append(0)
                print("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            expected_vl = 0
            for i in range(4):
                # calculate expected result and expected CR field
                result = vec[i] - gprs[8]
                crf = ((result==0)<<1) | ((result > 0)<<2) | ((result < 0) << 3)
                cr_res[i] = crf
                if result <= 0:
                    break
                # VLi=0 - test comes FIRST!
                expected[i] = result
                # only write out if successful
                expected_vl += 1

            for i, v in enumerate(cr_res):
                crf = sim.crl[i].get_range().value
                print ("crf", i, res[i], bin(crf), bin(v))
                self.assertEqual(crf, v)

            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, expected_vl)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

    def test_sv_addi_ffirst(self):
        lst = SVP64Asm(["sv.subf./ff=eq *0,8,*0"
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        gprs[8] = 3
        vec = [9, 8, 3, 4]

        res = []
        cr_res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                cr_res.append(0)
                print("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            for i in range(4):
                result = vec[i] - gprs[8]
                crf = ((result==0)<<1) | ((result > 0)<<2) | ((result < 0) << 3)
                cr_res[i] = crf
                if result == 0:
                    break
                # VLi=0 - test comes FIRST!
                expected[i] = result
            for i, v in enumerate(cr_res):
                crf = sim.crl[i].get_range().value
                print ("crf", i, res[i], bin(crf), bin(v))
                self.assertEqual(crf, v)

            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

    def test_sv_addi_ffirst_rc1(self):
        lst = SVP64Asm(["sv.subf/ff=RC1 *0,8,*0"  # RC1 auto-sets EQ (and Rc=1)
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        gprs[8] = 3
        vec = [9, 8, 3, 4]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                print("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            for i in range(4):
                result = expected[i] - gprs[8]
                if result == 0:
                    break
                # VLi=0 - test comes FIRST!
                expected[i] = result
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, 2)
            self.assertEqual(sim.svstate.maxvl, 4)
            self.assertEqual(sim.svstate.srcstep, 0)
            self.assertEqual(sim.svstate.dststep, 0)

    def test_sv_addi_ffirst_vli(self):
        """data-dependent fail-first with VLi=1, the test comes *after* write
        """
        lst = SVP64Asm(["sv.subf/ff=RC1/vli *0,8,*0"
                        ])
        lst = list(lst)

        # SVSTATE
        svstate = SVP64State()
        svstate.vl = 4  # VL
        svstate.maxvl = 4  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        gprs[8] = 3
        vec = [9, 8, 3, 4]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i] = x

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                       svstate=svstate)
            for i in range(4):
                val = sim.gpr(i).value
                res.append(val)
                print("i", i, val)
            # confirm that the results are as expected
            expected = deepcopy(vec)
            for i in range(4):
                # VLi=1 - test comes AFTER write!
                expected[i] -= gprs[8]
                if expected[i] == 0:
                    break
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

            self.assertEqual(sim.svstate.vl, 3)
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
