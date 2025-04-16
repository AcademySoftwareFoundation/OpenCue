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


"""Tests for cuegui.MenuActions."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import unittest

import getpass
import mock
import qtpy.QtGui
import qtpy.QtWidgets

import opencue_proto.depend_pb2
import opencue_proto.facility_pb2
import opencue_proto.filter_pb2
import opencue_proto.host_pb2
import opencue_proto.job_pb2
import opencue_proto.limit_pb2
import opencue_proto.subscription_pb2
import opencue_proto.task_pb2
import opencue.wrappers.allocation
import opencue.wrappers.depend
import opencue.wrappers.filter
import opencue.wrappers.frame
import opencue.wrappers.group
import opencue.wrappers.host
import opencue.wrappers.job
import opencue.wrappers.layer
import opencue.wrappers.limit
import opencue.wrappers.proc
import opencue.wrappers.show
import opencue.wrappers.subscription
import opencue.wrappers.task

import cuegui.Constants
import cuegui.CueJobMonitorTree
import cuegui.Main
import cuegui.MenuActions
from . import test_utils

_GB_TO_KB = 1024 * 1024


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class JobActionsTests(unittest.TestCase):
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.job_actions = cuegui.MenuActions.JobActions(self.widgetMock, mock.Mock(), None, None)

    def test_jobs(self):
        cuegui.MenuActions.MenuActions(self.widgetMock, None, None, None).jobs()

    def test_unmonitor(self):
        self.job_actions.unmonitor()

        self.widgetMock.actionRemoveSelectedItems.assert_called_with()

    def test_view(self):
        self.app.view_object = mock.Mock()
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=job_name))

        self.job_actions.view(rpcObjects=[job, opencue.wrappers.frame.Frame()])

        self.app.view_object.emit.assert_called_once_with(job)

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=job_name))

        self.job_actions.viewDepends(rpcObjects=[job])

        dependDialogMock.assert_called_with(job, self.widgetMock)
        dependDialogMock.return_value.show.assert_called()

    @mock.patch('cuegui.EmailDialog.EmailDialog')
    def test_emailArtist(self, emailDialogMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=job_name))

        self.job_actions.emailArtist(rpcObjects=[job])

        emailDialogMock.assert_called_with([job], self.widgetMock)
        emailDialogMock.return_value.show.assert_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock):
        highest_current_core_count = 20
        new_core_count = 50
        job1 = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(min_cores=highest_current_core_count - 10))
        job1.setMinCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(min_cores=highest_current_core_count))
        job2.setMinCores = mock.Mock()
        getDoubleMock.return_value = (new_core_count, True)

        self.job_actions.setMinCores(rpcObjects=[job1, job2])

        # Default value should be the highest core count of all jobs passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        job1.setMinCores.assert_called_with(new_core_count)
        job2.setMinCores.assert_called_with(new_core_count)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinCoresCanceled(self, getDoubleMock):
        job1 = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(min_cores=0))
        job1.setMinCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(min_cores=0))
        job2.setMinCores = mock.Mock()
        getDoubleMock.return_value = (None, False)

        self.job_actions.setMinCores(rpcObjects=[job1, job2])

        job1.setMinCores.assert_not_called()
        job2.setMinCores.assert_not_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMaxCores(self, getDoubleMock):
        highest_current_core_count = 20
        new_core_count = 50
        job1 = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(max_cores=highest_current_core_count - 10))
        job1.setMaxCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(max_cores=highest_current_core_count))
        job2.setMaxCores = mock.Mock()
        getDoubleMock.return_value = (new_core_count, True)

        self.job_actions.setMaxCores(rpcObjects=[job1, job2])

        # Default value should be the highest core count of all jobs passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        job1.setMaxCores.assert_called_with(new_core_count)
        job2.setMaxCores.assert_called_with(new_core_count)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMaxCoresCanceled(self, getDoubleMock):
        job1 = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(max_cores=0))
        job1.setMaxCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(max_cores=0))
        job2.setMaxCores = mock.Mock()
        getDoubleMock.return_value = (None, False)

        self.job_actions.setMaxCores(rpcObjects=[job1, job2])

        job1.setMaxCores.assert_not_called()
        job2.setMaxCores.assert_not_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    def test_setPriority(self, getIntMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(priority=0))
        job.setPriority = mock.Mock()
        new_priority = 25
        getIntMock.return_value = (new_priority, True)

        self.job_actions.setPriority(rpcObjects=[job])

        job.setPriority.assert_called_with(new_priority)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    def test_setPriorityCanceled(self, getIntMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(priority=0))
        job.setPriority = mock.Mock()
        getIntMock.return_value = (None, False)

        self.job_actions.setPriority(rpcObjects=[job])

        job.setPriority.assert_not_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    def test_setMaxRetries(self, getIntMock):
        job = opencue.wrappers.job.Job()
        job.setMaxRetries = mock.Mock()
        new_retries = 7
        getIntMock.return_value = (new_retries, True)

        self.job_actions.setMaxRetries(rpcObjects=[job])

        job.setMaxRetries.assert_called_with(new_retries)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    def test_setMaxRetriesCanceled(self, getIntMock):
        job = opencue.wrappers.job.Job()
        job.setMaxRetries = mock.Mock()
        getIntMock.return_value = (None, False)

        self.job_actions.setMaxRetries(rpcObjects=[job])

        job.setMaxRetries.assert_not_called()

    def test_pause(self):
        job = opencue.wrappers.job.Job()
        job.pause = mock.Mock()

        self.job_actions.pause(rpcObjects=[job])

        job.pause.assert_called()

    def test_resume(self):
        job = opencue.wrappers.job.Job()
        job.resume = mock.Mock()

        self.job_actions.resume(rpcObjects=[job])

        job.resume.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_kill(self, isPermissibleMock, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.kill = mock.Mock()
        job.getWhatDependsOnThis = mock.Mock()
        job.getWhatDependsOnThis.return_value = []

        self.job_actions.kill(rpcObjects=[job])

        job.kill.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_killCanceled(self, isPermissibleMock, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.kill = mock.Mock()

        self.job_actions.kill(rpcObjects=[job])

        job.kill.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_eatDead(self, isPermissibleMock, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.eatFrames = mock.Mock()

        self.job_actions.eatDead(rpcObjects=[job])

        job.eatFrames.assert_called_with(state=[opencue_proto.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_eatDeadCanceled(self, isPermissibleMock, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.eatFrames = mock.Mock()

        self.job_actions.eatDead(rpcObjects=[job])

        job.eatFrames.assert_not_called()

    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_autoEatOn(self, isPermissibleMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.setAutoEat = mock.Mock()
        job.eatFrames = mock.Mock()

        self.job_actions.autoEatOn(rpcObjects=[job])

        job.setAutoEat.assert_called_with(True)
        job.eatFrames.assert_called_with(state=[opencue_proto.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_autoEatOff(self, isPermissibleMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.setAutoEat = mock.Mock()

        self.job_actions.autoEatOff(rpcObjects=[job])

        job.setAutoEat.assert_called_with(False)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_retryDead(self, isPermissibleMock, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.retryFrames = mock.Mock()

        self.job_actions.retryDead(rpcObjects=[job])

        job.retryFrames.assert_called_with(state=[opencue_proto.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_retryDeadCanceled(self, isPermissibleMock, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.retryFrames = mock.Mock()

        self.job_actions.retryDead(rpcObjects=[job])

        job.retryFrames.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropExternalDependencies(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropExternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_called_with(opencue.api.depend_pb2.EXTERNAL)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_dropExternalDependenciesCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropExternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropInternalDependencies(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropInternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_called_with(opencue.api.depend_pb2.INTERNAL)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_dropInternalDependenciesCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropInternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_not_called()

    @mock.patch('cuegui.Comments.CommentListDialog')
    def test_viewComments(self, commentListMock):
        job = opencue.wrappers.job.Job()

        self.job_actions.viewComments(rpcObjects=[job])

        commentListMock.assert_called_with([job], self.widgetMock)
        commentListMock.return_value.show.assert_called()

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        jobs = [opencue.wrappers.job.Job()]

        self.job_actions.dependWizard(rpcObjects=jobs)

        dependWizardMock.assert_called_with(self.widgetMock, jobs)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_reorder(self, getTextMock, getItemMock):
        original_range = '1-10'
        new_order = 'REVERSE'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(range=original_range))]
        job.reorderFrames = mock.Mock()
        getTextMock.return_value = (original_range, True)
        getItemMock.return_value = (new_order, True)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_called_with(original_range, opencue_proto.job_pb2.REVERSE)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_reorderCanceled(self, getTextMock, getItemMock):
        original_range = '1-10'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(range=original_range))]
        job.reorderFrames = mock.Mock()

        getTextMock.return_value = (None, False)
        getItemMock.return_value = (None, True)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_not_called()

        getTextMock.return_value = (None, True)
        getItemMock.return_value = (None, False)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_not_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_stagger(self, getTextMock, getIntMock):
        original_range = '1-10'
        new_step = 28
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(range=original_range))]
        job.staggerFrames = mock.Mock()
        getTextMock.return_value = (original_range, True)
        getIntMock.return_value = (new_step, True)

        self.job_actions.stagger(rpcObjects=[job])

        job.staggerFrames.assert_called_with(original_range, new_step)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_staggerCanceled(self, getTextMock, getIntMock):
        original_range = '1-10'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue_proto.job_pb2.Layer(range=original_range))]
        job.staggerFrames = mock.Mock()
        getTextMock.return_value = (None, False)
        getIntMock.return_value = (None, True)

        self.job_actions.stagger(rpcObjects=[job])

        job.staggerFrames.assert_not_called()

        getTextMock.return_value = (None, True)
        getIntMock.return_value = (None, False)

        self.job_actions.stagger(rpcObjects=[job])

        job.staggerFrames.assert_not_called()

    @mock.patch('cuegui.UnbookDialog.UnbookDialog')
    def test_unbook(self, unbookDialogMock):
        jobs = [opencue.wrappers.job.Job()]

        self.job_actions.unbook(rpcObjects=jobs)

        unbookDialogMock.assert_called_with(jobs, self.widgetMock)
        unbookDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.CueJobMonitorTree.MoveDialog.move_items')
    @mock.patch('opencue.api.findShow')
    def test_sendToGroup(self, findShowMock, move_itemsMock):

        move_dialogMock = mock.Mock()

        move_dialogMock.open()
        group_name = 'arbitrary-group-name'
        job = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(
                name='arbitrary-job-name', show='arbitrary-show-name'))
        body_content = cuegui.CueJobMonitorTree.Body(group_names=[],
                                                     group_ids=[],
                                                     job_names=[job.name()],
                                                     job_ids=[job])

        group = opencue.wrappers.group.Group(opencue_proto.job_pb2.Group(name=group_name))
        group.reparentJobs = mock.Mock()

        show = opencue.wrappers.show.Show()
        findShowMock.return_value = show
        show.getGroups = mock.Mock(return_value=[group])

        move_dialogMock.dst_groups = {str(group_name): group}
        move_itemsMock.return_value = move_dialogMock.dst_groups[str(group_name)].reparentJobs(
                body_content.job_ids)
        move_dialogMock.accept()

        group.reparentJobs.assert_called_with(body_content.job_ids)

    @mock.patch('cuegui.CueJobMonitorTree.MoveDialog.move_items')
    @mock.patch('opencue.api.findShow')
    def test_sendToGroupCanceled(self, findShowMock, move_itemsMock):

        move_dialogMock = mock.Mock()

        move_dialogMock.open()
        group_name = 'arbitrary-group-name'
        job = opencue.wrappers.job.Job(
            opencue_proto.job_pb2.Job(
                name='arbitrary-job-name', show='arbitrary-show-name'))
        group = opencue.wrappers.group.Group(opencue_proto.job_pb2.Group(name=group_name))
        group.reparentJobs = mock.Mock()

        show = opencue.wrappers.show.Show()
        findShowMock.return_value = show
        show.getGroups = mock.Mock(return_value=[group])
        move_itemsMock.return_value = (None, False)
        move_dialogMock.reject()

        group.reparentJobs.assert_not_called()

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        job = opencue.wrappers.job.Job()

        self.job_actions.useLocalCores(rpcObjects=[job])

        localBookingDialogMock.assert_called_with(job, self.widgetMock)
        localBookingDialogMock.return_value.exec_.assert_called()

    @mock.patch('qtpy.QtWidgets.QApplication.clipboard')
    def test_copyLogFileDir(self, clipboardMock):
        logDir1 = '/some/random/dir'
        logDir2 = '/a/different/random/dir'
        job1 = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(log_dir=logDir1))
        job2 = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(log_dir=logDir2))

        self.job_actions.copyLogFileDir(rpcObjects=[job1, job2])

        clipboardMock.return_value.setText.assert_called_with(
            "%s %s" % (logDir1, logDir2), mock.ANY)

    def test_setUserColor(self):
        self.job_actions.setUserColor1()
        self.widgetMock.actionSetUserColor.assert_called_once_with(cuegui.Constants.COLOR_USER_1)
        self.widgetMock.actionSetUserColor.reset_mock()

        self.job_actions.setUserColor2()
        self.widgetMock.actionSetUserColor.assert_called_once_with(cuegui.Constants.COLOR_USER_2)
        self.widgetMock.actionSetUserColor.reset_mock()

        self.job_actions.setUserColor3()
        self.widgetMock.actionSetUserColor.assert_called_once_with(cuegui.Constants.COLOR_USER_3)
        self.widgetMock.actionSetUserColor.reset_mock()

        self.job_actions.setUserColor4()
        self.widgetMock.actionSetUserColor.assert_called_once_with(cuegui.Constants.COLOR_USER_4)
        self.widgetMock.actionSetUserColor.reset_mock()

        self.job_actions.clearUserColor()
        self.widgetMock.actionSetUserColor.assert_called_once_with(None)
        self.widgetMock.actionSetUserColor.reset_mock()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class LayerActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.job = mock.create_autospec(opencue.wrappers.job.Job())
        self.layer_actions = cuegui.MenuActions.LayerActions(
            self.widgetMock, mock.Mock(), None, lambda: self.job)

    def test_view(self):
        layer_name = 'arbitrary-name'
        layer = opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer(name=layer_name))

        self.layer_actions.view(rpcObjects=[layer, opencue.wrappers.frame.Frame()])

        self.widgetMock.handle_filter_layers_byLayer.emit.assert_called_with([layer_name])

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.viewDepends(rpcObjects=[layer])

        dependDialogMock.assert_called_with(layer, self.widgetMock)
        dependDialogMock.return_value.show.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinCores', autospec=True)
    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock, setMinCoresMock):
        highest_current_core_count = 20
        new_core_count = 50
        layer1 = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(min_cores=highest_current_core_count - 10))
        layer2 = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(min_cores=highest_current_core_count))
        getDoubleMock.return_value = (new_core_count, True)

        self.layer_actions.setMinCores(rpcObjects=[layer1, layer2])

        # Default value should be the highest core count of all layers passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        setMinCoresMock.assert_has_calls([
            mock.call(layer1, new_core_count), mock.call(layer2, new_core_count)])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinCores')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinCoresCanceled(self, getDoubleMock, setMinCoresMock):
        layer1 = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(min_cores=0))
        layer2 = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(min_cores=0))
        getDoubleMock.return_value = (None, False)

        self.layer_actions.setMinCores(rpcObjects=[layer1, layer2])

        setMinCoresMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinMemory', autospec=True)
    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinMemoryKb(self, getDoubleMock, setMinMemoryMock):
        highest_current_mem_limit_gb = 20
        new_mem_limit_gb = 50
        layer1 = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(
                min_memory=(highest_current_mem_limit_gb - 10) * _GB_TO_KB))
        layer2 = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(
                min_memory=highest_current_mem_limit_gb * _GB_TO_KB))
        getDoubleMock.return_value = (new_mem_limit_gb, True)

        self.layer_actions.setMinMemoryKb(rpcObjects=[layer1, layer2])

        # Default value should be the highest core count of all layers passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_mem_limit_gb, mock.ANY, mock.ANY,
            mock.ANY)

        setMinMemoryMock.assert_has_calls([
            mock.call(layer1, new_mem_limit_gb * _GB_TO_KB),
            mock.call(layer2, new_mem_limit_gb * _GB_TO_KB),
        ])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinMemory')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinMemoryKbCanceled(self, getDoubleMock, setMinMemoryMock):
        layer1 = opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer(min_memory=0))
        layer2 = opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer(min_memory=0))
        getDoubleMock.return_value = (None, False)

        self.layer_actions.setMinMemoryKb(rpcObjects=[layer1, layer2])

        setMinMemoryMock.assert_not_called()

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        layer = opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer())

        self.layer_actions.useLocalCores(rpcObjects=[layer])

        localBookingDialogMock.assert_called_with(layer, self.widgetMock)
        localBookingDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.LayerDialog.LayerPropertiesDialog')
    def test_setProperties(self, layerPropertiesDialogMock):
        layers = [opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer())]

        self.layer_actions.setProperties(rpcObjects=layers)

        layerPropertiesDialogMock.assert_called_with(layers)
        layerPropertiesDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.LayerDialog.LayerTagsDialog')
    def test_setTags(self, layerTagsDialogMock):
        layers = [opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer())]

        self.layer_actions.setTags(rpcObjects=layers)

        layerTagsDialogMock.assert_called_with(layers)
        layerTagsDialogMock.return_value.exec_.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'kill')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_kill(self, isPermissibleMock, yesNoMock, killMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.kill(rpcObjects=[layer])

        killMock.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'kill')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_killCanceled(self, isPermissibleMock, yesNoMock, killMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.kill(rpcObjects=[layer])

        killMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'eat')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_eat(self, isPermissibleMock, yesNoMock, eatMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.eat(rpcObjects=[layer])

        eatMock.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'eat')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_eatCanceled(self, isPermissibleMock, yesNoMock, eatMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.eat(rpcObjects=[layer])

        eatMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'retry', autospec=True)
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_retry(self, isPermissibleMock, yesNoMock, retryMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.retry(rpcObjects=[layer])

        retryMock.assert_called_with(layer)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'retry')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_retryCanceled(self, isPermissibleMock, yesNoMock, retryMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.retry(rpcObjects=[layer])

        retryMock.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_retryDead(self, isPermissibleMock, yesNoMock):
        layer_name = 'arbitrary-name'
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name=layer_name))
        layer.parent = lambda : self.job

        self.layer_actions.retryDead(rpcObjects=[layer])

        self.job.retryFrames.assert_called_with(
            layer=[layer_name], state=[opencue.api.job_pb2.DEAD])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'markdone', autospec=True)
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markdone(self, yesNoMock, markdoneMock):
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.markdone(rpcObjects=[layer])

        markdoneMock.assert_called_with(layer)

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        layers = [opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer())]

        self.layer_actions.dependWizard(rpcObjects=layers)

        dependWizardMock.assert_called_with(self.widgetMock, [self.job], layers=layers)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'reorderFrames', autospec=True)
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_reorder(self, getTextMock, getItemMock, reorderFramesMock):
        original_range = '1-10'
        new_order = 'REVERSE'
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(range=original_range))

        getTextMock.return_value = (original_range, True)
        getItemMock.return_value = (new_order, True)

        self.layer_actions.reorder(rpcObjects=[layer])

        reorderFramesMock.assert_called_with(
            layer, original_range, opencue_proto.job_pb2.REVERSE)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'staggerFrames', autospec=True)
    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_stagger(self, getTextMock, getIntMock, staggerFramesMock):
        original_range = '1-10'
        new_step = 28
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(range=original_range))
        getTextMock.return_value = (original_range, True)
        getIntMock.return_value = (new_step, True)

        self.layer_actions.stagger(rpcObjects=[layer])

        staggerFramesMock.assert_called_with(layer, original_range, new_step)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FrameActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.job = mock.create_autospec(opencue.wrappers.job.Job())
        self.frame_actions = cuegui.MenuActions.FrameActions(
            self.widgetMock, mock.Mock(), None, lambda: self.job)

    @mock.patch('cuegui.Utils.popupFrameView')
    def test_view(self, popupFrameViewMock):
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.view(rpcObjects=[opencue.wrappers.layer.Layer(), frame])

        popupFrameViewMock.assert_called_with(self.job, frame)

    @mock.patch('cuegui.Utils.popupFrameTail')
    def test_tail(self, popupFrameTailMock):
        frame = opencue.wrappers.frame.Frame(None)

        self.frame_actions.tail(rpcObjects=[frame])

        popupFrameTailMock.assert_called_with(self.job, frame)

    @mock.patch('cuegui.Utils.popupView')
    @mock.patch('glob.glob')
    @mock.patch('cuegui.Utils.getFrameLogFile')
    def test_viewLastLog(self, getFrameLogFileMock, globMock, popupViewMock):
        frame_log_path = '/some/path/to/job/logs/job-name.frame-name.rqlog'
        getFrameLogFileMock.return_value = frame_log_path
        file_list = ['{}/file1.0001'.format(frame_log_path), '{}/file2.0002'.format(frame_log_path)]
        globMock.return_value = file_list
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.viewLastLog(rpcObjects=[frame])

        popupViewMock.assert_called_with(file_list[-1])

    @mock.patch('cuegui.Utils.popupView')
    @mock.patch('glob.glob')
    @mock.patch('cuegui.Utils.getFrameLogFile')
    def test_viewLastLogNoFiles(self, getFrameLogFileMock, globMock, popupViewMock):
        frame_log_path = '/some/path/to/job/logs/job-name.frame-name.rqlog'
        getFrameLogFileMock.return_value = frame_log_path
        globMock.return_value = []
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.viewLastLog(rpcObjects=[frame])

        popupViewMock.assert_called_with(frame_log_path)

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.useLocalCores(rpcObjects=[frame])

        localBookingDialogMock.assert_called_with(frame, self.widgetMock)
        localBookingDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.Utils.popupFrameXdiff')
    def test_xdiff2(self, popupFrameXdiffMock):
        frame1 = opencue.wrappers.frame.Frame()
        frame2 = opencue.wrappers.frame.Frame()

        self.frame_actions.xdiff2(rpcObjects=[frame1, frame2])

        popupFrameXdiffMock.assert_called_with(self.job, frame1, frame2)

    @mock.patch('cuegui.Utils.popupFrameXdiff')
    def test_xdiff3(self, popupFrameXdiffMock):
        frame1 = opencue.wrappers.frame.Frame()
        frame2 = opencue.wrappers.frame.Frame()
        frame3 = opencue.wrappers.frame.Frame()

        self.frame_actions.xdiff3(rpcObjects=[frame1, frame2, frame3])

        popupFrameXdiffMock.assert_called_with(self.job, frame1, frame2, frame3)

    @mock.patch('opencue.api.findHost')
    def test_viewHost(self, findHostMock):
        self.app.view_hosts = mock.Mock()
        self.app.single_click = mock.Mock()
        host_name = 'arbitrary-host-name'
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id', name=host_name))
        frame = opencue.wrappers.frame.Frame(
            opencue_proto.job_pb2.Frame(last_resource='{}/foo'.format(host_name)))
        findHostMock.return_value = host

        self.frame_actions.viewHost(rpcObjects=[frame])

        self.app.view_hosts.emit.assert_called_with([host_name])
        self.app.single_click.emit.assert_called_with(host)

    def test_getWhatThisDependsOn(self):
        frame = opencue.wrappers.frame.Frame()
        depend = opencue.wrappers.depend.Depend(opencue_proto.depend_pb2.Depend())
        frame.getWhatThisDependsOn = lambda: [depend]

        # This method just logs info so no return value to check; just make sure it executes.
        self.frame_actions.getWhatThisDependsOn(rpcObjects=[frame])

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.viewDepends(rpcObjects=[frame])

        dependDialogMock.assert_called_with(frame, self.widgetMock)
        dependDialogMock.return_value.show.assert_called()

    def test_getWhatDependsOnThis(self):
        frame = opencue.wrappers.frame.Frame()
        depend = opencue.wrappers.depend.Depend(opencue_proto.depend_pb2.Depend())
        frame.getWhatDependsOnThis = lambda: [depend]

        # This method just logs info so no return value to check; just make sure it executes.
        self.frame_actions.getWhatDependsOnThis(rpcObjects=[frame])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_retry(self, isPermissibleMock, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.retry(rpcObjects=[frame])

        self.job.retryFrames.assert_called_with(name=[frame_name])

    @mock.patch('cuegui.PreviewWidget.PreviewProcessorDialog')
    def test_previewMain(self, previewProcessorDialogMock):
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.previewMain(rpcObjects=[frame])

        previewProcessorDialogMock.assert_called_with(self.job, frame, False)
        previewProcessorDialogMock.return_value.process.assert_called()
        previewProcessorDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.PreviewWidget.PreviewProcessorDialog')
    def test_previewAovs(self, previewProcessorDialogMock):
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.previewAovs(rpcObjects=[frame])

        previewProcessorDialogMock.assert_called_with(self.job, frame, True)
        previewProcessorDialogMock.return_value.process.assert_called()
        previewProcessorDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_eat(self, isPermissibleMock, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.eat(rpcObjects=[frame])

        self.job.eatFrames.assert_called_with(name=[frame_name])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_kill(self, isPermissibleMock, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.kill(rpcObjects=[frame])
        username = getpass.getuser()
        self.job.killFrames.assert_called_with(
            name=[frame_name],
            reason="Manual Frame(s) Kill Request in Cuegui by %s" % username)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markAsWaiting(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.markAsWaiting(rpcObjects=[frame])

        self.job.markAsWaiting.assert_called_with(name=[frame_name])

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        frames = [opencue.wrappers.frame.Frame()]

        self.frame_actions.dependWizard(rpcObjects=frames)

        dependWizardMock.assert_called_with(self.widgetMock, [self.job], frames=frames)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markdone(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.markdone(rpcObjects=[frame])

        self.job.markdoneFrames.assert_called_with(name=[frame_name])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'reorderFrames', autospec=True)
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_reorder(self, getItemMock, reorderFramesMock):
        new_order = 'REVERSE'
        getItemMock.return_value = (new_order, True)
        layer_name = 'arbitrary-layer-name'
        frame_num = 28
        frame = opencue.wrappers.frame.Frame(
            opencue_proto.job_pb2.Frame(layer_name=layer_name, number=frame_num))
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(name=layer_name))
        self.job.getLayers.return_value = [layer]

        self.frame_actions.reorder(rpcObjects=[frame])

        reorderFramesMock.assert_called_with(
            layer, str(frame_num), opencue_proto.job_pb2.REVERSE)

    @mock.patch('qtpy.QtWidgets.QApplication.clipboard')
    @mock.patch('cuegui.Utils.getFrameLogFile')
    def test_copyLogFileName(self, getFrameLogFileMock, clipboardMock):
        frame_log_path = '/some/path/to/job/logs/job-name.frame-name.rqlog'
        getFrameLogFileMock.return_value = frame_log_path
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.copyLogFileName(rpcObjects=[frame])

        clipboardMock.return_value.setText.assert_called_with([frame_log_path], mock.ANY)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'markdone', autospec=True)
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_eatandmarkdone(self, isPermissibleMock, yesNoMock, markdoneMock):
        layer_name = 'layer-name'
        frames = [
            opencue.wrappers.frame.Frame(
                opencue_proto.job_pb2.Frame(name='frame1', layer_name=layer_name)),
            opencue.wrappers.frame.Frame(
                opencue_proto.job_pb2.Frame(name='frame2', layer_name=layer_name))]
        layer = opencue.wrappers.layer.Layer(
            opencue_proto.job_pb2.Layer(
                name=layer_name, layer_stats=opencue_proto.job_pb2.LayerStats(
                    eaten_frames=7, succeeded_frames=3, total_frames=10)))
        self.job.getLayers.return_value = [layer]

        self.frame_actions.eatandmarkdone(rpcObjects=frames)

        self.job.eatFrames.assert_called_with(name=['frame1', 'frame2'])
        self.job.markdoneFrames.assert_called_with(name=['frame1', 'frame2'])
        markdoneMock.assert_called_with(layer)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class ShowActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.show_actions = cuegui.MenuActions.ShowActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('cuegui.ShowDialog.ShowDialog')
    def test_properties(self, showDialogMock):
        show = opencue.wrappers.show.Show()

        self.show_actions.properties(rpcObjects=[opencue.wrappers.layer.Layer(), show])

        showDialogMock.assert_called_with(show, mock.ANY)
        showDialogMock.return_value.show.assert_called()

    @mock.patch('cuegui.CreatorDialog.SubscriptionCreatorDialog')
    def test_createSubscription(self, subscriptionCreatorDialogMock):
        show = opencue.wrappers.show.Show()

        self.show_actions.createSubscription(rpcObjects=[opencue.wrappers.layer.Layer(), show])

        subscriptionCreatorDialogMock.assert_called_with(show=show)
        subscriptionCreatorDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.TasksDialog.TasksDialog')
    def test_viewTasks(self, tasksDialogMock):
        show = opencue.wrappers.show.Show()

        self.show_actions.viewTasks(rpcObjects=[opencue.wrappers.layer.Layer(), show])

        tasksDialogMock.assert_called_with(show, mock.ANY)
        tasksDialogMock.return_value.show.assert_called()

@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class GroupActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.group_actions = cuegui.MenuActions.GroupActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('cuegui.GroupDialog.ModifyGroupDialog')
    def test_properties(self, modifyGroupDialogMock):
        group = opencue.wrappers.group.Group(group=opencue_proto.job_pb2.Group())

        self.group_actions.properties(rpcObjects=[opencue.wrappers.layer.Layer(), group])

        modifyGroupDialogMock.assert_called_with(group, mock.ANY)
        modifyGroupDialogMock.return_value.show.assert_called()

    @mock.patch('cuegui.GroupDialog.NewGroupDialog')
    def test_createGroup(self, newGroupDialogMock):
        group = opencue.wrappers.group.Group(group=opencue_proto.job_pb2.Group())

        self.group_actions.createGroup(rpcObjects=[opencue.wrappers.layer.Layer(), group])

        newGroupDialogMock.assert_called_with(group, mock.ANY)
        newGroupDialogMock.return_value.show.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_deleteGroup(self):
        group = opencue.wrappers.group.Group(group=opencue_proto.job_pb2.Group())
        group.delete = mock.MagicMock()

        self.group_actions.deleteGroup(rpcObjects=[opencue.wrappers.layer.Layer(), group])

        group.delete.assert_called()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class SubscriptionActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.subscription_actions = cuegui.MenuActions.SubscriptionActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('qtpy.QtWidgets.QMessageBox')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_editSize(self, getDoubleMock, qMessageBoxMock):
        sub = opencue.wrappers.subscription.Subscription(
            opencue_proto.subscription_pb2.Subscription(size=382))
        sub.setSize = mock.MagicMock()
        newSize = 8479
        getDoubleMock.return_value = (newSize, True)
        qMessageBoxMock.return_value.exec_.return_value = qtpy.QtWidgets.QMessageBox.Yes

        self.subscription_actions.editSize(rpcObjects=[sub])

        sub.setSize.assert_called_with(newSize*100.0)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_editBurst(self, getDoubleMock):
        sub = opencue.wrappers.subscription.Subscription(
            opencue_proto.subscription_pb2.Subscription(burst=922))
        sub.setBurst = mock.MagicMock()
        newSize = 1078
        getDoubleMock.return_value = (newSize, True)

        self.subscription_actions.editBurst(rpcObjects=[sub])

        sub.setBurst.assert_called_with(newSize*100.0)

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        sub = opencue.wrappers.subscription.Subscription(
            opencue_proto.subscription_pb2.Subscription(name='arbitrary-name'))
        sub.delete = mock.MagicMock()

        self.subscription_actions.delete(rpcObjects=[sub])

        sub.delete.assert_called()


class AllocationActionsTests(unittest.TestCase):
    # pylint: disable=attribute-defined-outside-init
    def test_init(self):
        self.widgetMock = mock.Mock()
        cuegui.MenuActions.AllocationActions(self.widgetMock, mock.Mock(), None, None)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class HostActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.host_actions = cuegui.MenuActions.HostActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('cuegui.Comments.CommentListDialog')
    def test_viewComments(self, commentListDialogMock):
        host = opencue.wrappers.host.Host(opencue_proto.host_pb2.Host(id='arbitrary-id'))

        self.host_actions.viewComments(rpcObjects=[opencue.wrappers.layer.Layer, host])

        commentListDialogMock.assert_called_with([host], mock.ANY)
        commentListDialogMock.return_value.show.assert_called()

    def test_viewProc(self):
        self.app.view_procs = mock.Mock()
        hostName = 'arbitrary-name'
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id', name=hostName))

        self.host_actions.viewProc(rpcObjects=[opencue.wrappers.layer.Layer, host, host])

        self.app.view_procs.emit.assert_called_with([hostName])

    def test_lock(self):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        host.lock = mock.MagicMock()

        self.host_actions.lock(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.lock.assert_called()

    def test_unlock(self):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        host.unlock = mock.MagicMock()

        self.host_actions.unlock(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.unlock.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        rp1 = mock.MagicMock()
        rp2 = mock.MagicMock()
        host.getRenderPartitions = lambda: [rp1, rp2]
        host.delete = mock.MagicMock()

        self.host_actions.delete(rpcObjects=[opencue.wrappers.layer.Layer, host])

        rp1.delete.assert_called()
        rp2.delete.assert_called()
        host.delete.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_rebootWhenIdle(self):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        host.rebootWhenIdle = mock.MagicMock()

        self.host_actions.rebootWhenIdle(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.rebootWhenIdle.assert_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_addTags(self, getTextMock):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        tagsText = 'firstTag anotherTag,oneMoreTag'
        getTextMock.return_value = (tagsText, True)
        host.addTags = mock.MagicMock()

        self.host_actions.addTags(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.addTags.assert_called_with(['firstTag', 'anotherTag', 'oneMoreTag'])

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_removeTags(self, getTextMock):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(
                id='arbitrary-id', tags=['firstTag', 'anotherTag', 'oneMoreTag', 'tagToKeep']))
        getTextMock.return_value = ('firstTag anotherTag,oneMoreTag', True)
        host.removeTags = mock.MagicMock()

        self.host_actions.removeTags(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.removeTags.assert_called_with(['firstTag', 'anotherTag', 'oneMoreTag'])

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_renameTag(self, getItemMock, getTextMock):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        oldTagName = 'tagToRename'
        newTagName = 'newTagName'
        getItemMock.return_value = (oldTagName, True)
        getTextMock.return_value = (newTagName, True)
        host.renameTag = mock.MagicMock()

        self.host_actions.renameTag(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.renameTag.assert_called_with(oldTagName, newTagName)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.getAllocations')
    def test_changeAllocation(self, getAllocationsMock, getItemMock):
        host = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(id='arbitrary-id'))
        allocs = [
            opencue.wrappers.allocation.Allocation(
                opencue_proto.facility_pb2.Allocation(name='alloc1')),
            opencue.wrappers.allocation.Allocation(
                opencue_proto.facility_pb2.Allocation(name='alloc2')),
        ]
        getAllocationsMock.return_value = allocs
        getItemMock.return_value = ('alloc2', True)
        host.setAllocation = mock.MagicMock()

        self.host_actions.changeAllocation(rpcObjects=[opencue.wrappers.layer.Layer, host])

        host.setAllocation.assert_called_with(allocs[1])

    def test_setRepair(self):
        activeHost = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(
                id='active-host', state=opencue.api.host_pb2.UP))
        activeHost.setHardwareState = mock.MagicMock()
        repairingHost = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(
                id='repairing-host', state=opencue.api.host_pb2.REPAIR))
        repairingHost.setHardwareState = mock.MagicMock()

        self.host_actions.setRepair(
            rpcObjects=[opencue.wrappers.layer.Layer, activeHost, repairingHost])

        activeHost.setHardwareState.assert_called_with(opencue.api.host_pb2.REPAIR)
        repairingHost.setHardwareState.assert_not_called()

    def test_clearRepair(self):
        activeHost = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(
                id='active-host', state=opencue.api.host_pb2.UP))
        activeHost.setHardwareState = mock.MagicMock()
        repairingHost = opencue.wrappers.host.Host(
            opencue_proto.host_pb2.Host(
                id='repairing-host', state=opencue.api.host_pb2.REPAIR))
        repairingHost.setHardwareState = mock.MagicMock()

        self.host_actions.clearRepair(
            rpcObjects=[opencue.wrappers.layer.Layer, activeHost, repairingHost])

        repairingHost.setHardwareState.assert_called_with(opencue.api.host_pb2.DOWN)
        activeHost.setHardwareState.assert_not_called()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class ProcActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.proc_actions = cuegui.MenuActions.ProcActions(
            self.widgetMock, mock.Mock(), mock.Mock(), mock.Mock())

    @mock.patch('opencue.api.findJob')
    def test_view(self, findJobMock):
        self.app.view_object = mock.Mock()
        jobName = 'arbitraryJobName'
        job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(name=jobName))
        proc = opencue.wrappers.proc.Proc(opencue_proto.host_pb2.Proc(job_name=jobName))
        findJobMock.return_value = job

        self.proc_actions.view(rpcObjects=[opencue.wrappers.layer.Layer, proc])

        self.app.view_object.emit.assert_called_once_with(job)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    @mock.patch('cuegui.Utils.isPermissible', return_value=True)
    def test_kill(self, isPermissibleMock, yesNoMock):
        proc = opencue.wrappers.proc.Proc(opencue_proto.host_pb2.Proc())
        proc.kill = mock.MagicMock()

        self.proc_actions.kill(rpcObjects=[opencue.wrappers.layer.Layer, proc])

        proc.kill.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_unbook(self):
        proc = opencue.wrappers.proc.Proc(opencue_proto.host_pb2.Proc())
        proc.unbook = mock.MagicMock()

        self.proc_actions.unbook(rpcObjects=[opencue.wrappers.layer.Layer, proc])

        proc.unbook.assert_called_with(False)

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_unbookKill(self):
        proc = opencue.wrappers.proc.Proc(opencue_proto.host_pb2.Proc())
        proc.unbook = mock.MagicMock()

        self.proc_actions.unbookKill(rpcObjects=[opencue.wrappers.layer.Layer, proc])

        proc.unbook.assert_called_with(True)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class DependenciesActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.dep_actions = cuegui.MenuActions.DependenciesActions(
            self.widgetMock, mock.Mock(), None, None)

    def test_satisfy(self):
        dep = opencue.wrappers.depend.Depend(opencue_proto.depend_pb2.Depend())
        dep.satisfy = mock.MagicMock()

        self.dep_actions.satisfy(rpcObjects=[dep])

        dep.satisfy.assert_called()

    def test_unsatisfy(self):
        dep = opencue.wrappers.depend.Depend(opencue_proto.depend_pb2.Depend())
        dep.unsatisfy = mock.MagicMock()

        self.dep_actions.unsatisfy(rpcObjects=[dep])

        dep.unsatisfy.assert_called()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FilterActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.filter_actions = cuegui.MenuActions.FilterActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_rename(self, getTextMock):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.setName = mock.MagicMock()
        newName = 'newFilterName'
        getTextMock.return_value = (newName, True)

        self.filter_actions.rename(rpcObjects=[filter_wrapper])

        filter_wrapper.setName.assert_called_with(newName)

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.delete = mock.MagicMock()

        self.filter_actions.delete(rpcObjects=[filter_wrapper])

        filter_wrapper.delete.assert_called()

    def test_raiseOrder(self):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.raiseOrder = mock.MagicMock()

        self.filter_actions.raiseOrder(rpcObjects=[filter_wrapper])

        filter_wrapper.raiseOrder.assert_called()

    def test_lowerOrder(self):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.lowerOrder = mock.MagicMock()

        self.filter_actions.lowerOrder(rpcObjects=[filter_wrapper])

        filter_wrapper.lowerOrder.assert_called()

    def test_orderFirst(self):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.orderFirst = mock.MagicMock()

        self.filter_actions.orderFirst(rpcObjects=[filter_wrapper])

        filter_wrapper.orderFirst.assert_called()

    def test_orderLast(self):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.orderLast = mock.MagicMock()

        self.filter_actions.orderLast(rpcObjects=[filter_wrapper])

        filter_wrapper.orderLast.assert_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getInt')
    def test_setOrder(self, getTextMock):
        filter_wrapper = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())
        filter_wrapper.setOrder = mock.MagicMock()
        new_order = 47
        getTextMock.return_value = (new_order, True)

        self.filter_actions.setOrder(rpcObjects=[filter_wrapper])

        filter_wrapper.setOrder.assert_called_with(new_order)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class MatcherActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.matcher_actions = cuegui.MenuActions.MatcherActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        matcher = opencue.wrappers.filter.Matcher(opencue_proto.filter_pb2.Matcher())
        matcher.delete = mock.MagicMock()

        self.matcher_actions.delete(rpcObjects=[matcher])

        matcher.delete.assert_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_setValue(self, getTextMock):
        matcher = opencue.wrappers.filter.Matcher(opencue_proto.filter_pb2.Matcher())
        matcher.setValue = mock.MagicMock()
        newValue = 'newMatcherValue'
        getTextMock.return_value = (newValue, True)

        self.matcher_actions.setValue(rpcObjects=[matcher])

        matcher.setValue.assert_called_with(newValue)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class ActionActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.action_actions = cuegui.MenuActions.ActionActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        action = opencue.wrappers.filter.Action(opencue_proto.filter_pb2.Action())
        action.delete = mock.MagicMock()

        self.action_actions.delete(rpcObjects=[action])

        action.delete.assert_called()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class TaskActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.task_actions = cuegui.MenuActions.TaskActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock):
        task = opencue.wrappers.task.Task(opencue_proto.task_pb2.Task(min_cores=10))
        task.setMinCores = mock.MagicMock()
        newCoreCount = 28
        getDoubleMock.return_value = (newCoreCount, True)

        self.task_actions.setMinCores(rpcObjects=[task])

        task.setMinCores.assert_called_with(newCoreCount)

    def test_clearAdjustment(self):
        task = opencue.wrappers.task.Task(opencue_proto.task_pb2.Task())
        task.clearAdjustment = mock.MagicMock()

        self.task_actions.clearAdjustment(rpcObjects=[task])

        task.clearAdjustment.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        task = opencue.wrappers.task.Task(opencue_proto.task_pb2.Task())
        task.delete = mock.MagicMock()

        self.task_actions.delete(rpcObjects=[task])

        task.delete.assert_called()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class LimitActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.limit_actions = cuegui.MenuActions.LimitActions(
            self.widgetMock, mock.Mock(), None, None)

    @mock.patch('opencue.api.createLimit')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_create(self, getTextMock, createLimitMock):
        limitName = 'newLimitName'
        getTextMock.return_value = ('%s \t ' % limitName, True)

        self.limit_actions.create()

        createLimitMock.assert_called_with(limitName, 0)

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    def test_delete(self):
        limit = opencue.wrappers.limit.Limit(opencue_proto.limit_pb2.Limit())
        limit.delete = mock.MagicMock()

        self.limit_actions.delete(rpcObjects=[limit])

        limit.delete.assert_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getDouble')
    def test_editMaxValue(self, getDoubleMock):
        limit = opencue.wrappers.limit.Limit(opencue_proto.limit_pb2.Limit(max_value=920))
        limit.setMaxValue = mock.MagicMock()

        newMaxValue = 527
        getDoubleMock.return_value = (newMaxValue, True)

        self.limit_actions.editMaxValue(rpcObjects=[limit])

        limit.setMaxValue.assert_called_with(newMaxValue)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_rename(self, getTextMock):
        limit = opencue.wrappers.limit.Limit(opencue_proto.limit_pb2.Limit())
        limit.rename = mock.MagicMock()
        newName = 'newLimitName'
        getTextMock.return_value = (newName, True)

        self.limit_actions.rename(rpcObjects=[limit])

        limit.rename.assert_called_with(newName)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class MenuActionsTests(unittest.TestCase):
    def setUp(self):
        self.app = test_utils.createApplication()
        self.widgetMock = mock.Mock()
        self.args = [self.widgetMock, lambda: None, lambda: None, lambda: None]
        self.menuActions = cuegui.MenuActions.MenuActions(*self.args)

    @mock.patch('cuegui.MenuActions.JobActions')
    def test_jobs(self, jobActionsMock):
        self.menuActions.jobs()

        jobActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.LayerActions')
    def test_layers(self, layerActionsMock):
        self.menuActions.layers()

        layerActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.FrameActions')
    def test_frames(self, frameActionsMock):
        self.menuActions.frames()

        frameActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.ShowActions')
    def test_shows(self, showActionsMock):
        self.menuActions.shows()

        showActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.RootGroupActions')
    def test_rootgroups(self, rootGroupActionsMock):
        self.menuActions.rootgroups()

        rootGroupActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.GroupActions')
    def test_groups(self, groupActionsMock):
        self.menuActions.groups()

        groupActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.SubscriptionActions')
    def test_subscriptions(self, subscriptionActionsMock):
        self.menuActions.subscriptions()

        subscriptionActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.AllocationActions')
    def test_allocations(self, allocationActionsMock):
        self.menuActions.allocations()

        allocationActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.HostActions')
    def test_hosts(self, hostActionsMock):
        self.menuActions.hosts()

        hostActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.ProcActions')
    def test_procs(self, procActionsMock):
        self.menuActions.procs()

        procActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.DependenciesActions')
    def test_dependencies(self, dependenciesActionsMock):
        self.menuActions.dependencies()

        dependenciesActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.FilterActions')
    def test_filters(self, filterActionsMock):
        self.menuActions.filters()

        filterActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.MatcherActions')
    def test_matchers(self, matcherActionsMock):
        self.menuActions.matchers()

        matcherActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.ActionActions')
    def test_actions(self, actionActionsMock):
        self.menuActions.actions()

        actionActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.TaskActions')
    def test_tasks(self, taskActionsMock):
        self.menuActions.tasks()

        taskActionsMock.assert_called_with(*self.args)

    @mock.patch('cuegui.MenuActions.LimitActions')
    def test_limits(self, limitActionsMock):
        self.menuActions.limits()

        limitActionsMock.assert_called_with(*self.args)


if __name__ == '__main__':
    unittest.main()
