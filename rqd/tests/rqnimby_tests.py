#!/usr/bin/env python

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

import os
import mock
import signal
import unittest

import pyfakefs.fake_filesystem_unittest

import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.rqd_pb2
import rqd.rqconstants
import rqd.rqcore
import rqd.rqexceptions
import rqd.rqmachine
import rqd.rqnetwork
import rqd.rqnimby


@mock.patch('threading.Timer', new=mock.MagicMock())
@mock.patch('rqd.rqutil.permissionsHigh', new=mock.MagicMock())
@mock.patch('rqd.rqutil.permissionsLow', new=mock.MagicMock())
class RqNimbyTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.inputDevice = self.fs.create_file('/dev/input/event0', contents='mouse event')

        self.rqMachine = mock.MagicMock(spec=rqd.rqmachine.Machine)
        #self.rqCore.machine.isNimbySafeToRunJobs()
        self.rqCore = mock.MagicMock(spec=rqd.rqcore.RqCore)
        self.rqCore.machine = self.rqMachine
        self.nimby = rqd.rqnimby.Nimby(self.rqCore)

        #self.nimby.daemon = True

    def tearDown(self):
        #self.nimby.stop()
        #self.nimby.join()
        pass

    # unlockedIdle
    def test_unlockedIdle(self):
        self.nimby.active = True
        self.nimby.results = [[]]
        self.rqCore.machine.isNimbySafeToRunJobs.return_value = True

        # THIS BLOCKS -- need to find a different way to trigger
        self.nimby.unlockedIdle()

        with open('/dev/input/event0', 'a') as fp:
            fp.write('a new mouse event')

    # lockedIdle

    # lockedInUse

    # start(), check initial conditions, then stop()

    def footest_lockNimby(self):
        self.nimby.start()

        self.nimby.lockNimby()

        self.assertTrue(self.nimby.locked)
        self.rqCore.onNimbyLock.assert_called()

    def footest_unlockNimby(self):
        self.nimby.locked = True
        self.nimby.start()

        self.nimby.unlockNimby()

        self.assertFalse(self.nimby.locked)
        self.rqCore.onNimbyUnlock.assert_called()


if __name__ == '__main__':
    unittest.main()
