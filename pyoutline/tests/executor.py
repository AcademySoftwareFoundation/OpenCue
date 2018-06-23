#!/bin/env python2.5

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


import os
import sys
import logging
import unittest
import time

sys.path.insert(0,"../src")
from outline import TaskExecutor

logging.basicConfig(level=logging.DEBUG)

class TaskExecutorTest(unittest.TestCase):

    def test_simple_threading(self):
        e = TaskExecutor(5)
        e.execute(self.print_, "hello thread 1")
        e.execute(self.print_, "hello thread 2")
        e.execute(self.print_, "hello thread 3")
        e.execute(self.print_, "hello thread 4")
        e.execute(self.print_, "hello thread 5")
        e.wait()

    def print_(self, msg):
        print "Test Message: %s" % msg
        time.sleep(1)

if __name__ == '__main__':
    unittest.main()

