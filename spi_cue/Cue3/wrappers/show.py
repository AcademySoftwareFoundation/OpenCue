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

"""

import filter
import group
import subscription
from Cue3.compiled_proto import show_pb2
from Cue3.cuebot import Cuebot


class Show(object):

    def __init__(self, show):
        self.data = show
        self.stub = Cuebot.getStub('show')

    def createOwner(self, user):
        """Creates a new owner
        @type  user: str
        @param user: user name
        @rtype:  Owner
        @return: The created owner object"""
        response = self.stub.CreateOwner(show_pb2.ShowCreateOwnerRequest(show=self.data, name=user),
                                         timeout=Cuebot.Timeout)
        return response.owner

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
        response = self.stub.CreateSubscription(show_pb2.ShowCreateSubscriptionRequest(
            show=self.data, allocation_id=allocation.id, size=size, burst=burst),
            timeout=Cuebot.Timeout)
        return subscription.Subscription(response.subscription)

    def getSubscriptions(self):
        """Returns a list of all subscriptions
        @rtype:  list<Subscription>
        @return: A list of subscription objects"""
        response = self.stub.GetSubscriptions(show_pb2.ShowGetSubscriptionRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        subscriptionSeq = response.subscriptions
        return [subscription.Subscription(subs) for subs in subscriptionSeq.subscriptions]

    def findSubscription(self, name):
        """Returns the matching subscription
        @rtype:  Subscription
        @return: The matching subscription"""
        subscriptions = subscription.Subscription()
        return subscriptions.find(name)

    def getFilters(self):
        """Returns the job filters for this show
        @rtype: FilterSeq
        @return: Seq object containing a list of Filters"""
        response = self.stub.GetFilters(show_pb2.ShowGetFiltersRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        return [filter.Filter(filter) for filter in response.filters]

    def setDefaultMaxCores(self, maxcores):
        """Sets the default maximum number of cores
           that new jobs are launched with."""
        response = self.stub.SetDefaultMaxCores(show_pb2.ShowSetDefaultMaxCoresRequest(
            show=self.data, max_cores=maxcores),
            timeout=Cuebot.Timeout)
        return response

    def setDefaultMinCores(self, mincores):
        """Sets the default minimum number of cores
           all new jobs are launched with."""
        response = self.stub.SetDefaultMinCores(show_pb2.ShowSetDefaultMinCoresRequest(
            show=self.data, max_cores=mincores),
            timeout=Cuebot.Timeout)
        return response

    def findFilter(self, name):
        response = self.stub.FindFilter(show_pb2.ShowFindShowRequest(
            show=self.data, name=name), timeout=Cuebot.Timeout)
        return filter.Filter(response.filter)

    def createFilter(self, name):
        response = self.stub.CreateFilter(show_pb2.ShowCreateFilterRequest(
            show=self.data, name=name), timeout=Cuebot.Timeout)
        return filter.Filter(response.filter)

    def getGroups(self):
        """
        @rtype:  GroupSeq
        @return: """
        response = self.stub.GetGroups(show_pb2.ShowGetGroupsRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        return [group.Group(group) for group in response.groups]

    def getJobWhiteboard(self):
        response = self.stub.GetJobWhiteboard(show_pb2.ShowGetJobWhiteboardRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        return response.whiteboard

    def getRootGroup(self):
        response = self.stub.GetRootGroup(show_pb2.ShowGetRootGroupRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        return group.Group(response.group)

    def enableBooking(self, value):
        response = self.stub.EnableBooking(show_pb2.ShowEnableBookingRequest(
            show=self.data,
            enabled=value),
            timeout=Cuebot.Timeout)
        return response

    def enableDispatching(self, value):
        response = self.stub.EnableDispatching(show_pb2.ShowEnableDispatchingRequest(
            show=self.data,
            enabled=value),
            timeout=Cuebot.Timeout)
        return response

    def id(self):
        """Returns the id of the show
        @rtype:  str
        @return: Frame uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the show
        @rtype:  str
        @return: Show name"""
        return self.data.name

    def pendingJobs(self):
        """Total number of pending jobs.
        @rtype: int
        @return: the total number of pending jobs"""
        return self.data.show_stats.pending_jobs

    def pendingFrames(self):
        """Total number of running frames currently in the queue
        @rtype:  int
        @return: """
        return self.data.show_stats.pending_frames

    def runningFrames(self):
        """Total number of running frames currently in the queue
        @rtype:  int
        @return: """
        return self.data.show_stats.running_frames

    def deadFrames(self):
        """Total number of dead frames currently in the queue
        @rtype:  int
        @return: """
        return self.data.show_stats.dead_frames

    def reservedCores(self):
        """Total number of reserved cores by all frames
        @rtype:  float
        @return: """
        return self.data.show_stats.reserved_cores

    def defaultMinProcs(self):
        """Returns the default minProcs that new jobs are set to
        @rtype:  int
        @return: Default minProcs value for new jobs"""
        return self.data.default_min_procs

    def defaultMaxProcs(self):
        """Returns the default maxProcs that new jobs are set to
        @rtype:  int
        @return: Default maxProcs value for new jobs"""
        return self.data.default_max_procs
    
    def totalJobsCreated(self):
        """A running counter of jobs launched.
        @rtype: int"""
        return self.data.show_stats.created_job_count

    def totalFramesCreated(self):
        """A running counter of frames launched.
        @rtype: int"""
        return self.data.show_stats.created_frame_count


