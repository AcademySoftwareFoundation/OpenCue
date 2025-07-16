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

"""Tests for the opencue.wrappers.show module."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import facility_pb2
from opencue_proto import filter_pb2
from opencue_proto import host_pb2
from opencue_proto import job_pb2
from opencue_proto import service_pb2
from opencue_proto import show_pb2
from opencue_proto import subscription_pb2
import opencue.wrappers.allocation
import opencue.wrappers.show


TEST_ALLOCATION_ID = 'aaa-zzz-fff'
TEST_SHOW_NAME = 'pipe'
TEST_OWNER_NAME = 'opencue'
TEST_FILTER_NAME = 'unittest_filter'
TEST_SERVICE_NAME = 'unittest_service'
TEST_SUBSCRIPTION_NAME = 'unittest_subscription'
TEST_SUBSCRIPTION_SIZE = 1000
TEST_SUBSCRIPTION_BURST = 1200
TEST_MIN_CORES = 42
TEST_MAX_CORES = 47
TEST_MIN_GPUS = 2
TEST_MAX_GPUS = 7
TEST_ENABLE_VALUE = False
TEST_GROUP_NAME = 'group'
TEST_GROUP_DEPT = 'lighting'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class ShowTests(unittest.TestCase):

    def testCreateOwner(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.CreateOwner.return_value = show_pb2.ShowCreateOwnerResponse(
            owner=host_pb2.Owner(name=TEST_OWNER_NAME))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        owner = show.createOwner(TEST_OWNER_NAME)

        stubMock.CreateOwner.assert_called_with(
            show_pb2.ShowCreateOwnerRequest(show=show.data, name=TEST_OWNER_NAME),
            timeout=mock.ANY)
        self.assertEqual(owner.name, TEST_OWNER_NAME)

    def testCreateSubscription(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.CreateSubscription.return_value = show_pb2.ShowCreateSubscriptionResponse(
            subscription=subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME,
                                                       size=TEST_SUBSCRIPTION_SIZE,
                                                       burst=TEST_SUBSCRIPTION_BURST))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        allocation = opencue.wrappers.allocation.Allocation(
            facility_pb2.Allocation(id=TEST_ALLOCATION_ID))
        subscription = show.createSubscription(
            allocation, TEST_SUBSCRIPTION_SIZE, TEST_SUBSCRIPTION_BURST)

        stubMock.CreateSubscription.assert_called_with(
            show_pb2.ShowCreateSubscriptionRequest(show=show.data,
                                                   allocation_id=TEST_ALLOCATION_ID,
                                                   size=TEST_SUBSCRIPTION_SIZE,
                                                   burst=TEST_SUBSCRIPTION_BURST),
            timeout=mock.ANY)
        self.assertEqual(subscription.size(), TEST_SUBSCRIPTION_SIZE)
        self.assertEqual(subscription.burst(), TEST_SUBSCRIPTION_BURST)

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = show_pb2.ShowDeleteResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.delete()

        stubMock.Delete.assert_called_with(
            show_pb2.ShowDeleteRequest(show=show.data),
            timeout=mock.ANY)

    def testGetServiceOverrides(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetServiceOverrides.return_value = show_pb2.ShowGetServiceOverridesResponse(
            service_overrides=service_pb2.ServiceOverrideSeq(
                service_overrides=[
                    service_pb2.ServiceOverride(data=service_pb2.Service(name=TEST_SERVICE_NAME))
                ]))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        overrides = show.getServiceOverrides()

        stubMock.GetServiceOverrides.assert_called_with(
            show_pb2.ShowGetServiceOverridesRequest(show=show.data),
            timeout=mock.ANY)
        self.assertEqual(overrides[0].data.name, TEST_SERVICE_NAME)

    def testGetSubscriptions(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetSubscriptions.return_value = show_pb2.ShowGetSubscriptionResponse(
            subscriptions=subscription_pb2.SubscriptionSeq(
                subscriptions=[subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME)])
        )
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        subscriptions = show.getSubscriptions()

        stubMock.GetSubscriptions.assert_called_with(
            show_pb2.ShowGetSubscriptionRequest(show=show.data), timeout=mock.ANY)
        self.assertEqual(len(subscriptions), 1)
        self.assertEqual(subscriptions[0].name(), TEST_SUBSCRIPTION_NAME)

    def testFindSubscription(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = subscription_pb2.SubscriptionFindResponse(
            subscription=subscription_pb2.Subscription(name=TEST_SUBSCRIPTION_NAME))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        subscription = show.findSubscription(TEST_SUBSCRIPTION_NAME)

        stubMock.Find.assert_called_with(
            subscription_pb2.SubscriptionFindRequest(name=TEST_SUBSCRIPTION_NAME), timeout=mock.ANY)
        self.assertEqual(subscription.name(), TEST_SUBSCRIPTION_NAME)

    def testGetFilters(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetFilters.return_value = show_pb2.ShowGetFiltersResponse(
            filters=filter_pb2.FilterSeq(filters=[filter_pb2.Filter(name=TEST_FILTER_NAME)]))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        filters = show.getFilters()

        stubMock.GetFilters.assert_called_with(
            show_pb2.ShowGetFiltersRequest(show=show.data), timeout=mock.ANY)
        self.assertEqual(len(filters), 1)
        self.assertEqual(filters[0].name(), TEST_FILTER_NAME)

    def testSetActive(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetActive.return_value = show_pb2.ShowSetActiveResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.setActive(TEST_ENABLE_VALUE)

        stubMock.SetActive.assert_called_with(
            show_pb2.ShowSetActiveRequest(show=show.data, value=TEST_ENABLE_VALUE),
            timeout=mock.ANY)

    def testSetDefaultMaxCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultMaxCores.return_value = show_pb2.ShowSetDefaultMaxCoresResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.setDefaultMaxCores(TEST_MAX_CORES)

        stubMock.SetDefaultMaxCores.assert_called_with(
            show_pb2.ShowSetDefaultMaxCoresRequest(show=show.data, max_cores=TEST_MAX_CORES),
            timeout=mock.ANY)

    def testSetDefaultMinCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultMinCores.return_value = show_pb2.ShowSetDefaultMinCoresResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.setDefaultMinCores(TEST_MIN_CORES)

        stubMock.SetDefaultMinCores.assert_called_with(
            show_pb2.ShowSetDefaultMinCoresRequest(show=show.data, min_cores=TEST_MIN_CORES),
            timeout=mock.ANY)

    def testSetDefaultMaxGpus(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultMaxGpus.return_value = show_pb2.ShowSetDefaultMaxGpusResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.setDefaultMaxGpus(TEST_MAX_GPUS)

        stubMock.SetDefaultMaxGpus.assert_called_with(
            show_pb2.ShowSetDefaultMaxGpusRequest(show=show.data, max_gpus=TEST_MAX_GPUS),
            timeout=mock.ANY)

    def testSetDefaultMinGpus(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultMinGpus.return_value = show_pb2.ShowSetDefaultMinGpusResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.setDefaultMinGpus(TEST_MIN_GPUS)

        stubMock.SetDefaultMinGpus.assert_called_with(
            show_pb2.ShowSetDefaultMinGpusRequest(show=show.data, min_gpus=TEST_MIN_GPUS),
            timeout=mock.ANY)

    def testFindFilter(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.FindFilter.return_value = show_pb2.ShowFindFilterResponse(
            filter=filter_pb2.Filter(name=TEST_FILTER_NAME))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        filter_found = show.findFilter(TEST_FILTER_NAME)

        stubMock.FindFilter.assert_called_with(
            show_pb2.ShowFindFilterRequest(show=show.data, name=TEST_FILTER_NAME),
            timeout=mock.ANY)
        self.assertEqual(filter_found.name(), TEST_FILTER_NAME)

    def testCreateFilter(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.CreateFilter.return_value = show_pb2.ShowCreateFilterResponse(
            filter=filter_pb2.Filter(name=TEST_FILTER_NAME))
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        filter_created = show.createFilter(TEST_FILTER_NAME)

        stubMock.CreateFilter.assert_called_with(
            show_pb2.ShowCreateFilterRequest(show=show.data, name=TEST_FILTER_NAME),
            timeout=mock.ANY)
        self.assertEqual(filter_created.name(), TEST_FILTER_NAME)

    def testGetGroups(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetGroups.return_value = show_pb2.ShowGetGroupsResponse(
            groups=job_pb2.GroupSeq(
                groups=[job_pb2.Group(name=TEST_GROUP_NAME, department=TEST_GROUP_DEPT)])
        )
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        groups = show.getGroups()

        stubMock.GetGroups.assert_called_with(
            show_pb2.ShowGetGroupsRequest(show=show.data), timeout=mock.ANY)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name(), TEST_GROUP_NAME)
        self.assertEqual(groups[0].department(), TEST_GROUP_DEPT)

    def testGetJobWhiteboard(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetJobWhiteboard.return_value = show_pb2.ShowGetJobWhiteboardResponse(
            whiteboard=job_pb2.NestedGroup(name=TEST_GROUP_NAME,
                                           department=TEST_GROUP_DEPT)
        )
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        whiteboard = show.getJobWhiteboard()

        stubMock.GetJobWhiteboard.assert_called_with(
            show_pb2.ShowGetJobWhiteboardRequest(show=show.data), timeout=mock.ANY)
        self.assertEqual(whiteboard.name, TEST_GROUP_NAME)
        self.assertEqual(whiteboard.department, TEST_GROUP_DEPT)

    def testGetRootGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetRootGroup.return_value = show_pb2.ShowGetRootGroupResponse(
            group=job_pb2.Group(name=TEST_GROUP_NAME,
                                department=TEST_GROUP_DEPT)
        )
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        rootGroup = show.getRootGroup()

        stubMock.GetRootGroup.assert_called_with(
            show_pb2.ShowGetRootGroupRequest(show=show.data), timeout=mock.ANY)
        self.assertEqual(rootGroup.name(), TEST_GROUP_NAME)
        self.assertEqual(rootGroup.department(), TEST_GROUP_DEPT)

    def testEnableBooking(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EnableBooking.return_value = show_pb2.ShowEnableBookingResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.enableBooking(TEST_ENABLE_VALUE)

        stubMock.EnableBooking.assert_called_with(
            show_pb2.ShowEnableBookingRequest(show=show.data, enabled=TEST_ENABLE_VALUE),
            timeout=mock.ANY)

    def testEnableDispatching(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EnableDispatching.return_value = show_pb2.ShowEnableDispatchingResponse()
        getStubMock.return_value = stubMock

        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))
        show.enableDispatching(TEST_ENABLE_VALUE)

        stubMock.EnableDispatching.assert_called_with(
            show_pb2.ShowEnableDispatchingRequest(show=show.data, enabled=TEST_ENABLE_VALUE),
            timeout=mock.ANY)

    def testCreateServiceOverrideMemError(self, getStubMock):
        service = service_pb2.Service(name=TEST_SERVICE_NAME)
        show = opencue.wrappers.show.Show(show_pb2.Show(name=TEST_SHOW_NAME))

        self.assertRaises(ValueError, show.createServiceOverride, service)


if __name__ == '__main__':
    unittest.main()
