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
import abc
import atexit
import datetime
import logging
import os
import platform
import subprocess
import time

# Disable GRPC fork support to avoid the warning:
#  "fork_posix.cc Other threads are currently calling into gRPC, skipping fork() handlers"
# Adding this environment variable doesn't change the server behaviour
os.environ["GRPC_ENABLE_FORK_SUPPORT"] = "false"

# pylint: disable=wrong-import-position
import grpc

import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.report_pb2_grpc
import rqd.compiled_proto.rqd_pb2_grpc
import rqd.rqconstants
import rqd.rqexceptions
import rqd.rqdservicers
import rqd.rqutil


log = logging.getLogger(__name__)


class RunningFrame(object):
    """Represents a running frame."""

    def __init__(self, rqCore, runFrame):
        self.rqCore = rqCore
        self.runFrame = runFrame
        self.ignoreNimby = runFrame.ignore_nimby
        self.frameId = runFrame.frame_id

        self.killMessage = ""

        self.pid = runFrame.pid
        self.exitStatus = None
        self.frameAttendantThread = None
        self.exitSignal = 0
        self.runTime = 0

        self.rss = 0
        self.maxRss = 0
        self.vsize = 0
        self.maxVsize = 0

        self.usedGpuMemory = 0
        self.maxUsedGpuMemory = 0

        self.usedSwapMemory = 0

        self.realtime = 0
        self.utime = 0
        self.stime = 0

        self.lluTime = 0
        self.childrenProcs = {}
        self.completeReportSent = False

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
            num_gpus=self.runFrame.num_gpus,
            max_used_gpu_memory=self.maxUsedGpuMemory,
            used_gpu_memory=self.usedGpuMemory,
            children=self._serializeChildrenProcs(),
            used_swap_memory=self.usedSwapMemory,
        )
        return runningFrameInfo

    def _serializeChildrenProcs(self):
        """ Collect and serialize children proc stats for protobuf
            Convert to Kilobytes:
            * RSS (Resident set size) measured in pages
            * Statm size measured in pages
            * Stat size measured in bytes

        :param data: dictionary
        :return: serialized children proc host stats
        :rtype: rqd.compiled_proto.report_pb2.ChildrenProcStats
        """
        childrenProc = rqd.compiled_proto.report_pb2.ChildrenProcStats()
        for proc, values in self.childrenProcs.items():
            procStats = rqd.compiled_proto.report_pb2.ProcStats()
            procStatFile = rqd.compiled_proto.report_pb2.Stat()
            procStatmFile = rqd.compiled_proto.report_pb2.Statm()

            procStatFile.pid = proc
            procStatFile.name = values["name"] if values["name"] else ""
            procStatFile.state = values["state"]
            procStatFile.vsize = values["vsize"]
            procStatFile.rss = values["rss"]

            procStatmFile.size = values["statm_size"]
            procStatmFile.rss = values["statm_rss"]
            # pylint: disable=no-member
            procStats.stat.CopyFrom(procStatFile)
            procStats.statm.CopyFrom(procStatmFile)
            procStats.cmdline = " ".join(values["cmd_line"])

            startTime = datetime.datetime.now() - datetime.timedelta(seconds=values["start_time"])
            procStats.start_time = startTime.strftime("%Y-%m-%d %H:%M%S")
            childrenProc.children.extend([procStats])
            # pylint: enable=no-member
        return childrenProc

    def status(self):
        """Returns the status of the frame"""
        return self.runningFrameInfo()

    def kill(self, message=""):
        """Kills the frame"""
        log.info("Request received: kill")
        if self.frameAttendantThread is None:
            log.warning(
                "Kill requested before frameAttendantThread is created for: %s", self.frameId)
        elif self.frameAttendantThread.is_alive() and self.pid is None:
            log.warning("Kill requested before pid is available for: %s", self.frameId)
        elif self.frameAttendantThread.is_alive():
            # pylint: disable=broad-except
            try:
                if not self.killMessage and message:
                    self.killMessage = message
                rqd.rqutil.permissionsHigh()
                try:
                    if platform.system() == "Windows":
                        # pylint: disable=consider-using-with
                        subprocess.Popen('taskkill /F /T /PID %i' % self.pid, shell=True)
                    else:
                        os.killpg(self.pid, rqd.rqconstants.KILL_SIGNAL)
                finally:
                    log.warning(
                        "kill() successfully killed frameId=%s pid=%s", self.frameId, self.pid)
                    rqd.rqutil.permissionsLow()
            except OSError as e:
                log.warning(
                    "kill() tried to kill a non-existant pid for: %s Error: %s", self.frameId, e)
            # pylint: disable=broad-except
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
        log.warning('Stopping grpc server.')
        self.server.stop(10)

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
        if self.grpcServer:
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
            # create interceptors
            interceptors = (
                RetryOnRpcErrorClientInterceptor(
                    max_attempts=4,
                    sleeping_policy=ExponentialBackoff(init_backoff_ms=100,
                                                       max_backoff_ms=1600,
                                                       multiplier=2),
                    status_for_retry=(grpc.StatusCode.UNAVAILABLE,),
                ),
            )

            cuebots = rqd.rqconstants.CUEBOT_HOSTNAME.strip().split()
            if len(cuebots) == 0:
                raise rqd.rqexceptions.RqdException("CUEBOT_HOSTNAME is empty")
            shuffle(cuebots)
            self.channel = grpc.insecure_channel('%s:%s' % (cuebots[0],
                                                            rqd.rqconstants.CUEBOT_GRPC_PORT))
            self.channel = grpc.intercept_channel(self.channel, *interceptors)
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


# Python 2/3 compatible implementation of ABC
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class SleepingPolicy(ABC):
    """
    Implement policy for sleeping between API retries
    """
    @abc.abstractmethod
    def sleep(self, attempt):
        """
        How long to sleep in milliseconds.
        :param attempt: the number of attempt (starting from zero)
        """
        assert attempt >= 0


class ExponentialBackoff(SleepingPolicy):
    """
    Implement policy that will increase retry period by exponentially in every try
    """
    def __init__(self,
                 init_backoff_ms,
                 max_backoff_ms,
                 multiplier=2):
        """
        inputs in ms
        """
        self._init_backoff = init_backoff_ms
        self._max_backoff = max_backoff_ms
        self._multiplier = multiplier

    def sleep(self, attempt):
        sleep_time_ms = min(
            self._init_backoff * self._multiplier ** attempt,
            self._max_backoff
        )
        time.sleep(sleep_time_ms / 1000.0)


class RetryOnRpcErrorClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.StreamUnaryClientInterceptor
):
    """
    Implement Client/Stream interceptors for GRPC channels to retry
    calls that failed with retry-able states. This is required for
    handling server interruptions that are not automatically handled
    by grpc.insecure_channel
    """
    def __init__(self,
                 max_attempts,
                 sleeping_policy,
                 status_for_retry=None):
        self._max_attempts = max_attempts
        self._sleeping_policy = sleeping_policy
        self._retry_statuses = status_for_retry

    # pylint: disable=inconsistent-return-statements
    def _intercept_call(self, continuation, client_call_details,
                        request_or_iterator):
        for attempt in range(self._max_attempts):
            try:
                return continuation(client_call_details,
                                    request_or_iterator)
            except grpc.RpcError as response:
                # Return if it was last attempt
                if attempt == (self._max_attempts - 1):
                    return response

                # If status code is not in retryable status codes
                # pylint: disable=no-member
                if self._retry_statuses \
                        and hasattr(response, 'code') \
                        and response.code() \
                        not in self._retry_statuses:
                    return response

                self._sleeping_policy.sleep(attempt)

    def intercept_unary_unary(self, continuation, client_call_details,
                              request):
        return self._intercept_call(continuation, client_call_details,
                                    request)

    def intercept_stream_unary(
            self, continuation, client_call_details, request_iterator
    ):
        return self._intercept_call(continuation, client_call_details,
                                    request_iterator)
