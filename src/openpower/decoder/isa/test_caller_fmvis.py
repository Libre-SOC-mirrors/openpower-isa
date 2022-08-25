""" Decoder tests

related bugs:

 *
"""

import unittest
from openpower.test.runner import TestRunnerBase
from openpower.test.alu.fmvis_cases import FMVISTestCase

# writing the test_caller invocation this way makes it work with pytest


class TestFMVIS(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(FMVISTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
