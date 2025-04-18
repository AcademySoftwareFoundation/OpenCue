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

"""The OpenCue static API."""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from opencue_proto import comment_pb2
from opencue_proto import criterion_pb2
from opencue_proto import cue_pb2
from opencue_proto import department_pb2
from opencue_proto import depend_pb2
from opencue_proto import facility_pb2
from opencue_proto import filter_pb2
from opencue_proto import host_pb2
from opencue_proto import job_pb2
from opencue_proto import limit_pb2
from opencue_proto import renderPartition_pb2
from opencue_proto import report_pb2
from opencue_proto import service_pb2
from opencue_proto import show_pb2
from opencue_proto import subscription_pb2
from opencue_proto import task_pb2
from .cuebot import Cuebot
# pylint: disable=cyclic-import
from .wrappers.allocation import Allocation
from .wrappers.comment import Comment
from .wrappers.depend import Depend
from .wrappers.filter import Action
from .wrappers.filter import Filter
from .wrappers.filter import Matcher
from .wrappers.frame import Frame
from .wrappers.group import Group
from .wrappers.host import Host, NestedHost
from .wrappers.job import Job
from .wrappers.layer import Layer
from .wrappers.limit import Limit
from .wrappers.owner import Owner
from .wrappers.proc import Proc
from .wrappers.service import Service
from .wrappers.show import Show
from .wrappers.subscription import Subscription
from .wrappers.task import Task
from . import search
from . import util


__protobufs = [comment_pb2, criterion_pb2, cue_pb2, department_pb2, depend_pb2, facility_pb2,
               filter_pb2, host_pb2, job_pb2, renderPartition_pb2, report_pb2, service_pb2,
               show_pb2, subscription_pb2, task_pb2]

__wrappers = [Action, Allocation, Comment, Depend, Filter, Frame, Group, Host, Job, Layer, Matcher,
              NestedHost, Proc, Show, Subscription, Task]


#
# These are convenience methods that get imported into
# the package namespace.
#
@util.grpcExceptionParser
def getDefaultServices():
    """
    Return the default service list.  Services
    define the default application features.

    :rtype: list
    :return: List of Service objects
    """
    return Service.getDefaultServices()


@util.grpcExceptionParser
def getService(name):
    """
    Return the service with the provided name.

    :type name: str
    :param name: the name of the service
    :rtype: Service
    """
    return Service.getService(name)


@util.grpcExceptionParser
def createService(data):
    """
    Create the provided service and return it.

    :type data: Service
    :param data: Service object to create
    :rtype: Service
    """
    return Service(data).create()


@util.grpcExceptionParser
def getSystemStats():
    """Returns the system stats for a random
    OpenCue server in the cluster. This is used
    mainly by admins for troubleshooting OpenCue
    problems.

    :rtype: SystemStats
    :return: a struct of OpenCue application information."""
    return Cuebot.getStub('cue').GetSystemStats(
        cue_pb2.CueGetSystemStatsRequest(), timeout=Cuebot.Timeout).stats


#
# Facility
#
@util.grpcExceptionParser
def createFacility(name):
    """Create a given facility by name or unique ID.

    :type name: str
    :param name: a facility name or unique ID
    :rtype: Facility
    :return: a facility object
    """
    return Cuebot.getStub('facility').Create(
        facility_pb2.FacilityCreateRequest(name=name), timeout=Cuebot.Timeout).facility


@util.grpcExceptionParser
def getFacility(name):
    """Return a given facility by name or unique ID.

    :type name: str
    :param name: a facility name or unique ID
    :rtype: Facility
    :return: a facility object
    """
    return Cuebot.getStub('facility').Get(
        facility_pb2.FacilityGetRequest(name=name), timeout=Cuebot.Timeout).facility


@util.grpcExceptionParser
def renameFacility(facility, new_name):
    """Rename a given facility by name or unique ID.

    :type facility: str
    :param facility: an existing facility name or unique ID
    :type new_name: str
    :param new_name: a new facility name or unique ID
    """
    Cuebot.getStub('facility').Rename(
        facility_pb2.FacilityRenameRequest(facility=facility, new_name=new_name),
        timeout=Cuebot.Timeout)


@util.grpcExceptionParser
def deleteFacility(name):
    """Delete a given facility by name or unique ID.

    :type name: str
    :param name: a facility name or unique ID
    """
    Cuebot.getStub('facility').Delete(
        facility_pb2.FacilityDeleteRequest(name=name), timeout=Cuebot.Timeout)


#
# Departments
#
@util.grpcExceptionParser
def getDepartmentNames():
    """Return a list of the known department names.

    :rtype: list
    :return: a list of str department names
    """
    return list(Cuebot.getStub('department').GetDepartmentNames(
        department_pb2.DeptGetDepartmentNamesRequest(), timeout=Cuebot.Timeout).names)


#
# Shows
#
@util.grpcExceptionParser
def createShow(show):
    """Creates a new show.

     :type  show: str
     :param show: a new show name to create
     :rtype:  Show
     :return: the created show object"""
    return Show(Cuebot.getStub('show').CreateShow(
        show_pb2.ShowCreateShowRequest(name=show), timeout=Cuebot.Timeout).show)


@util.grpcExceptionParser
def deleteShow(show_id):
    """Deletes a show.

     :type  show_id: str
     :param show_id: a show ID to delete"""
    show = findShow(show_id)
    Cuebot.getStub('show').Delete(
        show_pb2.ShowDeleteRequest(show=show.data), timeout=Cuebot.Timeout)


@util.grpcExceptionParser
def getShows():
    """Returns a list of show objects.

    :rtype:  list
    :return: a list of Show objects"""
    showSeq = Cuebot.getStub('show').GetShows(
        show_pb2.ShowGetShowsRequest(), timeout=Cuebot.Timeout).shows
    return [Show(s) for s in showSeq.shows]


@util.grpcExceptionParser
def getActiveShows():
    """Returns a list of all active shows.

    :rtype:  list
    :return: a list of Show objects"""
    showSeq = Cuebot.getStub('show').GetActiveShows(
        show_pb2.ShowGetActiveShowsRequest(), timeout=Cuebot.Timeout).shows
    return [Show(s) for s in showSeq.shows]


@util.grpcExceptionParser
def findShow(name):
    """Returns a list of show objects.

    :type  name: str
    :param name: a string that represents a show to return
    :rtype:  Show
    :return: the matching Show object"""
    return Show(Cuebot.getStub('show').FindShow(
        show_pb2.ShowFindShowRequest(name=name), timeout=Cuebot.Timeout).show)


#
# Groups
#
@util.grpcExceptionParser
def findGroup(show, group):
    """Returns a group object.

    :type  show: str
    :param show: the name of a show
    :type  group: str
    :param group: the name of a group
    :rtype:  Group
    :return: the matching group object"""
    return Group(Cuebot.getStub('group').FindGroup(
        job_pb2.GroupFindGroupRequest(show=show, name=group), timeout=Cuebot.Timeout).group)


@util.grpcExceptionParser
def getGroup(uniq):
    """Returns a Group object from its unique ID.

    :type  uniq: str
    :param uniq: a unique group identifier
    :rtype:  Group
    :return: the matching group object"""
    return Group(Cuebot.getStub('group').GetGroup(
        job_pb2.GroupGetGroupRequest(id=uniq), timeout=Cuebot.Timeout).group)


#
# Jobs
#
@util.grpcExceptionParser
def findJob(name):
    """Returns a Job object for the given job name.
    This will only return one or zero active job.

    :type  name: str
    :param name: a job name
    :rtype:  Job
    :return: a Job object"""
    return Job(Cuebot.getStub('job').FindJob(
        job_pb2.JobFindJobRequest(name=name), timeout=Cuebot.Timeout).job)


@util.grpcExceptionParser
def getJob(uniq):
    """Returns a Job object for the given job ID.
    This will only return one or zero active job.

    :type  uniq: str
    :param uniq: a unique job identifier
    :rtype:  Job
    :return: a Job object"""
    return Job(Cuebot.getStub('job').GetJob(
        job_pb2.JobGetJobRequest(id=uniq), timeout=Cuebot.Timeout).job)


@util.grpcExceptionParser
def getJobs(**options):
    """
    Returns an array of Job objects using
    optional search criteria. Search criteria is
    supplied as a variable list of arguments.

    For example::

        # returns only pipe jobs.
        getJobs(show=["pipe"])

    Possible args:
        - job: job names - list
        - match:  job name substring match - str
        - regex: a job name search by regular expression - str
        - id: a job search by unique id - str
        - show: show names - list
        - shot: shot names - list
        - user: user names - list
        - include_finished - bool

    :rtype:  list
    :return: a list of Job objects
    """
    criteria = search.JobSearch.criteriaFromOptions(**options)
    jobSeq = Cuebot.getStub('job').GetJobs(
        job_pb2.JobGetJobsRequest(r=criteria), timeout=Cuebot.Timeout).jobs
    return [Job(j) for j in jobSeq.jobs]


@util.grpcExceptionParser
def isJobPending(name):
    """Returns true if there is an active job in the cue
    in the pending state.

    :type  name: str
    :param name: a job name
    :rtype: bool
    :return: true if the job exists"""
    return Cuebot.getStub('job').IsJobPending(
        job_pb2.JobIsJobPendingRequest(name=name), timeout=Cuebot.Timeout).value


@util.grpcExceptionParser
def launchSpec(spec):
    """Launch a new job with the given spec xml data.
    This call returns immediately but there is guarantee that
    the job was written to the database.

    :type spec: str
    :param spec: XML string containing job spec
    :rtype: list
    :return: List of str job names that were submitted
    """
    return Cuebot.getStub('job').LaunchSpec(
        job_pb2.JobLaunchSpecRequest(spec=spec), timeout=Cuebot.Timeout).names


@util.grpcExceptionParser
def launchSpecAndWait(spec):
    """Launch a new job with the given spec xml data.
    This call waits on the server until the job is committed
    in the database.

    :type spec: str
    :param spec: XML string containing job spec
    :rtype: list
    :return: List of Job objects that were submitted
    """
    jobSeq = Cuebot.getStub('job').LaunchSpecAndWait(
        job_pb2.JobLaunchSpecAndWaitRequest(spec=spec), timeout=Cuebot.Timeout).jobs
    return [Job(j) for j in jobSeq.jobs]


#
# Job Names
#
@util.grpcExceptionParser
def getJobNames(**options):
    """Returns a list of job names that match the search parameters.
    See getJobs for the job query options.

    :rtype:  list
    :return: List of matching str job names"""
    criteria = search.JobSearch.criteriaFromOptions(**options)
    return Cuebot.getStub('job').GetJobNames(
        job_pb2.JobGetJobNamesRequest(r=criteria), timeout=Cuebot.Timeout).names


#
# Layers
#
@util.grpcExceptionParser
def findLayer(job, layer):
    """Finds and returns a layer from the specified pending job.

    :type job: str
    :param job: the job name
    :type layer: str
    :param layer: the layer name
    :rtype: opencue.wrappers.layer.Layer
    :return: the layer matching the query"""
    return Layer(Cuebot.getStub('layer').FindLayer(
        job_pb2.LayerFindLayerRequest(job=job, layer=layer), timeout=Cuebot.Timeout).layer)


@util.grpcExceptionParser
def getLayer(uniq):
    """Returns a Layer object for the given layer ID.

    :type  uniq: str
    :param uniq: a unique layer identifier
    :rtype:  opencue.wrappers.layer.Layer
    :return: a Layer object"""
    return Layer(Cuebot.getStub('layer').GetLayer(
        job_pb2.LayerGetLayerRequest(id=uniq), timeout=Cuebot.Timeout).layer)


#
# Frames
#
@util.grpcExceptionParser
def findFrame(job, layer, number):
    """Finds and returns a layer from the specified pending job.

    :type job: str
    :param job: the job name
    :type layer: str
    :param layer: the layer name
    :type number: int
    :param number: the frame number
    :rtype: opencue.wrappers.frame.Frame
    :return: the frame matching the query"""
    return Frame(Cuebot.getStub('frame').FindFrame(
        job_pb2.FrameFindFrameRequest(job=job, layer=layer, frame=number),
        timeout=Cuebot.Timeout).frame)


@util.grpcExceptionParser
def getFrame(uniq):
    """Returns a Frame object from the unique ID.

    :type  uniq: str
    :param uniq: a unique frame identifier
    :rtype:  opencue.wrappers.frame.Frame
    :return: a Frame object"""
    return Frame(Cuebot.getStub('frame').GetFrame(
        job_pb2.FrameGetFrameRequest(id=uniq), timeout=Cuebot.Timeout).frame)


@util.grpcExceptionParser
def getFrames(job, **options):
    """Finds frames in a job that match the search criteria.

    :type job: str
    :param job: the job name
    :rtype: list
    :return: a list of matching Frame objects"""
    criteria = search.FrameSearch.criteriaFromOptions(**options)
    framesSeq = Cuebot.getStub('frame').GetFrames(
        job_pb2.FrameGetFramesRequest(job=job, r=criteria), timeout=Cuebot.Timeout).frames
    return [Frame(f) for f in framesSeq.frames]


#
# Depends
#
@util.grpcExceptionParser
def getDepend(uniq):
    """Finds a dependency from its unique ID.

    :type id: str
    :param id: the unique ID of the Depend object
    :rtype: opencue.wrappers.depend.Depend
    :return: a dependency"""
    return Depend(Cuebot.getStub('depend').GetDepend(
        depend_pb2.DependGetDependRequest(id=uniq), timeout=Cuebot.Timeout).depend)


#
# Hosts
#
@util.grpcExceptionParser
def getHostWhiteboard():
    """
    :rtype:  list<Host>
    :return: NestedHost """
    nestedHostSeq = Cuebot.getStub('host').GetHostWhiteboard(
        host_pb2.HostGetHostWhiteboardRequest(),
        timeout=Cuebot.Timeout).nested_hosts
    return [NestedHost(nh) for nh in nestedHostSeq.nested_hosts]


@util.grpcExceptionParser
def getHosts(**options):
    """
    Returns an array of Hroc objects using
    optional search criteria. Search criteria is
    supplied as a variable list of arguments.

    For example::

       # returns all vrack procs
       getHosts(match=["vrack"])

    Possible args:
       - host: host names - list
       - match: host name substring match - str
       - regex: a host name search by regular expression - str
       - id: a search by unique id - str
       - alloc: search by allocation. - list

    :rtype:  list
    :return: a list of Host objects
    """
    return search.HostSearch.byOptions(**options)


@util.grpcExceptionParser
def findHost(name):
    """Returns the host for the matching hostname.

    :type  name: str
    :param name: the unique name of a host
    :rtype:  Host
    :return: The matching host object"""
    return Host(Cuebot.getStub('host').FindHost(
        host_pb2.HostFindHostRequest(name=name), timeout=Cuebot.Timeout).host)


@util.grpcExceptionParser
def getHost(uniq):
    """Returns a Host object from a unique identifier.

    :type  uniq: str
    :param uniq: a unique host identifier
    :rtype:  Host
    :return: A Host object"""
    return Host(Cuebot.getStub('host').GetHost(
        host_pb2.HostGetHostRequest(id=uniq), timeout=Cuebot.Timeout).host)


#
# Owners
#
@util.grpcExceptionParser
def getOwner(owner_id):
    """Return an Owner object from the ID or name.

    :type  owner_id: str
    :param owner_id: a unique owner identifier or name
    :rtype:  Owner
    :return: An Owner object"""
    return Owner(Cuebot.getStub('owner').GetOwner(
        host_pb2.OwnerGetOwnerRequest(name=owner_id), timeout=Cuebot.Timeout).owner)

#
# Filters
#
@util.grpcExceptionParser
def findFilter(show_name, filter_name):
    """Returns the matching filter (for testing).

    :type  show_name: str
    :param show_name: a show name
    :type  filter_name: str
    :param filter_name: a filter name
    :rtype:  Filter
    :return: the matching Filter object"""
    return Filter(Cuebot.getStub('filter').FindFilter(
        filter_pb2.FilterFindFilterRequest(show=show_name, name=filter_name),
        timeout=Cuebot.Timeout).filter)

#
# Allocation
#
@util.grpcExceptionParser
def createAllocation(name, tag, facility):
    """Creates and returns an allocation.
    The host tag will be the lowercase of the allocation name.

    :type  name: str
    :param name: the name of the allocation
    :type  tag: str
    :param tag: the tag for the allocation
    :rtype:  Allocation
    :return: the newly created Allocation object"""
    return Allocation(Cuebot.getStub('allocation').Create(
        facility_pb2.AllocCreateRequest(name=name, tag=tag, facility=facility),
        timeout=Cuebot.Timeout).allocation)


@util.grpcExceptionParser
def getAllocations():
    """Returns a list of allocation objects.

    :rtype:  list
    :return: a list of Allocation objects"""
    allocationSeq = Cuebot.getStub('allocation').GetAll(
        facility_pb2.AllocGetAllRequest(), timeout=Cuebot.Timeout).allocations
    return [Allocation(a) for a in allocationSeq.allocations]


@util.grpcExceptionParser
def findAllocation(name):
    """Returns the Allocation object that matches the name.

    :type  name: str
    :param name: fully qualified name of the allocation (facility.allocation)
    :rtype:  Allocation
    :return: an Allocation object"""
    return Allocation(Cuebot.getStub('allocation').Find(
        facility_pb2.AllocFindRequest(name=name), timeout=Cuebot.Timeout).allocation)


@util.grpcExceptionParser
def getAllocation(allocId):
    """Returns the Allocation object that matches the ID.

    :type  allocId: str
    :param allocId: the ID of the allocation
    :rtype:  Allocation
    :return: an Allocation object"""
    return Allocation(Cuebot.getStub('allocation').Get(
        facility_pb2.AllocGetRequest(id=allocId), timeout=Cuebot.Timeout).allocation)


@util.grpcExceptionParser
def deleteAllocation(alloc):
    """Deletes an allocation.

    :type  alloc: facility_pb2.Allocation
    :param alloc: allocation to delete
    :rtype:  facility_pb2.AllocDeleteResponse
    :return: empty response"""
    return Cuebot.getStub('allocation').Delete(
        facility_pb2.AllocDeleteRequest(allocation=alloc), timeout=Cuebot.Timeout)


@util.grpcExceptionParser
def getDefaultAllocation():
    """Get the default allocation.

    :rtype:  Allocation
    :return: an Allocation object"""
    return Allocation(Cuebot.getStub('allocation').GetDefault(
        facility_pb2.AllocGetDefaultRequest(), timeout=Cuebot.Timeout).allocation)


@util.grpcExceptionParser
def setDefaultAllocation(alloc):
    """Set the default allocation.

    :type  alloc: facility_pb2.Allocation
    :param alloc: allocation to set default
    :rtype:  facility_pb2.AllocSetDefaultResponse
    :return: empty response"""
    return Cuebot.getStub('allocation').SetDefault(
        facility_pb2.AllocSetDefaultRequest(allocation=alloc), timeout=Cuebot.Timeout)


@util.grpcExceptionParser
def allocSetBillable(alloc, is_billable):
    """Sets an allocation billable or not.

    :type  alloc: facility_pb2.Allocation
    :param alloc: allocation to set
    :type  is_billable: bool
    :param is_billable: whether alloc should be billable or not
    :rtype:  facility_pb2.AllocSetBillableResponse
    :return: empty response
    """
    alloc.name = alloc.name.split(".")[-1]
    return Cuebot.getStub('allocation').SetBillable(
        facility_pb2.AllocSetBillableRequest(allocation=alloc, value=is_billable),
        timeout=Cuebot.Timeout)


@util.grpcExceptionParser
def allocSetName(alloc, name):
    """Sets an allocation name.

    :type  alloc: facility_pb2.Allocation
    :param alloc: allocation to set
    :type  name: str
    :param name: new name for the allocation
    :rtype:  facility_pb2.AllocSetNameResponse
    :return: empty response"""
    return Cuebot.getStub('allocation').SetName(
        facility_pb2.AllocSetNameRequest(allocation=alloc, name=name), timeout=Cuebot.Timeout)


@util.grpcExceptionParser
def allocSetTag(alloc, tag):
    """Sets an allocation tag.

    :type  alloc: facility_pb2.Allocation
    :param alloc: allocation to tag
    :type  tag: str
    :param tag: new tag
    :rtype:  facility_pb2.AllocSetTagResponse
    :return: empty response"""
    return Cuebot.getStub('allocation').SetTag(
        facility_pb2.AllocSetTagRequest(allocation=alloc, tag=tag), timeout=Cuebot.Timeout)


#
# Subscriptions
#
@util.grpcExceptionParser
def getSubscription(uniq):
    """Returns a Subscription object from a unique identifier.

    :type  uniq: str
    :param uniq: a unique subscription identifier
    :rtype:  Subscription
    :return: a Subscription object"""
    return Subscription(Cuebot.getStub('subscription').Get(
        subscription_pb2.SubscriptionGetRequest(id=uniq), timeout=Cuebot.Timeout).subscription)

@util.grpcExceptionParser
def findSubscription(name):
    """Returns the subscription object that matches the name.

    :type  name: str
    :param name: the name of the subscription
    :rtype:  Subscription
    :return: a Subscription object"""
    return Subscription(Cuebot.getStub('subscription').Find(
        subscription_pb2.SubscriptionFindRequest(name=name), timeout=Cuebot.Timeout).subscription)

#
# Procs
#
@util.grpcExceptionParser
def getProcs(**options):
    """Returns an array of Proc objects using
    optional search criteria. Search criteria is
    supplied as a variable list of arguments.

    For example::

        # returns procs running pipe jobs
        getProcs(show=["pipe"])

    Possible args:
       - host: host names - list
       - jobs: job names - list
       - layer: layer names - list
       - show: show names - list
       - alloc: allocation names - list
       - memory: used memory in gigabytes - str
         - "gt5" is greater than 5 gigs
         - "lt5" is less than 5 gigs
         - "5-10" is range of 5 to 10 gigs
       - duration: run time in hours - str
         - "gt5" is greater than 5 hours
         - "lt5" is less than 5 hours
         - "5-10" is range of 5 to 10 hours

    :rtype:  list[opencue.wrapper.proc.Proc]
    :return: a list of Proc objects"""
    procSeq = search.ProcSearch.byOptions(**options).procs
    return [Proc(p) for p in procSeq.procs]

#
# Limits
#
@util.grpcExceptionParser
def createLimit(name, maxValue):
    """Create a new Limit with the given name and max value.

    :type name: str
    :param name: the name of the new Limit
    :type maxValue: int
    :param maxValue: the maximum number of running frames for this limit
    :rtype: opencue.wrappers.limit.Limit
    :return: the newly created Limit
    """
    return Limit(Cuebot.getStub('limit').Create(
        limit_pb2.LimitCreateRequest(name=name, max_value=maxValue), timeout=Cuebot.Timeout))

@util.grpcExceptionParser
def getLimits():
    """Return a list of all known Limit objects.

    :rtype: list
    :return: a list of Limit objects"""
    return [Limit(limit) for limit in Cuebot.getStub('limit').GetAll(
        limit_pb2.LimitGetAllRequest(), timeout=Cuebot.Timeout).limits]

@util.grpcExceptionParser
def findLimit(name):
    """Returns the Limit object that matches the name.

    :type  name: str
    :param name: a string that represents a limit to return
    :rtype:  Limit
    :return: the matching Limit object"""
    return Limit(Cuebot.getStub('limit').Find(
        limit_pb2.LimitFindRequest(name=name), timeout=Cuebot.Timeout).limit)
