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
Tests for the outline.loader module.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import unittest
from xml.etree import ElementTree as Et

import FileSequence

import outline
import outline.cuerun
import outline.modules.shell
from . import test_utils


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
        self.assertEqual(path, ol.get_path())

        # Ensure the single event has been loaded
        self.assertEqual(1, len(ol.get_layers()))

        # ensure that outline returned from load_outline is
        # the same as current_outline
        self.assertEqual(ol, outline.current_outline())

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
        self.assertEqual(pathInYaml, ol.get_path())

        # Ensure the single event has been loaded
        self.assertEqual(1, len(ol.get_layers()))

        # ensure that outline returned from load_outline is
        # the same as current_outline
        self.assertEqual(ol, outline.current_outline())


class OutlineTest(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(SCRIPTS_DIR, 'shell.outline')

    def test_get_set_env(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            ol.set_env("ENV_1", "a")
            ol.set_env("ENV_2", "b", True)

            self.assertEqual(ol.get_env("ENV_1"), "a")
            self.assertFalse(ol.get_env()["ENV_1"][1])
            self.assertEqual(ol.get_env("ENV_2"), "b")
            self.assertTrue(ol.get_env()["ENV_2"][1])

    def test_add_get_remove_layer(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)
            ol.add_layer(outline.modules.shell.Shell("shell_command", cmd=["/bin/ls"]))

            self.assertEqual(2, len(ol.get_layers()))
            self.assertTrue(isinstance(ol.get_layer("shell_command"), outline.modules.shell.Shell))

            ol.remove_layer(ol.get_layer("shell_command"))

            self.assertEqual(1, len(ol.get_layers()))

    def test_get_layers(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            self.assertEqual(1, len(ol.get_layers()))
            self.assertTrue(isinstance(ol.get_layers(), list))

    def test_is_layer(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            self.assertTrue(ol.is_layer("cmd"))
            self.assertFalse(ol.is_layer("not_a_layer"))

    def test_get_set_path(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)
            path = '/tmp/foo.outline'

            ol.set_path(path)

            self.assertEqual(path, ol.get_path())

    def test_get_set_name(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)
            name = 'foo_name'

            ol.set_name(name)

            self.assertEqual(name, ol.get_name())

    def test_get_session(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            # The session is only available once the outline has been "setup"
            # Attempting to obtain the session before setup raises an
            # OutlineException because the session directory does not exist.
            self.assertRaises(outline.OutlineException, ol.get_session)

            ol.setup()

            self.assertTrue(isinstance(ol.get_session(), outline.Session))

    def test_get_set_frame_range(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            # Set frame range from string
            ol.set_frame_range('1-10')
            self.assertEqual('1-10', ol.get_frame_range())

            # Set frame range from sequence
            ol.set_frame_range([1, 2, 3, 4, 5])
            self.assertEqual('1,2,3,4,5', ol.get_frame_range())

            # Set frame range from FrameSet
            ol.set_frame_range(FileSequence.FrameSet('5-10'))
            self.assertEqual('5,6,7,8,9,10', ol.get_frame_range())

    def test_get_set_arg(self):
        with test_utils.TemporarySessionDirectory():
            ol = outline.load_outline(self.path)

            # Test normal get/set function
            ol.set_arg('foo', 1)
            self.assertEqual(1, ol.get_arg('foo'))

            # Test the default argument
            self.assertEqual('apple', ol.get_arg('foobar', 'apple'))

            # Test to ensure the set value is returned if a default
            # is passed.
            ol.set_arg('swoob', 8008)
            self.assertEqual(8008, ol.get_arg('swoob', 2112))


class LoadOutlineTest(unittest.TestCase):
    """
    Tests to ensure that the opencue spec generator
    is doing its job.
    """
    script = os.path.join(SCRIPTS_DIR, 'shell.outline')

    def test_ol_tag_override_env(self):
        """
        Check that the OL_TAG_OVERRIDE environment variable
        is handled properly.
        """
        ol = outline.load_outline(self.script)
        for layer in ol.get_layers():
            layer.set_arg("tags", ["foo", "man", "chu"])

        try:
            os.environ["OL_TAG_OVERRIDE"] = "general"
            l = outline.cuerun.OutlineLauncher(ol)

            root = Et.fromstring(l.serialize())
            self.assertEqual(os.environ["OL_TAG_OVERRIDE"],
                              root.find("job/layers/layer/tags").text)
        finally:
            del os.environ["OL_TAG_OVERRIDE"]

    def test_tags_as_list(self):
        """Check that tags passed in as a list."""

        ol = outline.load_outline(self.script)
        for layer in ol.get_layers():
            layer.set_arg("tags", ["foo", "man", "chu"])

        l = outline.cuerun.OutlineLauncher(ol)
        root = Et.fromstring(l.serialize())
        self.assertEqual("foo | man | chu",
                          root.find("job/layers/layer/tags").text)

    def test_tags_as_string(self):
        """Check tags passed in as a string."""

        ol = outline.load_outline(self.script)
        for layer in ol.get_layers():
            layer.set_arg("tags", "foo | man | chu")

        l = outline.cuerun.OutlineLauncher(ol)
        root = Et.fromstring(l.serialize())
        self.assertEqual("foo | man | chu",
                          root.find("job/layers/layer/tags").text)

    def test_os_flag(self):
        """
        Check that the os flag is handled properly.
        """
        ol = outline.load_outline(self.script)
        l = outline.cuerun.OutlineLauncher(ol, os="awesome")

        root = Et.fromstring(l.serialize())
        self.assertEqual("awesome",
                          root.find("job/os").text)

    def test_ol_os_env(self):
        """
        Check that the OL_OS environment variable
        is handled properly.
        """
        try:
            os.environ["OL_OS"] = "radical"
            ol = outline.load_outline(self.script)
            l = outline.cuerun.OutlineLauncher(ol)
            root = Et.fromstring(l.serialize())
            self.assertEqual("radical", root.find("job/os").text)
        finally:
            del os.environ["OL_OS"]


if __name__ == '__main__':
    unittest.main()
