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
Cue3 job module
"""

import cue.CueClientIce as CueClientIce
from ..api import *


class Group(CueClientIce.Group):

    def __init__(self):
        CueClientIce.Group.__init__(self)

    def createSubGroup(self,name):
        return self.proxy.createSubGroup(name)

    def delete(self):
        self.proxy.delete()

    def setName(self,name):
        self.proxy.setName(name)

    def setParent(self, group):
        self.proxy.setParent(group.proxy)

    def setMaxCores(self, value):
        self.proxy.setMaxCores(value)

    def setMinCores(self, value):
        self.proxy.setMinCores(value)

    def setDefaultJobPriority(self,value):
        self.proxy.setDefaultJobPriority(value)

    def setDefaultJobMinCores(self,value):
        self.proxy.setDefaultJobMinCores(value)

    def setDefaultJobMaxCores(self,value):
        self.proxy.setDefaultJobMaxCores(value)

    def getGroups(self):
        return self.proxy.getGroups()

    def getJobs(self):
        """Returns the jobs in this group
        @rtype:  list<Job>
        @return: List of jobs in this group"""
        return self.proxy.getJobs()

    def reparentJobs(self, jobs):
        """Moves the given jobs into this group
        @type  jobs: list<JobInterfacePrx or Job or id or str jobname>
        @param jobs: The jobs to add to this group"""
        proxies = proxy(jobs, "Job")
        if proxies:
            self.proxy.reparentJobs(proxies)

    def reparentGroups(self, groups, show = None):
        """Moves the given groups into this group
        @type  groups: list<GroupInterfacePrx or Group or id or str groupname>
        @param groups: The groups to move into
        @type  show: Show
        @param show: Supply the show if you wish to give groups by name"""
        if hasattr(show, "name"):
            show = show.name()
        proxies = api.proxy(groups,"Group")
        if proxies:
            self.proxy.reparentGroups(proxies)

    def setDepartment(self, name):
        """Sets the group's department to the specified name.  The department
        name must be one of the allowed department names.  All jobs in the group
        will inherit the new department name.  See AdminStatic for getting a list
        of allowed department names.  Department names are maintained by the
        middle-tier group.
        @type name: string
        @param name: a valid department name"""
        self.proxy.setDepartment(name)
        self.data.department = name

    def id(self):
        """Returns the id of the group
        @rtype:  str
        @return: Group uuid"""
        return self.proxy.ice_getIdentity().name

    def name(self):
        return self.data.name

    def department(self):
        return self.data.department

    def defaultJobPriority(self):
        return self.data.defaultJobPriority

    def defaultJobMinCores(self):
        return self.data.defaultJobMinCores

    def defaultJobMaxCores(self):
        return self.data.defaultJobMaxCores

    def maxCores(self):
        return self.data.maxCores;

    def minCores(self):
        return self.data.minCores;

    def reservedCores(self):
        """Returns the total number of reserved cores for the group
        @rtype: int
        @return: total numnber of frames"""
        return self.stats.reservedCores

    def totalRunning(self):
        """Returns the total number of running frames under this object
        @rtype:  int
        @return: Total number of running frames"""
        return self.stats.runningFrames

    def totalDead(self):
        """Returns the total number of deads frames under this object
        @rtype:  int
        @return: Total number of dead frames"""
        return self.stats.deadFrames

    def totalPending(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.
        @rtype:  int
        @return: Total number of pending (dependent and waiting) frames"""
        return self.stats.pendingFrames

    def pendingJobs(self):
       """Returns the total number of running jobs
       @rtype: int
       @return: total number of running jobs"""
       return self.stats.pendingJobs


class NestedGroup(CueClientIce.NestedGroup, Group):

    def __init__(self):
        CueClientIce.NestedGroup.__init__(self)
        self.__children = []
        self.__children_init = False

    def children(self):
        """returns jobs and groups in a single array"""
        if not self.__children_init:
            self.__children.extend(self.groups)
            self.__children.extend(self.jobs)
            self.__children_init = True;
        return self.__children

