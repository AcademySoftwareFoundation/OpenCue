#!/usr/bin/env python

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

"""Tests for `opencue.wrappers.task`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import task_pb2
import opencue.wrappers.task


@mock.patch('opencue.cuebot.Cuebot.getStub')
class TaskTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = task_pb2.TaskDeleteResponse()
        getStubMock.return_value = stubMock

        task = opencue.wrappers.task.Task(
            task_pb2.Task(name='testTask'))
        task.delete()

        stubMock.Delete.assert_called_with(
            task_pb2.TaskDeleteRequest(task=task.data), timeout=mock.ANY)

    def testSetMinCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Save.return_value = task_pb2.TaskSetMinCoresResponse()
        getStubMock.return_value = stubMock

        minCores = 10

        task = opencue.wrappers.task.Task(
            task_pb2.Task(name='testTask'))
        task.setMinCores(minCores)

        stubMock.SetMinCores.assert_called_with(
            task_pb2.TaskSetMinCoresRequest(task=task.data, new_min_cores=minCores),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
