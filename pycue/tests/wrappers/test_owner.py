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

"""Tests for `opencue.wrappers.owner`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import host_pb2
import opencue.wrappers.owner


TEST_DEED_ID = 'ddd-dd-dddd'
TEST_HOST_ID = 'hhh-hh-hhhh'
TEST_OWNER_ID = 'ooo-oo-oooo'
TEST_OWNER_NAME = 'testOwner'
TEST_SHOW_NAME = 'testShow'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class OwnerTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = host_pb2.OwnerDeleteResponse()
        getStubMock.return_value = stubMock

        owner = opencue.wrappers.owner.Owner(
            host_pb2.Owner(id=TEST_OWNER_ID, name=TEST_OWNER_NAME))
        owner.delete()

        stubMock.Delete.assert_called_with(
            host_pb2.OwnerDeleteRequest(owner=owner.data), timeout=mock.ANY)

    def testGetDeeds(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetDeeds.return_value = host_pb2.OwnerGetDeedsResponse(
            deeds=host_pb2.DeedSeq(deeds=[host_pb2.Deed(id=TEST_DEED_ID)]))
        getStubMock.return_value = stubMock

        owner = opencue.wrappers.owner.Owner(
            host_pb2.Owner(id=TEST_OWNER_ID, name=TEST_OWNER_NAME))
        deeds = owner.getDeeds()

        stubMock.GetDeeds.assert_called_with(
            host_pb2.OwnerGetDeedsRequest(owner=owner.data), timeout=mock.ANY)
        self.assertEqual(len(deeds), 1)
        self.assertEqual(deeds[0].id(), TEST_DEED_ID)

    def testGetHosts(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetHosts.return_value = host_pb2.OwnerGetHostsResponse(
            hosts=host_pb2.HostSeq(hosts=[host_pb2.Host(id=TEST_HOST_ID)]))
        getStubMock.return_value = stubMock

        owner = opencue.wrappers.owner.Owner(
            host_pb2.Owner(id=TEST_OWNER_ID, name=TEST_OWNER_NAME))
        hosts = owner.getHosts()

        stubMock.GetHosts.assert_called_with(
            host_pb2.OwnerGetHostsRequest(owner=owner.data), timeout=mock.ANY)
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].id(), TEST_HOST_ID)

    def testGetOwner(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetOwner.return_value = host_pb2.OwnerGetOwnerResponse(
            owner=host_pb2.Owner(id=TEST_OWNER_ID, name=TEST_OWNER_NAME))
        getStubMock.return_value = stubMock

        owner = opencue.wrappers.owner.Owner()
        response = owner.getOwner(TEST_OWNER_NAME)

        stubMock.GetOwner.assert_called_with(
            host_pb2.OwnerGetOwnerRequest(name=TEST_OWNER_NAME), timeout=mock.ANY)
        self.assertEqual(response.id(), TEST_OWNER_ID)
        self.assertEqual(response.name(), TEST_OWNER_NAME)

    def testSetShow(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetShow.return_value = host_pb2.OwnerSetShowResponse()
        getStubMock.return_value = stubMock

        owner = opencue.wrappers.owner.Owner(
            host_pb2.Owner(id=TEST_OWNER_ID, name=TEST_OWNER_NAME))
        owner.setShow(TEST_SHOW_NAME)

        stubMock.SetShow.assert_called_with(
            host_pb2.OwnerSetShowRequest(owner=owner.data, show=TEST_SHOW_NAME),
            timeout=mock.ANY)

    def testTakeOwnership(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.TakeOwnership.return_value = host_pb2.OwnerTakeOwnershipResponse()
        getStubMock.return_value = stubMock

        owner = opencue.wrappers.owner.Owner(
            host_pb2.Owner(id=TEST_OWNER_ID, name=TEST_OWNER_NAME))
        owner.takeOwnership(TEST_HOST_ID)

        stubMock.TakeOwnership.assert_called_with(
            host_pb2.OwnerTakeOwnershipRequest(owner=owner.data, host=TEST_HOST_ID),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
