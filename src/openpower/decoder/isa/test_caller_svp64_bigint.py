""" svp64 bigint tests
"""

import unittest

from openpower.test.bigint.bigint_cases import SVP64BigIntCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestSVP64BigInt(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64BigIntCases().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
