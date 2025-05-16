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

"""Tests for `opencue.wrappers.job`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import getpass
import os
import platform
import unittest

import mock

from opencue_proto import comment_pb2
from opencue_proto import depend_pb2
from opencue_proto import job_pb2
import opencue.wrappers.frame
import opencue.wrappers.group
import opencue.wrappers.job
import opencue.wrappers.layer


TEST_JOB_NAME = 'testJob'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class JobTests(unittest.TestCase):

    def testKill(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = job_pb2.JobKillResponse()
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        username = getpass.getuser()
        pid = os.getpid()
        host_kill = platform.uname()[1]
        reason = "Job Kill Request"
        job.kill(username=username, pid=pid, host_kill=host_kill, reason=reason)

        stubMock.Kill.assert_called_with(
            job_pb2.JobKillRequest(job=job.data,
                                   username=username,
                                   pid=str(pid),
                                   host_kill=host_kill,
                                   reason=reason), timeout=mock.ANY)

    def testPause(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Pause.return_value = job_pb2.JobPauseResponse()
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.pause()

        stubMock.Pause.assert_called_with(
            job_pb2.JobPauseRequest(job=job.data), timeout=mock.ANY)

    def testResume(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Resume.return_value = job_pb2.JobResumeResponse()
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.resume()

        stubMock.Resume.assert_called_with(
            job_pb2.JobResumeRequest(job=job.data), timeout=mock.ANY)

    def testKillFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.KillFrames.return_value = job_pb2.JobKillFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        criteria = opencue.search.FrameSearch.criteriaFromOptions(range=frameRange)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        username = getpass.getuser()
        pid = os.getpid()
        host_kill = platform.uname()[1]
        reason = "Job Kill Request"
        job.killFrames(range=frameRange,
                       username=username,
                       pid=str(pid),
                       host_kill=host_kill,
                       reason=reason)

        stubMock.KillFrames.assert_called_with(
            job_pb2.JobKillFramesRequest(job=job.data,
                                         username=username,
                                         pid=str(pid),
                                         host_kill=host_kill,
                                         reason=reason,
                                         req=criteria), timeout=mock.ANY)

    def testEatFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.EatFrames.return_value = job_pb2.JobEatFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        criteria = opencue.search.FrameSearch.criteriaFromOptions(range=frameRange)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.eatFrames(range=frameRange)

        stubMock.EatFrames.assert_called_with(
            job_pb2.JobEatFramesRequest(job=job.data, req=criteria), timeout=mock.ANY)

    def testRetryFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.RetryFrames.return_value = job_pb2.JobRetryFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        criteria = opencue.search.FrameSearch.criteriaFromOptions(range=frameRange)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.retryFrames(range=frameRange)

        stubMock.RetryFrames.assert_called_with(
            job_pb2.JobRetryFramesRequest(job=job.data, req=criteria), timeout=mock.ANY)

    def testMarkdoneFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.MarkDoneFrames.return_value = job_pb2.JobMarkDoneFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        criteria = opencue.search.FrameSearch.criteriaFromOptions(range=frameRange)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.markdoneFrames(range=frameRange)

        stubMock.MarkDoneFrames.assert_called_with(
            job_pb2.JobMarkDoneFramesRequest(job=job.data, req=criteria), timeout=mock.ANY)

    def testMarkAsWaiting(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.MarkAsWaiting.return_value = job_pb2.JobMarkAsWaitingResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        criteria = opencue.search.FrameSearch.criteriaFromOptions(range=frameRange)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.markAsWaiting(range=frameRange)

        stubMock.MarkAsWaiting.assert_called_with(
            job_pb2.JobMarkAsWaitingRequest(job=job.data, req=criteria), timeout=mock.ANY)

    def testSetMinCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMinCores.return_value = job_pb2.JobSetMinCoresResponse()
        getStubMock.return_value = stubMock

        cores = 2000
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.setMinCores(cores)

        stubMock.SetMinCores.assert_called_with(
            job_pb2.JobSetMinCoresRequest(job=job.data, val=cores), timeout=mock.ANY)

    def testSetMaxCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMaxCores.return_value = job_pb2.JobSetMaxCoresResponse()
        getStubMock.return_value = stubMock

        cores = 2000
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.setMaxCores(cores)

        stubMock.SetMaxCores.assert_called_with(
            job_pb2.JobSetMaxCoresRequest(job=job.data, val=cores), timeout=mock.ANY)

    def testSetPriority(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetPriority.return_value = job_pb2.JobSetPriorityResponse()
        getStubMock.return_value = stubMock

        priority = 50
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.setPriority(priority)

        stubMock.SetPriority.assert_called_with(
            job_pb2.JobSetPriorityRequest(job=job.data, val=priority), timeout=mock.ANY)

    def testSetMaxRetries(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMaxRetries.return_value = job_pb2.JobSetMaxRetriesResponse()
        getStubMock.return_value = stubMock

        retries = 10
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.setMaxRetries(retries)

        stubMock.SetMaxRetries.assert_called_with(
            job_pb2.JobSetMaxRetriesRequest(job=job.data, max_retries=retries), timeout=mock.ANY)

    def testGetLayers(self, getStubMock):
        layerNames = ['testLayerA', 'testLayerB']
        stubMock = mock.Mock()
        stubMock.GetLayers.return_value = job_pb2.JobGetLayersResponse(
            layers=job_pb2.LayerSeq(layers=[job_pb2.Layer(name=layerNames[0]),
                                            job_pb2.Layer(name=layerNames[1])]))
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        layers = job.getLayers()

        stubMock.GetLayers.assert_called_with(
            job_pb2.JobGetLayersRequest(job=job.data), timeout=mock.ANY)
        self.assertTrue(len(layers), 2)
        self.assertTrue(layers[0].name(), layerNames[0])
        self.assertTrue(layers[1].name(), layerNames[1])

    def testGetFrames(self, getStubMock):
        frameNames = ['testFrameA', 'testFrameB']
        stubMock = mock.Mock()
        stubMock.GetFrames.return_value = job_pb2.JobGetFramesResponse(
            frames=job_pb2.FrameSeq(frames=[job_pb2.Frame(name=frameNames[0]),
                                            job_pb2.Frame(name=frameNames[1])]))
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        criteria = opencue.search.FrameSearch.criteriaFromOptions(range=frameRange)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        frames = job.getFrames(range=frameRange)

        stubMock.GetFrames.assert_called_with(
            job_pb2.JobGetFramesRequest(job=job.data, req=criteria), timeout=mock.ANY)
        self.assertTrue(len(frames), 2)
        self.assertTrue(frames[0].name(), frameNames[0])
        self.assertTrue(frames[1].name(), frameNames[1])

    def testGetUpdatedFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetUpdatedFrames.return_value = job_pb2.JobGetUpdatedFramesResponse(
            state=job_pb2.FINISHED,
            server_time=987654321,
            updated_frames=job_pb2.UpdatedFrameSeq(
                updated_frames=[job_pb2.UpdatedFrame(id='uuu-uuuu-uuu')]))
        getStubMock.return_value = stubMock

        lastCheck = 123456789
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        framesResponse = job.getUpdatedFrames(lastCheck)

        stubMock.GetUpdatedFrames.assert_called_with(
            job_pb2.JobGetUpdatedFramesRequest(job=job.data, last_check=lastCheck,
                                               layer_filter=None),
            timeout=mock.ANY)
        self.assertEqual(framesResponse.state, job_pb2.FINISHED)
        self.assertEqual(len(framesResponse.updated_frames.updated_frames), 1)

    def testSetAutoEating(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetAutoEat.return_value = job_pb2.JobSetAutoEatResponse()
        getStubMock.return_value = stubMock

        value = True
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.setAutoEating(value)

        stubMock.SetAutoEat.assert_called_with(
            job_pb2.JobSetAutoEatRequest(job=job.data, value=value), timeout=mock.ANY)

    def testGetWhatDependsOnThis(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.GetWhatDependsOnThis.return_value = job_pb2.JobGetWhatDependsOnThisResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        depends = job.getWhatDependsOnThis()

        stubMock.GetWhatDependsOnThis.assert_called_with(
            job_pb2.JobGetWhatDependsOnThisRequest(job=job.data), timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testGetWhatThisDependsOn(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.GetWhatThisDependsOn.return_value = job_pb2.JobGetWhatThisDependsOnResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        depends = job.getWhatThisDependsOn()

        stubMock.GetWhatThisDependsOn.assert_called_with(
            job_pb2.JobGetWhatThisDependsOnRequest(job=job.data), timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testGetDepends(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.GetDepends.return_value = job_pb2.JobGetDependsResponse(
            depends=depend_pb2.DependSeq(depends=[depend_pb2.Depend(id=dependId)]))
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        depends = job.getDepends()

        stubMock.GetDepends.assert_called_with(
            job_pb2.JobGetDependsRequest(job=job.data),
            timeout=mock.ANY)
        self.assertEqual(len(depends), 1)
        self.assertEqual(depends[0].id(), dependId)

    def testDropDepends(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.DropDepends.return_value = job_pb2.JobDropDependsResponse()
        getStubMock.return_value = stubMock

        target = depend_pb2.EXTERNAL
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.dropDepends(target)

        stubMock.DropDepends.assert_called_with(
            job_pb2.JobDropDependsRequest(job=job.data, target=target),
            timeout=mock.ANY)

    def testCreateDependencyOnJob(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnJob.return_value = job_pb2.JobCreateDependencyOnJobResponse(
            depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        onJob = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME+"Depend"))
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        depend = job.createDependencyOnJob(onJob)

        stubMock.CreateDependencyOnJob.assert_called_with(
            job_pb2.JobCreateDependencyOnJobRequest(job=job.data, on_job=onJob.data),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateDependencyOnLayer(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        dependLayer = 'testLayer'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnLayer.return_value = job_pb2.JobCreateDependencyOnLayerResponse(
            depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        onLayer = opencue.wrappers.layer.Layer(
            job_pb2.Layer(name=dependLayer))
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        depend = job.createDependencyOnLayer(onLayer)

        stubMock.CreateDependencyOnLayer.assert_called_with(
            job_pb2.JobCreateDependencyOnLayerRequest(job=job.data, layer=onLayer.data),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testCreateDependencyOnFrame(self, getStubMock):
        dependId = 'ddd-dddd-ddd'
        dependFrame = 'testFrame'
        stubMock = mock.Mock()
        stubMock.CreateDependencyOnFrame.return_value = job_pb2.JobCreateDependencyOnFrameResponse(
            depend=depend_pb2.Depend(id=dependId))
        getStubMock.return_value = stubMock

        onFrame = opencue.wrappers.frame.Frame(
            job_pb2.Frame(name=dependFrame))
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        depend = job.createDependencyOnFrame(onFrame)

        stubMock.CreateDependencyOnFrame.assert_called_with(
            job_pb2.JobCreateDependencyOnFrameRequest(job=job.data, frame=onFrame.data),
            timeout=mock.ANY)
        self.assertEqual(depend.id(), dependId)

    def testAddComment(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.AddComment.return_value = job_pb2.JobAddCommentResponse()
        getStubMock.return_value = stubMock

        subject = 'test'
        message = 'this is a test.'
        comment = comment_pb2.Comment(user=os.getenv('USER', 'unknown'), subject=subject,
                                      message=message, timestamp=0)
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.addComment(subject, message)

        stubMock.AddComment.assert_called_with(
            job_pb2.JobAddCommentRequest(job=job.data, new_comment=comment),
            timeout=mock.ANY)

    def testGetComments(self, getStubMock):
        message = 'this is a test.'
        stubMock = mock.Mock()
        stubMock.GetComments.return_value = job_pb2.JobGetCommentsResponse(
            comments=comment_pb2.CommentSeq(comments=[comment_pb2.Comment(message=message)]))
        getStubMock.return_value = stubMock

        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        comments = job.getComments()

        stubMock.GetComments.assert_called_with(
            job_pb2.JobGetCommentsRequest(job=job.data),
            timeout=mock.ANY)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0].message(), message)

    def testSetGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetGroup.return_value = job_pb2.JobSetGroupResponse()
        getStubMock.return_value = stubMock

        groupId = 'ggg-gggg-ggg'
        group = opencue.wrappers.group.Group(
            job_pb2.Group(id=groupId))
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.setGroup(group)

        stubMock.SetGroup.assert_called_with(
            job_pb2.JobSetGroupRequest(job=job.data, group_id=groupId),
            timeout=mock.ANY)

    def testReorderFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReorderFrames.return_value = job_pb2.JobReorderFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        order = job_pb2.REVERSE
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.reorderFrames(frameRange, order)

        stubMock.ReorderFrames.assert_called_with(
            job_pb2.JobReorderFramesRequest(job=job.data, range=frameRange, order=order),
            timeout=mock.ANY)

    def testStaggerFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.StaggerFrames.return_value = job_pb2.JobStaggerFramesResponse()
        getStubMock.return_value = stubMock

        frameRange = '1-10'
        stagger = 5
        job = opencue.wrappers.job.Job(
            job_pb2.Job(name=TEST_JOB_NAME))
        job.staggerFrames(frameRange, stagger)

        stubMock.StaggerFrames.assert_called_with(
            job_pb2.JobStaggerFramesRequest(job=job.data, range=frameRange, stagger=stagger),
            timeout=mock.ANY)

    def testFrameStateTotals(self, getStubMock):
        runningFrames = 10
        waitingFrames = 50
        succeededFrames = 30
        expected = {job_pb2.WAITING: waitingFrames,
                    job_pb2.RUNNING: runningFrames,
                    job_pb2.SUCCEEDED: succeededFrames,
                    job_pb2.CHECKPOINT: 0,
                    job_pb2.SETUP: 0,
                    job_pb2.EATEN: 0,
                    job_pb2.DEAD: 0,
                    job_pb2.DEPEND: 0}

        job = opencue.wrappers.job.Job(job_pb2.Job(
            name="frameStateTestJob",
            job_stats=job_pb2.JobStats(
                running_frames=runningFrames,
                waiting_frames=waitingFrames,
                succeeded_frames=succeededFrames)))

        frameStateTotals = job.frameStateTotals()
        self.assertEqual(frameStateTotals, expected)


@mock.patch('opencue.cuebot.Cuebot.getStub')
class NestedJobTests(unittest.TestCase):

    def testAsJob(self, getStubMock):
        jobId = 'nnn-nnnn-nnn'
        state = job_pb2.FINISHED
        name = 'testNestedJob'
        shot = 'shotname'
        show = 'showname'
        user = 'username'
        group = 'groupname'
        facility = 'facilityname'
        jobOs = 'os'
        uid = 12345
        priority = 14
        minCores = 5
        maxCores = 6
        logDir = '/path/to/logs'
        isPaused = False
        nestedJob = opencue.wrappers.job.NestedJob(
            job_pb2.NestedJob(id=jobId, state=state, name=name, shot=shot, show=show, user=user,
                              group=group, facility=facility, os=jobOs, uid=uid, priority=priority,
                              min_cores=minCores, max_cores=maxCores, log_dir=logDir,
                              is_paused=isPaused))
        job = opencue.wrappers.job.Job(
            job_pb2.Job(id=jobId, state=state, name=name, shot=shot, show=show, user=user,
                        group=group, facility=facility, os=jobOs, uid=uid, priority=priority,
                        min_cores=minCores, max_cores=maxCores, log_dir=logDir,
                        is_paused=isPaused))

        asJob = nestedJob.asJob()
        attrs = ['id', 'state', 'name', 'shot', 'show', 'user', 'group', 'facility', 'os', 'uid',
                 'priority', 'minCores', 'maxCores', 'logDir', 'isPaused']
        for attr in attrs:
            self.assertEqual(getattr(job, attr)(), getattr(asJob, attr)())
            self.assertEqual(getattr(nestedJob, attr)(), getattr(asJob, attr)())


class JobEnumTests(unittest.TestCase):

    def testJobState(self):
        self.assertEqual(opencue.api.Job.JobState.PENDING, job_pb2.PENDING)
        self.assertEqual(opencue.api.Job.JobState.PENDING, 0)


if __name__ == '__main__':
    unittest.main()
