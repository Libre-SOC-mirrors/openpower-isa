from openpower.test.common import TestAccumulatorBase
from openpower.endian import bigendian
from openpower.simulator.program import Program
from hashlib import sha256


def hash_256(v):
    return int.from_bytes(
        sha256(bytes(v, encoding='utf-8')).digest(),
        byteorder='little'
    )


class BitManipTestCase(TestAccumulatorBase):
    def case_ternaryi(self):
        po = 5
        rt = 3
        ra = 4
        rb = 5
        rc = 1
        xo = 0
        for i in range(100):
            imm = hash_256(f"ternaryi imm {i}") & 0xFF
            instr = po
            instr = (instr << 5) | rt
            instr = (instr << 5) | ra
            instr = (instr << 5) | rb
            instr = (instr << 8) | imm
            instr = (instr << 2) | xo
            instr = (instr << 1) | rc
            lst = [f".4byte {hex(instr)}"]
            initial_regs = [0] * 32
            initial_regs[3] = hash_256(f"ternaryi rt {i}") % 2 ** 64
            initial_regs[4] = hash_256(f"ternaryi ra {i}") % 2 ** 64
            initial_regs[5] = hash_256(f"ternaryi rb {i}") % 2 ** 64
            self.add_case(Program(lst, bigendian), initial_regs)
