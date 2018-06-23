#!/usr/local64/bin/python2.5

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




import sys
import unittest
import logging

# Core tests

from layer import ChunkingTest, LayerTest, CompositeTest
from loader import LoaderTest
from session import SessionTest
from json import JsonTest

# Module tests
from module_shell import ShellModuleTest

tests = [
         ChunkingTest,
         LayerTest,
         CompositeTest,
         LoaderTest,
         SessionTest,
         JsonTest,
         ShellModuleTest,
        ]

def suite():
    suite = unittest.TestSuite()
    suite.addTests([unittest.makeSuite(test, "test") for test in tests])
    return suite

if __name__ == '__main__':

    if len(sys.argv) == 2:
        if sys.argv[1] == "-v":
            logging.basicConfig(level=logging.DEBUG)
    else:
        print "-v activates verbose mode."

    runner = unittest.TextTestRunner()
    runner.run(suite())
