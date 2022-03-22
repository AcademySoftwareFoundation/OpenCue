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


"""Nimby allows a desktop to be used as a render host when not used."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from abc import ABCMeta, abstractmethod
import os
import select
import time
import signal
import threading
import logging

import rqd.rqconstants
import rqd.rqutil


log = logging.getLogger(__name__)

# compatible with Python 2 and 3:
ABC = ABCMeta('ABC', (object,), {'__slots__': ()})

class NimbyFactory(object):
    @staticmethod
    def getNimby(rqCore):
        if rqd.rqconstants.USE_NIMBY_PYNPUT:
            return NimbyPynput(rqCore)
        else:
            return NimbySelect(rqCore)


class Nimby(threading.Thread, ABC):
    """Nimby == Not In My Back Yard.
       If enabled, nimby will lock and kill all frames running on the host if
       keyboard or mouse activity is detected. If sufficient idle time has
       passed, defined in the Constants class, nimby will then unlock the host
       and make it available for rendering."""

    def __init__(self, rqCore):
        """Nimby initialization
        @type    rqCore: RqCore
        @param   rqCore: Main RQD Object"""
        threading.Thread.__init__(self)

        self.rqCore = rqCore
        self.locked = False
        self.active = False
        log.warn("Locked state :%s", self.locked)
        log.warn("Active state :%s", self.active)

        self.fileObjList = []
        self.results = [[]]

        self.thread = None

        self.interaction_detected = False

        signal.signal(signal.SIGINT, self.signalHandler)

    def signalHandler(self, sig, frame):
        """If a signal is detected, call .stop()"""
        del sig
        del frame
        self.stop()

    def lockNimby(self):
        """Activates the nimby lock, calls lockNimby() in rqcore"""
        if self.active and not self.locked:
            self.locked = True
            log.info("Locked nimby")
            self.rqCore.onNimbyLock()

    def unlockNimby(self, asOf=None):
        """Deactivates the nimby lock, calls unlockNimby() in rqcore
        @param asOf: Time when idle state began, if known."""
        if self.locked:
            self.locked = False
            log.info("Unlocked nimby")
            self.rqCore.onNimbyUnlock(asOf=asOf)

    def run(self):
        """Starts the Nimby thread"""
        log.warn("Nimby Run")
        self.active = True
        self.locked = True
        self.startListener()
        self.unlockedIdle()

        rqd.rqutil.permissionsHigh()
        try:
            for device in os.listdir("/dev/input/"):
                if device.startswith("event") or device.startswith("mice"):
                    try:
                        self.fileObjList.append(open("/dev/input/%s" % device, "rb"))
                    except IOError as e:
                        # Bad device found
                        log.warning("IOError: Failed to open %s, %s", "/dev/input/%s" % device, e)
        finally:
            rqd.rqutil.permissionsLow()

    def stop(self):
        """Stops the Nimby thread"""
        log.warn("Stop Nimby")
        if self.thread:
            self.thread.cancel()
        self.active = False
        self.stopListener()
        self.unlockNimby()

    @abstractmethod
    def startListener(self):
        pass

    @abstractmethod
    def stopListener(self):
        pass

    @abstractmethod
    def lockedInUse(self):
        pass

    @abstractmethod
    def lockedIdle(self):
        pass

    @abstractmethod
    def unlockedIdle(self):
        pass


class NimbySelect(Nimby):
    def startListener(self):
        pass

    def stopListener(self):
        self.closeEvents()

    def lockedInUse(self):
        """Nimby State: Machine is in use, host is locked,
                        waiting for sufficient idle time"""
        log.warn("lockedInUse")
        self.openEvents()
        try:
            self.results = select.select(self.fileObjList, [], [], 5)
        # pylint: disable=broad-except
        except Exception as e:
            log.warn(e)
        if self.active and self.results[0] == []:
            self.lockedIdle()
        elif self.active:
            self.closeEvents()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def unlockedIdle(self):
        """Nimby State: Machine is idle, host is unlocked,
                        waiting for user activity"""
        log.warn("UnlockedIdle Nimby")
        while self.active and \
                self.results[0] == [] and \
                self.rqCore.machine.isNimbySafeToRunJobs():
            try:
                self.openEvents()
                self.results = select.select(self.fileObjList, [], [], 5)
            # pylint: disable=broad-except
            except Exception:
                pass
            if not self.rqCore.machine.isNimbySafeToRunJobs():
                log.warning("memory threshold has been exceeded, locking nimby")
                self.active = True

        if self.active:
            log.warn("Is active, locking Nimby")
            self.closeEvents()
            self.lockNimby()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def lockedIdle(self):
        """Nimby State: Machine is idle,
                        waiting for sufficient idle time to unlock"""
        log.warn("lockedIdle")
        self.openEvents()
        waitStartTime = time.time()
        try:
            self.results = select.select(self.fileObjList, [], [],
                                         rqd.rqconstants.MINIMUM_IDLE)
        # pylint: disable=broad-except
        except Exception as e:
            log.warn(e)
        if self.active and self.results[0] == [] and \
                self.rqCore.machine.isNimbySafeToUnlock():
            self.closeEvents()
            self.unlockNimby(asOf=waitStartTime)
            self.unlockedIdle()
        elif self.active:
            self.closeEvents()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def openEvents(self):
        """Opens the /dev/input/event* files so nimby can monitor them"""
        log.warn("openEvents")
        self.closeEvents()

        rqd.rqutil.permissionsHigh()
        try:
            for device in os.listdir("/dev/input/"):
                if device.startswith("event") or device.startswith("mice"):
                    try:
                        self.fileObjList.append(open("/dev/input/%s" % device, "rb"))
                    except IOError as e:
                        # Bad device found
                        log.warning("IOError: Failed to open %s, %s" % ("/dev/input/%s" % device, e))
        finally:
            rqd.rqutil.permissionsLow()

    def closeEvents(self):
        """Closes the /dev/input/event* files"""
        log.warning("closeEvents")
        if self.fileObjList:
            for fileObj in self.fileObjList:
                try:
                    fileObj.close()
                # pylint: disable=broad-except
                except Exception:
                    pass
            self.fileObjList = []

    def isNimbyActive(self):
        """ Check if user is active
        :return: boolean if events are logged and Nimby is active
        """
        return self.active and self.results[0] == []

class NimbyPynput(Nimby):
    def __init__(self, rqCore):
        Nimby.__init__(self, rqCore)

        import pynput
        self.mouse_listener = pynput.mouse.Listener(
            on_move=self.on_interaction,
            on_click=self.on_interaction,
            on_scroll=self.on_interaction)
        self.keyboard_listener = pynput.keyboard.Listener(on_press=self.on_interaction)

    def on_interaction(self, *args):
        self.interaction_detected = True

    def startListener(self):
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stopListener(self):
        self.mouse_listener.stop()
        self.keyboard_listener.stop()

    def lockedInUse(self):
        self.interaction_detected = False

        time.sleep(5)
        if self.active and self.interaction_detected == False:
            self.lockedIdle()
        elif self.active:

            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def unlockedIdle(self):
        log.warn("unlockedIdle")
        while self.active and \
                self.interaction_detected == False and \
                self.rqCore.machine.isNimbySafeToRunJobs():

            time.sleep(5)

            if not self.rqCore.machine.isNimbySafeToRunJobs():
                log.warning("memory threshold has been exceeded, locking nimby")
                self.active = True

        if self.active:
            log.warning("Is active, lock Nimby")
            self.lockNimby()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            log.warn("starting Thread")
            self.thread.start()

    def lockedIdle(self):
        log.warn("lockedIdle")
        waitStartTime = time.time()

        time.sleep(rqd.rqconstants.MINIMUM_IDLE)

        if self.active and self.interaction_detected == False and \
                self.rqCore.machine.isNimbySafeToUnlock():
            log.warn("Start wait time: %s", waitStartTime)
            self.unlockNimby(asOf=waitStartTime)
            self.unlockedIdle()
        elif self.active:

            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def isNimbyActive(self):
        return not self.active and self.interaction_detected
