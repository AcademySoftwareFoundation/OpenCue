#!/usr/local/bin/python

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

import Manifest

from api_test import APITestCase
from job_test import JobTestCase
from layer_test import LayerTestCase
from frame_test import FrameTestCase
from framelog_test import FrameLogTestCase
from host_test import HostTestCase
from depend_test import DependTestCase
from show_test import ShowTestCase

TESTCASES = [APITestCase, JobTestCase, LayerTestCase, FrameTestCase, FrameLogTestCase, HostTestCase, DependTestCase, ShowTestCase]

if __name__ == '__main__':
    prefix = 'test'

    suite = unittest.TestSuite([unittest.makeSuite(testCase, prefix) for testCase in TESTCASES])
    runner = unittest.TextTestRunner()
    runner.run(suite)

