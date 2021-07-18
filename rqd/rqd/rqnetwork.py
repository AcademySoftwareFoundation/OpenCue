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


"""Network specific module, implements the interface with gRPC."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import object
from concurrent import futures
from random import shuffle
import atexit
import logging as log
import os
import platform
import subprocess
import time

import grpc

import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.report_pb2_grpc
import rqd.compiled_proto.rqd_pb2_grpc
import rqd.rqconstants
import rqd.rqdservicers
import rqd.rqutil


class RunningFrame(object):
    """Represents a running frame."""

    def __init__(self, rqCore, runFrame):
        self.rqCore = rqCore
        self.runFrame = runFrame
        self.ignoreNimby = runFrame.ignore_nimby
        self.frameId = runFrame.frame_id

        self.killMessage = ""

        self.pid = None
        self.exitStatus = None
        self.frameAttendantThread = None
        self.exitSignal = 0
        self.runTime = 0

        self.rss = 0
        self.maxRss = 0
        self.vsize = 0
        self.maxVsize = 0

        self.numGpus = 0
        self.usedGpuMemory = 0
        self.maxUsedGpuMemory = 0

        self.realtime = 0
        self.utime = 0
        self.stime = 0

        self.lluTime = 0

    def runningFrameInfo(self):
        """Returns the RunningFrameInfo object"""
        runningFrameInfo = rqd.compiled_proto.report_pb2.RunningFrameInfo(
            resource_id=self.runFrame.resource_id,
            job_id=self.runFrame.job_id,
            job_name=self.runFrame.job_name,
            frame_id=self.runFrame.frame_id,
            frame_name=self.runFrame.frame_name,
            layer_id=self.runFrame.layer_id,
            num_cores=self.runFrame.num_cores,
            start_time=self.runFrame.start_time,
            max_rss=self.maxRss,
            rss=self.rss,
            max_vsize=self.maxVsize,
            vsize=self.vsize,
            attributes=self.runFrame.attributes,
            llu_time=self.lluTime,
            num_gpus=self.numGpus,
            max_used_gpu_memory=self.maxUsedGpuMemory,
            used_gpu_memory=self.usedGpuMemory
        )
        return runningFrameInfo

    def status(self):
        """Returns the status of the frame"""
        return self.runningFrameInfo()

    def kill(self, message=""):
        """Kills the frame"""
        log.info("Request recieved: kill")
        if self.frameAttendantThread is None:
            log.warning(
                "Kill requested before frameAttendantThread is created for: %s", self.frameId)
        elif self.frameAttendantThread.isAlive() and self.pid is None:
            log.warning("Kill requested before pid is available for: %s", self.frameId)
        elif self.frameAttendantThread.isAlive():
            # pylint: disable=broad-except
            try:
                if not self.killMessage and message:
                    self.killMessage = message
                rqd.rqutil.permissionsHigh()
                try:
                    if platform.system() == "Windows":
                        subprocess.Popen('taskkill /F /T /PID %i' % self.pid, shell=True)
                    else:
                        os.killpg(self.pid, rqd.rqconstants.KILL_SIGNAL)
                finally:
                    rqd.rqutil.permissionsLow()
            except OSError as e:
                log.warning(
                    "kill() tried to kill a non-existant pid for: %s Error: %s", self.frameId, e)
            except Exception as e:
                log.warning("kill() encountered an unknown error: %s", e)
        else:
            log.warning(
                "Kill requested after frameAttendantThread has exited for: %s", self.frameId)
            self.rqCore.deleteFrame(self.frameId)


class GrpcServer(object):
    """gRPC server class for managing messages from Cuebot back to RQD.

    This is used for controlling the render host and task actions initiated by
    Cuebot and CueGUI."""

    def __init__(self, rqCore):
        self.rqCore = rqCore
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=rqd.rqconstants.RQD_GRPC_MAX_WORKERS))
        self.servicers = ['RqdInterfaceServicer']
        self.server.add_insecure_port('[::]:{0}'.format(rqd.rqconstants.RQD_GRPC_PORT))

    def addServicers(self):
        """Registers the gRPC servicers defined in rqdservicers.py."""
        for servicer in self.servicers:
            addFunc = getattr(rqd.compiled_proto.rqd_pb2_grpc, 'add_{0}_to_server'.format(servicer))
            servicerClass = getattr(rqd.rqdservicers, servicer)
            addFunc(servicerClass(self.rqCore), self.server)

    def connectGrpcWithRetries(self):
        """Connects to the Cuebot gRPC, with built-in retries."""
        while True:
            try:
                self.rqCore.grpcConnected()
                break
            except grpc.RpcError as exc:
                # pylint: disable=no-member
                if exc.code() == grpc.StatusCode.UNAVAILABLE:
                    log.warning(
                        'GRPC connection failed. Retrying in %s seconds',
                        rqd.rqconstants.RQD_GRPC_CONNECTION_ATTEMPT_SLEEP_SEC)
                    time.sleep(rqd.rqconstants.RQD_GRPC_CONNECTION_ATTEMPT_SLEEP_SEC)
                else:
                    raise exc
                # pylint: enable=no-member

    def serve(self):
        """Starts serving gRPC."""
        self.addServicers()
        self.server.start()
        if rqd.rqconstants.RQD_GRPC_RETRY_CONNECTION:
            self.connectGrpcWithRetries()
        else:
            self.rqCore.grpcConnected()

    def serveForever(self):
        """Starts serving gRPC, then enters a loop to keep running until killed."""
        self.serve()
        self.stayAlive()

    def shutdown(self):
        """Stops the gRPC server."""
        log.info('Stopping grpc server.')
        self.server.stop(0)

    def stayAlive(self):
        """Runs forever until killed."""
        try:
            while True:
                time.sleep(rqd.rqconstants.RQD_GRPC_SLEEP_SEC)
        except KeyboardInterrupt:
            self.server.stop(0)


class Network(object):
    """Handles gRPC communication"""
    def __init__(self, rqCore):
        """Network class initialization"""
        self.rqCore = rqCore
        self.grpcServer = None
        self.channel = None

    def start_grpc(self):
        """Starts the gRPC server."""
        self.grpcServer = GrpcServer(self.rqCore)
        self.grpcServer.serveForever()

    def stopGrpc(self):
        """Stops the gRPC server."""
        self.grpcServer.shutdown()
        del self.grpcServer

    def closeChannel(self):
        """Closes the gRPC channel."""
        self.channel.close()
        del self.channel
        self.channel = None

    def __getChannel(self):
        # TODO(bcipriano) Add support for the facility nameserver or drop this concept? (Issue #152)
        if self.channel is None:
            cuebots = rqd.rqconstants.CUEBOT_HOSTNAME.split()
            shuffle(cuebots)
            for cuebotHostname in cuebots:
                self.channel = grpc.insecure_channel('%s:%s' % (cuebotHostname,
                                                                rqd.rqconstants.CUEBOT_GRPC_PORT))
            atexit.register(self.closeChannel)

    def __getReportStub(self):
        self.__getChannel()
        return rqd.compiled_proto.report_pb2_grpc.RqdReportInterfaceStub(self.channel)

    def reportRqdStartup(self, report):
        """Wraps the ability to send a startup report to rqd via grpc"""
        stub = self.__getReportStub()
        request = rqd.compiled_proto.report_pb2.RqdReportRqdStartupRequest(boot_report=report)
        stub.ReportRqdStartup(request, timeout=rqd.rqconstants.RQD_TIMEOUT)

    def reportStatus(self, report):
        """Wraps the ability to send a status report to the cuebot via grpc"""
        stub = self.__getReportStub()
        request = rqd.compiled_proto.report_pb2.RqdReportStatusRequest(host_report=report)
        stub.ReportStatus(request, timeout=rqd.rqconstants.RQD_TIMEOUT)

    def reportRunningFrameCompletion(self, report):
        """Wraps the ability to send a running frame completion report
           to the cuebot via grpc"""
        stub = self.__getReportStub()
        request = rqd.compiled_proto.report_pb2.RqdReportRunningFrameCompletionRequest(
            frame_complete_report=report)
        stub.ReportRunningFrameCompletion(request, timeout=rqd.rqconstants.RQD_TIMEOUT)
