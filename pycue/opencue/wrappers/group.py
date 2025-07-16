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

"""Modules for classes related to groups."""

from opencue_proto import job_pb2
from opencue import Cuebot
import opencue.wrappers.job


class Group(object):
    """This class contains the grpc implementation related to a Group."""

    def __init__(self, group=None):
        self.data = group
        self.stub = Cuebot.getStub('group')

    def createSubGroup(self, name):
        """Creates a subgroup under this group.

        :type  name: str
        :param name: name of the new subgroup
        """
        return Group(self.stub.CreateSubGroup(
            job_pb2.GroupCreateSubGroupRequest(group=self.data, name=name),
            timeout=Cuebot.Timeout).group)

    def delete(self):
        """Deletes the group."""
        self.stub.Delete(job_pb2.GroupDeleteRequest(group=self.data), timeout=Cuebot.Timeout)

    def setName(self, name):
        """Sets the name of the group.

        :type  name: str
        :param name: new name for the group
        """
        self.stub.SetName(job_pb2.GroupSetNameRequest(group=self.data, name=name),
                          timeout=Cuebot.Timeout)

    def setMaxCores(self, value):
        """Sets the maximum cores of everything in the group.

        :type  value: int
        :param value: new maximum number of cores
        """
        self.stub.SetMaxCores(job_pb2.GroupSetMaxCoresRequest(group=self.data, max_cores=value),
                              timeout=Cuebot.Timeout)

    def setMinCores(self, value):
        """Sets the minimum cores of everything the group.

        :type  value: int
        :param value: new minimum number of cores
        """
        self.stub.SetMinCores(job_pb2.GroupSetMinCoresRequest(group=self.data, min_cores=value),
                              timeout=Cuebot.Timeout)

    def setMaxGpus(self, value):
        """Sets the maximum gpus of everything in the group.

        :type  value: int
        :param value: new maximum number of gpus
        """
        self.stub.SetMaxGpus(job_pb2.GroupSetMaxGpusRequest(group=self.data, max_gpus=value),
                             timeout=Cuebot.Timeout)

    def setMinGpus(self, value):
        """Sets the minimum gpus of everything the group.

        :type  value: int
        :param value: new minimum number of gpus
        """
        self.stub.SetMinGpus(job_pb2.GroupSetMinGpusRequest(group=self.data, min_gpus=value),
                             timeout=Cuebot.Timeout)

    def setDefaultJobPriority(self, value):
        """Sets the default job priority for everything in the group.

        :type  value: int
        :param value: new default priority
        """
        self.stub.SetDefaultJobPriority(
            job_pb2.GroupSetDefJobPriorityRequest(group=self.data, priority=value),
            timeout=Cuebot.Timeout)

    def setDefaultJobMinCores(self, value):
        """Sets the default job minimum cores for everything in the group.

        :type  value: int
        :param value: new default job minimum cores
        """
        self.stub.SetDefaultJobMinCores(
            job_pb2.GroupSetDefJobMinCoresRequest(group=self.data, min_cores=value),
            timeout=Cuebot.Timeout)

    def setDefaultJobMaxCores(self, value):
        """Sets the default job maximum cores for everything in the group.

        :type  value: int
        :param value: new default job maximum cores
        """
        self.stub.SetDefaultJobMaxCores(
            job_pb2.GroupSetDefJobMaxCoresRequest(group=self.data, max_cores=value),
            timeout=Cuebot.Timeout)

    def setDefaultJobMinGpus(self, value):
        """Sets the default job minimum gpus for everything in the group.

        :type  value: int
        :param value: new default job minimum gpus
        """
        self.stub.SetDefaultJobMinGpus(
            job_pb2.GroupSetDefJobMinGpusRequest(group=self.data, min_gpus=value),
            timeout=Cuebot.Timeout)

    def setDefaultJobMaxGpus(self, value):
        """Sets the default job maximum gpus for everything in the group.

        :type  value: int
        :param value: new default job maximum gpus
        """
        self.stub.SetDefaultJobMaxGpus(
            job_pb2.GroupSetDefJobMaxGpusRequest(group=self.data, max_gpus=value),
            timeout=Cuebot.Timeout)

    def getGroups(self):
        """Returns child groups of this group.

        :rtype: list<opencue.wrappers.group.Group>
        :return: list of child groups
        """
        response = self.stub.GetGroups(job_pb2.GroupGetGroupsRequest(group=self.data),
                                       timeout=Cuebot.Timeout)
        return [Group(g) for g in response.groups.groups]

    def getJobs(self):
        """Returns the jobs in this group.

        :rtype:  list<opencue.wrappers.job.Job>
        :return: list of jobs in this group
        """
        response = self.stub.GetJobs(job_pb2.GroupGetJobsRequest(group=self.data),
                                     timeout=Cuebot.Timeout)
        return [opencue.wrappers.job.Job(j) for j in response.jobs.jobs]

    def reparentJobs(self, jobs):
        """Moves the given jobs into this group.

        :type  jobs: list<opencue.wrappers.job.Job>
        :param jobs: The jobs to add to this group
        """
        jobsToReparent = []
        for job in jobs:
            if isinstance(job, opencue.wrappers.job.NestedJob):
                job = job.asJob()
            jobsToReparent.append(job.data)
        jobSeq = job_pb2.JobSeq(jobs=jobsToReparent)
        self.stub.ReparentJobs(job_pb2.GroupReparentJobsRequest(group=self.data, jobs=jobSeq),
                               timeout=Cuebot.Timeout)

    def reparentGroups(self, groups):
        """Moves the given groups to be subgroups of this group.

        :type  groups: list<opencue.wrappers.group.Group>
        :param groups: the groups to make subgroups of this group
        """
        groupSeq = job_pb2.GroupSeq(groups=[group.data for group in groups])
        self.stub.ReparentGroups(
            job_pb2.GroupReparentGroupsRequest(group=self.data, groups=groupSeq),
            timeout=Cuebot.Timeout)

    def reparentGroupIds(self, groupIds):
        """Moves the given group ids into this group.

        :type  groupIds: list<str>
        :param groupIds: The group ids to make subgroups of this group
        """
        groups = [Group(job_pb2.Group(id=groupId)) for groupId in groupIds]
        self.reparentGroups(groups)

    def setDepartment(self, name):
        """Sets the group's department to the specified name.

        The department name must be one of the allowed department names.  All jobs in the group
        will inherit the new department name.

        :type  name: string
        :param name: a valid department name
        """
        self.stub.SetDepartment(job_pb2.GroupSetDeptRequest(group=self.data, dept=name),
                                timeout=Cuebot.Timeout)
        self.data.department = name

    def setGroup(self, parentGroup):
        """Sets this group's parent.

        :type  parentGroup: opencue.wrappers.group.Group
        :param parentGroup: group to parent under
        """
        self.stub.SetGroup(
            job_pb2.GroupSetGroupRequest(group=self.data, parent_group=parentGroup.data),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the group.

        :rtype:  str
        :return: id of the group
        """
        return self.data.id

    def name(self):
        """Returns the name of the group.

        :rtype:  str
        :return: name of the group"""
        return self.data.name

    def department(self):
        """Returns the department of the group.

        :rtype:  str
        :return: department of the group
        """
        return self.data.department

    def defaultJobPriority(self):
        """Returns the default job priority of the group.

        :rtype:  int
        :return: default job priority of the group
        """
        return self.data.default_job_priority

    def defaultJobMinCores(self):
        """Returns the default job minimum cores of the group.

        :rtype:  float
        :return: default job min cores
        """
        return self.data.default_job_min_cores

    def defaultJobMaxCores(self):
        """Returns the default job maximum cores of the group.

        :rtype:  float
        :return: default job max cores
        """
        return self.data.default_job_max_cores

    def maxCores(self):
        """Returns the maximum cores of the group.

        :rtype:  float
        :return: max cores of the group
        """
        return self.data.max_cores

    def minCores(self):
        """Returns the minimum cores of the group.

        :rtype:  float
        :return: min cores of the group
        """
        return self.data.min_cores

    def reservedCores(self):
        """Returns the total number of reserved cores for the group.

        :rtype:  float
        :return: total number of reserved cores
        """
        return self.data.group_stats.reserved_cores

    def totalRunning(self):
        """Returns the total number of running frames under this group.

        :rtype:  int
        :return: total number of running frames
        """
        return self.data.group_stats.running_frames

    def totalDead(self):
        """Returns the total number of dead frames under this group.

        :rtype:  int
        :return: total number of dead frames
        """
        return self.data.group_stats.dead_frames

    def totalPending(self):
        """Returns the total number of pending (dependent and waiting) frames under this group.

        :rtype:  int
        :return: total number of pending (dependent and waiting) frames
        """
        return self.data.group_stats.pending_frames

    def pendingJobs(self):
        """Returns the total number of running jobs.

        :rtype: int
        :return: total number of running jobs
        """
        return self.data.group_stats.pending_jobs


class NestedGroup(Group):
    """This class contains information and actions related to a nested group."""

    def __init__(self, group):
        super(NestedGroup, self).__init__(group)
        self.__children = []
        self.__children_init = False

    def createSubGroup(self, name):
        """Creates a subgroup under this nested group.

        :type  name: str
        :param name: name of the new subgroup
        """
        return self.asGroup().createSubGroup(name)

    def children(self):
        """Returns this group's jobs and child groups in a single array.

        :rtype: list<job_pb2.group/job_pb2.job>
        :return: list of all jobs and child groups in this group
        """
        if not self.__children_init:
            self.__children.extend(self.data.groups)
            self.__children.extend(self.data.jobs)
            self.__children_init = True
        return self.__children

    def asGroup(self):
        """Returns a Group object from this NestedGroup.

        :rtype: opencue.wrappers.group.Group
        :return: Group version of this NestedGroup
        """
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

    def hasParent(self):
        """Whether this NestedGroup has a parent group.

        :rtype:  bool
        :return: whether the group has a parent group.
        """
        return self.data.HasField('parent')
