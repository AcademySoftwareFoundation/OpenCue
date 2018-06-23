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

# Override the base outline config location.

sys.path.insert(0,"../src")
from outline import load_json

logging.basicConfig(level=logging.DEBUG)

class JsonTest(unittest.TestCase):

    def testJson(self):
        """Load in a json stirng"""
        s = str('{"name": "test_job", "range": "1-10", "layers": \
[{"name": "layer_1", "module": "outline.modules.shell.Shell", "command": ["/bin/ls"]}]}')

        ol = load_json(s)
        self.assertEquals("test_job", ol.get_name())
        self.assertEquals("1-10", ol.get_frame_range())

    def testJsonFile(self):
        ""
        ol = load_json(open("json/shell.outline").read())
        ol.setup()
        ol.get_layer("shell_layer").execute("1000")

if __name__ == '__main__':
    unittest.main()

