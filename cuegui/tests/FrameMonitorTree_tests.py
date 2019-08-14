#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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
import PySide2.QtTest
import PySide2.QtWidgets

import cuegui.FrameMonitor
import cuegui.FrameMonitorTree
import cuegui.Main
import cuegui.plugins.MonitorJobDetailsPlugin
import cuegui.Style
import opencue.compiled_proto.job_pb2
import opencue.wrappers.frame
import opencue.wrappers.job


_instance = None


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FrameMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        global _instance
        if _instance is None:
            _instance = cuegui.Main.CueGuiApplication()
        self.app = _instance

        PySide2.QtGui.qApp.settings = PySide2.QtCore.QSettings()
        cuegui.Style.init()
        self.parentWidget = PySide2.QtWidgets.QWidget()
        self.frameMonitorTree = cuegui.FrameMonitorTree.FrameMonitorTree(self.parentWidget)
        self.job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(id='foo'))
        self.frameMonitorTree.setJob(self.job)

    def tearDown(self):
        #del self.app
        pass

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
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(last_resource='foo/125.82723'))

        self.assertEqual(125.82723, self.frameMonitorTree.getCores(frame))
        self.assertEqual('125.83', self.frameMonitorTree.getCores(frame, format=True))

    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames', autospec=True)
    def test_rightClickItem(self, getFramesMock):
        frames = [
            opencue.wrappers.frame.Frame(
                opencue.compiled_proto.job_pb2.Frame(name='frame1')),
            opencue.wrappers.frame.Frame(
                opencue.compiled_proto.job_pb2.Frame(name='frame2'))]
        getFramesMock.return_value = frames
        self.frameMonitorTree.tick()

        PySide2.QtTest.QTest.mouseClick(self.frameMonitorTree, PySide2.QtCore.Qt.RightButton)


if __name__ == '__main__':
    unittest.main()
