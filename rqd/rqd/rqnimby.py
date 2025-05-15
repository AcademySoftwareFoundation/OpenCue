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
import threading
import time
import logging

import rqd.rqconstants
import rqd.rqutil


log = logging.getLogger(__name__)

class Nimby(threading.Thread):
    """A thread that monitors user activity through keyboard and mouse input.

    This class uses the pynput library to detect when a user is actively using
    the computer. When user activity is detected, it locks the machine from being
    used for rendering (nimby lock). When the user becomes inactive for a specified
    period, it releases the machine for rendering (nimby unlock).

    Attributes:
        is_ready (bool): Whether pynput was successfully imported and initialized.
        rq_core: Reference to the RQD core for managing nimby state.
        locked (bool): Whether the host is currently locked for rendering.
        last_activity_time (float): Timestamp of the last detected user activity.
    """
    def __init__(self, rqCore):
        self.is_ready = False
        self.rq_core = rqCore
        self.locked = False
        self.__is_user_active = False
        self.__interrupt = False

        try:
            Nimby.setup_display()
            # pylint: disable=import-outside-toplevel
            import pynput
            self.is_ready = True
        except Exception as e:
            # Ideally ImportError could be used here, but pynput
            # can throw other kinds of exception while trying to
            # access runpy components
            log.warning("Failed to import pynput: %s", e)
            return
        # If pynput is not available, is_user_active should stay False to make the host bookable

        threading.Thread.__init__(self)

        self.idle_threshold = rqd.rqconstants.MINIMUM_IDLE
        self.interval = rqd.rqconstants.CHECK_INTERVAL_LOCKED
        self.last_activity_time = time.time()

        self.mouse_listener = pynput.mouse.Listener(
            on_move=self.__on_interaction,
            on_click=self.__on_interaction,
            on_scroll=self.__on_interaction)
        self.keyboard_listener = pynput.keyboard.Listener(on_press=self.__on_interaction)

    @staticmethod
    def setup_display():
        """
        DISPLAY is required to import pynput internals and it's not automatically set depending
        on the environment rqd is running in. This function attemps to read the display value
        from a file on the path specified on the property rqconstants.RQD_DISPLAY_PATH. If the
        property doesn't exist or the file doesn't exist, fallback to rqconstants.DEFAULT_DISPLAY
        """
        if rqd.rqconstants.RQD_DISPLAY_PATH and "DISPLAY" not in os.environ:
            with open(rqd.rqconstants.RQD_DISPLAY_PATH, "r", encoding='utf-8') as file:
                display = file.read().strip()
                os.environ["DISPLAY"] = display
        if "DISPLAY" not in os.environ:
            os.environ['DISPLAY'] = rqd.rqconstants.DEFAULT_DISPLAY

    def run(self):
        """Start nimby thread"""
        if not self.is_ready:
            log.error("Nimby cannot be started. Pynput failed to be initialized")
            return
        log.warning("Starting NimbyPynput thread")
        self.mouse_listener.start()
        self.keyboard_listener.start()

        try:
            while not self.__interrupt:
                self.__check_state()
                time.sleep(self.interval)
        except KeyboardInterrupt:
            log.warning("Nimby thread interrupted")
        finally:
            self.is_ready = False
            self.mouse_listener.stop()
            self.keyboard_listener.stop()

    def stop(self):
        """Stop nimby thread"""
        self.__interrupt = True

    def __check_state(self):
        if self.__is_user_active and \
                (time.time() - self.last_activity_time) > self.idle_threshold:
            self.__is_user_active = False
            log.warning(
                "Nimby: No user activity detected for %s seconds", self.idle_threshold)
        # If the host was locked and there's no user activity, check if it's
        # safe to unlock it
        if self.locked and not self.__is_user_active:
            if self.rq_core.machine.isNimbySafeToRunJobs():
                self.__unlock_host_for_rendering()
            else:
                log.warning(
                    "Nimby: Not unlocking host due to resource limitations")

    # pylint: disable=unused-argument
    def __on_interaction(self, *args):
        if not self.__is_user_active:
            self.__lock_host_for_rendering()
        self.last_activity_time = time.time()
        self.__is_user_active = True

    def __unlock_host_for_rendering(self):
        self.rq_core.onNimbyUnlock()
        self.locked = False
        log.warning(
            "Nimby: Unlocked host for rendering")

    def __lock_host_for_rendering(self):
        self.rq_core.onNimbyLock()
        self.locked = True
        log.warning("Nimby: User activity detected")
