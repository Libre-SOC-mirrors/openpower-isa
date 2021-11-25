import random
from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
from openpower.simulator.program import Program
from openpower.decoder.selectable_int import SelectableInt
from openpower.decoder.power_enums import XER_bits
from openpower.decoder.isa.caller import special_sprs
from openpower.test.state import ExpectedState
import unittest


class ALUTestCase(TestAccumulatorBase):

    def case_1_regression(self):
        lst = [f"add. 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xc523e996a8ff6215
        initial_regs[2] = 0xe1e5b9cc9864c4a8
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xc523e996a8ff6215
        e.intregs[2] = 0xe1e5b9cc9864c4a8
        e.intregs[3] = 0xa709a363416426bd
        e.crregs[0] = 0x8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_2_regression(self):
        lst = [f"extsw 3, 1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0xb6a1fc6c8576af91
        e = ExpectedState(pc=4)
        e.intregs[1] = 0xb6a1fc6c8576af91
        e.intregs[3] = 0xffffffff8576af91
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"subf 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x3d7f3f7ca24bac7b
        initial_regs[2] = 0xf6b2ac5e13ee15c2
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x3d7f3f7ca24bac7b
        e.intregs[2] = 0xf6b2ac5e13ee15c2
        e.intregs[3] = 0xb9336ce171a26947
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"subf 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x833652d96c7c0058
        initial_regs[2] = 0x1c27ecff8a086c1a
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x833652d96c7c0058
        e.intregs[2] = 0x1c27ecff8a086c1a
        e.intregs[3] = 0x98f19a261d8c6bc2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"extsb 3, 1"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x7f9497aaff900ea0
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x7f9497aaff900ea0
        e.intregs[3] = 0xffffffffffffffa0
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = [f"add 3, 1, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x2e08ae202742baf8
        initial_regs[2] = 0x86c43ece9efe5baa
        e = ExpectedState(pc=4)
        e.intregs[1] = 0x2e08ae202742baf8
        e.intregs[2] = 0x86c43ece9efe5baa
        e.intregs[3] = 0xb4cceceec64116a2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rand(self):
        insns = ["add", "add.", "subf"]
        for i in range(40):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1, 2"]
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)
            initial_regs[2] = random.randint(0, (1 << 64)-1)

            e = ExpectedState(pc=4)
            e.intregs[1] = initial_regs[1]
            e.intregs[2] = initial_regs[2]
            if choice == "add":
                result = initial_regs[1] + initial_regs[2]
                if result < 0:
                    e.intregs[3] = (result + 2**64) & ((2**64)-1)
                else:
                    e.intregs[3] = result & ((2**64)-1)
            elif choice == "add.":
                result = initial_regs[1] + initial_regs[2]
                if result < 0:
                    e.intregs[3] = (result + 2**64) & ((2**64)-1)
                else:
                    e.intregs[3] = result & ((2**64)-1)
                eq = 0
                gt = 0
                le = 0
                if (e.intregs[3] & (1<<63)) != 0:
                    le = 1
                elif e.intregs[3] == 0:
                    eq = 1
                else:
                    gt = 1
                e.crregs[0] = (eq<<1) | (gt<<2) | (le<<3)
            elif choice == "subf":
                result = ~initial_regs[1] + initial_regs[2] + 1
                if result < 0:
                    e.intregs[3] = (result + 2**64) & ((2**64)-1)
                else:
                    e.intregs[3] = result & ((2**64)-1)

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

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
                xer[XER_bits['CA']] = 0  # input carry is 0 (see test below)
                initial_sprs[special_sprs['XER']] = xer

                # create expected results.  pc should be 4 (one instruction)
                e = ExpectedState(pc=4)
                # input value should not be modified
                e.intregs[16] = value
                # carry-out should always occur
                e.ca = 0x3
                # create output value
                if value == 0x7ffffffff:
                    e.intregs[6] = 0x7fffffffe
                else:
                    e.intregs[6] = 0xffff7ffff
                # CR version needs an expected CR
                if '.' in choice:
                    e.crregs[0] = 0x4
                self.add_case(Program(lst, bigendian),
                              initial_regs, initial_sprs,
                              expected=e)

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
                xer[XER_bits['CA']] = 1 # input carry is 1 (differs from above)
                initial_sprs[special_sprs['XER']] = xer
                e = ExpectedState(pc=4)
                e.intregs[16] = value
                e.ca = 0x3
                if value == 0x7ffffffff:
                    e.intregs[6] = 0x7ffffffff
                else:
                    e.intregs[6] = 0xffff80000
                if '.' in choice:
                    e.crregs[0] = 0x4
                self.add_case(Program(lst, bigendian),
                              initial_regs, initial_sprs, expected=e)

    def case_addme_ca_so_4(self):
        """test of SO being set
        """
        lst = ["addmeo. 6, 16"]
        initial_regs = [0] * 32
        initial_regs[16] = 0x7fffffffffffffff
        initial_sprs = {}
        xer = SelectableInt(0, 64)
        xer[XER_bits['CA']] = 1
        initial_sprs[special_sprs['XER']] = xer
        e = ExpectedState(pc=4)
        e.intregs[16] = 0x7fffffffffffffff
        e.intregs[6] = 0x7fffffffffffffff
        e.ca = 0x3
        e.crregs[0] = 0x4
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs, expected=e)

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
        e = ExpectedState(pc=4)
        e.intregs[16] = 0x7ffffffff
        e.intregs[6] = 0x7ffffffff
        e.crregs[0] = 0x5
        e.so = 0x1
        e.ca = 0x3
        self.add_case(Program(lst, bigendian),
                      initial_regs, initial_sprs, expected=e)

    def case_addze(self):
        insns = ["addze", "addze.", "addzeo", "addzeo."]
        for choice in insns:
            lst = [f"{choice} 6, 16"]
            initial_regs = [0] * 32
            initial_regs[16] = 0x00ff00ff00ff0080
            e = ExpectedState(pc=4)
            e.intregs[16] = 0xff00ff00ff0080
            e.intregs[6] = 0xff00ff00ff0080
            if '.' in choice:
                e.crregs[0] = 0x4
            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_addis_nonzero_r0_regression(self):
        lst = [f"addis 3, 0, 1"]
        print(lst)
        initial_regs = [0] * 32
        initial_regs[0] = 5
        e = ExpectedState(initial_regs, pc=4)
        e.intregs[3] = 0x10000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_addis_nonzero_r0(self):
        for i in range(10):
            imm = random.randint(-(1 << 15), (1 << 15)-1)
            lst = [f"addis 3, 0, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[0] = random.randint(0, (1 << 64)-1)
            e = ExpectedState(pc=4)
            e.intregs[0] = initial_regs[0]
            e.intregs[3] = (imm << 16) & ((1<<64)-1)
            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_rand_imm(self):
        insns = ["addi", "addis", "subfic"]
        for i in range(10):
            choice = random.choice(insns)
            imm = random.randint(-(1 << 15), (1 << 15)-1)
            lst = [f"{choice} 3, 1, {imm}"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)

            e = ExpectedState(pc=4)
            e.intregs[1] = initial_regs[1]
            if choice == "addi":
                result = initial_regs[1] + imm
                e.intregs[3] = result & ((2**64)-1)
            elif choice == "addis":
                result = initial_regs[1] + (imm<<16)
                if result < 0:
                    e.intregs[3] = (result + 2**64) & ((2**64)-1)
                else:
                    e.intregs[3] = result & ((2**64)-1)
            elif choice == "subfic":
                result = ~initial_regs[1] + imm + 1
                value = (~initial_regs[1]+2**64) + (imm) + 1
                if imm < 0:
                    value += 2**64
                carry_out = value & (1<<64) != 0
                if imm >= 0:
                    carry_out32 = (((~initial_regs[1]+2**64) & 0xffff_ffff) + \
                            (imm) + 1) & (1<<32)
                else:
                    carry_out32 = (((~initial_regs[1]+2**64) & 0xffff_ffff) + \
                            (imm+2**32) + 1) & (1<<32)
                if result < 0:
                    e.intregs[3] = (result + 2**64) & ((2**64)-1)
                else:
                    e.intregs[3] = result & ((2**64)-1)
                e.ca = carry_out | (carry_out32>>31)

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

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
            # calculate result *including carry* and mask it to 64-bit
            # (if it overflows, we don't care, because this is not addeo)
            result = 1 + initial_regs[6] + initial_regs[7]
            carry_out = result & (1<<64) != 0 # detect 65th bit as carry-out?
            carry_out32 = ((initial_regs[6] & 0xffff_ffff) + \
                    (initial_regs[7] & 0xffff_ffff)) & (1<<32)
            result = result & ((1<<64)-1) # round
            eq = 0
            gt = 0
            le = 0
            if (result & (1<<63)) != 0:
                le = 1
            elif result == 0:
                eq = 1
            else:
                gt = 1
            # now construct the state
            e = ExpectedState(pc=4)
            e.intregs[6] = initial_regs[6] # should be same as initial
            e.intregs[7] = initial_regs[7] # should be same as initial
            e.intregs[5] = result
            # carry_out goes into bit 0 of ca, carry_out32 into bit 1
            e.ca = carry_out | (carry_out32>>31)
            # eq goes into bit 1 of CR0, gt into bit 2, le into bit 3.
            # SO goes into bit 0 but overflow doesn't occur here [we hope]
            e.crregs[0] = (eq<<1) | (gt<<2) | (le<<3)

            self.add_case(Program(lst, bigendian),
                          initial_regs, initial_sprs, expected=e)

    def case_cmp(self):
        lst = ["subf. 1, 6, 7",
               "cmp cr2, 1, 6, 7"]
        initial_regs = [0] * 32
        initial_regs[6] = 0x10
        initial_regs[7] = 0x05
        e = ExpectedState(pc=8)
        e.intregs[6] = 0x10
        e.intregs[7] = 0x5
        e.intregs[1] = 0xfffffffffffffff5
        e.crregs[0] = 0x8
        e.crregs[2] = 0x4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmp2(self):
        lst = ["cmp cr2, 0, 2, 3"]
        initial_regs = [0] * 32
        initial_regs[2] = 0xffffffffaaaaaaaa
        initial_regs[3] = 0x00000000aaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[2] = 0xffffffffaaaaaaaa
        e.intregs[3] = 0xaaaaaaaa
        e.crregs[2] = 0x2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = ["cmp cr2, 0, 4, 5"]
        initial_regs = [0] * 32
        initial_regs[4] = 0x00000000aaaaaaaa
        initial_regs[5] = 0xffffffffaaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[4] = 0xaaaaaaaa
        e.intregs[5] = 0xffffffffaaaaaaaa
        e.crregs[2] = 0x2
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmp3(self):
        lst = ["cmp cr2, 1, 2, 3"]
        initial_regs = [0] * 32
        initial_regs[2] = 0xffffffffaaaaaaaa
        initial_regs[3] = 0x00000000aaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[2] = 0xffffffffaaaaaaaa
        e.intregs[3] = 0xaaaaaaaa
        e.crregs[2] = 0x8
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

        lst = ["cmp cr2, 1, 4, 5"]
        initial_regs = [0] * 32
        initial_regs[4] = 0x00000000aaaaaaaa
        initial_regs[5] = 0xffffffffaaaaaaaa
        e = ExpectedState(pc=4)
        e.intregs[4] = 0xaaaaaaaa
        e.intregs[5] = 0xffffffffaaaaaaaa
        e.crregs[2] = 0x4
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)

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

        e = ExpectedState(pc=4)
        e.intregs[10] = 0xfedf3fff0001c025
        e.intregs[17] = 0x1c026
        e.crregs[0] = 0x3
        e.crregs[1] = 0x5
        e.crregs[3] = 0x5
        e.crregs[4] = 0x5
        e.crregs[6] = 0x5
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR, expected=e)

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

        e = ExpectedState(pc=4)
        e.intregs[10] = 0xfedf3fff0001c025
        e.intregs[17] = 0x1c026
        e.crregs[0] = 0x3
        e.crregs[1] = 0x5
        e.crregs[3] = 0x5
        e.crregs[4] = 0x5
        e.crregs[6] = 0x5
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        p = Program(lst, bigendian)
        p.assembly = '\n'.join(dis)+'\n'
        self.add_case(p, initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR, expected=e)

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

        e = ExpectedState(pc=4)
        e.intregs[4] = 0xffff6dc1
        e.crregs[0] = 0x5
        e.crregs[1] = 0x9
        e.crregs[2] = 0x7
        e.crregs[3] = 0x5
        e.crregs[4] = 0x9
        e.crregs[5] = 0x9
        e.crregs[6] = 0x9
        e.crregs[7] = 0x9
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR, expected=e)

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

        e = ExpectedState(pc=4)
        e.intregs[13] = 0x301fc7a7
        e.crregs[0] = 0x9
        e.crregs[2] = 0x2
        e.crregs[3] = 0x1
        e.crregs[4] = 0x5
        e.crregs[5] = 0x5
        e.crregs[6] = 0x9
        e.crregs[7] = 0x3
        e.so = 0x1
        e.ov = 0x3
        e.ca = 0x3

        self.add_case(Program(lst, bigendian), initial_regs,
                                initial_sprs = {'XER': XER},
                                initial_cr = CR, expected=e)

    def case_extsb(self):
        insns = ["extsb", "extsh", "extsw"]
        for i in range(10):
            choice = random.choice(insns)
            lst = [f"{choice} 3, 1"]
            print(lst)
            initial_regs = [0] * 32
            initial_regs[1] = random.randint(0, (1 << 64)-1)

            e = ExpectedState(pc=4)
            e.intregs[1] = initial_regs[1]
            if choice == "extsb":
                s = ((initial_regs[1] & 0x1000_0000_0000_0080)>>7)&0x1
                if s == 1:
                    value = 0xffff_ffff_ffff_ff<<8
                else:
                    value = 0x0
                e.intregs[3] = value | (initial_regs[1] & 0xff)
            elif choice == "extsh":
                s = ((initial_regs[1] & 0x1000_0000_0000_8000)>>15)&0x1
                if s == 1:
                    value = 0xffff_ffff_ffff<<16
                else:
                    value = 0x0
                e.intregs[3] = value | (initial_regs[1] & 0xffff)
            else:
                s = ((initial_regs[1] & 0x1000_0000_8000_0000)>>31)&0x1
                if s == 1:
                    value = 0xffff_ffff<<32
                else:
                    value = 0x0
                e.intregs[3] = value | (initial_regs[1] & 0xffff_ffff)

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

    def case_cmpeqb(self):
        lst = ["cmpeqb cr1, 1, 2"]
        for i in range(20):
            initial_regs = [0] * 32
            initial_regs[1] = i
            initial_regs[2] = 0x0001030507090b0f

            e = ExpectedState(pc=4)
            e.intregs[1] = i
            e.intregs[2] = 0x1030507090b0f
            matlst = [ 0x00, 0x01, 0x03, 0x05, 0x07, 0x09, 0x0b, 0x0f ]
            for j in matlst:
                if j == i:
                    e.crregs[1] = 0x4

            self.add_case(Program(lst, bigendian), initial_regs, expected=e)

