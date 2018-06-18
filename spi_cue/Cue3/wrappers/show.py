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
Project: Cue3 Library

Module: show.py - Cue3 Library implementation of a show

Created: March 3, 2008

Contact: Middle-Tier Group 

SVN: $Id$
"""

import cue.CueClientIce as CueClientIce

class Show(CueClientIce.Show):
    """This class contains the ice implementation related to an Show."""
    def __init__(self):
        """_Show class initialization"""
        CueClientIce.Show.__init__(self)

    def createSubscription(self, allocation, size, burst):
        """Creates a new subscription
        @type  allocation: Allocation
        @param allocation: Allocation object
        @type  size: float
        @param size: Allocation size
        @type  burst: float
        @param burst: Allocation burst
        @rtype:  Subscription
        @return: The created subscription object"""
        return self.proxy.createSubscription(allocation.proxy, size, burst)

    def getSubscriptions(self):
        """Returns a list of all subscriptions
        @rtype:  list<Subscription>
        @return: A list of subscription objects"""
        return self.proxy.getSubscriptions()

    def findSubscription(self, name):
        """Returns the matching subscription
        @rtype:  Subscription
        @return: The matching subscription"""
        return self.proxy.findSubscription(name)

    def getFilters(self):
        """Returns the job filters for this show
        @rtype: list<Filter>
        @return: a list of Filters"""
        return self.proxy.getFilters()

    def setDefaultMaxProcs(self, maxprocs):
        """Sets the default maximum number of procs
           that new jobs are launched with."""
        self.proxy.setDefaultMaxProcs(maxprocs)

    def setDefaultMinProcs(self, minprocs):
        """Sets the default minimum number of procs
           all new jobs are launched with."""
        self.proxy.setDefaultMinProcs(minprocs)

    def findFilter(self, name):
        return self.proxy.findFilter(name)

    def createFilter(self, name):
        return self.proxy.createFilter(name)

    def getGroups(self):
        """
        @rtype:  list<Cue3.group.Group>
        @return: """
        return self.proxy.getGroups()

    def getJobWhiteboard(self):
        return self.proxy.getJobWhiteboard()

    def getRootGroup(self):
        return self.proxy.getRootGroup()

    def id(self):
        """Returns the id of the show
        @rtype:  str
        @return: Frame uuid"""
        return self.proxy.ice_getIdentity().name

    def name(self):
        """Returns the name of the show
        @rtype:  str
        @return: Show name"""
        return self.data.name

    def pendingJobs(self):
        """Total number of pending jobs.
        @rtype: int
        @return: the total number of pending jobs"""
        return self.stats.pendingJobs

    def pendingFrames(self):
        """Total number of running frames currently in the queue
        @rtype:  int
        @return: """
        return self.stats.pendingFrames

    def runningFrames(self):
        """Total number of running frames currently in the queue
        @rtype:  int
        @return: """
        return self.stats.runningFrames

    def deadFrames(self):
        """Total number of dead frames currently in the queue
        @rtype:  int
        @return: """
        return self.stats.deadFrames

    def reservedCores(self):
        """Total number of reserved cores by all frames
        @rtype:  float
        @return: """
        return self.stats.reservedCores

    def defaultMinProcs(self):
        """Returns the default minProcs that new jobs are set to
        @rtype:  int
        @return: Default minProcs value for new jobs"""
        return self.data.defaultMinProcs

    def defaultMaxProcs(self):
        """Returns the default maxProcs that new jobs are set to
        @rtype:  int
        @return: Default maxProcs value for new jobs"""
        return self.data.defaultMaxProcs
    
    def totalJobsCreated(self):
        """A running counter of jobs launched.
        @rtype: int"""
        return self.stats.createdJobCount

    def totalFramesCreated(self):
        """A running counter of frames launched.
        @rtype: int"""
        return self.stats.createdFrameCount


