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
import opencue.wrappers.group
import opencue.wrappers.job
import opencue.wrappers.show

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.CueJobMonitorTree
import cuegui.ItemDelegate
import cuegui.plugins.MonitorCuePlugin
import cuegui.Style

from . import test_utils


class _NonBlockingMenu(qtpy.QtWidgets.QMenu):  # pylint: disable=too-few-public-methods
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

    def _whiteboard(self, groups):
        """Builds a whiteboard for the show from a {group: parent group} dict."""
        protos = {'root': opencue_proto.job_pb2.NestedGroup(id='root', name=self.show_name)}
        for name in groups:
            protos[name] = opencue_proto.job_pb2.NestedGroup(id=name, name=name)
        # Nest the deepest groups first, as protobuf copies the messages.
        for name in sorted(groups, key=lambda name: -self._depth(groups, name)):
            parent = protos[groups[name]]
            protos[name].parent.CopyFrom(
                opencue_proto.job_pb2.NestedGroup(id=parent.id, name=parent.name))
            parent.groups.nested_groups.append(protos[name])
        show = mock.Mock()
        show.getJobWhiteboard.return_value = protos['root']
        return mock.patch.object(self.cue_job_monitor_tree, 'getShows', return_value=[show])

    @staticmethod
    def _depth(groups, name):
        depth = 0
        while name in groups:
            name = groups[name]
            depth += 1
        return depth

    def _expanded(self):
        return {itemId: item.isExpanded()
                for itemId, item in self.cue_job_monitor_tree._items.items()}

    def test_updateDoesNotExpandWholeTree(self):
        tree = self.cue_job_monitor_tree
        with self._whiteboard({'g1': 'root'}), \
                mock.patch.object(tree, 'expandAll') as expand_all_mock:
            tree._update()
            tree._update()

        expand_all_mock.assert_not_called()

    def test_newGroupsAreExpanded(self):
        tree = self.cue_job_monitor_tree
        with self._whiteboard({'g1': 'root', 'g2': 'g1'}):
            tree._update()

        self.assertEqual({'root': True, 'g1': True, 'g2': True}, self._expanded())

    def test_collapsedGroupStaysCollapsed(self):
        tree = self.cue_job_monitor_tree
        with self._whiteboard({'g1': 'root', 'g2': 'g1'}):
            tree._update()
        tree._items['g1'].setExpanded(False)

        with self._whiteboard({'g1': 'root', 'g2': 'g1', 'g3': 'g1'}):
            tree._update()

        self.assertEqual({'root': True, 'g1': False, 'g2': True, 'g3': True}, self._expanded())

    def test_reparentedGroupKeepsExpansionState(self):
        tree = self.cue_job_monitor_tree
        with self._whiteboard({'g1': 'root', 'g2': 'root', 'g3': 'g2', 'g4': 'g3'}):
            tree._update()
        tree._items['g3'].setExpanded(False)

        with self._whiteboard({'g1': 'root', 'g2': 'g1', 'g3': 'g2', 'g4': 'g3'}):
            tree._update()

        self.assertIs(tree._items['g1'], tree._items['g2'].parent())
        self.assertEqual(
            {'root': True, 'g1': True, 'g2': True, 'g3': False, 'g4': True}, self._expanded())

    def _showJobs(self, *jobs):
        """Updates the tree with the jobs in a group of the show."""
        root = opencue_proto.job_pb2.NestedGroup(id='root', name=self.show_name)
        group = root.groups.nested_groups.add(id='g1', name='g1')
        group.parent.CopyFrom(opencue_proto.job_pb2.NestedGroup(id='root', name=self.show_name))
        for job in jobs:
            group.jobs.append(job.id)
            group.inline_jobs.add().CopyFrom(job)
        show = mock.Mock()
        show.getJobWhiteboard.return_value = root
        with mock.patch.object(self.cue_job_monitor_tree, 'getShows', return_value=[show]):
            self.cue_job_monitor_tree._update()

    @staticmethod
    def _job(**stats):
        return opencue_proto.job_pb2.Job(
            id='job1', name='job1', min_cores=1, max_cores=10, start_time=int(time.time()),
            job_stats=opencue_proto.job_pb2.JobStats(**stats))

    def _cells(self, item, role):
        return [item.data(col, role) for col in range(self.cue_job_monitor_tree.columnCount())]

    def test_itemsDoNotOverrideData(self):
        # Qt calls into Python for every cell painted if data() is overridden.
        self._showJobs(self._job())

        items = self.cue_job_monitor_tree._items
        self.assertEqual({'root', 'g1', 'job1'}, set(items))
        for item in items.values():
            self.assertIs(qtpy.QtWidgets.QTreeWidgetItem.data, type(item).data)

    def test_jobCellsAreBaked(self):
        theme = cuegui.Style.ColorTheme
        self._showJobs(opencue_proto.job_pb2.Job(
            id='job1', name='job1', min_cores=1, max_cores=10, has_comment=True,
            start_time=int(time.time()),
            job_stats=opencue_proto.job_pb2.JobStats(
                running_frames=3, waiting_frames=4, succeeded_frames=5, reserved_cores=2.5,
                max_rss=cuegui.Constants.MEMORY_WARNING_LEVEL + 1)))
        tree = self.cue_job_monitor_tree
        item = tree._items['job1']

        display = self._cells(item, qtpy.QtCore.Qt.DisplayRole)
        self.assertEqual(
            [info[cuegui.Constants.COLUMN_INFO_DISPLAY](item.rpcObject)
             for info in tree.getColumnInfo(cuegui.Constants.TYPE_JOB)],
            display)
        self.assertEqual(['job1', 3, '2.50', 4], [display[0], display[3], display[4], display[6]])
        self.assertEqual([theme.COLOR_JOB_FOREGROUND] * len(display),
                         self._cells(item, qtpy.QtCore.Qt.ForegroundRole))
        background = self._cells(item, qtpy.QtCore.Qt.BackgroundRole)
        names = [info[cuegui.AbstractTreeWidget.COLUMN_NAME]
                 for info in tree.getColumnInfo(cuegui.Constants.TYPE_JOB)]
        self.assertEqual(names.index('MaxRss'), cuegui.CueJobMonitorTree.COLUMN_MAXRSS)
        self.assertEqual(names.index('Age'), cuegui.CueJobMonitorTree.COLUMN_AGE)
        self.assertEqual(theme.COLOR_JOB_HIGH_MEMORY, background[names.index('MaxRss')])
        self.assertEqual(qtpy.QtGui.QColor, type(background[0]))
        self.assertNotEqual(theme.COLOR_JOB_HIGH_MEMORY, background[0])
        self.assertIsInstance(
            item.data(cuegui.CueJobMonitorTree.COLUMN_COMMENT, qtpy.QtCore.Qt.DecorationRole),
            qtpy.QtGui.QIcon)
        self.assertIsNone(
            item.data(cuegui.CueJobMonitorTree.COLUMN_EAT, qtpy.QtCore.Qt.DecorationRole))

        bars = [col for col, info in enumerate(tree.getColumnInfo(cuegui.Constants.TYPE_JOB))
                if info[cuegui.AbstractTreeWidget.COLUMN_DELEGATE]]
        self.assertEqual(2, len(bars))
        for col in bars:
            self.assertEqual(cuegui.Constants.TYPE_JOB, item.data(col, qtpy.QtCore.Qt.UserRole))
            self.assertEqual(
                {opencue_proto.job_pb2.WAITING: 4, opencue_proto.job_pb2.RUNNING: 3,
                 opencue_proto.job_pb2.SUCCEEDED: 5, opencue_proto.job_pb2.CHECKPOINT: 0,
                 opencue_proto.job_pb2.SETUP: 0, opencue_proto.job_pb2.EATEN: 0,
                 opencue_proto.job_pb2.DEAD: 0, opencue_proto.job_pb2.DEPEND: 0},
                item.data(col, qtpy.QtCore.Qt.UserRole + 1))
            self.assertEqual((3, 4, 2.5, 1, 10), item.data(col, cuegui.ItemDelegate.BOOKING_ROLE))

    def test_jobCellsFollowUpdates(self):
        job = self._job(running_frames=3)
        self._showJobs(job)
        item = self.cue_job_monitor_tree._items['job1']

        job.is_paused = True
        job.has_comment = True
        job.job_stats.running_frames = 5
        self._showJobs(job)

        self.assertIs(item, self.cue_job_monitor_tree._items['job1'])
        self.assertEqual(5, item.data(3, qtpy.QtCore.Qt.DisplayRole))
        self.assertEqual([cuegui.Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND] * 21,
                         self._cells(item, qtpy.QtCore.Qt.BackgroundRole))
        self.assertIsInstance(
            item.data(cuegui.CueJobMonitorTree.COLUMN_COMMENT, qtpy.QtCore.Qt.DecorationRole),
            qtpy.QtGui.QIcon)
        self.assertEqual(5, item.data(9, cuegui.ItemDelegate.BOOKING_ROLE)[0])

    def test_unchangedJobOnlyUpdatesAge(self):
        job = self._job(waiting_frames=1)
        self._showJobs(job)
        item = self.cue_job_monitor_tree._items['job1']
        self.assertEqual('000:00', item.data(cuegui.CueJobMonitorTree.COLUMN_AGE,
                                             qtpy.QtCore.Qt.DisplayRole))

        later = time.time() + 3600
        with mock.patch('time.time', return_value=later), \
                mock.patch.object(cuegui.CueJobMonitorTree.JobWidgetItem, '_bake') as bake_mock:
            self._showJobs(job)

        bake_mock.assert_not_called()
        self.assertEqual('001:00', item.data(cuegui.CueJobMonitorTree.COLUMN_AGE,
                                             qtpy.QtCore.Qt.DisplayRole))
        # The job has been waiting without running frames for too long.
        self.assertEqual([cuegui.Style.ColorTheme.COLOR_JOB_WITHOUT_PROCS] * 21,
                         self._cells(item, qtpy.QtCore.Qt.BackgroundRole))

    def test_groupCellsAreBaked(self):
        theme = cuegui.Style.ColorTheme
        self._showJobs()
        items = self.cue_job_monitor_tree._items

        for itemId, name, foreground, background in (
                ('root', self.show_name, theme.COLOR_SHOW_FOREGROUND, theme.COLOR_SHOW_BACKGROUND),
                ('g1', 'g1', theme.COLOR_GROUP_FOREGROUND, theme.COLOR_GROUP_BACKGROUND)):
            item = items[itemId]
            self.assertEqual([foreground] * 21, self._cells(item, qtpy.QtCore.Qt.ForegroundRole))
            self.assertEqual([background] * 21, self._cells(item, qtpy.QtCore.Qt.BackgroundRole))
            self.assertEqual([cuegui.CueJobMonitorTree.FONT_BOLD] * 21,
                             self._cells(item, qtpy.QtCore.Qt.FontRole))
            self.assertIsInstance(item.data(0, qtpy.QtCore.Qt.DecorationRole), qtpy.QtGui.QIcon)
            self.assertEqual(name, item.data(0, qtpy.QtCore.Qt.DisplayRole))

    def test_bookingBarPaintsBakedData(self):
        self._showJobs(self._job(running_frames=3, waiting_frames=4, reserved_cores=3))
        tree = self.cue_job_monitor_tree
        item = tree._items['job1']
        delegate = tree.itemDelegateForColumn(9)
        self.assertIsInstance(delegate, cuegui.ItemDelegate.JobBookingBarDelegate)
        image = qtpy.QtGui.QImage(150, 20, qtpy.QtGui.QImage.Format_ARGB32)
        painter = qtpy.QtGui.QPainter(image)
        option = qtpy.QtWidgets.QStyleOptionViewItem()
        option.rect = qtpy.QtCore.QRect(0, 0, 150, 20)

        try:
            with mock.patch.object(tree, 'itemFromIndex') as item_from_index_mock:
                delegate.paint(painter, option, tree.indexFromItem(item, 9))
        finally:
            painter.end()

        item_from_index_mock.assert_not_called()

    def _runningJobs(self, **running):
        """Updates the tree with jobs that have the given numbers of running frames."""
        self._showJobs(*[
            opencue_proto.job_pb2.Job(
                id=name, name=name, start_time=int(time.time()),
                job_stats=opencue_proto.job_pb2.JobStats(running_frames=frames))
            for name, frames in running.items()])

    def _jobOrder(self):
        group = self.cue_job_monitor_tree._items['g1']
        return [group.child(i).rpcObject.data.name for i in range(group.childCount())]

    def test_jobsAreSortedByKeysComputedOncePerUpdate(self):
        tree = self.cue_job_monitor_tree
        tree.sortByColumn(3, qtpy.QtCore.Qt.AscendingOrder)
        info = tree.getColumnInfo(cuegui.Constants.TYPE_JOB)[3]
        sort_mock = mock.Mock(side_effect=info[cuegui.AbstractWidgetItem.SORT_LAMBDA])
        info[cuegui.AbstractWidgetItem.SORT_LAMBDA] = sort_mock

        self._runningJobs(a=5, b=1, c=3, d=4, e=2)

        self.assertEqual(['b', 'e', 'c', 'd', 'a'], self._jobOrder())
        self.assertLessEqual(sort_mock.call_count, 5)

        sort_mock.reset_mock()
        self._runningJobs(a=0, b=1, c=3, d=4, e=2, f=6)

        self.assertEqual(['a', 'b', 'e', 'c', 'd', 'f'], self._jobOrder())
        self.assertLessEqual(sort_mock.call_count, 6)

    def test_sortingIsPausedWhileItemsAreAdded(self):
        tree = self.cue_job_monitor_tree
        tree.sortByColumn(3, qtpy.QtCore.Qt.DescendingOrder)
        self._runningJobs(a=1)
        sorting = []
        job_widget_item = cuegui.CueJobMonitorTree.JobWidgetItem

        def addJob(job, parent):
            sorting.append(tree.isSortingEnabled())
            return job_widget_item(job, parent)

        with mock.patch.object(cuegui.CueJobMonitorTree, 'JobWidgetItem', side_effect=addJob):
            self._runningJobs(a=1, b=3, c=2)

        self.assertEqual([False, False], sorting)
        self.assertTrue(tree.isSortingEnabled())
        self.assertEqual(['b', 'c', 'a'], self._jobOrder())

    def test_sortingIsRestoredWhenUpdateFails(self):
        tree = self.cue_job_monitor_tree
        self._runningJobs(a=1)

        with mock.patch.object(
                cuegui.CueJobMonitorTree, 'JobWidgetItem', side_effect=ValueError):
            self._runningJobs(a=1, b=2)

        self.assertTrue(tree.isSortingEnabled())

    def test_dataChangesKeepSortingEnabled(self):
        tree = self.cue_job_monitor_tree
        tree.sortByColumn(3, qtpy.QtCore.Qt.AscendingOrder)
        self._runningJobs(a=5, b=1, c=3)

        with mock.patch.object(tree, 'setSortingEnabled') as set_sorting_mock:
            self._runningJobs(a=0, b=1, c=3)

        set_sorting_mock.assert_not_called()
        self.assertEqual(['a', 'b', 'c'], self._jobOrder())

    def test_groupsStayAlphabetical(self):
        tree = self.cue_job_monitor_tree
        tree.sortByColumn(3, qtpy.QtCore.Qt.DescendingOrder)

        with self._whiteboard({'gb': 'root', 'gc': 'root', 'ga': 'root'}):
            tree._update()

        root = tree._items['root']
        self.assertEqual(['ga', 'gb', 'gc'],
                         [root.child(i).rpcObject.name() for i in range(root.childCount())])

    @mock.patch('opencue.api.findShow')
    def test_addShowObjectSkipsLookup(self, find_show_mock):
        show = opencue.wrappers.show.Show(opencue_proto.show_pb2.Show(name='other-show'))

        with mock.patch.object(self.cue_job_monitor_tree, 'forceUpdate') as update_mock:
            self.cue_job_monitor_tree.addShow(show)

            find_show_mock.assert_not_called()
            update_mock.assert_called_once_with(fresh=False)
        self.assertIn('other-show', self.cue_job_monitor_tree.getShowNames())

    def test_showChangeWhileInFlightUpdatesAfterCurrentFetch(self):
        tree = self.cue_job_monitor_tree
        tree._updateInFlight = True

        with mock.patch.object(tree, '_getUpdate', return_value=None) as get_update_mock:
            tree.removeShow(self.show_name)
            get_update_mock.assert_not_called()
            self.assertTrue(tree._forceUpdatePending)

            # The in-flight fetch still had the removed show; refetch without it.
            tree._processUpdateGuarded(None, None)

            get_update_mock.assert_called_once_with(False)
            self.assertFalse(tree._forceUpdatePending)

    def test_deferredForcedUpdateIsFreshIfAnyRequestWas(self):
        tree = self.cue_job_monitor_tree
        tree._updateInFlight = True

        with mock.patch.object(tree, '_getUpdate', return_value=None) as get_update_mock:
            tree.forceUpdate()
            tree.forceUpdate(fresh=False)
            tree._processUpdateGuarded(None, None)

            get_update_mock.assert_called_once_with(True)
            self.assertFalse(tree._forceUpdateFresh)

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

    @mock.patch('opencue.api.findShow')
    def test_removeAllShowsDropsQueuedShowLookups(self, find_show_mock):
        find_show_mock.return_value = opencue.wrappers.show.Show(
            opencue_proto.show_pb2.Show(name='other-show'))
        tree = self.cue_job_monitor_tree
        tree.removeAllShows()
        app = test_utils.createApplication()
        runner = _DeferredActionRunner()
        app.action_runner = runner
        self.addCleanup(setattr, app, 'action_runner', None)

        tree.addShow('other-show')
        # Nothing is monitored, so the clear must still invalidate the lookup.
        tree.removeAllShows()
        runner.run()

        self.assertNotIn('other-show', tree.getShowNames())

    @mock.patch('cuegui.CueJobMonitorTree.plugin_loader.load_plugins', return_value=[])
    @mock.patch('qtpy.QtWidgets.QMenu', new=_NonBlockingMenu)
    def test_contextMenuLoadsPluginsOnce(self, load_plugins_mock):
        jobs = [opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job%d' % i))
                for i in range(3)]

        with mock.patch.object(self.cue_job_monitor_tree, 'selectedObjects', return_value=jobs):
            self.cue_job_monitor_tree.contextMenuEvent(mock.Mock())

        load_plugins_mock.assert_called_once_with(job=jobs[-1], parent=self.cue_job_monitor_tree)

    @mock.patch('cuegui.CueJobMonitorTree.plugin_loader.load_plugins')
    @mock.patch('qtpy.QtWidgets.QMenu', new=_NonBlockingMenu)
    def test_contextMenuPluginsOnlyGetJobs(self, load_plugins_mock):
        launched = []

        # The tree launches plugins of this type name once per selected job.
        class Plugin(object):  # pylint: disable=too-few-public-methods
            def __init__(self, job, parent=None):
                del parent
                self.job = job
                self._config = {'menu_label': 'arbitrary-plugin'}

            def launch_subprocess(self):
                launched.append(self.job)

        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job1'))
        group = opencue.wrappers.group.Group(opencue_proto.job_pb2.Group(name='group1'))
        load_plugins_mock.return_value = [Plugin(job)]
        tree = self.cue_job_monitor_tree

        with mock.patch.object(tree, 'selectedObjects', return_value=[job, group]):
            tree.contextMenuEvent(mock.Mock())

        load_plugins_mock.assert_called_once_with(job=job, parent=tree)
        actions = [action for action in tree.findChildren(qtpy.QtWidgets.QAction)
                   if action.text() == 'arbitrary-plugin']
        self.assertEqual(1, len(actions))
        actions[0].trigger()
        self.assertEqual([job], launched)


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
