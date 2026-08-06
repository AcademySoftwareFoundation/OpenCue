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

"""Tests for `opencue.wrappers.department`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import department_pb2
from opencue_proto import task_pb2
import opencue.wrappers.department


TEST_DEPARTMENT_ID = 'ddd-dddd-ddd'
TEST_DEPARTMENT_NAME = 'testDepartment'
TEST_SHOT = 'testShot'
TEST_TI_TASK = 'testTiTask'
TEST_MIN_CORES = 42


@mock.patch('opencue.cuebot.Cuebot.getStub')
class DepartmentTests(unittest.TestCase):

    def testId(self, getStubMock):
        department = opencue.wrappers.department.Department(
            department_pb2.Department(id=TEST_DEPARTMENT_ID))

        self.assertEqual(department.id(), TEST_DEPARTMENT_ID)

    def testName(self, getStubMock):
        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))

        self.assertEqual(department.name(), TEST_DEPARTMENT_NAME)

    def testAddTask(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.AddTask.return_value = department_pb2.DeptAddTaskResponse(
            task=task_pb2.Task(shot=TEST_SHOT, min_cores=TEST_MIN_CORES))
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        task = department.addTask(TEST_SHOT, TEST_MIN_CORES)

        stubMock.AddTask.assert_called_with(
            department_pb2.DeptAddTaskRequest(
                department=department.data, shot=TEST_SHOT, min_cores=TEST_MIN_CORES),
            timeout=mock.ANY)
        self.assertEqual(task.data.shot, TEST_SHOT)

    def testAddTasks(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.AddTasks.return_value = department_pb2.DeptAddTasksResponse(
            tasks=task_pb2.TaskSeq(tasks=[task_pb2.Task(shot=TEST_SHOT)]))
        getStubMock.return_value = stubMock

        taskMap = {TEST_SHOT: TEST_MIN_CORES}
        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        tasks = department.addTasks(taskMap)

        stubMock.AddTasks.assert_called_with(
            department_pb2.DeptAddTasksRequest(department=department.data, tmap=taskMap),
            timeout=mock.ANY)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].data.shot, TEST_SHOT)

    def testClearTaskAdjustments(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ClearTaskAdjustments.return_value = \
            department_pb2.DeptClearTaskAdjustmentsResponse()
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        department.clearTaskAdjustments()

        stubMock.ClearTaskAdjustments.assert_called_with(
            department_pb2.DeptClearTaskAdjustmentsRequest(department=department.data),
            timeout=mock.ANY)

    def testClearTasks(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ClearTasks.return_value = department_pb2.DeptClearTasksResponse()
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        department.clearTasks()

        stubMock.ClearTasks.assert_called_with(
            department_pb2.DeptClearTasksRequest(department=department.data),
            timeout=mock.ANY)

    def testDisableTiManaged(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.DisableTiManaged.return_value = department_pb2.DeptDisableTiManagedResponse()
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        department.disableTiManaged()

        stubMock.DisableTiManaged.assert_called_with(
            department_pb2.DeptDisableTiManagedRequest(department=department.data),
            timeout=mock.ANY)

    def testEnableTiManaged(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EnableTiManaged.return_value = department_pb2.DeptEnableTiManagedResponse()
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        department.enableTiManaged(TEST_TI_TASK, TEST_MIN_CORES)

        stubMock.EnableTiManaged.assert_called_with(
            department_pb2.DeptEnableTiManagedRequest(
                department=department.data, ti_task=TEST_TI_TASK, managed_cores=TEST_MIN_CORES),
            timeout=mock.ANY)

    def testGetTasks(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetTasks.return_value = department_pb2.DeptGetTasksResponse(
            tasks=task_pb2.TaskSeq(tasks=[task_pb2.Task(shot=TEST_SHOT)]))
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        tasks = department.getTasks()

        stubMock.GetTasks.assert_called_with(
            department_pb2.DeptGetTasksRequest(department=department.data),
            timeout=mock.ANY)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].data.shot, TEST_SHOT)

    def testReplaceTasks(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReplaceTasks.return_value = department_pb2.DeptReplaceTaskResponse(
            tasks=task_pb2.TaskSeq(tasks=[task_pb2.Task(shot=TEST_SHOT)]))
        getStubMock.return_value = stubMock

        taskMap = {TEST_SHOT: TEST_MIN_CORES}
        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        tasks = department.replaceTasks(taskMap)

        stubMock.ReplaceTasks.assert_called_with(
            department_pb2.DeptReplaceTaskRequest(department=department.data, tmap=taskMap),
            timeout=mock.ANY)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].data.shot, TEST_SHOT)

    def testSetManagedCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetManagedCores.return_value = department_pb2.DeptSetManagedCoresResponse()
        getStubMock.return_value = stubMock

        department = opencue.wrappers.department.Department(
            department_pb2.Department(name=TEST_DEPARTMENT_NAME))
        department.setManagedCores(TEST_MIN_CORES)

        stubMock.SetManagedCores.assert_called_with(
            department_pb2.DeptSetManagedCoresRequest(
                department=department.data, managed_cores=TEST_MIN_CORES),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
