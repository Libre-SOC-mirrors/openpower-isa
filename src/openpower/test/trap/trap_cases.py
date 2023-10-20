from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.consts import MSR
from openpower.test.state import ExpectedState

from openpower.test.common import TestAccumulatorBase, skip_case
import random


class TrapTestCase(TestAccumulatorBase):
    def case_1_kaivb(self):
        # https://bugs.libre-soc.org/show_bug.cgi?id=859
        lst = ["mtspr 850, 1",  # KAIVB
               "mfspr 2, 850",
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x129518230011feed
        initial_sprs = {'KAIVB': 0x12345678,
                        }
        msr = 0xa000000000000003
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      initial_msr=msr)

    def case_2_kaivb_test(self):
        # https://bugs.libre-soc.org/show_bug.cgi?id=859
        # sets KAIVB to 1<<13 then deliberately causes exception.
        # PC expected to jump to (1<<13)|0x700 *NOT* 0x700 as usual
        lst = ["mtspr 850, 1",  # KAIVB
               "tbegin.",       # deliberately use illegal instruction
               ]
        initial_regs = [0] * 32
        initial_regs[1] = 1 << 13
        initial_sprs = {'KAIVB': 0x12345678,
                        }
        msr = 0xa000000000000003
        e = ExpectedState(pc=0x2700)
        e.intregs[1] = 1 << 13
        e.sprs['SRR0'] = 0x4
        e.sprs['SRR1'] = 0xa000000000080003
        e.sprs['KAIVB'] = 0x2000
        e.msr = 0xa000000000000001
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      initial_msr=msr,
                      expected=e)

    def case_0_hrfid(self):
        lst = ["hrfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'HSRR0': 0x12345678, 'HSRR1': 0x5678}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_1_sc(self):
        lst = ["sc 0"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678}  # to overwrite
        # expected results: PC should be at 0xc00 (sc address)
        e = ExpectedState(pc=0xc00)
        e.intregs[1] = 1
        e.sprs['SRR0'] = 4                  # PC to return to: CIA+4
        e.sprs['SRR1'] = 0x9000000000022903  # MSR to restore after sc return
        e.msr = 0x9000000000000001          # MSR changed to this by sc/trap
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      expected=e)

    def case_1_sc_rfid(self):
        # https://bugs.libre-soc.org/show_bug.cgi?id=982#c104
        lst = ["ba 3080" ]      # branch to 0xc08
        lst += ["addi 0,0,0"] * (0xbfc//4) # 0x004 to 0xbfc all NOP
        lst += ["addi 3,0,3",  # 0xc00 set r3=3 as return result from sc
                "rfid",        # 0xc04
                "sc 0",        # 0xc08 make syscall here
                "addi 0,0,2",  # 0xc0c checks that we returned here
                ]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678} # to overwrite
        # expected results: PC should be at 0xc00 (sc address)
        e = ExpectedState(pc=0xc00)
        e.intregs[3] = 3 # due to instruction at 0xc00
        e.intregs[1] = 1 # should be unaltered
        e.intregs[0] = 2 # due to instruction at 0xc0c
        e.sprs['SRR0'] = 0xc0c              # PC to return to: CIA+4 (0xc0c)
        e.sprs['SRR1'] = 0xffff_ffff_ffff_ffff # MSR after rfid return
        e.msr = 0xffffffffffffffff          # MSR is restored (by rfid)
        e.pc = 0xc10                        # should stop after addi 0,0,2
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      initial_msr=0xffff_ffff_ffff_ffff,
                      expected=e)

    def case_1_rfid(self):
        lst = ["rfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678}
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    @skip_case("FIXME: add rest of expected state, expected pc looks wrong"
               "see https://bugs.libre-soc.org/show_bug.cgi?id=1193")
    def case_2_rfid(self):
        lst = ["rfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0xb000000000001033}
        e = ExpectedState(pc=0x700)
        e.intregs[1] = 1
        e.msr = 0xb000000000001033  # TODO, not actually checked
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      initial_msr=0xa000000000000003,
                      expected=e)

    def case_0_trap_eq_imm(self):
        insns = ["twi", "tdi"]
        for i in range(2):
            choice = random.choice(insns)
            lst = [f"{choice} 4, 1, %d" % i]  # TO=4: trap equal
            initial_regs = [0] * 32
            initial_regs[1] = 1
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_0_trap_eq(self):
        insns = ["tw", "td"]
        for i in range(2):
            choice = insns[i]
            lst = [f"{choice} 4, 1, 2"]  # TO=4: trap equal
            initial_regs = [0] * 32
            initial_regs[1] = 1
            initial_regs[2] = 1
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_3_mtmsr_0(self):
        lst = ["mtmsr 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_3_mtmsr_1(self):
        lst = ["mtmsr 1,1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_4_mtmsrd_0_linux(self):
        lst = ["mtmsrd 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xb000000000001033
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=0xa000000000000003)

    def case_4_mtmsrd_0(self):
        lst = ["mtmsrd 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_5_mtmsrd_1(self):
        lst = ["mtmsrd 1,1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_6_mtmsr_priv_0(self):
        lst = ["mtmsr 1,0"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xffffffffffffffff
        msr = 1 << MSR.PR  # set in "problem state"
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=msr)

    def case_7_rfid_priv_0(self):
        lst = ["rfid"]
        initial_regs = [0] * 32
        initial_regs[1] = 1
        initial_sprs = {'SRR0': 0x12345678, 'SRR1': 0x5678}
        msr = 1 << MSR.PR  # set in "problem state"
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs,
                      initial_msr=msr)

    def case_8_mfmsr(self):
        lst = ["mfmsr 1"]
        initial_regs = [0] * 32
        msr = (~(1 << MSR.PR)) & 0xffffffffffffffff
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=msr)

    def case_9_mfmsr_priv(self):
        lst = ["mfmsr 1"]
        initial_regs = [0] * 32
        msr = 1 << MSR.PR  # set in "problem state"
        self.add_case(Program(lst, bigendian), initial_regs,
                      initial_msr=msr)

    def case_999_illegal(self):
        # ok, um this is a bit of a cheat: use an instruction we know
        # is not implemented by either ISACaller or the core
        lst = ["tbegin.",
               "mtmsr 1,1"]  # should not get executed
        initial_regs = [0] * 32
        self.add_case(Program(lst, bigendian), initial_regs)
