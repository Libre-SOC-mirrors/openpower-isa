""" Decoder tests

related bugs:

 *
"""

import unittest

from openpower.test.alu.svp64_cases import SVP64ALUTestCase
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestSVP64ALU(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64ALUTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
