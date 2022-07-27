""" Decoder tests

related bugs:

 *
"""

import unittest
import sys

# These tests utilize the run_hdl=False parameter to compare
# simulator with expected states
from soc.simple.test.test_runner import TestRunner
from openpower.test.alu.fmvis_cases import FMVISTestCase


if __name__ == "__main__":

    # allow list of testing to be selected by command-line
    testing = sys.argv[1:]
    sys.argv = sys.argv[:1]

    if not testing:
        testing = ['fmvis', 'fishmv']

    unittest.main(exit=False)
    suite = unittest.TestSuite()

    # dictionary  of data for tests
    tests = {'fmvis': FMVISTestCase().test_data}

    # walk through all tests, those requested get added
    for tname, data in tests.items():
        if tname in testing:
            suite.addTest(TestRunner(data, run_hdl=False))

    runner = unittest.TextTestRunner()
    runner.run(suite)
