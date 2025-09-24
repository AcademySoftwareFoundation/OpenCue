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

"""Tests for `opencue.wrappers.depend`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import depend_pb2
import opencue.wrappers.depend


TEST_DEPEND_ID = 'zzz-aaa-fff'
TEST_DEPEND_ER = '111-111-111'
TEST_DEPEND_ON = '111-111-111'
TEST_DEPEND_ON_NEG = '222-222-222'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class DependTests(unittest.TestCase):

    def testSatisfy(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Satisfy.return_value = depend_pb2.DependSatisfyResponse()
        getStubMock.return_value = stubMock

        depend = opencue.wrappers.depend.Depend(
            depend_pb2.Depend(id=TEST_DEPEND_ID))
        depend.satisfy()

        stubMock.Satisfy.assert_called_with(
            depend_pb2.DependSatisfyRequest(depend=depend.data), timeout=mock.ANY)

    def testUnsatisfy(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Unsatisfy.return_value = depend_pb2.DependUnsatisfyResponse()
        getStubMock.return_value = stubMock

        depend = opencue.wrappers.depend.Depend(
            depend_pb2.Depend(id=TEST_DEPEND_ID))
        depend.unsatisfy()

        stubMock.Unsatisfy.assert_called_with(
            depend_pb2.DependUnsatisfyRequest(depend=depend.data), timeout=mock.ANY)

    def testIsInternalPos(self, getStubMock):
        stubMock = mock.Mock()
        getStubMock.return_value = stubMock

        dependPos = opencue.wrappers.depend.Depend(
            depend_pb2.Depend(id=TEST_DEPEND_ID,
                              depend_er_job=TEST_DEPEND_ER,
                              depend_on_job=TEST_DEPEND_ON))
        self.assertTrue(dependPos.isInternal())

    def testIsInternalNeg(self, getStubMock):
        stubMock = mock.Mock()
        getStubMock.return_value = stubMock

        dependNeg = opencue.wrappers.depend.Depend(
            depend_pb2.Depend(id=TEST_DEPEND_ID,
                              depend_er_job=TEST_DEPEND_ER,
                              depend_on_job=TEST_DEPEND_ON_NEG))
        self.assertFalse(dependNeg.isInternal())


class DependEnumTests(unittest.TestCase):

    def testDependType(self):
        self.assertEqual(opencue.api.Depend.DependType.JOB_ON_JOB,
                         depend_pb2.JOB_ON_JOB)
        self.assertEqual(opencue.api.Depend.DependType.JOB_ON_JOB, 0)

    def testDependTarget(self):
        self.assertEqual(opencue.api.Depend.DependTarget.ANY_TARGET,
                         depend_pb2.ANY_TARGET)
        self.assertEqual(opencue.api.Depend.DependTarget.ANY_TARGET, 2)


if __name__ == '__main__':
    unittest.main()
