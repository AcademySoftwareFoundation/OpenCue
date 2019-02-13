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
from opencue.compiled_proto import host_pb2
from opencue.compiled_proto import job_pb2
from opencue.compiled_proto import service_pb2
from opencue.compiled_proto import show_pb2
from opencue.compiled_proto import subscription_pb2


TEST_SHOW_NAME = 'pipe'
TEST_GROUP_NAME = 'pipe'
TEST_GROUP_ID = 'A0000000-0000-0000-0000-000000000000'
TEST_JOB_NAME = 'pipe-dev.cue-chambers_shell_v6'
TEST_LAYER_NAME = 'depend_er'
TEST_HOST_NAME = 'wolf1001'
TEST_SUB_NAME = 'pipe.General'


class ShowTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetShows(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetShows.return_value = show_pb2.ShowGetShowsResponse(
            shows=show_pb2.ShowSeq(shows=[show_pb2.Show(name=TEST_SHOW_NAME)]))
        getStubMock.return_value = stubMock

        showList = opencue.api.getShows()

        stubMock.GetShows.assert_called()
        self.assertEqual(1, len(showList))
        self.assertEqual(TEST_SHOW_NAME, showList[0].name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindShow(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.FindShow.return_value = show_pb2.ShowFindShowResponse(
            show=show_pb2.Show(name=TEST_SHOW_NAME))
        getStubMock.return_value = stubMock

        show = opencue.api.findShow(TEST_SHOW_NAME)

        stubMock.FindShow.assert_called_with(
            show_pb2.ShowFindShowRequest(name=TEST_SHOW_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_SHOW_NAME, show.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateShow(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.CreateShow.return_value = show_pb2.ShowCreateShowResponse(
            show=show_pb2.Show(name=TEST_SHOW_NAME))
        getStubMock.return_value = stubMock

        newShow = opencue.api.createShow(TEST_SHOW_NAME)

        stubMock.CreateShow.assert_called_with(
            show_pb2.ShowCreateShowRequest(name=TEST_SHOW_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_SHOW_NAME, newShow.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDeleteShow(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        showToDelete = show_pb2.Show(id=arbitraryId)
        stubMock = mock.Mock()
        stubMock.FindShow.return_value = show_pb2.ShowFindShowResponse(show=showToDelete)
        stubMock.Delete.return_value = show_pb2.ShowDeleteResponse()
        getStubMock.return_value = stubMock

        opencue.api.deleteShow(arbitraryId)

        stubMock.Delete.assert_called_with(
            show_pb2.ShowDeleteRequest(show=showToDelete), timeout=mock.ANY)


class GroupTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.FindGroup.return_value = job_pb2.GroupFindGroupResponse(
            group=job_pb2.Group(name=TEST_GROUP_NAME))
        getStubMock.return_value = stubMock

        group = opencue.api.findGroup(TEST_SHOW_NAME, TEST_GROUP_NAME)

        stubMock.FindGroup.assert_called_with(
            job_pb2.GroupFindGroupRequest(
                show=TEST_SHOW_NAME, name=TEST_GROUP_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_GROUP_NAME, group.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetGroup.return_value = job_pb2.GroupGetGroupResponse(
            group=job_pb2.Group(id=TEST_GROUP_ID))
        getStubMock.return_value = stubMock

        group = opencue.api.getGroup(TEST_GROUP_ID)

        stubMock.GetGroup.assert_called_with(
            job_pb2.GroupGetGroupRequest(id=TEST_GROUP_ID), timeout=mock.ANY)
        self.assertEqual(TEST_GROUP_ID, group.id())


class JobTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testIsJobPending(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.IsJobPending.return_value = job_pb2.JobIsJobPendingResponse(value=True)
        getStubMock.return_value = stubMock

        self.assertTrue(opencue.api.isJobPending(TEST_SHOW_NAME))

        stubMock.IsJobPending.return_value = job_pb2.JobIsJobPendingResponse(value=False)

        self.assertFalse(opencue.api.isJobPending(TEST_SHOW_NAME))

        stubMock.IsJobPending.assert_called_with(
            job_pb2.JobIsJobPendingRequest(name=TEST_SHOW_NAME), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindJob(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.FindJob.return_value = job_pb2.JobFindJobResponse(job=job_pb2.Job(name=TEST_JOB_NAME))
        getStubMock.return_value = stubMock

        job = opencue.api.findJob(TEST_JOB_NAME)

        stubMock.FindJob.assert_called_with(
            job_pb2.JobFindJobRequest(name=TEST_JOB_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_JOB_NAME, job.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetJobs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetJobs.return_value = job_pb2.JobGetJobsResponse(
            jobs=job_pb2.JobSeq(jobs=[job_pb2.Job(name=TEST_JOB_NAME)]))
        getStubMock.return_value = stubMock

        jobsByShow = opencue.api.getJobs(show=[TEST_SHOW_NAME], all=True)

        stubMock.GetJobs.assert_called_with(
            job_pb2.JobGetJobsRequest(
                r=job_pb2.JobSearchCriteria(shows=[TEST_SHOW_NAME])), timeout=mock.ANY)
        self.assertEqual(1, len(jobsByShow))
        self.assertEqual(TEST_JOB_NAME, jobsByShow[0].name())

        jobsByName = opencue.api.getJobs(name=[TEST_JOB_NAME], show=[TEST_SHOW_NAME])

        stubMock.GetJobs.assert_called_with(
            job_pb2.JobGetJobsRequest(
                r=job_pb2.JobSearchCriteria(
                    jobs=[TEST_JOB_NAME], shows=[TEST_SHOW_NAME])), timeout=mock.ANY)
        self.assertEqual(1, len(jobsByName))
        self.assertEqual(TEST_JOB_NAME, jobsByName[0].name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetJob(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.GetJob.return_value = job_pb2.JobGetJobResponse(job=job_pb2.Job(id=arbitraryId))
        getStubMock.return_value = stubMock

        job = opencue.api.getJob(arbitraryId)

        stubMock.GetJob.assert_called_with(
            job_pb2.JobGetJobRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, job.id())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetJobNames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetJobNames.return_value = job_pb2.JobGetJobNamesResponse(
            names=[TEST_JOB_NAME])
        getStubMock.return_value = stubMock

        jobNames = opencue.api.getJobNames(show=[TEST_SHOW_NAME])

        stubMock.GetJobNames.assert_called_with(
            job_pb2.JobGetJobNamesRequest(
                r=job_pb2.JobSearchCriteria(shows=[TEST_SHOW_NAME])), timeout=mock.ANY)
        self.assertEqual(1, len(jobNames))
        self.assertEqual(TEST_JOB_NAME, jobNames[0])


class LayerTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindLayer(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.FindLayer.return_value = job_pb2.LayerFindLayerResponse(
            layer=job_pb2.Layer(name=TEST_LAYER_NAME))
        getStubMock.return_value = stubMock

        layer = opencue.api.findLayer(TEST_JOB_NAME, TEST_LAYER_NAME)

        stubMock.FindLayer.assert_called_with(
            job_pb2.LayerFindLayerRequest(job=TEST_JOB_NAME, layer=TEST_LAYER_NAME),
            timeout=mock.ANY)
        self.assertEqual(TEST_LAYER_NAME, layer.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetLayer(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.GetLayer.return_value = job_pb2.LayerGetLayerResponse(
            layer=job_pb2.Layer(id=arbitraryId))
        getStubMock.return_value = stubMock

        layer = opencue.api.getLayer(arbitraryId)

        stubMock.GetLayer.assert_called_with(
            job_pb2.LayerGetLayerRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, layer.id())


class FrameTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindFrame(self, getStubMock):
        frameNum = 4
        stubMock = mock.Mock()
        stubMock.FindFrame.return_value = job_pb2.FrameFindFrameResponse(
            frame=job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=frameNum))
        getStubMock.return_value = stubMock

        frame = opencue.api.findFrame(TEST_JOB_NAME, TEST_LAYER_NAME, frameNum)

        stubMock.FindFrame.assert_called_with(
            job_pb2.FrameFindFrameRequest(job=TEST_JOB_NAME, layer=TEST_LAYER_NAME, frame=frameNum),
            timeout=mock.ANY)
        self.assertEqual(TEST_LAYER_NAME, frame.layer())
        self.assertEqual(frameNum, frame.number())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetFrame(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.GetFrame.return_value = job_pb2.FrameGetFrameResponse(
            frame=job_pb2.Frame(id=arbitraryId))
        getStubMock.return_value = stubMock

        frame = opencue.api.getFrame(arbitraryId)

        stubMock.GetFrame.assert_called_with(
            job_pb2.FrameGetFrameRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, frame.id())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetFrames(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetFrames.return_value = job_pb2.FrameGetFramesResponse(
            frames=job_pb2.FrameSeq(frames=[
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=1),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=2),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=3),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=4),
                job_pb2.Frame(layer_name=TEST_LAYER_NAME, number=5),
            ]))
        getStubMock.return_value = stubMock

        frames = opencue.api.getFrames(TEST_JOB_NAME, range="1-5")

        stubMock.GetFrames.assert_called_with(
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

    @mock.patch.object(opencue.wrappers.service.Service, 'stub')
    def testCreate(self, stubMock):
        stubMock.CreateService.return_value = service_pb2.ServiceCreateServiceResponse(
            service=self.service)

        newService = opencue.api.createService(self.service)

        stubMock.CreateService.assert_called_with(
            service_pb2.ServiceCreateServiceRequest(data=self.service), timeout=mock.ANY)

        self.assertEqual(self.testName, newService.name())
        self.assertEqual(self.testTags, newService.tags())
        self.assertEqual(self.testThreadable, newService.threadable())
        self.assertEqual(self.testMinCores, newService.minCores())
        self.assertEqual(self.testMaxCores, newService.maxCores())

    @mock.patch.object(opencue.wrappers.service.Service, 'stub')
    def testDelete(self, stubMock):
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=self.service)
        stubMock.Delete.return_value = service_pb2.ServiceDeleteResponse()

        opencue.api.getService(self.testName).delete()

        stubMock.Delete.assert_called_with(
            service_pb2.ServiceDeleteRequest(service=self.service), timeout=mock.ANY)

    @mock.patch.object(opencue.wrappers.service.Service, 'stub')
    def testGet(self, stubMock):
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=self.service)

        service = opencue.api.getService(self.testName)

        stubMock.GetService.assert_called_with(
            service_pb2.ServiceGetServiceRequest(name=self.testName), timeout=mock.ANY)
        self.assertEqual(self.testName, service.name())

    @mock.patch.object(opencue.wrappers.service.Service, 'stub')
    def testUpdate(self, stubMock):
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=self.service)
        stubMock.Update.return_value = service_pb2.ServiceUpdateResponse()

        updatedService = opencue.api.getService(self.testName)
        updatedService.setTags(['util'])
        updatedService.update()

        stubMock.Update.assert_called_with(
            service_pb2.ServiceUpdateRequest(service=updatedService.data), timeout=mock.ANY)


class SubscriptionTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindSubscription(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = subscription_pb2.SubscriptionFindResponse(
            subscription=subscription_pb2.Subscription(name=TEST_SUB_NAME))
        getStubMock.return_value = stubMock

        sub = opencue.api.findSubscription(TEST_SUB_NAME)

        stubMock.Find.assert_called_with(
            subscription_pb2.SubscriptionFindRequest(name=TEST_SUB_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_SUB_NAME, sub.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetSubscription(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.Get.return_value = subscription_pb2.SubscriptionGetResponse(
            subscription=subscription_pb2.Subscription(id=arbitraryId))
        getStubMock.return_value = stubMock

        sub = opencue.api.getSubscription(arbitraryId)

        stubMock.Get.assert_called_with(
            subscription_pb2.SubscriptionGetRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, sub.id())


class HostTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetHosts(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetHosts.return_value = host_pb2.HostGetHostsResponse(
            hosts=host_pb2.HostSeq(hosts=[host_pb2.Host(name=TEST_HOST_NAME)]))
        getStubMock.return_value = stubMock

        hosts = opencue.api.getHosts(name=[TEST_HOST_NAME])

        stubMock.GetHosts.assert_called_with(
            host_pb2.HostGetHostsRequest(r=host_pb2.HostSearchCriteria(hosts=[TEST_HOST_NAME])),
            timeout=mock.ANY)
        self.assertEqual(1, len(hosts))
        self.assertEqual(TEST_HOST_NAME, hosts[0].name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindHost(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.FindHost.return_value = host_pb2.HostFindHostResponse(
            host=host_pb2.Host(name=TEST_HOST_NAME))
        getStubMock.return_value = stubMock

        host = opencue.api.findHost(TEST_HOST_NAME)

        stubMock.FindHost.assert_called_with(
            host_pb2.HostFindHostRequest(name=TEST_HOST_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_HOST_NAME, host.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetHost(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.GetHost.return_value = host_pb2.HostGetHostResponse(
            host=host_pb2.Host(id=arbitraryId))
        getStubMock.return_value = stubMock

        host = opencue.api.getHost(arbitraryId)

        stubMock.GetHost.assert_called_with(
            host_pb2.HostGetHostRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, host.id())


if __name__ == '__main__':
    unittest.main()
