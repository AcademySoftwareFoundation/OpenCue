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
import platform

import rqd.rqconstants
import rqd.rqutil

log = logging.getLogger(__name__)

if platform.system() == 'Windows':
    pynputIsAvailable = False
    try:
        import pynput
        pynputIsAvailable = True
    except ImportError as e:
        log.error(e)


# compatible with Python 2 and 3:
ABC = ABCMeta('ABC', (object,), {'__slots__': ()})

class NimbyFactory(object):
    """ Factory to handle Linux/Windows platforms """
    @staticmethod
    def getNimby(rqCore):
        """ assign platform dependent Nimby instance """
        nimbyInstance = None
        if rqd.rqconstants.USE_NIMBY_PYNPUT and pynputIsAvailable:
            nimbyInstance = NimbyPynput(rqCore)
        else:
            nimbyInstance = NimbySelect(rqCore)
        return nimbyInstance


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
        log.warning("Locked state :%s", self.locked)
        log.warning("Active state :%s", self.active)

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
        log.warning("Nimby Run")
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
        log.warning("Stop Nimby")
        if self.thread:
            self.thread.cancel()
        self.active = False
        self.stopListener()
        self.unlockNimby()

    @abstractmethod
    def startListener(self):
        """ start listening """

    @abstractmethod
    def stopListener(self):
        """ stop listening """

    @abstractmethod
    def lockedInUse(self):
        """Nimby State: Machine is in use, host is locked,
                        waiting for sufficient idle time"""

    @abstractmethod
    def lockedIdle(self):
        """Nimby State: Machine is idle,
                        waiting for sufficient idle time to unlock"""

    @abstractmethod
    def unlockedIdle(self):
        """Nimby State: Machine is idle, host is unlocked,
                        waiting for user activity"""

    @abstractmethod
    def isNimbyActive(self):
        """ Check if user is active
        :return: boolean if events are logged and Nimby is active
        """


class NimbySelect(Nimby):
    """ Nimby Linux """
    def startListener(self):
        """ start listening """

    def stopListener(self):
        """ stop listening """
        self.closeEvents()

    def lockedInUse(self):
        """Nimby State: Machine is in use, host is locked,
                        waiting for sufficient idle time"""
        log.warning("lockedInUse")
        self.openEvents()
        try:
            self.results = select.select(self.fileObjList, [], [], 5)
        # pylint: disable=broad-except
        except Exception as e:
            log.warning(e)
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
        log.warning("UnlockedIdle Nimby")
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
            log.warning("Is active, locking Nimby")
            self.closeEvents()
            self.lockNimby()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def lockedIdle(self):
        """Nimby State: Machine is idle,
                        waiting for sufficient idle time to unlock"""
        log.warning("lockedIdle")
        self.openEvents()
        waitStartTime = time.time()
        try:
            self.results = select.select(self.fileObjList, [], [],
                                         rqd.rqconstants.MINIMUM_IDLE)
        # pylint: disable=broad-except
        except Exception as e:
            log.warning(e)
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
        log.warning("openEvents")
        self.closeEvents()

        rqd.rqutil.permissionsHigh()
        try:
            for device in os.listdir("/dev/input/"):
                if device.startswith("event") or device.startswith("mice"):
                    try:
                        self.fileObjList.append(open("/dev/input/%s" % device, "rb"))
                    except IOError as e:
                        # Bad device found
                        msg = ('IOError: Failed to open %s, %s'
                                 % ("/dev/input/%s" % device, e))
                        log.warning(msg)
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
    """ Nimby Windows """
    def __init__(self, rqCore):
        Nimby.__init__(self, rqCore)

        self.mouse_listener = pynput.mouse.Listener(
            on_move=self.on_interaction,
            on_click=self.on_interaction,
            on_scroll=self.on_interaction)
        self.keyboard_listener = pynput.keyboard.Listener(on_press=self.on_interaction)

    # pylint: disable=unused-argument
    def on_interaction(self, *args):
        """ interaction detected """
        self.interaction_detected = True

    def startListener(self):
        """ start listening """
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stopListener(self):
        """ stop listening """
        self.mouse_listener.stop()
        self.keyboard_listener.stop()

    def lockedInUse(self):
        """Nimby State: Machine is in use, host is locked,
                        waiting for sufficient idle time"""
        self.interaction_detected = False

        time.sleep(5)
        if self.active and not self.interaction_detected:
            self.lockedIdle()
        elif self.active:

            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def unlockedIdle(self):
        """Nimby State: Machine is idle, host is unlocked,
                        waiting for user activity"""
        log.warning("unlockedIdle")
        while self.active and \
                not self.interaction_detected and \
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
            log.warning("starting Thread")
            self.thread.start()

    def lockedIdle(self):
        """Nimby State: Machine is idle,
                        waiting for sufficient idle time to unlock"""
        log.warning("lockedIdle")
        waitStartTime = time.time()

        time.sleep(rqd.rqconstants.MINIMUM_IDLE)

        if self.active and not self.interaction_detected and \
                self.rqCore.machine.isNimbySafeToUnlock():
            log.warning("Start wait time: %s", waitStartTime)
            self.unlockNimby(asOf=waitStartTime)
            self.unlockedIdle()
        elif self.active:

            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def isNimbyActive(self):
        """ Check if user is active
        :return: boolean if events are logged and Nimby is active
        """
        return not self.active and self.interaction_detected
