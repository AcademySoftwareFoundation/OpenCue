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


"""Tests for cuegui.TagsWidget."""


import unittest

import cuegui.TagsWidget


class IsValidTagTests(unittest.TestCase):
    """Tests for TagsWidget._is_valid_tag method."""

    def test_alphanumeric_tag(self):
        """Standard alphanumeric tags should be valid."""
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('general'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag123'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('UPPERCASE'))

    def test_tag_with_dashes(self):
        """Tags containing dashes should be valid."""
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('test-layer-tag'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('my-tag'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('a-b-c'))

    def test_tag_with_underscores(self):
        """Tags containing underscores should be valid."""
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('my_tag'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('test_layer_tag'))

    def test_mixed_characters(self):
        """Tags with mixed valid characters should be valid."""
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('MixedCase-123'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag_with-both'))
        self.assertTrue(cuegui.TagsWidget.TagsWidget._is_valid_tag('GPU-v100_render'))

    def test_empty_tag(self):
        """Empty tags should be invalid."""
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag(''))

    def test_tag_with_spaces(self):
        """Tags containing spaces should be invalid."""
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag with space'))
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag(' leading'))
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('trailing '))

    def test_tag_with_special_characters(self):
        """Tags containing special characters should be invalid."""
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag@special'))
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag!'))
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag#hash'))
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag.dot'))
        self.assertFalse(cuegui.TagsWidget.TagsWidget._is_valid_tag('tag/slash'))


if __name__ == '__main__':
    unittest.main()
