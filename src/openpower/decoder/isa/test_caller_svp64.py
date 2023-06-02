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
        """>>> lst = ["addi 16, 0, 0x0010",
                        "addi 17, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stw *4, 0(*16)",
                        "sv.lwz *8, 0(*16)"]
        """
        lst = SVP64Asm(["addi 16, 0, 0x0010",
                        "addi 17, 0, 0x0008",
                        "addi 4, 0, 0x1234",
                        "addi 5, 0, 0x1235",
                        "sv.stw *4, 0(*16)",
                        "sv.lwz *8, 0(*16)"])
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

    def test_sv_add(self):
        """>>> lst = ['sv.add *1, *5, *9'
                       ]
        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321+0x1234
            * 2 = 6 + 10  => 0x3334 = 0x2223+0x1111
        """
        isa = SVP64Asm(['sv.add *1, *5, *9'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[5] = 0x4321
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        # copy before running, then compute answers
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = initial_regs[5] + initial_regs[9]  # 0x5555
        expected_regs[2] = initial_regs[6] + initial_regs[10]  # 0x3334

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_add_2(self):
        """>>> lst = ['sv.add 1, *5, *9' ]
        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321+0x1234
            * r1 is scalar so ENDS EARLY
        """
        isa = SVP64Asm(['sv.add 1, *5, *9'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = initial_regs[5] + initial_regs[9]  # 0x5555

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_add_3(self):
        """>>> lst = ['sv.add *1, 5, *9' ]

        adds:
            * 1 = 5 + 9   => 0x5555 = 0x4321+0x1234
            * 2 = 5 + 10  => 0x5432 = 0x4321+0x1111
        """
        isa = SVP64Asm(['sv.add *1, 5, *9'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[1] = initial_regs[5] + initial_regs[9]   # 0x5555
        expected_regs[2] = initial_regs[5] + initial_regs[10]  # 0x5432

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_add_vl_0(self):
        """>>> lst = ['sv.add 1, *5, *9'
                       ]
        adds:
            * none because VL is zero
        """
        isa = SVP64Asm(['sv.add 1, *5, *9'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        # SVSTATE (in this case, VL=0)
        svstate = SVP64State()
        svstate.vl = 0  # VL
        svstate.maxvl = 0  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_add_cr(self):
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
                        svstate=None):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
