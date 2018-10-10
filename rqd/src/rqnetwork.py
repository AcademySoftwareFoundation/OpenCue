
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

import os
import sys
import time
import signal
import logging as log
import platform
import traceback
import subprocess

from concurrent import futures

import rqconstants
import rqutil

import Ice
libPath = os.path.dirname(__file__)
for slice in ["--all -I{PATH}/slice/spi -I{PATH}/slice/cue {PATH}/slice/cue/rqd_ice.ice",
              "--all -I{PATH}/slice/spi -I{PATH}/slice/cue {PATH}/slice/cue/cue_ice.ice"]:
    Ice.loadSlice(slice.replace("{PATH}", libPath))
import cue.RqdIce as RqdIce
import cue.CueIce as CueIce
import spi.SpiIce as SpiIce

import grpc
import report_pb2
import rqd_pb2_grpc
import rqdservicers


class RunningFrame(object):

    def __init__(self, rqCore, runFrame):
        """RunningFrame class initialization"""
        self.rqCore = rqCore
        self.runFrame = runFrame
        self.ignoreNimby = runFrame.ignoreNimby
        self.frameId = runFrame.frameId

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
            resourceId=self.runFrame.resourceId,
            jobId=self.runFrame.jobId,
            jobName=self.runFrame.jobName,
            frameId=self.runFrame.frameId,
            frameName=self.runFrame.frameName,
            layerId=self.runFrame.layerId,
            numCores=self.runFrame.numCores,
            startTime=self.runFrame.startTime,
            maxRss=self.maxRss,
            rss=self.rss,
            maxVsize=self.maxVsize,
            vsize=self.vsize,
            attributes=self.runFrame.attributes
        )
        return runningFrameInfo

    def status(self):
        """Returns the status of the frame"""
        return self.runningFrameInfo()

    def kill(self, message = ""):
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


class RqdStatic(RqdIce.RqdStatic):
    """Maintains ice calls for rqdStatic interface. These are then passed to
    the rqcore functions"""
    def __init__(self, communicator, iceObjectAdapter, rqCore):
        """RqdStatuc class initialization"""
        identity = communicator.stringToIdentity(rqconstants.STRING_FROM_CUEBOT)
        iceObjectAdapter.add(self, identity)

        self.rqCore = rqCore
        self.__communicator = communicator
        self.__iceObjectAdapter = iceObjectAdapter

    def shutdown(self):
        """Shuts down the communicator"""
        current.adapter().getCommunicator().shutdown()

    """--------------------------------------------------------------------
        These functions are defined in slice/rqd_ice.ice and called by the
        cuebot via ICE.
       --------------------------------------------------------------------"""

    def launchFrame(self, frame, current = None):
        """Ice call that launches the given frame"""
        log.info("Request recieved: launchFrame")
        return self.rqCore.launchFrame(frame)

    def getRunningFrame(self, frameId, current = None):
        """Ice call that returns a frame proxy for the given frameId"""
        log.info("Request recieved: getRunningFrame")
        return self.rqCore.getRunningFrame(frameId)

    def reportStatus(self, current = None):
        """Ice call that returns reportStatus"""
        log.info("Request recieved: reportStatus")
        return self.rqCore.reportStatus()

    def shutdownRqdNow(self, current = None):
        """Ice call that kills all running frames and shuts down rqd"""
        log.info("Request recieved: shutdownRqdNow")
        self.rqCore.shutdownRqdNow()

    def shutdownRqdIdle(self, current = None):
        """Ice call that locks all cores and shuts down rqd when it is idle.
           unlockAll will abort the request."""
        log.info("Request recieved: shutdownRqdIdle")
        self.rqCore.shutdownRqdIdle()

    def restartRqdNow(self, current = None):
        """Ice call that kills all running frames and restarts rqd"""
        log.info("Request recieved: restartRqdNow")
        self.rqCore.restartRqdNow()

    def restartRqdIdle(self, current = None):
        """Ice call that that locks all cores and restarts rqd when idle.
           unlockAll will abort the request."""
        log.info("Request recieved: restartRqdIdle")
        self.rqCore.restartRqdIdle()

    def rebootNow(self, current = None):
        """Ice call that kills all running frames and reboots the host."""
        log.info("Request recieved: rebootNow")
        self.rqCore.rebootNow()

    def rebootIdle(self, current = None):
        """Ice call that that locks all cores and reboots the host when idle.
           unlockAll will abort the request."""
        log.info("Request recieved: rebootIdle")
        self.rqCore.rebootIdle()

    def nimbyOn(self, current = None):
        """Ice call that activates nimby"""
        log.info("Request recieved: nimbyOn")
        self.rqCore.nimbyOn()

    def nimbyOff(self, current = None):
        """Ice call that deactivates nimby"""
        log.info("Request recieved: nimbyOff")
        self.rqCore.nimbyOff()

    def lock(self, cores, current = None):
        """Ice call that locks a specific number of cores"""
        log.info("Request recieved: lock %d" % core)
        self.rqCore.lock(cores)

    def lockAll(self, current = None):
        """Ice call that locks all cores"""
        log.info("Request recieved: lockAll")
        self.rqCore.lockAll()

    def unlock(self, cores, current = None):
        """Ice call that unlocks a specific number of cores"""
        log.info("Request recieved: unlock %d" % cores)
        self.rqCore.unlock(cores)

    def unlockAll(self, current = None):
        """Ice call that unlocks all cores"""
        log.info("Request recieved: unlockAll")
        self.rqCore.unlockAll()


class GrpcServer(object):
    """
    gRPC server class for managing messages from cuebot back to rqd.
    This is used for controlling the render host and task actions initiated by cuebot and cuegui.
    """

    def __init__(self, rqCore):
        self.rqCore = rqCore
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=rqconstants.RQD_GRPC_MAX_WORKERS))
        self.servicers = ['RqdStaticServicer']
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


class Network(Ice.Application):
    """Handles ice communication"""
    def __init__(self, rqCore):
        """Network class initialization"""
        self.rqCore = rqCore
        self.__cuebotProxy = None
        self.grpcServer = None

    def start_grpc(self):
        self.grpcServer = GrpcServer(self.rqCore)
        self.grpcServer.serve()

    def start(self):
        """Creates ice communicator and whiteboard proxy"""
        initData = Ice.InitializationData()
        props = initData.properties = Ice.createProperties()

        props.setProperty('Ice.ThreadPool.Server.Size', '8',)

        if Ice.intVersion() >= 30600:
            props.setProperty('Ice.ACM.Client.Timeout', '60',)
            # Don't close connection when waiting for a response
            # from a server running Ice < 3.6.
            # Can remove when server is Ice >= 3.6.
            props.setProperty('Ice.ACM.Client.Close', '1',)
        else:
            props.setProperty('Ice.ACM.Client', '2',)

        # Allow Ice 3.5 clients, remove when server is also Ice 3.5
        if Ice.intVersion() >= 30500:
            props.setProperty('Ice.Default.EncodingVersion', '1.0')

        self.__communicator = Ice.initialize(initData)

        try:
            self.__iceObjectAdapter = self.__communicator.createObjectAdapterWithEndpoints(rqconstants.STRING_FROM_CUEBOT, 'default -p %s' % rqconstants.RQD_PORT)
        except Ice.SocketException:
            log.critical("Unable to open socket, "
                         "another instance of rqd must be running, exiting...")
            sys.exit(1)

        # Register all the static servants with the object adapter.
        RqdStatic(self.__communicator, self.__iceObjectAdapter, self.rqCore)

        # Activate the server.
        self.__iceObjectAdapter.activate()

        signal.signal(signal.SIGINT, self.signalHandler)

        if rqconstants.CUEBOT_HOSTNAME:
            # Using cuebot proxy from constants file:
            proxyString = rqconstants.STRING_TO_CUEBOT
            for cuebot in rqconstants.CUEBOT_HOSTNAME.split():
                proxyString += ":tcp -h %s -p %s -t %s" % (cuebot,
                                                           rqconstants.CUEBOT_PORT,
                                                           rqconstants.RQD_TIMEOUT)

            proxy = self.__communicator.stringToProxy(proxyString)
            log.warning("Using configured cuebot instead of one from the "
                        "facility name server: %s" % rqconstants.CUEBOT_HOSTNAME)
        else:
            # Get cuebot proxy from the facility ice name server
            base = self.__communicator.stringToProxy(rqconstants.FACILITY_ICE_NAMESERVER)
            try:
                facilityServer = FacilityIce.FacilityStaticPrx.checkedCast(base)
            except Exception, e:
                log.critical("Unable to contact facility name server, exiting...")
                log.critical(e)
                self.rqCore.shutdown()
                sys.exit(1)

            try:
                facility = facilityServer.getThisFacility()
                self.__communicator.setDefaultLocator(facility.locatorProxy)
            except Exception, e:
                log.critical("Unable to get the current facility, exiting...")
                log.critical(e)
                self.rqCore.shutdown()
                sys.exit(1)

            try:
                proxy = facility.facilityProxy.getCueRqdReportStatic()
            except Exception, e:
                log.critical("Unable to get the cuebot proxy for this facility, exiting...")
                log.critical(e)
                self.rqCore.shutdown()
                sys.exit(1)

        while self.__cuebotProxy is None and not self.__communicator.isShutdown():
            try:
                self.__cuebotProxy = CueIce.RqdReportStaticPrx.checkedCast(proxy)
                if not self.__cuebotProxy:
                    raise Exception("Invalid proxy")
            except Ice.ConnectionRefusedException:
                log.critical("Cuebot connection refused for: \"%s\" Sleeping"
                             % proxy)
                time.sleep(rqconstants.RQD_RETRY_STARTUP_CONNECT_DELAY)
            except Exception,e:
                log.critical("Unable to connect to Cuebot at: \"%s\" Sleeping"
                             % proxy)
                log.critical(e)
                time.sleep(rqconstants.RQD_RETRY_STARTUP_CONNECT_DELAY)

        if self.__communicator.isShutdown():
            sys.exit()

        self.rqCore.iceConnected()

    def shutdown(self):
        """Shuts down the ice communicator"""
        self.__communicator.shutdown()

    def waitForShutdown(self):
        """Waits for the communicator to shutdown"""
        self.__communicator.waitForShutdown()
        self.__communicator.destroy()

    def add(self, runningFrame):
        """Adds a frame servant to the ice object adapter
        @type  runningFrame: RunningFrame
        @param runningFrame: RunningFrame object"""
        self.__iceObjectAdapter.add(runningFrame, runningFrame.getIceId())

    def remove(self, iceId):
        """Remove a servant from ice object adapter
        @type  frameId: string
        @param frameId: A frame's unique Id"""
        self.__iceObjectAdapter.remove(iceId)

    def signalHandler(self, sig, frame):
        """Catches any signals and calls shutdown"""
        self.rqCore.shutdownRqdNow()

    def __sendWithErrorChecking(self, report, type, retry = False):
        """Handles exceptions and retrys associated with sending reports.
        @type  report: RqdIce.FrameCompleteReport or RqdIce.BootReport or RqdIce.HostReport
        @param report: The report to be sent
        @type  type: string
        @param type: The name of the report function required
        @type  retry: boolean
        @param retry: If the message should sent until it succeeds
        @rtype:  string
        @return: Command file location"""
        log.info("Sending %s" % type)
        log.debug(report)

        if retry:
            endMsg = "Waiting to retry..."
        else:
            endMsg = ""
        failMsg = "Sending %s failed." % type

        while self.__cuebotProxy:
            try:
                if type == "reportRqdStartup":
                    self.__cuebotProxy.reportRqdStartup(report)
                elif type == "reportStatus":
                    self.__cuebotProxy.reportStatus(report)
                elif type == "reportRunningFrameCompletion":
                    self.__cuebotProxy.reportRunningFrameCompletion(report)
                return True
            except Ice.UnknownLocalException, e:
                if e.unknown.find("Ice.MarshalException") != -1 or \
                   e.unknown.find("Ice.UnmarshalOutOfBoundsException") != -1:
                    log.critical("%s Slice definition mismatch between"
                                 "rqd and cuebot. %s" % (failMsg, endMsg))
                else:
                    log.critical("%s %s" % (failMsg, endMsg))
                    log.critical(e)
            except Ice.ConnectionRefusedException:
                log.critical("%s Cuebot connection refused. %s" % (failMsg,
                                                                   endMsg))
            except Exception, e:
                log.critical("%s %s" % (failMsg, endMsg))
                log.critical(e)

            if retry:
                time.sleep(rqconstants.RQD_RETRY_CRITICAL_REPORT_DELAY)
            else:
                return False

            if self.__communicator.isShutdown():
                sys.exit()

    #-----------------------------------------------------------------------
    # These functions wrap calls to the Cuebot, the function names are
    # arbratary and not required for ICE functionality.
    #-----------------------------------------------------------------------

    def reportRqdStartup(self, report):
        """Wraps the ability to send a startup report to rqd via Ice"""
        self.__sendWithErrorChecking(report, "reportRqdStartup", True)

    def reportStatus(self, report):
        """Wraps the ability to send a status report to the cuebot via Ice"""
        self.__sendWithErrorChecking(report, "reportStatus", False)

    def reportRunningFrameCompletion(self, report):
        """Wraps the ability to send a running frame completion report
           to the cuebot via Ice"""
        self.__sendWithErrorChecking(report, "reportRunningFrameCompletion", True)

class SpiAutoPopulatedExceptionMixin:
    """Mixin class for subtypes of the Ice generated VnpIce exception
    classes.  This mixin initializes the stackTrace and causedBy
    fields in the base VnpIce exception class."""

    def __init__(self, excInfo):
        """Initialize the stackTrace and causedBy fields in the base
        VnpIce exception class this mixin is mixed in with.  If the
        VnpIce exception that is being initialized should be chained
        with another exception, then exc_info should be the result of
        a sys.exc_info() call, otherwise, it should be None.

        Because the exception information from sys.exc_info() persists
        even after an exception has been handled, there is no way for
        this method to know if the information in sys.exc_info()
        should be chained into the new VnpIce exception that is
        currently being initialized, unless this mixin were to require
        that sys.exc_clear() were to be used to clear any recorded
        exception information.  However, this would place an
        additional burden on the programmer and be easily forgotten.
        So if the new VnpIce exception should chain another exception,
        then the exception information must be passed in explicitly."""

        # Populate the stackTrace field in the exception using a newly
        # generated stack trace for the construction of the VnpIce
        # exception instance.  Reverse the Python stack trace so that
        # the stack appears in the same order as the Java stack.
        frames = traceback.extract_stack()[:-2]
        self.stackTrace = [ '%s:%s in %s: %s' % f for f in frames ]
        self.stackTrace.reverse()

        # Populate the causedBy field if a chained exception was
        # given.
        if excInfo is not None:
            excType, exc, tb = excInfo

            if excType is not None and \
               exc is not None and \
               tb is not None:
                # A new SpiIceException should not be chained to
                # another SpiIceException, so warn the developers that
                # they should catch and handle the SpiIceException
                # separately from any other exceptions.
                if isinstance(exc, SpiIce.SpiIceException):
                    # ### Log this warning.
                    pass

                frames = traceback.extract_tb(tb)
                stacktrace = [ '%s:%s in %s: %s' % f for f in frames ]
                stacktrace.reverse()

                message = 'Caught %s: %s' % (excType, str(exc))
                self.causedBy = [ SpiIce.SpiIceCause(message, stacktrace) ]
            else:
                self.causedBy = [ ]
        else:
            self.causedBy = [ ]

class RqdIceException(RqdIce.FrameSetupFailureException,
                      SpiAutoPopulatedExceptionMixin):
    """Subclass of VnpIceUnsupportedOperationException which
    automatically initializes the stackTrace and causedBy fields."""

    def __init__(self, message, excInfo=None):
        """RqdIceException class initialization"""
        RqdIce.FrameSetupFailureException.__init__(self, message)
        SpiAutoPopulatedExceptionMixin.__init__(self, excInfo)

