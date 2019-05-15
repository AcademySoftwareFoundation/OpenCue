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

Module: subscription.py - opencue Library implementation of a subscription

"""

from opencue.compiled_proto import subscription_pb2
from opencue.cuebot import Cuebot


class Subscription(object):

    def __init__(self, subscription=None):
        self.data = subscription
        self.stub = Cuebot.getStub('subscription')

    def find(self, name):
        response = self.stub.Find(
            subscription_pb2.SubscriptionFindRequest(name=name),
            timeout=Cuebot.Timeout)
        return Subscription(response.subscription)

    def get(self, id):
        response = self.stub.Get(
            subscription_pb2.SubscriptionGetRequest(id=id),
            timeout=Cuebot.Timeout)
        return Subscription(response.subscription)

    def setSize(self, size):
        self.stub.SetSize(
            subscription_pb2.SubscriptionSetSizeRequest(subscription=self.data, new_size=size),
            timeout=Cuebot.Timeout)

    def setBurst(self, burst):
        self.stub.SetBurst(
            subscription_pb2.SubscriptionSetBurstRequest(subscription=self.data, burst=burst),
            timeout=Cuebot.Timeout)

    def delete(self):
        self.stub.Delete(
            subscription_pb2.SubscriptionDeleteRequest(subscription=self.data),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the subscription
        @rtype:  str
        @return: Frame uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the subscription
        @rtype:  str
        @return: Subscription name"""
        return self.data.name

    def size(self):
        """Returns the subscription size
        @rtype:  int
        @return: Subscription size"""
        return self.data.size

    def burst(self):
        """Returns the subscription burst
        @rtype:  int
        @return: Allowed burst"""
        return self.data.burst

    def reservedCores(self):
        """Returns the current number reserved in this subscription
        @rtype:  float
        @return: Total running cores"""
        return self.data.reserved_cores

    def show(self):
        """Returns the show that this subscription is for
        @rtype:  str
        @return: The show that this subscription is for"""
        return self.data.show_name

    def allocation(self):
        """Returns the allocation that this subscription is subscribed to
        @rtype:  str
        @return: The allocation subscribed to"""
        return self.data.allocation_name

