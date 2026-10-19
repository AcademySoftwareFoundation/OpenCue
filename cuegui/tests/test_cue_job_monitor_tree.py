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


import time
import unittest

import mock
import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtWidgets

import opencue_proto.job_pb2
import opencue_proto.show_pb2
import opencue.exception
import opencue.wrappers.job
import opencue.wrappers.show

import cuegui.Constants
import cuegui.CueJobMonitorTree
import cuegui.plugins.MonitorCuePlugin
import cuegui.Style

from . import test_utils


class _NonBlockingMenu(qtpy.QtWidgets.QMenu):
    """A QMenu that does not block when shown."""

    def exec_(self, *args):  # pylint: disable=arguments-differ,unused-argument
        return None


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

    @mock.patch('qtpy.QtCore.QTimer.singleShot')
    def test_updateSoonSchedulesForcedUpdate(self, single_shot_mock):
        self.cue_job_monitor_tree.updateSoon()

        single_shot_mock.assert_called_once_with(
            cuegui.Constants.AFTER_ACTION_UPDATE_DELAY,
            self.cue_job_monitor_tree.forceUpdate)

    def test_forceUpdateBypassesMinimumInterval(self):
        tree = self.cue_job_monitor_tree
        tree._lastUpdate = time.time()

        with mock.patch.object(tree, '_update') as update_mock:
            tree.updateRequest()
            update_mock.assert_not_called()

            tree.forceUpdate()
            update_mock.assert_called_once_with(fresh=True)

    def test_forceUpdateWhileInFlightRunsAfterCurrentFetch(self):
        tree = self.cue_job_monitor_tree
        tree._updateInFlight = True

        with mock.patch.object(tree, '_getUpdate', return_value=None) as get_update_mock:
            tree.forceUpdate()
            get_update_mock.assert_not_called()
            self.assertTrue(tree._forceUpdatePending)

            # The in-flight fetch lands; the deferred forced update runs next.
            tree._processUpdateGuarded(None, None)

            get_update_mock.assert_called_once_with(True)
            self.assertFalse(tree._forceUpdatePending)
            self.assertFalse(tree._updateInFlight)

    def test_forceUpdateRequestsFreshWhiteboard(self):
        tree = self.cue_job_monitor_tree
        show = mock.Mock()
        show.getJobWhiteboard.return_value = opencue_proto.job_pb2.NestedGroup(
            name=self.show_name)

        with mock.patch.object(tree, 'getShows', return_value=[show]):
            tree.forceUpdate()
            show.getJobWhiteboard.assert_called_once_with(fresh=True)

            show.getJobWhiteboard.reset_mock()
            tree._update()
            show.getJobWhiteboard.assert_called_once_with(fresh=False)

    @mock.patch('opencue.api.findShow')
    def test_addShowObjectSkipsLookup(self, find_show_mock):
        show = opencue.wrappers.show.Show(opencue_proto.show_pb2.Show(name='other-show'))

        with mock.patch.object(self.cue_job_monitor_tree, '_update') as update_mock:
            self.cue_job_monitor_tree.addShow(show)

            find_show_mock.assert_not_called()
            update_mock.assert_called_once_with()
        self.assertIn('other-show', self.cue_job_monitor_tree.getShowNames())

    @mock.patch('opencue.api.findShow')
    def test_addShowNameLooksShowUp(self, find_show_mock):
        find_show_mock.return_value = opencue.wrappers.show.Show(
            opencue_proto.show_pb2.Show(name='other-show'))

        with mock.patch.object(self.cue_job_monitor_tree, '_update'):
            self.cue_job_monitor_tree.addShow('other-show')

        find_show_mock.assert_called_once_with('other-show')
        self.assertIn('other-show', self.cue_job_monitor_tree.getShowNames())

    @mock.patch('opencue.api.findShow')
    def test_addMissingShowIsIgnored(self, find_show_mock):
        find_show_mock.side_effect = opencue.exception.EntityNotFoundException('not found')

        self.cue_job_monitor_tree.addShow('missing-show')

        self.assertNotIn('missing-show', self.cue_job_monitor_tree.getShowNames())

    @mock.patch('cuegui.CueJobMonitorTree.plugin_loader.load_plugins', return_value=[])
    @mock.patch('qtpy.QtWidgets.QMenu', new=_NonBlockingMenu)
    def test_contextMenuLoadsPluginsOnce(self, load_plugins_mock):
        jobs = [opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job%d' % i))
                for i in range(3)]

        with mock.patch.object(self.cue_job_monitor_tree, 'selectedObjects', return_value=jobs):
            self.cue_job_monitor_tree.contextMenuEvent(mock.Mock())

        load_plugins_mock.assert_called_once_with(job=jobs[-1], parent=self.cue_job_monitor_tree)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class MoveDialogTests(unittest.TestCase):

    def setUp(self):
        test_utils.createApplication()

    @mock.patch('opencue.api.getJob')
    def test_moveItemsUsesJobIdsWithoutFetchingJobs(self, get_job_mock):
        group = mock.Mock()
        event_item = mock.Mock()
        event_item.rpcObject.asGroup.return_value = group
        update_callback = mock.Mock()
        body = cuegui.CueJobMonitorTree.Body(
            group_names=['group-name'], group_ids=['group-id'],
            job_names=['job-a', 'job-b'], job_ids=['job-id-a', 'job-id-b'])
        dialog = cuegui.CueJobMonitorTree.MoveDialog(
            title='title', text='text', event_item=event_item, items=body, dst_groups={},
            update_callback=update_callback)

        dialog.move_items()

        get_job_mock.assert_not_called()
        jobs = group.reparentJobs.call_args[0][0]
        self.assertEqual(['job-id-a', 'job-id-b'], [job.id() for job in jobs])
        group.reparentGroupIds.assert_called_once_with(['group-id'])
        update_callback.assert_called_once_with()

    @mock.patch('qtpy.QtWidgets.QMessageBox.critical')
    def test_moveItemsReportsFailure(self, critical_mock):
        group = mock.Mock()
        group.reparentJobs.side_effect = opencue.exception.CueException('failed')
        update_callback = mock.Mock()
        body = cuegui.CueJobMonitorTree.Body(
            group_names=[], group_ids=[], job_names=['job-a'], job_ids=['job-id-a'])
        dialog = cuegui.CueJobMonitorTree.MoveDialog(
            title='title', text='text', event_item=None, items=body,
            dst_groups={'group': group}, send_to_groups=True, update_callback=update_callback)

        dialog.move_items()

        critical_mock.assert_called_once()
        update_callback.assert_called_once_with()


class _DeferredActionRunner(object):
    """Holds submitted work until run() is called."""

    def __init__(self):
        self.submitted = []

    def submit(self, work, callback=None, description=None):
        self.submitted.append((work, callback, description))

    def run(self):
        submitted, self.submitted = self.submitted, []
        for work, callback, _ in submitted:
            callback(work(), None)


class MonitorCueDockWidgetTests(unittest.TestCase):

    def setUp(self):
        self.app = test_utils.createApplication()
        self.app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.main_window = qtpy.QtWidgets.QMainWindow()

        stub_patcher = mock.patch('opencue.cuebot.Cuebot.getStub')
        self.addCleanup(stub_patcher.stop)
        self.stub = stub_patcher.start().return_value
        self.stub.GetActiveShows.return_value = opencue_proto.show_pb2.ShowGetActiveShowsResponse(
            shows=opencue_proto.show_pb2.ShowSeq(shows=[
                opencue_proto.show_pb2.Show(name='show-a'),
                opencue_proto.show_pb2.Show(name='show-b')]))
        self.stub.GetJobWhiteboard.return_value = \
            opencue_proto.show_pb2.ShowGetJobWhiteboardResponse(
                whiteboard=opencue_proto.job_pb2.NestedGroup(name='show-a'))

        self.runner = _DeferredActionRunner()
        self.app.action_runner = self.runner
        self.addCleanup(setattr, self.app, 'action_runner', None)

        self.widget = cuegui.plugins.MonitorCuePlugin.MonitorCueDockWidget(self.main_window)
        self.tree = self.widget._MonitorCueDockWidget__monitorCue

    def test_addShowsBeforeShowsAreListed(self):
        self.widget.addShows(['show-a', 'inactive-show'])

        # Restored shows are remembered, so saving settings does not lose them.
        self.assertEqual([], self.tree.getShowNames())
        self.assertEqual(['show-a', 'inactive-show'],
                         self.widget._MonitorCueDockWidget__getShowNames())
        self.stub.GetActiveShows.assert_not_called()

        self.runner.run()

        self.assertEqual(['show-a'], self.tree.getShowNames())
        self.assertEqual(['show-a'], self.widget._MonitorCueDockWidget__getShowNames())
        self.stub.FindShow.assert_not_called()

    def test_addShowsOnceShowsAreListed(self):
        self.runner.run()

        self.widget.addShows(['show-b'])

        self.assertEqual(['show-b'], self.tree.getShowNames())
        self.stub.FindShow.assert_not_called()
        self.assertEqual([], self.runner.submitted)


if __name__ == '__main__':
    unittest.main()
