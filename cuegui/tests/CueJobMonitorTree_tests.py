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


import mock
import unittest

import PySide2.QtCore
import PySide2.QtGui
import PySide2.QtWidgets

import cuegui.CueJobMonitorTree
import cuegui.plugins.MonitorCuePlugin
import cuegui.Style
import opencue.compiled_proto.job_pb2
import opencue.compiled_proto.show_pb2
import opencue.wrappers.show

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class CueJobMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, get_stub_mock):
        test_utils.createApplication()
        PySide2.QtGui.qApp.settings = PySide2.QtCore.QSettings()
        cuegui.Style.init()

        show_name = 'arbitrary-show-name'
        job_name = 'arbitrary-job-name'

        # Show is specified by name, and show details are fetched using FindShow.
        get_stub_mock.return_value.FindShow.return_value = \
            opencue.compiled_proto.show_pb2.ShowFindShowResponse(
                show=opencue.compiled_proto.show_pb2.Show(name=show_name))

        # The widget loads the show's "whiteboard", a nested data structure containing
        # all groups and jobs in the show. The top-level item is the show though it
        # uses the NestedGroup data type.
        get_stub_mock.return_value.GetJobWhiteboard.return_value = \
            opencue.compiled_proto.show_pb2.ShowGetJobWhiteboardResponse(
                whiteboard=opencue.compiled_proto.job_pb2.NestedGroup(
                    name=show_name,
                    jobs=[job_name]))

        self.main_window = PySide2.QtWidgets.QMainWindow()
        self.widget = cuegui.plugins.MonitorCuePlugin.MonitorCueDockWidget(self.main_window)
        self.cue_job_monitor_tree = cuegui.CueJobMonitorTree.CueJobMonitorTree(self.widget)
        self.cue_job_monitor_tree.addShow(show_name)

    def test_setup(self):
        pass
