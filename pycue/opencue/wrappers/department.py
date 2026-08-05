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

"""Module for classes related to departments."""

from opencue_proto import department_pb2
from opencue.cuebot import Cuebot
import opencue.wrappers.task


class Department(object):
    """This class contains the grpc implementation related to a Department."""

    def __init__(self, department=None):
        self.data = department
        self.stub = Cuebot.getStub('department')

    def addTask(self, shot, minCores):
        """Adds a task to the department and returns it.

        :type  shot: str
        :param shot: name of the shot the task is for
        :type  minCores: float
        :param minCores: the minimum number of cores the task needs
        :rtype:  opencue.wrappers.task.Task
        :return: the newly created task
        """
        response = self.stub.AddTask(
            department_pb2.DeptAddTaskRequest(
                department=self.data, shot=shot, min_cores=minCores),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.task.Task(response.task)

    def addTasks(self, taskMap):
        """Adds a map of tasks to the department and returns them as a list.

        :type  taskMap: dict<str, int>
        :param taskMap: map of shot names to minimum core units
        :rtype:  list<opencue.wrappers.task.Task>
        :return: the newly created tasks
        """
        response = self.stub.AddTasks(
            department_pb2.DeptAddTasksRequest(department=self.data, tmap=taskMap),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.task.Task(task) for task in response.tasks.tasks]

    def clearTaskAdjustments(self):
        """Clears all manual task adjustments to managed tasks.

        This won't do anything unless the department is Track-It managed.
        """
        self.stub.ClearTaskAdjustments(
            department_pb2.DeptClearTaskAdjustmentsRequest(department=self.data),
            timeout=Cuebot.Timeout)

    def clearTasks(self):
        """Clears all tasks from the department."""
        self.stub.ClearTasks(
            department_pb2.DeptClearTasksRequest(department=self.data),
            timeout=Cuebot.Timeout)

    def disableTiManaged(self):
        """Disables Track-It management; this also clears all tasks."""
        self.stub.DisableTiManaged(
            department_pb2.DeptDisableTiManagedRequest(department=self.data),
            timeout=Cuebot.Timeout)

    def enableTiManaged(self, tiTask, managedCores):
        """Enables Track-It management.

        This will pull a task list from Track-It and keep it synced.

        :type  tiTask: str
        :param tiTask: name of the Track-It task to manage the department with
        :type  managedCores: float
        :param managedCores: the number of cores to split up among the active tasks
        """
        self.stub.EnableTiManaged(
            department_pb2.DeptEnableTiManagedRequest(
                department=self.data, ti_task=tiTask, managed_cores=managedCores),
            timeout=Cuebot.Timeout)

    def getTasks(self):
        """Returns the list of tasks for the department.

        :rtype:  list<opencue.wrappers.task.Task>
        :return: tasks of the department
        """
        response = self.stub.GetTasks(
            department_pb2.DeptGetTasksRequest(department=self.data),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.task.Task(task) for task in response.tasks.tasks]

    def replaceTasks(self, taskMap):
        """Replaces a map of tasks; existing tasks are updated, new tasks are inserted.

        :type  taskMap: dict<str, int>
        :param taskMap: map of shot names to minimum core units
        :rtype:  list<opencue.wrappers.task.Task>
        :return: the resulting tasks
        """
        response = self.stub.ReplaceTasks(
            department_pb2.DeptReplaceTaskRequest(department=self.data, tmap=taskMap),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.task.Task(task) for task in response.tasks.tasks]

    def setManagedCores(self, managedCores):
        """Sets the minimum number of cores for the department to manage between its tasks.

        :type  managedCores: float
        :param managedCores: the number of cores to manage between the tasks
        """
        self.stub.SetManagedCores(
            department_pb2.DeptSetManagedCoresRequest(
                department=self.data, managed_cores=managedCores),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the unique id of the department.

        :rtype:  str
        :return: department id
        """
        return self.data.id

    def name(self):
        """Returns the name of the department.

        :rtype:  str
        :return: department name
        """
        return self.data.name
