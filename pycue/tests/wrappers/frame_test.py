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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import mock
import time
import unittest

import opencue
from opencue.compiled_proto import depend_pb2
from opencue.compiled_proto import job_pb2


TEST_FRAME_NAME = 'testFrame'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class FrameTests(unittest.TestCase):

    def testEat(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Eat.return_value = job_pb2.FrameEatResponse()
        getStubMock.return_value = stubMock

        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.WAITING))
        frame.eat()

        stubMock.Eat.assert_called_with(
            job_pb2.FrameEatRequest(frame=frame.data), timeout=mock.ANY)

    def testKill(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Kill.return_value = job_pb2.FrameKillResponse()
        getStubMock.return_value = stubMock

        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        frame.kill()

        stubMock.Kill.assert_called_with(
            job_pb2.FrameKillRequest(frame=frame.data), timeout=mock.ANY)

    def testRetry(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Retry.return_value = job_pb2.FrameRetryResponse()
        getStubMock.return_value = stubMock

        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        frame.retry()

        stubMock.Retry.assert_called_with(
            job_pb2.FrameRetryRequest(frame=frame.data), timeout=mock.ANY)

    def testGetWhatDependsOnThis(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.GetWhatDependsOnThis.return_value = job_pb2.FrameGetWhatDependsOnThisResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        depends = frame.getWhatDependsOnThis()

        stubMock.GetWhatDependsOnThis.assert_called_with(
            job_pb2.FrameGetWhatDependsOnThisRequest(frame=frame.data), timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testGetWhatThisDependsOn(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.GetWhatThisDependsOn.return_value = job_pb2.FrameGetWhatThisDependsOnResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        depends = frame.getWhatThisDependsOn()

        stubMock.GetWhatThisDependsOn.assert_called_with(
            job_pb2.FrameGetWhatThisDependsOnRequest(frame=frame.data), timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testCreateDependencyOnFrame(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnFrame.return_value = \
            job_pb2.FrameCreateDependencyOnFrameResponse(depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        dependFrameName = 'frameDependTest'
        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME))
        dependOnFrame = job_pb2.Frame(name=dependFrameName)
        depend = frame.createDependencyOnFrame(dependOnFrame)

        stubMock.CreateDependencyOnFrame.assert_called_with(
            job_pb2.FrameCreateDependencyOnFrameRequest(frame=frame.data,
                                                        depend_on_frame=dependOnFrame),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateDependencyOnJob(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnJob.return_value = \
            job_pb2.FrameCreateDependencyOnJobResponse(depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        dependJobName = 'jobDependTest'
        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        dependOnJob = job_pb2.Job(name=dependJobName)
        depend = frame.createDependencyOnJob(dependOnJob)

        stubMock.CreateDependencyOnJob.assert_called_with(
            job_pb2.FrameCreateDependencyOnJobRequest(frame=frame.data, job=dependOnJob),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateDependencyOnLayer(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnLayer.return_value = \
            job_pb2.FrameCreateDependencyOnLayerResponse(depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        dependLayerName = 'layerDependTest'
        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        dependOnLayer = job_pb2.Layer(name=dependLayerName)
        depend = frame.createDependencyOnLayer(dependOnLayer)

        stubMock.CreateDependencyOnLayer.assert_called_with(
            job_pb2.FrameCreateDependencyOnLayerRequest(frame=frame.data, layer=dependOnLayer),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testMarkAsWaiting(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.MarkAsWaiting.return_value = job_pb2.FrameMarkAsWaitingResponse()
        getStubMock.return_value = stubMock

        frame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, state=job_pb2.RUNNING))
        frame.markAsWaiting()

        stubMock.MarkAsWaiting.assert_called_with(
            job_pb2.FrameMarkAsWaitingRequest(frame=frame.data), timeout=mock.ANY)

    def testRunTimeZero(self, getStubMock):
        zeroFrame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, start_time=0, stop_time=1000))
        self.assertEqual(zeroFrame.runTime(), 0)

    def testRunTimeRunning(self, getStubMock):
        curTime = int(time.time())
        startTime = 100
        expected = curTime - startTime
        runningFrame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, start_time=startTime, stop_time=0))
        threshold = abs(runningFrame.runTime() - expected)
        self.assertTrue(threshold < 1)

    def testRunTimeDone(self, getStubMock):
        startTime = 100
        stopTime = 500
        expected = stopTime - startTime
        runningFrame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=TEST_FRAME_NAME, start_time=startTime, stop_time=stopTime))
        self.assertEqual(runningFrame.runTime(), expected)


if __name__ == '__main__':
    unittest.main()
