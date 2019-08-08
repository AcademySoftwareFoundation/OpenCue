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
import opencue.compiled_proto.job_pb2
import opencue.wrappers.frame
import opencue.wrappers.job
import opencue.wrappers.layer


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

        self.job_actions.view(rpcObjects=[job, opencue.wrappers.frame.Frame(None)])

        qAppMock.view_object.emit.assert_called_once_with(job)

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=job_name))

        self.job_actions.viewDepends(rpcObjects=[job])

        dependDialogMock.assert_called_with(job, mock.ANY)
        dependDialogMock.return_value.show.assert_called()

    @mock.patch('cuegui.EmailDialog.EmailDialog')
    def test_emailArtist(self, emailDialogMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=job_name))

        self.job_actions.emailArtist(rpcObjects=[job])

        emailDialogMock.assert_called_with(job, [], mock.ANY)
        emailDialogMock.return_value.show.assert_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock):
        highest_current_core_count = 20
        job1 = mock.Mock(spec=opencue.wrappers.job.Job)
        job1.data = mock.Mock()
        job1.data.min_cores = highest_current_core_count - 10
        job2 = mock.Mock(spec=opencue.wrappers.job.Job)
        job2.data = mock.Mock()
        job2.data.min_cores = highest_current_core_count
        new_core_count = 50
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
        job1 = mock.Mock(spec=opencue.wrappers.job.Job)
        job1.data = mock.Mock()
        job1.data.min_cores = 0
        job2 = mock.Mock(spec=opencue.wrappers.job.Job)
        job2.data = mock.Mock()
        job2.data.min_cores = 0
        getDoubleMock.return_value = (None, False)

        self.job_actions.setMinCores(rpcObjects=[job1, job2])

        job1.setMinCores.assert_not_called()
        job2.setMinCores.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMaxCores(self, getDoubleMock):
        highest_current_core_count = 20
        job1 = mock.Mock(spec=opencue.wrappers.job.Job)
        job1.data = mock.Mock()
        job1.data.max_cores = highest_current_core_count - 10
        job2 = mock.Mock(spec=opencue.wrappers.job.Job)
        job2.data = mock.Mock()
        job2.data.max_cores = highest_current_core_count
        new_core_count = 50
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
        job1 = mock.Mock(spec=opencue.wrappers.job.Job)
        job1.data = mock.Mock()
        job1.data.max_cores = 0
        job2 = mock.Mock(spec=opencue.wrappers.job.Job)
        job2.data = mock.Mock()
        job2.data.max_cores = 0
        getDoubleMock.return_value = (None, False)

        self.job_actions.setMaxCores(rpcObjects=[job1, job2])

        job1.setMaxCores.assert_not_called()
        job2.setMaxCores.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setPriority(self, getIntMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        job.data.priority = 0
        new_priority = 25
        getIntMock.return_value = (new_priority, True)

        self.job_actions.setPriority(rpcObjects=[job])

        job.setPriority.assert_called_with(new_priority)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setPriorityCanceled(self, getIntMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        job.data.priority = 0
        getIntMock.return_value = (None, False)

        self.job_actions.setPriority(rpcObjects=[job])

        job.setPriority.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setMaxRetries(self, getIntMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        new_retries = 7
        getIntMock.return_value = (new_retries, True)

        self.job_actions.setMaxRetries(rpcObjects=[job])

        job.setMaxRetries.assert_called_with(new_retries)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    def test_setMaxRetriesCanceled(self, getIntMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        getIntMock.return_value = (None, False)

        self.job_actions.setMaxRetries(rpcObjects=[job])

        job.setMaxRetries.assert_not_called()

    def test_pause(self):
        job = mock.Mock(spec=opencue.wrappers.job.Job)

        self.job_actions.pause(rpcObjects=[job])

        job.pause.assert_called()

    def test_resume(self):
        job = mock.Mock(spec=opencue.wrappers.job.Job)

        self.job_actions.resume(rpcObjects=[job])

        job.resume.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_kill(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.kill(rpcObjects=[job])

        job.kill.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_killCanceled(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.kill(rpcObjects=[job])

        job.kill.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_eatDead(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.eatDead(rpcObjects=[job])

        job.eatFrames.assert_called_with(state=opencue.compiled_proto.job_pb2.DEAD)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_eatDeadCanceled(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.eatDead(rpcObjects=[job])

        job.eatFrames.assert_not_called()

    def test_autoEatOn(self):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.autoEatOn(rpcObjects=[job])

        job.setAutoEat.assert_called_with(True)
        job.eatFrames.assert_called_with(state=opencue.compiled_proto.job_pb2.DEAD)

    def test_autoEatOff(self):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.autoEatOff(rpcObjects=[job])

        job.setAutoEat.assert_called_with(False)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retryDead(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.retryDead(rpcObjects=[job])

        job.retryFrames.assert_called_with(state=[opencue.compiled_proto.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_retryDeadCanceled(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.retryDead(rpcObjects=[job])

        job.retryFrames.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropExternalDependencies(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.dropExternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_called_with(opencue.api.depend_pb2.EXTERNAL)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_dropExternalDependenciesCanceled(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.dropExternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_dropInternalDependencies(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.dropInternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_called_with(opencue.api.depend_pb2.INTERNAL)

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_dropInternalDependenciesCanceled(self, yesNoMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()

        self.job_actions.dropInternalDependencies(rpcObjects=[job])

        job.dropDepends.assert_not_called()

    @mock.patch('cuegui.Comments.CommentListDialog')
    def test_viewComments(self, commentListMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)

        self.job_actions.viewComments(rpcObjects=[job])

        commentListMock.assert_called_with(job, mock.ANY)
        commentListMock.return_value.show.assert_called()

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        jobs = [mock.Mock(spec=opencue.wrappers.job.Job)]

        self.job_actions.dependWizard(rpcObjects=jobs)

        dependWizardMock.assert_called_with(mock.ANY, jobs)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_reorder(self, getTextMock, getItemMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        layer = mock.Mock()
        layer.data = mock.Mock()
        original_range = '1-10'
        layer.data.range = original_range
        job.getLayers.return_value = [layer]
        new_order = 'REVERSE'
        getTextMock.return_value = (original_range, True)
        getItemMock.return_value = (new_order, True)

        self.job_actions.reorder(rpcObjects=[job])

        job.reorderFrames.assert_called_with(original_range, opencue.compiled_proto.job_pb2.REVERSE)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_reorderCanceled(self, getTextMock, getItemMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        layer = mock.Mock()
        layer.data = mock.Mock()
        original_range = '1-10'
        layer.data.range = original_range
        job.getLayers.return_value = [layer]

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
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        layer = mock.Mock()
        layer.data = mock.Mock()
        original_range = '1-10'
        layer.data.range = original_range
        job.getLayers.return_value = [layer]
        new_step = 28
        getTextMock.return_value = (original_range, True)
        getIntMock.return_value = (new_step, True)

        self.job_actions.stagger(rpcObjects=[job])

        job.staggerFrames.assert_called_with(original_range, new_step)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_staggerCanceled(self, getTextMock, getIntMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        layer = mock.Mock()
        layer.data = mock.Mock()
        original_range = '1-10'
        layer.data.range = original_range
        job.getLayers.return_value = [layer]

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
        jobs = [mock.Mock(spec=opencue.wrappers.job.Job)]

        self.job_actions.unbook(rpcObjects=jobs)

        unbookDialogMock.assert_called_with(jobs, mock.ANY)
        unbookDialogMock.return_value.exec_.assert_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.findShow')
    def test_sendToGroup(self, findShowMock, getItemMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        job.data.name = 'arbitrary-job-name'
        job.data.show = 'arbitrary-show-name'
        show = mock.Mock()
        findShowMock.return_value = show
        group = mock.Mock()
        group.data = mock.Mock()
        group_name = 'arbitrary-group-name'
        group.data.name = group_name
        show.getGroups.return_value = [group]
        getItemMock.return_value = (group_name, True)

        self.job_actions.sendToGroup(rpcObjects=[job])

        group.reparentJobs.assert_called_with([job])

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('opencue.api.findShow')
    def test_sendToGroupCanceled(self, findShowMock, getItemMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)
        job.data = mock.Mock()
        job.data.name = 'arbitrary-job-name'
        group = mock.Mock()
        findShowMock.getGroups.return_value = []
        getItemMock.return_value = (None, False)

        self.job_actions.sendToGroup(rpcObjects=[job])

        group.reparentJobs.assert_not_called()

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        job = mock.Mock(spec=opencue.wrappers.job.Job)

        self.job_actions.useLocalCores(rpcObjects=[job])

        localBookingDialogMock.assert_called_with(job, mock.ANY)
        localBookingDialogMock.return_value.exec_.assert_called()

    @mock.patch('PySide2.QtWidgets.QApplication.clipboard')
    def test_copyLogFileDir(self, clipboardMock):
        job1 = mock.Mock(spec=opencue.wrappers.job.Job)
        job1.data = mock.Mock()
        logDir1 = '/some/random/dir'
        job1.data.log_dir = logDir1
        job2 = mock.Mock(spec=opencue.wrappers.job.Job)
        job2.data = mock.Mock()
        logDir2 = '/a/different/random/dir'
        job2.data.log_dir = logDir2

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
    def setUp(self):
        self.widgetMock = mock.Mock()
        self.layer_actions = cuegui.MenuActions.LayerActions(
            self.widgetMock, mock.Mock(), None, mock.Mock())

    def test_view(self):
        layer_name = 'arbitrary-name'
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(name=layer_name))

        self.layer_actions.view(rpcObjects=[layer, opencue.wrappers.frame.Frame(None)])

        self.widgetMock.handle_filter_layers_byLayer.emit.assert_called_with([layer_name])

    @mock.patch('cuegui.DependDialog.DependDialog')
    def test_viewDepends(self, dependDialogMock):
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))

        self.layer_actions.viewDepends(rpcObjects=[layer])

        dependDialogMock.assert_called_with(layer, mock.ANY)
        dependDialogMock.return_value.show.assert_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCores(self, getDoubleMock):
        highest_current_core_count = 20
        new_core_count = 50
        layer1 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=highest_current_core_count - 10))
        layer1.setMinCores = mock.Mock()
        layer2 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=highest_current_core_count))
        layer2.setMinCores = mock.Mock()
        getDoubleMock.return_value = (new_core_count, True)

        self.layer_actions.setMinCores(rpcObjects=[layer1, layer2])

        # Default value should be the highest core count of all layers passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_core_count, mock.ANY, mock.ANY,
            mock.ANY)

        layer1.setMinCores.assert_called_with(new_core_count)
        layer2.setMinCores.assert_called_with(new_core_count)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinCoresCanceled(self, getDoubleMock):
        layer1 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=0))
        layer1.setMinCores = mock.Mock()
        layer2 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(min_cores=0))
        layer2.setMinCores = mock.Mock()
        getDoubleMock.return_value = (None, False)

        self.layer_actions.setMinCores(rpcObjects=[layer1, layer2])

        layer1.setMinCores.assert_not_called()
        layer2.setMinCores.assert_not_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinMemoryKb(self, getDoubleMock):
        highest_current_mem_limit_gb = 20
        new_mem_limit_gb = 50
        layer1 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(
                min_memory=(highest_current_mem_limit_gb - 10) * _GB_TO_KB))
        layer1.setMinMemory = mock.Mock()
        layer2 = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(
                min_memory=highest_current_mem_limit_gb * _GB_TO_KB))
        layer2.setMinMemory = mock.Mock()
        getDoubleMock.return_value = (new_mem_limit_gb, True)

        self.layer_actions.setMinMemoryKb(rpcObjects=[layer1, layer2])

        # Default value should be the highest core count of all layers passed.
        getDoubleMock.assert_called_with(
            self.widgetMock, mock.ANY, mock.ANY, highest_current_mem_limit_gb, mock.ANY, mock.ANY,
            mock.ANY)

        layer1.setMinMemory.assert_called_with(new_mem_limit_gb * _GB_TO_KB)
        layer2.setMinMemory.assert_called_with(new_mem_limit_gb * _GB_TO_KB)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getDouble')
    def test_setMinMemoryKbCanceled(self, getDoubleMock):
        layer1 = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(min_memory=0))
        layer1.setMinMemory = mock.Mock()
        layer2 = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(min_memory=0))
        layer2.setMinMemory = mock.Mock()
        getDoubleMock.return_value = (None, False)

        self.layer_actions.setMinMemoryKb(rpcObjects=[layer1, layer2])

        layer1.setMinMemory.assert_not_called()
        layer2.setMinMemory.assert_not_called()

    @mock.patch('cuegui.LocalBooking.LocalBookingDialog')
    def test_useLocalCores(self, localBookingDialogMock):
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer())

        self.layer_actions.useLocalCores(rpcObjects=[layer])

        localBookingDialogMock.assert_called_with(layer, mock.ANY)
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

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_kill(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.kill = mock.Mock()

        self.layer_actions.kill(rpcObjects=[layer])

        layer.kill.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_killCanceled(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.kill = mock.Mock()

        self.layer_actions.kill(rpcObjects=[layer])

        layer.kill.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_eat(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.eat = mock.Mock()

        self.layer_actions.eat(rpcObjects=[layer])

        layer.eat.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_eatCanceled(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.eat = mock.Mock()

        self.layer_actions.eat(rpcObjects=[layer])

        layer.eat.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retry(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.retry = mock.Mock()

        self.layer_actions.retry(rpcObjects=[layer])

        layer.retry.assert_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=False)
    def test_retryCanceled(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.retry = mock.Mock()

        self.layer_actions.retry(rpcObjects=[layer])

        layer.retry.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_retryDead(self, yesNoMock):
        layer_name = 'arbitrary-name'
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name=layer_name))
        job = mock.Mock()
        layer.parent = job

        self.layer_actions.retryDead(rpcObjects=[layer])

        job.retryFrames.assert_called_with(layer=[layer_name], state=[opencue.api.job_pb2.DEAD])

    @mock.patch('cuegui.Utils.questionBoxYesNo', return_value=True)
    def test_markdone(self, yesNoMock):
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(name='arbitrary-name'))
        layer.markdoneFrames = mock.Mock()

        self.layer_actions.markdone(rpcObjects=[layer])

        layer.markdoneFrames.assert_called()

    @mock.patch('cuegui.DependWizard.DependWizard')
    def test_dependWizard(self, dependWizardMock):
        layers = [opencue.wrappers.layer.Layer(opencue.compiled_proto.job_pb2.Layer())]

        self.layer_actions.dependWizard(rpcObjects=layers)

        dependWizardMock.assert_called_with(self.widgetMock, mock.ANY, layers)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getItem')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_reorder(self, getTextMock, getItemMock):
        original_range = '1-10'
        new_order = 'REVERSE'
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(range=original_range))
        layer.reorderFrames = mock.Mock()

        getTextMock.return_value = (original_range, True)
        getItemMock.return_value = (new_order, True)

        self.layer_actions.reorder(rpcObjects=[layer])

        layer.reorderFrames.assert_called_with(
            original_range, opencue.compiled_proto.job_pb2.REVERSE)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getInt')
    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_stagger(self, getTextMock, getIntMock):
        original_range = '1-10'
        new_step = 28
        layer = opencue.wrappers.layer.Layer(
            opencue.compiled_proto.job_pb2.Layer(range=original_range))
        layer.staggerFrames = mock.Mock()
        getTextMock.return_value = (original_range, True)
        getIntMock.return_value = (new_step, True)

        self.layer_actions.stagger(rpcObjects=[layer])

        layer.staggerFrames.assert_called_with(original_range, new_step)


if __name__ == '__main__':
    unittest.main()
