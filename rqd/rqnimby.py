#!/usr/bin/python


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
Nimby allows a desktop to be used as a render host when not used.

Project: RQD

Module: rqnimby.py

Contact: Middle-Tier (middle-tier@imageworks.com)

SVN: $Id$
"""

import os
import select
import time
import signal
import threading
import logging as log

import rqconstants
import rqutil

class Nimby(threading.Thread):
    """Nimby == Not In My Back Yard.
       If enabled, nimby will lock and kill all frames running on the host if
       keyboard or mouse activitiy is detected. If sufficent idle time has
       passed, defined in the Constants class, nimby will then unlock the host
       and make it available for rendering."""

    def __init__(self, rq_core):
        """Nimby initialization
        @type    rq_core: RqCore
        @param   rq_core: Main RQD Object"""
        threading.Thread.__init__(self)

        self.rq_core = rq_core

        self.locked = False
        self.active = False

        self.fileObjList = []
        self.results = [[]]

        self.thread = None

        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        """If a signal is detected, call .stop()"""
        self.stop()

    def lockNimby(self):
        """Activates the nimby lock, calls lockNimby() in rqcore"""
        if self.active and not self.locked:
            self.locked = True
            log.info("Locked nimby")
            self.rq_core.onNimbyLock()

    def unlockNimby(self, asOf=None):
        """Deactivates the nimby lock, calls unlockNimby() in rqcore
        @param asOf: Time when idle state began, if known."""
        if self.locked:
            self.locked = False
            log.info("Unlocked nimby")
            self.rq_core.onNimbyUnlock(asOf=asOf)

    def _open_events(self):
        """Opens the /dev/input/event* files so nimby can monitor them"""
        self._close_events()

        rqutil.permissionsHigh()
        try:
            for device in os.listdir("/dev/input/"):
                if device.startswith("event") or device.startswith("mice"):
                    log.debug("Found device: %s" % device)
                    try:
                        self.fileObjList.append(open("/dev/input/%s" % device, "rb"))
                    except IOError, e:
                        # Bad device found
                        log.debug("IOError: Failed to open %s, %s" % ("/dev/input/%s" % device, e))
        finally:
            rqutil.permissionsLow()

    def _close_events(self):
        """Closes the /dev/input/event* files"""
        log.debug("_close_events")
        if self.fileObjList:
            for fileObj in self.fileObjList:
                try:
                    fileObj.close()
                except:
                    pass
            self.fileObjList = []

    def locked_inuse(self):
        """Nimby State: Machine is in use, host is locked,
                        waiting for sufficent idle time"""
        log.debug("locked_inuse")
        self._open_events()
        try:
            self.results = select.select(self.fileObjList, [], [], 5)
        except:
            pass
        if self.active and self.results[0] == []:
            self.locked_idle()
        elif self.active:
            self._close_events()
            self.thread = threading.Timer(rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.locked_inuse)
            self.thread.start()

    def locked_idle(self):
        """Nimby State: Machine is idle,
                        waiting for sufficent idle time to unlock"""
        log.debug("locked_idle")
        self._open_events()
        wait_start_time = time.time()
        try:
            self.results = select.select(self.fileObjList, [], [],
                                         rqconstants.MINIMUM_IDLE)
        except:
            pass
        if self.active and self.results[0] == [] and \
           self.rq_core.machine.isNimbySafeToUnlock():
            self._close_events()
            self.unlockNimby(asOf=wait_start_time)
            self.unlocked_idle()
        elif self.active:
            self._close_events()
            self.thread = threading.Timer(rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.locked_inuse)
            self.thread.start()

    def unlocked_idle(self):
        """Nimby State: Machine is idle, host is unlocked,
                        waiting for user activity"""
        log.debug("unlocked_idle")

        while self.active and \
              self.results[0] == [] and \
              self.rq_core.machine.isNimbySafeToRunJobs():
            try:
                self._open_events()
                self.results = select.select(self.fileObjList, [], [], 5)
            except:
                pass
            if not self.rq_core.machine.isNimbySafeToRunJobs():
                log.warning("memory threshold has been exceeded, locking nimby")
                self.active = True

        if self.active:
            self._close_events()
            self.lockNimby()
            self.thread = threading.Timer(rqconstants.CHECK_INTERVAL_LOCKED,
                                          self.locked_inuse)
            self.thread.start()

    def run(self):
        """Starts the Nimby thread"""
        log.debug("nimby.run()")
        self.active = True
        self.unlocked_idle()

    def stop(self):
        """Stops the Nimby thread"""
        log.debug("nimby.stop()")
        if self.thread:
            self.thread.cancel()
        self.active = False
        self._close_events()
        self.unlockNimby()

if __name__ == "__main__":
    # For debugging

    class machine:
        def isNimbySafeToRunJobs(self):
            log.debug("rq_core.machine: isNimbySafeToRunJobs()")
            return True

    class core:
        """For testing"""
        def __init__(self):
            """For testing"""
            self.machine = machine()

        def onNimbyLock(self):
            """For testing"""
            log.debug("rq_core: onNimbyLock()")
        def onNimbyUnlock(self, asOf=None):
            """For testing"""
            log.debug("rq_core: onNimbyUnlock()")

    rq_core = core()

    log.basicConfig(level=log.DEBUG)
    nimby = Nimby(rq_core)
    signal.signal(signal.SIGINT, nimby.signal_handler)
    nimby.locked = True
    nimby.check_interval_locked = 11
    nimby.minimum_idle = 20
    nimby.minimum_mem = 0
    nimby.maximum_load = 0
    nimby.start()

    time.sleep(30)
    print "calling stop"
    nimby.stop()

