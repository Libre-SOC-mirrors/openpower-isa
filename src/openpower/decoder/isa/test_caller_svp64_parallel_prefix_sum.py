""" svp64 parallel prefix-sum tests
"""

import unittest

from openpower.test.svp64.parallel_prefix_sum import ParallelPrefixSumCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestSVP64ParallelPrefixSum(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(ParallelPrefixSumCases().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
