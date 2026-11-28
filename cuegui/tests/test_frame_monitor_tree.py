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
import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtTest
import qtpy.QtWidgets

import opencue_proto.job_pb2
import opencue.exception
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
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.frameMonitorTree = cuegui.FrameMonitorTree.FrameMonitorTree(self.parentWidget)
        self.job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(id='foo'))
        self.frameMonitorTree.setJob(self.job)

    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames', autospec=True)
    def test_tickInitialLoad(self, getFramesMock):
        frames = [
            opencue.wrappers.frame.Frame(
                opencue_proto.job_pb2.Frame(name='frame1')),
            opencue.wrappers.frame.Frame(
                opencue_proto.job_pb2.Frame(name='frame2'))]
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
        getUpdatedResponse = opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue_proto.job_pb2.RUNNING,
            server_time=1000,
            updated_frames=opencue_proto.job_pb2.UpdatedFrameSeq(
                updated_frames=[opencue_proto.job_pb2.UpdatedFrame(id='foo')]))
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
        getUpdatedResponse = opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue_proto.job_pb2.RUNNING,
            server_time=1000,
            updated_frames=opencue_proto.job_pb2.UpdatedFrameSeq(
                updated_frames=[opencue_proto.job_pb2.UpdatedFrame(id='foo')]))
        getUpdatedFramesMock.return_value = getUpdatedResponse
        # Initial load.
        self.frameMonitorTree.tick()

        self.frameMonitorTree.updateRequest()
        self.frameMonitorTree.tick()

        getFramesMock.assert_called_with(self.job)
        getUpdatedFramesMock.assert_not_called()

    def __finishJob(self, getFramesMock, getUpdatedFramesMock):
        """Loads the job, then runs an update that reports the job as finished."""
        getFramesMock.return_value = []
        getUpdatedFramesMock.return_value = opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue_proto.job_pb2.FINISHED, server_time=1000)
        self.frameMonitorTree.tick()
        self.__pollChanged()
        getUpdatedFramesMock.reset_mock()

    def __pollChanged(self):
        """Runs the next update of the frames that changed."""
        self.frameMonitorTree.updateChangedRequest()
        self.frameMonitorTree.tick()

    @staticmethod
    def __finishedJob(**stats):
        return opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(
            id='foo', state=opencue_proto.job_pb2.FINISHED,
            job_stats=opencue_proto.job_pb2.JobStats(**stats)))

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames', autospec=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedAfterJobFinishedWithEatenFrames(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        getJobMock.return_value = self.__finishedJob(succeeded_frames=9, eaten_frames=1)
        self.__finishJob(getFramesMock, getUpdatedFramesMock)

        # The frame counts loaded with the job predate its finish, so they are fetched once.
        getJobMock.assert_called_once_with('foo')
        self.assertEqual(1, self.job.data.job_stats.eaten_frames)

        # A retry of its frames moves the job back to PENDING.
        getUpdatedFramesMock.return_value = opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue_proto.job_pb2.PENDING,
            server_time=2000,
            updated_frames=opencue_proto.job_pb2.UpdatedFrameSeq(
                updated_frames=[opencue_proto.job_pb2.UpdatedFrame(id='foo')]))
        self.__pollChanged()

        getUpdatedFramesMock.assert_called_with(self.job, mock.ANY)
        self.assertEqual(opencue_proto.job_pb2.PENDING, self.job.state())
        getJobMock.assert_called_once()

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickNoUpdateChangedAfterJobFinishedWithAllFramesSucceeded(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        getJobMock.return_value = self.__finishedJob(succeeded_frames=10)
        self.__finishJob(getFramesMock, getUpdatedFramesMock)

        self.__pollChanged()

        getUpdatedFramesMock.assert_not_called()
        getJobMock.assert_called_once_with('foo')

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=True)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickNoUpdateChangedAfterReadonlyJobFinished(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        self.__finishJob(getFramesMock, getUpdatedFramesMock)

        self.__pollChanged()

        getUpdatedFramesMock.assert_not_called()
        getJobMock.assert_not_called()

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickNoUpdateChangedForLoadedJobWithAllFramesSucceeded(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        getFramesMock.return_value = []
        # The frame counts loaded with a finished job are final.
        self.frameMonitorTree.setJob(self.__finishedJob(succeeded_frames=10))
        self.frameMonitorTree.tick()

        self.__pollChanged()

        getUpdatedFramesMock.assert_not_called()
        getJobMock.assert_not_called()

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames', autospec=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedForLoadedJobWithEatenFrames(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        getFramesMock.return_value = []
        getUpdatedFramesMock.return_value = opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue_proto.job_pb2.FINISHED, server_time=1000)
        job = self.__finishedJob(succeeded_frames=9, eaten_frames=1)
        self.frameMonitorTree.setJob(job)
        self.frameMonitorTree.tick()

        self.__pollChanged()

        getUpdatedFramesMock.assert_called_with(job, mock.ANY)
        getJobMock.assert_not_called()

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedRetriesFailedFrameCountsFetch(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        getJobMock.side_effect = [opencue.exception.CueException('arbitrary failure'),
                                  self.__finishedJob(succeeded_frames=10)]
        self.__finishJob(getFramesMock, getUpdatedFramesMock)

        # Without current counts the job is still polled, and the fetch is retried.
        self.__pollChanged()
        getUpdatedFramesMock.assert_called_once()
        self.assertEqual(2, getJobMock.call_count)

        # The counts show every frame succeeded, so polling stops.
        getUpdatedFramesMock.reset_mock()
        self.__pollChanged()
        getUpdatedFramesMock.assert_not_called()

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    @mock.patch('opencue.api.getJob')
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames', autospec=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedTakesTheStateReadWithTheFrameCounts(
            self, getFramesMock, getUpdatedFramesMock, getJobMock):
        # The job's eaten frames are retried after the update that reports it finished, so
        # the counts fetched next show none to retry.
        getJobMock.return_value = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(
            id='foo', state=opencue_proto.job_pb2.PENDING,
            job_stats=opencue_proto.job_pb2.JobStats(succeeded_frames=9, waiting_frames=1)))
        self.__finishJob(getFramesMock, getUpdatedFramesMock)

        # The job is pending again, as the counts say, so it is still polled.
        self.assertEqual(opencue_proto.job_pb2.PENDING, self.job.state())
        self.__pollChanged()
        getUpdatedFramesMock.assert_called_with(self.job, mock.ANY)

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getUpdatedFrames')
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedSetsJobState(self, getFramesMock, getUpdatedFramesMock):
        self.__finishJob(getFramesMock, getUpdatedFramesMock)

        # The layer view shares the job and reads its state for its menu.
        self.assertEqual(opencue_proto.job_pb2.FINISHED, self.job.state())

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedSetsStateOfPolledJob(self, getFramesMock):
        getFramesMock.return_value = []
        self.frameMonitorTree.tick()
        otherJob = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(id='bar'))

        def switchJobAndFinish(_):
            # Another job is opened while this job's update is in flight.
            self.frameMonitorTree._FrameMonitorTree__job = otherJob  # pylint: disable=protected-access
            return opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
                state=opencue_proto.job_pb2.FINISHED, server_time=1000)

        with mock.patch.object(self.job, 'getUpdatedFrames', side_effect=switchJobAndFinish):
            self.__pollChanged()

        self.assertEqual(opencue_proto.job_pb2.FINISHED, self.job.state())
        self.assertEqual(opencue_proto.job_pb2.PENDING, otherJob.state())

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_LAYER', new=True)
    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=True)
    @mock.patch.object(opencue.wrappers.job.Job, 'getFrames')
    def test_tickUpdateChangedLeavesTheTreeToAJobOpenedInFlight(self, getFramesMock):
        getFramesMock.return_value = []
        self.frameMonitorTree.tick()
        otherJob = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(id='bar'))

        def openOtherJobAndFinish(_):
            # Another job is opened while this job's update is in flight.
            self.frameMonitorTree._FrameMonitorTree__setJob(otherJob)  # pylint: disable=protected-access
            return opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
                state=opencue_proto.job_pb2.FINISHED, server_time=1000)

        with mock.patch.object(self.job, 'getUpdatedFrames', side_effect=openOtherJobAndFinish):
            self.__pollChanged()

        # The tree's state is still the other job's, which is pending, so it is polled.
        otherUpdate = opencue_proto.job_pb2.JobGetUpdatedFramesResponse(
            state=opencue_proto.job_pb2.PENDING, server_time=2000)
        with mock.patch.object(otherJob, 'getUpdatedFrames',
                               return_value=otherUpdate) as otherGetUpdatedFramesMock:
            self.__pollChanged()
        otherGetUpdatedFramesMock.assert_called_once()

    def test_getCores(self):
        frame = opencue.wrappers.frame.Frame(
            opencue_proto.job_pb2.Frame(last_resource='foo/125.82723/0'))

        self.assertEqual(125.82723, self.frameMonitorTree.getCores(frame))
        self.assertEqual('125.83', self.frameMonitorTree.getCores(frame, format_as_string=True))

    @mock.patch.object(cuegui.FrameMonitorTree.FrameContextMenu, 'exec_')
    def test_rightClickItem(self, execMock):
        mouse_position = qtpy.QtCore.QPoint()

        # Ensure the job attribute is set
        self.frameMonitorTree.setJob(self.job)

        # Mock the getLayers method to return an empty list or a list of mock layers
        with mock.patch.object(self.job, 'getLayers', return_value=[]):
            self.frameMonitorTree.contextMenuEvent(
                qtpy.QtGui.QContextMenuEvent(
                    qtpy.QtGui.QContextMenuEvent.Reason.Mouse, mouse_position, mouse_position))

        execMock.assert_called_with(mouse_position)


class FrameWidgetItemTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.host_name = 'arbitrary-hostname'
        self.dispatch_order = 285
        self.state = opencue_proto.job_pb2.RUNNING

        self.frame = opencue.wrappers.frame.Frame(
            opencue_proto.job_pb2.Frame(
                name='frame1',
                last_resource='{}/foo'.format(self.host_name),
                dispatch_order=self.dispatch_order,
                state=self.state,
                checkpoint_state=opencue_proto.job_pb2.ENABLED))

        # The widget needs a var, otherwise it gets garbage-collected before tests can run.
        parentWidget = qtpy.QtWidgets.QWidget()

        self.frameWidgetItem = cuegui.FrameMonitorTree.FrameWidgetItem(
            self.frame,
            cuegui.FrameMonitorTree.FrameMonitorTree(parentWidget),
            opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(id='unused-job-id')))

    def test_data(self):
        cuegui.FrameMonitorTree.LOCALRESOURCE = '{}/'.format(self.host_name)
        dispatch_order_col = 0

        self.assertEqual(
            self.dispatch_order,
            self.frameWidgetItem.data(dispatch_order_col, qtpy.QtCore.Qt.DisplayRole))

        self.assertEqual(
            cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND,
            self.frameWidgetItem.data(dispatch_order_col, qtpy.QtCore.Qt.ForegroundRole))

        self.assertEqual(
            cuegui.FrameMonitorTree.QCOLOR_BLACK,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.STATUS_COLUMN, qtpy.QtCore.Qt.ForegroundRole))

        self.assertEqual(
            cuegui.FrameMonitorTree.QCOLOR_GREEN,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.PROC_COLUMN, qtpy.QtCore.Qt.ForegroundRole))

        self.assertEqual(
            cuegui.Constants.RGB_FRAME_STATE[self.state],
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.STATUS_COLUMN, qtpy.QtCore.Qt.BackgroundRole))

        self.assertEqual(
            qtpy.QtGui.QIcon,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.CHECKPOINT_COLUMN,
                qtpy.QtCore.Qt.DecorationRole).__class__)

        self.assertEqual(
            qtpy.QtCore.Qt.AlignCenter,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.STATUS_COLUMN, qtpy.QtCore.Qt.TextAlignmentRole))

        self.assertEqual(
            qtpy.QtCore.Qt.AlignRight,
            self.frameWidgetItem.data(
                cuegui.FrameMonitorTree.PROC_COLUMN, qtpy.QtCore.Qt.TextAlignmentRole))

        self.assertEqual(
            cuegui.Constants.TYPE_FRAME,
            self.frameWidgetItem.data(dispatch_order_col, qtpy.QtCore.Qt.UserRole))


if __name__ == '__main__':
    unittest.main()
