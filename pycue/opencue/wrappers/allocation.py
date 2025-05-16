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

"""Module for classes related to OpenCue allocations."""

from opencue_proto import facility_pb2
from opencue_proto import host_pb2
from opencue.cuebot import Cuebot
import opencue.wrappers.host
import opencue.wrappers.subscription


class Allocation(object):
    """This class contains the grpc implementation related to an Allocation."""

    def __init__(self, allocation=None):
        self.data = allocation
        self.stub = Cuebot.getStub('allocation')

    def delete(self):
        """Deletes the allocation."""
        self.stub.Delete(
            facility_pb2.AllocDeleteRequest(allocation=self.data),
            timeout=Cuebot.Timeout)

    def getHosts(self):
        """Returns the list of hosts for the allocation.

        :rtype:  list<opencue.wrappers.host.Host>
        :return: list of hosts
        """
        hostSeq = self.stub.GetHosts(facility_pb2.AllocGetHostsRequest(allocation=self.data),
                                     timeout=Cuebot.Timeout).hosts
        return [opencue.wrappers.host.Host(h) for h in hostSeq.hosts]

    def getSubscriptions(self):
        """Returns the subscriptions of the allocation.

        :rtype:  list<opencue.wrappers.subscription.Subscription>
        :return: a list of subscriptions
        """
        subscriptionSeq = self.stub.GetSubscriptions(
            facility_pb2.AllocGetSubscriptionsRequest(allocation=self.data),
            timeout=Cuebot.Timeout).subscriptions
        return [opencue.wrappers.subscription.Subscription(sub)
                for sub in subscriptionSeq.subscriptions]

    def reparentHosts(self, hosts):
        """Moves the given hosts into the allocation.

        :type  hosts: list<opencue.wrappers.host.Host>
        :param hosts: the hosts to move to this allocation
        """
        hostSeq = host_pb2.HostSeq()
        # pylint: disable=no-member
        hostSeq.hosts.extend([host.data for host in hosts])
        # pylint: enable=no-member
        self.stub.ReparentHosts(
            facility_pb2.AllocReparentHostsRequest(allocation=self.data, hosts=hostSeq),
            timeout=Cuebot.Timeout)

    def reparentHostIds(self, hostIds):
        """Moves the hosts identified by the given host ids into the allocation.

        :type  hostIds: list<str>
        :param hostIds: the host ids to move to this allocation
        """
        hosts = [opencue.wrappers.host.Host(host_pb2.Host(id=hostId)) for hostId in hostIds]
        self.reparentHosts(hosts)

    def setName(self, name):
        """Sets a new name for the allocation.

        :type  name: str
        :param name: the new name
        """
        self.stub.SetName(
            facility_pb2.AllocSetNameRequest(allocation=self.data, name=name),
            timeout=Cuebot.Timeout)

    def setTag(self, tag):
        """Sets a new tag for the allocation.

        :type  tag: str
        :param tag: the new tag
        """
        self.stub.SetTag(
            facility_pb2.AllocSetTagRequest(allocation=self.data, tag=tag),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the allocation.

        :rtype:  str
        :return: the id of the allocation
        """
        return self.data.id

    def name(self):
        """Returns the name of the allocation.

        :rtype:  str
        :return: the name of the allocation
        """
        return self.data.name

    def tag(self):
        """Returns the tag of the allocation.

        :rtype:  str
        :return: the tag of the allocation
        """
        return self.data.tag

    def totalCores(self):
        """Returns the total number of cores in the allocation.

        :rtype:  float
        :return: total number of cores in the allocation
        """
        return self.data.stats.cores

    def totalAvailableCores(self):
        """Returns the total number of cores available for booking in the allocation.

        :rtype:  float
        :return: total number of cores in the allocation
        """
        return self.data.stats.available_cores

    def totalIdleCores(self):
        """Returns the total number of idle cores in the allocation.

        :rtype:  float
        :return: total number of idle cores in the allocation
        """
        return self.data.stats.idle_cores

    def totalRunningCores(self):
        """Returns the total number of running cores in the allocation.

        Each 100 returned is the same as 1 physical core.

        :rtype:  float
        :return: total number of running cores in the allocation
        """
        return self.data.stats.running_cores

    def totalLockedCores(self):
        """Returns the total number of locked cores in the allocation.

        Each 100 returned is the same as 1 physical core.

        :rtype:  float
        :return: total number of locked cores in the allocation
        """
        return self.data.stats.locked_cores

    def totalGpus(self):
        """Returns the total number of gpus in the allocation.

        :rtype:  float
        :return: total number of gpus in the allocation
        """
        return self.data.stats.gpus

    def totalAvailableGpus(self):
        """Returns the total number of gpus available for booking in the allocation.

        :rtype:  float
        :return: total number of gpus in the allocation
        """
        return self.data.stats.available_gpus

    def totalIdleGpus(self):
        """Returns the total number of idle gpus in the allocation.

        :rtype:  float
        :return: total number of idle gpus in the allocation
        """
        return self.data.stats.idle_gpus

    def totalRunningGpus(self):
        """Returns the total number of running gpus in the allocation.

        :rtype:  float
        :return: total number of running gpus in the allocation
        """
        return self.data.stats.running_gpus

    def totalLockedGpus(self):
        """Returns the total number of locked gpus in the allocation.

        :rtype:  float
        :return: total number of locked gpus in the allocation
        """
        return self.data.stats.locked_gpus

    def totalHosts(self):
        """Returns the total number of hosts in the allocation.

        :rtype:  int
        :return: total number of hosts in the allocation
        """
        return self.data.stats.hosts

    def totalLockedHosts(self):
        """Returns the total number of locked hosts in the allocation.

        :rtype:  int
        :return: total number of locked hosts in the allocation
        """
        return self.data.stats.locked_hosts

    def totalDownHosts(self):
        """Returns the total number of down hosts in the allocation.

        :rtype:  int
        :return: total number of down hosts in the allocation
        """
        return self.data.stats.down_hosts
