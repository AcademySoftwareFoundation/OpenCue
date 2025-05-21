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


"""Tests for cuegui.UnbookDialog."""


import unittest

import mock

import qtpy.QtCore
import qtpy.QtGui

import opencue_proto.criterion_pb2
import opencue_proto.host_pb2
import opencue_proto.job_pb2
import opencue_proto.show_pb2
import opencue_proto.subscription_pb2
import opencue.wrappers.group
import opencue.wrappers.job
import opencue.wrappers.proc
import opencue.wrappers.show
import opencue.wrappers.subscription

import cuegui.Style
import cuegui.UnbookDialog

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class UnbookDialogTests(unittest.TestCase):

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, get_stub_mock, find_show_mock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        show_name = 'showname'
        self.job_names = [
            '%s-shotname-username_job1' % show_name, '%s-shotname-username_job2' % show_name]
        self.jobs = [
            opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=self.job_names[0])),
            opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=self.job_names[1]))]
        show = opencue.wrappers.show.Show(opencue_proto.show_pb2.Show(name=show_name))
        self.tag_names = ['general', 'desktop']
        subscriptions = [
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    name='local.%s.%s' % (self.tag_names[0], show_name))),
            opencue.wrappers.subscription.Subscription(
                opencue_proto.subscription_pb2.Subscription(
                    name='local.%s.%s' % (self.tag_names[1], show_name))),
        ]
        show.getSubscriptions = mock.Mock()
        show.getSubscriptions.return_value = subscriptions
        find_show_mock.return_value = show

        self.dialog = cuegui.UnbookDialog.UnbookDialog(self.jobs)

    def test__should_show_all_jobs_and_subscriptions(self):
        self.dialog.open()

        jobs_shown = self.dialog._UnbookDialog__jobList.toPlainText().split()
        self.assertEqual(self.job_names, jobs_shown)
        subscription_matrix = self.dialog._UnbookDialog__matrix
        subscriptions_shown = [
            checkbox.text()
            for checkbox in subscription_matrix._CheckBoxSelectionMatrix__checkBoxes]
        subscriptions_checked = subscription_matrix.checkedOptions()
        self.assertEqual(self.tag_names, subscriptions_shown)
        self.assertEqual(self.tag_names, subscriptions_checked)

    @mock.patch('qtpy.QtWidgets.QMessageBox', new=mock.Mock())
    @mock.patch('opencue.api.getProcs')
    def test__should_unbook_procs(self, get_procs_mock):
        num_procs = 17
        min_mem = 56
        max_mem = 143
        expected_proc_search = opencue.search.ProcSearch(
            allocs=self.tag_names, jobs=self.job_names, maxResults=[num_procs],
            memoryRange=[opencue_proto.criterion_pb2.InRangeIntegerSearchCriterion(
                min=min_mem*1024, max=max_mem*1024)])
        returned_proc1 = opencue.wrappers.proc.Proc()
        returned_proc1.unbook = mock.Mock()
        returned_proc2 = opencue.wrappers.proc.Proc()
        returned_proc2.unbook = mock.Mock()
        get_procs_mock.return_value = [returned_proc1, returned_proc2]

        self.dialog.open()
        self.dialog._UnbookDialog__amount.setValue(num_procs)
        self.dialog._UnbookDialog__memoryRangeBox._RangeBox__group.setChecked(True)
        self.dialog._UnbookDialog__memoryRangeBox._RangeBox__range.setChecked(True)
        self.dialog._UnbookDialog__memoryRangeBox._RangeBox__min.setValue(min_mem)
        self.dialog._UnbookDialog__memoryRangeBox._RangeBox__max.setValue(max_mem)
        self.dialog.accept()

        get_procs_mock.assert_called_with(**expected_proc_search.options)
        returned_proc1.unbook.assert_called()
        returned_proc2.unbook.assert_called()

    @mock.patch('cuegui.UnbookDialog.KillConfirmationDialog')
    def test__should_show_kill_confirmation_dialog(self, kill_dialog_mock):
        num_procs = 2
        min_runtime = 90
        max_runtime = 105
        expected_proc_search = opencue.search.ProcSearch(
            allocs=self.tag_names, jobs=self.job_names, maxResults=[num_procs],
            durationRange=[opencue_proto.criterion_pb2.InRangeIntegerSearchCriterion(
                min=min_runtime*60, max=max_runtime*60)])
        kill_dialog_mock.return_value.result.return_value = True

        self.dialog.open()
        self.dialog._UnbookDialog__amount.setValue(num_procs)
        self.dialog._UnbookDialog__kill.setChecked(True)
        self.dialog._UnbookDialog__runtimeRangeBox._RangeBox__group.setChecked(True)
        self.dialog._UnbookDialog__runtimeRangeBox._RangeBox__range.setChecked(True)
        self.dialog._UnbookDialog__runtimeRangeBox._RangeBox__min.setValue(min_runtime)
        self.dialog._UnbookDialog__runtimeRangeBox._RangeBox__max.setValue(max_runtime)
        self.dialog.accept()

        kill_dialog_mock.assert_called_with(expected_proc_search, mock.ANY)

    @mock.patch('qtpy.QtWidgets.QMessageBox', new=mock.Mock())
    @mock.patch('opencue.api.getProcs')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.getActiveShows')
    def test__should_redirect_proc_to_group(
            self, get_active_shows_mock, get_item_mock, get_procs_mock):
        num_procs = 50
        other_show_name = 'some-other-show'
        group_name = 'group-to-redirect-to'
        show = opencue.wrappers.show.Show(
            opencue_proto.show_pb2.Show(name=other_show_name))
        group = opencue.wrappers.group.Group(opencue_proto.job_pb2.Group(name=group_name))
        show.getGroups = mock.Mock()
        show.getGroups.return_value = [group]
        get_active_shows_mock.return_value = [show]
        get_item_mock.side_effect = [(other_show_name, True), ('Group', True), (group_name, True)]
        expected_proc_search = opencue.search.ProcSearch(
            allocs=self.tag_names, jobs=self.job_names, maxResults=[num_procs])
        proc_to_redirect = opencue.wrappers.proc.Proc()
        proc_to_redirect.redirectToGroup = mock.Mock()
        get_procs_mock.return_value = [proc_to_redirect]

        self.dialog.open()
        self.dialog._UnbookDialog__amount.setValue(num_procs)
        self.dialog._UnbookDialog__redirect.setChecked(True)
        self.dialog.accept()

        get_procs_mock.assert_called_with(**expected_proc_search.options)
        proc_to_redirect.redirectToGroup.assert_called_with(group, False)

    @mock.patch('qtpy.QtWidgets.QMessageBox', new=mock.Mock())
    @mock.patch('opencue.api.getProcs')
    @mock.patch('cuegui.UnbookDialog.SelectItemsWithSearchDialog')
    @mock.patch('opencue.api.getJobs')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.getActiveShows')
    def test__should_redirect_proc_to_job(
            self, get_active_shows_mock, get_item_mock, get_jobs_mock, select_job_mock,
            get_procs_mock):
        num_procs = 50
        other_show_name = 'some-other-show'
        job_name = 'job-to-redirect-to'
        show = opencue.wrappers.show.Show(
            opencue_proto.show_pb2.Show(name=other_show_name))
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=job_name))
        get_active_shows_mock.return_value = [show]
        get_item_mock.side_effect = [(other_show_name, True), ('Job', True)]
        get_jobs_mock.return_value = [job]
        select_job_mock.return_value.selected.return_value = [job_name]
        expected_proc_search = opencue.search.ProcSearch(
            allocs=self.tag_names, jobs=self.job_names, maxResults=[num_procs])
        proc_to_redirect = opencue.wrappers.proc.Proc()
        proc_to_redirect.redirectToJob = mock.Mock()
        get_procs_mock.return_value = [proc_to_redirect]

        self.dialog.open()
        self.dialog._UnbookDialog__amount.setValue(num_procs)
        self.dialog._UnbookDialog__redirect.setChecked(True)
        self.dialog.accept()

        get_procs_mock.assert_called_with(**expected_proc_search.options)
        proc_to_redirect.redirectToJob.assert_called_with(job, False)


class SelectItemsWithSearchDialogTests(unittest.TestCase):

    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

    def test__should_display_all_items(self):
        items_to_be_shown = ['item1', 'item2', 'item3']

        dialog = cuegui.UnbookDialog.SelectItemsWithSearchDialog(None, 'header', items_to_be_shown)
        dialog.open()

        item_list = dialog._SelectItemsWithSearchDialog__widget._SelectItemsWithSearchWidget__list
        all_items_shown = [item_list.item(x).text() for x in range(item_list.count())]
        self.assertEqual(items_to_be_shown, all_items_shown)

    def test__should_filter_items(self):
        initial_item_list = ['item1', 'itemSubstr2', 'item3', 'itemsubstr4']

        dialog = cuegui.UnbookDialog.SelectItemsWithSearchDialog(None, 'header', initial_item_list)
        dialog.open()
        dialog._SelectItemsWithSearchDialog__widget._SelectItemsWithSearchWidget__filter.setText(
            'substr')

        item_list = dialog._SelectItemsWithSearchDialog__widget._SelectItemsWithSearchWidget__list
        items_shown = [item_list.item(x).text() for x in range(item_list.count())]
        self.assertEqual(['itemSubstr2', 'itemsubstr4'], items_shown)

    def test__should_return_selected_items(self):
        initial_item_list = ['item1', 'item2', 'item3', 'item4']

        dialog = cuegui.UnbookDialog.SelectItemsWithSearchDialog(None, 'header', initial_item_list)
        dialog.open()
        item_list = dialog._SelectItemsWithSearchDialog__widget._SelectItemsWithSearchWidget__list
        item_list.item(1).setSelected(True)
        item_list.item(2).setSelected(True)
        dialog.accept()

        self.assertEqual(['item2', 'item3'], dialog.selected())


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class KillConfirmationDialogTests(unittest.TestCase):

    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

    @mock.patch('qtpy.QtWidgets.QMessageBox.information', new=mock.Mock())
    @mock.patch('opencue.api.getProcs')
    def test__should_kill_procs(self, get_procs_mock):
        proc_search = opencue.search.ProcSearch(
            allocs=['tag1', 'tag2'], jobs=['someJob', 'anotherJob'], maxResults=[57])
        proc1 = opencue.wrappers.proc.Proc(
            opencue_proto.host_pb2.Proc(job_name='someJob', frame_name='0002'))
        proc1.kill = mock.Mock()
        proc2 = opencue.wrappers.proc.Proc(
            opencue_proto.host_pb2.Proc(job_name='anotherJob', frame_name='2847'))
        proc2.kill = mock.Mock()
        get_procs_mock.return_value = [proc1, proc2]

        dialog = cuegui.UnbookDialog.KillConfirmationDialog(proc_search)
        dialog.accept()

        proc1.kill.assert_called()
        proc2.kill.assert_called()

    @mock.patch('qtpy.QtWidgets.QMessageBox.information', new=mock.Mock())
    @mock.patch('opencue.api.getProcs')
    def test__should_cancel_kill(self, get_procs_mock):
        proc_search = opencue.search.ProcSearch(
            allocs=['tag1', 'tag2'], jobs=['someJob', 'anotherJob'], maxResults=[57])
        proc1 = opencue.wrappers.proc.Proc(
            opencue_proto.host_pb2.Proc(job_name='someJob', frame_name='0002'))
        proc1.kill = mock.Mock()
        proc2 = opencue.wrappers.proc.Proc(
            opencue_proto.host_pb2.Proc(job_name='anotherJob', frame_name='2847'))
        proc2.kill = mock.Mock()
        get_procs_mock.return_value = [proc1, proc2]

        dialog = cuegui.UnbookDialog.KillConfirmationDialog(proc_search)
        dialog.reject()

        proc1.kill.assert_not_called()
        proc2.kill.assert_not_called()
