""" Decoder tests

related bugs:

 *
"""

import unittest

from openpower.test.alu.maddrs_cases import MADDRSTestCase
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestMADDRS(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(MADDRSTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
