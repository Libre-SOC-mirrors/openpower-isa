"""Trap tests

related bugs:

 * https://bugs.libre-soc.org/show_bug.cgi?id=982
"""

import unittest

from openpower.test.trap.trap_cases import TrapTestCase
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TrapTest(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(TrapTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
