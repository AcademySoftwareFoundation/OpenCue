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
Tests for the outline.cfg spec_version
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import unittest

from xml.etree import ElementTree as Et

import outline
import outline.modules.shell


class SpecVersiondTest(unittest.TestCase):
    def _makeSpec(self):
        # Ensure to reset current
        outline.Outline.current = None
        ol = outline.Outline(name="spec_version_test")
        layer = outline.modules.shell.Shell("test_layer", command=["/bin/ls"])
        layer.set_arg("timeout", 420)
        layer.set_arg("timeout_llu", 4200)
        ol.add_layer(layer)
        l = outline.cuerun.OutlineLauncher(ol)
        l.set_flag("priority", 42)
        return Et.fromstring(l.serialize())

    def test_1_9(self):
        outline.config.set("outline", "spec_version", "1.9")
        root = self._makeSpec()
        self.assertIsNone(root.find("job/layers/layer/timeout"))
        self.assertIsNone(root.find("job/layers/layer/timeout_llu"))
        self.assertIsNone(root.find("job/priority"))

    def test_1_10(self):
        outline.config.set("outline", "spec_version", "1.10")
        root = self._makeSpec()
        self.assertEqual(root.find("job/layers/layer/timeout").text, "420")
        self.assertEqual(root.find("job/layers/layer/timeout_llu").text, "4200")
        self.assertIsNone(root.find("job/priority"))

    def test_1_11(self):
        outline.config.set("outline", "spec_version", "1.11")
        root = self._makeSpec()
        self.assertEqual(root.find("job/layers/layer/timeout").text, "420")
        self.assertEqual(root.find("job/layers/layer/timeout_llu").text, "4200")
        self.assertEqual(root.find("job/priority").text, "42")

    def _makeGpuSpec(self):
        ol = outline.Outline(name="spec_version_test")
        layer = outline.modules.shell.Shell("test_layer", command=["/bin/ls"])
        layer.set_arg("gpus", 4)
        layer.set_arg("gpu_memory", 8 * 1024 * 1024)
        ol.add_layer(layer)
        l = outline.cuerun.OutlineLauncher(ol)
        return Et.fromstring(l.serialize())

    def test_gpu_1_11(self):
        outline.config.set("outline", "spec_version", "1.11")
        root = self._makeGpuSpec()
        self.assertIsNone(root.find("job/layers/layer/gpus"))
        self.assertIsNone(root.find("job/layers/layer/gpus_memory"))

    def test_gpu_1_12(self):
        outline.config.set("outline", "spec_version", "1.12")
        root = self._makeGpuSpec()
        self.assertEqual(root.find("job/layers/layer/gpus").text, "4")
        self.assertEqual(root.find("job/layers/layer/gpu_memory").text, "8388608")

    def _makeMaxCoresGpusSpec(self):
        ol = outline.Outline(name="override_max_cores_and_gpus", maxcores=8, maxgpus=7)
        layer = outline.modules.shell.Shell("test_layer", command=["/bin/ls"])
        ol.add_layer(layer)
        l = outline.cuerun.OutlineLauncher(ol)
        return Et.fromstring(l.serialize())

    def test_max_cores_gpus_1_12(self):
        outline.config.set("outline", "spec_version", "1.12")
        root = self._makeMaxCoresGpusSpec()
        self.assertIsNone(root.find("job/maxcores"))
        self.assertIsNone(root.find("job/maxgpus"))

    def test_max_cores_gpus_1_13(self):
        outline.config.set("outline", "spec_version", "1.13")
        root = self._makeMaxCoresGpusSpec()
        self.assertEqual(root.find("job/maxcores").text, "8")
        self.assertEqual(root.find("job/maxgpus").text, "7")
