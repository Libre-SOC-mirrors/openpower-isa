""" Decoder tests

related bugs:

 *
"""

import unittest
from openpower.test.runner import TestRunnerBase
from openpower.test.mul.mul_cases import MulTestCases2Arg, SVP64MAdd

# writing the test_caller invocation this way makes it work with pytest


class TestMul2Arg(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(MulTestCases2Arg().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


class TestSVP64MAdd(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64MAdd().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
