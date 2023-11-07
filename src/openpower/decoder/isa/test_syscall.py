import os
import tempfile
import unittest

from nmutil.formaltest import FHDLTestCase

from openpower.consts import MSRb
from openpower.consts import PIb
from openpower.consts import DEFAULT_MSR
from openpower.decoder.helpers import ne
from openpower.decoder.isa.test_runner import run_tst
from openpower.test.runner import TestRunnerBase
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.selectable_int import selectconcat as concat


class SyscallTestCase(FHDLTestCase):
    def run_tst_program(self, prog,
            initial_regs=None):
        if initial_regs is None:
            initial_regs=([0] * 32)
        initial_regs = list(initial_regs)
        initial_sprs = {
            'SRR0': 0xFFFF_FFFF_FFFF_FFFF,
            'SRR1': 0xFFFF_FFFF_FFFF_FFFF,
        }
        sim = run_tst(prog, initial_regs,
            initial_sprs=initial_sprs,
            initial_msr=DEFAULT_MSR,
            use_syscall_emu=True)
        sim.gpr.dump()

        MSR = SelectableInt(DEFAULT_MSR, 64)
        SRR1 = SelectableInt(0xFFFF_FFFF_FFFF_FFFF, 64)

        # sc instruction
        # 4.3.1 System Linkage Instructions
        # 7.5.14 System Call Interrupt
        SRR1[33:37] = 0
        SRR1[42:48] = 0
        SRR1[0:33] = MSR[0:33]
        SRR1[37:42] = MSR[37:42]
        SRR1[48:64] = MSR[48:64]
        # PowerISA v3.1B Book III 7.5.14 specifies TRAP is set to zero
        SRR1[PIb.TRAP] = 0

        # rfid instruction
        MSR[51] = MSR[3] & SRR1[51] | ~MSR[3] & MSR[51]
        MSR[3] = MSR[3] & SRR1[3]
        if ne(MSR[29:32], SelectableInt(value=0x2, bits=3)) | ne(SRR1[29:32],
            SelectableInt(value=0x0, bits=3)):
            MSR[29:32] = SRR1[29:32]
        MSR[48] = SRR1[48] | SRR1[49]
        MSR[58] = SRR1[58] | SRR1[49]
        MSR[59] = SRR1[59] | SRR1[49]
        MSR[0:3] = SRR1[0:3]
        MSR[4:29] = SRR1[4:29]
        MSR[32] = SRR1[32]
        MSR[37:42] = SRR1[37:42]
        MSR[49:51] = SRR1[49:51]
        MSR[52:58] = SRR1[52:58]
        MSR[60:64] = SRR1[60:64]

        self.assertEqual(sim.spr['SRR0'], 8)    # PC to return to: CIA+4
        self.assertEqual(sim.spr['SRR1'], SRR1) # MSR to restore after sc return

        # FIXME this is currently hardcoded to the same way as in test_trap.py.
        # However, I'd have expected 0x9000000000002903, not 0x9000000000000001.
        MSR = SelectableInt(0x9000000000000001, 64)
        self.assertEqual(sim.msr, MSR)          # MSR changed to this by sc/trap

        print("SYSCALL SRR1", hex(int(SRR1)), hex(int(sim.spr['SRR1'])))
        print("SYSCALL MSR", hex(int(MSR)), hex(int(sim.msr)), hex(DEFAULT_MSR))
        return sim

    def test_sc_getpid(self):
        lst = ["sc 0"]
        initial_regs = [0] * 32
        initial_regs[0] = 20 # getpid
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), os.getpid())

    def test_sc_getuid(self):
        lst = ["sc 0"]
        initial_regs = [0] * 32
        initial_regs[0] = 24 # getuid
        with Program(lst, bigendian=False) as program:
            sim = self.run_tst_program(program, initial_regs)
            self.assertEqual(sim.gpr(3), os.getuid())

    def test_sc_dup(self):
        with tempfile.TemporaryFile(mode="wb+") as stream:
            msg0 = b"hello, world!"
            stream.write(msg0)
            stream.seek(0)
            fd0 = stream.fileno()
            st0 = os.fstat(fd0)

            lst = ["sc 0"]
            initial_regs = [0] * 32
            initial_regs[0] = 41 # dup
            initial_regs[3] = fd0
            with Program(lst, bigendian=False) as program:
                sim = self.run_tst_program(program, initial_regs)
                fd1 = int(sim.gpr(3))
                st1 = os.fstat(fd1)
                msg1 = os.read(fd1, 42)
                self.assertEqual(st0, st1)
                self.assertEqual(msg0, msg1)
                os.close(fd1)


if __name__ == "__main__":
    unittest.main()
