from openpower.simulator.program import Program
from openpower.decoder.isa.all import ISA
from openpower.endian import bigendian
from openpower.consts import MSR


from openpower.test.common import TestAccumulatorBase, skip_case
import random


class SPRTestCase(TestAccumulatorBase):

    def case_1_mfspr(self):
        lst = ["mfspr 1, 26",  # SRR0
               "mfspr 2, 27",  # SRR1
               "mfspr 3, 8",  # LR
               "mfspr 4, 1", ]  # XER
        initial_regs = [0] * 32
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678, 'LR': 0x1234,
                        'XER': 0xe00c0000}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_1_mtspr(self):
        lst = ["mtspr 26, 1",  # SRR0
               "mtspr 27, 2",  # SRR1
               "mtspr 1, 3",  # XER
               "mtspr 9, 4", ]  # CTR
        initial_regs = [0] * 32
        initial_regs[1] = 0x129518230011feed
        initial_regs[2] = 0x123518230011feed
        initial_regs[3] = 0xe00c0000
        initial_regs[4] = 0x1010101010101010
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678, 'LR': 0x1234,
                        'XER': 0x0}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_2_mtspr_mfspr(self):
        lst = ["mtspr 26, 1",  # SRR0
               "mtspr 27, 2",  # SRR1
               "mtspr 1, 3",  # XER
               "mtspr 9, 4",  # CTR
               "mfspr 2, 26",  # SRR0
               "mfspr 3, 27",  # and into reg 2
               "mfspr 4, 1",  # XER
               "mfspr 5, 9", ]  # CTR
        initial_regs = [0] * 32
        initial_regs[1] = 0x129518230011feed
        initial_regs[2] = 0x123518230011feed
        initial_regs[3] = 0xe00c0000
        initial_regs[4] = 0x1010101010101010
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678, 'LR': 0x1234,
                        'XER': 0x0}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    # TODO XXX whoops...
    @skip_case("spr does not have TRAP in it. has to be done another way")
    def case_3_mtspr_priv(self):
        lst = ["mtspr 26, 1",  # SRR0
               "mtspr 27, 2",  # SRR1
               "mtspr 1, 3",  # XER
               "mtspr 9, 4", ]  # CTR
        initial_regs = [0] * 32
        initial_regs[1] = 0x129518230011feed
        initial_regs[2] = 0x123518230011feed
        initial_regs[3] = 0xe00c0000
        initial_regs[4] = 0x1010101010101010
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678, 'LR': 0x1234,
                        'XER': 0x0}
        msr = 1 << MSR.PR
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs, initial_msr=msr)

    def case_4_mfspr_slow(self):
        lst = ["mfspr 1, 272",    # SPRG0
               "mfspr 4, 273", ]  # SPRG1
        initial_regs = [0] * 32
        initial_sprs = {'SPRG0_priv': 0x12345678, 'SPRG1_priv': 0x5678,
                        }
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_5_mtspr(self):
        lst = ["mtspr 272, 1",  # SPRG0
               "mtspr 273, 2",  # SPRG1
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x129518230011feed
        initial_regs[2] = 0x123518230011fee0
        initial_sprs = {'SPRG0_priv': 0x12345678, 'SPRG1_priv': 0x5678,
                        }
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

