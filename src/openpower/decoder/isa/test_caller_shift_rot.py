""" Decoder tests

related bugs:

 *
"""

import unittest
from openpower.test.runner import TestRunnerBase
from openpower.test.shift_rot.shift_rot_cases2 import ShiftRotTestCase2

# writing the test_caller invocation this way makes it work with pytest


class TestShiftRot2(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(ShiftRotTestCase2().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
