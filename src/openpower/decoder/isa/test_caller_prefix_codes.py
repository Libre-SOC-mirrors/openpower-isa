""" prefix-codes tests
"""

import unittest

from openpower.test.prefix_codes.prefix_codes_cases import PrefixCodesCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestPrefixCodes(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(PrefixCodesCases().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
