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

"""Tests for `opencue.wrappers.allocation`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import facility_pb2
from opencue_proto import host_pb2
from opencue_proto import subscription_pb2
import opencue.wrappers.allocation
import opencue.wrappers.host


TEST_ALLOC_NAME = 'test_allocation'
TEST_ALLOC_TAG = 'test_tag'
TEST_HOST_NAME = 'test_host'
TEST_HOST_ID = 'hhh-hhhh-hhh'
TEST_SUBSCRIPTION_NAME = 'test_subscription'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class AllocationTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = facility_pb2.AllocDeleteResponse()
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(
            facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        alloc.delete()

        stubMock.Delete.assert_called_with(
            facility_pb2.AllocDeleteRequest(allocation=alloc.data), timeout=mock.ANY)

    def testGetHosts(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetHosts.return_value = facility_pb2.AllocGetHostsResponse(
            hosts=host_pb2.HostSeq(
                hosts=[host_pb2.Host(name=TEST_HOST_NAME)]))
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(
            facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        hosts = alloc.getHosts()

        stubMock.GetHosts.assert_called_with(
            facility_pb2.AllocGetHostsRequest(allocation=alloc.data), timeout=mock.ANY)
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].name(), TEST_HOST_NAME)

    def testGetSubscriptions(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetSubscriptions.return_value = facility_pb2.AllocGetSubscriptionsResponse(
            subscriptions=subscription_pb2.SubscriptionSeq(
                subscriptions=[subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME)]))
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(
            facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        subscriptions = alloc.getSubscriptions()

        stubMock.GetSubscriptions.assert_called_with(
            facility_pb2.AllocGetSubscriptionsRequest(allocation=alloc.data), timeout=mock.ANY)
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0].name(), TEST_SUBSCRIPTION_NAME)

    def testReparentHosts(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReparentHosts.return_value = facility_pb2.AllocReparentHostsResponse()
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(
            facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        hosts = [opencue.wrappers.host.Host(host_pb2.Host(name=TEST_HOST_NAME))]
        alloc.reparentHosts(hosts)

        stubMock.ReparentHosts.assert_called_with(
            facility_pb2.AllocReparentHostsRequest(
                allocation=alloc.data,
                hosts=host_pb2.HostSeq(hosts=[host.data for host in hosts])),
            timeout=mock.ANY)

    def testReparentHostIds(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReparentHosts.return_value = facility_pb2.AllocReparentHostsResponse()
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(
            facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        hostIds = [TEST_HOST_ID]
        alloc.reparentHostIds(hostIds)
        hosts = [host_pb2.Host(id=TEST_HOST_ID)]

        stubMock.ReparentHosts.assert_called_with(
            facility_pb2.AllocReparentHostsRequest(
                allocation=alloc.data, hosts=host_pb2.HostSeq(hosts=hosts)), timeout=mock.ANY)

    def testSetName(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetName.return_value = facility_pb2.AllocSetNameResponse()
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(facility_pb2.Allocation())
        alloc.setName(TEST_ALLOC_NAME)

        stubMock.SetName.assert_called_with(
            facility_pb2.AllocSetNameRequest(allocation=alloc.data, name=TEST_ALLOC_NAME),
            timeout=mock.ANY)

    def setTag(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetTag.return_value = facility_pb2.AllocSetTagResponse()
        getStubMock.return_value = stubMock

        alloc = opencue.wrappers.allocation.Allocation(facility_pb2.Allocation())
        alloc.setTag(TEST_ALLOC_TAG)

        stubMock.SetTag.assert_called_with(
            facility_pb2.AllocSetTagRequest(allocation=alloc.data, tag=TEST_ALLOC_TAG),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
