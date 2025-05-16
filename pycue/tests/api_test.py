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

"""Tests for `opencue.api`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import cue_pb2
from opencue_proto import depend_pb2
from opencue_proto import facility_pb2
from opencue_proto import filter_pb2
from opencue_proto import host_pb2
from opencue_proto import job_pb2
from opencue_proto import limit_pb2
from opencue_proto import service_pb2
from opencue_proto import show_pb2
from opencue_proto import subscription_pb2
import opencue.api


TEST_SHOW_NAME = 'pipe'
TEST_GROUP_NAME = 'pipe'
TEST_GROUP_ID = 'A0000000-0000-0000-0000-000000000000'
TEST_JOB_NAME = 'pipe-dev.cue-chambers_shell_v6'
TEST_LAYER_NAME = 'depend_er'
TEST_LIMIT_NAME = 'test-limit'
TEST_HOST_NAME = 'wolf1001'
TEST_SUB_NAME = 'pipe.General'
TEST_FACILITY_NAME = 'arbitrary-facility-name'
TEST_TAG = 'General'
TEST_ALLOC_NAME = 'pipe.General'
TEST_PROC_NAME = 'arbitrary-proc-name'



class ShowTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetShows(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetShows.return_value = show_pb2.ShowGetShowsResponse(
            shows=show_pb2.ShowSeq(shows=[show_pb2.Show(name=TEST_SHOW_NAME)]))
        getStubMock.return_value = stubMock

        showList = opencue.api.getShows()

        stubMock.GetShows.assert_called_with(show_pb2.ShowGetShowsRequest(), timeout=mock.ANY)
        self.assertEqual([TEST_SHOW_NAME], [show.name() for show in showList])

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

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetActiveShows(self, getStubMock):
        show1Name = 'first-show'
        show2Name = 'second-show'
        stubMock = mock.Mock()
        stubMock.GetActiveShows.return_value = show_pb2.ShowGetActiveShowsResponse(
            shows=show_pb2.ShowSeq(
                shows=[show_pb2.Show(name=show1Name), show_pb2.Show(name=show2Name)]))
        getStubMock.return_value = stubMock

        showList = opencue.api.getActiveShows()

        stubMock.GetActiveShows.assert_called_with(
            show_pb2.ShowGetActiveShowsRequest(), timeout=mock.ANY)
        self.assertEqual([show1Name, show2Name], [show.name() for show in showList])


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
        stubMock.FindJob.return_value = job_pb2.JobFindJobResponse(
            job=job_pb2.Job(name=TEST_JOB_NAME))
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

        jobsByShow = opencue.api.getJobs(show=[TEST_SHOW_NAME])

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
    def testGetAllJobs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetJobs.return_value = job_pb2.JobGetJobsResponse(
            jobs=job_pb2.JobSeq(jobs=[job_pb2.Job(name=TEST_JOB_NAME)]))
        getStubMock.return_value = stubMock

        jobs = opencue.api.getJobs()

        stubMock.GetJobs.assert_called_with(
            job_pb2.JobGetJobsRequest(
                r=job_pb2.JobSearchCriteria()), timeout=mock.ANY)
        self.assertEqual(1, len(jobs))
        self.assertEqual(TEST_JOB_NAME, jobs[0].name())

    def testRaiseExceptionOnBadCriteriaSearch(self):
        with self.assertRaises(Exception) as context:
            opencue.api.getJobs(bad_criteria=["00000000-0000-0000-0000-012345678980"])

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

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testLaunchSpec(self, getStubMock):
        spec = 'arbitrary-spec'
        stubMock = mock.Mock()
        stubMock.LaunchSpec.return_value = job_pb2.JobLaunchSpecResponse(
            names=[TEST_JOB_NAME])
        getStubMock.return_value = stubMock

        jobNames = opencue.api.launchSpec(spec)

        stubMock.LaunchSpec.assert_called_with(
            job_pb2.JobLaunchSpecRequest(spec=spec), timeout=mock.ANY)
        self.assertEqual([TEST_JOB_NAME], jobNames)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testLaunchSpecAndWait(self, getStubMock):
        spec = 'arbitrary-spec'
        stubMock = mock.Mock()
        stubMock.LaunchSpecAndWait.return_value = job_pb2.JobLaunchSpecAndWaitResponse(
            jobs=job_pb2.JobSeq(jobs=[job_pb2.Job(name=TEST_JOB_NAME)]))
        getStubMock.return_value = stubMock

        jobs = opencue.api.launchSpecAndWait(spec)

        stubMock.LaunchSpecAndWait.assert_called_with(
            job_pb2.JobLaunchSpecAndWaitRequest(spec=spec), timeout=mock.ANY)
        self.assertEqual([TEST_JOB_NAME], [job.name() for job in jobs])


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
        framePageLimit = opencue.api.search.FrameSearch.limit

        stubMock.GetFrames.assert_called_with(
            job_pb2.FrameGetFramesRequest(
                job=TEST_JOB_NAME, r=job_pb2.FrameSearchCriteria(
                    frame_range="1-5", page=1, limit=framePageLimit)),
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
    minMemoryIncrease = 2068378

    def setUp(self):
        self.service = service_pb2.Service(
                name=self.testName, threadable=self.testThreadable, min_cores=self.testMinCores,
                max_cores=self.testMaxCores, tags=self.testTags,
                min_memory_increase=self.minMemoryIncrease)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreate(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.CreateService.return_value = service_pb2.ServiceCreateServiceResponse(
            service=self.service)
        getStubMock.return_value = stubMock

        newService = opencue.api.createService(self.service)

        stubMock.CreateService.assert_called_with(
            service_pb2.ServiceCreateServiceRequest(data=self.service), timeout=mock.ANY)

        self.assertEqual(self.testName, newService.name())
        self.assertEqual(self.testTags, newService.tags())
        self.assertEqual(self.testThreadable, newService.threadable())
        self.assertEqual(self.testMinCores, newService.minCores())
        self.assertEqual(self.testMaxCores, newService.maxCores())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=self.service)
        stubMock.Delete.return_value = service_pb2.ServiceDeleteResponse()
        getStubMock.return_value = stubMock

        opencue.api.getService(self.testName).delete()

        stubMock.Delete.assert_called_with(
            service_pb2.ServiceDeleteRequest(service=self.service), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGet(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=self.service)
        getStubMock.return_value = stubMock

        service = opencue.api.getService(self.testName)

        stubMock.GetService.assert_called_with(
            service_pb2.ServiceGetServiceRequest(name=self.testName), timeout=mock.ANY)
        self.assertEqual(self.testName, service.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testUpdate(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=self.service)
        stubMock.Update.return_value = service_pb2.ServiceUpdateResponse()
        getStubMock.return_value = stubMock

        updatedService = opencue.api.getService(self.testName)
        updatedService.setTags(['util'])
        updatedService.update()

        stubMock.Update.assert_called_with(
            service_pb2.ServiceUpdateRequest(service=updatedService.data), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetDefault(self, getStubMock):
        stubMock = mock.Mock()
        service1 = 'service1'
        service2 = 'service2'
        stubMock.GetDefaultServices.return_value = service_pb2.ServiceGetDefaultServicesResponse(
            services=service_pb2.ServiceSeq(
                services=[service_pb2.Service(name=service1), service_pb2.Service(name=service2)]))
        getStubMock.return_value = stubMock

        services = opencue.api.getDefaultServices()

        stubMock.GetDefaultServices.assert_called_with(
            service_pb2.ServiceGetDefaultServicesRequest(), timeout=mock.ANY)
        self.assertEqual([service1, service2], [service.name() for service in services])


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

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetHostWhiteboard(self, getStubMock):
        hostId1 = 'host-one'
        hostId2 = 'host-two'
        stubMock = mock.Mock()
        stubMock.GetHostWhiteboard.return_value = host_pb2.HostGetHostWhiteboardResponse(
            nested_hosts=host_pb2.NestedHostSeq(
                nested_hosts=[host_pb2.NestedHost(id=hostId1), host_pb2.NestedHost(id=hostId2)]))
        getStubMock.return_value = stubMock

        hosts = opencue.api.getHostWhiteboard()

        stubMock.GetHostWhiteboard.assert_called_with(
            host_pb2.HostGetHostWhiteboardRequest(), timeout=mock.ANY)
        self.assertEqual([hostId1, hostId2], [host.id() for host in hosts])


class SystemTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetHost(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetSystemStats.return_value = cue_pb2.CueGetSystemStatsResponse()
        getStubMock.return_value = stubMock

        opencue.api.getSystemStats()

        stubMock.GetSystemStats.assert_called_with(
            cue_pb2.CueGetSystemStatsRequest(), timeout=mock.ANY)

class FacilityTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateFacility(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Create.return_value = facility_pb2.FacilityCreateResponse(
            facility=facility_pb2.Facility(name=TEST_FACILITY_NAME))
        getStubMock.return_value = stubMock

        newFacility = opencue.api.createFacility(TEST_FACILITY_NAME)

        stubMock.Create.assert_called_with(
            facility_pb2.FacilityCreateRequest(name=TEST_FACILITY_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_FACILITY_NAME, newFacility.name)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetFacility(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Get.return_value = facility_pb2.FacilityGetResponse(
            facility=facility_pb2.Facility(name=TEST_FACILITY_NAME))
        getStubMock.return_value = stubMock

        facility = opencue.api.getFacility(TEST_FACILITY_NAME)

        stubMock.Get.assert_called_with(
            facility_pb2.FacilityGetRequest(name=TEST_FACILITY_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_FACILITY_NAME, facility.name)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testRenameFacility(self, getStubMock):
        facility = facility_pb2.Facility(name=TEST_FACILITY_NAME)
        newName = 'new-name'
        stubMock = mock.Mock()
        stubMock.Rename.return_value = facility_pb2.FacilityRenameResponse()
        getStubMock.return_value = stubMock

        opencue.api.renameFacility(facility, newName)

        stubMock.Rename.assert_called_with(
            facility_pb2.FacilityRenameRequest(facility=facility, new_name=newName),
            timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDeleteFacility(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = facility_pb2.FacilityDeleteResponse()
        getStubMock.return_value = stubMock

        opencue.api.deleteFacility(TEST_FACILITY_NAME)

        stubMock.Delete.assert_called_with(
            facility_pb2.FacilityDeleteRequest(name=TEST_FACILITY_NAME), timeout=mock.ANY)


class DependTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetDepend(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.GetDepend.return_value = depend_pb2.DependGetDependResponse(
            depend=depend_pb2.Depend(id=arbitraryId))
        getStubMock.return_value = stubMock

        depend = opencue.api.getDepend(arbitraryId)

        stubMock.GetDepend.assert_called_with(
            depend_pb2.DependGetDependRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, depend.id())


class OwnerTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetOwner(self, getStubMock):
        ownerName = 'arbitrary-name'
        stubMock = mock.Mock()
        stubMock.GetOwner.return_value = host_pb2.OwnerGetOwnerResponse(
            owner=host_pb2.Owner(name=ownerName))
        getStubMock.return_value = stubMock

        owner = opencue.api.getOwner(ownerName)

        stubMock.GetOwner.assert_called_with(
            host_pb2.OwnerGetOwnerRequest(name=ownerName), timeout=mock.ANY)
        self.assertEqual(ownerName, owner.name())


class FilterTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindFilter(self, getStubMock):
        filterName = 'arbitrary-name'
        stubMock = mock.Mock()
        stubMock.FindFilter.return_value = filter_pb2.FilterFindFilterResponse(
            filter=filter_pb2.Filter(name=filterName))
        getStubMock.return_value = stubMock

        filterReturned = opencue.api.findFilter(TEST_SHOW_NAME, filterName)

        stubMock.FindFilter.assert_called_with(
            filter_pb2.FilterFindFilterRequest(show=TEST_SHOW_NAME, name=filterName),
            timeout=mock.ANY)
        self.assertEqual(filterName, filterReturned.name())


class AllocTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateAlloc(self, getStubMock):
        facility = facility_pb2.Facility(name=TEST_FACILITY_NAME)
        stubMock = mock.Mock()
        stubMock.Create.return_value = facility_pb2.AllocCreateResponse(
            allocation=facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        getStubMock.return_value = stubMock

        alloc = opencue.api.createAllocation(TEST_ALLOC_NAME, TEST_TAG, facility)

        stubMock.Create.assert_called_with(
            facility_pb2.AllocCreateRequest(name=TEST_ALLOC_NAME, tag=TEST_TAG, facility=facility),
            timeout=mock.ANY)
        self.assertEqual(TEST_ALLOC_NAME, alloc.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetAllocs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetAll.return_value = facility_pb2.AllocGetAllResponse(
            allocations=facility_pb2.AllocationSeq(
                allocations=[facility_pb2.Allocation(name=TEST_ALLOC_NAME)]))
        getStubMock.return_value = stubMock

        allocs = opencue.api.getAllocations()

        stubMock.GetAll.assert_called_with(
            facility_pb2.AllocGetAllRequest(), timeout=mock.ANY)
        self.assertEqual([TEST_ALLOC_NAME], [alloc.name() for alloc in allocs])

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindAlloc(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = facility_pb2.AllocFindResponse(
            allocation=facility_pb2.Allocation(name=TEST_ALLOC_NAME))
        getStubMock.return_value = stubMock

        alloc = opencue.api.findAllocation(TEST_ALLOC_NAME)

        stubMock.Find.assert_called_with(
            facility_pb2.AllocFindRequest(name=TEST_ALLOC_NAME), timeout=mock.ANY)
        self.assertEqual(TEST_ALLOC_NAME, alloc.name())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetAlloc(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.Get.return_value = facility_pb2.AllocGetResponse(
            allocation=facility_pb2.Allocation(id=arbitraryId))
        getStubMock.return_value = stubMock

        alloc = opencue.api.getAllocation(arbitraryId)

        stubMock.Get.assert_called_with(
            facility_pb2.AllocGetRequest(id=arbitraryId), timeout=mock.ANY)
        self.assertEqual(arbitraryId, alloc.id())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testDeleteAlloc(self, getStubMock):
        allocToDelete = facility_pb2.Allocation(name=TEST_ALLOC_NAME)
        stubMock = mock.Mock()
        stubMock.Delete.return_value = facility_pb2.AllocDeleteResponse()
        getStubMock.return_value = stubMock

        opencue.api.deleteAllocation(allocToDelete)

        stubMock.Delete.assert_called_with(
            facility_pb2.AllocDeleteRequest(allocation=allocToDelete), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetDefaultAlloc(self, getStubMock):
        arbitraryId = '00000000-0000-0000-0000-012345678980'
        stubMock = mock.Mock()
        stubMock.GetDefault.return_value = facility_pb2.AllocGetDefaultResponse(
            allocation=facility_pb2.Allocation(id=arbitraryId))
        getStubMock.return_value = stubMock

        alloc = opencue.api.getDefaultAllocation()

        stubMock.GetDefault.assert_called_with(
            facility_pb2.AllocGetDefaultRequest(), timeout=mock.ANY)
        self.assertEqual(arbitraryId, alloc.id())

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testSetDefaultAlloc(self, getStubMock):
        alloc = facility_pb2.Allocation(name=TEST_ALLOC_NAME)
        stubMock = mock.Mock()
        stubMock.SetDefault.return_value = facility_pb2.AllocSetDefaultResponse()
        getStubMock.return_value = stubMock

        opencue.api.setDefaultAllocation(alloc)

        stubMock.SetDefault.assert_called_with(
            facility_pb2.AllocSetDefaultRequest(allocation=alloc), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testAllocSetBillable(self, getStubMock):
        alloc = facility_pb2.Allocation(name=TEST_ALLOC_NAME)
        isBillable = True
        stubMock = mock.Mock()
        stubMock.SetBillable.return_value = facility_pb2.AllocSetBillableResponse()
        getStubMock.return_value = stubMock

        opencue.api.allocSetBillable(alloc, isBillable)

        stubMock.SetBillable.assert_called_with(
            facility_pb2.AllocSetBillableRequest(allocation=alloc, value=isBillable),
            timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testAllocSetName(self, getStubMock):
        alloc = facility_pb2.Allocation(name=TEST_ALLOC_NAME)
        newName = 'arbitrary-name'
        stubMock = mock.Mock()
        stubMock.SetName.return_value = facility_pb2.AllocSetNameResponse()
        getStubMock.return_value = stubMock

        opencue.api.allocSetName(alloc, newName)

        stubMock.SetName.assert_called_with(
            facility_pb2.AllocSetNameRequest(allocation=alloc, name=newName), timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testAllocSetTag(self, getStubMock):
        alloc = facility_pb2.Allocation(name=TEST_ALLOC_NAME)
        newTag = 'arbitrary-tag'
        stubMock = mock.Mock()
        stubMock.SetTag.return_value = facility_pb2.AllocSetTagResponse()
        getStubMock.return_value = stubMock

        opencue.api.allocSetTag(alloc, newTag)

        stubMock.SetTag.assert_called_with(
            facility_pb2.AllocSetTagRequest(allocation=alloc, tag=newTag), timeout=mock.ANY)


class ProcTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetProcs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetProcs.return_value = host_pb2.ProcGetProcsResponse(
            procs=host_pb2.ProcSeq(procs=[host_pb2.Proc(name=TEST_PROC_NAME)]))
        getStubMock.return_value = stubMock

        procs = opencue.api.getProcs(show=[TEST_SHOW_NAME], alloc=[TEST_ALLOC_NAME])

        stubMock.GetProcs.assert_called_with(
            host_pb2.ProcGetProcsRequest(
                r=host_pb2.ProcSearchCriteria(shows=[TEST_SHOW_NAME], allocs=[TEST_ALLOC_NAME])),
            timeout=mock.ANY)
        self.assertEqual([TEST_PROC_NAME], [proc.name() for proc in procs])


class LimitTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testCreateLimit(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Create.return_value = limit_pb2.LimitCreateResponse()
        getStubMock.return_value = stubMock

        testLimitValue = 42
        opencue.api.createLimit(TEST_LIMIT_NAME, testLimitValue)

        stubMock.Create.assert_called_with(
            limit_pb2.LimitCreateRequest(name=TEST_LIMIT_NAME, max_value=testLimitValue),
            timeout=mock.ANY)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testGetLimits(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetAll.return_value = limit_pb2.LimitGetAllResponse(
            limits=[limit_pb2.Limit(name=TEST_LIMIT_NAME)])
        getStubMock.return_value = stubMock

        limits = opencue.api.getLimits()

        stubMock.GetAll.assert_called_with(limit_pb2.LimitGetAllRequest(), timeout=mock.ANY)
        self.assertEqual(len(limits), 1)
        self.assertEqual(limits[0].name(), TEST_LIMIT_NAME)

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def testFindLimit(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Find.return_value = limit_pb2.LimitFindResponse(
            limit=limit_pb2.Limit(name=TEST_LIMIT_NAME, max_value=42))
        getStubMock.return_value = stubMock

        limit = opencue.api.findLimit(TEST_LIMIT_NAME)
        self.assertEqual(TEST_LIMIT_NAME, limit.name())
        self.assertEqual(42, limit.maxValue())

        stubMock.Find.assert_called_with(
            limit_pb2.LimitFindRequest(name=TEST_LIMIT_NAME),
            timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
