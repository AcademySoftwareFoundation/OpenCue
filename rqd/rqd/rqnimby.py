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

import os
import select
import time
import signal
import threading
import logging as log

import rqd.rqconstants
import rqd.rqutil


class Nimby(threading.Thread):
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
        self.use_pynput = rqd.rqconstants.USE_NIMBY_PYNPUT

        if self.use_pynput:
            import pynput
            self.mouse_listener = pynput.mouse.Listener(
                on_move=self.on_interaction,
                on_click=self.on_interaction,
                on_scroll=self.on_interaction)
            self.keyboard_listener = pynput.keyboard.Listener(on_press=self.on_interaction)

        self.locked = False
        self.active = False

        self.fileObjList = []
        self.results = [[]]

        self.thread = None

        self.interaction_detected = False

        signal.signal(signal.SIGINT, self.signalHandler)

    def on_interaction(self, *args):
        self.interaction_detected = True

    def signalHandler(self, sig, frame):
        """If a signal is detected, call .stop()"""
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

    def _openEvents(self):
        """Opens the /dev/input/event* files so nimby can monitor them"""
        self._closeEvents()

        rqd.rqutil.permissionsHigh()
        try:
            for device in os.listdir("/dev/input/"):
                if device.startswith("event") or device.startswith("mice"):
                    log.debug("Found device: %s" % device)
                    try:
                        self.fileObjList.append(open("/dev/input/%s" % device, "rb"))
                    except IOError as e:
                        # Bad device found
                        log.debug("IOError: Failed to open %s, %s" % ("/dev/input/%s" % device, e))
        finally:
            rqd.rqutil.permissionsLow()

    def _closeEvents(self):
        """Closes the /dev/input/event* files"""
        log.debug("_closeEvents")
        if self.fileObjList:
            for fileObj in self.fileObjList:
                try:
                    fileObj.close()
                except:
                    pass
            self.fileObjList = []

    def lockedInUse(self):
        """Nimby State: Machine is in use, host is locked, waiting for sufficient idle time"""
        log.debug("lockedInUse")
        if self.use_pynput:
            self._lockedInUsePynput()
        else:
            self._lockedInUseSelect()

    def _lockedInUseSelect(self):
        self._openEvents()
        try:
            self.results = select.select(self.fileObjList, [], [], 5)
        except:
            pass
        if self.active and self.results[0] == []:
            self.lockedIdle()
        elif self.active:
            self._closeEvents()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def _lockedInUsePynput(self):
        self.interaction_detected = False

        time.sleep(5)
        if self.active and self.interaction_detected == False:
            self.lockedIdle()
        elif self.active:

            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def lockedIdle(self):
        """Nimby State: Machine is idle, waiting for sufficient idle time to unlock"""
        log.debug("locked_idle")
        if self.use_pynput:
            self._lockedIdlePynput()
        else:
            self._lockedIdleSelect()

    def _lockedIdleSelect(self):
        """Nimby State: Machine is idle,
                        waiting for sufficient idle time to unlock"""
        self._openEvents()
        waitStartTime = time.time()
        try:
            self.results = select.select(self.fileObjList, [], [],
                                         rqd.rqconstants.MINIMUM_IDLE)
        except:
            pass
        if self.active and self.results[0] == [] and \
           self.rqCore.machine.isNimbySafeToUnlock():
            self._closeEvents()
            self.unlockNimby(asOf=waitStartTime)
            self.unlockedIdle()
        elif self.active:
            self._closeEvents()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def _lockedIdlePynput(self):
        waitStartTime = time.time()

        time.sleep(rqd.rqconstants.MINIMUM_IDLE)

        if self.active and self.interaction_detected == False and \
                self.rqCore.machine.isNimbySafeToUnlock():

            self.unlockNimby(asOf=waitStartTime)
            self.unlockedIdle()
        elif self.active:

            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def unlockedIdle(self):
        """Nimby State: Machine is idle, host is unlocked, waiting for user activity"""
        log.debug("unlockedIdle")
        if self.use_pynput:
            self._lockedIdlePynput()
        else:
            self._unlockedIdleSelect()

    def _unlockedIdleSelect(self):
        """Nimby State: Machine is idle, host is unlocked,
                        waiting for user activity"""
        while self.active and \
              self.results[0] == [] and \
              self.rqCore.machine.isNimbySafeToRunJobs():
            try:
                self._openEvents()
                self.results = select.select(self.fileObjList, [], [], 5)
            except:
                pass
            if not self.rqCore.machine.isNimbySafeToRunJobs():
                log.warning("memory threshold has been exceeded, locking nimby")
                self.active = True

        if self.active:
            self._closeEvents()
            self.lockNimby()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def _unlockedIdlePynput(self):
        while self.active and \
                self.interaction_detected == False and \
                self.rqCore.machine.isNimbySafeToRunJobs():

            time.sleep(5)

            if not self.rqCore.machine.isNimbySafeToRunJobs():
                log.warning("memory threshold has been exceeded, locking nimby")
                self.active = True

        if self.active:
            self.lockNimby()
            self.thread = threading.Timer(rqd.rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.lockedInUse)
            self.thread.start()

    def run(self):
        """Starts the Nimby thread"""
        log.debug("nimby.run()")
        self.active = True
        if self.use_pynput:
            self.mouse_listener.start()
            self.keyboard_listener.start()
        self.unlockedIdle()

    def stop(self):
        """Stops the Nimby thread"""
        log.debug("nimby.stop()")
        if self.thread:
            self.thread.cancel()
        self.active = False
        if self.use_pynput:
            self.mouse_listener.stop()
            self.keyboard_listener.stop()
        else:
            self._closeEvents()
        self.unlockNimby()
