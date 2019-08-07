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

import cuegui.CueJobMonitorTree
import cuegui.Main
import cuegui.MenuActions
import opencue.compiled_proto.job_pb2
import opencue.wrappers.job


@mock.patch('PySide2.QtGui.qApp')
@mock.patch('opencue.cuebot.Cuebot.getStub')
class JobActionsTests(unittest.TestCase):
    def setUp(self):
        self.widgetMock = mock.Mock()
        self.job_actions = cuegui.MenuActions.JobActions(self.widgetMock, None, None, None)

    def test_unmonitor(self, getStubMock, qAppMock):
        self.job_actions.unmonitor()

        self.widgetMock.actionRemoveSelectedItems.assert_called_with()

    def test_view(self, getStubMock, qAppMock):
        job_name = 'arbitrary-name'
        job = opencue.wrappers.job.Job(opencue.compiled_proto.job_pb2.Job(name=job_name))

        self.job_actions.view(rpcObjects=[job])

        qAppMock.view_object.emit.assert_called_with(job)


if __name__ == '__main__':
    unittest.main()
