# SPDX-License-Identifier: LGPLv3+
# Copyright (C) 2020, 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# Funded by NLnet http://nlnet.nl

import unittest
from openpower.decoder.isa.mem import Mem, MemMMap
from openpower.util import log
import ctypes
from openpower.syscalls import ppc_flags
import tempfile


class TestMem(unittest.TestCase):
    def test_mem_align_st(self):
        m = Mem(row_bytes=8, initial_mem={})
        m.st(4, 0x12345678, width=4, swap=False)
        d = m.dump()
        log("dict", d)
        self.assertEqual(d, [(0, 0x1234567800000000)])

    def test_mem_misalign_st(self):
        m = Mem(row_bytes=8, initial_mem={}, misaligned_ok=True)
        m.st(3, 0x12345678, width=4, swap=False)
        d = m.dump()
        log("dict", d)
        self.assertEqual(d, [(0, 0x0012345678000000)])

    def test_mem_misalign_st_rollover(self):
        m = Mem(row_bytes=8, initial_mem={}, misaligned_ok=True)
        m.st(6, 0x912345678, width=8, swap=False)
        d = m.dump()
        log("dict", d)
        self.assertEqual(d, [(0, 0x5678000000000000),
                             (8, 0x0000000000091234)])


class TestMemCommon(unittest.TestCase):
    maxDiff = None
    MemCls = Mem

    @staticmethod
    def log_fancy_to_string(m):
        def log2(*args, kind):
            text_parts.append(" ".join(args))

        text_parts = []
        m.log_fancy(log=log2)
        return "\n".join(text_parts)

    def test_log_fancy(self):
        def log2(*args, kind):
            text_parts.append(" ".join(args))

        m = self.MemCls(row_bytes=8, initial_mem=(0x58, [
            0x5DE6DA2A1137745E, 0x6054D17B4C773D2D,
            0x5B66920D9540B825, 0x7753D053D9854A8F,
            0x9F2A58E2B5B79829, 0x974AC142D081CE83,
            0xAA963F95FC566F57, 0xE63A95A3F654A57E,
            0x103709510CBE0EEF, 0xF6A18DEDFE1B69A5,
            0x5053575776376ACD, 0xCFDFF67B7C5096C2,
            0x9F8FC1B06E7868A0, 0x6E7B1D27CCBAF8E7,
            0xEB91B92FAF546BA1, 0x21FB683F34641876,
        ]))

        m.st(0x7fff_fedc_ba98, 0xabcdef0123456789, width=8, swap=False)

        text = self.log_fancy_to_string(m)
        self.assertEqual(text, """
Memory:
0x00000050:  00 00 00 00 00 00 00 00  5E 74 37 11 2A DA E6 5D  |........^t7.*..]|
0x00000060:  2D 3D 77 4C 7B D1 54 60  25 B8 40 95 0D 92 66 5B  |-=wL{.T`%.@...f[|
0x00000070:  8F 4A 85 D9 53 D0 53 77  29 98 B7 B5 E2 58 2A 9F  |.J..S.Sw)....X*.|
0x00000080:  83 CE 81 D0 42 C1 4A 97  57 6F 56 FC 95 3F 96 AA  |....B.J.WoV..?..|
0x00000090:  7E A5 54 F6 A3 95 3A E6  EF 0E BE 0C 51 09 37 10  |~.T...:.....Q.7.|
0x000000A0:  A5 69 1B FE ED 8D A1 F6  CD 6A 37 76 57 57 53 50  |.i.......j7vWWSP|
0x000000B0:  C2 96 50 7C 7B F6 DF CF  A0 68 78 6E B0 C1 8F 9F  |..P|{....hxn....|
0x000000C0:  E7 F8 BA CC 27 1D 7B 6E  A1 6B 54 AF 2F B9 91 EB  |....'.{n.kT./...|
0x000000D0:  76 18 64 34 3F 68 FB 21  00 00 00 00 00 00 00 00  |v.d4?h.!........|
*
0x7FFFFEDCBA90:  00 00 00 00 00 00 00 00  89 67 45 23 01 EF CD AB  |.........gE#....|
""")


class TestMemMMap(TestMemCommon):
    MemCls = MemMMap

    def test_read_ctypes(self):
        m = MemMMap(row_bytes=8, initial_mem=(0x58, [
            0x5DE6DA2A1137745E, 0x6054D17B4C773D2D,
            0x5B66920D9540B825, 0x7753D053D9854A8F,
            0x9F2A58E2B5B79829, 0x974AC142D081CE83,
            0xAA963F95FC566F57, 0xE63A95A3F654A57E,
            0x103709510CBE0EEF, 0xF6A18DEDFE1B69A5,
            0x5053575776376ACD, 0xCFDFF67B7C5096C2,
            0x9F8FC1B06E7868A0, 0x6E7B1D27CCBAF8E7,
            0xEB91B92FAF546BA1, 0x21FB683F34641876,
        ]))

        bytes_ = m.get_ctypes(0x58, 128, False)

        self.assertSequenceEqual(bytes_, [
            0x5E, 0x74, 0x37, 0x11, 0x2A, 0xDA, 0xE6, 0x5D,
            0x2D, 0x3D, 0x77, 0x4C, 0x7B, 0xD1, 0x54, 0x60,
            0x25, 0xB8, 0x40, 0x95, 0x0D, 0x92, 0x66, 0x5B,
            0x8F, 0x4A, 0x85, 0xD9, 0x53, 0xD0, 0x53, 0x77,
            0x29, 0x98, 0xB7, 0xB5, 0xE2, 0x58, 0x2A, 0x9F,
            0x83, 0xCE, 0x81, 0xD0, 0x42, 0xC1, 0x4A, 0x97,
            0x57, 0x6F, 0x56, 0xFC, 0x95, 0x3F, 0x96, 0xAA,
            0x7E, 0xA5, 0x54, 0xF6, 0xA3, 0x95, 0x3A, 0xE6,
            0xEF, 0x0E, 0xBE, 0x0C, 0x51, 0x09, 0x37, 0x10,
            0xA5, 0x69, 0x1B, 0xFE, 0xED, 0x8D, 0xA1, 0xF6,
            0xCD, 0x6A, 0x37, 0x76, 0x57, 0x57, 0x53, 0x50,
            0xC2, 0x96, 0x50, 0x7C, 0x7B, 0xF6, 0xDF, 0xCF,
            0xA0, 0x68, 0x78, 0x6E, 0xB0, 0xC1, 0x8F, 0x9F,
            0xE7, 0xF8, 0xBA, 0xCC, 0x27, 0x1D, 0x7B, 0x6E,
            0xA1, 0x6B, 0x54, 0xAF, 0x2F, 0xB9, 0x91, 0xEB,
            0x76, 0x18, 0x64, 0x34, 0x3F, 0x68, 0xFB, 0x21,
        ])

    def test_write_ctypes(self):
        m = MemMMap(row_bytes=8, initial_mem=(0x58, [
            0x5DE6DA2A1137745E, 0x6054D17B4C773D2D,
        ]))

        bytes_ = m.get_ctypes(0x160, 16, True)

        self.assertIsInstance(bytes_, ctypes.c_ubyte * 16)

        for i in range(16):
            bytes_[i] = i * 0x11

        text = self.log_fancy_to_string(m)
        self.assertEqual(text, """
Memory:
0x00000050:  00 00 00 00 00 00 00 00  5E 74 37 11 2A DA E6 5D  |........^t7.*..]|
0x00000060:  2D 3D 77 4C 7B D1 54 60  00 00 00 00 00 00 00 00  |-=wL{.T`........|
*
0x00000160:  00 11 22 33 44 55 66 77  88 99 AA BB CC DD EE FF  |.."3DUfw........|
""")

    def make_mmap_with_pattern(self):
        m = MemMMap(row_bytes=8, emulating_mmap=True)

        prot = ppc_flags.PROT_READ | ppc_flags.PROT_WRITE
        flags = ppc_flags.MAP_PRIVATE | ppc_flags.MAP_FIXED
        retval = m.mmap_syscall(addr=1 << 16, length=15 << 16, prot=prot,
                                flags=flags, fd=-1, offset=0, is_mmap2=False)
        self.assertEqual(retval, 1 << 16)

        text = self.log_fancy_to_string(m)
        self.assertEqual(text, """
Memory:

""")

        for i in range(1, 16):
            bytes_ = m.get_ctypes(i << 16, 16, True)

            self.assertIsInstance(bytes_, ctypes.c_ubyte * 16)

            for j in range(16):
                bytes_[j] = i * 0x10 + j

        text = self.log_fancy_to_string(m)
        self.assertEqual(text, """
Memory:
0x00010000:  10 11 12 13 14 15 16 17  18 19 1A 1B 1C 1D 1E 1F  |................|
*
0x00020000:  20 21 22 23 24 25 26 27  28 29 2A 2B 2C 2D 2E 2F  | !"#$%&'()*+,-./|
*
0x00030000:  30 31 32 33 34 35 36 37  38 39 3A 3B 3C 3D 3E 3F  |0123456789:;<=>?|
*
0x00040000:  40 41 42 43 44 45 46 47  48 49 4A 4B 4C 4D 4E 4F  |@ABCDEFGHIJKLMNO|
*
0x00050000:  50 51 52 53 54 55 56 57  58 59 5A 5B 5C 5D 5E 5F  |PQRSTUVWXYZ[\]^_|
*
0x00060000:  60 61 62 63 64 65 66 67  68 69 6A 6B 6C 6D 6E 6F  |`abcdefghijklmno|
*
0x00070000:  70 71 72 73 74 75 76 77  78 79 7A 7B 7C 7D 7E 7F  |pqrstuvwxyz{|}~.|
*
0x00080000:  80 81 82 83 84 85 86 87  88 89 8A 8B 8C 8D 8E 8F  |................|
*
0x00090000:  90 91 92 93 94 95 96 97  98 99 9A 9B 9C 9D 9E 9F  |................|
*
0x000A0000:  A0 A1 A2 A3 A4 A5 A6 A7  A8 A9 AA AB AC AD AE AF  |................|
*
0x000B0000:  B0 B1 B2 B3 B4 B5 B6 B7  B8 B9 BA BB BC BD BE BF  |................|
*
0x000C0000:  C0 C1 C2 C3 C4 C5 C6 C7  C8 C9 CA CB CC CD CE CF  |................|
*
0x000D0000:  D0 D1 D2 D3 D4 D5 D6 D7  D8 D9 DA DB DC DD DE DF  |................|
*
0x000E0000:  E0 E1 E2 E3 E4 E5 E6 E7  E8 E9 EA EB EC ED EE EF  |................|
*
0x000F0000:  F0 F1 F2 F3 F4 F5 F6 F7  F8 F9 FA FB FC FD FE FF  |................|
""")
        return m

    def test_mmap_anon(self):
        m = self.make_mmap_with_pattern()

        prot = ppc_flags.PROT_READ | ppc_flags.PROT_WRITE
        flags = ppc_flags.MAP_PRIVATE | ppc_flags.MAP_FIXED
        retval = m.mmap_syscall(addr=3 << 16, length=2 << 16, prot=prot,
                                flags=flags, fd=-1, offset=0, is_mmap2=False)
        self.assertEqual(retval, 3 << 16)

        text = self.log_fancy_to_string(m)
        self.assertEqual(text, """
Memory:
0x00010000:  10 11 12 13 14 15 16 17  18 19 1A 1B 1C 1D 1E 1F  |................|
*
0x00020000:  20 21 22 23 24 25 26 27  28 29 2A 2B 2C 2D 2E 2F  | !"#$%&'()*+,-./|
*
0x00050000:  50 51 52 53 54 55 56 57  58 59 5A 5B 5C 5D 5E 5F  |PQRSTUVWXYZ[\]^_|
*
0x00060000:  60 61 62 63 64 65 66 67  68 69 6A 6B 6C 6D 6E 6F  |`abcdefghijklmno|
*
0x00070000:  70 71 72 73 74 75 76 77  78 79 7A 7B 7C 7D 7E 7F  |pqrstuvwxyz{|}~.|
*
0x00080000:  80 81 82 83 84 85 86 87  88 89 8A 8B 8C 8D 8E 8F  |................|
*
0x00090000:  90 91 92 93 94 95 96 97  98 99 9A 9B 9C 9D 9E 9F  |................|
*
0x000A0000:  A0 A1 A2 A3 A4 A5 A6 A7  A8 A9 AA AB AC AD AE AF  |................|
*
0x000B0000:  B0 B1 B2 B3 B4 B5 B6 B7  B8 B9 BA BB BC BD BE BF  |................|
*
0x000C0000:  C0 C1 C2 C3 C4 C5 C6 C7  C8 C9 CA CB CC CD CE CF  |................|
*
0x000D0000:  D0 D1 D2 D3 D4 D5 D6 D7  D8 D9 DA DB DC DD DE DF  |................|
*
0x000E0000:  E0 E1 E2 E3 E4 E5 E6 E7  E8 E9 EA EB EC ED EE EF  |................|
*
0x000F0000:  F0 F1 F2 F3 F4 F5 F6 F7  F8 F9 FA FB FC FD FE FF  |................|
""")

    def test_mmap_file(self):
        m = self.make_mmap_with_pattern()
        with tempfile.NamedTemporaryFile() as file:
            file.truncate(5 << 16)
            file.write(b"Shouldn't see this\n")
            file.seek(1 << 16)
            file.write(b"Shouldn't see this #2\n")
            file.seek(2 << 16)
            file.write(b"Hello World!\n")
            file.seek(3 << 16)
            file.write(b"Foo Bar\n")
            file.seek(4 << 16)
            file.write(b"Shouldn't see this #3\n")
            file.flush()
            fd = file.file.fileno()

            prot = ppc_flags.PROT_READ | ppc_flags.PROT_WRITE
            flags = ppc_flags.MAP_PRIVATE | ppc_flags.MAP_FIXED
            retval = m.mmap_syscall(addr=3 << 16, length=2 << 16, prot=prot,
                                    flags=flags, fd=fd, offset=2 << 16,
                                    is_mmap2=False)
            self.assertEqual(retval, 3 << 16)

            text = self.log_fancy_to_string(m)
            self.assertEqual(text, """
Memory:
0x00010000:  10 11 12 13 14 15 16 17  18 19 1A 1B 1C 1D 1E 1F  |................|
*
0x00020000:  20 21 22 23 24 25 26 27  28 29 2A 2B 2C 2D 2E 2F  | !"#$%&'()*+,-./|
*
0x00030000:  48 65 6C 6C 6F 20 57 6F  72 6C 64 21 0A 00 00 00  |Hello World!....|
*
0x00040000:  46 6F 6F 20 42 61 72 0A  00 00 00 00 00 00 00 00  |Foo Bar.........|
*
0x00050000:  50 51 52 53 54 55 56 57  58 59 5A 5B 5C 5D 5E 5F  |PQRSTUVWXYZ[\]^_|
*
0x00060000:  60 61 62 63 64 65 66 67  68 69 6A 6B 6C 6D 6E 6F  |`abcdefghijklmno|
*
0x00070000:  70 71 72 73 74 75 76 77  78 79 7A 7B 7C 7D 7E 7F  |pqrstuvwxyz{|}~.|
*
0x00080000:  80 81 82 83 84 85 86 87  88 89 8A 8B 8C 8D 8E 8F  |................|
*
0x00090000:  90 91 92 93 94 95 96 97  98 99 9A 9B 9C 9D 9E 9F  |................|
*
0x000A0000:  A0 A1 A2 A3 A4 A5 A6 A7  A8 A9 AA AB AC AD AE AF  |................|
*
0x000B0000:  B0 B1 B2 B3 B4 B5 B6 B7  B8 B9 BA BB BC BD BE BF  |................|
*
0x000C0000:  C0 C1 C2 C3 C4 C5 C6 C7  C8 C9 CA CB CC CD CE CF  |................|
*
0x000D0000:  D0 D1 D2 D3 D4 D5 D6 D7  D8 D9 DA DB DC DD DE DF  |................|
*
0x000E0000:  E0 E1 E2 E3 E4 E5 E6 E7  E8 E9 EA EB EC ED EE EF  |................|
*
0x000F0000:  F0 F1 F2 F3 F4 F5 F6 F7  F8 F9 FA FB FC FD FE FF  |................|
""")

            bytes_ = m.get_ctypes(3 << 16, 16, True)

            self.assertIsInstance(bytes_, ctypes.c_ubyte * 16)

            for i in range(16):
                bytes_[i] = i * 0x11

            text = self.log_fancy_to_string(m)
            self.assertEqual(text, """
Memory:
0x00010000:  10 11 12 13 14 15 16 17  18 19 1A 1B 1C 1D 1E 1F  |................|
*
0x00020000:  20 21 22 23 24 25 26 27  28 29 2A 2B 2C 2D 2E 2F  | !"#$%&'()*+,-./|
*
0x00030000:  00 11 22 33 44 55 66 77  88 99 AA BB CC DD EE FF  |.."3DUfw........|
*
0x00040000:  46 6F 6F 20 42 61 72 0A  00 00 00 00 00 00 00 00  |Foo Bar.........|
*
0x00050000:  50 51 52 53 54 55 56 57  58 59 5A 5B 5C 5D 5E 5F  |PQRSTUVWXYZ[\]^_|
*
0x00060000:  60 61 62 63 64 65 66 67  68 69 6A 6B 6C 6D 6E 6F  |`abcdefghijklmno|
*
0x00070000:  70 71 72 73 74 75 76 77  78 79 7A 7B 7C 7D 7E 7F  |pqrstuvwxyz{|}~.|
*
0x00080000:  80 81 82 83 84 85 86 87  88 89 8A 8B 8C 8D 8E 8F  |................|
*
0x00090000:  90 91 92 93 94 95 96 97  98 99 9A 9B 9C 9D 9E 9F  |................|
*
0x000A0000:  A0 A1 A2 A3 A4 A5 A6 A7  A8 A9 AA AB AC AD AE AF  |................|
*
0x000B0000:  B0 B1 B2 B3 B4 B5 B6 B7  B8 B9 BA BB BC BD BE BF  |................|
*
0x000C0000:  C0 C1 C2 C3 C4 C5 C6 C7  C8 C9 CA CB CC CD CE CF  |................|
*
0x000D0000:  D0 D1 D2 D3 D4 D5 D6 D7  D8 D9 DA DB DC DD DE DF  |................|
*
0x000E0000:  E0 E1 E2 E3 E4 E5 E6 E7  E8 E9 EA EB EC ED EE EF  |................|
*
0x000F0000:  F0 F1 F2 F3 F4 F5 F6 F7  F8 F9 FA FB FC FD FE FF  |................|
""")

            # assert file wasn't modified by memory write
            file.seek(2 << 16)
            bytes_ = file.read(16)
            self.assertEqual(bytes_, b"Hello World!\n\0\0\0")


if __name__ == '__main__':
    unittest.main()
