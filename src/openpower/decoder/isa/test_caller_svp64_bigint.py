from nmigen import Module, Signal
from nmigen.sim import Simulator, Delay, Settle
from nmutil.formaltest import FHDLTestCase
import unittest
from openpower.decoder.isa.caller import ISACaller
from openpower.decoder.power_decoder import (create_pdecode)
from openpower.decoder.power_decoder2 import (PowerDecode2)
from openpower.simulator.program import Program
from openpower.decoder.isa.caller import ISACaller, SVP64State, CRFields
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.orderedset import OrderedSet
from openpower.decoder.isa.all import ISA
from openpower.decoder.isa.test_caller import Register, run_tst
from openpower.sv.trans.svp64 import SVP64Asm
from openpower.consts import SVP64CROffs
from copy import deepcopy

class DecoderTestCase(FHDLTestCase):

    def _check_regs(self, sim, expected):
        for i in range(32):
            self.assertEqual(sim.gpr(i), SelectableInt(expected[i], 64),
                             "reg %d expected %x got %x" % \
                            (i, sim.gpr(i).value, expected[i]))

    def test_sv_bigint_add(self):
        """performs a carry-rollover-vector-add aka "big integer vector add"
        this is remarkably simple, each sv.adde uses and produces a CA which
        goes into the next sv.adde.  arbitrary size is possible (1024+) as
        is looping using the CA bit from one sv.adde on another batch to do
        unlimited-size biginteger add.

        r3/r2: 0x0000_0000_0000_0001 0xffff_ffff_ffff_ffff +
        r5/r4: 0x8000_0000_0000_0000 0x0000_0000_0000_0001 =
        r1/r0: 0x8000_0000_0000_0002 0x0000_0000_0000_0000
        """
        isa = SVP64Asm(['sv.adde *0, *2, *4'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[2] = 0xffff_ffff_ffff_ffff   # lo dword A
        initial_regs[3] = 0x0000_0000_0000_0001   # hi dword A
        initial_regs[4] = 0x0000_0000_0000_0001   # lo dword B
        initial_regs[5] = 0x8000_0000_0000_0000   # hi dword B
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[0] = 0x0                   # rollover to zero, carry
        expected_regs[1] = 0x8000_0000_0000_0002 # carry rolled-over

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_bigint_scalar_shiftright(self):
        """performs a scalar-to-vector right-shift.

        r3                    r2                    r1                       r4
        0x0000_0000_0000_0002 0x8000_8000_8000_8001 0xffff_ffff_ffff_ffff >> 4
        0x0000_0000_0000_0002 0x2800_0800_0800_0800 0x1fff_ffff_ffff_ffff
        """
        isa = SVP64Asm(['sv.dsrd *0,*1,4,1'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[0] = 0xffff_ffff_ffff_ffff   # lo dword A
        initial_regs[1] = 0x8000_8000_8000_8001   # mid dword A
        initial_regs[2] = 0x0000_0000_0000_0002   # hi dword A
        initial_regs[4] = 0x0000_0000_0000_0004   # shift amount (a nibble)
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[0] = 0x1fff_ffff_ffff_ffff   # MSB nibble gets LSB
        expected_regs[1] = 0x2800_0800_0800_0800   # hi dword A

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_bigint_scalar_shiftleft(self):
        """performs a scalar-to-vector left-shift: because the result is moved
        down by one scalar (RT=0 not 1) there is no need for reverse-gear.
        r2 is *not* modified (contains its original value).
        r2                    r1                    r0                       r4
        0x0000_0000_0001_0002 0x3fff_ffff_ffff_ffff 0x4000_0000_0000_0001 << 4
        0x0000_0000_0001_0002 0x0000_0000_0010_0023 0xffff_ffff_ffff_fff4
        """
        isa = SVP64Asm(['sv.dsld *0,*1,4,1'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[0] = 0x4000_0000_0000_0001   # lo dword A
        initial_regs[1] = 0x3fff_ffff_ffff_ffff   # mid dword A
        initial_regs[2] = 0x0000_0000_0001_0002   # hi dword A
        initial_regs[4] = 0x0000_0000_0000_0004   # shift amount (a nibble)
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 2 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        expected_regs[0] = 0xffff_ffff_ffff_fff4   # MSB nibble gets LSB
        expected_regs[1] = 0x0000_0000_0010_0023   # hi dword A

        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs, svstate)
            self._check_regs(sim, expected_regs)

    def test_sv_bigint_mul(self):
        """performs a carry-rollover-vector-mul-with-add with a scalar,
        using "RC" as a 64-bit carry

                                 r1                    r0
                                 0xffff_ffff_ffff_ffff 0xffff_ffff_ffff_ffff *
        r4 (scalar)                                    0xffff_ffff_ffff_fffe +
        r10 (scalar-add-in)                            0x0000_0000_0000_0100 +

           0xffff_ffff_ffff_fffd 0xffff_ffff_ffff_ffff 0x0000_0000_0000_0102
           r10 (RC, MSB)         r9                    r8
        """
        isa = SVP64Asm(['sv.maddedu *8, *0, 4, 10'
                       ])
        lst = list(isa)
        print ("listing", lst)

        # initial values in GPR regfile
        initial_regs = [0] * 32
        initial_regs[0] = 0xffff_ffff_ffff_ffff   # lo dword of Vector A
        initial_regs[1] = 0xffff_ffff_ffff_ffff   # hi dword of Vector A
        initial_regs[4] = 0xffff_ffff_ffff_fffe   # scalar B
        initial_regs[10] = 0x0000_0000_0000_0100  # RC-input
        # SVSTATE (in this case, VL=2)
        svstate = SVP64State()
        svstate.vl = 2 # VL
        svstate.maxvl = 3 # MAXVL
        print ("SVSTATE", bin(svstate.asint()))
        # copy before running
        expected_regs = deepcopy(initial_regs)
        # XXX the result is *three*-dword-long.  RC, the carry roll-over,
        # is a *legitimate* (valid) part of the result as it contains the
        # hi-64-bit of the last multiply.
        expected_regs[8] = 0x0000_0000_0000_0102 # least dword
        expected_regs[9] = 0xffff_ffff_ffff_ffff # next dword
        expected_regs[10] = 0xffff_ffff_ffff_fffd # carry roll-over, top dword

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
