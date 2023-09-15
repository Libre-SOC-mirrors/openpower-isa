# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2023 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

""" modular exponentiation (`pow(x, y, z)`) tests

related bugs:

 * https://bugs.libre-soc.org/show_bug.cgi?id=1044
"""

import unittest

from openpower.test.bigint.powmod import PowModCases
from openpower.test.runner import TestRunnerBase

# writing the test_caller invocation this way makes it work with pytest


class TestPowMod(TestRunnerBase):
    def __init__(self, test):
        assert test == 'test'
        super().__init__(PowModCases().test_data)

    def test(self):
        # dummy function to make unittest try to test this class
        pass


if __name__ == "__main__":
    unittest.main()
