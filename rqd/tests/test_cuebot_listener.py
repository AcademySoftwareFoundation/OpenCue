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


"""
A simple test script that acts like the Cuebot by listening for messages from RQD.

THIS IS FOR TESTING rqd.py ONLY
"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import object
from concurrent import futures
import time
import sys

import grpc

import opencue_proto.report_pb2_grpc
import rqd.rqconstants


class RqdReportStaticServer(object):

    def __init__(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))
        self.servicerName = 'RqdReportInterfaceServicer'
        self.servicer = None
        self.server.add_insecure_port('[::]:{0}'.format(rqd.rqconstants.CUEBOT_GRPC_PORT))

    def addServicers(self):
        addFunc = getattr(
            opencue_proto.report_pb2_grpc, 'add_{0}_to_server'.format(self.servicerName))
        servicerClass = globals()[self.servicerName]
        self.servicer = servicerClass()
        addFunc(self.servicer, self.server)

    def serve(self):
        self.addServicers()
        self.server.start()

    def serveForever(self):
        self.serve()
        self.stayAlive()

    def shutdown(self):
        self.server.stop(0)

    def stayAlive(self):
        try:
            while True:
                time.sleep(rqd.rqconstants.RQD_GRPC_SLEEP_SEC)
        except KeyboardInterrupt:
            self.server.stop(0)


class RqdReportInterfaceServicer(opencue_proto.report_pb2_grpc.RqdReportInterfaceServicer):
    """Test class implements RqdReportStatic interface.
       Received reports are stored in the variables listed below.
       Create as an object to connect.
       call .wait() to block until ice exits.
       call .stop to destroy the ice communicator, after .wait() will exit."""
    lastReportRqdStartup = None
    lastReportStatus = None
    lastReportRunningFrameCompletion = None

    statusCheckin = {}

    def __init__(self):
        self.verbose = 2

    def _trackUpdateTime(self, report):
        now = time.time()
        self.statusCheckin[report.host.name] = {"last": now, "report": report}
        print("-" * 20, time.asctime(time.localtime(now)), "-" * 20)
        for host in sorted(self.statusCheckin.keys()):
            secondsSinceLast = now - self.statusCheckin[host]["last"]
            if host == report.host.name:
                print(" >", end=' ')
            else:
                print("  ", end=' ')
            print(
                host.ljust(15), str(int(secondsSinceLast)).ljust(10),
                str(self.statusCheckin[host]["report"].host.load).ljust(5),
                str(self.statusCheckin[host]["report"].host.freeMem).ljust(10),
                ",".join(self.statusCheckin[host]["report"].host.tags))

    def ReportRqdStartup(self, request, context):
        report = request.bootReport
        self.lastReportRqdStartup = report

        if self.verbose == 0:
            pass
        elif self.verbose == 1:
            sys.stdout.write("1")
            sys.stdout.flush()
        elif self.verbose == 2:
            print(
                "%s : startup.host    - nimbyEnabled = %s, numProcs = %s, coresPerProc = %d, "
                "load = %s, bootTime = %s" % (
                    report.host.name, report.host.nimbyEnabled, report.host.numProcs,
                    report.host.coresPerProc, report.host.load, report.host.bootTime))
            print(
                "%s : startup.host    - totalSwap = %s, totalMem = %s, totalMcp = %s, "
                "freeSwap = %s, freeMem = %s, freeMcp = %s" % (
                    report.host.name, report.host.totalSwap, report.host.totalMem,
                    report.host.totalMcp, report.host.freeSwap, report.host.freeMem,
                    report.host.freeMcp))
            print(
                "%s : startup.host    - tags = %s, state = %s" % (
                    report.host.name, report.host.tags, report.host.state))
            print(
                "%s : startup.coreInfo - totalCores = %s, idleCores = %s, lockedCores = %s, "
                "bookedCores = %s" % (
                    report.host.name, report.coreInfo.totalCores, report.coreInfo.idleCores,
                    report.coreInfo.lockedCores, report.coreInfo.bookedCores))
        elif self.verbose == 3:
            print("Receiving reportRqdStartup")
            print(report)
        elif self.verbose == 4:
            self._trackUpdateTime(report)

    def ReportStatus(self, request, context):
        report = request.hostReport
        self.lastReportStatus = report

        if self.verbose == 0:
            pass
        elif self.verbose == 1:
            sys.stdout.write(".")
            sys.stdout.flush()
        elif self.verbose == 2:
            print(
                "%s : status.host    - nimbyEnabled = %s, numProcs = %s, coresPerProc = %d, "
                "load = %s, bootTime = %s" % (
                    report.host.name, report.host.nimbyEnabled, report.host.numProcs,
                    report.host.coresPerProc, report.host.load,report.host.bootTime))
            print(
                "%s : status.host    - totalSwap = %s, totalMem = %s, totalMcp = %s, "
                "freeSwap = %s, freeMem = %s, freeMcp = %s" % (
                    report.host.name, report.host.totalSwap, report.host.totalMem,
                    report.host.totalMcp, report.host.freeSwap, report.host.freeMem,
                    report.host.freeMcp))
            print(
                "%s : status.host    - tags = %s, state = %s" % (
                    report.host.name, report.host.tags, report.host.state))
            for job in report.frames:
                print(
                    "%s : status.frames[x] - frameId = %s, jobId = %s, numCores = %d, "
                    "usedMem = %s" % (
                        report.host.name, job.frameId, job.jobId, job.numCores, job.usedMem))
            print(
                "%s : status.coreInfo - totalCores = %s, idleCores = %s, lockedCores = %s, "
                "bookedCores = %s" % (
                    report.host.name, report.coreInfo.totalCores, report.coreInfo.idleCores,
                    report.coreInfo.lockedCores, report.coreInfo.bookedCores))
        elif self.verbose == 3:
            print("Receiving reportStatus")
            print(report)
        elif self.verbose == 4:
            self._trackUpdateTime(report)

    def ReportRunningFrameCompletion(self, request, context):
        report = request.frameCompleteReport
        self.lastReportRunningFrameCompletion = report

        if self.verbose == 0:
            pass
        elif self.verbose == 1:
            sys.stdout.write("X")
            sys.stdout.flush()
        elif self.verbose == 2:
            print(
                "%s : FrameCompletion.host    - nimbyEnabled = %s, numProcs = %s, "
                "coresPerProc = %d, load = %s, bootTime = %s" % (
                    report.host.name, report.host.nimbyEnabled, report.host.numProcs,
                    report.host.coresPerProc, report.host.load,report.host.bootTime))
            print(
                "%s : FrameCompletion.host    - totalSwap = %s, totalMem = %s, totalMcp = %s, "
                "freeSwap = %s, freeMem = %s, freeMcp = %s" % (
                    report.host.name, report.host.totalSwap, report.host.totalMem,
                    report.host.totalMcp, report.host.freeSwap, report.host.freeMem,
                    report.host.freeMcp))
            print("%s : FrameCompletion.host    - tags = %s" % (report.host.name, report.host.tags))
            print(
                "%s : FrameCompletion.frame   - jobId = %s, frameId = %s, numCores = %d, "
                "usedMem = %d" % (
                    report.host.name, report.frame.jobId, report.frame.frameId,
                    report.frame.numCores, report.frame.usedMem))
            print(
                "%s : FrameCompletion         - exitStatus = %s, exitSignal = %s, "
                "runTime = %s, maxRss = %s" % (
                    report.host.name, report.exitStatus, report.exitSignal, report.runTime,
                    report.maxRss))
        elif self.verbose == 3:
            print("Receiving reportRunningFrameCompletion")
            print(report)
