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
Performs work in a thread and then returns the results.

A general purpose thread pool used for IO operations that shouldn't
be tied to the GUI thread.  Python has a global thread lock, so you won't
ever get true multi-threading unless your callable is implmented in C.  For
example, using cElementTree, you could parse a large XML in the background
without affecting the GUI too much.

Worker threads are started the first time work is placed in the queue.

The callbacks run on the GUI thread, which also releases the work and its
result: the work usually references widgets, and Qt objects must not be
destroyed on a worker thread. Workers do not wait for the callbacks, so a busy
GUI thread does not stop them. A callback is only run when the work succeeds.

Example code:
# Setup a threadpool with 2 threads:
import threadpool
workerpool = threadpool.ThreadPool(2)

# Add work to the queue:
workerpool.queue(someWork, someWorkCallback, "doing some work", unit)

# Create someWork function: (Executes in worker thread)
def someWork(unit):
    return 5*unit

# Create someWorkCallback function: (Executes in GUI thread)
def someWorkCallback(work, result):
    print result
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import range
import collections
import os
import threading

from qtpy import QtCore
import grpc

import cuegui.Logger


logger = cuegui.Logger.getLogger(__file__)


def systemCpuCount():
    """systemCpuCount()->int
        returns the # of procs on the system, linux only
    """
    # pylint: disable=bare-except
    try:
        return len([p for p in os.listdir("/sys/devices/system/cpu") if p.startswith("cpu")])
    except:
        return 1


# pylint: disable=no-member
class ThreadPool(QtCore.QObject):
    """A general purpose work queue class."""

    # Carries no Python objects across threads: the finished work is handed
    # over through self._done, and this only wakes the GUI thread up to
    # collect it.
    _workDone = QtCore.Signal()

    def __init__(self, num_threads, max_queue=50, parent=None):
        QtCore.QObject.__init__(self, parent=parent)
        self.app = cuegui.app()
        self.__threads = []
        self.__started = False
        self.__max_queue = max_queue
        self.__num_threads = num_threads

        self._q_mutex = QtCore.QMutex()
        self._q_empty = QtCore.QWaitCondition()
        self._q_queue = []
        self._dropped_tasks = {}

        # (work, result, succeeded) of the finished work, until the GUI thread
        # collects it.
        self._done = collections.deque()
        self._done_lock = threading.Lock()
        self._workDone.connect(self.__deliver, QtCore.Qt.QueuedConnection)

    def start(self):
        """Initializes the thread pool and starts running work."""
        if self.__started:
            return
        self.__started = True
        for i in range(0, self.__num_threads):
            thread = ThreadPool.WorkerThread(i, self)
            self.app.threads.append(thread)
            self.__threads.append(thread)
            self.__threads[i].start()

    def queue(self, callable_to_queue, callback, comment, *args):
        """Queues up a callable to be run from within a separate thread of execution."""
        self._q_mutex.lock()
        if not self.__started:
            self.start()
        if len(self._q_queue) <= self.__max_queue:
            # Check if this is a duplicate refresh task for the same widget
            is_duplicate = False
            for existing_task in self._q_queue:
                if existing_task[2] == comment:
                    is_duplicate = True
                    break

            if not is_duplicate:
                self._q_queue.append((callable_to_queue, callback, comment, args))
            else:
                # Task already queued, skip adding duplicate
                logger.debug("Skipping duplicate task: %s", comment)
        else:
            # Track dropped tasks to avoid spamming logs
            if comment not in self._dropped_tasks:
                self._dropped_tasks[comment] = 0
            self._dropped_tasks[comment] += 1

            # Only log every 10th drop for the same task to reduce log spam
            if self._dropped_tasks[comment] % 10 == 1:
                logger.warning("Queue length exceeds %s. Dropped task %d times: %s",
                             self.__max_queue, self._dropped_tasks[comment], comment)
        self._q_mutex.unlock()
        self._q_empty.wakeAll()

    def local(self, callable_to_queue, callback, comment, *args):
        """Executes a callable then immediately executes a callback, if given."""
        work = (callable_to_queue, callback, comment, args)
        try:
            if work[3]:
                result = work[0](*work[3])
            else:
                result = work[0]()
        except (TypeError, ValueError, RuntimeError) as e:
            logger.error("Error executing local task '%s': %s", comment, e)
            # Exit early to avoid calling the callback with an invalid result
            return

        if work[1]:
            try:
                self.runCallback(work, result)
            except AttributeError as e:
                logger.error("Error executing callback for task '%s': %s", comment, e)

    def __deliver(self):
        """Runs the callbacks of the finished work on the GUI thread."""
        while True:
            with self._done_lock:
                if not self._done:
                    return
                work, result, succeeded = self._done.popleft()
            if succeeded:
                # pylint: disable=broad-except
                try:
                    self.runCallback(work, result)
                except Exception:
                    logger.exception("Error in callback function for '%s'", work[2])

    def runCallback(self, work, result):
        """Runs the callback function."""
        if work[1]:  # Ensure callback exists
            try:
                work[1](work, result)  # Execute the callback function
            except TypeError as e:
                logger.error("TypeError in callback function for '%s': %s", work[2], e)
            except ValueError as e:
                logger.error("ValueError in callback function for '%s': %s", work[2], e)
            except AttributeError as e:
                logger.error("AttributeError: Callback function missing or not callable for "
                             "'%s': %s", work[2], e)
            except RuntimeError as e:
                logger.error("RuntimeError in callback function for '%s': %s", work[2], e)

    class WorkerThread(QtCore.QThread):
        """A thread running the work of the pool."""

        def __init__(self, name, parent):
            QtCore.QThread.__init__(self, parent)
            self.__parent = parent
            # pylint: disable=unused-private-member
            self.__name = name
            self.__running = False

        # pylint: disable=protected-access
        # pylint: disable=missing-function-docstring
        def run(self):
            self.__running = True
            while self.__running:

                work = None
                self.__parent._q_mutex.lock()
                try:
                    if self.__parent._q_queue:
                        work = self.__parent._q_queue.pop(0)
                    else:
                        self.__parent._q_empty.wait(self.__parent._q_mutex)
                except IndexError as e:
                    logger.error("IndexError: Tried to pop from an empty queue: %s", e)
                except RuntimeError as e:
                    logger.error("RuntimeError: Threading issue while waiting for queue: %s", e)
                # Fallback for unexpected issues
                except Exception as e:
                    logger.error("Unexpected error fetching work from queue: %s", e)
                finally:
                    self.__parent._q_mutex.unlock()

                if not work:
                    continue

                result = None
                succeeded = False
                try:
                    if work[3]:
                        result = work[0](*work[3])
                    else:
                        result = work[0]()
                    succeeded = True
                except grpc.RpcError as e:
                    # Handle gRPC errors gracefully - these are often transient
                    # pylint: disable=no-member
                    if hasattr(e, 'code') and e.code() in [grpc.StatusCode.CANCELLED,
                                                             grpc.StatusCode.UNAVAILABLE]:
                        logger.warning("gRPC connection issue for '%s': %s - "
                                     "UI will retry on next update", work[2], e.details())
                    else:
                        logger.error("gRPC error processing work for '%s': %s", work[2], e)
                    # pylint: enable=no-member
                except TypeError as e:
                    logger.error("TypeError in work processing for '%s': %s", work[2], e)
                except ValueError as e:
                    logger.error("ValueError in work processing for '%s': %s", work[2], e)
                except RuntimeError as e:
                    logger.error("RuntimeError in work processing for '%s': %s", work[2], e)
                except Exception as e:
                    logger.error("Unexpected error processing work for '%s': %s", work[2], e)

                logger.info("Done:' %s '", work[2])
                # Hand the work over to the GUI thread, even when it failed, so
                # that the last references to it are dropped there. This thread
                # drops its own before the GUI thread can collect them.
                with self.__parent._done_lock:
                    self.__parent._done.append((work, result, succeeded))
                    work = result = None
                try:
                    self.__parent._workDone.emit()
                except RuntimeError:
                    # The pool is being destroyed.
                    return
            logger.debug("Thread Stopping")

        def stop(self):
            """Stops the worker thread."""
            self.__running = False
            self.__parent._q_empty.wakeAll()
