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

"""Module for classes related to shows."""

from opencue_proto import show_pb2
from opencue.cuebot import Cuebot
import opencue.wrappers.filter
import opencue.wrappers.group
import opencue.wrappers.subscription
from opencue.wrappers.service import ServiceOverride


class Show(object):
    """This class contains the grpc implementation related to a Show."""

    def __init__(self, show=None):
        self.data = show
        self.stub = Cuebot.getStub('show')

    def createOwner(self, user):
        """Creates a new owner for the show.

        :type  user: str
        :param user: user name
        :rtype:  host_pb2.Owner
        :return: the created owner object
        """
        response = self.stub.CreateOwner(show_pb2.ShowCreateOwnerRequest(show=self.data, name=user),
                                         timeout=Cuebot.Timeout)
        return response.owner

    def createSubscription(self, allocation, size, burst):
        """Creates a new subscription for the show.

        A subscription links a show to an allocation, and determines how many cores the show
        can utilize within that allocation.

        :type  allocation: opencue.wrappers.allocation.Allocation
        :param allocation: allocation to subscribe to
        :type  size: float
        :param size: number of cores the show is allowed to use consistently
        :type  burst: float
        :param burst: number of cores the show is allowed to burst to
        :rtype:  opencue.wrappers.subscription.Subscription
        :return: the created subscription object
        """
        response = self.stub.CreateSubscription(show_pb2.ShowCreateSubscriptionRequest(
            show=self.data, allocation_id=allocation.id(), size=size, burst=burst),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.subscription.Subscription(response.subscription)

    def delete(self):
        """Deletes this show."""
        self.stub.Delete(show_pb2.ShowDeleteRequest(show=self.data), timeout=Cuebot.Timeout)

    def createServiceOverride(self, data):
        """Creates a Service Override at the show level.
        :type data: opencue.wrapper.service.Service
        :param data: Service.data object
        """

        # min_memory_increase has to be greater than 0.
        if data.min_memory_increase <= 0:
            raise ValueError("Minimum memory increase must be > 0")
        self.stub.CreateServiceOverride(show_pb2.ShowCreateServiceOverrideRequest(
                                        show=self.data, service=data),
                                        timeout=Cuebot.Timeout)

    def getServiceOverride(self, serviceName):
        """
        Returns a service override for a show

        :param serviceName: name of the service for the show
        :return: service override object
        """
        serviceOverride = self.stub.GetServiceOverride(show_pb2.ShowGetServiceOverrideRequest(
                                                       show=self.data, name=serviceName),
                                                       timeout=Cuebot.Timeout).service_override
        return ServiceOverride(serviceOverride)

    def getServiceOverrides(self):
        """Returns a list of service overrides on the show.

        :rtype:  list<service_pb2.ServiceOverride>
        :return: list of service overrides on the show
        """
        serviceOverrideSeq = self.stub.GetServiceOverrides(
            show_pb2.ShowGetServiceOverridesRequest(show=self.data),
            timeout=Cuebot.Timeout).service_overrides
        return [ServiceOverride(override) for override in serviceOverrideSeq.service_overrides]

    def getSubscriptions(self):
        """Returns a list of all subscriptions the show has.

        :rtype:  list<opencue.wrappers.subscription.Subscription>
        :return: list of the show's subscriptions
        """
        response = self.stub.GetSubscriptions(
            show_pb2.ShowGetSubscriptionRequest(show=self.data), timeout=Cuebot.Timeout)
        subscriptionSeq = response.subscriptions
        return [opencue.wrappers.subscription.Subscription(subs)
                for subs in subscriptionSeq.subscriptions]

    @staticmethod
    def findSubscription(name):
        """Returns the matching subscription.

        :type name: str
        :param name: name of subscription to find
        :rtype:  opencue.wrappers.subscription.Subscription
        :return: the matching subscription
        """
        subscriptions = opencue.wrappers.subscription.Subscription()
        return subscriptions.find(name)

    def getFilters(self):
        """Returns the job filters for this show.

        :rtype:  list<opencue.wrappers.filter.Filter>
        :return: list of filters for this show
        """
        response = self.stub.GetFilters(
            show_pb2.ShowGetFiltersRequest(show=self.data), timeout=Cuebot.Timeout)
        filterSeq = response.filters
        return [opencue.wrappers.filter.Filter(filter) for filter in filterSeq.filters]

    def setActive(self, value):
        """Sets whether this show is active.

        :type  value: bool
        :param value: whether the show is active
        """
        self.stub.SetActive(show_pb2.ShowSetActiveRequest(show=self.data, value=value),
                            timeout=Cuebot.Timeout)

    def setDefaultMaxCores(self, maxcores):
        """Sets the default maximum number of cores that new jobs are launched with.

        :type  maxcores: float
        :param maxcores: new maximum number of cores for new jobs
        :rtype:  show_pb2.ShowSetDefaultMaxCoresResponse
        :return: response is empty
        """
        response = self.stub.SetDefaultMaxCores(show_pb2.ShowSetDefaultMaxCoresRequest(
            show=self.data, max_cores=maxcores),
            timeout=Cuebot.Timeout)
        return response

    def setDefaultMinCores(self, mincores):
        """Sets the default minimum number of cores new jobs are launched with.

        :type  mincores: float
        :param mincores: new minimum number of cores for new jobs
        :rtype:  show_pb2.ShowSetDefaultMinCoresResponse
        :return: response is empty
        """
        response = self.stub.SetDefaultMinCores(show_pb2.ShowSetDefaultMinCoresRequest(
            show=self.data, min_cores=mincores),
            timeout=Cuebot.Timeout)
        return response

    def setDefaultMaxGpus(self, maxgpus):
        """Sets the default maximum number of gpus
        that new jobs are launched with.
        :type: float
        :param: value to set maxGpu to
        :rtype: show_pb2.ShowSetDefaultMaxGpuResponse
        :return: response is empty
        """
        response = self.stub.SetDefaultMaxGpus(show_pb2.ShowSetDefaultMaxGpusRequest(
            show=self.data, max_gpus=maxgpus),
            timeout=Cuebot.Timeout)
        return response

    def setDefaultMinGpus(self, mingpus):
        """Sets the default minimum number of gpus
        all new jobs are launched with.
        :type: float
        :param: value to set minGpus to
        :rtype: show_pb2.ShowSetDefaultMinGpusResponse
        :return: response is empty
        """
        response = self.stub.SetDefaultMinGpus(show_pb2.ShowSetDefaultMinGpusRequest(
            show=self.data, min_gpus=mingpus),
            timeout=Cuebot.Timeout)
        return response

    def findFilter(self, name):
        """Finds a filter by name.

        :type  name: string
        :param name: name of filter to find
        :rtype:  opencue.wrappers.filter.Filter
        :return: matching filter
        """
        response = self.stub.FindFilter(show_pb2.ShowFindFilterRequest(
            show=self.data, name=name), timeout=Cuebot.Timeout)
        return opencue.wrappers.filter.Filter(response.filter)

    def createFilter(self, name):
        """Creates a filter on the show.

        :type  name: str
        :param name: name of the filter to create
        :rtype:  opencue.wrappers.filter.Filter
        :return: the new filter object
        """
        response = self.stub.CreateFilter(show_pb2.ShowCreateFilterRequest(
            show=self.data, name=name), timeout=Cuebot.Timeout)
        return opencue.wrappers.filter.Filter(response.filter)

    def getGroups(self):
        """Gets the groups for the show.

        :rtype:  list<opencue.wrappers.group.Group>
        :return: list of groups for this show
        """
        response = self.stub.GetGroups(show_pb2.ShowGetGroupsRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        groupSeq = response.groups
        return [opencue.wrappers.group.Group(grp) for grp in groupSeq.groups]

    def getJobWhiteboard(self):
        """Gets the whiteboard for the show.

        :rtype:  job_pb2.NestedGroup
        :return: NestedGroup whiteboard for the show
        """
        response = self.stub.GetJobWhiteboard(show_pb2.ShowGetJobWhiteboardRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        return response.whiteboard

    def getRootGroup(self):
        """Gets the root group for the show.

        :rtype:  opencue.wrappers.group.Group
        :return: the root group
        """
        response = self.stub.GetRootGroup(show_pb2.ShowGetRootGroupRequest(
            show=self.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.group.Group(response.group)

    def enableBooking(self, value):
        """Enables or disables booking on the show.

        :type  value: bool
        :param value: whether to enable booking
        :rtype:  show_pb2.ShowEnableBookingResponse
        :return: response is empty
        """
        response = self.stub.EnableBooking(show_pb2.ShowEnableBookingRequest(
            show=self.data,
            enabled=value),
            timeout=Cuebot.Timeout)
        return response

    def enableDispatching(self, value):
        """Enables or disables dispatching on the show.

        :type value: bool
        :param value: whether to enable booking
        :rtype:  show_pb2.ShowEnableDispatchingResponse
        :return: response is empty
        """
        response = self.stub.EnableDispatching(show_pb2.ShowEnableDispatchingRequest(
            show=self.data,
            enabled=value),
            timeout=Cuebot.Timeout)
        return response

    def id(self):
        """Returns the show id.

        :rtype:  str
        :return: id of the show
        """
        return self.data.id

    def name(self):
        """Returns the show name.

        :rtype:  str
        :return: name of the show
        """
        return self.data.name

    def pendingJobs(self):
        """Returns the total number of pending jobs on the show.

        :rtype:  int
        :return: total number of pending jobs
        """
        return self.data.show_stats.pending_jobs

    def pendingFrames(self):
        """Returns the total number of running frames currently in the queue.

        :rtype:  int
        :return: the total number of pending frames
        """
        return self.data.show_stats.pending_frames

    def runningFrames(self):
        """Returns the total number of running frames currently in the queue.

        :rtype:  int
        :return: the total number of running frames
        """
        return self.data.show_stats.running_frames

    def deadFrames(self):
        """Returns the total number of dead frames currently in the queue.

        :rtype:  int
        :return: the total number dead frames
        """
        return self.data.show_stats.dead_frames

    def reservedCores(self):
        """Returns the total number of reserved cores by all frames.

        :rtype:  float
        :return: the total number of reserved cores
        """
        return self.data.show_stats.reserved_cores

    def defaultMinProcs(self):
        """Returns the default minProcs that new jobs are set to.

        :rtype:  int
        :return: default minProcs value for new jobs
        """
        return self.data.default_min_procs

    def defaultMaxProcs(self):
        """Returns the default maxProcs that new jobs are set to.

        :rtype:  int
        :return: default maxProcs value for new jobs
        """
        return self.data.default_max_procs

    def totalJobsCreated(self):
        """A running counter of jobs launched.

        :rtype:  int
        :return: total number of jobs created
        """
        return self.data.show_stats.created_job_count

    def totalFramesCreated(self):
        """A running counter of frames launched.

        :rtype:  int
        :return: total number of frames created
        """
        return self.data.show_stats.created_frame_count
