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
import logging
import unittest

logging.basicConfig(level=logging.INFO)

import outline
from outline import cuerun
from outline.modules.shell import Shell, ShellSequence, ShellScript

from outline.backend import cue

import opencue

class ShellModuleTest(unittest.TestCase):

    """Shell Module Tests"""

    def testShell(self):
        """Test a simple shell command."""

        ol = outline.Outline(name="shell_test_v1")
        ol.add_layer(Shell("bah", command=["/bin/ls"]))
        cuerun.launch(ol, range="1", test=True)

    def testFailedShell(self):
        """Test that a failed frame throws an OutlineException in test mode."""

        ol = outline.Outline(name="shell_test_v2", current=True)
        ol.add_layer(Shell("bah", command=["/bin/lssdsdasdsd"]))
        self.assertRaises(outline.OutlineException,
                          cuerun.launch, ol, range="1", test=True)

    def testShellSequence(self):
        """Test a simple sequence of shell commands"""

        commands = ["/bin/ls"] * 10

        ol = outline.Outline(name="shell_sequence_test_v1", current=True)
        ol.add_layer(ShellSequence("bah", commands=commands, cores=10, memory="512m"))
        job = cuerun.launch(ol, pause=True)

        self.assertEquals(10, job.stats.waitingFrames)
        self.assertEquals(10, job.stats.pendingFrames)

        cue.test(job)

        job = opencue.getJob(job)
        self.assertEquals(0, job.stats.waitingFrames)
        self.assertEquals(10, job.stats.succeededFrames)

    def testShellScript(self):
        
        fp = open("test.sh", "w")
        fp.write("#!/bin/sh\n")
        fp.write("echo zoom zoom zoom")
        fp.close()

        ol = outline.Outline(name="shell_script_test_v1", current=True)
        ol.add_layer(ShellScript("script", script="test.sh"))
        cuerun.launch(ol, test=True)

    def testShellToString(self):
        """Test a string shell command."""
        ol = outline.Outline(name="string_test_v1")
        ol.add_layer(Shell("string_test", command="/bin/ls -l ./"))
        cuerun.launch(ol, range="1", test=True)


if __name__ == '__main__':
    unittest.main()

