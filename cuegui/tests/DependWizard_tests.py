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


"""Tests for cuegui.DependWizard."""


import unittest

import mock
import PySide2.QtCore
import PySide2.QtGui
import PySide2.QtWidgets
import PySide2.QtTest

import opencue.compiled_proto.job_pb2
import opencue.wrappers.job

import cuegui.DependWizard
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class DependWizardTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        test_utils.createApplication()
        PySide2.QtGui.qApp.settings = PySide2.QtCore.QSettings()
        cuegui.Style.init()

        #self.show = opencue.wrappers.show.Show(opencue.compiled_proto.show_pb2.Show(name='fooShow'))
        #filterProto = opencue.compiled_proto.filter_pb2.Filter(
        #    id='filter-one-id', name='filterOne', order=1, enabled=True)
        #self.filter = opencue.wrappers.filter.Filter(filterProto)

        #getStubMock.return_value.GetFilters.return_value = \
        #    opencue.compiled_proto.show_pb2.ShowGetFiltersResponse(
        #        filters=opencue.compiled_proto.filter_pb2.FilterSeq(filters=[filterProto]))

        self.parentWidget = PySide2.QtWidgets.QWidget()
        self.job = opencue.wrappers.job.Job(
            opencue.compiled_proto.job_pb2.Job(id='arbitrary-job-id', show='arbitrary-show'))
        self.filterDialog = cuegui.DependWizard.DependWizard(self.parentWidget, [self.job])

    def test__init(self):
        pass
