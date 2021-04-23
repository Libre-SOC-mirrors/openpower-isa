from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.consts import MSR


from openpower.test.common import TestAccumulatorBase, skip_case
import random


#incomplete test - connect fsm inputs first
class MMUTestCase(TestAccumulatorBase):
    # MMU handles MTSPR, MFSPR, DCBZ and TLBIE.
    # other instructions here -> must be load/store

    #before running the test case: set DISR and DAR

    def case_mfspr_after_invalid_load(self):
        lst = [ # TODO -- set SPR on both simulator and port interface
                "mfspr 1, 18", # DSISR to reg 1
                "mfspr 2, 19", # DAR to reg 2
                # TODO -- verify returned sprvals
              ]

        initial_regs = [0] * 32

        initial_sprs = {'DSISR': 0x12345678, 'DAR': 0x87654321}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

