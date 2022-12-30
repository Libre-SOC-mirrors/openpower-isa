# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2020, 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl

import unittest
from openpower.decoder.isa.mem import Mem
from openpower.util import log


class TestMem(unittest.TestCase):

    def test_mem_align_st(self):
        m = Mem(row_bytes=8, initial_mem={})
        m.st(4, 0x12345678, width=4, swap=False)
        d = m.dump()
        log ("dict", d)
        self.assertEqual(d, [(0, 0x1234567800000000)])

    def test_mem_misalign_st_rollover(self):
        m = Mem(row_bytes=8, initial_mem={}, misaligned_ok=True)
        m.st(6, 0x912345678, width=8, swap=False)
        d = m.dump()
        log ("dict", d)
        self.assertEqual(d, [(0, 0x5678000000000000),
                             (8, 0x0000000000091234)])


if __name__ == '__main__':
    unittest.main()
