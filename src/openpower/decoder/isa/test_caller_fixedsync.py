""" sync tests
"""

import unittest

from openpower.test.ldst.fixedsync_cases import FixedSyncCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestFixedSync(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(FixedSyncCases().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
