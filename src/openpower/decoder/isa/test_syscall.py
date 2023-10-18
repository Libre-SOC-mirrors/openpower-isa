import os
import tempfile
import unittest

from nmutil.formaltest import FHDLTestCase

from openpower.decoder.isa.test_runner import run_tst
from openpower.test.runner import TestRunnerBase
from openpower.simulator.program import Program


class SyscallTestCase(FHDLTestCase):
    def run_tst_program(self, prog, initial_regs=[0] * 32):
        simulator = run_tst(prog, initial_regs, use_syscall_emu=True)
        simulator.gpr.dump()
        return simulator

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
