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

"""Tests for `opencue.wrappers.group`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import job_pb2
import opencue.wrappers.group
import opencue.wrappers.job


TEST_GROUP_NAME = 'testGroup'


@mock.patch('opencue.cuebot.Cuebot.getStub')
class GroupTests(unittest.TestCase):

    def testCreateSubGroup(self, getStubMock):
        subgroupName = 'testSubgroup'
        stubMock = mock.Mock()
        stubMock.CreateSubGroup.return_value = job_pb2.GroupCreateSubGroupResponse(
            group=job_pb2.Group(name=subgroupName))
        getStubMock.return_value = stubMock

        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        subgroup = group.createSubGroup(subgroupName)

        stubMock.CreateSubGroup.assert_called_with(
            job_pb2.GroupCreateSubGroupRequest(group=group.data, name=subgroupName),
            timeout=mock.ANY)
        self.assertEqual(subgroup.name(), subgroupName)

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = job_pb2.GroupDeleteResponse()
        getStubMock.return_value = stubMock

        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.delete()

        stubMock.Delete.assert_called_with(
            job_pb2.GroupDeleteRequest(group=group.data),
            timeout=mock.ANY)

    def testSetName(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetName.return_value = job_pb2.GroupSetNameResponse()
        getStubMock.return_value = stubMock

        newName = 'changedName'
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setName(newName)

        stubMock.SetName.assert_called_with(
            job_pb2.GroupSetNameRequest(group=group.data, name=newName),
            timeout=mock.ANY)

    def testSetMaxCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMaxCores.return_value = job_pb2.GroupSetMaxCoresResponse()
        getStubMock.return_value = stubMock

        value = 523
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setMaxCores(value)

        stubMock.SetMaxCores.assert_called_with(
            job_pb2.GroupSetMaxCoresRequest(group=group.data, max_cores=value),
            timeout=mock.ANY)

    def testSetMinCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetMinCores.return_value = job_pb2.GroupSetMinCoresResponse()
        getStubMock.return_value = stubMock

        value = 2
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setMinCores(value)

        stubMock.SetMinCores.assert_called_with(
            job_pb2.GroupSetMinCoresRequest(group=group.data, min_cores=value),
            timeout=mock.ANY)

    def testSetDefaultJobPriority(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultJobPriority.return_value = job_pb2.GroupSetDefJobPriorityResponse()
        getStubMock.return_value = stubMock

        value = 500
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setDefaultJobPriority(value)

        stubMock.SetDefaultJobPriority.assert_called_with(
            job_pb2.GroupSetDefJobPriorityRequest(group=group.data, priority=value),
            timeout=mock.ANY)

    def testSetDefaultJobMaxCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultJobMaxCores.return_value = job_pb2.GroupSetDefJobMaxCoresResponse()
        getStubMock.return_value = stubMock

        value = 523
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setDefaultJobMaxCores(value)

        stubMock.SetDefaultJobMaxCores.assert_called_with(
            job_pb2.GroupSetDefJobMaxCoresRequest(group=group.data, max_cores=value),
            timeout=mock.ANY)

    def testSetDefaultJobMinCores(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDefaultJobMinCores.return_value = job_pb2.GroupSetDefJobMinCoresResponse()
        getStubMock.return_value = stubMock

        value = 2
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setDefaultJobMinCores(value)

        stubMock.SetDefaultJobMinCores.assert_called_with(
            job_pb2.GroupSetDefJobMinCoresRequest(group=group.data, min_cores=value),
            timeout=mock.ANY)

    def testGetGroups(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetGroups.return_value = job_pb2.GroupGetGroupsResponse(
            groups=job_pb2.GroupSeq(groups=[job_pb2.Group(name=TEST_GROUP_NAME)]))
        getStubMock.return_value = stubMock

        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        groups = group.getGroups()

        stubMock.GetGroups.assert_called_with(
            job_pb2.GroupGetGroupsRequest(group=group.data),
            timeout=mock.ANY)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name(), TEST_GROUP_NAME)

    def testGetJobs(self, getStubMock):
        jobName = 'testJob'
        stubMock = mock.Mock()
        stubMock.GetJobs.return_value = job_pb2.GroupGetJobsResponse(
            jobs=job_pb2.JobSeq(jobs=[job_pb2.Job(name=jobName)]))
        getStubMock.return_value = stubMock

        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        jobs = group.getJobs()

        stubMock.GetJobs.assert_called_with(
            job_pb2.GroupGetJobsRequest(group=group.data),
            timeout=mock.ANY)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].name(), jobName)

    def testReparentJobs(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReparentJobs.return_value = job_pb2.GroupReparentJobsResponse()
        getStubMock.return_value = stubMock

        testJob = job_pb2.Job(name='testJob')
        testNestedJob = job_pb2.NestedJob(name='testNestedJob')
        jobs = [opencue.wrappers.job.Job(testJob), opencue.wrappers.job.NestedJob(testNestedJob)]
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.reparentJobs(jobs)

        expected = job_pb2.JobSeq(jobs=[job_pb2.Job(name='testJob'),
                                        job_pb2.Job(name='testNestedJob',
                                                    job_stats=job_pb2.JobStats())])
        stubMock.ReparentJobs.assert_called_with(
            job_pb2.GroupReparentJobsRequest(group=group.data, jobs=expected),
            timeout=mock.ANY)

    def testReparentGroups(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReparentGroups.return_value = job_pb2.GroupReparentGroupsResponse()
        getStubMock.return_value = stubMock

        groups = [opencue.wrappers.group.Group(job_pb2.Group())]
        groupSeq = job_pb2.GroupSeq(groups=[grp.data for grp in groups])
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.reparentGroups(groups)

        stubMock.ReparentGroups.assert_called_with(
            job_pb2.GroupReparentGroupsRequest(group=group.data, groups=groupSeq),
            timeout=mock.ANY)

    def testReparentGroupIds(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.ReparentGroups.return_value = job_pb2.GroupReparentGroupsResponse()
        getStubMock.return_value = stubMock

        groupId = 'ggg-gggg-ggg'
        groupIds = [groupId]
        groups = [opencue.wrappers.group.Group(job_pb2.Group(id='ggg-gggg-ggg'))]
        groupSeq = job_pb2.GroupSeq(groups=[grp.data for grp in groups])
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.reparentGroupIds(groupIds)

        stubMock.ReparentGroups.assert_called_with(
            job_pb2.GroupReparentGroupsRequest(group=group.data, groups=groupSeq),
            timeout=mock.ANY)

    def testSetDepartment(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetDepartment.return_value = job_pb2.GroupSetDeptResponse()
        getStubMock.return_value = stubMock

        dept = 'pipeline'
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setDepartment(dept)

        expected = job_pb2.Group(name=TEST_GROUP_NAME)
        stubMock.SetDepartment.assert_called_with(
            job_pb2.GroupSetDeptRequest(group=expected, dept=dept),
            timeout=mock.ANY)

    def testSetGroup(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.SetGroup.return_value = job_pb2.GroupSetGroupResponse()
        getStubMock.return_value = stubMock

        parentGroup = opencue.wrappers.group.Group(job_pb2.Group(name='parentGroup'))
        group = opencue.wrappers.group.Group(
            job_pb2.Group(name=TEST_GROUP_NAME))
        group.setGroup(parentGroup)

        stubMock.SetGroup.assert_called_with(
            job_pb2.GroupSetGroupRequest(group=group.data, parent_group=parentGroup.data),
            timeout=mock.ANY)


@mock.patch('opencue.cuebot.Cuebot.getStub')
class NestedGroupTests(unittest.TestCase):

    def testAsGroup(self, getStubMock):
        nestedGroup = opencue.wrappers.group.NestedGroup(job_pb2.NestedGroup(
            id='ngn-ngng-ngn',
            name='testNestedGroup',
            department='pipeline'
        ))
        group = nestedGroup.asGroup()
        self.assertEqual(nestedGroup.data.id, group.data.id)
        self.assertEqual(nestedGroup.data.name, group.data.name)
        self.assertEqual(nestedGroup.data.department, group.data.department)



if __name__ == '__main__':
    unittest.main()
