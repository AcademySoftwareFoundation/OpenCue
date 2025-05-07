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

"""Module for classes related to limits."""

from opencue_proto import limit_pb2
from opencue import Cuebot


class Limit(object):
    """This class contains the grpc implementation related to a Limit."""

    def __init__(self, limit=None):
        self.data = limit
        self.stub = Cuebot.getStub('limit')

    def create(self):
        """Creates a new Limit from the current Limit object.

        :rtype:  opencue.wrappers.limit.Limit
        :return: the newly created Limit
        """
        return Limit(self.stub.Create(
            limit_pb2.LimitCreateRequest(name=self.name(), max_value=self.maxValue()),
            timeout=Cuebot.Timeout))

    def delete(self):
        """Deletes the limit."""
        self.stub.Delete(limit_pb2.LimitDeleteRequest(name=self.name()), timeout=Cuebot.Timeout)

    def find(self, name):
        """Finds an existing limit by its name.

        :type  name: str
        :param name: name of limit to find
        :rtype:  opencue.wrappers.limit.Limit
        :return: the limit found by name
        """
        return Limit(
            self.stub.Find(limit_pb2.LimitFindRequest(name=name), timeout=Cuebot.Timeout).limit)

    def get(self, limit_id):
        """Returns an existing limit by its id.

        :type  limit_id: str
        :param limit_id: id of limit to find
        :rtype:  opencue.wrappers.limit.Limit
        :return: the limit found by id.
        """
        return Limit(
            self.stub.Get(limit_pb2.LimitGetRequest(id=limit_id), timeout=Cuebot.Timeout).limit)

    def rename(self, newName):
        """Renames the limit.

        :type  newName: str
        :param newName: new limit name
        """
        self.stub.Rename(limit_pb2.LimitRenameRequest(old_name=self.name(), new_name=newName),
                         timeout=Cuebot.Timeout)
        self._update()

    def setMaxValue(self, maxValue):
        """Sets the maximum value of an existing limit.

        :type  maxValue: int
        :param maxValue: new limit maximum
        """
        self.stub.SetMaxValue(
            limit_pb2.LimitSetMaxValueRequest(name=self.name(), max_value=maxValue),
            timeout=Cuebot.Timeout)
        self._update()

    def _update(self):
        """Updates the current data object from the database."""
        self.data = self.stub.Get(limit_pb2.LimitGetRequest(id=self.id()), timeout=Cuebot.Timeout)

    def id(self):
        """Returns the limit id.

        :rtype:  str
        :return: the limit id
        """
        return self.data.id

    def name(self):
        """Returns the limit name.

        :rtype:  str
        :return: the limit name
        """
        if hasattr(self.data, 'name'):
            return self.data.name
        return ""

    def maxValue(self):
        """Returns the limit maximum.

        :rtype: int
        :return: the limit maximum
        """
        if hasattr(self.data, 'max_value'):
            return self.data.max_value
        return -1

    def currentRunning(self):
        """Returns the current amount of the limit in use.

        :rtype: int
        :return: current limit usage
        """
        if hasattr(self.data, 'current_running'):
            return self.data.current_running
        return -1
