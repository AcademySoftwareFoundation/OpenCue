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


"""Tests for cuegui.LayerDialog."""


import unittest

import mock

import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtWidgets

import opencue_proto.show_pb2
import opencue_proto.filter_pb2
import opencue_proto.job_pb2
import opencue_proto.limit_pb2
import opencue.wrappers.filter
import opencue.wrappers.layer
import opencue.wrappers.limit
import opencue.wrappers.show

import cuegui.LayerDialog
import cuegui.Style
import cuegui.Utils

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class LayerPropertiesDialogTests(unittest.TestCase):

    @mock.patch('opencue.api.getLimits')
    @mock.patch('opencue.api.getLayer')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, get_stub_mock, get_layer_mock, get_limits_mock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        self.layers = {
            'layer1Id': opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(
                    id='layer1Id', name='layer1Name', range='1-5', tags=['tag1', 'tag2'],
                    min_cores=1, max_cores=3, is_threadable=False,
                    min_memory=2097152, min_gpu_memory=1,
                    chunk_size=1, timeout=30, timeout_llu=1, memory_optimizer_enabled=True,
                    limits=['limit1Name', 'limit2Name'])),
            'layer2Id': opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(
                    id='layer2Id', name='layer2Name', range='2-22', tags=['tag2', 'tag3'],
                    min_cores=2, max_cores=2, is_threadable=True,
                    min_memory=6291456, min_gpu_memory=2,
                    chunk_size=5, timeout=60, timeout_llu=5, memory_optimizer_enabled=False,
                    limits=['limit2Name', 'limit3Name'])),
        }

        get_layer_mock.side_effect = lambda layer_id: self.layers[layer_id]
        get_limits_mock.return_value = [
            opencue.wrappers.limit.Limit(
                opencue_proto.limit_pb2.Limit(id='limit1Id', name='limit1Name')),
            opencue.wrappers.limit.Limit(
                opencue_proto.limit_pb2.Limit(id='limit2Id', name='limit2Name')),
            opencue.wrappers.limit.Limit(
                opencue_proto.limit_pb2.Limit(id='limit3Id', name='limit3Name')),
            opencue.wrappers.limit.Limit(
                opencue_proto.limit_pb2.Limit(id='limit4Id', name='limit4Name')),
        ]

        self.parent_widget = qtpy.QtWidgets.QWidget()
        self.layer_properties_dialog = cuegui.LayerDialog.LayerPropertiesDialog(
            ['layer1Id', 'layer2Id'], parent=self.parent_widget)

    def test__should_display_current_values(self):
        default_config = cuegui.Utils.getResourceConfig()

        self.assertEqual(
            int(self.layer_properties_dialog.mem_min_gb * 1024),
            self.layer_properties_dialog._LayerPropertiesDialog__mem.slider.minimum())
        self.assertEqual(
            default_config['max_memory'] * 1024,
            self.layer_properties_dialog._LayerPropertiesDialog__mem.slider.maximum())
        # Layer with the higher min_memory determines the initial value.
        self.assertEqual(
            6144, self.layer_properties_dialog._LayerPropertiesDialog__mem.slider.value())

        # Is memory optimizer is on for any layer, it shows as checked in the dialog.
        self.assertTrue(self.layer_properties_dialog._LayerPropertiesDialog__mem_opt.isChecked())

        self.assertEqual(
            0,
            self.layer_properties_dialog._LayerPropertiesDialog__core.minimum())
        self.assertEqual(
            default_config['max_cores'],
            self.layer_properties_dialog._LayerPropertiesDialog__core.maximum())
        # Layer with the higher min_cores determines the initial value.
        self.assertEqual(
            2,
            self.layer_properties_dialog._LayerPropertiesDialog__core.value())

        self.assertEqual(
            0,
            self.layer_properties_dialog._LayerPropertiesDialog__max_cores.minimum())
        self.assertEqual(
            default_config['max_cores'],
            self.layer_properties_dialog._LayerPropertiesDialog__max_cores.maximum())
        # Layer with the higher max_cores determines the initial value.
        self.assertEqual(
            3,
            self.layer_properties_dialog._LayerPropertiesDialog__max_cores.value())

        # Is any layer is threadable, it shows as checked in the dialog.
        self.assertTrue(self.layer_properties_dialog._LayerPropertiesDialog__thread.isChecked())

        self.assertEqual(
            int(self.layer_properties_dialog.gpu_mem_min_gb * 1024 * 1024),
            self.layer_properties_dialog._LayerPropertiesDialog__gpu_mem.slider.minimum())
        self.assertEqual(
            int(self.layer_properties_dialog.gpu_mem_max_gb * 1024 * 1024) //
            int(self.layer_properties_dialog.gpu_mem_tick_gb * 1024 * 1024),
            self.layer_properties_dialog._LayerPropertiesDialog__gpu_mem.slider.maximum())

        # Layer with the highest timeout determines the initial value.
        self.assertEqual(60, self.layer_properties_dialog._LayerPropertiesDialog__timeout.value())

        # Layer with the highest LLU timeout determines the initial value.
        self.assertEqual(
            5, self.layer_properties_dialog._LayerPropertiesDialog__timeout_llu.value())

        # Tags list should contain a union of tags in all layers, without duplicating any tags
        # which appear in multiple layers.
        self.assertListEqual(
            ['tag1', 'tag2', 'tag3'],
            sorted(
                self.layer_properties_dialog._LayerPropertiesDialog__tags._tags_widget.get_tags()))

        # Limits list will contain a list of all limits defined by opencue.api.getLimits. The only
        # checked ones should be the union of limits in all layers, without duplicating any limits
        # which appear in multiple layers.
        limits_widget = self.layer_properties_dialog._LayerPropertiesDialog__limits._limits_widget
        self.assertListEqual(
            ['limit1Name', 'limit2Name', 'limit3Name'], sorted(limits_widget.get_selected_limits()))

    def test__should_fail_on_memory_too_high(self):
        self.layer_properties_dialog._LayerPropertiesDialog__mem.slider.setValue(
            self.layer_properties_dialog.mem_max_mb * 2)
        self.assertFalse(self.layer_properties_dialog.verify())

    def test__should_fail_on_memory_too_low(self):
        self.layer_properties_dialog._LayerPropertiesDialog__mem.slider.setValue(
            self.layer_properties_dialog.mem_min_mb / 3)
        self.assertFalse(self.layer_properties_dialog.verify())

    def test__should_fail_on_gpu_too_high(self):
        self.layer_properties_dialog._LayerPropertiesDialog__gpu_mem.slider.setValue(
            self.layer_properties_dialog.gpu_mem_max_kb * 2)
        self.assertFalse(self.layer_properties_dialog.verify())

    def test__should_fail_on_gpu_too_low(self):
        self.layer_properties_dialog._LayerPropertiesDialog__gpu_mem.slider.setValue(
            self.layer_properties_dialog.gpu_mem_min_kb / 3)
        self.assertFalse(self.layer_properties_dialog.verify())

    def test__should_apply_new_settings(self):
        layer1_mock = mock.Mock()
        layer1_mock.limits.return_value = ['limit1Name', 'limit2Name']
        layer2_mock = mock.Mock()
        layer2_mock.limits.return_value = ['limit2Name', 'limit3Name']
        self.layer_properties_dialog._LayerPropertiesDialog__layers = [layer1_mock, layer2_mock]
        self.layer_properties_dialog._LayerPropertiesDialog__tags._LayerTagsWidget__layers = [
            layer1_mock, layer2_mock]
        self.layer_properties_dialog._LayerPropertiesDialog__limits._LayerLimitsWidget__layers = [
            layer1_mock, layer2_mock]

        new_mem_value = self.layer_properties_dialog.mem_max_mb
        self.layer_properties_dialog._LayerPropertiesDialog__mem.parent().parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__mem.slider.setValue(new_mem_value)

        new_mem_opt_is_enabled = False
        self.layer_properties_dialog._LayerPropertiesDialog__mem_opt.parent().parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__mem_opt.setChecked(
            new_mem_opt_is_enabled)

        new_min_cores = 10
        self.layer_properties_dialog._LayerPropertiesDialog__core.parent().parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__core.setDisabled(False)
        self.layer_properties_dialog._LayerPropertiesDialog__core.setValue(new_min_cores)

        new_max_cores = 12
        self.layer_properties_dialog._LayerPropertiesDialog__max_cores.parent().parent().enable(
            True)
        self.layer_properties_dialog._LayerPropertiesDialog__max_cores.setValue(new_max_cores)

        new_is_threadable = False
        self.layer_properties_dialog._LayerPropertiesDialog__thread.parent().parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__thread.setChecked(new_is_threadable)

        new_min_gpu_memory = 6
        self.layer_properties_dialog._LayerPropertiesDialog__gpu_mem.parent().parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__gpu_mem.slider.setValue(
            new_min_gpu_memory)

        new_timeout = 20
        self.layer_properties_dialog._LayerPropertiesDialog__timeout.parent().parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__timeout.setValue(new_timeout)

        new_timeout_llu = 15
        self.layer_properties_dialog._LayerPropertiesDialog__timeout_llu.parent().parent().enable(
            True)
        self.layer_properties_dialog._LayerPropertiesDialog__timeout_llu.setValue(new_timeout_llu)

        new_tags = ['newTag1', 'newTag2']
        self.layer_properties_dialog._LayerPropertiesDialog__tags.parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__tags._tags_widget.set_tags(new_tags)

        new_limits = ['limit3Name', 'limit4Name']
        self.layer_properties_dialog._LayerPropertiesDialog__limits.parent().enable(True)
        self.layer_properties_dialog._LayerPropertiesDialog__limits._limits_widget.enable_limits(
            limits_to_enable=new_limits)

        self.layer_properties_dialog.apply()
        layer1_mock.setMinMemory.assert_called_with(new_mem_value * 1024)
        layer2_mock.setMinMemory.assert_called_with(new_mem_value * 1024)
        layer1_mock.enableMemoryOptimizer.assert_called_with(new_mem_opt_is_enabled)
        layer2_mock.enableMemoryOptimizer.assert_called_with(new_mem_opt_is_enabled)
        layer1_mock.setMinCores.assert_called_with(100 * new_min_cores)
        layer2_mock.setMinCores.assert_called_with(100 * new_min_cores)
        layer1_mock.setMaxCores.assert_called_with(100 * new_max_cores)
        layer2_mock.setMaxCores.assert_called_with(100 * new_max_cores)
        layer1_mock.setThreadable.assert_called_with(new_is_threadable)
        layer2_mock.setThreadable.assert_called_with(new_is_threadable)
        layer1_mock.setMinGpuMemory.assert_called_with(
            new_min_gpu_memory * self.layer_properties_dialog.gpu_mem_tick_kb)
        layer2_mock.setMinGpuMemory.assert_called_with(
            new_min_gpu_memory * self.layer_properties_dialog.gpu_mem_tick_kb)
        layer1_mock.setTimeout.assert_called_with(new_timeout)
        layer2_mock.setTimeout.assert_called_with(new_timeout)
        layer1_mock.setTimeoutLLU.assert_called_with(new_timeout_llu)
        layer2_mock.setTimeoutLLU.assert_called_with(new_timeout_llu)
        layer1_mock.setTags.assert_called_with(new_tags)
        layer2_mock.setTags.assert_called_with(new_tags)
        layer1_mock.addLimit.assert_has_calls(
            [mock.call('limit3Id'), mock.call('limit4Id')], any_order=True)
        layer1_mock.dropLimit.assert_has_calls(
            [mock.call('limit1Id'), mock.call('limit2Id')], any_order=True)
        layer2_mock.addLimit.assert_has_calls([mock.call('limit4Id')])
        layer2_mock.dropLimit.assert_has_calls([mock.call('limit2Id')])
