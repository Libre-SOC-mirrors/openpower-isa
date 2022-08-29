# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from openpower.test.algorithms.svp64_utf_8_validation import \
    SVP64UTF8ValidationTestCase
from openpower.test.runner import TestRunnerBase
from functools import lru_cache

# writing the test_caller invocation this way makes it work with pytest


@lru_cache
def make_cases():
    # cache globally, so we only have to create test_data once per process
    return SVP64UTF8ValidationTestCase().test_data


class TestSVP64UTF8ValidationBase(TestRunnerBase):
    __test__ = False

    # split up test cases into SPLIT_COUNT tests, so we get some parallelism
    SPLIT_COUNT = 64
    SPLIT_INDEX = -1

    def __init__(self, test):
        assert test == 'test', f"test={test!r}"
        cases = make_cases()
        assert self.SPLIT_INDEX != -1, "must be overridden"
        # split cases evenly over tests
        start = (len(cases) * self.SPLIT_INDEX) // self.SPLIT_COUNT
        end = (len(cases) * (self.SPLIT_INDEX + 1)) // self.SPLIT_COUNT
        # if we have less cases than tests, move them all to the beginning,
        # making finding failures faster
        if len(cases) < self.SPLIT_COUNT:
            start = 0
            end = 0
            if self.SPLIT_INDEX < len(cases):
                start = self.SPLIT_INDEX
                end = start + 1
        # can't do raise SkipTest if `start == end`, it makes unittest break
        super().__init__(cases[start:end])

    @classmethod
    def make_split_classes(cls):
        for i in range(cls.SPLIT_COUNT):
            exec(f"""
class TestSVP64UTF8Validation{i}(TestSVP64UTF8ValidationBase):
    __test__ = True
    SPLIT_INDEX = {i}

    def test(self):
        # dummy function to make unittest try to test this class
        pass
            """, globals())


TestSVP64UTF8ValidationBase.make_split_classes()

if __name__ == "__main__":
    unittest.main()
