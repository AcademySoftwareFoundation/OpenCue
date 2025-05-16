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


"""Tests for cuegui.CueJobMonitorTree."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtWidgets

import opencue_proto.job_pb2
import opencue_proto.show_pb2

import cuegui.CueJobMonitorTree
import cuegui.plugins.MonitorCuePlugin
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class CueJobMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, get_stub_mock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        self.show_name = 'arbitrary-show-name'
        self.jobs = ['arbitrary-job-name']

        # Show is specified by name, and show details are fetched using FindShow.
        get_stub_mock.return_value.FindShow.return_value = \
            opencue_proto.show_pb2.ShowFindShowResponse(
                show=opencue_proto.show_pb2.Show(name=self.show_name))

        # The widget loads the show's "whiteboard", a nested data structure containing
        # all groups and jobs in the show. The top-level item is the show though it
        # uses the NestedGroup data type.
        get_stub_mock.return_value.GetJobWhiteboard.return_value = \
            opencue_proto.show_pb2.ShowGetJobWhiteboardResponse(
                whiteboard=opencue_proto.job_pb2.NestedGroup(
                    name=self.show_name,
                    jobs=self.jobs))

        self.main_window = qtpy.QtWidgets.QMainWindow()
        self.widget = cuegui.plugins.MonitorCuePlugin.MonitorCueDockWidget(self.main_window)
        self.cue_job_monitor_tree = cuegui.CueJobMonitorTree.CueJobMonitorTree(self.widget)
        self.cue_job_monitor_tree.addShow(self.show_name)

    def test_setup(self):
        pass
