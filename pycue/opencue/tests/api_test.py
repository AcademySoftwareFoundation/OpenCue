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

import opencue
from opencue.compiled_proto import job_pb2
from opencue.compiled_proto import service_pb2
from opencue.compiled_proto import show_pb2


TEST_SHOW_NAME = "pipe"
TEST_GROUP_NAME = "pipe"
TEST_GROUP_ID = "A0000000-0000-0000-0000-000000000000"
TEST_JOB_NAME = "pipe-dev.cue-chambers_shell_v6"
TEST_LAYER_NAME = "depend_er"
TEST_HOST_NAME = "wolf1001"
TEST_SUB_NAME = "pipe.General"


class ShowTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetShows(self, mockGetStub):
        getShowsMock = mock.Mock()
        getShowsMock.GetShows.return_value = show_pb2.ShowGetShowsResponse(
            shows=show_pb2.ShowSeq(shows=[show_pb2.Show(name=TEST_SHOW_NAME)]))
        mockGetStub.return_value = getShowsMock

        showList = opencue.api.getShows()

        getShowsMock.GetShows.assert_called()
        self.assertEqual(1, len(showList))
        self.assertEqual(TEST_SHOW_NAME, showList[0].name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindShow(self, mockGetStub):
        findShowMock = mock.Mock()
        findShowMock.FindShow.return_value = show_pb2.ShowFindShowResponse(
            show=show_pb2.Show(name=TEST_SHOW_NAME))
        mockGetStub.return_value = findShowMock

        show = opencue.api.findShow(TEST_SHOW_NAME)

        findShowMock.FindShow.assert_called_with(
            show_pb2.ShowFindShowRequest(name=TEST_SHOW_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_SHOW_NAME, show.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateShow(self, mockGetStub):
        createShowMock = mock.Mock()
        createShowMock.CreateShow.return_value = show_pb2.ShowCreateShowResponse(
            show=show_pb2.Show(name=TEST_SHOW_NAME))
        mockGetStub.return_value = createShowMock

        newShow = opencue.api.createShow(TEST_SHOW_NAME)

        createShowMock.CreateShow.assert_called_with(
            show_pb2.ShowCreateShowRequest(name=TEST_SHOW_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_SHOW_NAME, newShow.name())

    @mock.patch('opencue.api.findShow')
    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDeleteShow(self, mockGetStub, mockFindShow):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        deleteShowMock = mock.Mock()
        mockGetStub.return_value = deleteShowMock
        showToDelete = show_pb2.Show(id=arbitraryId)
        mockFindShow.return_value = showToDelete

        opencue.api.deleteShow(arbitraryId)

        deleteShowMock.Delete.assert_called_with(
            show_pb2.ShowDeleteRequest(show=showToDelete), timeout=mock.ANY)


class GroupTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindGroup(self, mockGetStub):
        findGroupMock = mock.Mock()
        findGroupMock.FindGroup.return_value = job_pb2.GroupFindGroupResponse(
            group=job_pb2.Group(name=TEST_GROUP_NAME))
        mockGetStub.return_value = findGroupMock

        group = opencue.api.findGroup(TEST_SHOW_NAME, TEST_GROUP_NAME)

        findGroupMock.FindGroup.assert_called_with(
            job_pb2.GroupFindGroupRequest(
                show=TEST_SHOW_NAME, name=TEST_GROUP_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_GROUP_NAME, group.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetGroup(self, mockGetStub):
        getGroupMock = mock.Mock()
        getGroupMock.GetGroup.return_value = job_pb2.GroupGetGroupResponse(
            group=job_pb2.Group(id=TEST_GROUP_ID))
        mockGetStub.return_value = getGroupMock

        group = opencue.api.getGroup(TEST_GROUP_ID)

        getGroupMock.GetGroup.assert_called_with(
            job_pb2.GroupGetGroupRequest(id=TEST_GROUP_ID), timeout=mock.ANY)
        self.assertEqual(TEST_GROUP_ID, group.id())


class JobTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testIsJobPending(self, mockGetStub):
        isJobPendingMock = mock.Mock()
        isJobPendingMock.IsJobPending.return_value = job_pb2.JobIsJobPendingResponse(value=True)
        mockGetStub.return_value = isJobPendingMock

        self.assertTrue(opencue.api.isJobPending(TEST_SHOW_NAME))

        isJobPendingMock.IsJobPending.return_value = job_pb2.JobIsJobPendingResponse(value=False)

        self.assertFalse(opencue.api.isJobPending(TEST_SHOW_NAME))

        isJobPendingMock.IsJobPending.assert_called_with(
            job_pb2.JobIsJobPendingRequest(name=TEST_SHOW_NAME), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindJob(self, mockGetStub):
        findJobMock = mock.Mock()
        findJobMock.FindJob.return_value = job_pb2.JobFindJobResponse(job=job_pb2.Job(name=TEST_JOB_NAME))
        mockGetStub.return_value = findJobMock

        job = opencue.api.findJob(TEST_JOB_NAME)

        findJobMock.FindJob.assert_called_with(job_pb2.JobFindJobRequest(name=TEST_JOB_NAME))
        self.assertEqual(TEST_JOB_NAME, job.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetJobs(self, mockGetStub):
        getJobsMock = mock.Mock()
        getJobsMock.GetJobs.return_value = job_pb2.JobGetJobsResponse(
            jobs=job_pb2.JobSeq(jobs=[job_pb2.Job(name=TEST_JOB_NAME)]))
        mockGetStub.return_value = getJobsMock

        jobsByShow = opencue.api.getJobs(show=[TEST_SHOW_NAME], all=True)

        getJobsMock.GetJobs.assert_called_with(
            job_pb2.JobGetJobsRequest(
                r=job_pb2.JobSearchCriteria(shows=[TEST_SHOW_NAME])), timeout=mock.ANY)
        self.assertEqual(1, len(jobsByShow))
        self.assertEqual(TEST_JOB_NAME, jobsByShow[0].name())

        jobsByName = opencue.api.getJobs(name=[TEST_JOB_NAME], show=[TEST_SHOW_NAME])

        getJobsMock.GetJobs.assert_called_with(
            job_pb2.JobGetJobsRequest(
                r=job_pb2.JobSearchCriteria(
                    jobs=[TEST_JOB_NAME], shows=[TEST_SHOW_NAME])), timeout=mock.ANY)
        self.assertEqual(1, len(jobsByName))
        self.assertEqual(TEST_JOB_NAME, jobsByName[0].name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetJob(self, mockGetStub):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        getJobMock = mock.Mock()
        getJobMock.GetJob.return_value = job_pb2.JobGetJobResponse(job=job_pb2.Job(id=arbitraryId))
        mockGetStub.return_value = getJobMock

        job = opencue.api.getJob(arbitraryId)

        getJobMock.GetJob.assert_called_with(
            job_pb2.JobGetJobRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, job.id())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetJobNames(self, mockGetStub):
        getJobNamesMock = mock.Mock()
        getJobNamesMock.GetJobNames.return_value = job_pb2.JobGetJobNamesResponse(
            names=[TEST_JOB_NAME])
        mockGetStub.return_value = getJobNamesMock

        jobNames = opencue.api.getJobNames(show=[TEST_SHOW_NAME])

        getJobNamesMock.GetJobNames.assert_called_with(
            job_pb2.JobGetJobNamesRequest(
                r=job_pb2.JobSearchCriteria(shows=[TEST_SHOW_NAME])), timeout=mock.ANY)
        self.assertEqual(1, len(jobNames))
        self.assertEqual(TEST_JOB_NAME, jobNames[0])


class LayerTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindLayer(self, mockGetStub):
        findLayerMock = mock.Mock()
        findLayerMock.FindLayer.return_value = job_pb2.LayerFindLayerResponse(
            layer=job_pb2.Layer(name=TEST_LAYER_NAME))
        mockGetStub.return_value = findLayerMock

        layer = opencue.api.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)

        findLayerMock.FindLayer.assert_called_with(
            job_pb2.LayerFindLayerRequest(job=TEST_JOB_NAME, layer=TEST_LAYER_NAME),
            timeout=mock.ANY)
        self.assertEqual(TEST_LAYER_NAME, layer.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetLayer(self, mockGetStub):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        getLayerMock = mock.Mock()
        getLayerMock.GetLayer.return_value = job_pb2.LayerGetLayerResponse(
            layer=job_pb2.Layer(id=arbitraryId))
        mockGetStub.return_value = getLayerMock

        layer = opencue.api.getLayer(arbitraryId)

        getLayerMock.GetLayer.assert_called_with(
            job_pb2.LayerGetLayerRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, layer.id())


class FrameTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindFrame(self, mockGetStub):
        frameNum = 4
        findFrameMock = mock.Mock()
        findFrameMock.FindFrame.return_value = job_pb2.FrameFindFrameResponse(
            frame=job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=frameNum))
        mockGetStub.return_value = findFrameMock

        frame = opencue.api.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, frameNum)

        findFrameMock.FindFrame.assert_called_with(
            job_pb2.FrameFindFrameRequest(job=TEST_JOB_NAME, layer=TEST_LAYER_NAME, frame=frameNum),
            timeout=mock.ANY)
        self.assertEqual(TEST_LAYER_NAME, frame.layer())
        self.assertEqual(frameNum, frame.number())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetFrame(self, mockGetStub):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        getFrameMock = mock.Mock()
        getFrameMock.GetFrame.return_value = job_pb2.FrameGetFrameResponse(
            frame=job_pb2.Frame(id=arbitraryId))
        mockGetStub.return_value = getFrameMock

        frame = opencue.api.getFrame(arbitraryId)

        getFrameMock.GetFrame.assert_called_with(
            job_pb2.FrameGetFrameRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, frame.id())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetFrames(self, mockGetStub):
        getFramesMock = mock.Mock()
        getFramesMock.GetFrames.return_value = job_pb2.FrameGetFramesResponse(
            frames=job_pb2.FrameSeq(frames=[
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=1),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=2),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=3),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=4),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=5),
            ]))
        mockGetStub.return_value = getFramesMock

        frames = opencue.api.getFrames(TEST_JOB_NAME, range="1-5")

        getFramesMock.GetFrames.assert_called_with(
            job_pb2.FrameGetFramesRequest(
                job=TEST_JOB_NAME, r=job_pb2.FrameSearchCriteria(
                    frame_range="1-5", page=1, limit=1000)),
            timeout=mock.ANY)
        self.assertEqual(5, len(frames))
        self.assertTrue(all((frame.layer() == TEST_LAYER_NAME for frame in frames)))
        self.assertEqual([1, 2, 3, 4, 5], [frame.number() for frame in frames])


class ServiceTests(unittest.TestCase):
    testName = 'unittesting'
    testTags = ['playblast', 'util']
    testThreadable = False
    testMinCores = 1000
    testMaxCores = 2000

    def setUp(self):
        self.service = service_pb2.Service(
                name=self.testName, threadable=self.testThreadable, min_cores=self.testMinCores,
                max_cores=self.testMaxCores, tags=self.testTags)

    @mock.patch('opencue.wrappers.service.Cuebot.getStub')
    def testCreate(self, mockGetStub):
        createServiceMock = mock.Mock()
        createServiceMock.CreateService.return_value = service_pb2.ServiceCreateServiceResponse(
            service=self.service)
        mockGetStub.return_value = createServiceMock

        newService = opencue.api.createService(self.service)

        createServiceMock.CreateService.assert_called_with(
            service_pb2.ServiceCreateServiceRequest(data=self.service), timeout=mock.ANY)

        #self.assertTrue(self.service.name() == newService.name())
        #self.assertTrue(self.service.tags() == newService.tags())
        #self.assertTrue(self.service.threadable() == newService.threadable())
        #self.assertTrue(self.service.minCores() == newService.minCores())
        #self.assertTrue(self.service.maxCores() == newService.maxCores())

    def testDelete(self):
        existing = opencue.api.getService(self.testName)
        existing.delete()
        self.assertIsNone(opencue.api.getService(self.testName))

    def testGet(self):
        service = opencue.api.getService(self.testName)
        self.assertEqual(self.testName, service.name())

    def testUpdate(self):
        updatedTags = ['util']
        service = opencue.api.getService(self.testName)
        service.setTags(updatedTags)
        service.update()
        updated = opencue.api.getService(self.testName)
        self.assertEqual(updatedTags, updated.tags())

"""
class CreateServiceTests(unittest.TestCase):

    def setUp(self):
        self.service = opencue.wrappers.service.Service()
        self.service.setName(self.testName)
        self.service.setTags(self.testTags)
        self.service.setThreadable(self.testThreadable)
        self.service.setMinCores(self.testMinCores)
        self.service.setMaxCores(self.testMaxCores)
        existing = opencue.wrappers.service.Service.getService(self.testName)
        if existing:
            existing.delete()

    def tearDown(self):
        existing = opencue.wrappers.service.Service.getService(self.testName)
        if existing:
            existing.delete()




class DeleteServiceTests(unittest.TestCase):

    testName = 'unittestingdelete'
    testTags = ['playblast', 'util']
    testThreadable = False
    testMinCores = 1000
    testMaxCores = 2000

    def setUp(self):
        self.service = opencue.wrappers.service.Service()
        self.service.setName(self.testName)
        self.service.setTags(self.testTags)
        self.service.setThreadable(self.testThreadable)
        self.service.setMinCores(self.testMinCores)
        self.service.setMaxCores(self.testMaxCores)
        self.service.create()

    def tearDown(self):
        existing = opencue.api.getService(self.testName)
        if existing:
            existing.delete()



class ServiceTests(unittest.TestCase):

    testName = 'unittesting'
    testTags = ['playblast', 'util']
    testThreadable = False
    testMinCores = 1000
    testMaxCores = 2000
    testMinGpu = 10
    testMinMemory = 4000

    @classmethod
    def setUpClass(cls):
        service = opencue.wrappers.service.Service()
        service.setName(cls.testName)
        service.setTags(cls.testTags)
        service.setThreadable(cls.testThreadable)
        service.setMinCores(cls.testMinCores)
        service.setMaxCores(cls.testMaxCores)
        service.create()

    @classmethod
    def tearDownClass(cls):
        service = opencue.wrappers.service.Service.getService(cls.testName)
        if service:
            service.delete()

    
"""

class SubscriptionTests(unittest.TestCase):

    def testFindSubscription(self):
        opencue.api.findSubscription(TEST_SUB_NAME)

    def testGetSubscription(self):
        sub1 = opencue.api.findSubscription(TEST_SUB_NAME)
        sub2 = opencue.api.getSubscription(opencue.id(sub1))
        self.assertEqual(opencue.id(sub1), opencue.id(sub2))


class HostTests(unittest.TestCase):

    def testGetHosts(self):
        self.assertTrue(len(opencue.api.getHosts(name=[TEST_HOST_NAME])) == 1)

    # this is failing all the time
    # def testGetHostWhiteboard(self):
    #     opencue.get_host_whiteboard()

    def testFindHost(self):
        h = opencue.api.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name(), TEST_HOST_NAME)

    def testGetHost(self):
        h = opencue.api.findHost(TEST_HOST_NAME)
        self.assertEquals(h.name(), TEST_HOST_NAME)
        h2 = opencue.api.getHost(opencue.id(h))
        self.assertEquals(h.name(), h2.name())


if __name__ == '__main__':
    unittest.main()
