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
import os

from Cue3 import cue_pb2
from Cue3 import cue_pb2_grpc
from cuebot import Cuebot
from search import *
from exception import *
from util import *

def takesproxy(f):
    """takesproxy(func f)
    A decoratory that converts arguments from
    ice objects to a proxy allowing methods to take
    an ice object, a proxy, or a string id!"""
    def takesProxyFactory(uniq):
        o = f(id(uniq))
        return o
    return takesProxyFactory

#
# These are conviniennce methods that get imported into
# package namespace.
#
def getDefaultServices():
    """
    Return the default service list.  Services
    define the default application features.
    @rtype list<Service>
    """
    return Cuebot.Proxy.getDefaultServices()

def getService(id):
    """
    Return the default service list.  Services
    define the default application features.
    @rtype list<Service>
    """
    return Cuebot.Proxy.getService(id)

def createService(data):
    """
    Return the default service list.  Services
    define the default application features.
    @rtype list<Service>
    """
    return Cuebot.Proxy.createService(data)

# functions are in tree order, for example
# shows, groups, jobs, layers, frames, etc

def getSystemStats():
    """Returns the system stats for a random
    Cue3 server in the cluster.  This is used
    mainly by admins for troubleshooting Cue3
    problems.
    @rtype: SystemStats
    @return: a struct of Cue3 application information."""
    return Cuebot.Proxy.getSystemStats()

#
# Facility
#

def createFacility(name):
    stub = cue_pb2_grpc.FacilityInterfaceStub(Cuebot.RpcChannel)
    return stub.Create(cue_pb2.FacilityCreateRequest(name=name), timeout=Cuebot.Timeout)

def getFacility(name):
    """Return a given facility by name or unique ID.
    @type name: str
    @param name: A facility name or unique ID.
    @rtype: Facility
    @return: A facility object.
    """
    stub = cue_pb2_grpc.FacilityInterfaceStub(Cuebot.RpcChannel)
    return stub.Get(cue_pb2.FacilityGetRequest(name=name), timeout=Cuebot.Timeout)

def renameFacility(facility, new_name):
    stub = cue_pb2_grpc.FacilityInterfaceStub(Cuebot.RpcChannel)
    stub.Rename(cue_pb2.FacilityRenameRequest(facility=facility, new_name=new_name), timeout=Cuebot.Timeout)

def deleteFacility(name):
    stub = cue_pb2_grpc.FacilityInterfaceStub(Cuebot.RpcChannel)
    stub.Delete(cue_pb2.FacilityDeleteRequest(name=name), timeout=Cuebot.Timeout)

#
# Shows
#

def createShow(show):
    """Creates a new show
    @type  show: str
    @param show: A new show name to create
    @rtype:  Show
    @return: The created show object"""
    return Cuebot.Proxy.createShow(show)

def getShows():
    """Returns a list of show objects
    @rtype:  list<Show>
    @return: List of show objects"""
    return Cuebot.Proxy.getShows()

def getActiveShows():
    """Returns a list of all active shows.
    @rtype:  list<Show>
    @return: List of show objects"""
    return Cuebot.Proxy.getActiveShows()

def findShow(name):
    """Returns a list of show objects
    @type  name: str
    @param name: A string that represents a show to return.
    @rtype:  Show
    @return: List of show objects"""
    return Cuebot.Proxy.findShow(name)

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
    return Cuebot.Proxy.findGroup(show, group)

@takesproxy
def getGroup(uniq):
    """Returns a Group object from its uniq
    id or proxy.
    @rtype:  Group
    @return: The matching group object"""
    return Cuebot.Proxy.getGroup(uniq)

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
    return Cuebot.Proxy.isJobPending(name)

def findJob(name):
    """Returns a Job object for the given job name.
    This will only return one or zero active job.
    @type  name: str
    @param name: A job name
    @rtype:  Job
    @return: Job object"""
    return Cuebot.Proxy.findJob(name)

@takesproxy
def getJob(uniq):
    """Returns a Job object for the given job name.
    This will only return one or zero active job.
    @type  name: str
    @param name: A job name
    @rtype:  Job
    @return: Job object"""
    return Cuebot.Proxy.getJob(uniq)

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
    return JobSearch.byOptions(**options)

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
    s = JobSearch()
    s.setOptions(**options)
    return Cuebot.Proxy.getJobNames(s)

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
    return Cuebot.Proxy.findLayer(job, layer)

@takesproxy
def getLayer(uniq):
    """Returns a Layer object for the given layer id or proxy.
    @type  uniq: a unique identifier.
    @param uniq: an object, proxy, or id
    @rtype:  Layer
    @return: A Layer object"""
    return Cuebot.Proxy.getLayer(uniq)

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
    return Cuebot.Proxy.findFrame(job, layer, number)

@takesproxy
def getFrame(uniq):
    """Returns a Frame object from a unique frame identifier such
    as a Frame object, a proxy, or a unique id.
    @type  uniq: a unique identifier.
    @param uniq: an object, proxy, or id
    @rtype:  Frame
    @return: A Frame object"""
    return Cuebot.Proxy.getFrame(uniq)

def getFrames(job, **options):
    """Finds frames in a job that match the search critieria
    @type job: A uniquie job identifier.
    @param: An id, prx, object, or a job name.
    @rtype: List<Frame>
    @return: a list of matching frames"""
    try:
        j = proxy(job, "Job")
    except:
        j = findJob(job).proxy
    return j.getFrames(FrameSearch(**options))

#
# Depends
#
@takesproxy
def getDepend(uniq):
    """Finds a dependency from its unique ID
    @type id: str
    @param id: the depends' unique id
    @rtype: Depend
    @return: a dependency"""
    return Cuebot.Proxy.getDepend(uniq)

#
# Hosts
#
def getHostWhiteboard():
    """
    @rtype:  list<Host>
    @return: NestedHost """
    return Cuebot.Proxy.getHostWhiteboard()

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
    return HostSearch.byOptions(**options)

def findHost(name):
    """Returns the host for the matching hostname
    @type  name: str
    @param name: The unique name of a host
    @rtype:  Host
    @return: The matching host object"""
    return Cuebot.Proxy.findHost(name)

@takesproxy
def getHost(uniq):
    """Returns a Host object from a unique identifier
    @type  uniq: a unique identifier.
    @param uniq: an object, proxy, or id
    @rtype:  Host
    @return: A Host object"""
    return Cuebot.Proxy.getHost(uniq)

#
# Owners
#
def getOwner(id):
    """Return an Owner object from the id or name."""
    return Cuebot.Proxy.getOwner(id)

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
    return Cuebot.Proxy.findFilter(show_name,filter_name)

#
# Allocation
#
def createAllocation(name, tag):
    """Creates and returns an allocation.
    The host tag will be the lowercase of the allocation name.
    @type  name: str
    @param name: The name of the allocation
    @type  tag: str
    @param tag: The tag for the allocation
    @rtype:  Allocation
    @return: The created allocation object"""
    return Cuebot.Proxy.createAllocation(name, tag)

def getAllocations():
    """Returns a list of allocation objects
    @rtype:  list<Allocation>
    @return: List of allocation objects"""
    return Cuebot.Proxy.getAllocations()

def findAllocation(name):
    """Returns the Allocation object that matches the name.
    @type  name: str
    @param name: The name of the allocation
    @rtype:  Allocation
    @return: Allocation object"""
    return Cuebot.Proxy.findAllocation(name)

#
# Subscriptions
#
@takesproxy
def getSubscription(uniq):
    """Returns a Subscription object from a unique identifier
    @type  uniq: a unique identifier.
    @param uniq: an object, proxy, or id
    @rtype:  Subscription
    @return: A Subscription object"""
    return Cuebot.Proxy.getSubscription(uniq)

def findSubscription(name):
    """Returns the subscription object that matches the name.
    @type  name: str
    @param name: The name of the subscription
    @rtype:  Subscription
    @return: Subscription object"""
    return Cuebot.Proxy.findSubscription(name)

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
    return ProcSearch.byOptions(**options)


