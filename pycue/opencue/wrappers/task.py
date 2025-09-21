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

"""Module for classes related to tasks."""

from opencue_proto import task_pb2
from opencue.cuebot import Cuebot


class Task(object):
    """This class contains the grpc implementation related to a Task."""

    def __init__(self, task=None):
        self.data = task
        self.stub = Cuebot.getStub('task')

    def id(self):
        """Returns the unique id of the task.

        :rtype: str
        :return: task id
        """
        return self.data.id

    def setMinCores(self, minCores):
        """Sets the minimum amount of cores for the task.

        :type  minCores: int
        :param minCores: the minimum number of cores the task needs
        """
        self.stub.SetMinCores(
            task_pb2.TaskSetMinCoresRequest(task=self.data, new_min_cores=minCores),
            timeout=Cuebot.Timeout)

    def delete(self):
        """Deletes the task."""
        self.stub.Delete(task_pb2.TaskDeleteRequest(task=self.data), timeout=Cuebot.Timeout)
