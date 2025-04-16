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

"""Module for classes related to deeds."""

from opencue_proto import host_pb2
from opencue.cuebot import Cuebot
# pylint: disable=cyclic-import
import opencue.wrappers.host
import opencue.wrappers.owner


class Deed(object):
    """This class contains the grpc implementation related to a Deed."""

    def __init__(self, deed=None):
        self.data = deed
        self.stub = Cuebot.getStub('comment')

    def delete(self):
        """Deletes the deed."""
        self.stub.Delete(host_pb2.DeedDeleteRequest(deed=self.data), timeout=Cuebot.Timeout)

    def getHost(self):
        """Returns the host for the deed.

        :rtype:  opencue.wrappers.host.Host
        :return: deed host
        """
        return opencue.wrappers.host.Host(
            self.stub.GetHost(host_pb2.DeedGetHostRequest(deed=self.data),
                              timeout=Cuebot.Timeout).host)

    def getOwner(self):
        """Returns the owner of the deed.

        :rtype:  opencue.wrappers.owner.Owner
        :return: deed owner
        """
        return opencue.wrappers.owner.Owner(
            self.stub.GetOwner(host_pb2.DeedGetOwnerRequest(deed=self.data),
                               timeout=Cuebot.Timeout).owner)

    def id(self):
        """Returns the id of the deed.

        :rtype:  str
        :return: deed id
        """
        return self.data.id

    def host(self):
        """Returns the name of the host associated with the deed.

        :rtype:  str
        :return: name of the deed host
        """
        return self.data.host

    def owner(self):
        """Returns the name of the owner of the deed.

        :rtype:  str
        :return: name of the deed owner
        """
        return self.data.owner

    def show(self):
        """Returns the name of the show of the deed.

        :rtype:  str
        :return: name of the deed show
        """
        return self.data.show
