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


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import logging as log

import grpc

import rqd.compiled_proto.rqd_pb2
import rqd.compiled_proto.rqd_pb2_grpc


class RqdInterfaceServicer(rqd.compiled_proto.rqd_pb2_grpc.RqdInterfaceServicer):
    """Service interface for RqdStatic gRPC definition"""

    def __init__(self, rqCore):
        self.rqCore = rqCore

    def LaunchFrame(self, request, context):
        """RPC call that launches the given frame"""
        log.info("Request received: launchFrame")
        self.rqCore.launchFrame(request.run_frame)
        return rqd.compiled_proto.rqd_pb2.RqdStaticLaunchFrameResponse()

    def ReportStatus(self, request, context):
        """RPC call that returns reportStatus"""
        log.info("Request received: reportStatus")
        return rqd.compiled_proto.rqd_pb2.RqdStaticReportStatusResponse(host_report=self.rqCore.reportStatus())

    def GetRunningFrameStatus(self, request, context):
        """RPC call to return the frame info for the given frame id"""
        log.info("Request received: getRunningFrameStatus")
        frame = self.rqCore.getRunningFrame(request.frameId)
        if frame:
            return rqd.compiled_proto.rqd_pb2.RqdStaticGetRunningFrameStatusResponse(
                running_frame_info=frame.runningFrameInfo())
        else:
            context.set_details(
                "The requested frame was not found. frameId: {}".format(request.frameId))
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return rqd.compiled_proto.rqd_pb2.RqdStaticGetRunningFrameStatusResponse()

    def KillRunningFrame(self, request, context):
        """RPC call that kills the running frame with the given id"""
        log.info("Request received: killRunningFrame")
        frame = self.rqCore.getRunningFrame(request.frame_id)
        if frame:
            frame.kill(message=request.message)
        return rqd.compiled_proto.rqd_pb2.RqdStaticKillRunningFrameResponse()

    def ShutdownRqdNow(self, request, context):
        """RPC call that kills all running frames and shuts down rqd"""
        log.info("Request received: shutdownRqdNow")
        self.rqCore.shutdownRqdNow()
        return rqd.compiled_proto.rqd_pb2.RqdStaticShutdownNowResponse()

    def ShutdownRqdIdle(self, request, context):
        """RPC call that locks all cores and shuts down rqd when it is idle.
           unlockAll will abort the request."""
        log.info("Request received: shutdownRqdIdle")
        self.rqCore.shutdownRqdIdle()
        return rqd.compiled_proto.rqd_pb2.RqdStaticShutdownIdleResponse()

    def RestartRqdNow(self, request, context):
        """RPC call that kills all running frames and restarts rqd"""
        log.info("Request received: restartRqdNow")
        self.rqCore.restartRqdNow()
        return rqd.compiled_proto.rqd_pb2.RqdStaticRestartNowResponse()

    def RestartRqdIdle(self, request, context):
        """RPC call that that locks all cores and restarts rqd when idle.
           unlockAll will abort the request."""
        log.info("Request received: restartRqdIdle")
        self.rqCore.restartRqdIdle()
        return rqd.compiled_proto.rqd_pb2.RqdStaticRestartIdleResponse()

    def RebootNow(self, request, context):
        """RPC call that kills all running frames and reboots the host."""
        log.info("Request received: rebootNow")
        self.rqCore.rebootNow()
        return rqd.compiled_proto.rqd_pb2.RqdStaticRebootNowResponse()

    def RebootIdle(self, request, context):
        """RPC call that that locks all cores and reboots the host when idle.
           unlockAll will abort the request."""
        log.info("Request received: rebootIdle")
        self.rqCore.rebootIdle()
        return rqd.compiled_proto.rqd_pb2.RqdStaticRebootIdleResponse()

    def NimbyOn(self, request, context):
        """RPC call that activates nimby"""
        log.info("Request received: nimbyOn")
        self.rqCore.nimbyOn()
        return rqd.compiled_proto.rqd_pb2.RqdStaticNimbyOnResponse()

    def NimbyOff(self, request, context):
        """RPC call that deactivates nimby"""
        log.info("Request received: nimbyOff")
        self.rqCore.nimbyOff()
        return rqd.compiled_proto.rqd_pb2.RqdStaticNimbyOffResponse()

    def Lock(self, request, context):
        """RPC call that locks a specific number of cores"""
        log.info("Request received: lock %d" % request.cores)
        self.rqCore.lock(request.cores)
        return rqd.compiled_proto.rqd_pb2.RqdStaticLockResponse()

    def LockAll(self, request, context):
        """RPC call that locks all cores"""
        log.info("Request received: lockAll")
        self.rqCore.lockAll()
        return rqd.compiled_proto.rqd_pb2.RqdStaticLockAllResponse()

    def Unlock(self, request, context):
        """RPC call that unlocks a specific number of cores"""
        log.info("Request received: unlock %d" % request.cores)
        self.rqCore.unlock(request.cores)
        return rqd.compiled_proto.rqd_pb2.RqdStaticUnlockResponse()

    def UnlockAll(self, request, context):
        """RPC call that unlocks all cores"""
        log.info("Request received: unlockAll")
        self.rqCore.unlockAll()
        return rqd.compiled_proto.rqd_pb2.RqdStaticUnlockAllResponse()
