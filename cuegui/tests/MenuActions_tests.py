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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import *

import mock
import unittest

import cuegui.Constants
import cuegui.CueJobMonitorTree
import cuegui.Main
import cuegui.MenuActions
import opencue.compiled_proto.depend_pb2
import opencue.compiled_proto.host_pb2
import opencue.compiled_proto.job_pb2
import opencue.wrappers.depend
import opencue.wrappers.frame
import opencue.wrappers.group
import opencue.wrappers.host
import opencue.wrappers.job
import opencue.wrappers.layer
import opencue.wrappers.show


_GB_TO_KB = 1024 * 1024


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class JobActionsTests(unittest.TestCase):
    def setUp(self):
        self.widgetMock = mock.Mock()
        self.job_actions = cuegui.MenuActions.JobActions(self.widgetMock, mock.Mock(), None, None)

    def test_unmonitor(self):
        self.job_actions.unmonitor()

        self.widgetMock.actionRemoveSelectedItems.assert_called_with()

    @mock.patch('PySide2.QtGui.qApp')
    def test_view(self, qAppMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=job_name))

        self.job_actions.view(rpcObjects=[job, opencue.wrappers.frame.Frame()])

        qAppMock.view_object.emit.assert_called_once_with(job)

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=job_name))

        self.job_actions.viewDepends(rpcObjects=[job])

        dependDialogMock.assert_called_with(job, self.widgetMock)
        dependDialogMock.return_value.show.assert_called()

    @mock.patch('cuegui.EmailDialog.EmailDialog')
    def test_emailArtist(self, emailDialogMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=job_name))

        self.job_actions.emailArtist(rpcObjects=[job])

        emailDialogMock.assert_called_with(job, [], self.widgetMock)
        emailDialogMock.return_value.show.assert_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock):
        highest_current_core_count = 20
        new_core_count = 50
        job1 = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(min_cores=highest_current_core_count - 10))
        job1.setMinCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(min_cores=highest_current_core_count))
        job2.setMinCores = mock.Mock()
        getDoubleMock.return_value = (new_core_count, True)

        self.job_actions.setMinCores(rpcObjects=[job1, job2])

        # Default value should be the highest core count of all jobs passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        job1.setMinCores.assert_called_with(new_core_count)
        job2.setMinCores.assert_called_with(new_core_count)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCoresCanceled(self, getDoubleMock):
        job1 = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(min_cores=0))
        job1.setMinCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(min_cores=0))
        job2.setMinCores = mock.Mock()
        getDoubleMock.return_value = (None, False)

        self.job_actions.setMinCores(rpcObjects=[job1, job2])

        job1.setMinCores.assert_not_called()
        job2.setMinCores.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMaxCores(self, getDoubleMock):
        highest_current_core_count = 20
        new_core_count = 50
        job1 = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(max_cores=highest_current_core_count - 10))
        job1.setMaxCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(max_cores=highest_current_core_count))
        job2.setMaxCores = mock.Mock()
        getDoubleMock.return_value = (new_core_count, True)

        self.job_actions.setMaxCores(rpcObjects=[job1, job2])

        # Default value should be the highest core count of all jobs passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        job1.setMaxCores.assert_called_with(new_core_count)
        job2.setMaxCores.assert_called_with(new_core_count)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMaxCoresCanceled(self, getDoubleMock):
        job1 = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(max_cores=0))
        job1.setMaxCores = mock.Mock()
        job2 = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(max_cores=0))
        job2.setMaxCores = mock.Mock()
        getDoubleMock.return_value = (None, False)

        self.job_actions.setMaxCores(rpcObjects=[job1, job2])

        job1.setMaxCores.assert_not_called()
        job2.setMaxCores.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setPriority(self, getIntMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(priority=0))
        job.setPriority = mock.Mock()
        new_priority = 25
        getIntMock.return_value = (new_priority, True)

        self.job_actions.setPriority(rpcObjects=[job])

        job.setPriority.assert_called_with(new_priority)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setPriorityCanceled(self, getIntMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(priority=0))
        job.setPriority = mock.Mock()
        getIntMock.return_value = (None, False)

        self.job_actions.setPriority(rpcObjects=[job])

        job.setPriority.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setMaxRetries(self, getIntMock):
        job = opencue.wrappers.job.Job()
        job.setMaxRetries = mock.Mock()
        new_retries = 7
        getIntMock.return_value = (new_retries, True)

        self.job_actions.setMaxRetries(rpcObjects=[job])

        job.setMaxRetries.assert_called_with(new_retries)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
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
    def test_kill(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.kill = mock.Mock()

        self.job_actions.kill(rpcObjects=[job])

        job.kill.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_killCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.kill = mock.Mock()

        self.job_actions.kill(rpcObjects=[job])

        job.kill.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_eatDead(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.eatFrames = mock.Mock()

        self.job_actions.eatDead(rpcObjects=[job])

        job.eatFrames.assert_called_with(state=[opencue.compiled_proto.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_eatDeadCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.eatFrames = mock.Mock()

        self.job_actions.eatDead(rpcObjects=[job])

        job.eatFrames.assert_not_called()

    def test_autoEatOn(self):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.setAutoEat = mock.Mock()
        job.eatFrames = mock.Mock()

        self.job_actions.autoEatOn(rpcObjects=[job])

        job.setAutoEat.assert_called_with(True)
        job.eatFrames.assert_called_with(state=[opencue.compiled_proto.job_pb2.DEAD])

    def test_autoEatOff(self):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.setAutoEat = mock.Mock()

        self.job_actions.autoEatOff(rpcObjects=[job])

        job.setAutoEat.assert_called_with(False)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retryDead(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.retryFrames = mock.Mock()

        self.job_actions.retryDead(rpcObjects=[job])

        job.retryFrames.assert_called_with(state=[opencue.compiled_proto.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_retryDeadCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.retryFrames = mock.Mock()

        self.job_actions.retryDead(rpcObjects=[job])

        job.retryFrames.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropExternalDependencies(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropExternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_called_with(opencue.api.depend_pb2.EXTERNAL)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_dropExternalDependenciesCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropExternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropInternalDependencies(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropInternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_called_with(opencue.api.depend_pb2.INTERNAL)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_dropInternalDependenciesCanceled(self, yesNoMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.dropDepends = mock.Mock()

        self.job_actions.dropInternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_not_called()

    @mock.patch('cuegui.Comments.CommentListDialog')
    def test_viewComments(self, commentListMock):
        job = opencue.wrappers.job.Job()

        self.job_actions.viewComments(rpcObjects=[job])

        commentListMock.assert_called_with(job, self.widgetMock)
        commentListMock.return_value.show.assert_called()

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        jobs = [opencue.wrappers.job.Job()]

        self.job_actions.dependWizard(rpcObjects=jobs)

        dependWizardMock.assert_called_with(self.widgetMock, jobs)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_reorder(self, getTextMock, getItemMock):
        original_range = '1-10'
        new_order = 'REVERSE'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue.compiled_proto.job_pb2.Layer(range=original_range))]
        job.reorderFrames = mock.Mock()
        getTextMock.return_value = (original_range, True)
        getItemMock.return_value = (new_order, True)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_called_with(original_range, opencue.compiled_proto.job_pb2.REVERSE)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_reorderCanceled(self, getTextMock, getItemMock):
        original_range = '1-10'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue.compiled_proto.job_pb2.Layer(range=original_range))]
        job.reorderFrames = mock.Mock()

        getTextMock.return_value = (None, False)
        getItemMock.return_value = (None, True)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_not_called()

        getTextMock.return_value = (None, True)
        getItemMock.return_value = (None, False)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_stagger(self, getTextMock, getIntMock):
        original_range = '1-10'
        new_step = 28
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue.compiled_proto.job_pb2.Layer(range=original_range))]
        job.staggerFrames = mock.Mock()
        getTextMock.return_value = (original_range, True)
        getIntMock.return_value = (new_step, True)

        self.job_actions.stagger(rpcObjects=[job])

        job.staggerFrames.assert_called_with(original_range, new_step)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_staggerCanceled(self, getTextMock, getIntMock):
        original_range = '1-10'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        job.getLayers = lambda: [
            opencue.wrappers.layer.Layer(
                opencue.compiled_proto.job_pb2.Layer(range=original_range))]
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

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.findShow')
    def test_sendToGroup(self, findShowMock, getItemMock):
        group_name = 'arbitrary-group-name'
        job = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(
                name='arbitrary-job-name', show='arbitrary-show-name'))
        show = opencue.wrappers.show.Show()
        group = opencue.wrappers.group.Group(opencue.compiled_proto.job_pb2.Group(name=group_name))
        group.reparentJobs = mock.Mock()
        findShowMock.return_value = show
        show.getGroups = mock.Mock(return_value=[group])
        getItemMock.return_value = (group_name, True)

        self.job_actions.sendToGroup(rpcObjects=[job])

        group.reparentJobs.assert_called_with([job])

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.findShow')
    def test_sendToGroupCanceled(self, findShowMock, getItemMock):
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name='job-name'))
        group = opencue.wrappers.group.Group()
        group.reparentJobs = mock.Mock()
        findShowMock.getGroups.return_value = []
        getItemMock.return_value = (None, False)

        self.job_actions.sendToGroup(rpcObjects=[job])

        group.reparentJobs.assert_not_called()

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        job = opencue.wrappers.job.Job()

        self.job_actions.useLocalCores(rpcObjects=[job])

        localBookingDialogMock.assert_called_with(job, self.widgetMock)
        localBookingDialogMock.return_value.exec_.assert_called()

    @mock.patch('PySide2.QtWidgets.QApplication.clipboard')
    def test_copyLogFileDir(self, clipboardMock):
        logDir1 = '/some/random/dir'
        logDir2 = '/a/different/random/dir'
        job1 = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(log_dir=logDir1))
        job2 = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(log_dir=logDir2))

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
        self.widgetMock = mock.Mock()
        self.job = mock.create_autospec(opencue.wrappers.job.Job())
        self.layer_actions = cuegui.MenuActions.LayerActions(
            self.widgetMock, mock.Mock(), None, lambda: self.job)

    def test_view(self):
        layer_name = 'arbitrary-name'
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(name=layer_name))

        self.layer_actions.view(rpcObjects=[layer, opencue.wrappers.frame.Frame()])

        self.widgetMock.handle_filter_layers_byLayer.emit.assert_called_with([layer_name])

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.viewDepends(rpcObjects=[layer])

        dependDialogMock.assert_called_with(layer, self.widgetMock)
        dependDialogMock.return_value.show.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinCores', autospec=True)
    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock, setMinCoresMock):
        highest_current_core_count = 20
        new_core_count = 50
        layer1 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=highest_current_core_count - 10))
        layer2 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=highest_current_core_count))
        getDoubleMock.return_value = (new_core_count, True)

        self.layer_actions.setMinCores(rpcObjects=[layer1, layer2])

        # Default value should be the highest core count of all layers passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        setMinCoresMock.assert_has_calls([
            mock.call(layer1, new_core_count), mock.call(layer2, new_core_count)])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinCores')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCoresCanceled(self, getDoubleMock, setMinCoresMock):
        layer1 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=0))
        layer2 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=0))
        getDoubleMock.return_value = (None, False)

        self.layer_actions.setMinCores(rpcObjects=[layer1, layer2])

        setMinCoresMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'setMinMemory', autospec=True)
    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinMemoryKb(self, getDoubleMock, setMinMemoryMock):
        highest_current_mem_limit_gb = 20
        new_mem_limit_gb = 50
        layer1 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(
                min_memory=(highest_current_mem_limit_gb - 10) * _GB_TO_KB))
        layer2 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(
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
    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinMemoryKbCanceled(self, getDoubleMock, setMinMemoryMock):
        layer1 = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(min_memory=0))
        layer2 = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(min_memory=0))
        getDoubleMock.return_value = (None, False)

        self.layer_actions.setMinMemoryKb(rpcObjects=[layer1, layer2])

        setMinMemoryMock.assert_not_called()

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer())

        self.layer_actions.useLocalCores(rpcObjects=[layer])

        localBookingDialogMock.assert_called_with(layer, self.widgetMock)
        localBookingDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.LayerDialog.LayerPropertiesDialog')
    def test_setProperties(self, layerPropertiesDialogMock):
        layers = [opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer())]

        self.layer_actions.setProperties(rpcObjects=layers)

        layerPropertiesDialogMock.assert_called_with(layers)
        layerPropertiesDialogMock.return_value.exec_.assert_called()

    @mock.patch('cuegui.LayerDialog.LayerTagsDialog')
    def test_setTags(self, layerTagsDialogMock):
        layers = [opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer())]

        self.layer_actions.setTags(rpcObjects=layers)

        layerTagsDialogMock.assert_called_with(layers)
        layerTagsDialogMock.return_value.exec_.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'kill')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_kill(self, yesNoMock, killMock):
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.kill(rpcObjects=[layer])

        killMock.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'kill')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_killCanceled(self, yesNoMock, killMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.kill(rpcObjects=[layer])

        killMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'eat')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_eat(self, yesNoMock, eatMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.eat(rpcObjects=[layer])

        eatMock.assert_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'eat')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_eatCanceled(self, yesNoMock, eatMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.eat(rpcObjects=[layer])

        eatMock.assert_not_called()

    @mock.patch.object(opencue.wrappers.layer.Layer, 'retry', autospec=True)
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retry(self, yesNoMock, retryMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.retry(rpcObjects=[layer])

        retryMock.assert_called_with(layer)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'retry')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_retryCanceled(self, yesNoMock, retryMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.retry(rpcObjects=[layer])

        retryMock.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retryDead(self, yesNoMock):
        layer_name = 'arbitrary-name'
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name=layer_name))
        layer.parent = lambda : self.job

        self.layer_actions.retryDead(rpcObjects=[layer])

        self.job.retryFrames.assert_called_with(
            layer=[layer_name], state=[opencue.api.job_pb2.DEAD])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'markdone', autospec=True)
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markdone(self, yesNoMock, markdoneMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.markdone(rpcObjects=[layer])

        markdoneMock.assert_called_with(layer)

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        layers = [opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer())]

        self.layer_actions.dependWizard(rpcObjects=layers)

        dependWizardMock.assert_called_with(self.widgetMock, [self.job], layers)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'reorderFrames', autospec=True)
    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_reorder(self, getTextMock, getItemMock, reorderFramesMock):
        original_range = '1-10'
        new_order = 'REVERSE'
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(range=original_range))

        getTextMock.return_value = (original_range, True)
        getItemMock.return_value = (new_order, True)

        self.layer_actions.reorder(rpcObjects=[layer])

        reorderFramesMock.assert_called_with(
            layer, original_range, opencue.compiled_proto.job_pb2.REVERSE)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'staggerFrames', autospec=True)
    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_stagger(self, getTextMock, getIntMock, staggerFramesMock):
        original_range = '1-10'
        new_step = 28
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(range=original_range))
        getTextMock.return_value = (original_range, True)
        getIntMock.return_value = (new_step, True)

        self.layer_actions.stagger(rpcObjects=[layer])

        staggerFramesMock.assert_called_with(layer, original_range, new_step)


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FrameActionsTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    def setUp(self):
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
    @mock.patch('PySide2.QtGui.qApp')
    def test_viewHost(self, qAppMock, findHostMock):
        host_name = 'arbitrary-host-name'
        host = opencue.wrappers.host.Host(
            opencue.compiled_proto.host_pb2.Host(id='arbitrary-id', name=host_name))
        frame = opencue.wrappers.frame.Frame(
            opencue.compiled_proto.job_pb2.Frame(last_resource='{}/foo'.format(host_name)))
        findHostMock.return_value = host

        self.frame_actions.viewHost(rpcObjects=[frame])

        qAppMock.view_hosts.emit.assert_called_with([host_name])
        qAppMock.single_click.emit.assert_called_with(host)

    def test_getWhatThisDependsOn(self):
        frame = opencue.wrappers.frame.Frame()
        depend = opencue.wrappers.depend.Depend(opencue.compiled_proto.depend_pb2.Depend())
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
        depend = opencue.wrappers.depend.Depend(opencue.compiled_proto.depend_pb2.Depend())
        frame.getWhatDependsOnThis = lambda: [depend]

        # This method just logs info so no return value to check; just make sure it executes.
        self.frame_actions.getWhatDependsOnThis(rpcObjects=[frame])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retry(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name=frame_name))

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
    def test_eat(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.eat(rpcObjects=[frame])

        self.job.eatFrames.assert_called_with(name=[frame_name])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_kill(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.kill(rpcObjects=[frame])

        self.job.killFrames.assert_called_with(name=[frame_name])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markAsWaiting(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.markAsWaiting(rpcObjects=[frame])

        self.job.markAsWaiting.assert_called_with(name=[frame_name])

    @mock.patch('opencue.search.FrameSearch')
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropDepends(self, yesNoMock, frameSearchMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name=frame_name))
        frame.dropDepends = mock.Mock()

        self.frame_actions.dropDepends(rpcObjects=[frame])

        frame.dropDepends.assert_called_with(opencue.api.depend_pb2.ANY_TARGET)

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        frames = [opencue.wrappers.frame.Frame()]

        self.frame_actions.dependWizard(rpcObjects=frames)

        dependWizardMock.assert_called_with(self.widgetMock, [self.job], [], frames)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markdone(self, yesNoMock):
        frame_name = 'arbitrary-frame-name'
        frame = opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name=frame_name))

        self.frame_actions.markdone(rpcObjects=[frame])

        self.job.markdoneFrames.assert_called_with(name=[frame_name])

    @mock.patch.object(opencue.wrappers.layer.Layer, 'reorderFrames', autospec=True)
    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    def test_reorder(self, getItemMock, reorderFramesMock):
        new_order = 'REVERSE'
        getItemMock.return_value = (new_order, True)
        layer_name = 'arbitrary-layer-name'
        frame_num = 28
        frame = opencue.wrappers.frame.Frame(
            opencue.compiled_proto.job_pb2.Frame(layer_name=layer_name, number=frame_num))
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name=layer_name))
        self.job.getLayers.return_value = [layer]

        self.frame_actions.reorder(rpcObjects=[frame])

        reorderFramesMock.assert_called_with(layer, str(frame_num), opencue.compiled_proto.job_pb2.REVERSE)

    @mock.patch('PySide2.QtWidgets.QApplication.clipboard')
    @mock.patch('cuegui.Utils.getFrameLogFile')
    def test_copyLogFileName(self, getFrameLogFileMock, clipboardMock):
        frame_log_path = '/some/path/to/job/logs/job-name.frame-name.rqlog'
        getFrameLogFileMock.return_value = frame_log_path
        frame = opencue.wrappers.frame.Frame()

        self.frame_actions.copyLogFileName(rpcObjects=[frame])

        clipboardMock.return_value.setText.assert_called_with([frame_log_path], mock.ANY)

    @mock.patch.object(opencue.wrappers.layer.Layer, 'markdone', autospec=True)
    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_eatandmarkdone(self, yesNoMock, markdoneMock):
        layer_name = 'layer-name'
        frames = [
            opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name='frame1', layer_name=layer_name)),
            opencue.wrappers.frame.Frame(opencue.compiled_proto.job_pb2.Frame(name='frame2', layer_name=layer_name))]
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(
                name=layer_name, layer_stats=opencue.compiled_proto.job_pb2.LayerStats(
                    eaten_frames=7, succeeded_frames=3, total_frames=10)))
        self.job.getLayers.return_value = [layer]

        self.frame_actions.eatandmarkdone(rpcObjects=frames)

        self.job.eatFrames.assert_called_with(name=['frame1', 'frame2'])
        self.job.markdoneFrames.assert_called_with(name=['frame1', 'frame2'])
        markdoneMock.assert_called_with(layer)


if __name__ == '__main__':
    unittest.main()
