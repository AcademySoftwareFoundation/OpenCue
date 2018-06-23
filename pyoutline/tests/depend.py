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
import outline

from outline.modules.shell import Shell, ShellSequence
from outline.depend import DependType
from outline.backend import cue3

logging.basicConfig(level=logging.DEBUG)

class DependTest(unittest.TestCase):

    def testShell(self):
        """Test a simple shell command."""

        ol = outline.Outline(name="depend_test_v1")
        ol.add_layer(Shell("bah1", command=["/bin/ls"]))
        ol.add_layer(Shell("bah2", command=["/bin/ls"]))
        ol.get_layer("bah1").depend_all("bah2")

        job = outline.cuerun.launch(ol, range="1", pause=True)

        self.assertEquals(1, job.stats.dependFrames)
        cue3.test(job)

    def testShortHandDepend(self):

        ol = outline.Outline(name="depend_test_v2")
        ol.add_layer(Shell("bah1", command=["/bin/ls"]))
        ol.add_layer(Shell("bah2", command=["/bin/ls"],
                           require=["bah1:all"]))
            
        job = outline.cuerun.launch(ol, range="1", pause=True)

        self.assertEquals(1, job.stats.dependFrames)
        cue3.test(job)

    def testAnyFrameDepend(self):

        ol = outline.Outline(name="depend_test_any_frame")
        ol.add_layer(Shell("bah1", command=["/bin/ls"], range="1-2"))
        ol.add_layer(Shell("bah2", command=["/bin/ls"],
                           require=["bah1:any"], range="1-1"))

        job = outline.cuerun.launch(ol, pause=True)

        self.assertEquals(1, job.stats.dependFrames)
        cue3.test(job)

if __name__ == '__main__':
    unittest.main()

