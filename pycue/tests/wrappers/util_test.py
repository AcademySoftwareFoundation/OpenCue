#!/usr/bin/env python

#  Copyright Contributors to the OpenCue Project
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Tests for `opencue.wrappers.util`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import time
import unittest

import opencue.wrappers.util


TEST_SECONDS_A = 1557942905
TEST_SECONDS_B = 2000
TEST_SECONDS_C = 0
MEM_500_M = 1024 * 512
MEM_6_G = 1024 * 1024 * 6
MEM_6000_G = 1024 * 1024 * 1024 * 6


class UtilTests(unittest.TestCase):

    def setUp(self):
        os.environ['TZ'] = 'Europe/London'
        time.tzset()

    def testFormatTime(self):
        expected = '05/15 18:55'
        timeString = opencue.wrappers.util.format_time(TEST_SECONDS_A)
        self.assertEqual(timeString, expected)

        expected = '01/01 01:33'
        timeString = opencue.wrappers.util.format_time(TEST_SECONDS_B)
        self.assertEqual(timeString, expected)

        expected = '--/-- --:--'
        timeString = opencue.wrappers.util.format_time(TEST_SECONDS_C)
        self.assertEqual(timeString, expected)


    def testDateToMMDDHHMM(self):
        expected = '05/15 18:55'
        timeString = opencue.wrappers.util.dateToMMDDHHMM(TEST_SECONDS_A)
        self.assertEqual(timeString, expected)

        expected = '01/01 01:33'
        timeString = opencue.wrappers.util.dateToMMDDHHMM(TEST_SECONDS_B)
        self.assertEqual(timeString, expected)

        expected = '--/-- --:--'
        timeString = opencue.wrappers.util.dateToMMDDHHMM(TEST_SECONDS_C)
        self.assertEqual(timeString, expected)

    def testSecondsToHHMMSS(self):
        expected = '432761:55:05'
        timeString = opencue.wrappers.util.secondsToHHMMSS(TEST_SECONDS_A)
        self.assertEqual(timeString, expected)

        expected = '00:33:20'
        timeString = opencue.wrappers.util.secondsToHHMMSS(TEST_SECONDS_B)
        self.assertEqual(timeString, expected)

        expected = '00:00:00'
        timeString = opencue.wrappers.util.secondsToHHMMSS(TEST_SECONDS_C)
        self.assertEqual(timeString, expected)

    def testSecondsToHMMSS(self):
        expected = '432761:55:05'
        timeString = opencue.wrappers.util.secondsToHMMSS(TEST_SECONDS_A)
        self.assertEqual(timeString, expected)

        expected = '0:33:20'
        timeString = opencue.wrappers.util.secondsToHMMSS(TEST_SECONDS_B)
        self.assertEqual(timeString, expected)

        expected = '0:00:00'
        timeString = opencue.wrappers.util.secondsToHMMSS(TEST_SECONDS_C)
        self.assertEqual(timeString, expected)

    def testSecondsToHHHMM(self):
        expected = '432761:55'
        timeString = opencue.wrappers.util.secondsToHHHMM(TEST_SECONDS_A)
        self.assertEqual(timeString, expected)

        expected = '000:33'
        timeString = opencue.wrappers.util.secondsToHHHMM(TEST_SECONDS_B)
        self.assertEqual(timeString, expected)

        expected = '000:00'
        timeString = opencue.wrappers.util.secondsToHHHMM(TEST_SECONDS_C)
        self.assertEqual(timeString, expected)

    def testSecondsDiffToHMMSS(self):

        expected = '432761:21:45'
        timeString = opencue.wrappers.util.secondsDiffToHMMSS(TEST_SECONDS_B, TEST_SECONDS_A)
        self.assertEqual(timeString, expected)

        expected = '432761:21:45'
        timeString = opencue.wrappers.util.secondsDiffToHMMSS(TEST_SECONDS_A, TEST_SECONDS_B)
        self.assertEqual(timeString, expected)

    def testConvertMem(self):
        expected = '6291456K'
        memString = opencue.wrappers.util.convert_mem(MEM_6_G, 'K')
        self.assertEqual(memString, expected)

        expected = '6291456M'
        memString = opencue.wrappers.util.convert_mem(MEM_6000_G, 'M')
        self.assertEqual(memString, expected)

        expected = '6.0G'
        memString = opencue.wrappers.util.convert_mem(MEM_6_G, 'G')
        self.assertEqual(memString, expected)

        expected = '0.5G'
        memString = opencue.wrappers.util.convert_mem(MEM_500_M, 'G')
        self.assertEqual(memString, expected)


if __name__ == '__main__':
    unittest.main()
