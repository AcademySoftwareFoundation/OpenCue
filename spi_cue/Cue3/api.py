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
The Cue3 Static API.  This is exported into the package namespace.

Project: Cue3 Library

Module: API.py - Cue3 Library API.

Created: October 17, 2007

Contact: Middle-Tier Group 

SVN: $Id$
"""

import search
from cuebot import Cuebot
from Cue3.compiled_proto import cue_pb2
from Cue3.compiled_proto import depend_pb2
from Cue3.compiled_proto import facility_pb2
from Cue3.compiled_proto import filter_pb2
from Cue3.compiled_proto import host_pb2
from Cue3.compiled_proto import job_pb2
from Cue3.compiled_proto import service_pb2
from Cue3.compiled_proto import show_pb2
from Cue3.compiled_proto import subscription_pb2


#
# These are convenience methods that get imported into
# package namespace.
#
def getDefaultServices():
    """
    Return the default service list.  Services
    define the default application features.
    @rtype list<Service>
    """
    response = Cuebot.getStub('service').GetDefaultServices(
        service_pb2.ServiceGetDefaultServicesRequest(), timeout=Cuebot.Timeout)
    return response.services


def getService(id):
    """
    Return the default service list.  Services
    define the default application features.
    @rtype list<Service>
    """
    return Cuebot.getStub('service').GetService(
        service_pb2.ServiceGetServiceRequest(id), timeout=Cuebot.Timeout).service


def createService(data):
    """
    Return the default service list.  Services
    define the default application features.
    @rtype list<Service>
    """
    return Cuebot.getStub('service').CreateService(
        service_pb2.ServiceCreateServiceRequest(data), timeout=Cuebot.Timeout).service


def getSystemStats():
    """Returns the system stats for a random
    Cue3 server in the cluster.  This is used
    mainly by admins for troubleshooting Cue3
    problems.
    @rtype: SystemStats
    @return: a struct of Cue3 application information."""
    return Cuebot.getStub('cue').GetSystemStats(
        cue_pb2.CueGetSystemStatsRequest(), timeout=Cuebot.Timeout).stats


#
# Facility
#
def createFacility(name):
    return Cuebot.getStub('facility').Create(
        facility_pb2.FacilityCreateRequest(name=name), timeout=Cuebot.Timeout).facility


def getFacility(name):
    """Return a given facility by name or unique ID.
    @type name: str
    @param name: A facility name or unique ID.
    @rtype: Facility
    @return: A facility object.
    """
    return Cuebot.getStub('facility').Get(
        facility_pb2.FacilityGetRequest(name=name), timeout=Cuebot.Timeout).facility


def renameFacility(facility, new_name):
    Cuebot.getStub('facility').Rename(
        facility_pb2.FacilityRenameRequest(facility=facility, new_name=new_name),
        timeout=Cuebot.Timeout)


def deleteFacility(name):
    Cuebot.getStub('facility').Delete(
        facility_pb2.FacilityDeleteRequest(name=name), timeout=Cuebot.Timeout)


#
# Shows
#
def createShow(show):
    """Creates a new show
     @type  show: str
     @param show: A new show name to create
     @rtype:  Show
     @return: The created show object"""
    return Cuebot.getStub('show').CreateShow(
        show_pb2.ShowCreateShowRequest(name=show), timeout=Cuebot.Timeout).show


def deleteShow(show_id):
    """Deletes a show
     @type  show_id: str
     @param show_id: A show id to delete"""
    Cuebot.getStub('show').DeleteShow(
        show_pb2.ShowDeleteRequest(show_id=show_id), timeout=Cuebot.Timeout)


def getShows():
    """Returns a list of show objects
    @rtype:  list<Show>
    @return: List of show objects"""
    response = Cuebot.getStub('show').GetShows(
        show_pb2.ShowGetShowsRequest(), timeout=Cuebot.Timeout)
    return response.shows


def getActiveShows():
    """Returns a list of all active shows.
    @rtype:  list<Show>
    @return: List of show objects"""
    response = Cuebot.getStub('show').GetActiveShows(
        show_pb2.ShowGetActiveShowsRequest(), timeout=Cuebot.Timeout)
    return response.shows


def findShow(name):
    """Returns a list of show objects
    @type  name: str
    @param name: A string that represents a show to return.
    @rtype:  Show
    @return: List of show objects"""
    return Cuebot.getStub('show').FindShow(
        show_pb2.ShowFindShowRequest(name=name), timeout=Cuebot.Timeout).show

#
# Groups
#


def findGroup(show, group):
    """Returns a group object
    @type  show: str
    @param show: The name of a show
    @type  group: str
    @param group: The name of a group
    @rtype:  Group
    @return: The matching group object"""
    return Cuebot.getStub('group').FindGroup(
        job_pb2.GroupFindGroupRequest(show=show, name=group), timeout=Cuebot.Timeout).group


def getGroup(uniq):
    """Returns a Group object from its uniq id.
    @rtype:  Group
    @return: The matching group object"""
    return Cuebot.getStub('group').GetGroup(
        job_pb2.GroupGetGroupRequest(id=uniq), timeout=Cuebot.Timeout).group


#
# Jobs
#
def isJobPending(name):
    """Returns true if there is an active job in the cue
    in the pendint state.
    @type  name: str
    @param name: A job name
    @rtype: bool
    @return: true if the job exists"""
    return Cuebot.getStub('job').IsJobPending(
        job_pb2.JobIsJobPendingRequest(name=name), timeout=Cuebot.Timeout).value


def findJob(name):
    """Returns a Job object for the given job name.
    This will only return one or zero active job.
    @type  name: str
    @param name: A job name
    @rtype:  Job
    @return: Job object"""
    return Cuebot.getStub('job').FindJob(
        job_pb2.JobFindJobRequest(name=name), timeout=Cuebot.Timeout).job


def getJob(uniq):
    """Returns a Job object for the given job name.
    This will only return one or zero active job.
    @type  name: str
    @param name: A job name
    @rtype:  Job
    @return: Job object"""
    return Cuebot.getStub('job').GetJob(
        job_pb2.JobGetJobRequest(id=uniq), timeout=Cuebot.Timeout).job


def getJobs(**options):
    """
    Returns an array of Job objects using
    optional search criteria. Search criteria is
    supplied as a variable list of arguments.

    For example:
    getJobs(show=["pipe"]) would return only pipe jobs.

    Possible args:
        - job: job names
        - match:  job name substring match
        - regex: a job name search by regular expression
        - id: a job search by unique id
        - show: show names
        - shot: shot names
        - user: user names

    @rtype:  List<Job>
    @return: a list of jobs
    """
    criteria = search.JobSearch.criteriaFromOptions(**options)
    return Cuebot.getStub('job').GetJobs(
        job_pb2.JobGetJobsRequest(r=criteria), timeout=Cuebot.Timeout).jobs


#
# Job Names
#
def getJobNames(**options):
    """Returns a list of job names that match the search parameters.
    See getJobs for the job query options.
    @type  options: dict
    @param options: a variable list of search criteria
    @rtype:  list<str>
    @return: List of matching job names"""
    criteria = search.JobSearch.criteriaFromOptions(**options)
    return Cuebot.getStub('job').GetJobNames(
        job_pb2.JobGetJobNamesRequest(r=criteria), timeout=Cuebot.Timeout).names


#
# Layers
#
def findLayer(job, layer):
    """Finds and returns a layer from the specified pending job
    @type job: str
    @param job: the job name
    @type layer: str
    @param layer: the layer name
    @rtype: Layer
    @return: the layer matching the query"""
    return Cuebot.getStub('layer').FindLayer(
        job_pb2.LayerFindLayerRequest(job=job, layer=layer), timeout=Cuebot.Timeout).layer


def getLayer(uniq):
    """Returns a Layer object for the given layer id.
    @type  uniq: a unique identifier.
    @param uniq: id
    @rtype:  Layer
    @return: A Layer object"""
    return Cuebot.getStub('layer').GetLayer(
        job_pb2.LayerGetLayerRequest(id=uniq), timeout=Cuebot.Timeout).layer


#
# Frames
#
def findFrame(job, layer, number):
    """Finds and returns a layer from the specified pending job
    @type job: str
    @param job: the job name
    @type layer: str
    @param layer: the layer name
    @type number: int
    @param number: the frame number
    @rtype: Frame
    @return: the frame matching the query"""
    return Cuebot.getStub('frame').FindFrame(
        job_pb2.FrameFindFrameRequest(job=job, layer=layer, frame=number),
        timeout=Cuebot.Timeout).frame


def getFrame(uniq):
    """Returns a Frame object from the unique id.
    @type  uniq: a unique identifier.
    @param uniq: id
    @rtype:  Frame
    @return: A Frame object"""
    return Cuebot.getStub('frame').GetFrame(
        job_pb2.FrameGetFrameRequest(id=uniq), timeout=Cuebot.Timeout).frame


def getFrames(job, **options):
    """Finds frames in a job that match the search critieria
    @type job: A unique job identifier.
    @param: An id
    @rtype: List<Frame>
    @return: a list of matching frames"""
    criteria = search.FrameSearch.criteriaFromOptions(**options)
    return Cuebot.getStub('frame').GetFrames(
        job_pb2.FrameGetFramesRequest(job=job, r=criteria), timeout=Cuebot.Timeout).frames


#
# Depends
#
def getDepend(uniq):
    """Finds a dependency from its unique ID
    @type id: str
    @param id: the depends' unique id
    @rtype: Depend
    @return: a dependency"""
    return Cuebot.getStub('depend').GetDepend(
        depend_pb2.DependGetDependRequest(id=uniq), timeout=Cuebot.Timeout).depend


#
# Hosts
#
def getHostWhiteboard():
    """
    @rtype:  list<Host>
    @return: NestedHost """
    return Cuebot.getStub('host').GetHostWhiteboard(host_pb2.HostGetHostWhiteboardRequest(),
                                                    timeout=Cuebot.Timeout).nested_hosts


def getHosts(**options):
    """
    Returns an array of Hroc objects using
    optional search criteria. Search criteria is
    supplied as a variable list of arguments.

    For example:
    getHosts(match=["vrack"]) would return all vrack procs.

    Possible args:
       - host: host names
       - match: host name substring match
       - regex: a host name search by regular expression
       - id: a search by unique id
       - alloc: search by allocation.

    @rtype:  List<Host>
    @return: a list of hosts
    """
    return search.HostSearch.byOptions(**options).hosts


def findHost(name):
    """Returns the host for the matching hostname
    @type  name: str
    @param name: The unique name of a host
    @rtype:  Host
    @return: The matching host object"""
    return Cuebot.getStub('host').FindHost(
        host_pb2.HostFindHostRequest(name=name), timeout=Cuebot.Timeout).host


def getHost(uniq):
    """Returns a Host object from a unique identifier
    @type  uniq: a unique identifier.
    @param uniq: an id
    @rtype:  Host
    @return: A Host object"""
    return Cuebot.getStub('host').GetHost(
        host_pb2.HostGetHostsRequest(id=uniq), timeout=Cuebot.Timeout).host


#
# Owners
#
def getOwner(id):
    """Return an Owner object from the id or name."""
    return Cuebot.getStub('owner').GetOwner(
        host_pb2.OwnerGetOwnerRequest(name=id), timout=Cuebot.Timeout).owner

#
# Filters
#
def findFilter(show_name, filter_name):
    """Returns the matching filter(for testing)
    @type  show_name: str
    @param show_name: a show name
    @type  filter_name: str
    @param filter_name: a filter name
    @rtype:  Filter
    @return: The matching filter"""
    return Cuebot.getStub('filter').FindFilter(
        filter_pb2.FilterFindFilterRequest(show=show_name, name=filter_name),
        timeout=Cuebot.Timeout).filter

#
# Allocation
#
def createAllocation(name, tag, facility):
    """Creates and returns an allocation.
    The host tag will be the lowercase of the allocation name.
    @type  name: str
    @param name: The name of the allocation
    @type  tag: str
    @param tag: The tag for the allocation
    @rtype:  Allocation
    @return: The created allocation object"""
    return Cuebot.getStub('allocation').Create(
        facility_pb2.AllocCreateRequest(name=name, tag=tag, facility=facility),
        timeout=Cuebot.Timeout).allocation


def getAllocations():
    """Returns a list of allocation objects
    @rtype:  list<Allocation>
    @return: List of allocation objects"""
    return Cuebot.getStub('allocation').GetAll(
        facility_pb2.AllocGetAllRequest(), timeout=Cuebot.Timeout).allocations


def findAllocation(name):
    """Returns the Allocation object that matches the name.
    @type  name: str
    @param name: The name of the allocation
    @rtype:  Allocation
    @return: Allocation object"""
    return Cuebot.getStub('allocation').Find(
        facility_pb2.AllocFindRequest(name=name), timeout=Cuebot.Timeout).allocation


def getAllocation(allocId):
    return Cuebot.getStub('allocation').Get(
        facility_pb2.AllocGetRequest(id=allocId), timeout=Cuebot.Timeout).allocations


def deleteAllocation(alloc):
    return Cuebot.getStub('allocation').Delete(
        facility_pb2.AllocDeleteRequest(allocation=alloc), timeout=Cuebot.Timeout)


def allocSetBillable(alloc, is_billable):
    return Cuebot.getStub('allocation').SetBillable(
        facility_pb2.AllocSetBillableRequest(allocation=alloc, value=is_billable),
        timeout=Cuebot.Timeout)


def allocSetName(alloc, name):
    return Cuebot.getStub('allocation').SetName(
        facility_pb2.AllocSetNameRequest(allocation=alloc, name=name), timeout=Cuebot.Timeout)


def allocSetTag(alloc, tag):
    return Cuebot.getStub('allocation').SetTag(
        facility_pb2.AllocSetTagRequest(allocation=alloc, tag=tag), timeout=Cuebot.Timeout)


#
# Subscriptions
#
def getSubscription(uniq):
    """Returns a Subscription object from a unique identifier
    @type  uniq: a unique identifier.
    @param uniq: an id
    @rtype:  Subscription
    @return: A Subscription object"""
    return Cuebot.getStub('subscription').Get(
        subscription_pb2.SubscriptionGetRequest(id=uniq), timeout=Cuebot.Timeout).subscription

def findSubscription(name):
    """Returns the subscription object that matches the name.
    @type  name: str
    @param name: The name of the subscription
    @rtype:  Subscription
    @return: Subscription object"""
    return Cuebot.getStub('subscription').Find(
        subscription_pb2.SubscriptionFindRequest(name=name), timeout=Cuebot.Timeout).subscription

#
# Procs
#
def getProcs(**options):
    """Returns an array of Proc objects using
    optional search criteria. Search criteria is
    supplied as a variable list of arguments.

    For example:
    getProcs(show=["pipe"]) would return procs running pipe jobs.

    Possible args:
       - host: host names
       - jobs: job names
       - layer: layer names
       - show: show names
       - alloc: allocation names
       - memory: used memory in gigabytes
         - "gt5" is greater than 5 gigs
         - "lt5" is less than 5 gigs
         - "5-10" is range of 5 to 10 gigs
       - duration: run time in hours
         - "gt5" is greater than 5 hours
         - "lt5" is less than 5 hours
         - "5-10" is range of 5 to 10 hours

    @rtype:  List<Proc>
    @return: a list of procs"""
    return search.ProcSearch.byOptions(**options).procs
