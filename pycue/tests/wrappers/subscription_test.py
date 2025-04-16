#!/usr/bin/env python

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

"""Tests for `opencue.wrappers.subscription`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import subscription_pb2
import opencue.wrappers.subscription


TEST_SUBSCRIPTION_ID = 'aaaa-aaa-aaaa'
TEST_SUBSCRIPTION_NAME = 'testSubscription'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class SubscriptionTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = subscription_pb2.SubscriptionDeleteResponse()
        getStubMock.return_value = stubMock

        subscription = opencue.wrappers.subscription.Subscription(
            subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME))
        subscription.delete()

        stubMock.Delete.assert_called_with(
            subscription_pb2.SubscriptionDeleteRequest(subscription=subscription.data),
            timeout=mock.ANY)

    def testFind(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = subscription_pb2.SubscriptionFindResponse(
            subscription=subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME))
        getStubMock.return_value = stubMock

        expected = opencue.wrappers.subscription.Subscription(
            subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME))
        wrapper = opencue.wrappers.subscription.Subscription()
        subscription = wrapper.find(name=TEST_SUBSCRIPTION_NAME)

        stubMock.Find.assert_called_with(
            subscription_pb2.SubscriptionFindRequest(name=TEST_SUBSCRIPTION_NAME),
            timeout=mock.ANY)
        self.assertEqual(expected.name(), subscription.name())

    def testGet(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Get.return_value = subscription_pb2.SubscriptionGetResponse(
            subscription=subscription_pb2.Subscription(id=TEST_SUBSCRIPTION_ID,
                                                       name=TEST_SUBSCRIPTION_NAME))
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.subscription.Subscription()
        subscription = wrapper.get(TEST_SUBSCRIPTION_ID)

        stubMock.Get.assert_called_with(
            subscription_pb2.SubscriptionGetRequest(id=TEST_SUBSCRIPTION_ID),
            timeout=mock.ANY)
        self.assertEqual(subscription.id(), TEST_SUBSCRIPTION_ID)

    def testSetBurst(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetBurst.return_value = subscription_pb2.SubscriptionSetBurstResponse()
        getStubMock.return_value = stubMock

        subscription = opencue.wrappers.subscription.Subscription(
            subscription_pb2.Subscription(name='testSubscription'))
        subscription.setBurst(15)

        stubMock.SetBurst.assert_called_with(
            subscription_pb2.SubscriptionSetBurstRequest(subscription=subscription.data, burst=15),
            timeout=mock.ANY)

    def testSetSize(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetSize.return_value = subscription_pb2.SubscriptionSetSizeResponse()
        getStubMock.return_value = stubMock

        subscription = opencue.wrappers.subscription.Subscription(
            subscription_pb2.Subscription(name='testSubscription'))
        subscription.setSize(16)

        stubMock.SetSize.assert_called_with(
            subscription_pb2.SubscriptionSetSizeRequest(
                subscription=subscription.data, new_size=16),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
