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

"""
Tests for the outline.depend module.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import unittest

import outline
import outline.depend
import outline.modules.shell
from . import test_utils


class DependTest(unittest.TestCase):

    def setUp(self):
        outline.Outline.current = None

    def testShell(self):
        """Test a simple shell command."""
        layer1Name = 'bah1'
        layer2Name = 'bah2'
        layer1 = outline.modules.shell.Shell(layer1Name, command=['/bin/ls'])
        layer2 = outline.modules.shell.Shell(layer2Name, command=['/bin/ls'])

        ol = outline.Outline(name='depend_test_v1')
        ol.add_layer(layer1)
        ol.add_layer(layer2)
        ol.get_layer(layer1Name).depend_all(layer2Name)

        depends = ol.get_layer(layer1Name).get_depends()
        self.assertEqual(1, len(depends))
        self.assertEqual(outline.depend.DependType.LayerOnLayer, depends[0].get_type())
        self.assertEqual(layer2, depends[0].get_depend_on_layer())

    def testShortHandDepend(self):
        with test_utils.TemporarySessionDirectory():
            layer1Name = 'bah1'
            layer2Name = 'bah2'
            layer1 = outline.modules.shell.Shell(layer1Name, command=['/bin/ls'])
            layer2 = outline.modules.shell.Shell(
                layer2Name, command=['/bin/ls'], require=['%s:all' % layer1Name])

            ol = outline.Outline(name='depend_test_v2')
            ol.add_layer(layer1)
            ol.add_layer(layer2)
            ol.setup()

            depends = ol.get_layer(layer2Name).get_depends()
            self.assertEqual(1, len(depends))
            self.assertEqual(outline.depend.DependType.LayerOnLayer, depends[0].get_type())
            self.assertEqual(layer1, depends[0].get_depend_on_layer())

    def testAnyFrameDepend(self):
        with test_utils.TemporarySessionDirectory():
            layer1Name = 'bah1'
            layer2Name = 'bah2'
            layer1 = outline.modules.shell.Shell(layer1Name, command=['/bin/ls'], range='1-2')
            layer2 = outline.modules.shell.Shell(layer2Name, command=['/bin/ls'], range='1-1',
                           require=['%s:any' % layer1Name])

            ol = outline.Outline(name='depend_test_any_frame')
            ol.add_layer(layer1)
            ol.add_layer(layer2)
            ol.setup()

            depends = ol.get_layer(layer2Name).get_depends()
            self.assertEqual(1, len(depends))
            self.assertEqual(outline.depend.DependType.FrameByFrame, depends[0].get_type())
            self.assertEqual(layer1, depends[0].get_depend_on_layer())


if __name__ == '__main__':
    unittest.main()
