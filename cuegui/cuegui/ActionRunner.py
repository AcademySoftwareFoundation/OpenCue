#  Copyright (c) OpenCue Project Authors
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


"""Runs user-triggered Cuebot calls off the GUI thread.

pycue calls block for up to Cuebot.Timeout and are retried on UNAVAILABLE, so
making them on the GUI thread freezes the whole window while Cuebot is slow.

The ThreadPool is meant for periodic refreshes: it has several workers, so it
does not keep the order of the work, it skips work whose comment is already
queued and it drops work when its queue is long. None of that is acceptable for
user actions (a pause followed by a resume must not run in the other order, and
a kill must not be dropped), so they go through the ActionRunner instead: a
single worker thread that runs the work in submission order and hands each
result to a callback on the GUI thread.

Usage::

    def work():  # runs on the worker thread
        job.pause()

    def done(result, error):  # runs on the GUI thread
        ...

    cuegui.ActionRunner.submit(work, done, "Pausing job")
"""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import queue
import threading

from qtpy import QtCore

import cuegui
import cuegui.Logger


logger = cuegui.Logger.getLogger(__file__)

# Seconds the application waits on exit for submitted work to finish.
SHUTDOWN_TIMEOUT = 5


def submit(work, callback=None, description=None):
    """Runs work() off the GUI thread, then callback(result, error) on the GUI thread.

    Work runs on the application's ActionRunner, one item at a time, in
    submission order. Without an ActionRunner (unit tests, or tools that build
    widgets without going through cuegui.Main), work and callback run inline.

    @type  work: callable
    @param work: called with no arguments; must not touch Qt widgets
    @type  callback: callable or None
    @param callback: called as callback(result, error); error is the exception
                     raised by work, or None
    @type  description: str
    @param description: what the work does, used in log messages"""
    runner = getattr(cuegui.app(), "action_runner", None)
    if runner is None:
        result, error = _call(work, description)
        if callback is not None:
            _callCallback(callback, result, error, description)
        return
    runner.submit(work, callback, description)


def _call(work, description):
    try:
        return work(), None
    # Anything raised here would otherwise be lost on the worker thread.
    # pylint: disable=broad-except
    except Exception as e:
        logger.warning("%s failed", description or "Action", exc_info=True)
        return None, e


def _callCallback(callback, result, error, description):
    try:
        callback(result, error)
    # The widget the callback belongs to may have been closed in the meantime.
    # pylint: disable=broad-except
    except Exception:
        logger.exception("Callback for '%s' failed", description or "action")


class ActionRunner(QtCore.QObject):
    """Runs work on a single worker thread, in order, with GUI-thread callbacks."""

    # Carries no Python objects across threads: results are handed over through
    # self.__done, and this only wakes the GUI thread up to collect them.
    _workDone = QtCore.Signal()

    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.__pending = queue.Queue()
        self.__done = collections.deque()
        self.__doneLock = threading.Lock()
        self.__thread = None
        self.__stopped = False
        # pylint: disable=no-member
        self._workDone.connect(self.__deliver, QtCore.Qt.QueuedConnection)
        # pylint: enable=no-member

    def submit(self, work, callback=None, description=None):
        """Queues work. See cuegui.ActionRunner.submit. Work submitted after
        shutdown is ignored."""
        if self.__stopped:
            logger.warning("Not running '%s': the application is exiting",
                           description or "action")
            return
        if self.__thread is None:
            self.__thread = threading.Thread(
                target=self.__run, name="cuegui-action-runner", daemon=True)
            self.__thread.start()
        self.__pending.put((work, callback, description))

    def shutdown(self, timeout=SHUTDOWN_TIMEOUT):
        """Stops the worker once the work queued so far is done, waiting at
        most timeout seconds. From then on, callbacks are not run and new work
        is ignored: the widgets they belong to are being torn down."""
        self.__stopped = True
        if self.__thread is None:
            return
        self.__pending.put(None)
        self.__thread.join(timeout)
        if self.__thread.is_alive():
            logger.warning("Exiting before all submitted Cuebot calls completed")

    def __run(self):
        while True:
            item = self.__pending.get()
            if item is None:
                return
            work, callback, description = item
            result, error = _call(work, description)
            with self.__doneLock:
                self.__done.append((callback, result, error, description))
                # Drop this thread's references before the GUI thread can
                # collect them, so that the GUI thread holds the last ones; the
                # work may reference Qt objects.
                del item, work, callback, result, error
            try:
                self._workDone.emit()
            except RuntimeError:
                # The application is being torn down.
                return

    def __deliver(self):
        while True:
            with self.__doneLock:
                if not self.__done:
                    return
                callback, result, error, description = self.__done.popleft()
            if callback is not None and not self.__stopped:
                _callCallback(callback, result, error, description)
