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

Module: owner.py - opencue Library implementation of a owner

"""

import opencue.wrappers.deed
import opencue.wrappers.host
from opencue import Cuebot
from opencue.compiled_proto import host_pb2


class Owner(object):
    """This class contains the grpc implementation related to an Owner."""

    def __init__(self, owner=None):
        """Host class initialization"""
        self.data = owner
        self.stub = Cuebot.getStub('owner')

    def delete(self):
        """Delete the owner record"""
        self.stub.Delete(host_pb2.OwnerDeleteRequest(owner=self.data), timeout=Cuebot.Timeout)

    def getDeeds(self):
        """Return the list of deeds for the owner.

        :rtype:  List<opencue.wrappers..deed.Deed Wrapper>
        :return: The list of deeds associated with this owner."""
        response = self.stub.GetDeeds(host_pb2.OwnerGetDeedsRequest(owner=self.data),
                                      timeout=Cuebot.Timeout)
        return [opencue.wrappers.deed.Deed(deed) for deed in response.deeds.deeds]

    def getHosts(self):
        """Get a list of all hosts this owner is responsible for.

        :rtype:  List<opencue.wrappers.host.Host Wrapper>
        :return: List of hosts the owned by this owner."""
        response = self.stub.GetHosts(host_pb2.OwnerGetHostsRequest(owner=self.data),
                                      timeout=Cuebot.Timeout)
        return [opencue.wrappers.host.Host(host) for host in response.hosts.hosts]

    def getOwner(self, name):
        """Return an owner by name.

        :type:   str
        :param:  Name of the owner
        :rtype:  opencue.wrappers.owner.Owner
        :return: Owner that matches the specified name"""
        return Owner(self.stub.GetOwner(host_pb2.OwnerGetOwnerRequest(name=name),
                                        timeout=Cuebot.Timeout).owner)

    def setShow(self, show):
        """Set the show for the owner.

        :type:  str
        :param: name of the show"""
        self.stub.SetShow(host_pb2.OwnerSetShowRequest(owner=self.data, show=show),
                          timeout=Cuebot.Timeout)

    def takeOwnership(self, host):
        """Set the hosts new owner settings."""
        self.stub.TakeOwnership(host_pb2.OwnerTakeOwnershipRequest(owner=self.data, host=host),
                                timeout=Cuebot.Timeout)

    def hostCount(self):
        return self.data.host_count

    def id(self):
        return self.data.id

    def name(self):
        return self.data.name

    def show(self):
        return self.data.show
