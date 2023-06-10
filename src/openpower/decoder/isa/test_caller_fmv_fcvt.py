""" fmv/fcvt tests
"""

import unittest
from functools import lru_cache
import os
from openpower.test.fmv_fcvt.fmv_fcvt import (FMvFCvtCases,
                                              SVP64FMvFCvtCases)
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


@lru_cache()
def make_cases():
    # cache globally, so we only have to create test_data once per process
    return FMvFCvtCases().test_data


class TestFMvFCvtBase(TestRunnerBase):
    __test__ = False

    # split up test cases into SPLIT_COUNT tests, so we get some parallelism
    SPLIT_COUNT = 16
    SPLIT_INDEX = -1

    def __init__(self, test):
        assert test == 'test', f"test={test!r}"
        self.__old_silence_log = os.environ.get("SILENCELOG")
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
        super().__init__(cases[start:end], fp=True)

    def setUp(self):
        super().setUp()
        if self.__old_silence_log is None:
            os.environ["SILENCELOG"] = "!*,default"

    def tearDown(self):
        super().tearDown()
        if self.__old_silence_log is None:
            del os.environ["SILENCELOG"]

    @classmethod
    def make_split_classes(cls):
        for i in range(cls.SPLIT_COUNT):
            exec(f"""
class TestFMvFCvt{i}(TestFMvFCvtBase):
    __test__ = True
    SPLIT_INDEX = {i}

    def test(self):
        # dummy function to make unittest try to test this class
        pass
            """, globals())


TestFMvFCvtBase.make_split_classes()


class TestSVP64FMvFCvtCases(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(SVP64FMvFCvtCases().test_data, fp=True)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
