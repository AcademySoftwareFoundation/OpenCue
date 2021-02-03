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


"""Tests for cuegui.FrameMonitorTree."""


import unittest

import mock
import PySide2.QtCore
import PySide2.QtGui
import PySide2.QtTest
import PySide2.QtWidgets

import opencue.compiled_proto.job_pb2
import opencue.wrappers.frame
import opencue.wrappers.job

import cuegui.Constants
import cuegui.FrameMonitor
import cuegui.FrameMonitorTree
import cuegui.Main
import cuegui.plugins.MonitorJobDetailsPlugin
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FrameMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        test_utils.createApplication()

        PySide2.QtGui.qApp.settings = PySide2.QtCore.QSettings()
        cuegui.Style.init()
        self.parentWidget = PySide2.QtWidgets.QWidget()
        self.frameMonitorTree = cuegui.FrameMonitorTree.FrameMonitorTree(self.parentWidget)
        self.job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(id='foo'))
        self.frameMonitorTree.setJob(self.job)

    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames', autospec=True)
    def test_tickInitialLoad(self, getFramesMock):
        frames = [
            opencue.wrappers.frame.Frame(
                opencue.compiled_proto.job_pb2.Frame(name='frame1')),
            opencue.wrappers.frame.Frame(
                opencue.compiled_proto.job_pb2.Frame(name='frame2'))]
        getFramesMock.return_value = frames

        self.frameMonitorTree.tick()

        getFramesMock.assert_called_with(self.job)

    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickNoUpdate(self, getFramesMock, getUpdatedFramesMock):
        getFramesMock.return_value = []
        # Initial load.
        self.frameMonitorTree.tick()
        getFramesMock.reset_mock()
        getUpdatedFramesMock.reset_mock()

        self.frameMonitorTree.tick()

        getFramesMock.assert_not_called()
        getUpdatedFramesMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames', autospec=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChanged(self, getFramesMock, getUpdatedFramesMock):
        getFramesMock.return_value = []
        getUpdatedResponse = opencue.compiled_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue.compiled_proto.job_pb2.RUNNING,
            server_time=1000,
            updated_frames=opencue.compiled_proto.job_pb2.UpdatedFrameSeq(
                updated_frames=[opencue.compiled_proto.job_pb2.UpdatedFrame(id='foo')]))
        getUpdatedFramesMock.return_value = getUpdatedResponse
        # Initial load.
        self.frameMonitorTree.tick()
        getFramesMock.reset_mock()

        self.frameMonitorTree.updateChangedRequest()
        self.frameMonitorTree.tick()

        getFramesMock.assert_not_called()
        getUpdatedFramesMock.assert_called_with(self.job, mock.ANY)

    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames', autospec=True)
    def test_tickFullUpdate(self, getFramesMock, getUpdatedFramesMock):
        getFramesMock.return_value = []
        getUpdatedResponse = opencue.compiled_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue.compiled_proto.job_pb2.RUNNING,
            server_time=1000,
            updated_frames=opencue.compiled_proto.job_pb2.UpdatedFrameSeq(
                updated_frames=[opencue.compiled_proto.job_pb2.UpdatedFrame(id='foo')]))
        getUpdatedFramesMock.return_value = getUpdatedResponse
        # Initial load.
        self.frameMonitorTree.tick()

        self.frameMonitorTree.updateRequest()
        self.frameMonitorTree.tick()

        getFramesMock.assert_called_with(self.job)
        getUpdatedFramesMock.assert_not_called()

    def test_getCores(self):
        frame = opencue.wrappers.frame.Frame(
            opencue.compiled_proto.job_pb2.Frame(last_resource='foo/125.82723'))

        self.assertEqual(125.82723, self.frameMonitorTree.getCores(frame))
        self.assertEqual('125.83', self.frameMonitorTree.getCores(frame, format_as_string=True))

    @mock.patch.object(cuegui.FrameMonitorTree.FrameContextMenu, 'exec_')
    def test_rightClickItem(self, execMock):
        mouse_position = PySide2.QtCore.QPoint()

        self.frameMonitorTree.contextMenuEvent(
            PySide2.QtGui.QContextMenuEvent(
                PySide2.QtGui.QContextMenuEvent.Reason.Mouse, mouse_position, mouse_position))

        execMock.assert_called_with(mouse_position)


class FrameWidgetItemTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.host_name = 'arbitrary-hostname'
        self.dispatch_order = 285
        self.state = opencue.compiled_proto.job_pb2.RUNNING

        self.frame = opencue.wrappers.frame.Frame(
            opencue.compiled_proto.job_pb2.Frame(
                name='frame1',
                last_resource='{}/foo'.format(self.host_name),
                dispatch_order=self.dispatch_order,
                state=self.state,
                checkpoint_state=opencue.compiled_proto.job_pb2.ENABLED))

        # The widget needs a var, otherwise it gets garbage-collected before tests can run.
        parentWidget = PySide2.QtWidgets.QWidget()

        self.frameWidgetItem = cuegui.FrameMonitorTree.FrameWidgetItem(
            self.frame,
            cuegui.FrameMonitorTree.FrameMonitorTree(parentWidget),
            opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(id='unused-job-id')))

    def test_data(self):
        cuegui.FrameMonitorTree.LOCALRESOURCE = '{}/'.format(self.host_name)
        dispatch_order_col = 0

        self.assertEqual(
            self.dispatch_order,
            self.frameWidgetItem.data(dispatch_order_col, PySide2.QtCore.Qt.DisplayRole))

        self.assertEqual(
            cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND,
            self.frameWidgetItem.data(dispatch_order_col, PySide2.QtCore.Qt.ForegroundRole))

        self.assertEqual(
            cuegui.FrameMonitorTree.QCOLOR_BLACK,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.STATUS_COLUMN, PySide2.QtCore.Qt.ForegroundRole))

        self.assertEqual(
            cuegui.FrameMonitorTree.QCOLOR_GREEN,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.PROC_COLUMN, PySide2.QtCore.Qt.ForegroundRole))

        self.assertEqual(
            cuegui.Constants.RGB_FRAME_STATE[self.state],
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.STATUS_COLUMN, PySide2.QtCore.Qt.BackgroundRole))

        self.assertEqual(
            PySide2.QtGui.QIcon,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.CHECKPOINT_COLUMN,
                PySide2.QtCore.Qt.DecorationRole).__class__)

        self.assertEqual(
            PySide2.QtCore.Qt.AlignCenter,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.STATUS_COLUMN, PySide2.QtCore.Qt.TextAlignmentRole))

        self.assertEqual(
            PySide2.QtCore.Qt.AlignRight,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.PROC_COLUMN, PySide2.QtCore.Qt.TextAlignmentRole))

        self.assertEqual(
            cuegui.Constants.TYPE_FRAME,
            self.frameWidgetItem.data(dispatch_order_col, PySide2.QtCore.Qt.UserRole))


if __name__ == '__main__':
    unittest.main()
