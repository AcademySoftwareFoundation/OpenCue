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



import sys
import unittest
import logging

sys.path.insert(0,"../src")

import outline
from outline.modules.shell import Shell

class LoaderTest(unittest.TestCase):

    def test_script_parse(self):
        """
        Test to ensure a basic outline script parses.
        """
        path = "scripts/shell.outline"
        ol = outline.load_outline(path)

        # check to ensure the loader returns the correct type.
        self.assertTrue(isinstance(ol,outline.Outline))

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
        ## Yaml likes to have the full path or else it refuses to parse.
        path = "./scripts/yamlized.yaml"
        ol = outline.load_outline(path)

        # check to ensure the loader returns the correct type.
        self.assertTrue(isinstance(ol,outline.Outline))

        # Ensure the path is the same
        self.assertEquals(path, ol.get_path())

        # Ensure the single event has been loaded
        self.assertEquals(1, len(ol.get_layers()))

        # ensure that outline returned from load_outline is
        # the same as current_outline
        self.assertEquals(ol, outline.current_outline())

class OutlineTest(unittest.TestCase):

    def setUp(self):
        self.path = "scripts/shell.outline"
        self.ol = outline.load_outline(self.path)

    def tearDown(self):
        """Remove the session directory that  gets created if it exists."""
        try:
            shutil.rmtree(self.ol.get_session().get_path())
        except:
            pass

    def test_get_set_env(self):

        self.ol.set_env("ENV_1", "a")
        self.assertEquals(self.ol.get_env("ENV_1"), "a")
        self.assertFalse(self.ol.get_env()["ENV_1"][1])

        self.ol.set_env("ENV_2", "b", True)
        self.assertEquals(self.ol.get_env("ENV_2"), "b")
        self.assertTrue(self.ol.get_env()["ENV_2"][1])

    def test_add_get_remove_layer(self):

        self.ol.add_layer(Shell("shell_command", cmd=["/bin/ls"]))
        self.assertEquals(2, len(self.ol.get_layers()))
        self.assertTrue(isinstance(self.ol.get_layer("shell_command"), Shell))
        self.ol.remove_layer(self.ol.get_layer("shell_command"))
        self.assertEquals(1, len(self.ol.get_layers()))

    def test_get_layers(self):
        self.assertEquals(1, len(self.ol.get_layers()))
        self.assertTrue(isinstance(self.ol.get_layers(),list))

    def test_is_layer(self):
        self.assertTrue(self.ol.is_layer("cmd"))
        self.assertFalse(self.ol.is_layer("not_a_layer"))

    def test_get_set_path(self):
        path = "/tmp/foo.outline"
        self.ol.set_path(path)
        self.assertEquals(path, self.ol.get_path())

    def test_get_set_name(self):
        name = "foo_name"
        self.ol.set_name(name)
        self.assertEquals(name, self.ol.get_name())

    def test_get_session(self):

        # The session is only available once the outline has been "setup"
        # Attempting to obtain the session before setup raises an
        # OutlineException because the session directory does not exist.
        self.assertRaises(outline.OutlineException, self.ol.get_session)
        self.ol.setup()
        self.assertTrue(isinstance(self.ol.get_session(), outline.Session))

    def test_get_set_frame_range(self):

        # Set frame range from string
        self.ol.set_frame_range("1-10")
        self.assertEquals("1-10", self.ol.get_frame_range())

        # Set frame range from sequence
        self.ol.set_frame_range([1,2,3,4,5])
        self.assertEquals("1,2,3,4,5", self.ol.get_frame_range())

        # Set frame range from FrameSet
        from outline.manifest import FileSequence
        self.ol.set_frame_range(FileSequence.FrameSet("5-10"))
        self.assertEquals("5-10", self.ol.get_frame_range());

    def test_get_set_arg(self):

        # Test normal get/set function
        self.ol.set_arg("foo", 1)
        self.assertEquals(1, self.ol.get_arg("foo"))

        # Test the default argument
        self.assertEquals("apple", self.ol.get_arg("foobar","apple"))

        # Test to ensure the set value is returned if a default
        # is passed.
        self.ol.set_arg("swoob", 8008)
        self.assertEquals(8008, self.ol.get_arg("swoob",2112))




if __name__ == '__main__':
    unittest.main()

