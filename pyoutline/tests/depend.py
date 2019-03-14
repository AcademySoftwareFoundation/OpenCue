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

import outline
from outline.depend import DependType
from outline.modules.shell import Shell
from outline.backend import cue


class DependTest(unittest.TestCase):

    def testShell(self):
        """Test a simple shell command."""
        layer1Name = 'bah1'
        layer2Name = 'bah2'
        layer1 = Shell(layer1Name, command=["/bin/ls"])
        layer2 = Shell(layer2Name, command=["/bin/ls"])

        ol = outline.Outline(name="depend_test_v1")
        ol.add_layer(layer1)
        ol.add_layer(layer2)
        ol.get_layer(layer1Name).depend_all(layer2Name)

        depends = ol.get_layer(layer1Name).get_depends()
        self.assertEqual(1, len(depends))
        self.assertEqual(DependType.LayerOnLayer, depends[0].get_type())
        self.assertEqual(layer2, depends[0].get_depend_on_layer())

    def testShortHandDepend(self):
        ol = outline.Outline(name="depend_test_v2")
        ol.add_layer(Shell("bah1", command=["/bin/ls"]))
        ol.add_layer(Shell("bah2", command=["/bin/ls"],
                           require=["bah1:all"]))
            
        job = outline.cuerun.launch(ol, range="1", pause=True)

        self.assertEquals(1, job.stats.dependFrames)
        cue.test(job)

    def testAnyFrameDepend(self):

        ol = outline.Outline(name="depend_test_any_frame")
        ol.add_layer(Shell("bah1", command=["/bin/ls"], range="1-2"))
        ol.add_layer(Shell("bah2", command=["/bin/ls"],
                           require=["bah1:any"], range="1-1"))

        job = outline.cuerun.launch(ol, pause=True)

        self.assertEquals(1, job.stats.dependFrames)
        cue.test(job)

if __name__ == '__main__':
    unittest.main()

