""" Decoder tests

related bugs:

 *
"""

import unittest
import sys

# These tests utilize the run_hdl=False parameter to compare
# simulator with expected states
from openpower.test.runner import TestRunnerBase
from openpower.test.shift_rot.shift_rot_cases2 import ShiftRotTestCase2


if __name__ == "__main__":

    # allow list of testing to be selected by command-line
    testing = sys.argv[1:]
    sys.argv = sys.argv[:1]

    if not testing:
        testing = ['shiftrot2']

    unittest.main(exit=False)
    suite = unittest.TestSuite()

    # dictionary  of data for tests
    tests = {'shiftrot2': ShiftRotTestCase2().test_data}

    # walk through all tests, those requested get added
    for tname, data in tests.items():
        if tname in testing:
            suite.addTest(TestRunnerBase(data))

    runner = unittest.TextTestRunner()
    runner.run(suite)
