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
Tests for the outline.session module.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import unittest

import outline


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), 'scripts')


class SessionTest(unittest.TestCase):

    def setUp(self):
        self.script_path = os.path.join(SCRIPTS_DIR, 'shell.outline')
        self.ol = outline.load_outline(self.script_path)
        self.ol.set_frame_range("1-10")
        self.ol.setup()
        self.session = self.ol.get_session()

    def test_put_file(self):
        """Testing get/put file into outline."""

        # Put file into session proper.
        path = self.session.put_file(self.script_path)
        self.assertEqual(path, self.session.get_file('shell.outline'))

    def test_put_file_rename(self):
        """Testing get/put file into outline."""

        # Put file into session proper.
        path = self.session.put_file(self.script_path, rename="outline")
        self.assertEqual(path, self.session.get_file("outline"))

    def test_put_file_to_layer(self):
        """Testing get/put file into layer."""

        # Put file into layer
        layer = self.ol.get_layer("cmd")
        path = layer.put_file(self.script_path)
        self.assertEqual(path, layer.get_file("shell.outline"))

    def test_get_new_file_from_layer(self):
        """Tests the new option for the get_file method. """

        # Put file into layer
        layer = self.ol.get_layer("cmd")

        # Getting a file that doesn't exist should raise SessionException
        # Unless the new flag is passed in.
        self.assertRaises(outline.SessionException, layer.get_file, "foo.bar")

        path = layer.get_file("foo.bar", new=True)
        self.assertEqual("%s/foo.bar" % layer.get_path(), path)

        # If the file already exists, new should throw an exception
        layer.put_file(self.script_path)
        self.assertRaises(
            outline.SessionException, layer.get_file, "shell.outline", new=True)

    def test_get_unchecked_file(self):
        """Tests the new option for the get_file method. """
        self.ol.get_layer("cmd")

    def test_put_data(self):
        """Test get/set data"""

        # Serialize an array of ints into the session and then retrieve it.
        value = [100, 200, 300, 400, 500]
        self.session.put_data("foo", value)
        self.assertEqual(value, self.session.get_data("foo"))

    def test_put_data_to_layer(self):
        """Test get/set layer data."""

        layer = self.ol.get_layer("cmd")
        value = [100, 200, 300, 400, 500]
        layer.put_data("foo", value)
        self.assertEqual(value, layer.get_data("foo"))


if __name__ == '__main__':
    unittest.main()
