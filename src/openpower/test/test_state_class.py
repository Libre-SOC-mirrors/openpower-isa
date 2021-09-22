""" Test States

This module tests the functionality of the state class by manually
loading various registers and memory with values to be compared
between different states.

related bugs:
    * https://bugs.libre-soc.org/show_bug.cgi?id=686

"""

import unittest
import random
from openpower.test.state import SimState, state_factory
from soc.simple.test.teststate import HDLState


class TestStates(unittest.TestCase):
    def test_basic_regs(self):
        initial_regs = [0] * 32
        for i in range(32):
            initial_regs[i] = random.randint(0, (1 << 64) - 1)
        sim = self.empty_state('sim')
        sim.intregs = initial_regs
        hdl = self.empty_state('hdl')
        hdl.intregs = initial_regs
        sim.compare(hdl)
        sim = self.empty_state('sim')
        sim.intregs = initial_regs
        hdl = self.empty_state('hdl')
        hdl.intregs = initial_regs
        hdl.compare(sim)

    @unittest.expectedFailure
    def test_basic_regs_fail(self):
        initial_regs = [0] * 32
        for i in range(32):
            initial_regs[i] = random.randint(0, (1 << 64) - 1)
            fail_regs[i] = random.randint(0, (1 << 64) - 1)
        sim = self.empty_state('sim')
        sim.intregs = initial_regs
        hdl = self.empty_state('hdl')
        hdl.intregs = fail_regs
        sim.compare(hdl)
        sim = self.empty_state('sim')
        sim.intregs = initial_regs
        hdl = self.empty_state('hdl')
        hdl.intregs = fail_regs
        hdl.compare(sim)

    def test_basic_mem(self):
        initial_mem = {}
        for i in range(32):
            initial_mem[i*8] = random.randint(0, (1 << 64) - 1)
        sim = self.empty_state('sim')
        sim.mem = initial_mem
        hdl = self.empty_state('hdl')
        hdl.mem = initial_mem
        sim.compare_mem(hdl)
        hdl.compare_mem(sim)

    def test_basic_mem_size_0_diff(self):
        sim_mem = {0: 8, 16: 24, 240: 32}
        hdl_mem = {0: 8, 16: 24, 224: 0, 232: 0, 240: 32}
        sim = self.empty_state('sim')
        sim.mem = sim_mem
        hdl = self.empty_state('hdl')
        hdl.mem = hdl_mem
        sim.compare_mem(hdl)
        hdl.compare_mem(sim)

    @unittest.expectedFailure
    def test_basic_mem_size_fail(self):
        initial_mem = {}
        for i in range(32):
            initial_mem[i] = random.randint(0, (1 << 64) - 1)
        sim = self.empty_state('sim')
        sim.mem = initial_mem
        hdl = self.empty_state('hdl')
        for i in range(16):
            hdl.mem[i] = initial_mem[i]
        sim.compare_mem(hdl)
        hdl.compare_mem(sim)

    @unittest.expectedFailure
    def test_basic_mem_off_by_one(self):
        sim_mem = {0: 8, 16: 24, 24: 0}
        hdl_mem = {0: 8, 8: 24, 24: 0}
        sim = self.empty_state('sim')
        sim.mem = sim_mem
        hdl = self.empty_state('hdl')
        hdl.mem = hdl_mem
        sim.compare_mem(hdl)
        hdl.compare_mem(sim)

    @unittest.expectedFailure
    def test_basic_mem_one_word_fail(self):
        sim_mem = {0: 8}
        hdl_mem = {0: 16}
        sim = self.empty_state('sim')
        sim.mem = sim_mem
        hdl = self.empty_state('hdl')
        hdl.mem = hdl_mem
        sim.compare_mem(hdl)
        hdl.compare_mem(sim)

    @unittest.expectedFailure
    def test_basic_no_mem_fail(self):
        hdl_mem = {16: 32}
        sim = self.empty_state('sim')
        hdl = self.empty_state('hdl')
        hdl.mem = hdl_mem
        sim.compare_mem(hdl)
        hdl.compare_mem(sim)

    def empty_state(self, state_type):
        state_class = state_factory[state_type]
        state = state_class(None)
        state.intregs = []
        state.crregs = []
        state.pc = []
        state.so, state.sv, state.ov, state.ca = 0, 0, 0, 0
        state.mem = {}
        state.code = 0
        state.dut = self
        state.state_type = state_type
        return state


if __name__ == '__main__':
    unittest.main()
