#!/usr/bin/env python

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

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import mock
import unittest

import pyfakefs.fake_filesystem_unittest

import rqd.rqcore
import rqd.rqmachine
import rqd.rqnimby


@mock.patch('rqd.rqutil.permissionsHigh', new=mock.MagicMock())
@mock.patch('rqd.rqutil.permissionsLow', new=mock.MagicMock())
class RqNimbyTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.inputDevice = self.fs.create_file('/dev/input/event0', contents='mouse event')

        self.rqMachine = mock.MagicMock(spec=rqd.rqmachine.Machine)
        self.rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        self.rqCore.machine = self.rqMachine
        self.nimby = rqd.rqnimby.NimbyFactory.getNimby(self.rqCore)
        self.nimby.daemon = True

    @mock.patch.object(rqd.rqnimby.NimbySelect, 'unlockedIdle')
    def test_initialState(self, unlockedIdleMock):
        self.nimby.daemon = True

        self.nimby.start()
        self.nimby.join()

        # Initial state should be "unlocked and idle".
        unlockedIdleMock.assert_called()

        self.nimby.stop()

    @mock.patch('select.select', new=mock.MagicMock(return_value=[['a new mouse event'], [], []]))
    @mock.patch('threading.Timer')
    def test_unlockedIdle(self, timerMock):
        self.nimby.active = True
        self.nimby.results = [[]]
        self.rqCore.machine.isNimbySafeToRunJobs.return_value = True

        self.nimby.unlockedIdle()

        # Given a mouse event, Nimby should transition to "locked and in use".
        timerMock.assert_called_with(mock.ANY, self.nimby.lockedInUse)
        timerMock.return_value.start.assert_called()

    @mock.patch('select.select', new=mock.MagicMock(return_value=[[], [], []]))
    @mock.patch.object(rqd.rqnimby.NimbySelect, 'unlockedIdle')
    @mock.patch('threading.Timer')
    def test_lockedIdleWhenIdle(self, timerMock, unlockedIdleMock):
        self.nimby.active = True
        self.nimby.results = [[]]
        self.rqCore.machine.isNimbySafeToRunJobs.return_value = True

        self.nimby.lockedIdle()

        # Given no events, Nimby should transition to "unlocked and idle".
        unlockedIdleMock.assert_called()

    @mock.patch('select.select', new=mock.MagicMock(return_value=[['a new mouse event'], [], []]))
    @mock.patch('threading.Timer')
    def test_lockedIdleWhenInUse(self, timerMock):
        self.nimby.active = True
        self.nimby.results = [[]]
        self.rqCore.machine.isNimbySafeToRunJobs.return_value = True

        self.nimby.lockedIdle()

        # Given a mouse event, Nimby should transition to "locked and in use".
        timerMock.assert_called_with(mock.ANY, self.nimby.lockedInUse)
        timerMock.return_value.start.assert_called()

    @mock.patch('select.select', new=mock.MagicMock(return_value=[[], [], []]))
    @mock.patch.object(rqd.rqnimby.NimbySelect, 'lockedIdle')
    @mock.patch('threading.Timer')
    def test_lockedInUseWhenIdle(self, timerMock, lockedIdleMock):
        self.nimby.active = True
        self.nimby.results = [[]]
        self.rqCore.machine.isNimbySafeToRunJobs.return_value = True

        self.nimby.lockedInUse()

        # Given no events, Nimby should transition to "locked and idle".
        lockedIdleMock.assert_called()

    @mock.patch('select.select', new=mock.MagicMock(return_value=[['a new mouse event'], [], []]))
    @mock.patch('threading.Timer')
    def test_lockedInUseWhenInUse(self, timerMock):
        self.nimby.active = True
        self.nimby.results = [[]]
        self.rqCore.machine.isNimbySafeToRunJobs.return_value = True

        self.nimby.lockedInUse()

        # Given a mouse event, Nimby should stay in state "locked and in use".
        timerMock.assert_called_with(mock.ANY, self.nimby.lockedInUse)
        timerMock.return_value.start.assert_called()

    def test_lockNimby(self):
        self.nimby.active = True
        self.nimby.locked = False

        self.nimby.lockNimby()

        self.assertTrue(self.nimby.locked)
        self.rqCore.onNimbyLock.assert_called()

    def test_unlockNimby(self):
        self.nimby.locked = True

        self.nimby.unlockNimby()

        self.assertFalse(self.nimby.locked)
        self.rqCore.onNimbyUnlock.assert_called()


if __name__ == '__main__':
    unittest.main()
