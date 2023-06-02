import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.consts import SVP64CROffs
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_load_store(self):
        """>>> lst = ["addi 2, 0, 0x0010",
                        "addi 3, 0, 0x0008",
                        "addi 6, 0, 0x1234",
                        "addi 7, 0, 0x1235",
                        "sv.stw *6, 0(*2)",
                        "sv.lwz *8, 0(*2)"]
        """
        lst = SVP64Asm(["addi 2, 0, 0x0010",
                        "addi 3, 0, 0x0008",
                        "addi 6, 0, 0x1234",
                        "addi 7, 0, 0x1235",
                        "sv.stw *6, 0(*2)",
                        "sv.lwz *8, 0(*2)"])
        lst = list(lst)

        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate)
            print(sim.gpr(1))
            self.assertEqual(sim.gpr(8), SelectableInt(0x1234, 64))
            self.assertEqual(sim.gpr(9), SelectableInt(0x1235, 64))

    def test_sv_branch_cond(self):
        for i in [0, 10]:  # , 10]: #[0, 10]:
            lst = SVP64Asm(
                [f"addi 1, 0, {i}",  # set r1 to i
                 f"addi 2, 0, {i}",  # set r2 to i
                 "cmpi cr0, 1, 1, 10",  # compare r1 with 10 and store to cr0
                 "cmpi cr1, 1, 2, 10",  # compare r2 with 10 and store to cr1
                 "sv.bc 12, *2, 0xc",    # beq 0xc -
                 # branch if r1 equals 10 to the nop below
                 "addi 3, 0, 0x1234",   # if r1 == 10 this shouldn't execute
                 "or 0, 0, 0"]          # branch target
            )
            lst = list(lst)

            # SVSTATE (in this case, VL=2)
            svstate = SVP64State()
            svstate.vl = 2  # VL
            svstate.maxvl = 2  # MAXVL
            print("SVSTATE", bin(svstate.asint()))

            with Program(lst, bigendian=False) as program:
                sim = self.run_tst_program(program, svstate=svstate)
                if i == 10:
                    self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
                else:
                    self.assertEqual(sim.gpr(3), SelectableInt(0x1234, 64))

    def test_sv_branch_cond_all(self):
        for i in [7, 8, 9]:
            lst = SVP64Asm(
                [f"addi 1, 0, {i+1}",  # set r1 to i
                 f"addi 2, 0, {i}",  # set r2 to i
                 "cmpi cr0, 1, 1, 8",  # compare r1 with 10 and store to cr0
                 "cmpi cr1, 1, 2, 8",  # compare r2 with 10 and store to cr1
                 "sv.bc/all 12, *1, 0xc",    # bgt 0xc - branch if BOTH
                                       # r1 AND r2 greater 8 to the nop below
                 "addi 3, 0, 0x1234",   # if tests fail this shouldn't execute
                 "or 0, 0, 0"]          # branch target
            )
            lst = list(lst)

            # SVSTATE (in this case, VL=2)
            svstate = SVP64State()
            svstate.vl = 2  # VL
            svstate.maxvl = 2  # MAXVL
            print("SVSTATE", bin(svstate.asint()))

            with Program(lst, bigendian=False) as program:
                sim = self.run_tst_program(program, svstate=svstate)
                if i == 9:
                    self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
                else:
                    self.assertEqual(sim.gpr(3), SelectableInt(0x1234, 64))

    def test_sv_branch_cond_all_vlset(self):
        for i in [7, 8, 9]:
            lst = SVP64Asm(
                [f"addi 1, 0, {i+1}",  # set r1 to i
                 f"addi 2, 0, {i}",  # set r2 to i
                 "cmpi cr0, 1, 1, 8",  # compare r1 with 10 and store to cr0
                 "cmpi cr1, 1, 2, 8",  # compare r2 with 10 and store to cr1
                 "sv.bc/all/vs 12, *1, 0xc",  # bgt 0xc - branch if BOTH
                                       # r1 AND r2 greater 8 to the nop below
                                       # also truncate VL at the fail-point
                 "addi 3, 0, 0x1234",   # if tests fail this shouldn't execute
                 "or 0, 0, 0"]          # branch target
            )
            lst = list(lst)

            # SVSTATE (in this case, VL=2)
            svstate = SVP64State()
            svstate.vl = 2  # VL
            svstate.maxvl = 2  # MAXVL
            print("SVSTATE", bin(svstate.asint()))

            with Program(lst, bigendian=False) as program:
                sim = self.run_tst_program(program, svstate=svstate)
                if i == 9:
                    self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
                else:
                    self.assertEqual(sim.gpr(3), SelectableInt(0x1234, 64))
                print("SVSTATE.vl", bin(svstate.vl))
                self.assertEqual(svstate.vl, i-7)

    def test_sv_branch_cond_vlset_inv(self):
        for i in [7, 8, 9]:
            lst = SVP64Asm(
                [f"addi 1, 0, {i+1}",  # set r1 to i
                 f"addi 2, 0, {i}",  # set r2 to i
                 "cmpi cr0, 1, 1, 8",  # compare r1 with 8 and store to cr0
                 "cmpi cr1, 1, 2, 8",  # compare r2 with 8 and store to cr1
                 "sv.bc/vsb 4, *1, 0xc",  # bgt 0xc - branch if BOTH
                                       # r1 AND r2 greater 8 to the nop below
                                       # also truncate VL at the fail-point
                 "addi 3, 0, 0x1234",   # if tests fail this shouldn't execute
                 "or 0, 0, 0"]          # branch target
            )
            lst = list(lst)

            # SVSTATE (in this case, VL=2)
            svstate = SVP64State()
            svstate.vl = 2  # VL
            svstate.maxvl = 2  # MAXVL
            print("SVSTATE", bin(svstate.asint()))

            with self.subTest("vlset_inv %d" % i):
                with Program(lst, bigendian=False) as program:
                    sim = self.run_tst_program(program, svstate=svstate)
                    print("SVSTATE.vl", bin(svstate.vl))
                    if i == 9:
                        self.assertEqual(sim.gpr(3), SelectableInt(0x1234, 64))
                    else:
                        self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
                    self.assertEqual(svstate.vl, i-7)

    def test_sv_branch_cond_ctr_vlset_inv(self):
        for i in [7, 8, 9]:
            lst = SVP64Asm(
                [f"addi 1, 0, {i+1}",  # set r1 to i
                 f"addi 2, 0, {i}",  # set r2 to i
                 "cmpi cr0, 1, 1, 8",  # compare r1 with 8 and store to cr0
                 "cmpi cr1, 1, 2, 8",  # compare r2 with 8 and store to cr1
                 "sv.bc/vsb 0, *1, 0xc",  # bgt 0xc - branch if BOTH
                                       # r1 AND r2 greater 8 to the nop below
                                       # also truncate VL at the fail-point
                 "addi 3, 0, 0x1234",   # if tests fail this shouldn't execute
                 "or 0, 0, 0"]          # branch target
            )
            lst = list(lst)

            # SVSTATE (in this case, VL=2)
            svstate = SVP64State()
            svstate.vl = 2  # VL
            svstate.maxvl = 2  # MAXVL
            print("SVSTATE", bin(svstate.asint()))
            sprs = {'CTR': i}

            with self.subTest("vlset_ctr_inv %d" % i):
                with Program(lst, bigendian=False) as program:
                    sim = self.run_tst_program(program, svstate=svstate,
                                               initial_sprs=sprs)
                    print("SVSTATE.vl", bin(svstate.vl))
                    print("CTR", sim.spr('CTR').value)
                    if i == 9:
                        self.assertEqual(sim.gpr(3), SelectableInt(0x1234, 64))
                    else:
                        self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
                    self.assertEqual(svstate.vl, i-7)

    def test_sv_branch_ctr(self):
        """XXX under development, seems to be good.
        basically this will reduce CTR under a *vector* loop, where BO[0]
        is 1 so there is no CR-bit-test, and BO[2] is 0 so there is a CTR-zero
        test.  when the CTR-zero test fails the loop is exited, with CTR
        having been reduced by up to at least VL times.  without VLSET
        mode at the same time (which truncates VL at this same fail-point)
        however this is not necessarily so useful, but at least the branch
        occurs with CTR being reduced *at least* by VL.
        """
        for i in [1, 2, 3]:
            lst = SVP64Asm(
                [
                    "sv.bc/ctr/all 16, *0, 0xc",  # branch, test CTR, reducing by VL
                    "addi 3, 0, 0x1234",   # if tests fail this shouldn't execute
                    "or 0, 0, 0"]          # branch target
            )
            lst = list(lst)

            # SVSTATE (in this case, VL=2)
            svstate = SVP64State()
            svstate.vl = 2  # VL
            svstate.maxvl = 2  # MAXVL
            print("SVSTATE", bin(svstate.asint()))
            sprs = {'CTR': i}

            with Program(lst, bigendian=False) as program:
                sim = self.run_tst_program(program, svstate=svstate,
                                           initial_sprs=sprs)
                sim.gpr.dump()
                sim.spr.dump()
                if i != 3:
                    self.assertEqual(sim.gpr(3), SelectableInt(0x1234, 64))
                    self.assertEqual(sim.spr('CTR'), SelectableInt(0, 64))
                else:
                    self.assertEqual(sim.gpr(3), SelectableInt(0, 64))
                    self.assertEqual(sim.spr('CTR'), SelectableInt(1, 64))

    def test_sv_branch_ctr_loop(self):
        """this is a branch-ctr-loop demo which shows an (unconditional)
        decrementing of CTR by VL.  BI still has to be set to Vector even
        though it is unused (BO[0]=1).
        """
        maxvl = 4
        lst = SVP64Asm(
            [
                # VL (and r1) = MIN(CTR,MAXVL=4)
                "setvl 1, 0, %d, 0, 1, 1" % maxvl,
                "add 2, 2, 1",            # for fun accumulate r1 (VL) into r2
                "sv.bc/all 16, *0, -0x8",  # branch, test CTR, reducing by VL
            ]
        )
        lst = list(lst)

        # SVSTATE - set vl and maxvl to 2, they get overridden with setvl
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        target = 15
        sprs = {'CTR': target}

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, svstate=svstate,
                                       initial_sprs=sprs)
            sim.gpr.dump()
            sim.spr.dump()
            self.assertEqual(sim.spr('CTR'), SelectableInt(0, 64))
            self.assertEqual(sim.gpr(2), SelectableInt(target, 64))
            # MAXVL repeatedly subtracted from VL (r1), last loop has remainder
            self.assertEqual(sim.gpr(1), SelectableInt(target % maxvl, 64))

    def norun_sv_add_cr(self):
        """>>> lst = ['sv.add. *1, *5, *9'
                       ]

        adds when Rc=1:                               TODO CRs higher up
            * 1 = 5 + 9   => 0 = -1+1                 CR0=0b100
            * 2 = 6 + 10  => 0x3334 = 0x2223+0x1111   CR1=0b010
        """
        isa = SVP64Asm(['sv.add. *1, *5, *9'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0xffffffffffffffff
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x1
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = initial_regs[5] + initial_regs[9]  # 0x0
        expected_regs[2] = initial_regs[6] + initial_regs[10]  # 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            # XXX TODO, these need to move to higher range (offset)
            cr0_idx = SVP64CROffs.CR0
            cr1_idx = SVP64CROffs.CR1
            CR0 = sim.crl[cr0_idx].get_range().value
            CR1 = sim.crl[cr1_idx].get_range().value
            print("CR0", CR0)
            print("CR1", CR1)
            self._check_regs(sim, expected_regs)
            self.assertEqual(CR0, SelectableInt(2, 4))
            self.assertEqual(CR1, SelectableInt(4, 4))

    def run_tst_program(self, prog, initial_regs=None,
                        svstate=None,
                        initial_sprs=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate,
                            initial_sprs=initial_sprs)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
