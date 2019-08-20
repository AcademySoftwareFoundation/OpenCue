#!/usr/bin/env python

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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import mock
import unittest

import opencue
from opencue.compiled_proto import host_pb2


TEST_DEED_ID = 'ddd-dd-dddd'
TEST_DEED_OWNER = 'testDeedOwner'
TEST_HOST_ID = 'hhh-hh-hhhh'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class DeedTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = host_pb2.DeedDeleteResponse()
        getStubMock.return_value = stubMock

        deed = opencue.wrappers.deed.Deed(host_pb2.Deed(id=TEST_DEED_ID))
        deed.delete()

        stubMock.Delete.assert_called_with(
            host_pb2.DeedDeleteRequest(deed=deed.data), timeout=mock.ANY)

    def testGetHost(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetHost.return_value = host_pb2.DeedGetHostResponse(
            host=host_pb2.Host(id=TEST_HOST_ID))
        getStubMock.return_value = stubMock

        deed = opencue.wrappers.deed.Deed(host_pb2.Deed(id=TEST_DEED_ID))
        host = deed.getHost()

        stubMock.GetHost.assert_called_with(
            host_pb2.DeedGetHostRequest(deed=deed.data), timeout=mock.ANY)
        self.assertEqual(host.id(), TEST_HOST_ID)

    def testGetOwner(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetOwner.return_value = host_pb2.DeedGetOwnerResponse(
            owner=host_pb2.Owner(name=TEST_DEED_OWNER))
        getStubMock.return_value = stubMock

        deed = opencue.wrappers.deed.Deed(host_pb2.Deed(id=TEST_DEED_ID))
        owner = deed.getOwner()

        stubMock.GetOwner.assert_called_with(
            host_pb2.DeedGetOwnerRequest(deed=deed.data), timeout=mock.ANY)
        self.assertEqual(owner.name(), TEST_DEED_OWNER)

    def testSetBlackoutTime(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetBlackoutTime.return_value = host_pb2.DeedSetBlackoutTimeResponse()
        getStubMock.return_value = stubMock

        testStartTime = 100
        testStopTime = 200
        deed = opencue.wrappers.deed.Deed(host_pb2.Deed(id=TEST_DEED_ID))
        deed.setBlackoutTime(testStartTime, testStopTime)

        stubMock.SetBlackoutTime.assert_called_with(
            host_pb2.DeedSetBlackoutTimeRequest(deed=deed.data,
                                                start_time=testStartTime,
                                                stop_time=testStopTime),
            timeout=mock.ANY)

    def testSetBlackoutTimeEnabled(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetBlackoutTimeEnabled.return_value = host_pb2.DeedSetBlackoutTimeEnabledResponse()
        getStubMock.return_value = stubMock

        testBlackoutEnabled = True
        deed = opencue.wrappers.deed.Deed(host_pb2.Deed(id=TEST_DEED_ID))
        deed.setBlackoutTimeEnabled(testBlackoutEnabled)

        stubMock.SetBlackoutTimeEnabled.assert_called_with(
            host_pb2.DeedSetBlackoutTimeEnabledRequest(deed=deed.data,
                                                       enabled=testBlackoutEnabled),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
