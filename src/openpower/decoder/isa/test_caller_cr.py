""" CR tests
"""

import unittest

from openpower.test.cr.cr_cases import CRTestCase
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestBigInt(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(CRTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
