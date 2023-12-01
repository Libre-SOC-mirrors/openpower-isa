""" ELF simple tests
"""

import unittest

from openpower.test.elf.simple_cases import SimpleCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestELFSimple(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SimpleCases().test_data,
                         fp=True, use_syscall_emu=True)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
