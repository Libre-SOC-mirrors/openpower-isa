""" fptrans tests
"""

import unittest

from openpower.test.fptrans.fptrans_cases import FPTransCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestFPTrans(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(FPTransCases().test_data, fp=True)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
