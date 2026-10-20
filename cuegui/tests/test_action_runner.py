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


"""Tests for cuegui.ActionRunner."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import threading
import time
import unittest
import weakref

import qtpy.QtCore

import cuegui.ActionRunner

from . import test_utils


def _waitFor(condition, timeout=5.0):
    deadline = time.time() + timeout
    while not condition() and time.time() < deadline:
        qtpy.QtCore.QCoreApplication.processEvents()
        time.sleep(0.01)
    return condition()


def _fail():
    raise ValueError('arbitrary-error')


class _Owner(object):
    """Stands for a widget: owns the work and the callback of an action."""

    def work(self):
        return 'result'

    def callback(self, result, error):
        pass


class SubmitWithoutRunnerTests(unittest.TestCase):

    def setUp(self):
        self.app = test_utils.createApplication()
        self.app.action_runner = None

    def test_runsInline(self):
        results = []

        cuegui.ActionRunner.submit(lambda: 42, lambda result, error: results.append(
            (result, error)))

        self.assertEqual([(42, None)], results)

    def test_passesErrorToCallback(self):
        results = []
        failure = ValueError('arbitrary-error')

        def work():
            raise failure

        cuegui.ActionRunner.submit(work, lambda result, error: results.append(
            (result, error)))

        self.assertEqual([(None, failure)], results)

    def test_callbackErrorIsContained(self):
        def callback(_, __):
            raise ValueError('arbitrary-error')

        cuegui.ActionRunner.submit(lambda: None, callback)


class ActionRunnerTests(unittest.TestCase):

    def setUp(self):
        self.app = test_utils.createApplication()
        self.runner = cuegui.ActionRunner.ActionRunner()
        self.app.action_runner = self.runner

    def tearDown(self):
        self.runner.shutdown()
        self.app.action_runner = None

    def test_runsWorkOffGuiThreadInOrder(self):
        workThreads = []
        callbackThreads = []
        results = []

        def makeWork(i):
            def work():
                workThreads.append(threading.current_thread())
                # Work submitted first must complete first, even when slower.
                time.sleep(0.02 * (5 - i))
                return i
            return work

        def callback(result, error):
            callbackThreads.append(threading.current_thread())
            results.append((result, error))

        for i in range(5):
            cuegui.ActionRunner.submit(makeWork(i), callback)

        self.assertTrue(_waitFor(lambda: len(results) == 5))
        self.assertEqual([(i, None) for i in range(5)], results)
        self.assertNotIn(threading.main_thread(), workThreads)
        self.assertEqual([threading.main_thread()] * 5, callbackThreads)

    def test_failureDoesNotStopLaterWork(self):
        results = []
        failure = ValueError('arbitrary-error')

        def failingWork():
            raise failure

        cuegui.ActionRunner.submit(failingWork, lambda r, e: results.append((r, e)))
        cuegui.ActionRunner.submit(lambda: 'ok', lambda r, e: results.append((r, e)))

        self.assertTrue(_waitFor(lambda: len(results) == 2))
        self.assertEqual([(None, failure), ('ok', None)], results)

    def test_releasesWorkOnGuiThread(self):
        # The owner of the work is usually a widget, which must not be
        # destroyed on the worker thread.
        releaseThreads = []

        for i in range(20):
            owner = _Owner()
            weakref.finalize(owner, lambda: releaseThreads.append(threading.current_thread()))
            # The failing work does not reference the owner, as the logged
            # exception keeps the frames of the work alive.
            cuegui.ActionRunner.submit(_fail if i % 2 else owner.work, owner.callback)
            del owner

        self.assertTrue(_waitFor(lambda: len(releaseThreads) == 20))
        self.assertEqual([threading.main_thread()] * 20, releaseThreads)

    def test_shutdownWaitsForQueuedWork(self):
        done = []

        def work():
            time.sleep(0.05)
            done.append(True)

        self.runner.submit(work)
        self.runner.submit(work)
        self.runner.shutdown()

        self.assertEqual([True, True], done)

    def test_shutdownStopsCallbacksAndNewWork(self):
        results = []
        ran = []

        self.runner.submit(lambda: 'result', lambda result, error: results.append(result))
        self.runner.shutdown()
        self.runner.submit(lambda: ran.append(True), lambda result, error: ran.append(True))

        # The work is done, but its callback was not delivered before shutdown.
        self.assertFalse(_waitFor(lambda: results or ran, timeout=0.2))


if __name__ == '__main__':
    unittest.main()
