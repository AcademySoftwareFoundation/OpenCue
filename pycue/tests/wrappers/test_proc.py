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

"""Tests for `opencue.wrappers.proc`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import host_pb2
from opencue_proto import job_pb2
import opencue.wrappers.proc


TEST_HOST_NAME = 'testHost'
TEST_JOB_NAME = 'testJob'
TEST_LAYER_NAME = 'testLayer'
TEST_PROC_NAME = 'testProc'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class ProcTests(unittest.TestCase):

    def testKill(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Kill.return_value = host_pb2.ProcKillResponse()
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        proc.kill()

        stubMock.Kill.assert_called_with(
            host_pb2.ProcKillRequest(proc=proc.data), timeout=mock.ANY)

    def testUnbook(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Unbook.return_value = host_pb2.ProcUnbookResponse()
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        proc.unbook()

        stubMock.Unbook.assert_called_with(
            host_pb2.ProcUnbookRequest(proc=proc.data, kill=False), timeout=mock.ANY)

    def testUnbookKill(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Unbook.return_value = host_pb2.ProcUnbookResponse()
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        proc.unbook(kill=True)

        stubMock.Unbook.assert_called_with(
            host_pb2.ProcUnbookRequest(proc=proc.data, kill=True), timeout=mock.ANY)

    def testGetHost(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetHost.return_value = host_pb2.ProcGetHostResponse(
            host=host_pb2.Host(name=TEST_HOST_NAME))
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        host = proc.getHost()

        stubMock.GetHost.assert_called_with(
            host_pb2.ProcGetHostRequest(proc=proc.data), timeout=mock.ANY)
        self.assertEqual(host.name(), TEST_HOST_NAME)

    def testGetFrame(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetFrame.return_value = host_pb2.ProcGetFrameResponse(
            frame=job_pb2.Frame(layer_name=TEST_LAYER_NAME))
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        frame = proc.getFrame()

        stubMock.GetFrame.assert_called_with(
            host_pb2.ProcGetFrameRequest(proc=proc.data), timeout=mock.ANY)
        self.assertEqual(frame.layer(), TEST_LAYER_NAME)

    def testGetLayer(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetLayer.return_value = host_pb2.ProcGetLayerResponse(
            layer=job_pb2.Layer(name=TEST_LAYER_NAME))
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        layer = proc.getLayer()

        stubMock.GetLayer.assert_called_with(
            host_pb2.ProcGetLayerRequest(proc=proc.data), timeout=mock.ANY)
        self.assertEqual(layer.name(), TEST_LAYER_NAME)

    def testGetJob(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetJob.return_value = host_pb2.ProcGetJobResponse(
            job=job_pb2.Job(name=TEST_JOB_NAME))
        getStubMock.return_value = stubMock

        proc = opencue.wrappers.proc.Proc(
            host_pb2.Proc(name=TEST_PROC_NAME))
        job = proc.getJob()

        stubMock.GetJob.assert_called_with(
            host_pb2.ProcGetJobRequest(proc=proc.data), timeout=mock.ANY)
        self.assertEqual(job.name(), TEST_JOB_NAME)


class ProcEnumTests(unittest.TestCase):

    def testRedirectType(self):
        self.assertEqual(opencue.api.Proc.RedirectType.JOB_REDIRECT,
                         host_pb2.JOB_REDIRECT)
        self.assertEqual(opencue.api.Proc.RedirectType.JOB_REDIRECT, 0)

    def testRunState(self):
        self.assertEqual(opencue.api.Proc.RunState.BOOKED, host_pb2.BOOKED)
        self.assertEqual(opencue.api.Proc.RunState.BOOKED, 1)


if __name__ == '__main__':
    unittest.main()
