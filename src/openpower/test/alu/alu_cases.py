import random
from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.power_enums import XER_bits
from openpower.decoder.isa.caller import special_sprs
import unittest


class ALUTestCase(TestAccumulatorBase):

    def case_1_regression(self):
        lst = [f"extsw 3, 1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xb6a1fc6c8576af91
        self.add_case(Program(lst, bigendian), initial_regs)
        lst = [f"subf 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3d7f3f7ca24bac7b
        initial_regs[2] = 0xf6b2ac5e13ee15c2
        self.add_case(Program(lst, bigendian), initial_regs)
        lst = [f"subf 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x833652d96c7c0058
        initial_regs[2] = 0x1c27ecff8a086c1a
        self.add_case(Program(lst, bigendian), initial_regs)
        lst = [f"extsb 3, 1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x7f9497aaff900ea0
        self.add_case(Program(lst, bigendian), initial_regs)
        lst = [f"add. 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        self.add_case(Program(lst, bigendian), initial_regs)
        lst = [f"add 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x2e08ae202742baf8
        initial_regs[2] = 0x86c43ece9efe5baa
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand(self):
        insns = ["add", "add.", "subf"]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_addme_ca_0(self):
        insns = ["addme", "addme.", "addmeo", "addmeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            for value in [0x7ffffffff,
                          0xffff80000]:
                initial_regs = [0] * 32
                initial_regs[16] = value
                initial_sprs = {}
                xer = SelectableInt(0, 64)
                xer[XER_bits['CA']] = 0
                initial_sprs[special_sprs['XER']] = xer
                self.add_case(Program(lst, bigendian),
                              initial_regs, initial_sprs)

    def case_addme_ca_1(self):
        insns = ["addme", "addme.", "addmeo", "addmeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            for value in [0x7ffffffff, # fails, bug #476
                          0xffff80000]:
                initial_regs = [0] * 32
                initial_regs[16] = value
                initial_sprs = {}
                xer = SelectableInt(0, 64)
                xer[XER_bits['CA']] = 1
                initial_sprs[special_sprs['XER']] = xer
                self.add_case(Program(lst, bigendian),
                              initial_regs, initial_sprs)

    def case_addme_ca_so_3(self):
        """bug where SO does not get passed through to CR0
        """
        lst = ["addme. 6, 16"]
        initial_regs = [0] * 32
        initial_regs[16] = 0x7ffffffff
        initial_sprs = {}
        xer = SelectableInt(0, 64)
        xer[XER_bits['CA']] = 1
        xer[XER_bits['SO']] = 1
        initial_sprs[special_sprs['XER']] = xer
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs)

    def case_addze(self):
        insns = ["addze", "addze.", "addzeo", "addzeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            initial_regs = [0] * 32
            initial_regs[16] = 0x00ff00ff00ff0080
            self.add_case(Program(lst, bigendian), initial_regs)

        self.add_case(Program(lst, bigendian), initial_regs)

    def case_addis_nonzero_r0_regression(self):
        lst = [f"addis 3, 0, 1"]
        print(lst)
        initial_regs = [0] * 32
        initial_regs[0] = 5
        self.add_case(Program(lst, bigendian), initial_regs)

    def case_addis_nonzero_r0(self):
        for i in range(10):
            imm = random.randint(-(1 << 15), (1 << 15)-1)
            lst = [f"addis 3, 0, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[0] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_rand_imm(self):
        insns = ["addi", "addis", "subfic"]
        for i in range(10):
            choice = random.choice(insns)
            imm = random.randint(-(1 << 15), (1 << 15)-1)
            lst = [f"{choice} 3, 1, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_0_adde(self):
        lst = ["adde. 5, 6, 7"]
        for i in range(10):
            initial_regs = [0] * 32
            initial_regs[6] = random.randint(0, (1 << 64)-1)
            initial_regs[7] = random.randint(0, (1 << 64)-1)
            initial_sprs = {}
            xer = SelectableInt(0, 64)
            xer[XER_bits['CA']] = 1
            initial_sprs[special_sprs['XER']] = xer
            self.add_case(Program(lst, bigendian),
                          initial_regs, initial_sprs)

    def case_cmp(self):
        lst = ["subf. 1, 6, 7",
               "cmp cr2, 1, 6, 7"]
        initial_regs = [0] * 32
        initial_regs[6] = 0x10
        initial_regs[7] = 0x05
        self.add_case(Program(lst, bigendian), initial_regs, {})

    def case_cmp2(self):
        lst = ["cmp cr2, 0, 2, 3"]
        initial_regs = [0] * 32
        initial_regs[2] = 0xffffffffaaaaaaaa
        initial_regs[3] = 0x00000000aaaaaaaa
        self.add_case(Program(lst, bigendian), initial_regs, {})

        lst = ["cmp cr2, 0, 4, 5"]
        initial_regs = [0] * 32
        initial_regs[4] = 0x00000000aaaaaaaa
        initial_regs[5] = 0xffffffffaaaaaaaa
        self.add_case(Program(lst, bigendian), initial_regs, {})

    def case_cmp3(self):
        lst = ["cmp cr2, 1, 2, 3"]
        initial_regs = [0] * 32
        initial_regs[2] = 0xffffffffaaaaaaaa
        initial_regs[3] = 0x00000000aaaaaaaa
        self.add_case(Program(lst, bigendian), initial_regs, {})

        lst = ["cmp cr2, 1, 4, 5"]
        initial_regs = [0] * 32
        initial_regs[4] = 0x00000000aaaaaaaa
        initial_regs[5] = 0xffffffffaaaaaaaa
        self.add_case(Program(lst, bigendian), initial_regs, {})

    def case_cmpl_microwatt_0(self):
        """microwatt 1.bin:
           115b8:   40 50 d1 7c     .long 0x7cd15040 # cmpl 6, 0, 17, 10
            register_file.vhdl: Reading GPR 11 000000000001C026
            register_file.vhdl: Reading GPR 0A FEDF3FFF0001C025
            cr_file.vhdl: Reading CR 35055050
            cr_file.vhdl: Writing 35055058 to CR mask 01 35055058
        """

        lst = ["cmpl 6, 0, 17, 10"]
        initial_regs = [0] * 32
        initial_regs[0x11] = 0x1c026
        initial_regs[0xa] =  0xFEDF3FFF0001C025
        XER = 0xe00c0000
        CR = 0x35055050

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR)

    def case_cmpl_microwatt_0_disasm(self):
        """microwatt 1.bin: disassembled version
           115b8:   40 50 d1 7c     .long 0x7cd15040 # cmpl 6, 0, 17, 10
            register_file.vhdl: Reading GPR 11 000000000001C026
            register_file.vhdl: Reading GPR 0A FEDF3FFF0001C025
            cr_file.vhdl: Reading CR 35055050
            cr_file.vhdl: Writing 35055058 to CR mask 01 35055058
        """

        dis = ["cmpl 6, 0, 17, 10"]
        lst = bytes([0x40, 0x50, 0xd1, 0x7c]) # 0x7cd15040
        initial_regs = [0] * 32
        initial_regs[0x11] = 0x1c026
        initial_regs[0xa] =  0xFEDF3FFF0001C025
        XER = 0xe00c0000
        CR = 0x35055050

        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR)

    def case_cmplw_microwatt_1(self):
        """microwatt 1.bin:
           10d94:   40 20 96 7c     cmplw   cr1,r22,r4
            gpr: 00000000ffff6dc1 <- r4
            gpr: 0000000000000000 <- r22
        """

        lst = ["cmpl 1, 0, 22, 4"]
        initial_regs = [0] * 32
        initial_regs[4] = 0xffff6dc1
        initial_regs[22] = 0
        XER = 0xe00c0000
        CR = 0x50759999

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR)

    def case_cmpli_microwatt(self):
        """microwatt 1.bin: cmpli
           123ac:   9c 79 8d 2a     cmpli   cr5,0,r13,31132
            gpr: 00000000301fc7a7 <- r13
            cr : 0000000090215393
            xer: so 1 ca 0 32 0 ov 0 32 0

        """

        lst = ["cmpli 5, 0, 13, 31132"]
        initial_regs = [0] * 32
        initial_regs[13] = 0x301fc7a7
        XER = 0xe00c0000
        CR = 0x90215393

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR)

    def case_extsb(self):
        insns = ["extsb", "extsh", "extsw"]
        for i in range(10):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            self.add_case(Program(lst, bigendian), initial_regs)

    def case_cmpeqb(self):
        lst = ["cmpeqb cr1, 1, 2"]
        for i in range(20):
            initial_regs = [0] * 32
            initial_regs[1] = i
            initial_regs[2] = 0x0001030507090b0f
            self.add_case(Program(lst, bigendian), initial_regs, {})

