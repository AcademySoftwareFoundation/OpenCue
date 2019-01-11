
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

"""
Network specific module, implements the interface with ICE.

Project: RQD

Module: rqnetwork.py

Contact: Middle-Tier

SVN: $Id$

RQD Interface:
==============
Everything can throw SpiIce.SpiIceException

  - RunningFrame * launchFrame(RunFrame frame)
  - HostReport reportStatus()
  - void shutdownRqdNow()
  - void shutdownRqdIdle()
  - void restartRqdNow()
  - void restartRqdIdle()
  - void rebootNow()
  - void rebootIdle()
  - void nimbyOn()
  - void nimbyOff()
  - void lock(int cores)
  - void lockAll()
  - void unlock(int cores)
  - void unlockAll()

Frame Interface:
================
Everything can throw SpiIce.SpiIceException

  - RunningFrameInfo status()
  - void kill()
"""


from concurrent import futures
import os
import time
import logging as log
import platform
import subprocess

import grpc

from compiled_proto import report_pb2
from compiled_proto import report_pb2_grpc
from compiled_proto import rqd_pb2_grpc
import rqconstants
import rqdservicers
import rqutil


class RunningFrame(object):

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

        self.realtime = 0
        self.utime = 0
        self.stime = 0

    def runningFrameInfo(self):
        """Returns the RunningFrameInfo object"""
        runningFrameInfo = report_pb2.RunningFrameInfo(
            resourceId=self.runFrame.resource_id,
            jobId=self.runFrame.job_id,
            jobName=self.runFrame.job_name,
            frameId=self.runFrame.frame_id,
            frameName=self.runFrame.frame_name,
            layerId=self.runFrame.layer_id,
            numCores=self.runFrame.num_cores,
            startTime=self.runFrame.start_time,
            maxRss=self.max_rss,
            rss=self.rss,
            maxVsize=self.max_vsize,
            vsize=self.vsize,
            attributes=self.runFrame.attributes
        )
        return runningFrameInfo

    def status(self):
        """Returns the status of the frame"""
        return self.runningFrameInfo()

    def kill(self, message=""):
        """Kills the frame"""
        log.info("Request recieved: kill")
        if self.frameAttendantThread is None:
            log.warning("Kill requested before frameAttendantThread is created "
                        "for: %s" % self.frameId)
        elif self.frameAttendantThread.isAlive() and self.pid is None:
            log.warning("Kill requested before pid is available for: %s"
                        % self.frameId)
        elif self.frameAttendantThread.isAlive():
            try:
                if not self.killMessage and message:
                    self.killMessage = message
                rqutil.permissionsHigh()
                try:
                    if platform.system() == "Windows":
                        subprocess.Popen('taskkill /F /T /PID %i' % self.pid, shell=True)
                    else:
                        os.killpg(self.pid, rqconstants.KILL_SIGNAL)
                finally:
                    rqutil.permissionsLow()
            except OSError, e:
                log.warning("kill() tried to kill a non-existant pid for: %s "
                            "Error: %s" % (self.frameId, e))
            except Exception, e:
                log.warning("kill() encountered an unknown error: %s" % e)
        else:
            log.warning("Kill requested after frameAttendantThread has exited "
                        "for: %s" % self.frameId)
            self.rqCore.deleteFrame(self.frameId)


class GrpcServer(object):
    """
    gRPC server class for managing messages from cuebot back to rqd.
    This is used for controlling the render host and task actions initiated by cuebot and cuegui.
    """

    def __init__(self, rqCore):
        self.rqCore = rqCore
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=rqconstants.RQD_GRPC_MAX_WORKERS))
        self.servicers = ['RqdInterfaceServicer']
        self.server.add_insecure_port('[::]:{0}'.format(rqconstants.RQD_GRPC_PORT))

    def addServicers(self):
        for servicer in self.servicers:
            addFunc = getattr(rqd_pb2_grpc, 'add_{0}_to_server'.format(servicer))
            servicerClass = getattr(rqdservicers, servicer)
            addFunc(servicerClass(self.rqCore), self.server)

    def serve(self):
        self.addServicers()
        self.server.start()
        self.rqCore.grpcConnected()

    def serveForever(self):
        self.serve()
        self.stayAlive()

    def shutdown(self):
        self.server.stop(0)

    def stayAlive(self):
        try:
            while True:
                time.sleep(rqconstants.RQD_GRPC_SLEEP)
        except KeyboardInterrupt:
            self.server.stop(0)


class Network(object):
    """Handles ice communication"""
    def __init__(self, rqCore):
        """Network class initialization"""
        self.rqCore = rqCore
        self.grpcServer = None

    def start_grpc(self):
        self.grpcServer = GrpcServer(self.rqCore)
        self.grpcServer.serveForever()

    def __getReportStub(self):
        # TODO(cipriano) Add support for the facility nameserver or drop this concept? (b/)
        cuebotHostname = rqconstants.CUEBOT_HOSTNAME.split()[0]
        channel = grpc.insecure_channel('%s:%s' % (cuebotHostname, rqconstants.CUEBOT_GRPC_PORT))
        return report_pb2_grpc.RqdReportInterfaceStub(channel)

    def reportRqdStartup(self, report):
        """Wraps the ability to send a startup report to rqd via grpc"""
        stub = self.__getReportStub()
        request = report_pb2.RqdReportRqdStartupRequest(boot_report=report)
        stub.ReportRqdStartup(request, timeout=rqconstants.RQD_TIMEOUT)

    def reportStatus(self, report):
        """Wraps the ability to send a status report to the cuebot via grpc"""
        stub = self.__getReportStub()
        request = report_pb2.RqdReportStatusRequest(host_report=report)
        stub.ReportStatus(request, timeout=rqconstants.RQD_TIMEOUT)

    def reportRunningFrameCompletion(self, report):
        """Wraps the ability to send a running frame completion report
           to the cuebot via grpc"""
        stub = self.__getReportStub()
        request = report_pb2.RqdReportRunningFrameCompletionRequest(frame_complete_report=report)
        stub.ReportRunningFrameCompletion(request, timeout=rqconstants.RQD_TIMEOUT)
