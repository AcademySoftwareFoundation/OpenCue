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
import unittest

import FileSequence
import outline
from outline.modules.shell import Shell
from tests.test_utils import TemporarySessionDirectory

SCRIPTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'scripts')


class LoaderTest(unittest.TestCase):

    def test_script_parse(self):
        """
        Test to ensure a basic outline script parses.
        """
        path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        ol = outline.load_outline(path)

        # check to ensure the loader returns the correct type.
        self.assertTrue(isinstance(ol, outline.Outline))

        # Ensure the path is the same
        self.assertEquals(path, ol.get_path())

        # Ensure the single event has been loaded
        self.assertEquals(1, len(ol.get_layers()))

        # ensure that outline returned from load_outline is
        # the same as current_outline
        self.assertEquals(ol, outline.current_outline())

    def test_serialized_parse(self):
        """
        Test to ensure a serialized outline parses.
        """
        filename = 'yamlized.yaml'
        pathOnDisk = os.path.join(SCRIPTS_DIR, filename)
        pathInYaml = './scripts/' + filename
        ol = outline.load_outline(pathOnDisk)

        # check to ensure the loader returns the correct type.
        self.assertTrue(isinstance(ol, outline.Outline))

        # Ensure the path is the same
        self.assertEquals(pathInYaml, ol.get_path())

        # Ensure the single event has been loaded
        self.assertEquals(1, len(ol.get_layers()))

        # ensure that outline returned from load_outline is
        # the same as current_outline
        self.assertEquals(ol, outline.current_outline())


class OutlineTest(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(SCRIPTS_DIR, 'shell.outline')

    def test_get_set_env(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            ol.set_env("ENV_1", "a")
            ol.set_env("ENV_2", "b", True)

            self.assertEquals(ol.get_env("ENV_1"), "a")
            self.assertFalse(ol.get_env()["ENV_1"][1])
            self.assertEquals(ol.get_env("ENV_2"), "b")
            self.assertTrue(ol.get_env()["ENV_2"][1])

    def test_add_get_remove_layer(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)
            ol.add_layer(Shell("shell_command", cmd=["/bin/ls"]))

            self.assertEquals(2, len(ol.get_layers()))
            self.assertTrue(isinstance(ol.get_layer("shell_command"), Shell))

            ol.remove_layer(ol.get_layer("shell_command"))

            self.assertEquals(1, len(ol.get_layers()))

    def test_get_layers(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            self.assertEquals(1, len(ol.get_layers()))
            self.assertTrue(isinstance(ol.get_layers(), list))

    def test_is_layer(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            self.assertTrue(ol.is_layer("cmd"))
            self.assertFalse(ol.is_layer("not_a_layer"))

    def test_get_set_path(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)
            path = '/tmp/foo.outline'

            ol.set_path(path)

            self.assertEquals(path, ol.get_path())

    def test_get_set_name(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)
            name = 'foo_name'

            ol.set_name(name)

            self.assertEquals(name, ol.get_name())

    def test_get_session(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            # The session is only available once the outline has been "setup"
            # Attempting to obtain the session before setup raises an
            # OutlineException because the session directory does not exist.
            self.assertRaises(outline.OutlineException, ol.get_session)

            ol.setup()

            self.assertTrue(isinstance(ol.get_session(), outline.Session))

    def test_get_set_frame_range(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            # Set frame range from string
            ol.set_frame_range('1-10')
            self.assertEquals('1-10', ol.get_frame_range())

            # Set frame range from sequence
            ol.set_frame_range([1, 2, 3, 4, 5])
            self.assertEquals('1,2,3,4,5', ol.get_frame_range())

            # Set frame range from FrameSet
            ol.set_frame_range(FileSequence.FrameSet('5-10'))
            self.assertEquals('5,6,7,8,9,10', ol.get_frame_range())

    def test_get_set_arg(self):
        with TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            # Test normal get/set function
            ol.set_arg('foo', 1)
            self.assertEquals(1, ol.get_arg('foo'))

            # Test the default argument
            self.assertEquals('apple', ol.get_arg('foobar', 'apple'))

            # Test to ensure the set value is returned if a default
            # is passed.
            ol.set_arg('swoob', 8008)
            self.assertEquals(8008, ol.get_arg('swoob', 2112))


if __name__ == '__main__':
    unittest.main()

