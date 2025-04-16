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

"""Module for classes related to subscriptions."""

from opencue_proto import subscription_pb2
from opencue.cuebot import Cuebot


class Subscription(object):
    """This class contains the grpc implementation related to a Subscription.

    A subscription associates a show with an allocation. It allows the show to utilize resources
    within that allocation and determines the amount of resources the show is allowed to use at
    any given time."""

    def __init__(self, subscription=None):
        self.data = subscription
        self.stub = Cuebot.getStub('subscription')

    def find(self, name):
        """Returns a subscription by name.

        :type  name: str
        :param name: name of subscription to find
        :rtype:  opencue.wrappers.subscription.Subscription
        :return: the named subscription
        """
        response = self.stub.Find(
            subscription_pb2.SubscriptionFindRequest(name=name),
            timeout=Cuebot.Timeout)
        return Subscription(response.subscription)

    def get(self, subscription_id):
        """Returns a subscription by id.

        :type  subscription_id: str
        :param subscription_id: id of subscription to get
        :rtype:  opencue.wrappers.subscription.Subscription
        :return: the subscription of the id
        """
        response = self.stub.Get(
            subscription_pb2.SubscriptionGetRequest(id=subscription_id),
            timeout=Cuebot.Timeout)
        return Subscription(response.subscription)

    def setSize(self, size):
        """Sets subscription size; the number of cores the show is allowed to use consistently.

        :type  size: int
        :param size: the new subscription size
        """
        assert (isinstance(size, int)), "size is not expected type: int"
        self.stub.SetSize(
            subscription_pb2.SubscriptionSetSizeRequest(subscription=self.data, new_size=size),
            timeout=Cuebot.Timeout)

    def setBurst(self, burst):
        """Sets subscription burst size; the number of cores the show is allowed to burst to.

        :type  burst: int
        :param burst: the new burst size
        """
        assert (isinstance(burst, int)), "burst is not expected type: int"
        self.stub.SetBurst(
            subscription_pb2.SubscriptionSetBurstRequest(subscription=self.data, burst=burst),
            timeout=Cuebot.Timeout)

    def delete(self):
        """Deletes a subscription."""
        self.stub.Delete(
            subscription_pb2.SubscriptionDeleteRequest(subscription=self.data),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the subscription.

        :rtype:  str
        :return: id of the subscription
        """
        return self.data.id

    def name(self):
        """Returns the name of the subscription.

        Subscription names follow the format `<allocation name>.<show name>`, which can also be
        read as `<facility name>.<tag>.<show name>` due to the way allocations are named. For
        example the subscription name `local.general.testing` would indicate the show `testing`
        has a subscription to the `local.general` allocation. The `local.general` allocation
        indicates all hosts in the facility `local` containing the `general` tag.

        :rtype:  str
        :return: name of the subscription
        """
        return self.data.name

    def size(self):
        """Returns the subscription size.

        :rtype:  int
        :return: subscription size
        """
        return self.data.size

    def burst(self):
        """Returns the subscription burst size.

        :rtype:  int
        :return: subscription burst size
        """
        return self.data.burst

    def reservedCores(self):
        """Returns the current number of cores reserved in this subscription.

        :rtype:  float
        :return: reserved cores
        """
        return self.data.reserved_cores

    def show(self):
        """Returns the name of the show that this subscription is for.

        :rtype:  str
        :return: the name of the show that this subscription is for
        """
        return self.data.show_name

    def allocation(self):
        """Returns the allocation that this subscription is for.

        :rtype:  str
        :return: the allocation subscribed to
        """
        return self.data.allocation_name
