""" bigint tests
"""

import unittest

from openpower.test.bigint.shadd_cases import ShiftAddCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestShAdd(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(ShiftAddCases().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
