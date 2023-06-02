import unittest
from copy import deepcopy

from nmutil.formaltest import FHDLTestCase
from openpower.decoder.isa.caller import SVP64State
from openpower.decoder.isa.test_caller import run_tst
from openpower.decoder.selectable_int import SelectableInt
from openpower.simulator.program import Program
from openpower.insndb.asm import SVP64Asm


class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64))

    def test_sv_add_intpred(self):
        # adds, integer predicated mask r3=0b10
        #       1 = 5 + 9   => not to be touched (skipped)
        #       2 = 6 + 10  => 0x3334 = 0x2223+0x1111
        #   reg num        0 1 2 3 4 5 6 7 8 9 10 11
        #   src r3=0b10      | |     N N Y Y N N Y Y
        #                    | |         | |     | |
        #                    | | +-------+-|-add-+ |
        #                    | | | +-------+-add---+
        #                    | | | |
        #   dest r3=0b10     N N Y Y
        isa = SVP64Asm(['sv.add/vec2/m=r30 *1, *5, *9'
                        ])
        lst = list(isa)
        print("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[1] = 0xbeef   # not to be altered
        initial_regs[2] = 0xefbe  # not to be altered
        initial_regs[3] = 0xebbe
        initial_regs[4] = 0xbeeb
        initial_regs[30] = 0b10   # predicate mask
        initial_regs[9] = 0x1234
        initial_regs[10] = 0x1111
        initial_regs[11] = 0x7eee
        initial_regs[12] = 0x2aaa
        initial_regs[5] = 0x4321
        initial_regs[6] = 0x2223
        initial_regs[7] = 0x4321
        initial_regs[8] = 0x2223
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2  # VL
        svstate.maxvl = 2  # MAXVL
        print("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[3] = initial_regs[7]+initial_regs[11]
        expected_regs[4] = initial_regs[8]+initial_regs[12]

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def run_tst_program(self, prog, initial_regs=None,
                        svstate=None,
                        initial_cr=0):
        if initial_regs is None:
            initial_regs = [0] * 32
        simulator = run_tst(prog, initial_regs, svstate=svstate,
                            initial_cr=initial_cr)
        simulator.gpr.dump()
        return simulator


if __name__ == "__main__":
    unittest.main()
