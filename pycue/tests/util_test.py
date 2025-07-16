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

"""Tests for `opencue.util`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from builtins import range
import unittest
import uuid

import grpc
import mock

from opencue_proto import job_pb2
import opencue.exception
from opencue.wrappers.job import Job


@opencue.util.grpcExceptionParser
def testRaise(exc):
    uuid.uuid4()
    raise exc


class ProxyTests(unittest.TestCase):
    """proxy converts different types of entities to usable Ice proxies"""

    def testNotFoundExceptionParser(self):
        response = grpc.RpcError()
        response.code = lambda: grpc.StatusCode.NOT_FOUND
        response.details = lambda: "testing not found"
        self.assertRaises(opencue.exception.EntityNotFoundException,
                          lambda: testRaise(response))

    def testExistsExceptionParser(self):
        response = grpc.RpcError()
        response.code = lambda: grpc.StatusCode.ALREADY_EXISTS
        response.details = lambda: "already exists"
        self.assertRaises(opencue.exception.EntityAlreadyExistsException,
                          lambda: testRaise(response))

    def testDeadlineExceptionParser(self):
        response = grpc.RpcError()
        response.code = lambda: grpc.StatusCode.DEADLINE_EXCEEDED
        response.details = lambda: "deadline exceeded"
        self.assertRaises(opencue.exception.DeadlineExceededException,
                          lambda: testRaise(response))

    def testInternalExceptionParser(self):
        response = grpc.RpcError()
        response.code = lambda: grpc.StatusCode.INTERNAL
        response.details = lambda: "Internal Error"
        self.assertRaises(opencue.exception.CueInternalErrorException,
                          lambda: testRaise(response))

    @mock.patch('uuid.uuid4')
    def testConnectionExceptionParser(self, mockUuid):
        with mock.patch('opencue.exception.getRetryCount', return_value=3):
            response = grpc.RpcError()
            response.code = lambda: grpc.StatusCode.UNAVAILABLE
            response.details = lambda: "Connection Error"
            self.assertRaises(opencue.exception.ConnectionException,
                              lambda: testRaise(response))
        self.assertEqual(mockUuid.call_count, 4)

    @mock.patch('uuid.uuid4')
    def testConnectionExceptionZeroRetries(self, mockUuid):
        with mock.patch('opencue.exception.getRetryCount', return_value=0):
            response = grpc.RpcError()
            response.code = lambda: grpc.StatusCode.UNAVAILABLE
            response.details = lambda: "Connection Error"
            self.assertRaises(opencue.exception.ConnectionException,
                              lambda: testRaise(response))
        self.assertEqual(mockUuid.call_count, 1)

    def testUnknownExceptionParser(self):
        response = grpc.RpcError()
        response.code = lambda: "unknown"
        response.details = lambda: "unknown"
        self.assertRaises(opencue.exception.CueException,
                          lambda: testRaise(response))

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testProxyUniqueId(self, getStubMock):
        """convert a string and class name to proxy"""
        objectId = 'A0000000-0000-0000-0000-000000000000'
        stubMock = mock.Mock()
        stubMock.GetGroup.return_value = job_pb2.GroupGetGroupResponse(
            group=job_pb2.Group(id=objectId))
        getStubMock.return_value = stubMock

        proxy = opencue.proxy(objectId, 'Group')

        stubMock.GetGroup.assert_called_with(job_pb2.GroupGetGroupRequest(id=objectId))
        self.assertEqual(objectId, proxy.group.id)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testProxyUniqueIdArray(self, getStubMock):
        """convert a list of strings and a class name to a proxy"""
        ids = ['A0000000-0000-0000-0000-000000000000', 'B0000000-0000-0000-0000-000000000000']
        stubMock = mock.Mock()
        stubMock.GetGroup.side_effect = lambda request : job_pb2.GroupGetGroupResponse(
            group=job_pb2.Group(id=request.id))
        getStubMock.return_value = stubMock

        proxyList = opencue.proxy(ids, 'Group')

        stubMock.GetGroup.assert_has_calls([
            mock.call(job_pb2.GroupGetGroupRequest(id=ids[0])),
            mock.call(job_pb2.GroupGetGroupRequest(id=ids[1])),
        ])
        self.assertEqual(ids, [proxy.group.id for proxy in proxyList])

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testProxyObjectArray(self, getStubMock):
        """convert a list of proto object and a class name to a proxy"""
        ids = ['A0000000-0000-0000-0000-000000000000', 'B0000000-0000-0000-0000-000000000000']
        protos = [job_pb2.Group(id=id) for id in ids]
        stubMock = mock.Mock()
        stubMock.GetGroup.side_effect = lambda request: job_pb2.GroupGetGroupResponse(
            group=job_pb2.Group(id=request.id))
        getStubMock.return_value = stubMock

        proxyList = opencue.proxy(protos, 'Group')

        stubMock.GetGroup.assert_has_calls([
            mock.call(job_pb2.GroupGetGroupRequest(id=ids[0])),
            mock.call(job_pb2.GroupGetGroupRequest(id=ids[1])),
        ])
        self.assertEqual(ids, [proxy.group.id for proxy in proxyList])


class IdTests(unittest.TestCase):
    """id() takes an entity and returns the unique id"""

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testIdOnEntity(self, getStubMock):
        del getStubMock
        arbitraryId = 'foo'
        job = Job(job_pb2.Job(id=arbitraryId))

        self.assertEqual(arbitraryId, opencue.id(job))

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testIdOnEntityList(self, getStubMock):
        del getStubMock
        arbitraryIds = ['foo', 'bar']
        jobs = [Job(job_pb2.Job(id=arbitraryIds[0])), Job(job_pb2.Job(id=arbitraryIds[1]))]

        ids = opencue.id(jobs)

        self.assertEqual(len(jobs), len(ids))
        for i in range(0, len(jobs)):
            self.assertEqual(arbitraryIds[i], ids[i])


if __name__ == '__main__':
    unittest.main()
