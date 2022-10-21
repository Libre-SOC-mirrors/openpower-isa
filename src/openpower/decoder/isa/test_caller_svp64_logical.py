""" Decoder tests

related bugs:

 *
"""

import unittest

from openpower.test.logical.svp64_cases import SVP64LogicalTestCase
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestSVP64Logical(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64LogicalTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
