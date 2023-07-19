""" fminmax tests
"""

import unittest

from openpower.test.fptrans.fminmax_cases import FMinMaxCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestFMinMax(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(FMinMaxCases().test_data, fp=True)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
