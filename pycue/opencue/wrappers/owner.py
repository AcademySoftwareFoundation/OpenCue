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

"""Module for classes related to owners."""

from opencue_proto import host_pb2
from opencue import Cuebot
import opencue.wrappers.deed
import opencue.wrappers.host


class Owner(object):
    """This class contains the grpc implementation related to an Owner."""

    def __init__(self, owner=None):
        self.data = owner
        self.stub = Cuebot.getStub('owner')

    def delete(self):
        """Deletes the owner record."""
        self.stub.Delete(host_pb2.OwnerDeleteRequest(owner=self.data), timeout=Cuebot.Timeout)

    def getDeeds(self):
        """Returns the list of deeds for the owner.

        :rtype:  list<opencue.wrappers.deed.Deed Wrapper>
        :return: the list of deeds associated with this owner
        """
        response = self.stub.GetDeeds(host_pb2.OwnerGetDeedsRequest(owner=self.data),
                                      timeout=Cuebot.Timeout)
        return [opencue.wrappers.deed.Deed(deed) for deed in response.deeds.deeds]

    def getHosts(self):
        """Returns a list of all hosts this owner is responsible for.

        :rtype:  list<opencue.wrappers.host.Host>
        :return: list of hosts owned by this owner
        """
        response = self.stub.GetHosts(host_pb2.OwnerGetHostsRequest(owner=self.data),
                                      timeout=Cuebot.Timeout)
        return [opencue.wrappers.host.Host(host) for host in response.hosts.hosts]

    def getOwner(self, name):
        """Returns an owner by name.

        :type  name: str
        :param name: Name of the owner
        :rtype: opencue.wrappers.owner.Owner
        :return: owner that matches the specified name
        """
        return Owner(self.stub.GetOwner(host_pb2.OwnerGetOwnerRequest(name=name),
                                        timeout=Cuebot.Timeout).owner)

    def setShow(self, show):
        """Sets the show for the owner.

        :type  show: str
        :param show: name of the show
        """
        self.stub.SetShow(host_pb2.OwnerSetShowRequest(owner=self.data, show=show),
                          timeout=Cuebot.Timeout)

    def takeOwnership(self, host):
        """Sets the hosts for the owner.

        :type  host: str
        :param host: the name of the host to take ownership of
        """
        self.stub.TakeOwnership(host_pb2.OwnerTakeOwnershipRequest(owner=self.data, host=host),
                                timeout=Cuebot.Timeout)

    def hostCount(self):
        """Returns the number of hosts owned by this owner.

        :rtype:  int
        :return: number of hosts owned by this owner
        """
        return self.data.host_count

    def id(self):
        """Returns the owner id.

        :rtype: str
        :return: the owner id"""
        return self.data.id

    def name(self):
        """Returns the owner name.

        :rtype:  str
        :return: the owner name"""
        return self.data.name

    def show(self):
        """Returns the name of the show of the owner.

        :rtype:  str
        :return: the name of the show of the owner"""
        return self.data.show
