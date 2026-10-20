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


"""Tests for cuegui.ThreadPool."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import threading
import time
import unittest
import weakref

import qtpy.QtCore

import cuegui.ThreadPool

from . import test_utils


def _waitFor(condition, timeout=5.0, processEvents=True):
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        if processEvents:
            qtpy.QtCore.QCoreApplication.processEvents()
        time.sleep(0.01)
    return condition()


def _fail():
    raise ValueError('arbitrary-error')


class _Owner(object):
    """Stands for a widget: owns the work and the callback of a task."""

    def __init__(self):
        self.callbacks = []

    def work(self):
        return 'result'

    def callback(self, work, result):
        self.callbacks.append((work[2], result))


class ThreadPoolTests(unittest.TestCase):

    def setUp(self):
        self.app = test_utils.createApplication()
        self.threadsBefore = list(self.app.threads)
        self.pool = cuegui.ThreadPool.ThreadPool(1)

    def tearDown(self):
        qtpy.QtCore.QCoreApplication.processEvents()
        threads = [t for t in self.app.threads if t not in self.threadsBefore]
        for thread in threads:
            thread.stop()
        for thread in threads:
            thread.wait(2000)
            self.app.threads.remove(thread)

    def test_runsCallbackOnGuiThreadWithResult(self):
        workThreads = []
        callbacks = []

        def work(value):
            workThreads.append(threading.current_thread())
            return value * 2

        def callback(work, result):
            callbacks.append((work[2], result, threading.current_thread()))

        self.pool.queue(work, callback, 'arbitrary-task', 21)

        self.assertTrue(_waitFor(lambda: callbacks))
        self.assertEqual([('arbitrary-task', 42, threading.main_thread())], callbacks)
        self.assertNotIn(threading.main_thread(), workThreads)

    def test_runsCallbacksInOrder(self):
        callbacks = []

        for i in range(5):
            self.pool.queue(lambda i=i: i, lambda _, result: callbacks.append(result),
                            'task-%d' % i)

        self.assertTrue(_waitFor(lambda: len(callbacks) == 5))
        self.assertEqual(list(range(5)), callbacks)

    def test_failedWorkRunsNoCallback(self):
        failing = _Owner()
        succeeding = _Owner()

        self.pool.queue(_fail, failing.callback, 'failing-task')
        self.pool.queue(succeeding.work, succeeding.callback, 'succeeding-task')

        self.assertTrue(_waitFor(lambda: succeeding.callbacks))
        self.assertEqual([], failing.callbacks)
        self.assertEqual([('succeeding-task', 'result')], succeeding.callbacks)

    def test_releasesWorkOnGuiThread(self):
        # The owner of the work is usually a widget, which must not be
        # destroyed on a worker thread.
        for fail in (False, True):
            releaseThreads = []
            owner = _Owner()
            weakref.finalize(
                owner, lambda threads=releaseThreads: threads.append(
                    threading.current_thread()))
            # The failing work does not reference the owner, as the logged
            # exception keeps the frames of the work alive.
            self.pool.queue(_fail if fail else owner.work, owner.callback, 'task-%s' % fail)
            del owner

            self.assertTrue(_waitFor(lambda threads=releaseThreads: threads))
            self.assertEqual([threading.main_thread()], releaseThreads)

    def test_workersDoNotWaitForGuiThread(self):
        done = []

        def work(i):
            done.append(i)
            return i

        self.pool.queue(work, lambda _, __: None, 'first-task', 1)
        self.pool.queue(work, lambda _, __: None, 'second-task', 2)

        self.assertTrue(_waitFor(lambda: len(done) == 2, timeout=2.0, processEvents=False))


if __name__ == '__main__':
    unittest.main()
