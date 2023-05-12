from openpower.fpscr import FPSCRState
import unittest


class TestFPSCR(unittest.TestCase):
    def test_smoke_test(self):
        """ test to ensure FPSCR isn't horribly broken -- not at all thorough -- a smoke-test """
        FPSCR = FPSCRState()
        self.assertEqual(FPSCR.RN, 0)
        FPSCR.RN = 3
        self.assertEqual(FPSCR.RN, 3)
        expected = 0x3
        self.assertEqual(FPSCR, expected)
        self.assertEqual(FPSCR.VXCVI, 0)
        FPSCR.VXCVI = 1
        self.assertEqual(FPSCR.VXCVI, 1)
        expected |= 1 << (64 - 55 - 1)
        self.assertEqual(FPSCR, expected)
        self.assertEqual(FPSCR.FX, 0)
        FPSCR.FX = 1
        self.assertEqual(FPSCR.FX, 1)
        expected |= 1 << (64 - 32 - 1)
        self.assertEqual(FPSCR, expected)
        self.assertEqual(FPSCR.C, 0)
        FPSCR.C = 1
        self.assertEqual(FPSCR.C, 1)
        expected |= 1 << (64 - 47 - 1)
        self.assertEqual(FPSCR, expected)
        self.assertEqual(FPSCR.FPRF, 0b10000)
        self.assertEqual(FPSCR.FPCC, 0b0000)
        self.assertEqual(FPSCR.FE, 0)
        FPSCR.FE = 1
        self.assertEqual(FPSCR.FE, 1)
        expected |= 1 << (64 - 50 - 1)
        self.assertEqual(FPSCR, expected)
        self.assertEqual(FPSCR.FPRF, 0b10010)
        self.assertEqual(FPSCR.FPCC, 0b0010)


if __name__ == "__main__":
    unittest.main()
