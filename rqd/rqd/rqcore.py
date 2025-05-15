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


"""Main RQD module, handles gRPC function implementation and job launching."""


from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from builtins import str
from builtins import object
import datetime
import logging
import os
import platform
import random
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import select
import uuid

import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.rqd_pb2
import rqd.rqconstants
from rqd.rqconstants import DOCKER_AGENT
import rqd.rqexceptions
import rqd.rqmachine
import rqd.rqnetwork
from rqd.rqnimby import Nimby
import rqd.rqutil
import rqd.rqlogging

INT32_MAX = 2147483647
INT32_MIN = -2147483648
log = logging.getLogger(__name__)


class RqCore(object):
    """Main body of RQD, handles the integration of all components,
       the setup and launching of a frame and acts on all gRPC calls
       that are passed from the Network module."""

    def __init__(self, optNimbyoff=False):
        """RqCore class initialization"""
        self.__whenIdle = False
        self.__reboot = False

        self.__optNimbyoff = optNimbyoff

        self.cores = rqd.compiled_proto.report_pb2.CoreDetail(
            total_cores=0,
            idle_cores=0,
            locked_cores=0,
            booked_cores=0,
            reserved_cores=[],
        )

        self.nimby = Nimby(self)

        self.machine = rqd.rqmachine.Machine(self, self.cores)
        self.network = rqd.rqnetwork.Network(self)
        self.__threadLock = threading.Lock()
        self.__cache = {}
        self.updateRssThread = None
        self.onIntervalThread = None
        self.intervalStartTime = 0
        self.intervalSleepTime = rqd.rqconstants.RQD_MIN_PING_INTERVAL_SEC

        #  pylint: disable=unused-private-member
        self.__cluster = None
        self.__session = None
        self.__stmt = None
        self._heartbeat_counter = 0

        self.docker_agent = None

        if DOCKER_AGENT:
            self.docker_agent = DOCKER_AGENT
            self.docker_agent.refreshFrameImages()

        self.backup_cache_path = None
        if rqd.rqconstants.BACKUP_CACHE_PATH:
            if not rqd.rqconstants.DOCKER_AGENT:
                log.warning("Cache backup is currently only available "
                    "when RUN_ON_DOCKER mode")
            else:
                self.backup_cache_path = rqd.rqconstants.BACKUP_CACHE_PATH
                if not os.path.exists(os.path.dirname(self.backup_cache_path)):
                    os.makedirs(os.path.dirname(self.backup_cache_path))
                self.recoverCache()

        signal.signal(signal.SIGINT, self.handleExit)
        signal.signal(signal.SIGTERM, self.handleExit)

    def start(self):
        """Called by main to start the rqd service"""
        if self.shouldStartNimby():
            self.nimbyOn()
        self.network.start_grpc()

    def grpcConnected(self):
        """After gRPC connects to the cuebot, this function is called"""
        self.network.reportRqdStartup(self.machine.getBootReport())

        self.updateRssThread = threading.Timer(rqd.rqconstants.RSS_UPDATE_INTERVAL, self.updateRss)
        self.updateRssThread.start()

        self.onIntervalThread = threading.Timer(self.intervalSleepTime, self.onInterval)
        self.intervalStartTime = time.time()
        self.onIntervalThread.start()

        log.warning('RQD Started')

    def onInterval(self, sleepTime=None):

        """This is called by self.grpcConnected as a timer thread to execute
           every interval"""
        if sleepTime is None:
            self.intervalSleepTime = random.randint(
                rqd.rqconstants.RQD_MIN_PING_INTERVAL_SEC,
                rqd.rqconstants.RQD_MAX_PING_INTERVAL_SEC)
        else:
            self.intervalSleepTime = sleepTime
        try:
            self.onIntervalThread = threading.Timer(self.intervalSleepTime, self.onInterval)
            self.intervalStartTime = time.time()
            self.onIntervalThread.start()
        # pylint: disable=broad-except
        except Exception as e:
            log.critical(
                'Unable to schedule a ping due to %s at %s',
                e, traceback.extract_tb(sys.exc_info()[2]))

        try:
            if self.__whenIdle and not self.__cache:
                if not self.machine.isUserLoggedIn():
                    self.shutdownRqdNow()
                else:
                    log.warning('Shutdown requested but a user is logged in.')
        # pylint: disable=broad-except
        except Exception as e:
            log.warning(
                'Unable to shutdown due to %s at %s', e, traceback.extract_tb(sys.exc_info()[2]))

        # Count number of times this function is being executed to allow
        # executing action on different heartbeat counts
        if self._heartbeat_counter >= sys.maxsize:
            self._heartbeat_counter = 0
        self._heartbeat_counter += 1

        # Periodically attempt to start nimby if it failed previously
        try:
            self.retryNimby()
        # pylint: disable=broad-except
        except Exception as e:
            log.warning("Failed to initialize Nimby. %s", e)

        try:
            self.sendStatusReport()
        # pylint: disable=broad-except
        except Exception:
            log.exception('Unable to send status report')

    def retryNimby(self):
        """Ensure nimby is active if required"""
        if self.shouldStartNimby() and not self.nimby.is_ready and self._heartbeat_counter % 5 == 0:
            log.warning("Retrying to initialize Nimby")
            self.nimby = Nimby(self)
            self.nimbyOn()

    def updateRss(self):
        """Triggers and schedules the updating of rss information"""
        if self.__cache:
            try:
                self.machine.rssUpdate(self.__cache)
                if self.backup_cache_path:
                    self.backupCache()
            finally:
                self.updateRssThread = threading.Timer(
                    rqd.rqconstants.RSS_UPDATE_INTERVAL, self.updateRss)
                self.updateRssThread.start()

    def backupCache(self):
        """Backs up a copy of the running frames cache for a possible recovery.
        each backup is destructive and erases the last known state"""
        if not self.backup_cache_path:
            return
        with open(self.backup_cache_path, "wb") as f:
            for item in list(self.__cache.values()):
                serialized = item.runFrame.SerializeToString()
                f.write(len(serialized).to_bytes(4, byteorder="big"))
                f.write(serialized)

    def recoverCache(self):
        """Reload the running frames from the latest backup. The backup file
        will be rejected if it hasn't been updated recently
        (rqconstants.BACKUP_CACHE_TIME_TO_LIVE_SECONDS)
        """
        if not self.backup_cache_path or \
            not os.path.exists(self.backup_cache_path) or \
            (time.time() - os.path.getmtime(self.backup_cache_path) > \
                rqd.rqconstants.BACKUP_CACHE_TIME_TO_LIVE_SECONDS):
            return
        with open(self.backup_cache_path, "rb") as f:
            while True:
                # Read length (4 bytes)
                length_bytes = f.read(4)
                if not length_bytes:
                    break  # End of file

                length = int.from_bytes(length_bytes, byteorder='big')
                # Read the message data
                message_data = f.read(length)

                run_frame = rqd.compiled_proto.rqd_pb2.RunFrame()
                # Ignore frames that failed to be parsed
                try:
                    run_frame.ParseFromString(message_data)
                    log.warning("Recovered frame %s.%s", run_frame.job_name, run_frame.frame_name)
                    running_frame = rqd.rqnetwork.RunningFrame(self, run_frame)
                    running_frame.frameAttendantThread = FrameAttendantThread(
                        self, run_frame, running_frame, recovery_mode=True)
                    # Make sure cores are accounted for
                    # pylint: disable=no-member
                    self.cores.idle_cores -= run_frame.num_cores
                    self.cores.booked_cores += run_frame.num_cores
                    # pylint: enable=no-member

                    running_frame.frameAttendantThread.start()
                # pylint: disable=broad-except
                except Exception:
                    pass
                    # Ignore frames that got corrupted

    def getFrame(self, frameId):
        """Gets a frame from the cache based on frameId
        @type  frameId: string
        @param frameId: A frame's unique Id
        @rtype:  rqd.rqnetwork.RunningFrame
        @return: rqd.rqnetwork.RunningFrame object"""
        return self.__cache[frameId]

    def getFrameKeys(self):
        """Gets a list of all keys from the cache
        @rtype:  list
        @return: List of all frameIds running on host"""
        return list(self.__cache.keys())

    def storeFrame(self, frameId, runningFrame):
        """Stores a frame in the cache and adds the network adapter
        @type  frameId: string
        @param frameId: A frame's unique Id
        @type  runningFrame: rqd.rqnetwork.RunningFrame
        @param runningFrame: rqd.rqnetwork.RunningFrame object"""
        with self.__threadLock:
            if frameId in self.__cache:
                raise rqd.rqexceptions.RqdException(
                    "frameId " + frameId + " is already running on this machine")
            self.__cache[frameId] = runningFrame

    def deleteFrame(self, frameId):
        """Deletes a frame from the cache
        @type  frameId: string
        @param frameId: A frame's unique Id"""
        with self.__threadLock:
            if frameId in self.__cache:
                del self.__cache[frameId]
                # pylint: disable=no-member
                if not self.__cache and self.cores.reserved_cores:
                    # pylint: disable=no-member
                    log.error(
                        'No running frames but reserved_cores is not empty: %s',
                        self.cores.reserved_cores)
                    # pylint: disable=no-member
                    self.cores.reserved_cores.clear()
                log.info("Successfully delete frame with Id: %s", frameId)
            else:
                log.info("Frame with Id: %s not found in cache", frameId)

    def killAllFrame(self, reason):
        """Will execute .kill() on every frame in cache until no frames remain
        @type  reason: string
        @param reason: Reason for requesting all frames to be killed"""

        if self.__cache:
            log.warning(
                "killAllFrame called due to: %s\n%s", reason, ",".join(self.getFrameKeys()))

        while self.__cache:
            if reason.startswith("NIMBY"):
                # Since this is a nimby kill, ignore any frames that are ignoreNimby
                frameKeys = [
                    frame.frameId for frame in list(self.__cache.values()) if not frame.ignoreNimby]
            else:
                frameKeys = list(self.__cache.keys())

            if not frameKeys:
                # No frames left to kill
                return

            for frameKey in frameKeys:
                try:
                    self.__cache[frameKey].kill(reason)
                except KeyError:
                    pass
            time.sleep(1)

    def releaseCores(self, reqRelease, releaseHT=None, releaseGpus=None):
        """The requested number of cores are released
        @type  reqRelease: int
        @param reqRelease: Number of cores to release, 100 = 1 physical core"""
        with self.__threadLock:
            # pylint: disable=no-member
            self.cores.booked_cores -= reqRelease
            maxRelease = (self.cores.total_cores -
                          self.cores.locked_cores -
                          self.cores.idle_cores -
                          self.cores.booked_cores)

            if maxRelease > 0:
                self.cores.idle_cores += min(maxRelease, reqRelease)
            # pylint: enable=no-member

            if releaseHT:
                self.machine.releaseHT(releaseHT)

            if releaseGpus:
                self.machine.releaseGpus(releaseGpus)

        # pylint: disable=no-member
        if self.cores.idle_cores > self.cores.total_cores:
            log.critical(
                "idle_cores (%d) have become greater than total_cores (%d): %s at %s",
                self.cores.idle_cores, self.cores.total_cores, sys.exc_info()[0],
                traceback.extract_tb(sys.exc_info()[2]))
        # pylint: enable=no-member

    def shutdown(self):
        """Shuts down all rqd systems"""
        self.nimbyOff()
        if self.onIntervalThread is not None:
            self.onIntervalThread.cancel()
        if self.updateRssThread is not None:
            self.updateRssThread.cancel()
        elif self.__reboot:
            log.warning("Rebooting machine by request")
            self.machine.reboot()
        else:
            log.warning("Shutting down RQD by request. pid(%s)", os.getpid())
        self.network.stopGrpc()
        # Using sys.exit would raise SystemExit, giving exception handlers a chance
        # to block this
        # pylint: disable=protected-access
        os._exit(0)

    def handleExit(self, signalnum, flag):
        """Shutdown threads and exit RQD."""
        del signalnum
        del flag
        self.shutdown()

    def launchFrame(self, runFrame):
        """This will setup for the launch the frame specified in the arguments.
        If a problem is encountered, a CueException will be thrown.
        @type   runFrame: RunFrame
        @param  runFrame: rqd_pb2.RunFrame"""
        log.info("Running command %s for %s", runFrame.command, runFrame.frame_id)
        log.debug(runFrame)

        #
        # Check for reasons to abort launch
        #

        if self.machine.state != rqd.compiled_proto.host_pb2.UP:
            err = "Not launching, rqd HardwareState is not Up"
            log.info(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        if self.__whenIdle:
            err = "Not launching, rqd is waiting for idle to shutdown"
            log.info(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        if self.nimby.locked and not runFrame.ignore_nimby:
            err = "Not launching, rqd is lockNimby and not Ignore Nimby"
            log.info(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        if runFrame.frame_id in self.__cache:
            err = "Not launching, frame is already running on this proc %s" % runFrame.frame_id
            log.critical(err)
            raise rqd.rqexceptions.DuplicateFrameViolationException(err)

        if runFrame.HasField("uid") and runFrame.uid <= 0:
            err = "Not launching, will not run frame as uid=%d" % runFrame.uid
            log.warning(err)
            raise rqd.rqexceptions.InvalidUserException(err)

        if runFrame.num_cores <= 0:
            err = "Not launching, numCores must be > 0"
            log.warning(err)
            raise rqd.rqexceptions.CoreReservationFailureException(err)

        # See if all requested cores are available
        with self.__threadLock:
            # pylint: disable=no-member
            if self.cores.idle_cores < runFrame.num_cores:
                err = "Not launching, insufficient idle cores"
                log.critical(err)
                raise rqd.rqexceptions.CoreReservationFailureException(err)
            # pylint: enable=no-member

            if runFrame.environment.get('CUE_THREADABLE') == '1':
                reserveHT = self.machine.reserveHT(runFrame.num_cores)
                if reserveHT:
                    runFrame.attributes['CPU_LIST'] = reserveHT

            if runFrame.num_gpus:
                reserveGpus = self.machine.reserveGpus(runFrame.num_gpus)
                if reserveGpus:
                    runFrame.attributes['GPU_LIST'] = reserveGpus

            # They must be available at this point, reserve them
            # pylint: disable=no-member
            self.cores.idle_cores -= runFrame.num_cores
            self.cores.booked_cores += runFrame.num_cores
            # pylint: enable=no-member

        runningFrame = rqd.rqnetwork.RunningFrame(self, runFrame)
        runningFrame.frameAttendantThread = FrameAttendantThread(self, runFrame, runningFrame)
        runningFrame.frameAttendantThread.start()

    def getRunningFrame(self, frameId):
        """Gets the currently running frame."""
        try:
            return self.__cache[frameId]
        except KeyError:
            log.info("frameId %s is not running on this machine", frameId)
            return None

    def getCoreInfo(self):
        """Gets the core info report."""
        return self.cores

    def reportStatus(self):
        """Replies with hostReport"""
        return self.machine.getHostReport()

    def shutdownRqdNow(self):
        """Kill all running frames and shutdown RQD"""
        self.machine.state = rqd.compiled_proto.host_pb2.DOWN
        # When running on docker, stopping RQD will trigger the creation of a new container,
        # and running frames will be recovered on a new instance.
        # Thus, shutdown doesn't require locking and killing frames when running on docker.
        if self.docker_agent is not None:
            self.__reboot = False
            self.shutdown()
        else:
            try:
                self.lockAll()
                self.killAllFrame("shutdownRqdNow Command")
                    # pylint: disable=broad-except
            except Exception:
                log.exception("Failed to kill frames, stopping service anyways")
            if not self.__cache:
                self.shutdown()

    def shutdownRqdIdle(self):
        """When machine is idle, shutdown RQD"""
        log.info("shutdownRqdIdle")
        self.lockAll()
        self.__whenIdle = True
        self.sendStatusReport()
        if not self.__cache:
            self.shutdownRqdNow()

    def rebootNow(self):
        """Kill all running frames and reboot machine.
           This is not available when a user is logged in"""
        log.warning('Requested to reboot now')
        if self.machine.isUserLoggedIn():
            err = ('Rebooting via RQD is not supported for a desktop machine '
                   'when a user is logged in')
            log.warning(err)
            raise rqd.rqexceptions.RqdException(err)
        self.__reboot = True
        self.shutdownRqdNow()

    def rebootIdle(self):
        """When machine is idle, reboot it"""
        log.warning('Requested to reboot machine when idle')
        self.lockAll()
        self.__whenIdle = True
        self.__reboot = True
        self.sendStatusReport()
        if not self.__cache and not self.machine.isUserLoggedIn():
            self.shutdownRqdNow()

    def shouldStartNimby(self):
        """Decide if the nimby logic should be turned on"""
        if self.__optNimbyoff:
            log.warning('Nimby startup has been disabled via --nimbyoff')
            return False

        if rqd.rqconstants.OVERRIDE_NIMBY:
            log.warning('Nimby startup has been enabled via OVERRIDE_NIMBY')
            return True

        return False

    def nimbyOn(self):
        """Activates nimby, does not kill any running frames until next nimby
           event. Also does not unlock until sufficient idle time is reached."""
        if self.nimby and self.nimby.is_ready:
            try:
                self.nimby.start()
                log.warning("Nimby has been activated")
            # pylint: disable=broad-except
            except Exception:
                err = "Nimby failed to start. Unexpected state"
                log.exception(err)

    def nimbyOff(self):
        """Deactivates nimby and unlocks any nimby lock"""
        self.nimby.stop()
        log.info("Nimby has been deactivated")

    def onNimbyLock(self):
        """This is called by nimby when it locks the machine.
           All running frames are killed.
           A new report is sent to the cuebot."""
        self.killAllFrame("NIMBY Triggered")
        self.sendStatusReport()

    def onNimbyUnlock(self, asOf=None):
        """This is called by nimby when it unlocks the machine due to sufficient
           idle. A new report is sent to the cuebot.
        @param asOf: Time when idle state began, if known."""
        del asOf
        self.sendStatusReport()

    def lock(self, reqLock):
        """Locks the requested core.
        If a locked status changes, a status report is sent to the cuebot.
        @type  reqLock: int
        @param reqLock: Number of cores to lock, 100 = 1 physical core"""
        sendUpdate = False
        with self.__threadLock:
            # pylint: disable=no-member
            numLock = min(self.cores.total_cores - self.cores.locked_cores,
                          reqLock)
            if numLock > 0:
                self.cores.locked_cores += numLock
                self.cores.idle_cores -= min(numLock, self.cores.idle_cores)
                sendUpdate = True
            # pylint: enable=no-member

        log.debug(self.cores)

        if sendUpdate:
            self.sendStatusReport()

    def lockAll(self):
        """"Locks all cores on the machine.
            If a locked status changes, a status report is sent."""
        sendUpdate = False
        with self.__threadLock:
            # pylint: disable=no-member
            if self.cores.locked_cores < self.cores.total_cores:
                self.cores.locked_cores = self.cores.total_cores
                self.cores.idle_cores = 0
                sendUpdate = True
            # pylint: enable=no-member

        log.debug(self.cores)

        if sendUpdate:
            self.sendStatusReport()

    def unlock(self, reqUnlock):
        """Unlocks the requested number of cores.
        Also resets reboot/shutdown/restart when idle requests.
        If a locked status changes, a status report is sent to the cuebot.
        @type  reqUnlock: int
        @param reqUnlock: Number of cores to unlock, 100 = 1 physical core"""

        sendUpdate = False

        if (self.__whenIdle or self.__reboot or
            self.machine.state != rqd.compiled_proto.host_pb2.UP):
            sendUpdate = True

        self.__whenIdle = False
        self.__reboot = False
        self.machine.state = rqd.compiled_proto.host_pb2.UP

        with self.__threadLock:
            # pylint: disable=no-member
            numUnlock = min(self.cores.locked_cores, reqUnlock)
            if numUnlock > 0:
                self.cores.locked_cores -= numUnlock
                self.cores.idle_cores += numUnlock
                sendUpdate = True
            # pylint: enable=no-member

        log.debug(self.cores)

        if sendUpdate:
            self.sendStatusReport()

    def unlockAll(self):
        """"Unlocks all cores on the machine.
            Also resets reboot/shutdown/restart when idle requests.
            If a locked status changes, a status report is sent."""

        sendUpdate = False

        if (self.__whenIdle or self.__reboot
                or self.machine.state != rqd.compiled_proto.host_pb2.UP):
            sendUpdate = True

        self.__whenIdle = False
        self.__reboot = False
        self.machine.state = rqd.compiled_proto.host_pb2.UP

        with self.__threadLock:
            # pylint: disable=no-member
            if self.cores.locked_cores > 0:
                if not self.nimby.locked:
                    self.cores.idle_cores += self.cores.locked_cores
                self.cores.locked_cores = 0
                sendUpdate = True
            # pylint: enable=no-member

        log.debug(self.cores)

        if sendUpdate:
            self.sendStatusReport()

    def sendStatusReport(self):
        """Sends the current host report to Cuebot."""
        self.network.reportStatus(self.machine.getHostReport())

    def isWaitingForIdle(self):
        """Returns whether the host is waiting until idle to take some action."""
        return self.__whenIdle

    def sendFrameCompleteReport(self, runningFrame):
        """Send a frameCompleteReport to Cuebot"""
        if not runningFrame.completeReportSent:
            report = rqd.compiled_proto.report_pb2.FrameCompleteReport()
            # pylint: disable=no-member
            report.host.CopyFrom(self.machine.getHostInfo())
            report.frame.CopyFrom(runningFrame.runningFrameInfo())
            # pylint: enable=no-member

            if runningFrame.exitStatus is None:
                report.exit_status = 1
            else:
                report.exit_status = runningFrame.exitStatus

            report.exit_signal = runningFrame.exitSignal
            report.run_time = int(runningFrame.runTime)

            # If nimby is active, then frame must have been killed by nimby
            # Set the exitSignal to indicate this event
            if self.nimby.locked and not runningFrame.ignoreNimby:
                report.exit_status = rqd.rqconstants.EXITSTATUS_FOR_NIMBY_KILL

            self.network.reportRunningFrameCompletion(report)
            runningFrame.completeReportSent = True

    def sanitizeFrames(self):
        """
        Iterate over the cache and update the status of frames that might have
        completed but never reported back to cuebot.
        """
        for frameId in list(self.__cache.keys()):
            runningFrame = self.__cache[frameId]
            # If the frame was marked as completed (exitStatus) and a report has not been sent
            # try to file the report again
            if runningFrame.exitStatus is not None and not runningFrame.completeReportSent:
                try:
                    self.sendFrameCompleteReport(runningFrame)
                    self.deleteFrame(frameId)
                    log.info("Successfully deleted frame from cache for %s/%s (%s)",
                                  runningFrame.runFrame.job_name,
                                  runningFrame.runFrame.frame_name,
                                  frameId)
                # pylint: disable=broad-except
                except Exception:
                    log.exception("Failed to sanitize frame %s/%s",
                                  runningFrame.runFrame.job_name,
                                  runningFrame.runFrame.frame_name)


class FrameAttendantThread(threading.Thread):
    """Once a frame has been received and checked by RQD, this class handles
       the launching, waiting on, and cleanup work related to running the
       frame."""
    def __init__(self, rqCore: RqCore, runFrame, frameInfo, recovery_mode=False):
        """FrameAttendantThread class initialization
           @type    rqCore: RqCore
           @param   rqCore: Main RQD Object
           @type   runFrame: RunFrame
           @param  runFrame: rqd_pb2.RunFrame
           @type  frameInfo: rqd.rqnetwork.RunningFrame
           @param frameInfo: Servant for running frame
           @type  recovery_mode: bool
           @param recovery_mode: Run in frame recovery mode
        """
        threading.Thread.__init__(self)
        self.rqCore = rqCore
        self.docker_agent = rqCore.docker_agent
        self.frameId = runFrame.frame_id
        self.runFrame = runFrame
        self.startTime = 0
        self.endTime = 0
        self.frameInfo = frameInfo
        self._tempLocations = []
        self.rqlog = None
        self.recovery_mode = recovery_mode

    def __createEnvVariables(self):
        """Define the environmental variables for the frame"""
        # If linux specific, they need to move into self.runLinux()
        # pylint: disable=attribute-defined-outside-init
        self.frameEnv = {}
        self.frameEnv["PATH"] = self.rqCore.machine.getPathEnv()
        self.frameEnv["TERM"] = "unknown"
        self.frameEnv["TZ"] = self.rqCore.machine.getTimezone()
        self.frameEnv["USER"] = self.runFrame.user_name
        self.frameEnv["LOGNAME"] = self.runFrame.user_name
        self.frameEnv["mcp"] = "1"
        self.frameEnv["show"] = self.runFrame.show
        self.frameEnv["shot"] = self.runFrame.shot
        self.frameEnv["jobid"] = self.runFrame.job_name
        self.frameEnv["jobhost"] = self.rqCore.machine.getHostname()
        self.frameEnv["frame"] = self.runFrame.frame_name
        self.frameEnv["zframe"] = self.runFrame.frame_name
        self.frameEnv["logfile"] = self.runFrame.log_file
        self.frameEnv["maxframetime"] = "0"
        self.frameEnv["minspace"] = "200"
        self.frameEnv["CUE3"] = "True"
        self.frameEnv["CUE_GPU_MEMORY"] = str(self.rqCore.machine.getGpuMemoryFree())
        self.frameEnv["SP_NOMYCSHRC"] = "1"

        if rqd.rqconstants.RQD_CUSTOM_HOME_PREFIX:
            self.frameEnv["HOME"] = "%s/%s" % (
                rqd.rqconstants.RQD_CUSTOM_HOME_PREFIX,
                self.runFrame.user_name)

        if rqd.rqconstants.RQD_CUSTOM_MAIL_PREFIX:
            self.frameEnv["MAIL"] = "%s/%s" % (
                rqd.rqconstants.RQD_CUSTOM_MAIL_PREFIX,
                self.runFrame.user_name)

        if platform.system() == "Windows":
            for variable in ["SYSTEMROOT", "APPDATA", "TMP", "COMMONPROGRAMFILES", "SYSTEMDRIVE"]:
                if variable in os.environ:
                    self.frameEnv[variable] = os.environ[variable]
        for variable in rqd.rqconstants.RQD_HOST_ENV_VARS:
            # Fallback to empty string, easy to spot what is missing in the log
            self.frameEnv[variable] = os.environ.get(variable, '')


        if platform.system() == "Windows":
            for variable in ["SYSTEMROOT", "APPDATA", "TMP", "COMMONPROGRAMFILES", "SYSTEMDRIVE"]:
                if variable in os.environ:
                    self.frameEnv[variable] = os.environ[variable]
        if rqd.rqconstants.RQD_HOST_ENV_VARS:
            for variable in rqd.rqconstants.RQD_HOST_ENV_VARS:
                # Fallback to empty string, easy to spot what is missing in the log
                self.frameEnv[variable] = os.environ.get(variable, '')
        elif rqd.rqconstants.RQD_USE_ALL_HOST_ENV_VARS:
            # Add host environment variables
            for key, value in os.environ.items():
                # Merge frame PATH with host PATH
                if "PATH" == key and key in self.frameEnv:
                    self.frameEnv[key] += os.pathsep + value
                else:
                    self.frameEnv[key] = value
        for key, value in self.runFrame.environment.items():
            if key == 'PATH':
                self.frameEnv[key] += os.pathsep + value
            else:
                self.frameEnv[key] = value

        # Add threads to use all assigned hyper-threading cores
        if 'CPU_LIST' in self.runFrame.attributes and 'CUE_THREADS' in self.frameEnv:
            self.frameEnv['CUE_THREADS'] = str(max(
                int(self.frameEnv['CUE_THREADS']),
                len(self.runFrame.attributes['CPU_LIST'].split(','))))
            if self.rqCore.machine.getHyperthreadingMultiplier() > 1:
                self.frameEnv['CUE_HT'] = "True"
            else:
                self.frameEnv['CUE_HT'] = "False"

        # Add GPU's to use all assigned GPU cores
        if 'GPU_LIST' in self.runFrame.attributes:
            self.frameEnv['CUE_GPU_CORES'] = self.runFrame.attributes['GPU_LIST']

    # pylint: disable=inconsistent-return-statements
    def _createCommandFile(self, command):
        """Creates a file that subprocess. Popen then executes.
        @type  command: string
        @param command: The command specified in the runFrame request
        @rtype:  string
        @return: Command file location"""
        commandFile = ""
        try:
            if platform.system() == "Windows":
                rqd_tmp_dir = os.path.join(tempfile.gettempdir(), 'rqd')
                try:
                    os.mkdir(rqd_tmp_dir)
                except OSError:
                    pass  # okay, already exists

                # Windows Batch needs some characters escaped:
                command = command.replace('%', '%%')
                for char in '^&<>|':
                    command = command.replace(char, '^' + char)

                commandFile = os.path.join(
                    rqd_tmp_dir,
                    'cmd-%s-%s.bat' % (self.runFrame.frame_id, time.time()))
            else:
                commandFile = os.path.join(tempfile.gettempdir(),
                                           'rqd-cmd-%s-%s' % (self.runFrame.frame_id, time.time()))
            with open(commandFile, "w", encoding='utf-8') as rqexe:
                self._tempLocations.append(commandFile)
                rqexe.write(command)
                rqexe.close()
            os.chmod(commandFile, 0o777)
            return commandFile
        # pylint: disable=broad-except
        except Exception as e:
            log.critical(
                "Unable to make command file: %s due to %s at %s",
                commandFile, e, traceback.extract_tb(sys.exc_info()[2]))
            raise e

    def __writeHeader(self):
        """Writes the frame's log header"""

        self.startTime = time.time()

        try:
            print("="*59, file=self.rqlog)
            print("RenderQ JobSpec      %s" % time.ctime(self.startTime), "\n", file=self.rqlog)
            print("proxy                rqd.rqnetwork.RunningFrame/%s -t:tcp -h %s -p 10021" % (
                self.runFrame.frame_id,
                self.rqCore.machine.getHostname()), file=self.rqlog)
            print("%-21s%s" % ("command", self.runFrame.command), file=self.rqlog)
            print("%-21s%s" % ("uid", self.runFrame.uid), file=self.rqlog)
            print("%-21s%s" % ("gid", self.runFrame.gid), file=self.rqlog)
            print("%-21s%s" % ("logDestination",
                                              self.runFrame.log_dir_file), file=self.rqlog)
            print("%-21s%s" % ("cwd", self.runFrame.frame_temp_dir), file=self.rqlog)
            print("%-21s%s" % ("renderHost",
                                              self.rqCore.machine.getHostname()), file=self.rqlog)
            print("%-21s%s" % ("jobId", self.runFrame.job_id), file=self.rqlog)
            print("%-21s%s" % ("frameId", self.runFrame.frame_id), file=self.rqlog)
            for env in sorted(self.frameEnv):
                print("%-21s%s=%s" % ("env", env, self.frameEnv[env]), file=self.rqlog)
            print("="*59, file=self.rqlog)

            if 'CPU_LIST' in self.runFrame.attributes:
                print('Hyper-threading enabled', file=self.rqlog)

        # pylint: disable=broad-except
        except Exception as e:
            log.critical(
                "Unable to write header to rqlog: %s due to %s at %s",
                self.runFrame.log_dir_file, e, traceback.extract_tb(sys.exc_info()[2]))

    def __writeFooter(self):
        """Writes frame's log footer"""

        self.endTime = time.time()
        self.frameInfo.runTime = int(self.endTime - self.startTime)
        try:
            print("", file=self.rqlog)
            print("="*59, file=self.rqlog)
            print("RenderQ Job Complete\n", file=self.rqlog)
            print("%-20s%s" % ("exitStatus", self.frameInfo.exitStatus), file=self.rqlog)
            print("%-20s%s" % ("exitSignal", self.frameInfo.exitSignal), file=self.rqlog)
            if self.frameInfo.killMessage:
                print("%-20s%s" % ("killMessage", self.frameInfo.killMessage), file=self.rqlog)
            print("%-20s%s" % ("startTime",
                                         time.ctime(self.startTime)), file=self.rqlog)
            print("%-20s%s" % ("endTime",
                                         time.ctime(self.endTime)), file=self.rqlog)
            print("%-20s%s" % ("maxrss", self.frameInfo.maxRss), file=self.rqlog)
            print("%-20s%s" % ("maxUsedGpuMemory",
                                         self.frameInfo.maxUsedGpuMemory), file=self.rqlog)
            print("%-20s%s" % ("utime", self.frameInfo.utime), file=self.rqlog)
            print("%-20s%s" % ("stime", self.frameInfo.stime), file=self.rqlog)
            print("%-20s%s" % ("renderhost", self.rqCore.machine.getHostname()), file=self.rqlog)

            print("%-20s%s" % ("maxrss (KB)", self.frameInfo.maxRss), file=self.rqlog)
            for child in sorted(self.frameInfo.childrenProcs.items(),
                                key=lambda item: item[1]['start_time']):
                print("\t%-20s%s" % (child[1]['name'], child[1]['rss']), file=self.rqlog)
                print("\t%-20s%s" % ("start_time",
                                      datetime.timedelta(seconds=child[1]["start_time"])),
                                      file=self.rqlog)
                print("\t%-20s%s" % ("cmdline", " ".join(child[1]["cmd_line"])), file=self.rqlog)

            print("="*59, file=self.rqlog)

        # pylint: disable=broad-except
        except Exception as e:
            log.critical(
                "Unable to write footer: %s due to %s at %s",
                self.runFrame.log_dir_file, e, traceback.extract_tb(sys.exc_info()[2]))

    def __cleanup(self):
        """Cleans up temporary files"""
        rqd.rqutil.permissionsHigh()
        try:
            for location in self._tempLocations:
                if os.path.isfile(location):
                    try:
                        os.remove(location)
                    # pylint: disable=broad-except
                    except Exception as e:
                        log.warning(
                            "Unable to delete file: %s due to %s at %s",
                            location, e, traceback.extract_tb(sys.exc_info()[2]))
        finally:
            rqd.rqutil.permissionsLow()

        # Close log file
        try:
            self.rqlog.close()
        # pylint: disable=broad-except
        except Exception as e:
            log.warning(
                "Unable to close file: %s due to %s at %s",
                self.runFrame.log_file, e, traceback.extract_tb(sys.exc_info()[2]))

    def runLinux(self):
        """The steps required to handle a frame under linux"""
        frameInfo = self.frameInfo
        runFrame = self.runFrame

        self.__createEnvVariables()
        self.__writeHeader()

        tempStatFile = "%srqd-stat-%s-%s" % (self.rqCore.machine.getTempPath(),
                                             frameInfo.frameId,
                                             time.time())
        self._tempLocations.append(tempStatFile)
        tempCommand = []
        if self.rqCore.machine.isDesktop():
            tempCommand += ["/bin/nice"]
        tempCommand += ["/usr/bin/time", "-p", "-o", tempStatFile]

        if 'CPU_LIST' in runFrame.attributes:
            tempCommand += ['taskset', '-c', runFrame.attributes['CPU_LIST']]

        rqd.rqutil.permissionsHigh()
        try:
            if rqd.rqconstants.RQD_BECOME_JOB_USER:
                tempCommand += ["/bin/su", runFrame.user_name, rqd.rqconstants.SU_ARGUMENT,
                                '"' + self._createCommandFile(runFrame.command) + '"']
            else:
                tempCommand += [self._createCommandFile(runFrame.command)]

            # pylint: disable=subprocess-popen-preexec-fn,consider-using-with
            frameInfo.forkedCommand = subprocess.Popen(tempCommand,
                                                       env=self.frameEnv,
                                                       cwd=self.rqCore.machine.getTempPath(),
                                                       stdin=subprocess.PIPE,
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE,
                                                       close_fds=True,
                                                       preexec_fn=os.setsid)
        finally:
            rqd.rqutil.permissionsLow()

        frameInfo.pid = runFrame.pid = frameInfo.forkedCommand.pid

        if not self.rqCore.updateRssThread.is_alive():
            self.rqCore.updateRssThread = threading.Timer(rqd.rqconstants.RSS_UPDATE_INTERVAL,
                                                          self.rqCore.updateRss)
            self.rqCore.updateRssThread.start()

        poller = select.poll()
        poller.register(frameInfo.forkedCommand.stdout, select.POLLIN)
        poller.register(frameInfo.forkedCommand.stderr, select.POLLIN)
        while True:
            for fd, event in poller.poll():
                if event & select.POLLIN:
                    if fd == frameInfo.forkedCommand.stdout.fileno():
                        line = frameInfo.forkedCommand.stdout.readline()
                    elif fd == frameInfo.forkedCommand.stderr.fileno():
                        line = frameInfo.forkedCommand.stderr.readline()
                    else:
                        continue
                    if not line:
                        break
                    self.rqlog.write(line, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
            if frameInfo.forkedCommand.poll() is not None:
                break

        returncode = frameInfo.forkedCommand.wait()

        # Find exitStatus and exitSignal
        if returncode < 0:
            # Exited with a signal
            frameInfo.exitStatus = 1
            frameInfo.exitSignal = -returncode
        else:
            frameInfo.exitStatus = returncode
            frameInfo.exitSignal = 0

        try:
            with open(tempStatFile, "r", encoding='utf-8') as statFile:
                frameInfo.realtime = statFile.readline().split()[1]
                frameInfo.utime = statFile.readline().split()[1]
                frameInfo.stime = statFile.readline().split()[1]
                statFile.close()
        # pylint: disable=broad-except
        except Exception:
            pass  # This happens when frames are killed

        self.__writeFooter()
        self.__cleanup()

    def runDocker(self):
        """The steps required to handle a frame under a docker container"""
        # pylint: disable=import-outside-toplevel
        # pylint: disable=import-error
        from docker.errors import APIError
        from rqd.rqdocker import InvalidFrameOsError

        frameInfo = self.frameInfo
        runFrame = self.runFrame

        # Ensure Nullable attributes have been initialized
        if not self.rqlog:
            raise RuntimeError("Invalid state. rqlog has not been initialized")
        if not self.docker_agent:
            raise RuntimeError("Invalid state: docker_agent must have been initialized.")

        self.__createEnvVariables()
        self.__writeHeader()

        tempStatFile = "%srqd-stat-%s-%s" % (self.rqCore.machine.getTempPath(),
                                             frameInfo.frameId,
                                             time.time())
        self._tempLocations.append(tempStatFile)

        # Prevent frame from attempting to run as ROOT
        gid = runFrame.gid
        if runFrame.gid <= 0:
            gid = rqd.rqconstants.LAUNCH_FRAME_USER_GID

        # Prevent invalid uids, fallback to daemon uid
        uid = runFrame.uid
        if uid < rqd.rqconstants.RQD_MIN_UID or uid > rqd.rqconstants.RQD_MAX_UID:
            msg = "Frame launched with an invalid uid=%s. Falling back to daemon uid" % runFrame.uid
            self.rqlog.write(msg, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
            uid = rqd.rqconstants.RQD_DAEMON_UID

        # Never give frame ROOT permissions
        if uid == 0 or gid == 0:
            msg = "Frame %s cannot run as ROOT" % frameInfo.frameId
            self.rqlog.write(msg, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
            raise RuntimeError(msg)

        # Thread affinity
        tasksetCmd = ""
        if runFrame.attributes['CPU_LIST']:
            tasksetCmd = "taskset -c %s" % runFrame.attributes['CPU_LIST']

        # Set process to use nice if running on a desktop
        nice = ""
        if self.rqCore.machine.isDesktop():
            nice = "/bin/nice"

        # A temporary password for the user created inside of the frame container.
        # This user is only valid inside the container, meaning a leakage would only
        # be harmful if the perpetrator gains access to run docker commands.
        tempPassword = str(uuid.uuid4())
        # Command wrapper
        command = r"""#!/bin/sh
useradd -u %s -g %s -p %s %s >& /dev/null || true;
exec su -s %s %s -c "echo \$$; %s /usr/bin/time -p -o %s %s %s"
""" % (
            uid,
            gid,
            tempPassword,
            runFrame.user_name,
            self.docker_agent.docker_shell_path,
            runFrame.user_name,
            nice,
            tempStatFile,
            tasksetCmd,
            runFrame.command.replace('"', r"""\"""")
        )

        # Log entrypoint on frame log to simplify replaying frames
        self.rqlog.write("DOCKER_ENTRYPOINT = %s" %
            # Mask password
            command.replace(tempPassword, "[password]").replace(";", "\n"),
            prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

        if self.docker_agent.gpu_mode:
            self.rqlog.write("GPU_MODE activated")

        # Handle memory limits. Cuebot users KB docker uses Bytes.
        # Docker min requirement is 6MB, if request is bellow limit, give the frame a reasonable
        # amount of memory.
        soft_memory_limit = runFrame.soft_memory_limit * 1000
        if soft_memory_limit <= 6291456:
            logging.warning("Frame requested %s bytes of soft_memory_limit, which is lower than "
                            "minimum required. Running with 1MB", soft_memory_limit)
            soft_memory_limit = "1GB"
        hard_memory_limit = runFrame.hard_memory_limit * 1000
        if hard_memory_limit <= 6291456:
            logging.warning("Frame requested %s bytes of hard_memory_limit, which is lower than "
                            "minimum required. Running with 2MB", hard_memory_limit)
            hard_memory_limit = "2GB"

        # Write command to a file on the job tmpdir to simplify replaying a frame
        command = self._createCommandFile(command)
        container = None
        docker_client = None
        container_id = "00000000"
        frameInfo.pid = -1
        try:
            log_stream = None
            docker_client, container = self.docker_agent.runContainer(
                image_key=runFrame.os,
                environment=self.frameEnv,
                working_dir=self.rqCore.machine.getTempPath(),
                hostname=self.frameEnv["jobhost"],
                mem_reservation=soft_memory_limit,
                mem_limit=hard_memory_limit,
                entrypoint=command)

            log_stream = container.logs(stream=True)

            if not container or not log_stream:
                raise RuntimeError("Container failed to start for %s.%s(%s)" % (
                    runFrame.job_name,
                    runFrame.frame_name,
                    frameInfo.frameId))

            # Try to get the cmd pid from top if the container is still running.
            # If that fails the pid can be acquired from the first line of the log
            try:
                # Docker SDK type hint states that `top` returns an str
                # when in reality it returns a Dict {"Processes": [[]], "Columns": [[]]}
                container_top: dict = container.top()
                frameInfo.pid = runFrame.pid = int(container_top["Processes"][0][1])
            except (APIError, TypeError):
                for first_line in log_stream:
                    frameInfo.pid = int(first_line)
                    break

            # Log frame start info
            msg = "Container %s started for %s.%s(%s) with pid %s" % (
                container.short_id,
                runFrame.job_name,
                runFrame.frame_name,
                frameInfo.frameId,
                frameInfo.pid)

            log.info(msg)
            self.rqlog.write(msg, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

            # Ping rss thread on rqCore
            if self.rqCore.updateRssThread and not self.rqCore.updateRssThread.is_alive():
                self.rqCore.updateRssThread = threading.Timer(rqd.rqconstants.RSS_UPDATE_INTERVAL,
                                                            self.rqCore.updateRss)
                self.rqCore.updateRssThread.start()

            # Store container id in case this frame needs to be restored from the backup
            runFrame.attributes["container_id"] = container.short_id
            # Atatch to the job and follow the logs
            for line in log_stream:
                self.rqlog.write(line, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

            output = container.wait()
            returncode = output["StatusCode"]
        except StopIteration:
            # This exception can happen when a container is interrupted
            # If frame pid is set it means the container has started successfully
            if frameInfo.pid and container:
                output = container.wait()
                returncode = output["StatusCode"]
            else:
                returncode = -1
                container_id = container.short_id if container else -1
                msg = "Failed to read frame container logs on %s for %s.%s(%s)" % (
                    container_id,
                    runFrame.job_name,
                    runFrame.frame_name,
                    frameInfo.frameId)
                logging.error(msg)
                self.rqlog.write(msg, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
        except InvalidFrameOsError as e:
            # Frame container didn't get created
            returncode = rqd.rqconstants.EXITSTATUS_FOR_FAILED_LAUNCH
            self.__writeHeader()
            self.rqlog.write(str(e), prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
        # pylint: disable=broad-except
        except Exception as e:
            returncode = rqd.rqconstants.EXITSTATUS_FOR_FAILED_LAUNCH
            msg = "Failed to launch frame container"
            logging.exception(msg)
            self.rqlog.write("%s - %s" % (msg, e),
                                prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
        finally:
            # Clear up container after if finishes
            if container:
                container_id = container.short_id
                container.remove()
            if docker_client:
                docker_client.close()

        # Find exitStatus and exitSignal
        if returncode < 0:
            # Exited with a signal
            frameInfo.exitStatus = 1
            frameInfo.exitSignal = -returncode
        else:
            frameInfo.exitStatus = returncode
            frameInfo.exitSignal = 0

        # Log frame start info
        log.warning("Frame %s.%s(%s) with pid %s finished on container %s with exitStatus %s %s ",
            runFrame.job_name,
            runFrame.frame_name,
            frameInfo.frameId,
            frameInfo.pid,
            container_id,
            frameInfo.exitStatus,
            "" if frameInfo.exitStatus == 0 else " - " + runFrame.log_dir_file)

        try:
            with open(tempStatFile, "r", encoding='utf-8') as statFile:
                frameInfo.realtime = statFile.readline().split()[1]
                frameInfo.utime = statFile.readline().split()[1]
                frameInfo.stime = statFile.readline().split()[1]
                statFile.close()
        # pylint: disable=broad-except
        except Exception:
            pass  # This happens when frames are killed

        self.__writeFooter()
        self.__cleanup()

    def runWindows(self):
        """The steps required to handle a frame under windows"""
        frameInfo = self.frameInfo
        runFrame = self.runFrame

        self.__createEnvVariables()
        self.__writeHeader()

        try:
            runFrame.command = runFrame.command.replace('%{frame}', self.frameEnv['CUE_IFRAME'])
            tempCommand = [self._createCommandFile(runFrame.command)]

            # pylint: disable=consider-using-with
            frameInfo.forkedCommand = subprocess.Popen(tempCommand,
                                                       env=self.frameEnv,
                                                       stdin=subprocess.PIPE,
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.STDOUT)
        # pylint: disable=broad-except
        except Exception:
            log.critical(
                "Failed subprocess.Popen: Due to: \n%s",
                ''.join(traceback.format_exception(*sys.exc_info())))

        frameInfo.pid = runFrame.pid = frameInfo.forkedCommand.pid

        if not self.rqCore.updateRssThread.is_alive():
            self.rqCore.updateRssThread = threading.Timer(rqd.rqconstants.RSS_UPDATE_INTERVAL,
                                                          self.rqCore.updateRss)
            self.rqCore.updateRssThread.start()

        while True:
            output = frameInfo.forkedCommand.stdout.readline()
            if not output and frameInfo.forkedCommand.poll() is not None:
                break
            if output:
                self.rqlog.write(output, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

        frameInfo.forkedCommand.wait()

        # Find exitStatus and exitSignal
        returncode = frameInfo.forkedCommand.returncode
        if returncode < INT32_MIN:
            returncode = 303
        if returncode > INT32_MAX:
            returncode = 304
        frameInfo.exitStatus = returncode
        frameInfo.exitSignal = returncode

        frameInfo.realtime = 0
        frameInfo.utime = 0
        frameInfo.stime = 0

        self.__writeFooter()
        self.__cleanup()

    def runDarwin(self):
        """The steps required to handle a frame under mac"""
        frameInfo = self.frameInfo

        self.__createEnvVariables()
        self.__writeHeader()

        rqd.rqutil.permissionsHigh()
        try:
            tempCommand = ["/usr/bin/su", frameInfo.runFrame.user_name, "-c", '"' +
                           self._createCommandFile(frameInfo.runFrame.command) + '"']

            # pylint: disable=subprocess-popen-preexec-fn,consider-using-with
            frameInfo.forkedCommand = subprocess.Popen(tempCommand,
                                                       env=self.frameEnv,
                                                       cwd=self.rqCore.machine.getTempPath(),
                                                       stdin=subprocess.PIPE,
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.STDOUT,
                                                       preexec_fn=os.setsid)
        finally:
            rqd.rqutil.permissionsLow()

        frameInfo.pid = frameInfo.forkedCommand.pid

        if not self.rqCore.updateRssThread.is_alive():
            self.rqCore.updateRssThread = threading.Timer(rqd.rqconstants.RSS_UPDATE_INTERVAL,
                                                          self.rqCore.updateRss)
            self.rqCore.updateRssThread.start()

        while True:
            output = frameInfo.forkedCommand.stdout.readline()
            if not output and frameInfo.forkedCommand.poll() is not None:
                break
            if output:
                self.rqlog.write(output, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

        frameInfo.forkedCommand.wait()

        # Find exitStatus and exitSignal
        returncode = frameInfo.forkedCommand.returncode
        if os.WIFEXITED(returncode):
            frameInfo.exitStatus = os.WEXITSTATUS(returncode)
        else:
            frameInfo.exitStatus = 1
        if os.WIFSIGNALED(returncode):
            frameInfo.exitSignal = os.WTERMSIG(returncode)

        self.__writeFooter()
        self.__cleanup()

    def setup(self):
        """Setup for running or recovering a frame"""
        runFrame = self.runFrame
        run_on_docker = self.rqCore.docker_agent is not None

        runFrame.job_temp_dir = os.path.join(self.rqCore.machine.getTempPath(),
                                                runFrame.job_name)
        runFrame.frame_temp_dir = os.path.join(runFrame.job_temp_dir,
                                                runFrame.frame_name)
        runFrame.log_file = "%s.%s.rqlog" % (runFrame.job_name,
                                                runFrame.frame_name)
        runFrame.log_dir_file = os.path.join(runFrame.log_dir, runFrame.log_file)

        # Ensure permissions return to Low after this block
        try:
            if rqd.rqconstants.RQD_CREATE_USER_IF_NOT_EXISTS and runFrame.HasField("uid"):
                rqd.rqutil.checkAndCreateUser(runFrame.user_name,
                                                runFrame.uid,
                                                runFrame.gid)
                if not run_on_docker:
                    # Do everything as launching user:
                    runFrame.gid = rqd.rqconstants.LAUNCH_FRAME_USER_GID
                    rqd.rqutil.permissionsUser(runFrame.uid, runFrame.gid)

            # Setup frame logging
            if self.runFrame.loki_url:
                log.info("Logging with Loki")
                self.rqlog = rqd.rqlogging.LokiLogger(self.runFrame.loki_url, runFrame)
            else:
                self.rqlog = rqd.rqlogging.RqdLogger(runFrame.log_dir_file)
            self.rqlog.waitForFile()
        # pylint: disable=broad-except
        except Exception as e:
            err = "Unable to write to %s due to %s" % (runFrame.log_dir_file, e)
            raise RuntimeError(err)
        finally:
            rqd.rqutil.permissionsLow()


    def runUnknown(self):
        """The steps required to handle a frame under an unknown OS."""

    def run(self):
        """Thread initialization"""
        if self.recovery_mode:
            self.runRecovery()
            return

        log.info("Monitor frame started for frameId=%s", self.frameId)

        runFrame = self.runFrame
        run_on_docker = self.rqCore.docker_agent is not None

        # pylint: disable=too-many-nested-blocks
        try:
            self.setup()
            # Store frame in cache and register servant
            self.rqCore.storeFrame(runFrame.frame_id, self.frameInfo)

            if run_on_docker:
                self.runDocker()
            elif platform.system() == "Linux":
                self.runLinux()
            elif platform.system() == "Windows":
                self.runWindows()
            elif platform.system() == "Darwin":
                self.runDarwin()
            else:
                self.runUnknown()

        # pylint: disable=broad-except
        except Exception:
            log.critical(
                "Failed launchFrame: For %s due to: \n%s",
                runFrame.frame_id, ''.join(traceback.format_exception(*sys.exc_info())))
            # Notifies the cuebot that there was an error launching
            self.frameInfo.exitStatus = rqd.rqconstants.EXITSTATUS_FOR_FAILED_LAUNCH
            # Delay keeps the cuebot from spamming failing booking requests
            time.sleep(10)
        finally:
            self.postFrameAction()

    def postFrameAction(self):
        """Action to be executed after a frame completes its execution"""
        self.rqCore.releaseCores(self.runFrame.num_cores,
            self.runFrame.attributes.get('CPU_LIST'),
            self.runFrame.attributes.get('GPU_LIST')
                if 'GPU_LIST' in self.runFrame.attributes else None)

        self.rqCore.deleteFrame(self.runFrame.frame_id)

        self.rqCore.sendFrameCompleteReport(self.frameInfo)
        time_till_next = (
                (self.rqCore.intervalStartTime + self.rqCore.intervalSleepTime) - time.time())
        if time_till_next > (2 * rqd.rqconstants.RQD_MIN_PING_INTERVAL_SEC):
            self.rqCore.onIntervalThread.cancel()
            self.rqCore.onInterval(rqd.rqconstants.RQD_MIN_PING_INTERVAL_SEC)

        log.info("Monitor frame ended for frameId=%s",
                    self.runFrame.frame_id)

    def recoverDocker(self):
        """The steps required to handle a frame under a docker container"""
        frameInfo = self.frameInfo
        runFrame = self.runFrame
        container = None

        # Ensure Nullable attributes have been initialized
        if not self.rqlog:
            raise RuntimeError("Invalid state. rqlog has not been initialized")
        if not self.rqCore.docker_agent:
            raise RuntimeError("Invalid state: docker_agent must have been initialized.")
        if not runFrame.attributes.get("container_id"):
            raise RuntimeError("Invalid state: recovered frame does't contain a container id")
        container_id = runFrame.attributes.get("container_id")

        docker_client = self.rqCore.docker_agent.new_client()
        # The recovered frame will stream back the logs into a new file,
        # therefore, write a new header
        self.__createEnvVariables()
        self.__writeHeader()

        tempStatFile = "%srqd-stat-%s-%s" % (self.rqCore.machine.getTempPath(),
                                             frameInfo.frameId,
                                             time.time())
        self._tempLocations.append(tempStatFile)

        try:
            log_stream = None
            with self.rqCore.docker_agent.docker_lock:
                container = docker_client.containers.get(container_id)
            log_stream = container.logs(stream=True)

            if not container or not log_stream:
                raise RuntimeError("Failed to recover container for %s.%s(%s)" % (
                    runFrame.job_name,
                    runFrame.frame_name,
                    frameInfo.frameId))

            # Log frame start info
            msg = "Container %s recovered for %s.%s(%s) with pid %s" % (
                container.short_id,
                runFrame.job_name,
                runFrame.frame_name,
                frameInfo.frameId,
                frameInfo.pid)

            log.info(msg)
            self.rqlog.write(msg, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

            # Ping rss thread on rqCore
            if self.rqCore.updateRssThread and not self.rqCore.updateRssThread.is_alive():
                self.rqCore.updateRssThread = threading.Timer(rqd.rqconstants.RSS_UPDATE_INTERVAL,
                                                            self.rqCore.updateRss)
                self.rqCore.updateRssThread.start()

            # Attach to the job and follow the logs
            for line in log_stream:
                self.rqlog.write(line, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)

            output = container.wait()
            returncode = output["StatusCode"]
        except StopIteration:
            # This exception can happen when a container is interrupted
            # If frame pid is set it means the container has started successfully
            if frameInfo.pid and container:
                output = container.wait()
                returncode = output["StatusCode"]
            else:
                returncode = -1
                container_id = container.short_id if container else -1
                msg = "Failed to read frame container logs on %s for %s.%s(%s)" % (
                    container_id,
                    runFrame.job_name,
                    runFrame.frame_name,
                    frameInfo.frameId)
                logging.error(msg)
                self.rqlog.write(msg, prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
        # pylint: disable=broad-except
        except Exception as e:
            returncode = -1
            msg = "Failed to recover frame container"
            logging.warning(msg)
            self.rqlog.write("%s - The frame might have finishes during rqd's reinitialization "
                "- %s" % (msg, e),
                prependTimestamp=rqd.rqconstants.RQD_PREPEND_TIMESTAMP)
        finally:
            # Clear up container after if finishes
            if container:
                container_id = container.short_id
                container.remove()
            docker_client.close()

        if container:
            # Find exitStatus and exitSignal
            if returncode < 0:
                # Exited with a signal
                frameInfo.exitStatus = 1
                frameInfo.exitSignal = -returncode
            else:
                frameInfo.exitStatus = returncode
                frameInfo.exitSignal = 0

            # Log frame start info
            log.warning(
                "Frame %s.%s(%s) with pid %s finished on container %s with exitStatus %s %s",
                runFrame.job_name,
                runFrame.frame_name,
                frameInfo.frameId,
                frameInfo.pid,
                container_id,
                frameInfo.exitStatus,
                "" if frameInfo.exitStatus == 0 else " - " + runFrame.log_dir_file)

            try:
                with open(tempStatFile, "r", encoding='utf-8') as statFile:
                    frameInfo.realtime = statFile.readline().split()[1]
                    frameInfo.utime = statFile.readline().split()[1]
                    frameInfo.stime = statFile.readline().split()[1]
                    statFile.close()
            # pylint: disable=broad-except
            except Exception:
                pass  # This happens when frames are killed

            self.__writeFooter()
        self.__cleanup()

    def runRecovery(self):
        """Recover a frame that was running before this instance started"""
        if not self.recovery_mode:
            return

        log.info("Monitor recovered frame started for frameId=%s", self.frameId)

        runFrame = self.runFrame
        run_on_docker = self.rqCore.docker_agent is not None

        # pylint: disable=too-many-nested-blocks
        try:
            self.setup()
            # Store frame in cache and register servant
            self.rqCore.storeFrame(runFrame.frame_id, self.frameInfo)

            if run_on_docker:
                self.recoverDocker()
            elif platform.system() == "Linux":
                # TODO
                pass
            elif platform.system() == "Windows":
                # TODO
                pass
            elif platform.system() == "Darwin":
                # TODO
                pass
            else:
                self.runUnknown()

        # pylint: disable=broad-except
        except Exception:
            log.critical(
                "Failed launchFrame: For %s due to: \n%s",
                runFrame.frame_id, ''.join(traceback.format_exception(*sys.exc_info())))
            # Notifies the cuebot that there was an error launching
            self.frameInfo.exitStatus = rqd.rqconstants.EXITSTATUS_FOR_FAILED_LAUNCH
            # Delay keeps the cuebot from spamming failing booking requests
            time.sleep(10)
        finally:
            self.postFrameAction()
