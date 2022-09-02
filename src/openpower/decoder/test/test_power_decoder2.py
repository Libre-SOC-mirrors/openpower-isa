from nmigen import Module, Signal

# NOTE: to use cxxsim, export NMIGEN_SIM_MODE=cxxsim from the shell
# Also, check out the cxxsim nmigen branch, and latest yosys from git
from nmutil.sim_tmp_alternative import Simulator, Delay, Settle
# to be renamed for a c-based module.
from openpower.decoder.test.pysim import PySimEngine

from nmutil.formaltest import FHDLTestCase
from nmigen.cli import rtlil
import os
import time
import unittest
from openpower.decoder.power_decoder2 import PowerDecode2
from openpower.decoder.power_enums import (Function, MicrOp,
                                     In1Sel, In2Sel, In3Sel,
                                     CRInSel, CROutSel,
                                     OutSel, LdstLen, CryIn,
                                     single_bit_flags,
                                     get_signal_name, get_csv)
from openpower.decoder.decode2execute1 import IssuerDecode2ToOperand
from openpower.decoder.decode2execute1 import Data
from openpower.state import CoreState


class Decoder2TestCase(FHDLTestCase):

    def run_tst(self, raw_opcode):
        m = Module()
        comb = m.d.comb
        opcode = Signal(32)
        bigendian = Signal()
        comb += bigendian.eq(0)

        # copied this from issuer.py
        cur_state = CoreState("cur")  # current state (MSR/PC/SVSTATE)
        m.submodules.dut = dut = PowerDecode2(None, state=cur_state,
                                              opkls=IssuerDecode2ToOperand,
                                              svp64_en=True,
                                              regreduce_en=True)

        comb += [dut.dec.raw_opcode_in.eq(opcode),
                 dut.dec.bigendian.eq(bigendian),
                 ]

        #sim = Simulator(m)
        # Use the below line instead to run the work-in-progress C simulator.
        sim = Simulator(m, engine=PySimEngine)
        # for test purposes repeat the simulation to get performance stats
        repeat_times = 10

        def process():
            tic = time.perf_counter()
            for i in range(repeat_times):
                yield opcode.eq(raw_opcode)

                yield Delay(1e-6)
                yield Settle()
                #self.assertEqual(expected, result, msg)
            ticend = time.perf_counter()
            print ("time taken:", ticend - tic)

        sim.add_process(process)
        prefix = "test_power_decoder2"
        with sim.write_vcd("%s.vcd" % prefix, "%s.gtkw" % prefix, traces=[
                opcode, 
                ]):
            sim.run()

    def test_ld(self):
        self.run_tst(0xe8c20000) # LD operation

if __name__ == "__main__":
    unittest.main()
