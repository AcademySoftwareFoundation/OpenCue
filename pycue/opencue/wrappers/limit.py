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


"""
Project: opencue Library

Module: limit.py - opencue Library implementation of a limit

"""

from opencue import Cuebot
from opencue.compiled_proto import limit_pb2


class Limit(object):
    """This class contains the grpc implementation related to a Limit."""

    def __init__(self, limit=None):
        """Limit class initialization"""
        self.data = limit
        self.stub = Cuebot.getStub('limit')

    def create(self):
        """Create a new Limit from the current Limit object.
        
        :rtype: Limit
        :return: The newly created Limit
        """
        return Limit(self.stub.Create(
            limit_pb2.LimitCreateRequest(name=self.name(), max_value=self.maxValue()),
            timeout=Cuebot.Timeout))

    def delete(self):
        """Delete the limit record"""
        self.stub.Delete(limit_pb2.LimitDeleteRequest(name=self.name()), timeout=Cuebot.Timeout)

    def find(self, name):
        """Find an existing limit by it's name.
        
        :type name: str
        :param name: Name of limit to find.
        :rtype: opencue.wrappers.limit.Limit
        :return: The limit found by name.
        """
        return Limit(self.stub.Find(limit_pb2.LimitFindRequest(name=name), timeout=Cuebot.Timeout).limit)

    def get(self, id):
        """Return an existing limit by it's id.
        
        :type id: str
        :param id: Name of limit to find.
        :rtype: opencue.wrappers.limit.Limit
        :return: The limit found by id.
        """
        return Limit(self.stub.Get(limit_pb2.LimitGetRequest(id=id), timeout=Cuebot.Timeout).limit)

    def rename(self, newName):
        """Rename the current limit to the provided newName.
        
        :type newName: str
        :param newName: Name to rename the limit to.
        """
        self.stub.Rename(limit_pb2.LimitRenameRequest(old_name=self.name(), new_name=newName),
                         timeout=Cuebot.Timeout)
        self._update()

    def setMaxValue(self, maxValue):
        """Set the max value of an existing limit.
        
        :type maxValue: int
        :param maxValue: Max value number to set limit to.
        """
        self.stub.SetMaxValue(limit_pb2.LimitSetMaxValueRequest(name=self.name(), max_value=maxValue),
                              timeout=Cuebot.Timeout)
        self._update()

    def _update(self):
        """Update the current data object from the DB."""
        self.data = self.stub.Get(limit_pb2.LimitGetRequest(id=self.id()), timeout=Cuebot.Timeout)

    def id(self):
        return self.data.id

    def name(self):
        if hasattr(self.data, 'name'):
            return self.data.name
        else:
            return ""

    def maxValue(self):
        if hasattr(self.data, 'max_value'):
            return self.data.max_value
        else:
            return -1

    def currentRunning(self):
        if hasattr(self.data, 'current_running'):
            return self.data.current_running
        else:
            return -1
