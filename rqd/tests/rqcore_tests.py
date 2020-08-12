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

from builtins import str
import mock
import os.path
import unittest

import pyfakefs.fake_filesystem_unittest

import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.rqd_pb2
import rqd.rqconstants
import rqd.rqcore
import rqd.rqexceptions
import rqd.rqnetwork
import rqd.rqnimby


class RqCoreTests(unittest.TestCase):

    @mock.patch('rqd.rqnimby.NimbySelect', autospec=True)
    @mock.patch('rqd.rqnetwork.Network', autospec=True)
    @mock.patch('rqd.rqmachine.Machine', autospec=True)
    def setUp(self, machineMock, networkMock, nimbyMock):
        self.machineMock = machineMock
        self.networkMock = networkMock
        self.nimbyMock = nimbyMock
        self.rqcore = rqd.rqcore.RqCore()

    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOn')
    def test_startServer(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = False
        self.machineMock.return_value.isDesktop.return_value = False

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOn', autospec=True)
    def test_startServerWithNimby(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = True
        self.machineMock.return_value.isDesktop.return_value = False

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_called_with(self.rqcore)

    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOn', autospec=True)
    def test_startDesktopNimbyOn(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = True
        self.machineMock.return_value.isDesktop.return_value = True

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_called_with(self.rqcore)

    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOn')
    def test_startDesktopNimbyOff(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = False
        self.machineMock.return_value.isDesktop.return_value = True

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOn')
    def test_startDesktopNimbyUndefined(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = None
        self.machineMock.return_value.isDesktop.return_value = True

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch('rqd.rqnetwork.Network', autospec=True)
    @mock.patch('rqd.rqmachine.Machine', autospec=True)
    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOn')
    def test_startDesktopNimbyOffWithFlag(self, nimbyOnMock, machineMock, networkMock):
        rqd.rqconstants.OVERRIDE_NIMBY = True
        machineMock.return_value.isDesktop.return_value = True
        rqcore = rqd.rqcore.RqCore(optNimbyoff=True)

        rqcore.start()

        networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch('threading.Timer')
    def test_grpcConnected(self, timerMock):
        update_rss_thread = mock.MagicMock()
        interval_thread = mock.MagicMock()
        timerMock.side_effect = [update_rss_thread, interval_thread]

        self.rqcore.grpcConnected()

        self.networkMock.return_value.reportRqdStartup.assert_called()
        update_rss_thread.start.assert_called()
        interval_thread.start.assert_called()

    @mock.patch.object(rqd.rqcore.RqCore, 'sendStatusReport', autospec=True)
    @mock.patch('threading.Timer')
    def test_onInterval(self, timerMock, sendStatusReportMock):
        self.rqcore.onInterval()

        timerMock.return_value.start.assert_called()
        sendStatusReportMock.assert_called_with(self.rqcore)

    @mock.patch('threading.Timer', autospec=True)
    def test_onIntervalWithSleepTime(self, timerMock):
        sleep_time = 72

        self.rqcore.onInterval(sleepTime=sleep_time)

        timerMock.assert_called_with(sleep_time, mock.ANY)
        timerMock.return_value.start.assert_called()

    @mock.patch.object(rqd.rqcore.RqCore, 'shutdownRqdNow')
    @mock.patch('threading.Timer', new=mock.MagicMock())
    def test_onIntervalShutdown(self, shutdownRqdNowMock):
        self.rqcore.shutdownRqdIdle()
        self.machineMock.return_value.isUserLoggedIn.return_value = False
        shutdownRqdNowMock.reset_mock()
        shutdownRqdNowMock.assert_not_called()

        self.rqcore.onInterval()

        shutdownRqdNowMock.assert_called_with()

    @mock.patch('threading.Timer')
    def test_updateRss(self, timerMock):
        self.rqcore.storeFrame('frame-id', mock.MagicMock(spec=rqd.rqnetwork.RunningFrame))

        self.rqcore.updateRss()

        self.machineMock.return_value.rssUpdate.assert_called()
        timerMock.return_value.start.assert_called()

    def test_getFrame(self):
        frame_id = 'arbitrary-frame-id'
        frame = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        self.rqcore.storeFrame(frame_id, frame)

        self.assertEqual(frame, self.rqcore.getFrame(frame_id))

    def test_getFrameKeys(self):
        frame_ids = ['frame1', 'frame2']
        self.rqcore.storeFrame(frame_ids[0], mock.MagicMock(spec=rqd.rqnetwork.RunningFrame))
        self.rqcore.storeFrame(frame_ids[1], mock.MagicMock(spec=rqd.rqnetwork.RunningFrame))

        self.assertEqual(set(frame_ids), set(self.rqcore.getFrameKeys()))

    def test_storeFrame(self):
        frame_id = 'arbitrary-frame-id'
        frame = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        with self.assertRaises(KeyError):
            self.rqcore.getFrame(frame_id)

        self.rqcore.storeFrame(frame_id, frame)

        self.assertEqual(frame, self.rqcore.getFrame(frame_id))

    def test_storeFrameDuplicate(self):
        frame_id = 'arbitrary-frame-id'
        self.rqcore.storeFrame(frame_id, mock.MagicMock(spec=rqd.rqnetwork.RunningFrame))

        with self.assertRaises(rqd.rqexceptions.RqdException):
            self.rqcore.storeFrame(frame_id, mock.MagicMock(spec=rqd.rqnetwork.RunningFrame))

    def test_deleteFrame(self):
        frame_id = 'arbitrary-frame-id'
        frame = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        self.rqcore.storeFrame(frame_id, frame)

        self.rqcore.deleteFrame(frame_id)
        self.rqcore.deleteFrame('unknown-key-should-succeed')

        with self.assertRaises(KeyError):
            self.rqcore.getFrame(frame_id)

    def test_killAllFrame(self):
        frameAttendantThread = mock.MagicMock()
        frameAttendantThread.isAlive.return_value = False
        frame1Id = 'frame1'
        frame2Id = 'frame2'
        frame3Id = 'frame3'
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame1Id))
        frame1.frameAttendantThread = frameAttendantThread
        frame2 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame2Id))
        frame2.frameAttendantThread = frameAttendantThread
        frame3 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame3Id))
        frame3.frameAttendantThread = frameAttendantThread
        self.rqcore.storeFrame(frame1Id, frame1)
        self.rqcore.storeFrame(frame2Id, frame2)
        self.rqcore.storeFrame(frame3Id, frame3)

        # There's no result to verify here; if the method completes successfully
        # it means that all frames were properly killed, as the method won't finish
        # until its frame cache is cleared by the kill process.
        self.rqcore.killAllFrame('arbitrary reason')

    def test_killAllFrameIgnoreNimby(self):
        frameAttendantThread = mock.MagicMock()
        frameAttendantThread.isAlive.return_value = False
        frame1Id = 'frame1'
        frame2Id = 'frame2'
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame1Id))
        frame1.frameAttendantThread = frameAttendantThread
        frame2 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame2Id, ignore_nimby=True))
        frame2.frameAttendantThread = frameAttendantThread
        self.rqcore.storeFrame(frame1Id, frame1)
        self.rqcore.storeFrame(frame2Id, frame2)

        self.rqcore.killAllFrame('NIMBY related reason')

        self.assertEqual(frame2, self.rqcore.getFrame(frame2Id))

    def test_releaseCores(self):
        num_idle_cores = 10
        num_booked_cores = 7
        num_cores_to_release = 5
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(
            total_cores=50, idle_cores=num_idle_cores, locked_cores=2, booked_cores=num_booked_cores)

        self.rqcore.releaseCores(num_cores_to_release)

        self.assertEqual(num_booked_cores-num_cores_to_release, self.rqcore.cores.booked_cores)
        self.assertEqual(num_idle_cores+num_cores_to_release, self.rqcore.cores.idle_cores)

    @mock.patch.object(rqd.rqcore.RqCore, 'nimbyOff')
    def test_shutdown(self, nimbyOffMock):
        self.rqcore.onIntervalThread = mock.MagicMock()
        self.rqcore.updateRssThread = mock.MagicMock()

        self.rqcore.shutdown()

        nimbyOffMock.assert_called()
        self.rqcore.onIntervalThread.cancel.assert_called()
        self.rqcore.updateRssThread.cancel.assert_called()

    @mock.patch('rqd.rqnetwork.Network', autospec=True)
    @mock.patch('sys.exit')
    def test_handleExit(self, networkMock, exitMock):
        self.rqcore = rqd.rqcore.RqCore()

        self.rqcore.handleExit(None, None)

        exitMock.assert_called()

    @mock.patch('rqd.rqcore.FrameAttendantThread')
    def test_launchFrame(self, frameThreadMock):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=20)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)

        self.rqcore.launchFrame(frame)

        frameThreadMock.return_value.start.assert_called()

    def test_launchFrameOnDownHost(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.DOWN
        frame = rqd.compiled_proto.rqd_pb2.RunFrame()

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameOnHostWaitingForShutdown(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.active = False
        frame = rqd.compiled_proto.rqd_pb2.RunFrame()
        self.rqcore.shutdownRqdIdle()

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    @mock.patch('rqd.rqcore.FrameAttendantThread')
    def test_launchFrameOnNimbyHost(self, frameThreadMock):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=20)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)
        frameIgnoreNimby = rqd.compiled_proto.rqd_pb2.RunFrame(
            uid=22, num_cores=10, ignore_nimby=True)
        self.rqcore.nimby = mock.create_autospec(rqd.rqnimby.NimbySelect)
        self.rqcore.nimby.locked = True

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

        self.rqcore.launchFrame(frameIgnoreNimby)

        frameThreadMock.return_value.start.assert_called()

    def test_launchDuplicateFrame(self):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=20)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frameId = 'arbitrary-frame-id'
        self.rqcore.storeFrame(frameId, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frameId))
        frameToLaunch = rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frameId)

        with self.assertRaises(rqd.rqexceptions.DuplicateFrameViolationException):
            self.rqcore.launchFrame(frameToLaunch)

    def test_launchFrameWithInvalidUid(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=0)

        with self.assertRaises(rqd.rqexceptions.InvalidUserException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameWithInvalidCoreCount(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=22, num_cores=0)

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameWithInsufficientCores(self):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=5)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_getRunningFrame(self):
        frameId = 'arbitrary-frame-id'
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frameId)
        self.rqcore.storeFrame(frameId, frame)

        self.assertEqual(frame, self.rqcore.getRunningFrame(frameId))
        self.assertIsNone(self.rqcore.getRunningFrame('some-unknown-frame-id'))

    @mock.patch.object(rqd.rqcore.RqCore, 'respawn_rqd', autospec=True)
    def test_restartRqdNowNoFrames(self, respawnMock):
        self.nimbyMock.return_value.active = False

        self.rqcore.restartRqdNow()

        respawnMock.assert_called_with(self.rqcore)

    @mock.patch.object(rqd.rqcore.RqCore, 'killAllFrame', autospec=True)
    def test_restartRqdNowWithFrames(self, killAllFrameMock):
        frame1Id = 'frame1'
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame1Id))
        self.rqcore.storeFrame(frame1Id, frame1)

        self.rqcore.restartRqdNow()

        killAllFrameMock.assert_called_with(self.rqcore, mock.ANY)

    @mock.patch.object(rqd.rqcore.RqCore, 'respawn_rqd', autospec=True)
    def test_restartRqdIdleNoFrames(self, respawnMock):
        self.nimbyMock.return_value.active = False

        self.rqcore.restartRqdIdle()

        respawnMock.assert_called_with(self.rqcore)

    @mock.patch.object(rqd.rqcore.RqCore, 'respawn_rqd')
    def test_restartRqdIdleWithFrames(self, respawnMock):
        frame1Id = 'frame1'
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame1Id))
        self.rqcore.storeFrame(frame1Id, frame1)

        self.rqcore.restartRqdIdle()

        self.assertTrue(self.rqcore.isWaitingForIdle())
        respawnMock.assert_not_called()

    def test_rebootNowNoUser(self):
        self.machineMock.return_value.isUserLoggedIn.return_value = False
        self.nimbyMock.return_value.active = False

        self.rqcore.rebootNow()

        self.machineMock.return_value.reboot.assert_called_with()

    def test_rebootNowWithUser(self):
        self.machineMock.return_value.isUserLoggedIn.return_value = True

        with self.assertRaises(rqd.rqexceptions.RqdException):
            self.rqcore.rebootNow()

    def test_rebootIdleNoFrames(self):
        self.machineMock.return_value.isUserLoggedIn.return_value = False
        self.nimbyMock.return_value.active = False

        self.rqcore.rebootIdle()

        self.machineMock.return_value.reboot.assert_called_with()

    def test_rebootIdleWithFrames(self):
        frame1Id = 'frame1'
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frame1Id))
        self.rqcore.storeFrame(frame1Id, frame1)

        self.rqcore.rebootIdle()

        self.assertTrue(self.rqcore.isWaitingForIdle())
        self.machineMock.return_value.reboot.assert_not_called()

    @mock.patch('os.getuid', new=mock.MagicMock(return_value=0))
    @mock.patch('platform.system', new=mock.MagicMock(return_value='Linux'))
    def test_nimbyOn(self):
        self.nimbyMock.return_value.active = False

        self.rqcore.nimbyOn()

        self.nimbyMock.return_value.run.assert_called_with()

    def test_nimbyOff(self):
        self.nimbyMock.return_value.active = True

        self.rqcore.nimbyOff()

        self.nimbyMock.return_value.stop.assert_called_with()

    @mock.patch.object(rqd.rqcore.RqCore, 'killAllFrame', autospec=True)
    def test_onNimbyLock(self, killAllFrameMock):
        self.rqcore.onNimbyLock()

        killAllFrameMock.assert_called_with(self.rqcore, mock.ANY)

    @mock.patch.object(rqd.rqcore.RqCore, 'sendStatusReport', autospec=True)
    def test_onNimbyUnlock(self, sendStatusReportMock):
        self.rqcore.onNimbyUnlock()

        sendStatusReportMock.assert_called_with(self.rqcore)

    def test_lock(self):
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.lock(20)

        self.assertEqual(20, self.rqcore.cores.idle_cores)
        self.assertEqual(30, self.rqcore.cores.locked_cores)

    def test_lockMoreCoresThanThereAre(self):
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.lock(100)

        self.assertEqual(0, self.rqcore.cores.idle_cores)
        self.assertEqual(50, self.rqcore.cores.locked_cores)

    def test_lockAll(self):
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.lockAll()

        self.assertEqual(0, self.rqcore.cores.idle_cores)
        self.assertEqual(50, self.rqcore.cores.locked_cores)

    def test_unlock(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 10
        self.rqcore.cores.locked_cores = 40

        self.rqcore.unlock(20)

        self.assertEqual(30, self.rqcore.cores.idle_cores)
        self.assertEqual(20, self.rqcore.cores.locked_cores)

    def test_unlockMoreCoresThanThereAre(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.unlock(100)

        self.assertEqual(50, self.rqcore.cores.idle_cores)
        self.assertEqual(0, self.rqcore.cores.locked_cores)

    def test_unlockAll(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.unlockAll()

        self.assertEqual(50, self.rqcore.cores.idle_cores)
        self.assertEqual(0, self.rqcore.cores.locked_cores)

    def test_unlockAllWhenNimbyLocked(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = True
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.unlockAll()

        self.assertEqual(40, self.rqcore.cores.idle_cores)
        self.assertEqual(0, self.rqcore.cores.locked_cores)


@mock.patch('rqd.rqutil.checkAndCreateUser', new=mock.MagicMock())
@mock.patch('rqd.rqutil.permissionsHigh', new=mock.MagicMock())
@mock.patch('rqd.rqutil.permissionsLow', new=mock.MagicMock())
@mock.patch('subprocess.Popen')
@mock.patch('time.time')
@mock.patch('rqd.rqutil.permissionsUser', spec=True)
class FrameAttendantThreadTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        rqd.rqconstants.SU_ARGUEMENT = '-c'

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('tempfile.gettempdir')
    def test_runLinux(self, getTempDirMock, permsUser, timeMock, popenMock): # mkdirMock, openMock,
        # given
        currentTime = 1568070634.3
        jobTempPath = '/job/temp/path/'
        logDir = '/path/to/log/dir/'
        tempDir = '/some/random/temp/dir'
        frameId = 'arbitrary-frame-id'
        jobName = 'arbitrary-job-name'
        frameName = 'arbitrary-frame-name'
        frameUid = 928
        frameUsername = 'my-random-user'
        returnCode = 0
        renderHost = rqd.compiled_proto.report_pb2.RenderHost(name='arbitrary-host-name')
        logFile = os.path.join(logDir, '%s.%s.rqlog' % (jobName, frameName))

        self.fs.create_dir(tempDir)

        timeMock.return_value = currentTime
        getTempDirMock.return_value = tempDir
        popenMock.return_value.wait.return_value = returnCode

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False

        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir)
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        # when
        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        # then
        permsUser.assert_called_with(frameUid, mock.ANY)
        popenMock.assert_called_with(
            [
                '/bin/nice', '/usr/bin/time', '-p', '-o',
                jobTempPath + 'rqd-stat-' + frameId + '-' + str(currentTime),
                '/bin/su', frameUsername, '-c',
                '"' + tempDir + '/rqd-cmd-' + frameId + '-' + str(currentTime) + '"'
            ],
            env=mock.ANY,
            cwd=jobTempPath,
            stdin=mock.ANY,
            stdout=mock.ANY,
            stderr=mock.ANY,
            close_fds=mock.ANY,
            preexec_fn=mock.ANY)

        self.assertTrue(os.path.exists(logDir))
        self.assertTrue(os.path.isfile(logFile))
        _, kwargs = popenMock.call_args
        self.assertEqual(logFile, kwargs['stdout'].name)
        self.assertEqual(logFile, kwargs['stderr'].name)

        rqCore.network.reportRunningFrameCompletion.assert_called_with(
            rqd.compiled_proto.report_pb2.FrameCompleteReport(
                host=renderHost,
                frame=rqd.compiled_proto.report_pb2.RunningFrameInfo(
                    job_name=jobName, frame_id=frameId, frame_name=frameName),
                exit_status=returnCode))

    # TODO(bcipriano) Re-enable this test once Windows is supported. The main sticking point here
    #   is that the log directory is always overridden on Windows which makes mocking difficult.
    @mock.patch('platform.system', new=mock.Mock(return_value='Windows'))
    def disabled__test_runWindows(self, permsUser, timeMock, popenMock):
        currentTime = 1568070634.3
        jobTempPath = '/job/temp/path/'
        logDir = '/path/to/log/dir/'
        tempDir = 'C:\\temp'
        frameId = 'arbitrary-frame-id'
        jobId = 'arbitrary-job-id'
        jobName = 'arbitrary-job-name'
        frameName = 'arbitrary-frame-name'
        frameUid = 928
        frameUsername = 'my-random-user'
        returnCode = 0
        renderHost = rqd.compiled_proto.report_pb2.RenderHost(name='arbitrary-host-name')

        timeMock.return_value = currentTime
        popenMock.return_value.returncode = returnCode

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False

        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_id=jobId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            environment={'CUE_IFRAME': '2000'})
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        permsUser.assert_called_with(frameUid, mock.ANY)
        popenMock.assert_called_with(
            [tempDir + '/rqd-cmd-' + frameId + '-' + str(currentTime) + '.bat'],
            stdin=mock.ANY,
            stdout=mock.ANY,
            stderr=mock.ANY)
        # TODO(bcipriano) Verify the log directory was created and used for stdout/stderr.

        rqCore.network.reportRunningFrameCompletion.assert_called_with(
            rqd.compiled_proto.report_pb2.FrameCompleteReport(
                host=renderHost,
                frame=rqd.compiled_proto.report_pb2.RunningFrameInfo(
                    job_name=jobName, frame_id=frameId, frame_name=frameName),
                exit_status=returnCode))

    @mock.patch('platform.system', new=mock.Mock(return_value='Darwin'))
    @mock.patch('tempfile.gettempdir')
    def test_runDarwin(self, getTempDirMock, permsUser, timeMock, popenMock):
        # given
        currentTime = 1568070634.3
        jobTempPath = '/job/temp/path/'
        logDir = '/path/to/log/dir/'
        tempDir = '/some/random/temp/dir'
        frameId = 'arbitrary-frame-id'
        jobName = 'arbitrary-job-name'
        frameName = 'arbitrary-frame-name'
        frameUid = 928
        frameUsername = 'my-random-user'
        returnCode = 0
        renderHost = rqd.compiled_proto.report_pb2.RenderHost(name='arbitrary-host-name')
        logFile = os.path.join(logDir, '%s.%s.rqlog' % (jobName, frameName))

        self.fs.create_dir(tempDir)

        timeMock.return_value = currentTime
        getTempDirMock.return_value = tempDir
        popenMock.return_value.returncode = returnCode

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False

        runFrame = rqd.compiled_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir)
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        # when
        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        # then
        permsUser.assert_called_with(frameUid, mock.ANY)
        popenMock.assert_called_with(
            [
                '/usr/bin/su', frameUsername, '-c',
                '"' + tempDir + '/rqd-cmd-' + frameId + '-' + str(currentTime) + '"'
            ],
            env=mock.ANY,
            cwd=jobTempPath,
            stdin=mock.ANY,
            stdout=mock.ANY,
            stderr=mock.ANY,
            preexec_fn=mock.ANY)

        self.assertTrue(os.path.exists(logDir))
        self.assertTrue(os.path.isfile(logFile))
        _, kwargs = popenMock.call_args
        self.assertEqual(logFile, kwargs['stdout'].name)
        self.assertEqual(logFile, kwargs['stderr'].name)

        rqCore.network.reportRunningFrameCompletion.assert_called_with(
            rqd.compiled_proto.report_pb2.FrameCompleteReport(
                host=renderHost,
                frame=rqd.compiled_proto.report_pb2.RunningFrameInfo(
                    job_name=jobName, frame_id=frameId, frame_name=frameName),
                exit_status=returnCode))


if __name__ == '__main__':
    unittest.main()
