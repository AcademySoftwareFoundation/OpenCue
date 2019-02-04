#!/usr/bin/env python

#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


import unittest

from opencue.tests.api_test import FrameTests
from opencue.tests.api_test import GroupTests
from opencue.tests.api_test import HostTests
from opencue.tests.api_test import JobTests
from opencue.tests.api_test import LayerTests
from opencue.tests.api_test import ShowTests
from opencue.tests.api_test import SubscriptionTests
from search_test import JobSearchTests
from util_tests import IdTests
from util_tests import ProxyTests

TESTCASES = [
    ShowTests,
    GroupTests,
    JobTests,
    LayerTests,
    FrameTests,
    SubscriptionTests,
    HostTests,
    JobSearchTests,
    ProxyTests,
    IdTests
]

if __name__ == '__main__':
    prefix = 'test'
    suite = unittest.TestSuite([unittest.makeSuite(testCase, prefix) for testCase in TESTCASES])
    runner = unittest.TextTestRunner()
    runner.run(suite)
