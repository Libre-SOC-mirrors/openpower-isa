""" fmv/fcvt tests
"""

import unittest

from openpower.test.fmv_fcvt.fmv_fcvt import (FMvFCvtCases,
                                              SVP64FMvFCvtCases)
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestFMvFCvtCases(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(FMvFCvtCases().test_data, fp=True)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


class TestSVP64FMvFCvtCases(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64FMvFCvtCases().test_data, fp=True)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
