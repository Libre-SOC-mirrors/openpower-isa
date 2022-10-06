from nmigen import Module, Signal
from nmigen.sim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, SVP64State
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA
from openpower.decoder.isa.test_caller import Register, run_tst
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.consts import SVP64CROffs
from copy import deepcopy
from openpower.decoder.helpers import fp64toselectable
from openpower.decoder.isa.remap_preduce_yield import preduce_y
from functools import reduce
import operator


def signcopy(x, y):
    y = abs(y)
    if x < 0:
        return -y
    return y


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_cmp_ff_vli(self):
        lst = SVP64Asm(["sv.cmp/ff=eq/vli *0, 1, *16, 0",
                        ])
        lst = list(lst)

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 3 # VL
        svstate.maxvl = 3 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        vec = [1, 2, 3]
        crs_expected = [8, 2, 0] # LT EQ GT

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i+16] = x

        gprs[0] = 2 # middle value of vec

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                                svstate=svstate)
            print ("spr svstate ", sim.svstate)
            print ("          vl", sim.svstate.vl)
            for i in range(len(vec)):
                val = sim.gpr(16+i).value
                res.append(val)
                crf = sim.crl[i].get_range().value
                print ("i", i, val, crf)
            for i in range(len(vec)):
                crf = sim.crl[i].get_range().value
                assert crf == crs_expected[i], "cr %d %s expect %s" % \
                        (i, crf, crs_expected[i])
            assert sim.svstate.vl == 2

    def test_sv_cmp_ff(self):
        lst = SVP64Asm(["sv.cmp/ff=eq *0, 1, *16, 0",
                        ])
        lst = list(lst)

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 3 # VL
        svstate.maxvl = 3 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        vec = [1, 2, 3]
        crs_expected = [8, 0, 0] # LT EQ GT

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i+16] = x

        gprs[0] = 2 # middle value of vec

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                                svstate=svstate)
            print ("spr svstate ", sim.svstate)
            print ("          vl", sim.svstate.vl)
            for i in range(len(vec)):
                val = sim.gpr(16+i).value
                res.append(val)
                crf = sim.crl[i].get_range().value
                print ("i", i, val, crf)
            for i in range(len(vec)):
                crf = sim.crl[i].get_range().value
                assert crf == crs_expected[i], "cr %d %s expect %s" % \
                        (i, crf, crs_expected[i])
            assert sim.svstate.vl == 1

    def test_sv_cmp_ff_lt(self):
        lst = SVP64Asm(["sv.cmp/ff=gt *0, 1, *16, 0",
                        ])
        lst = list(lst)

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 3 # VL
        svstate.maxvl = 3 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        vec = [1, 2, 3]
        crs_expected = [8, 2, 0] # LT EQ GT

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i+16] = x

        gprs[0] = 2 # middle value of vec

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                                svstate=svstate)
            print ("spr svstate ", sim.svstate)
            print ("          vl", sim.svstate.vl)
            for i in range(len(vec)):
                val = sim.gpr(16+i).value
                res.append(val)
                crf = sim.crl[i].get_range().value
                print ("i", i, val, crf)
            for i in range(len(vec)):
                crf = sim.crl[i].get_range().value
                assert crf == crs_expected[i], "cr %d %s expect %s" % \
                        (i, crf, crs_expected[i])
            assert sim.svstate.vl == 2

    def test_sv_cmp(self):
        lst = SVP64Asm(["sv.cmp *0, 1, *16, 0",
                        ])
        lst = list(lst)

        # SVSTATE vl=10
        svstate = SVP64State()
        svstate.vl = 3 # VL
        svstate.maxvl = 3 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))

        gprs = [0] * 64
        vec = [1, 2, 3]
        crs_expected = [8, 2, 4] # LT EQ GT

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i+16] = x

        gprs[0] = 2 # middle value of vec

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs,
                                                svstate=svstate)
            print ("spr svstate ", sim.spr['SVSTATE'])
            for i in range(len(vec)):
                val = sim.gpr(16+i).value
                res.append(val)
                crf = sim.crl[i].get_range().value
                print ("i", i, val, crf)
                assert crf == crs_expected[i]

    def tst_sv_insert_sort(self):
        """
                ctr = alen-1
                li r10, 1 # prepare mask
                sld r10, alen, r10
                addi r10, r10, -1 # all 1s. must be better way
            loop:
                setvl r3, ctr
                sv.mv/m=1<<r3 key, *array   # get key item
                sld r10, 1  # shift in another zero MSB
                sv.cmp/ff=GT/m=~r10 *0, *array, key # stop cmp at 1st GT fail
                sv.mv/m=GT *array-1, *array    # after cmp and ffirst
                getvl r3
                sub r3, 1                   # reduce by one
                sv.mv/m=1<<r3 *array, key   # put key into array
                bc 16, loop                 # dec CTR, back around

        """
        lst = SVP64Asm(["addi 10, 0, 1",
                        "addi 9, 11, -1",
                        "slw 10, 10, 9",
                        "addi 10, 10, -1",
                        "mtspr 9, 11",
                        "setvl 3, 0, 10, 0, 1, 1",
                        "addi 3, 3, -1",
                        "sv.addi/m=1<<r3 12, *16, 0",  # VEXTRACT to 12
                        "sv.cmp/ff=le/m=~r10 *0, 1, *16, 12",
                        "slw 10, 10, 9",
                        "bc 16, 0, -28",  # decrement CTR, repeat
                        ])
        lst = list(lst)

        gprs = [0] * 64
        #vec = [1, 2, 3, 4, 9, 5, 6]
        vec = [9, 5, 6]

        res = []
        # store GPRs
        for i, x in enumerate(vec):
            gprs[i+16] = x

        gprs[11] = len(vec)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs=gprs)
            print ("spr svstate ", sim.spr['SVSTATE'])
            print ("spr svshape0", sim.spr['SVSHAPE0'])
            print ("    xdimsz", sim.spr['SVSHAPE0'].xdimsz)
            print ("    ydimsz", sim.spr['SVSHAPE0'].ydimsz)
            print ("    zdimsz", sim.spr['SVSHAPE0'].zdimsz)
            print ("spr svshape1", sim.spr['SVSHAPE1'])
            print ("spr svshape2", sim.spr['SVSHAPE2'])
            print ("spr svshape3", sim.spr['SVSHAPE3'])
            for i in range(len(vec)):
                val = sim.gpr(16+i).value
                res.append(val)
                crf = sim.crl[i].get_range().value
                print ("i", i, val, crf)
            # confirm that the results are as expected
            expected = list(reversed(sorted(vec)))
            for i, v in enumerate(res):
                self.assertEqual(v, expected[i])

    def run_tst_program(self, prog, initial_regs=None,
                              svstate=None,
                              initial_mem=None,
                              initial_fprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, mem=initial_mem,
                                                initial_fprs=initial_fprs,
                                                svstate=svstate)

        print ("GPRs")
        simulator.gpr.dump()
        print ("FPRs")
        simulator.fpr.dump()

        return simulator


if __name__ == "__main__":
    unittest.main()
