#  Copyright (c) OpenCue Project Authors
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


"""Tests for cuegui.images."""


import unittest

# pylint: disable=unused-import
import cuegui.images.icons_rcc
import cuegui.images.bluecurve.icons_rcc
import cuegui.images.crystal.icons_rcc


class ImagesTests(unittest.TestCase):

    def test_iconsImportShouldSucceed(self):
        # Nothing to test here really -- we're just verifying the icons files import without
        # any syntax errors. This test is mostly intended to fix a SonarCloud bug which
        # sometimes shows these files as uncovered.
        pass


if __name__ == '__main__':
    unittest.main()
