import random
from openpower.test.common import TestAccumulatorBase, skip_case
from openpower.endian import bigendian
from openpower.simulator.program import Program
#from openpower.decoder.selectable_int import SelectableInt
#from openpower.decoder.power_enums import XER_bits
#from openpower.decoder.isa.caller import special_sprs
from openpower.decoder.helpers import exts
from openpower.test.state import ExpectedState
from openpower.util import log
from pathlib import Path
#import gzip
#import json
#import sys
#from hashlib import sha256
#from functools import lru_cache

class SysCallTestCase(TestAccumulatorBase):
    def case_sc(self):
        lst = [f"sc"]
        print(lst)
        message = b'Hello world!\n'
        message_len = len(message)
        initial_regs = [0] * 32
        initial_regs[0] = 4 # write syscall, see ppc64 ABI
        initial_regs[3] = 1 # fd = 1 (stdout)
        # The example code stores bits 0-63 of the msg into r4
        # but message is actually 13 bytes, so just store 8 for now
        msg_8bytes = int(message[0:8].hex(), 16)
        initial_regs[4] =  msg_8bytes
        initial_regs[5] = 8 # message_len
        e = ExpectedState(initial_regs, pc=4)
        e.intregs[3] = 0x10000
        self.add_case(Program(lst, bigendian), initial_regs, expected=e)