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

"""Tests for `opencue.wrappers.limit`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import limit_pb2
import opencue.wrappers.limit


TEST_LIMIT_ID = 'lll-llll-lll'
TEST_LIMIT_NAME = 'imalimit'
TEST_LIMIT_MAX_VALUE = 42


@mock.patch('opencue.cuebot.Cuebot.getStub')
class LimitTests(unittest.TestCase):

    def testCreate(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Create.return_value = limit_pb2.LimitCreateResponse()
        getStubMock.return_value = stubMock

        limit = opencue.wrappers.limit.Limit(
            limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE))
        limit.create()

        stubMock.Create.assert_called_with(
            limit_pb2.LimitCreateRequest(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE),
            timeout=mock.ANY)

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = limit_pb2.LimitDeleteResponse()
        getStubMock.return_value = stubMock

        limit = opencue.wrappers.limit.Limit(
            limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE))
        limit.delete()

        stubMock.Delete.assert_called_with(
            limit_pb2.LimitDeleteRequest(name=TEST_LIMIT_NAME), timeout=mock.ANY)

    def testFind(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = limit_pb2.LimitFindResponse(
          limit=limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE))
        getStubMock.return_value = stubMock

        limit = opencue.wrappers.limit.Limit()
        responseLimit = limit.find(TEST_LIMIT_NAME)

        stubMock.Find.assert_called_with(
            limit_pb2.LimitFindRequest(name=TEST_LIMIT_NAME), timeout=mock.ANY)
        self.assertEqual(responseLimit.name(), TEST_LIMIT_NAME)
        self.assertEqual(responseLimit.maxValue(), TEST_LIMIT_MAX_VALUE)

    def testGet(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Get.return_value = limit_pb2.LimitGetResponse(
            limit=limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE))
        getStubMock.return_value = stubMock

        limit = opencue.wrappers.limit.Limit()
        responseLimit = limit.get(TEST_LIMIT_ID)

        stubMock.Get.assert_called_with(
            limit_pb2.LimitGetRequest(id=TEST_LIMIT_ID), timeout=mock.ANY)
        self.assertEqual(responseLimit.name(), TEST_LIMIT_NAME)
        self.assertEqual(responseLimit.maxValue(), TEST_LIMIT_MAX_VALUE)

    def testRename(self, getStubMock):
        test_new_name = 'new_name'
        stubMock = mock.Mock()
        stubMock.Rename.return_value = limit_pb2.LimitRenameResponse()
        getStubMock.return_value = stubMock

        limit = opencue.wrappers.limit.Limit(
            limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE))
        limit.rename(test_new_name)

        stubMock.Rename.assert_called_with(
            limit_pb2.LimitRenameRequest(old_name=TEST_LIMIT_NAME, new_name=test_new_name),
            timeout=mock.ANY)

    def testSetMaxValue(self, getStubMock):
        max_value = 16
        stubMock = mock.Mock()
        stubMock.SetMaxValue.return_value = limit_pb2.LimitSetMaxValueResponse()
        getStubMock.return_value = stubMock

        limit = opencue.wrappers.limit.Limit(
            limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=TEST_LIMIT_MAX_VALUE))
        limit.setMaxValue(max_value)

        stubMock.SetMaxValue.assert_called_with(
            limit_pb2.LimitSetMaxValueRequest(name=TEST_LIMIT_NAME, max_value=max_value),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
