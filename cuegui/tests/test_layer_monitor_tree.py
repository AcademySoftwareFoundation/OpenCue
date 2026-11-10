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


"""Tests for cuegui.LayerMonitorTree."""


import unittest

import mock

import opencue_proto.job_pb2
import opencue.wrappers.layer

import cuegui.LayerMonitorTree


def _layer(min_memory, booked_memory, auto_memory):
    return opencue.wrappers.layer.Layer(
        opencue_proto.job_pb2.Layer(
            min_memory=min_memory, booked_memory=booked_memory,
            memory_optimizer_enabled=auto_memory))


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class LayerMemoryColumnTests(unittest.TestCase):

    def test__auto_memory_shows_the_booked_size(self):
        layer = _layer(16777216, 6291456, True)
        self.assertEqual('6.0G (auto)', cuegui.LayerMonitorTree.layerMemoryText(layer))
        self.assertEqual(6291456, cuegui.LayerMonitorTree.layerMemoryKb(layer))

    def test__unsized_layer_shows_the_ask(self):
        layer = _layer(16777216, 0, True)
        self.assertEqual('16.0G', cuegui.LayerMonitorTree.layerMemoryText(layer))

    def test__pinned_layer_shows_the_ask(self):
        layer = _layer(8388608, 8388608, False)
        self.assertEqual('8.0G', cuegui.LayerMonitorTree.layerMemoryText(layer))
        self.assertEqual(8388608, cuegui.LayerMonitorTree.layerMemoryKb(layer))


if __name__ == '__main__':
    unittest.main()
