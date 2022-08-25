# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from openpower.test.algorithms.svp64_utf_8_validation import \
    SVP64UTF8ValidationTestCase
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestSVP64UTF8Validation(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64UTF8ValidationTestCase().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
