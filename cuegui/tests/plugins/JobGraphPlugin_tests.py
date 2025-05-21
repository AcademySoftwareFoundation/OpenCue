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


"""Tests for cuegui.plugins.MonitorJobGraphPlugin."""


import unittest

import mock

import opencue_proto.job_pb2
import opencue_proto.depend_pb2
import opencue.wrappers.job
import opencue.wrappers.layer
import opencue.wrappers.depend

import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtTest
import qtpy.QtWidgets

import cuegui.Main
import cuegui.plugins.MonitorJobGraphPlugin
import cuegui.JobMonitorGraph
import cuegui.Style
from .. import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class MonitorJobGraphPluginTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
    @mock.patch('opencue.api.getJob')
    def setUp(self, getJobMock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.main_window = qtpy.QtWidgets.QMainWindow()

        self.job = opencue.wrappers.job.Job(opencue_proto.job_pb2.Job(id='foo'))
        layer = opencue.wrappers.layer.Layer(opencue_proto.job_pb2.Layer(name='layer1'))
        depend = opencue.wrappers.depend.Depend(opencue_proto.depend_pb2.Depend())
        layer.getWhatDependsOnThis = lambda: [depend]
        self.job.getLayers = lambda: [layer]
        self.jobGraph = cuegui.JobMonitorGraph.JobMonitorGraph(self.main_window)
        self.jobGraph.setJob(self.job)

    def test_setup(self):
        pass

    def test_job(self):
        self.assertNotEqual(None, self.jobGraph.getJob())
