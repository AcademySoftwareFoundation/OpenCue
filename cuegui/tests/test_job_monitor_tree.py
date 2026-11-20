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


"""Tests for cuegui.JobMonitorTree."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtWidgets

import opencue_proto.job_pb2
import opencue.wrappers.job

import cuegui.JobMonitorTree
import cuegui.Style

from . import test_utils


def _job(state=opencue_proto.job_pb2.PENDING, **stats):
    return opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(
        name='job-name', state=state, job_stats=opencue_proto.job_pb2.JobStats(**stats)))


@mock.patch('cuegui.JobMonitorTree.plugin_loader.load_plugins', new=mock.Mock(return_value=[]))
@mock.patch('cuegui.Constants.OUTPUT_VIEWERS', new=[])
@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class JobMonitorTreeMenuTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.jobMonitorTree = cuegui.JobMonitorTree.JobMonitorTree(self.parentWidget)

    def __menuOnRightClick(self, *jobs):
        """Opens the context menu on the jobs and returns its actions by text."""
        shownMenus = []

        class RecordingMenu(qtpy.QtWidgets.QMenu):
            """Records the menu instead of showing it."""
            def exec_(self, *_):  # pylint: disable=arguments-differ
                shownMenus.append(self)

        with mock.patch('qtpy.QtWidgets.QMenu', new=RecordingMenu), \
                mock.patch.object(self.jobMonitorTree, 'selectedObjects', return_value=list(jobs)):
            self.jobMonitorTree.contextMenuEvent(mock.Mock())
        return {action.text(): action for action in shownMenus[-1].actions()}

    def test_rightClickJobWithEatenFrames(self):
        actions = self.__menuOnRightClick(_job(succeeded_frames=9, eaten_frames=1))

        self.assertTrue(actions['Retry unsuccessful frames'].isEnabled())
        self.assertNotIn('Retry dead frames', actions)

    def test_rightClickJobWithDeadFrames(self):
        actions = self.__menuOnRightClick(_job(dead_frames=1))

        self.assertTrue(actions['Retry unsuccessful frames'].isEnabled())
        self.assertIn('Retry dead frames', actions)
        self.assertIn('Eat dead frames', actions)

    def test_rightClickJobWithNothingToRetry(self):
        actions = self.__menuOnRightClick(_job(succeeded_frames=10))

        self.assertNotIn('Retry unsuccessful frames', actions)
        self.assertNotIn('Retry dead frames', actions)

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=True)
    def test_rightClickReadonlyFinishedJob(self):
        actions = self.__menuOnRightClick(
            _job(state=opencue_proto.job_pb2.FINISHED, succeeded_frames=9, eaten_frames=1))

        self.assertFalse(actions['Retry unsuccessful frames'].isEnabled())

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=False)
    def test_rightClickFinishedJobWhenConfigAllowsRetry(self):
        actions = self.__menuOnRightClick(
            _job(state=opencue_proto.job_pb2.FINISHED, succeeded_frames=9, eaten_frames=1))

        self.assertTrue(actions['Retry unsuccessful frames'].isEnabled())

    @mock.patch('cuegui.Constants.FINISHED_JOBS_READONLY_FRAME', new=True)
    def test_rightClickFinishedAndPendingJobs(self):
        # The pending job's frames can still be retried, so the action stays enabled; it
        # leaves the finished job out when run.
        actions = self.__menuOnRightClick(
            _job(state=opencue_proto.job_pb2.FINISHED, eaten_frames=1),
            _job(eaten_frames=1, running_frames=1))

        self.assertTrue(actions['Retry unsuccessful frames'].isEnabled())


if __name__ == '__main__':
    unittest.main()
