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


"""Tests for rqd.cuerqd."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
import sys
import unittest

import mock

import opencue_proto.rqd_pb2
import rqd.cuerqd


SCRIPT_NAME = '/arbitrary/path/to/script'
RQD_HOSTNAME = 'arbitrary-rqd-hostname'


@mock.patch('opencue_proto.rqd_pb2_grpc.RunningFrameStub')
@mock.patch('opencue_proto.rqd_pb2_grpc.RqdInterfaceStub')
@mock.patch('grpc.insecure_channel', new=mock.MagicMock())
class CueRqdTests(unittest.TestCase):

    @mock.patch('rqd.cuerqd.RqdHost')
    def test_init(self, rqdHostMock, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '-s']

        rqd.cuerqd.main()

        rqdHostMock.assert_called_with(RQD_HOSTNAME)

    @mock.patch('rqd.cuerqd.RqdHost')
    def test_initWithLocalhost(self, rqdHostMock, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, '-s']

        rqd.cuerqd.main()

        rqdHostMock.assert_called_with('localhost')

    def test_status(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '-s']
        statusRequest = opencue_proto.rqd_pb2.RqdStaticReportStatusRequest()

        rqd.cuerqd.main()

        stubMock.return_value.ReportStatus.assert_called_with(statusRequest)

    def test_getRunningFrame(self, stubMock, frameStubMock):
        frameId = 'arbitrary-frame-id'
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--getproxy', frameId]
        runFrameRequest = opencue_proto.rqd_pb2.RqdStaticGetRunFrameRequest(frame_id=frameId)

        rqd.cuerqd.main()

        stubMock.return_value.GetRunFrame.assert_called_with(runFrameRequest)

    def test_nimbyOff(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--nimbyoff']
        nimbyOffRequest = opencue_proto.rqd_pb2.RqdStaticNimbyOffRequest()

        rqd.cuerqd.main()

        stubMock.return_value.NimbyOff.assert_called_with(nimbyOffRequest)

    def test_nimbyOn(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--nimbyon']
        nimbyOnRequest = opencue_proto.rqd_pb2.RqdStaticNimbyOnRequest()

        rqd.cuerqd.main()

        stubMock.return_value.NimbyOn.assert_called_with(nimbyOnRequest)

    def test_lockAll(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--lh']
        lockAllRequest = opencue_proto.rqd_pb2.RqdStaticLockAllRequest()

        rqd.cuerqd.main()

        stubMock.return_value.LockAll.assert_called_with(lockAllRequest)

    def test_unlockAll(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--ulh']
        unlockAllRequest = opencue_proto.rqd_pb2.RqdStaticUnlockAllRequest()

        rqd.cuerqd.main()

        stubMock.return_value.UnlockAll.assert_called_with(unlockAllRequest)

    def test_lock(self, stubMock, frameStubMock):
        numCoresToLock = 85
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--lp', str(numCoresToLock)]
        lockRequest = opencue_proto.rqd_pb2.RqdStaticLockRequest(cores=numCoresToLock)

        rqd.cuerqd.main()

        stubMock.return_value.Lock.assert_called_with(lockRequest)

    def test_unlock(self, stubMock, frameStubMock):
        numCoresToUnlock = 52
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--ulp', str(numCoresToUnlock)]
        unlockRequest = opencue_proto.rqd_pb2.RqdStaticUnlockRequest(cores=numCoresToUnlock)

        rqd.cuerqd.main()

        stubMock.return_value.Unlock.assert_called_with(unlockRequest)

    def test_shutdownRqdIdle(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--exit']
        shutdownIdleRequest = opencue_proto.rqd_pb2.RqdStaticShutdownIdleRequest()

        rqd.cuerqd.main()

        stubMock.return_value.ShutdownRqdIdle.assert_called_with(shutdownIdleRequest)

    def test_shutdownRqdNow(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--exit_now']
        shutdownNowRequest = opencue_proto.rqd_pb2.RqdStaticShutdownNowRequest()

        rqd.cuerqd.main()

        stubMock.return_value.ShutdownRqdNow.assert_called_with(shutdownNowRequest)

    def test_rebootIdle(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--reboot']
        rebootIdleRequest = opencue_proto.rqd_pb2.RqdStaticRebootIdleRequest()

        rqd.cuerqd.main()

        stubMock.return_value.RebootIdle.assert_called_with(rebootIdleRequest)

    def test_rebootNow(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--reboot_now']
        rebootNowRequest = opencue_proto.rqd_pb2.RqdStaticRebootNowRequest()

        rqd.cuerqd.main()

        stubMock.return_value.RebootNow.assert_called_with(rebootNowRequest)

    def test_launchFrame(self, stubMock, frameStubMock):
        runFrame = opencue_proto.rqd_pb2.RunFrame()
        runFrame.job_id = "SD6F3S72DJ26236KFS"
        runFrame.job_name = "edu-trn_job-name"
        runFrame.frame_id = "FD1S3I154O646UGSNN"
        runFrameRequest = opencue_proto.rqd_pb2.RqdStaticLaunchFrameRequest(run_frame=runFrame)
        rqdHost = rqd.cuerqd.RqdHost(RQD_HOSTNAME)
        rqdHost.active = False

        rqdHost.launchFrame(runFrame)

        stubMock.return_value.LaunchFrame.assert_called_with(runFrameRequest)

    def test_killFrame(self, stubMock, frameStubMock):
        frameId = 'arbitrary-frame-id'
        runFrame = opencue_proto.rqd_pb2.RunFrame(frame_id=frameId)
        stubMock.return_value.GetRunFrame.return_value = runFrame
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--kill', frameId]

        rqd.cuerqd.main()

        frameStubMock.return_value.Kill.assert_called_with(run_frame=runFrame, message=mock.ANY)

    def test_testEduFrame(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--test_edu_frame']

        rqd.cuerqd.main()

        stubMock.return_value.LaunchFrame.assert_called()

    def test_testScriptFrame(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--test_script_frame']

        rqd.cuerqd.main()

        stubMock.return_value.LaunchFrame.assert_called()

    def test_testScriptFrameMac(self, stubMock, frameStubMock):
        sys.argv = [SCRIPT_NAME, RQD_HOSTNAME, '--test_script_frame_mac']

        rqd.cuerqd.main()

        stubMock.return_value.LaunchFrame.assert_called()

if __name__ == '__main__':
    unittest.main()
