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


"""
opencue group module
"""


from opencue import Cuebot
from opencue.compiled_proto import job_pb2
import opencue.wrappers.job


class Group(object):

    def __init__(self, group):
        self.data = group
        self.stub = Cuebot.getStub('group')

    def createSubGroup(self, name):
        return Group(self.stub.CreateSubGroup(
            job_pb2.GroupCreateSubGroupRequest(group=self.data, name=name),
            timeout=Cuebot.Timeout).group)

    def delete(self):
        self.stub.Delete(job_pb2.GroupDeleteRequest(group=self.data), timeout=Cuebot.Timeout)

    def setName(self, name):
        self.stub.SetName(job_pb2.GroupSetNameRequest(group=self.data, name=name),
                          timeout=Cuebot.Timeout)

    def setMaxCores(self, value):
        self.stub.SetMaxCores(job_pb2.GroupSetMaxCoresRequest(group=self.data, max_cores=value),
                              timeout=Cuebot.Timeout)

    def setMinCores(self, value):
        self.stub.SetMinCores(job_pb2.GroupSetMinCoresRequest(group=self.data, min_cores=value),
                              timeout=Cuebot.Timeout)

    def setDefaultJobPriority(self, value):
        self.stub.SetDefaultJobPriority(
            job_pb2.GroupSetDefJobPriorityRequest(group=self.data, priority=value),
            timeout=Cuebot.Timeout)

    def setDefaultJobMinCores(self, value):
        self.stub.SetDefaultJobMinCores(
            job_pb2.GroupSetDefJobMinCoresRequest(group=self.data, min_cores=value),
            timeout=Cuebot.Timeout)

    def setDefaultJobMaxCores(self, value):
        self.stub.SetDefaultJobMaxCores(
            job_pb2.GroupSetDefJobMaxCoresRequest(group=self.data, max_cores=value),
            timeout=Cuebot.Timeout)

    def getGroups(self):
        response = self.stub.GetGroups(job_pb2.GroupGetGroupsRequest(group=self.data),
                                       timeout=Cuebot.Timeout)
        return [Group(g) for g in response.groups.groups]

    def getJobs(self):
        """Returns the jobs in this group
        @rtype:  list<Job>
        @return: List of jobs in this group"""
        response = self.stub.GetJobs(job_pb2.GroupGetJobsRequest(group=self.data),
                                     timeout=Cuebot.Timeout)
        return [opencue.wrappers.job.Job(j) for j in response.jobs.jobs]

    def reparentJobs(self, jobs):
        """Moves the given jobs into this group
        @type  jobs: list<Job>
        @param jobs: The jobs to add to this group"""
        jobsToReparent = []
        for job in jobs:
            if isinstance(job, opencue.wrappers.job.NestedJob):
                job = job.asJob()
            jobsToReparent.append(job.data)
        jobSeq = job_pb2.JobSeq(jobs=jobsToReparent)
        self.stub.ReparentJobs(job_pb2.GroupReparentJobsRequest(group=self.data, jobs=jobSeq),
                               timeout=Cuebot.Timeout)

    def reparentGroups(self, groups):
        """Moves the given groups into this group
        @type  groups: list<Group>
        @param groups: The groups to move into"""
        groupSeq = job_pb2.GroupSeq(groups=groups)
        self.stub.ReparentGroups(
            job_pb2.GroupReparentGroupsRequest(group=self.data, groups=groupSeq),
            timeout=Cuebot.Timeout)

    def setDepartment(self, name):
        """Sets the group's department to the specified name.  The department
        name must be one of the allowed department names.  All jobs in the group
        will inherit the new department name.  See AdminStatic for getting a list
        of allowed department names.  Department names are maintained by the
        middle-tier group.
        @type name: string
        @param name: a valid department name"""
        self.stub.SetDepartment(job_pb2.GroupSetDeptRequest(group=self.data, dept=name),
                                timeout=Cuebot.Timeout)
        self.data.department = name

    def setGroup(self, parentGroup):
        """Sets this group's parent to parentGroup.
        @type  parentGroup: Group
        @param parentGroup: Group to parent under"""
        self.stub.SetGroup(job_pb2.GroupSetGroupRequest(group=self.data, parent_group=parentGroup),
                           timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the group
        @rtype:  str
        @return: Group uuid"""
        return self.data.id

    def name(self):
        return self.data.name

    def department(self):
        return self.data.department

    def defaultJobPriority(self):
        return self.data.default_job_priority

    def defaultJobMinCores(self):
        return self.data.default_job_min_cores

    def defaultJobMaxCores(self):
        return self.data.default_job_max_cores

    def maxCores(self):
        return self.data.max_cores

    def minCores(self):
        return self.data.min_cores

    def reservedCores(self):
        """Returns the total number of reserved cores for the group
        @rtype: int
        @return: total numnber of frames"""
        return self.data.group_stats.reserved_cores

    def totalRunning(self):
        """Returns the total number of running frames under this object
        @rtype:  int
        @return: Total number of running frames"""
        return self.data.group_stats.running_frames

    def totalDead(self):
        """Returns the total number of deads frames under this object
        @rtype:  int
        @return: Total number of dead frames"""
        return self.data.group_stats.dead_frames

    def totalPending(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.
        @rtype:  int
        @return: Total number of pending (dependent and waiting) frames"""
        return self.data.group_stats.pending_frames

    def pendingJobs(self):
        """Returns the total number of running jobs
        @rtype: int
        @return: total number of running jobs"""
        return self.data.group_stats.pending_jobs


class NestedGroup(Group):

    def __init__(self, group):
        super(NestedGroup, self).__init__(group)
        self.__children = []
        self.__children_init = False

    def createSubGroup(self, name):
        """Create a sub group"""
        return self.asGroup().createSubGroup(name)

    def children(self):
        """returns jobs and groups in a single array"""
        if not self.__children_init:
            self.__children.extend(self.groups)
            self.__children.extend(self.jobs)
            self.__children_init = True
        return self.__children

    def asGroup(self):
        """returns a Group object from this NestedGroup"""
        return Group(job_pb2.Group(
            id=self.data.id,
            name=self.data.name,
            department=self.data.department,
            default_job_priority=self.data.default_job_priority,
            default_job_min_cores=self.data.default_job_min_cores,
            default_job_max_cores=self.data.default_job_max_cores,
            min_cores=self.data.min_cores,
            max_cores=self.data.max_cores,
            level=self.data.level,
            group_stats=self.data.stats,
        ))
