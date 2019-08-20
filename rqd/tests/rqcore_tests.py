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


import mock
import unittest

import rqd.compiled_proto.host_pb2
import rqd.compiled_proto.report_pb2
import rqd.compiled_proto.rqd_pb2
import rqd.rqconstants
import rqd.rqcore
import rqd.rqexceptions
import rqd.rqnetwork
import rqd.rqnimby


class RqCoreTests(unittest.TestCase):

    @mock.patch('rqd.rqnetwork.Network', autospec=True)
    @mock.patch('rqd.rqmachine.Machine', autospec=True)
    def setUp(self, machineMock, networkMock):
        self.machineMock = machineMock
        self.networkMock = networkMock
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

    @mock.patch('sys.exit')
    def test_handleExit(self, exitMock):
        self.rqcore = rqd.rqcore.RqCore()

        self.rqcore.handleExit(None, None)

        exitMock.assert_called()

    @mock.patch('rqd.rqcore.FrameAttendantThread')
    def test_launchFrame(self, frameThreadMock):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=20)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
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
        self.rqcore.nimby = mock.create_autospec(rqd.rqnimby.Nimby)
        self.rqcore.nimby.locked = True

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

        self.rqcore.launchFrame(frameIgnoreNimby)

        frameThreadMock.return_value.start.assert_called()

    def test_launchDuplicateFrame(self):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=20)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        frameId = 'arbitrary-frame-id'
        self.rqcore.storeFrame(frameId, rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frameId))
        frameToLaunch = rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frameId)

        with self.assertRaises(rqd.rqexceptions.DuplicateFrameViolationException):
            self.rqcore.launchFrame(frameToLaunch)

    def test_launchFrameWithInvalidUid(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=0)

        with self.assertRaises(rqd.rqexceptions.InvalidUserException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameWithInvalidCoreCount(self):
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=22, num_cores=0)

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_launchFrameWithInsufficientCores(self):
        self.rqcore.cores = rqd.compiled_proto.report_pb2.CoreDetail(total_cores=100, idle_cores=5)
        self.machineMock.return_value.state = rqd.compiled_proto.host_pb2.UP
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(uid=22, num_cores=10)

        with self.assertRaises(rqd.rqexceptions.CoreReservationFailureException):
            self.rqcore.launchFrame(frame)

    def test_getRunningFrame(self):
        frameId = 'arbitrary-frame-id'
        frame = rqd.compiled_proto.rqd_pb2.RunFrame(frame_id=frameId)
        self.rqcore.storeFrame(frameId, frame)

        self.assertEqual(frame, self.rqcore.getRunningFrame(frameId))
        self.assertIsNone(self.rqcore.getRunningFrame('some-unknown-frame-id'))


if __name__ == '__main__':
    unittest.main()
