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


"""Tests for cuegui.GarbageCollector."""


import gc
import unittest

import mock
import qtpy.QtCore

import cuegui.GarbageCollector

from . import test_utils


class GarbageCollectorTests(unittest.TestCase):

    def setUp(self):
        test_utils.createApplication()
        if gc.isenabled():
            self.addCleanup(gc.enable)
        self.parent = qtpy.QtCore.QObject()
        self.collector = cuegui.GarbageCollector.GarbageCollector(self.parent)
        self.collector.timer.stop()

    def test_disablesAutomaticCollection(self):
        self.assertFalse(gc.isenabled())

    @mock.patch('gc.collect')
    def test_collectsFullHeapEveryFullCollectionTicks(self, collect_mock):
        ticks = cuegui.GarbageCollector.GarbageCollector.FULL_COLLECTION_TICKS

        for _ in range(2 * ticks):
            self.collector.check()

        young = mock.call(1)
        full = mock.call()
        self.assertEqual(
            ([young] * (ticks - 1) + [full]) * 2, collect_mock.call_args_list)


if __name__ == '__main__':
    unittest.main()
