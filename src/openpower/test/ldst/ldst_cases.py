from openpower.simulator.program import Program
from openpower.endian import bigendian
from openpower.test.common import TestAccumulatorBase


class LDSTTestCase(TestAccumulatorBase):

    def case_1_load(self):
        lst = ["lhz 3, 0(1)"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0004
        initial_regs[2] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_2_load_store(self):
        lst = [
               "stb 3, 1(2)",
               "lbz 4, 1(2)",
        ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0004
        initial_regs[2] = 0x0008
        initial_regs[3] = 0x00ee
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_3_load_store(self):
        lst = ["sth 4, 0(2)",
               "lhz 4, 0(2)"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0004
        initial_regs[2] = 0x0002
        initial_regs[3] = 0x15eb
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_4_load_store_rev_ext(self):
        lst = ["stwx 1, 4, 2",
               "lwbrx 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_5_load_store_rev_ext(self):
        lst = ["stwbrx 1, 4, 2",
               "lwzx 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_6_load_store_rev_ext(self):
        lst = ["stwbrx 1, 4, 2",
               "lwbrx 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_7_load_store_d(self):
        lst = [
               "std 3, 0(2)",
               "ld 4, 0(2)",
        ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0004
        initial_regs[2] = 0x0008
        initial_regs[3] = 0x00ee
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_8_load_store_d_update(self):
        lst = [
               "stdu 3, 0(2)",
               "ld 4, 0(2)",
        ]
        initial_regs = [0] * 32
        initial_regs[1] = 0x0004
        initial_regs[2] = 0x0008
        initial_regs[3] = 0x00ee
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_9_load_algebraic_1(self):
        lst = ["lwax 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0xf000000f0000ffff, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_9_load_algebraic_2(self):
        lst = ["lwax 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x7000000f0000ffff, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_9_load_algebraic_3(self):
        lst = ["lwaux 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0xf000000f0000ffff, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_9_load_algebraic_4(self):
        lst = ["lwa 3, 4(4)"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[4] = 0x0020
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0xf000000f1234ffff, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_10_load_algebraic_1(self):
        lst = ["lhax 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x0000f00f0000ffff, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_10_load_algebraic_2(self):
        lst = ["lhax 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x0000700f0000ffff, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

    def case_10_load_store_cix(self):
        lst = ["stbcix 1, 4, 2",
               "lwzcix 3, 4, 2"]
        initial_regs = [0] * 32
        initial_regs[1] = 0x5678
        initial_regs[2] = 0x001c
        initial_regs[4] = 0x0008
        initial_mem = {0x0000: (0x5432123412345678, 8),
                       0x0008: (0xabcdef0187654321, 8),
                       0x0020: (0x1828384822324252, 8),
                        }
        self.add_case(Program(lst, bigendian), initial_regs,
                             initial_mem=initial_mem)

