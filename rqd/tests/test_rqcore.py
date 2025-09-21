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


"""Tests for rqd.rqcore."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
import os.path
import unittest
import subprocess

import mock
import pyfakefs.fake_filesystem_unittest

import opencue_proto.host_pb2
import opencue_proto.report_pb2
import opencue_proto.rqd_pb2
import rqd.rqconstants
import rqd.rqcore
import rqd.rqexceptions
import rqd.rqnetwork
import rqd.rqnimby


class RqCoreTests(unittest.TestCase):

    @mock.patch("rqd.rqnimby.Nimby", autospec=True)
    @mock.patch("rqd.rqnetwork.Network", autospec=True)
    @mock.patch("rqd.rqmachine.Machine", autospec=True)
    def setUp(self, machineMock, networkMock, nimbyMock):
        self.machineMock = machineMock
        self.networkMock = networkMock
        self.nimbyMock = nimbyMock
        self.rqcore = rqd.rqcore.RqCore()

    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOn")
    def test_startServer(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = False
        self.machineMock.return_value.isDesktop.return_value = False

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOn", autospec=True)
    def test_startServerWithNimby(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = True
        self.machineMock.return_value.isDesktop.return_value = False

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_called_with(self.rqcore)

    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOn", autospec=True)
    def test_startDesktopNimbyOn(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = True
        self.machineMock.return_value.isDesktop.return_value = True

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_called_with(self.rqcore)

    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOn")
    def test_startDesktopNimbyOff(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = False
        self.machineMock.return_value.isDesktop.return_value = True

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOn")
    def test_startDesktopNimbyUndefined(self, nimbyOnMock):
        rqd.rqconstants.OVERRIDE_NIMBY = None
        self.machineMock.return_value.isDesktop.return_value = True

        self.rqcore.start()

        self.networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch("rqd.rqnetwork.Network", autospec=True)
    @mock.patch("rqd.rqmachine.Machine", autospec=True)
    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOn")
    def test_startDesktopNimbyOffWithFlag(self, nimbyOnMock, machineMock, networkMock):
        rqd.rqconstants.OVERRIDE_NIMBY = True
        machineMock.return_value.isDesktop.return_value = True
        rqcore = rqd.rqcore.RqCore(optNimbyoff=True)

        rqcore.start()

        networkMock.return_value.start_grpc.assert_called()
        nimbyOnMock.assert_not_called()

    @mock.patch("threading.Timer")
    def test_grpcConnected(self, timerMock):
        update_rss_thread = mock.MagicMock()
        interval_thread = mock.MagicMock()
        timerMock.side_effect = [update_rss_thread, interval_thread]

        self.rqcore.grpcConnected()

        self.networkMock.return_value.reportRqdStartup.assert_called()
        update_rss_thread.start.assert_called()
        interval_thread.start.assert_called()

    @mock.patch.object(rqd.rqcore.RqCore, "sendStatusReport", autospec=True)
    @mock.patch("threading.Timer")
    def test_onInterval(self, timerMock, sendStatusReportMock):
        self.rqcore.onInterval()

        timerMock.return_value.start.assert_called()
        sendStatusReportMock.assert_called_with(self.rqcore)

    @mock.patch("threading.Timer", autospec=True)
    def test_onIntervalWithSleepTime(self, timerMock):
        sleep_time = 72

        self.rqcore.onInterval(sleepTime=sleep_time)

        timerMock.assert_called_with(sleep_time, mock.ANY)
        timerMock.return_value.start.assert_called()

    @mock.patch.object(rqd.rqcore.RqCore, "shutdownRqdNow")
    @mock.patch("threading.Timer", new=mock.MagicMock())
    def test_onIntervalShutdown(self, shutdownRqdNowMock):
        self.rqcore.shutdownRqdIdle()
        self.machineMock.return_value.isUserLoggedIn.return_value = False
        shutdownRqdNowMock.reset_mock()
        shutdownRqdNowMock.assert_not_called()

        self.rqcore.onInterval()

        shutdownRqdNowMock.assert_called_with()

    @mock.patch("threading.Timer")
    def test_updateRss(self, timerMock):
        self.rqcore.storeFrame(
            "frame-id", mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        )
        self.rqcore.backup_cache_path = None

        self.rqcore.updateRss()

        self.machineMock.return_value.rssUpdate.assert_called()
        timerMock.return_value.start.assert_called()

    def test_getFrame(self):
        frame_id = "arbitrary-frame-id"
        frame = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        self.rqcore.storeFrame(frame_id, frame)

        self.assertEqual(frame, self.rqcore.getFrame(frame_id))

    def test_getFrameKeys(self):
        frame_ids = ["frame1", "frame2"]
        self.rqcore.storeFrame(
            frame_ids[0], mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        )
        self.rqcore.storeFrame(
            frame_ids[1], mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        )

        self.assertEqual(set(frame_ids), set(self.rqcore.getFrameKeys()))

    def test_storeFrame(self):
        frame_id = "arbitrary-frame-id"
        frame = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        with self.assertRaises(KeyError):
            self.rqcore.getFrame(frame_id)

        self.rqcore.storeFrame(frame_id, frame)

        self.assertEqual(frame, self.rqcore.getFrame(frame_id))

    def test_storeFrameDuplicate(self):
        frame_id = "arbitrary-frame-id"
        self.rqcore.storeFrame(
            frame_id, mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        )

        with self.assertRaises(rqd.rqexceptions.RqdException):
            self.rqcore.storeFrame(
                frame_id, mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
            )

    def test_deleteFrame(self):
        frame_id = "arbitrary-frame-id"
        frame = mock.MagicMock(spec=rqd.rqnetwork.RunningFrame)
        self.rqcore.storeFrame(frame_id, frame)

        self.rqcore.deleteFrame(frame_id)
        self.rqcore.deleteFrame("unknown-key-should-succeed")

        with self.assertRaises(KeyError):
            self.rqcore.getFrame(frame_id)

    def test_killAllFrame(self):
        frameAttendantThread = mock.MagicMock()
        frameAttendantThread.is_alive.return_value = False
        frame1Id = "frame1"
        frame2Id = "frame2"
        frame3Id = "frame3"
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, opencue_proto.rqd_pb2.RunFrame(frame_id=frame1Id)
        )
        frame1.frameAttendantThread = frameAttendantThread
        frame2 = rqd.rqnetwork.RunningFrame(
            self.rqcore, opencue_proto.rqd_pb2.RunFrame(frame_id=frame2Id)
        )
        frame2.frameAttendantThread = frameAttendantThread
        frame3 = rqd.rqnetwork.RunningFrame(
            self.rqcore, opencue_proto.rqd_pb2.RunFrame(frame_id=frame3Id)
        )
        frame3.frameAttendantThread = frameAttendantThread
        self.rqcore.storeFrame(frame1Id, frame1)
        self.rqcore.storeFrame(frame2Id, frame2)
        self.rqcore.storeFrame(frame3Id, frame3)

        # There's no result to verify here; if the method completes successfully
        # it means that all frames were properly killed, as the method won't finish
        # until its frame cache is cleared by the kill process.
        self.rqcore.killAllFrame("arbitrary reason")

    def test_killAllFrameIgnoreNimby(self):
        frameAttendantThread = mock.MagicMock()
        frameAttendantThread.is_alive.return_value = False
        frame1Id = "frame1"
        frame2Id = "frame2"
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, opencue_proto.rqd_pb2.RunFrame(frame_id=frame1Id)
        )
        frame1.frameAttendantThread = frameAttendantThread
        frame2 = rqd.rqnetwork.RunningFrame(
            self.rqcore,
            opencue_proto.rqd_pb2.RunFrame(frame_id=frame2Id, ignore_nimby=True),
        )
        frame2.frameAttendantThread = frameAttendantThread
        self.rqcore.storeFrame(frame1Id, frame1)
        self.rqcore.storeFrame(frame2Id, frame2)

        self.rqcore.killAllFrame("NIMBY related reason")

        self.assertEqual(frame2, self.rqcore.getFrame(frame2Id))

    def test_releaseCores(self):
        num_idle_cores = 10
        num_booked_cores = 7
        num_cores_to_release = 5
        self.rqcore.cores = opencue_proto.report_pb2.CoreDetail(
            total_cores=50,
            idle_cores=num_idle_cores,
            locked_cores=2,
            booked_cores=num_booked_cores,
        )

        self.rqcore.releaseCores(num_cores_to_release)

        # pylint: disable=no-member
        self.assertEqual(
            num_booked_cores - num_cores_to_release, self.rqcore.cores.booked_cores
        )
        self.assertEqual(
            num_idle_cores + num_cores_to_release, self.rqcore.cores.idle_cores
        )

    @mock.patch.object(rqd.rqcore.RqCore, "nimbyOff")
    @mock.patch("os._exit")
    def test_shutdown(self, nimbyOffMock, exitMock):
        self.rqcore.onIntervalThread = mock.MagicMock()
        self.rqcore.updateRssThread = mock.MagicMock()

        self.rqcore.shutdown()

        nimbyOffMock.assert_called()
        self.rqcore.onIntervalThread.cancel.assert_called()
        self.rqcore.updateRssThread.cancel.assert_called()

    @mock.patch("rqd.rqnetwork.Network", autospec=True)
    @mock.patch("os._exit")
    def test_handleExit(self, networkMock, exitMock):
        self.rqcore = rqd.rqcore.RqCore()

        self.rqcore.handleExit(None, None)

        exitMock.assert_called()

    @mock.patch("rqd.rqcore.FrameAttendantThread")
    def test_launchFrame(self, frameThreadMock):
        self.rqcore.cores = opencue_proto.report_pb2.CoreDetail(
            total_cores=100, idle_cores=20
        )
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = opencue_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)
        rqd.rqconstants.OVERRIDE_NIMBY = None

        self.rqcore.launchFrame(frame)

        frameThreadMock.return_value.start.assert_called()

    def test_launchFrameOnDownHost(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.DOWN
        frame = opencue_proto.rqd_pb2.RunFrame()

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    @mock.patch("os._exit")
    def test_launchFrameOnHostWaitingForShutdown(self, exitMock):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.is_ready = False
        frame = opencue_proto.rqd_pb2.RunFrame()
        self.rqcore.shutdownRqdIdle()

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    @mock.patch("rqd.rqcore.FrameAttendantThread")
    def test_launchFrameOnNimbyHost(self, frameThreadMock):
        self.rqcore.cores = opencue_proto.report_pb2.CoreDetail(
            total_cores=100, idle_cores=20
        )
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        frame = opencue_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)
        frameIgnoreNimby = opencue_proto.rqd_pb2.RunFrame(
            uid=22, num_cores=10, ignore_nimby=True
        )
        self.rqcore.nimby = mock.create_autospec(rqd.rqnimby.Nimby)
        self.rqcore.nimby.locked = True

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

        self.rqcore.launchFrame(frameIgnoreNimby)

        frameThreadMock.return_value.start.assert_called()

    def test_launchDuplicateFrame(self):
        self.rqcore.cores = opencue_proto.report_pb2.CoreDetail(
            total_cores=100, idle_cores=20
        )
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frameId = "arbitrary-frame-id"
        self.rqcore.storeFrame(
            frameId, opencue_proto.rqd_pb2.RunFrame(frame_id=frameId)
        )
        frameToLaunch = opencue_proto.rqd_pb2.RunFrame(frame_id=frameId)
        rqd.rqconstants.OVERRIDE_NIMBY = None

        with self.assertRaises(rqd.rqexceptions.DuplicateFrameViolationException):
            self.rqcore.launchFrame(frameToLaunch)

    def test_launchFrameWithInvalidUid(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = opencue_proto.rqd_pb2.RunFrame(uid=0)

        with self.assertRaises(rqd.rqexceptions.InvalidUserException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameWithInvalidCoreCount(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = opencue_proto.rqd_pb2.RunFrame(uid=22, num_cores=0)

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameWithInsufficientCores(self):
        self.rqcore.cores = opencue_proto.report_pb2.CoreDetail(
            total_cores=100, idle_cores=5
        )
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        frame = opencue_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_getRunningFrame(self):
        frameId = "arbitrary-frame-id"
        frame = opencue_proto.rqd_pb2.RunFrame(frame_id=frameId)
        self.rqcore.storeFrame(frameId, frame)

        self.assertEqual(frame, self.rqcore.getRunningFrame(frameId))
        self.assertIsNone(self.rqcore.getRunningFrame("some-unknown-frame-id"))

    @mock.patch("os._exit")
    def test_rebootNowNoUser(self, exitMock):
        self.machineMock.return_value.isUserLoggedIn.return_value = False
        self.nimbyMock.return_value.is_ready = False

        self.rqcore.rebootNow()

        self.machineMock.return_value.reboot.assert_called_with()

    def test_rebootNowWithUser(self):
        self.machineMock.return_value.isUserLoggedIn.return_value = True

        with self.assertRaises(rqd.rqexceptions.RqdException):
            self.rqcore.rebootNow()

    @mock.patch("os._exit")
    def test_rebootIdleNoFrames(self, exitMock):
        self.machineMock.return_value.isUserLoggedIn.return_value = False
        self.nimbyMock.return_value.is_ready = False

        self.rqcore.rebootIdle()

        self.machineMock.return_value.reboot.assert_called_with()

    @mock.patch("os._exit")
    def test_rebootIdleWithFrames(self, exitMock):
        frame1Id = "frame1"
        frame1 = rqd.rqnetwork.RunningFrame(
            self.rqcore, opencue_proto.rqd_pb2.RunFrame(frame_id=frame1Id)
        )
        self.rqcore.storeFrame(frame1Id, frame1)

        self.rqcore.rebootIdle()

        self.assertTrue(self.rqcore.isWaitingForIdle())
        self.machineMock.return_value.reboot.assert_not_called()

    @mock.patch.object(rqd.rqcore.RqCore, "killAllFrame", autospec=True)
    def test_onNimbyLock(self, killAllFrameMock):
        self.rqcore.onNimbyLock()

        killAllFrameMock.assert_called_with(self.rqcore, mock.ANY)

    @mock.patch.object(rqd.rqcore.RqCore, "sendStatusReport", autospec=True)
    def test_onNimbyUnlock(self, sendStatusReportMock):
        self.rqcore.onNimbyUnlock()

        sendStatusReportMock.assert_called_with(self.rqcore)

    def test_lock(self):
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.lock(20)

        # pylint: disable=no-member
        self.assertEqual(20, self.rqcore.cores.idle_cores)
        self.assertEqual(30, self.rqcore.cores.locked_cores)

    def test_lockMoreCoresThanThereAre(self):
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.lock(100)

        # pylint: disable=no-member
        self.assertEqual(0, self.rqcore.cores.idle_cores)
        self.assertEqual(50, self.rqcore.cores.locked_cores)

    def test_lockAll(self):
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.lockAll()

        # pylint: disable=no-member
        self.assertEqual(0, self.rqcore.cores.idle_cores)
        self.assertEqual(50, self.rqcore.cores.locked_cores)

    def test_unlock(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 10
        self.rqcore.cores.locked_cores = 40

        self.rqcore.unlock(20)

        # pylint: disable=no-member
        self.assertEqual(30, self.rqcore.cores.idle_cores)
        self.assertEqual(20, self.rqcore.cores.locked_cores)

    def test_unlockMoreCoresThanThereAre(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.unlock(100)

        # pylint: disable=no-member
        self.assertEqual(50, self.rqcore.cores.idle_cores)
        self.assertEqual(0, self.rqcore.cores.locked_cores)

    def test_unlockAll(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = False
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10

        self.rqcore.unlockAll()

        # pylint: disable=no-member
        self.assertEqual(50, self.rqcore.cores.idle_cores)
        self.assertEqual(0, self.rqcore.cores.locked_cores)

    def test_unlockAllWhenNimbyLocked(self):
        self.machineMock.return_value.state = opencue_proto.host_pb2.UP
        self.nimbyMock.return_value.locked = True
        self.rqcore.cores.total_cores = 50
        self.rqcore.cores.idle_cores = 40
        self.rqcore.cores.locked_cores = 10
        self.rqcore.nimby.locked = True

        self.rqcore.unlockAll()

        # pylint: disable=no-member
        self.assertEqual(40, self.rqcore.cores.idle_cores)
        self.assertEqual(0, self.rqcore.cores.locked_cores)

    def test_sendFrameCompleteReport(self):
        logDir = "/path/to/log/dir/"
        frameId = "arbitrary-frame-id"
        jobName = "arbitrary-job-name"
        frameName = "arbitrary-frame-name"
        frameUid = 928
        frameUsername = "my-random-user"
        children = opencue_proto.report_pb2.ChildrenProcStats()
        returnCode = 0

        runFrame = opencue_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            children=children,
        )
        frameInfo = rqd.rqnetwork.RunningFrame(self.rqcore, runFrame)
        frameInfo.exitStatus = 0
        frameInfo.exitSignal = 0
        frameInfo.ignoreNimby = True

        renderHost = opencue_proto.report_pb2.RenderHost(
            name="arbitrary-host-name"
        )
        self.rqcore.machine.getHostInfo.return_value = renderHost
        self.rqcore.nimby = mock.MagicMock()
        self.rqcore.nimby.locked.return_value = False
        self.rqcore.network.reportRunningFrameCompletion = mock.MagicMock()
        self.rqcore.sendFrameCompleteReport(frameInfo)

        self.rqcore.network.reportRunningFrameCompletion.assert_called_once_with(
            opencue_proto.report_pb2.FrameCompleteReport(
                    host=renderHost,
                    frame=opencue_proto.report_pb2.RunningFrameInfo(
                        job_name=jobName,
                        frame_id=frameId,
                        frame_name=frameName,
                        children=children,
                    ),
                    exit_status=returnCode,
            )
        )


class RqCoreBackupTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.rqcore = rqd.rqcore.RqCore()
        self.setUpPyfakefs()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    def test_backupCache_withPath(self, mockOpen):
        """Test backupCache writes frame data when backup path is configured"""
        self.rqcore.backup_cache_path = '/tmp/rqd/cache.dat'
        frameId = 'frame123'
        runningFrame = mock.MagicMock()
        runningFrame.runFrame = mock.MagicMock()
        runningFrame.runFrame.SerializeToString.return_value = b'serialized_frame_data'
        self.rqcore.storeFrame(frameId, runningFrame)

        self.rqcore.backupCache()

        mockOpen.assert_called_once_with('/tmp/rqd/cache.dat', 'wb')
        handle = mockOpen()
        handle.write.assert_called_with(b'serialized_frame_data')

    def test_backupCache_noPath(self):
        """Test backupCache does nothing when no backup path configured"""
        self.rqcore.backup_cache_path = None
        frameId = 'frame123'
        runFrame = mock.MagicMock()
        self.rqcore.storeFrame(frameId, runFrame)

        self.rqcore.backupCache()

        runFrame.SerializeToString.assert_not_called()

    def test_recoverCache_noPath(self):
        """Test recoverCache does nothing when no backup path configured"""
        self.rqcore.backup_cache_path = None

        self.rqcore.recoverCache()

        self.assertEqual(len(self.rqcore._RqCore__cache), 0)

    @mock.patch('os.path.exists')
    def test_recoverCache_noFile(self, mockExists):
        """Test recoverCache does nothing when backup file doesn't exist"""
        self.rqcore.backup_cache_path = '/tmp/rqd/cache.dat'
        mockExists.return_value = False

        self.rqcore.recoverCache()

        self.assertEqual(len(self.rqcore._RqCore__cache), 0)

    @mock.patch('os.path.getmtime')
    @mock.patch('time.time')
    @mock.patch('os.path.exists')
    def test_recoverCache_expiredFile(self, mockExists, mockTime, mockGetmtime):
        """Test recoverCache does nothing when backup file is too old"""
        self.rqcore.backup_cache_path = '/tmp/rqd/cache.dat'
        mockExists.return_value = True
        mockTime.return_value = 1000
        mockGetmtime.return_value = 1 # Very old file

        self.rqcore.recoverCache()

        self.assertEqual(len(self.rqcore._RqCore__cache), 0)

    @mock.patch("rqd.rqcore.FrameAttendantThread", autospec=True)
    def test_recoverCache_validBackup(self, attendant_patch):
        """Test recoverCache skips frames that fail to parse"""
        self.rqcore.backup_cache_path = 'cache.dat'

        frameId = 'frame123'
        frame = opencue_proto.rqd_pb2.RunFrame(
            job_id = "job_id",
            job_name = "job_name",
            frame_id = frameId,
            frame_name = "frame_name",
            num_cores = 4
        )
        running_frame = rqd.rqnetwork.RunningFrame(self.rqcore, frame)
        self.rqcore.storeFrame(frameId, running_frame)
        self.rqcore.cores.idle_cores = 8
        self.rqcore.cores.booked_cores = 0
        self.rqcore.backupCache()
        self.rqcore._RqCore__cache = {}
        self.rqcore.recoverCache()
        self.assertEqual(4, self.rqcore.cores.idle_cores)
        self.assertEqual(4, self.rqcore.cores.booked_cores)

    def test_recoverCache_invalidFrame(self):
        """Test recoverCache loads frame data from valid backup file"""
        self.rqcore.backup_cache_path = 'cache.dat'
        with open(self.rqcore.backup_cache_path, "w", encoding='utf-8') as f:
            f.write("this is not a run frame")

        self.rqcore.recoverCache()

        self.assertNotIn('frame123', self.rqcore._RqCore__cache)

@mock.patch("rqd.rqutil.checkAndCreateUser", new=mock.MagicMock())
@mock.patch("rqd.rqutil.permissionsHigh", new=mock.MagicMock())
@mock.patch("rqd.rqutil.permissionsLow", new=mock.MagicMock())
@mock.patch("subprocess.Popen")
@mock.patch("time.time")
@mock.patch("rqd.rqutil.permissionsUser", spec=True)
class FrameAttendantThreadTests(pyfakefs.fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        rqd.rqconstants.SU_ARGUMENT = "-c"

    @mock.patch("platform.system", new=mock.Mock(return_value="Linux"))
    @mock.patch("tempfile.gettempdir")
    @mock.patch("select.poll")
    def test_runLinux(
        self, selectMock, getTempDirMock, permsUser, timeMock, popenMock
    ):  # mkdirMock, openMock,
        # given
        currentTime = 1568070634.3
        jobTempPath = "/job/temp/path/"
        logDir = "/path/to/log/dir/"
        tempDir = "/some/random/temp/dir"
        frameId = "arbitrary-frame-id"
        jobName = "arbitrary-job-name"
        frameName = "arbitrary-frame-name"
        frameUid = 928
        frameUsername = "my-random-user"
        returnCode = 0
        renderHost = opencue_proto.report_pb2.RenderHost(
            name="arbitrary-host-name"
        )
        logFile = os.path.join(logDir, "%s.%s.rqlog" % (jobName, frameName))

        self.fs.create_dir(tempDir)

        timeMock.return_value = currentTime
        getTempDirMock.return_value = tempDir

        popenMock.return_value.wait.return_value = returnCode
        popenMock.return_value.stdout.readline.return_value = None

        selectMock.return_value.poll.return_value = []

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False
        rqCore.docker_agent = None
        children = opencue_proto.report_pb2.ChildrenProcStats()

        runFrame = opencue_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            children=children,
        )
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        # when
        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        # then
        permsUser.assert_called_with(frameUid, mock.ANY)
        popenMock.assert_called_with(
            [
                "/bin/nice",
                "/usr/bin/time",
                "-p",
                "-o",
                jobTempPath + "rqd-stat-" + frameId + "-" + str(currentTime),
                tempDir + "/rqd-cmd-" + frameId + "-" + str(currentTime),
            ],
            env=mock.ANY,
            cwd=jobTempPath,
            stdin=mock.ANY,
            stdout=mock.ANY,
            stderr=mock.ANY,
            close_fds=mock.ANY,
            preexec_fn=mock.ANY,
        )

        self.assertTrue(os.path.exists(logDir))
        self.assertTrue(os.path.isfile(logFile))
        _, kwargs = popenMock.call_args

        rqCore.sendFrameCompleteReport.assert_called_with(
            frameInfo
        )

    @mock.patch('platform.system', new=mock.Mock(return_value='Linux'))
    @mock.patch('tempfile.gettempdir')
    def test_runDocker(self, getTempDirMock, permsUser, timeMock, popenMock):
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
        softLimit = 2000000000
        hardLimit = 5000000000
        renderHost = opencue_proto.report_pb2.RenderHost(name='arbitrary-host-name')
        logFile = os.path.join(logDir, '%s.%s.rqlog' % (jobName, frameName))

        self.fs.create_dir(tempDir)

        timeMock.return_value = currentTime
        getTempDirMock.return_value = tempDir

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False

        children = opencue_proto.report_pb2.ChildrenProcStats()

        # Test Valid memory limit
        runFrame = opencue_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            children=children,
            environment={"ENVVAR": "env_value"},
            os="centos7",
            soft_memory_limit=softLimit,
            hard_memory_limit=hardLimit)
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        # when
        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        # then
        cmd_file = os.path.join(tempDir, 'rqd-cmd-%s-%s' % (runFrame.frame_id, currentTime))
        rqCore.docker_agent.runContainer.assert_called_with(
            image_key="centos7",
            environment=mock.ANY,
            working_dir=jobTempPath,
            hostname=mock.ANY,
            mem_reservation=softLimit*1000,
            mem_limit=hardLimit*1000,
            entrypoint=cmd_file
        )

        self.assertTrue(os.path.exists(logDir))
        self.assertTrue(os.path.isfile(logFile))

        rqCore.sendFrameCompleteReport.assert_called_with(
            frameInfo
        )

        ### Test minimum memory limit
        runFrame = opencue_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            children=children,
            environment={"ENVVAR": "env_value"},
            os="centos7",
            soft_memory_limit=1,
            hard_memory_limit=2)
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        # when
        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        # then
        cmd_file = os.path.join(tempDir, 'rqd-cmd-%s-%s' % (runFrame.frame_id, currentTime))
        rqCore.docker_agent.runContainer.assert_called_with(
            image_key="centos7",
            environment=mock.ANY,
            working_dir=jobTempPath,
            hostname=mock.ANY,
            mem_reservation="1GB",
            mem_limit="2GB",
            entrypoint=cmd_file
        )


    # TODO(bcipriano) Re-enable this test once Windows is supported. The main sticking point here
    #   is that the log directory is always overridden on Windows which makes mocking difficult.
    @mock.patch("platform.system", new=mock.Mock(return_value="Windows"))
    def disabled__test_runWindows(self, permsUser, timeMock, popenMock):
        currentTime = 1568070634.3
        jobTempPath = "/job/temp/path/"
        logDir = "/path/to/log/dir/"
        tempDir = "C:\\temp"
        frameId = "arbitrary-frame-id"
        jobId = "arbitrary-job-id"
        jobName = "arbitrary-job-name"
        frameName = "arbitrary-frame-name"
        frameUid = 928
        frameUsername = "my-random-user"
        returnCode = 0
        renderHost = opencue_proto.report_pb2.RenderHost(
            name="arbitrary-host-name"
        )

        timeMock.return_value = currentTime
        popenMock.return_value.returncode = returnCode

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False
        children = opencue_proto.report_pb2.ChildrenProcStats()

        runFrame = opencue_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_id=jobId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            children=children,
            environment={"CUE_IFRAME": "2000"},
        )
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        permsUser.assert_called_with(frameUid, mock.ANY)
        popenMock.assert_called_with(
            [tempDir + "/rqd-cmd-" + frameId + "-" + str(currentTime) + ".bat"],
            stdin=mock.ANY,
            stdout=mock.ANY,
            stderr=mock.ANY,
        )
        # TODO(bcipriano) Verify the log directory was created and used for stdout/stderr.

        rqCore.network.reportRunningFrameCompletion.assert_called_with(
            opencue_proto.report_pb2.FrameCompleteReport(
                host=renderHost,
                frame=opencue_proto.report_pb2.RunningFrameInfo(
                    job_name=jobName,
                    frame_id=frameId,
                    frame_name=frameName,
                    children=children,
                ),
                exit_status=returnCode,
            )
        )

    @mock.patch("platform.system", new=mock.Mock(return_value="Darwin"))
    @mock.patch("tempfile.gettempdir")
    def test_runDarwin(self, getTempDirMock, permsUser, timeMock, popenMock):
        # given
        currentTime = 1568070634.3
        jobTempPath = "/job/temp/path/"
        logDir = "/path/to/log/dir/"
        tempDir = "/some/random/temp/dir"
        frameId = "arbitrary-frame-id"
        jobName = "arbitrary-job-name"
        frameName = "arbitrary-frame-name"
        frameUid = 928
        frameUsername = "my-random-user"
        returnCode = 0
        renderHost = opencue_proto.report_pb2.RenderHost(
            name="arbitrary-host-name"
        )
        logFile = os.path.join(logDir, "%s.%s.rqlog" % (jobName, frameName))

        self.fs.create_dir(tempDir)

        timeMock.return_value = currentTime
        getTempDirMock.return_value = tempDir
        popenMock.return_value.returncode = returnCode
        popenMock.return_value.stdout.readline.return_value = None

        rqCore = mock.MagicMock()
        rqCore.intervalStartTime = 20
        rqCore.intervalSleepTime = 40
        rqCore.machine.getTempPath.return_value = jobTempPath
        rqCore.machine.isDesktop.return_value = True
        rqCore.machine.getHostInfo.return_value = renderHost
        rqCore.nimby.locked = False
        rqCore.docker_agent = None
        children = opencue_proto.report_pb2.ChildrenProcStats()

        runFrame = opencue_proto.rqd_pb2.RunFrame(
            frame_id=frameId,
            job_name=jobName,
            frame_name=frameName,
            uid=frameUid,
            user_name=frameUsername,
            log_dir=logDir,
            children=children,
        )
        frameInfo = rqd.rqnetwork.RunningFrame(rqCore, runFrame)

        # when
        attendantThread = rqd.rqcore.FrameAttendantThread(rqCore, runFrame, frameInfo)
        attendantThread.start()
        attendantThread.join()

        # then
        permsUser.assert_called_with(frameUid, mock.ANY)
        popenMock.assert_called_with(
            [
                "/usr/bin/su",
                frameUsername,
                "-c",
                '"' + tempDir + "/rqd-cmd-" + frameId + "-" + str(currentTime) + '"',
            ],
            env=mock.ANY,
            cwd=jobTempPath,
            stdin=mock.ANY,
            stdout=mock.ANY,
            stderr=mock.ANY,
            preexec_fn=mock.ANY,
        )

        self.assertTrue(os.path.exists(logDir))
        self.assertTrue(os.path.isfile(logFile))
        _, kwargs = popenMock.call_args
        self.assertEqual(subprocess.PIPE, kwargs["stdout"])
        self.assertEqual(subprocess.STDOUT, kwargs["stderr"])

        rqCore.sendFrameCompleteReport.assert_called_with(
            frameInfo
        )


if __name__ == "__main__":
    unittest.main()
