# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2023 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

""" modular exponentiation (`pow(x, y, z)`) tests

related bugs:

 * https://bugs.libre-soc.org/show_bug.cgi?id=1044
"""

import unittest
from functools import lru_cache
import os
from openpower.test.bigint.powmod import (
    PowModCases, python_divmod_algorithm, python_powmod_256_algorithm)
from openpower.test.runner import TestRunnerBase


class TestPythonAlgorithms(unittest.TestCase):
    def test_python_divmod_algorithm(self):
        for n, d in PowModCases.divmod_512x256_to_256x256_test_inputs():
            q, r = divmod(n, d)
            with self.subTest(n=f"{n:#_x}", d=f"{d:#_x}",
                              q=f"{q:#_x}", r=f"{r:#_x}"):
                log_regex = n == 2 ** 511 - 1 and d == 2 ** 256 - 1
                out_q, out_r = python_divmod_algorithm(
                    n, d, log_regex=log_regex)
                with self.subTest(out_q=f"{out_q:#_x}", out_r=f"{out_r:#_x}"):
                    self.assertEqual(out_q, q)
                    self.assertEqual(out_r, r)

    def test_python_powmod_algorithm(self):
        for base, exp, mod in PowModCases.powmod_256_test_inputs():
            expected = pow(base, exp, mod)
            with self.subTest(base=f"{base:#_x}", exp=f"{exp:#_x}",
                              mod=f"{mod:#_x}", expected=f"{expected:#_x}"):
                out = python_powmod_256_algorithm(base, exp, mod)
                with self.subTest(out=f"{out:#_x}"):
                    self.assertEqual(expected, out)


# writing the test_caller invocation this way makes it work with pytest


@lru_cache()
def make_cases():
    # cache globally, so we only have to create test_data once per process
    return PowModCases().test_data


class TestPowModBase(TestRunnerBase):
    __test__ = False

    # split up test cases into SPLIT_COUNT tests, so we get some parallelism
    SPLIT_COUNT = 64
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
        super().__init__(cases[start:end])

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
class TestPowMod{i}(TestPowModBase):
    __test__ = True
    SPLIT_INDEX = {i}

    def test(self):
        # dummy function to make unittest try to test this class
        pass
            """, globals())


TestPowModBase.make_split_classes()

if __name__ == "__main__":
    unittest.main()
