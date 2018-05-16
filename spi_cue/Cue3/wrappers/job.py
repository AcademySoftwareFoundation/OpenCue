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

Module: job.py - Cue3 Library implementation of a job

Created: February 12, 2008

Contact: Middle-Tier Group (middle-tier@imageworks.com)

SVN: $Id$
"""
import os
import time
import datetime

import cue.CueClientIce as CueClientIce
import cue.CueIce as CueIce

from ..search import *


class Job(CueClientIce.Job):
    """This class contains the ice implementation related to a job."""
    def __init__(self):
        """_Job class initialization"""
        CueClientIce.Job.__init__(self)

    def kill(self):
        """Kills the job"""
        self.proxy.kill()

    def pause(self):
        """Pauses the job"""
        self.proxy.pause()

    def resume(self):
        """Resumes the job"""
        self.proxy.resume()

    def killFrames(self, **request):
        """Kills all frames that match the FrameSearch
        @type  request: FrameSearch
        @param request: A FrameSearch object"""
        return self.proxy.killFrames(FrameSearch(**request))

    def eatFrames(self, **request):
        """Eats all frames that match the FrameSearch
        @type  request: FrameSearch
        @param request: A FrameSearch object"""
        return self.proxy.eatFrames(FrameSearch(**request))

    def retryFrames(self, **request):
        """Retries all frames that match the FrameSearch
        @type  request: FrameSearch
        @param request: A FrameSearch object"""
        return self.proxy.retryFrames(FrameSearch(**request))

    def markdoneFrames(self, **request):
        """Drops any dependency that requires any frame that matches the
        FrameSearch
        @type  request: FrameSearch
        @param request: A FrameSearch object"""
        return self.proxy.markdoneFrames(FrameSearch(**request))

    def markAsWaiting(self, **request):
        """Changes the matching frames from the depend state to the waiting state
        @type  request: FrameSearch
        @param request: A FrameSearch object"""
        return self.proxy.markAsWaiting(FrameSearch(**request))

    def setMinCores(self, minCores):
        """Sets the minimum procs value
        @type  minCores: int
        @param minCores: New minimum cores value"""
        self.proxy.setMinCores(minCores)

    def setMaxCores(self, maxCores):
        """Sets the maximum procs value
        @type  maxCores: int
        @param maxCores: New maximum cores value"""
        self.proxy.setMaxCores(maxCores)

    def setPriority(self, priority):
        """Sets the priority number
        @type  priority: int
        @param priority: New priority number"""
        self.proxy.setPriority(priority)

    def setMaxRetries(self, maxRetries):
        """Sets the number of retries before a frame goes dead
        @type  maxRetries: int
        @param maxRetries: New max retries"""
        self.proxy.setMaxRetries(maxRetries)

    def getLayers(self):
        """Returns the list of layers
        @rtype:  list<Layer>
        @return: List of layers"""
        return self.proxy.getLayers()

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the job.
        frames = job.getFrames(show=["edu","beo"],user="jwelborn")
        frames = job.getFrames(show="edu",shot="bs.012")
        Allowed: offset, limit, states+, layers+. frameset, changedate
        @rtype:  list<Frame>
        @return: List of frames"""
        return self.proxy.getFrames(FrameSearch(**options))

    def getUpdatedFrames(self, lastCheck, layers = []):
        """Returns a list of updated state information for frames that have
        changed since the last update time as well as the current state of the
        job. If layer proxies are provided in the layers list, only frames from
        those layers will be returned.
        UpdatedFrameCheckResult:
        CueIce::JobState state =
        int updated =
        UpdatedFrameSeq updatedFrames =
        @type  lastCheck: int
        @param lastCheck: Epoch when last updated
        @type  layers: list<Layer>
        @param layers: List of layers to check, empty list checks all
        @rtype:  UpdatedFrameCheckResult
        @return: Job state and a list of updatedFrames"""
        return self.proxy.getUpdatedFrames(lastCheck, layers)

    def setAutoEating(self, value):
        """If set to true, any frames that would become dead, will become eaten
        @type  value: bool
        @param value: State of autoeat"""
        self.proxy.setAutoEat(value)

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this job
        @rtype:  list<Depend>
        @return: List of dependencies that depend directly on this job"""
        return self.proxy.getWhatDependsOnThis()

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this job depends on
        @rtype:  list<Depend>
        @return: dependencies that this job depends on"""
        return self.proxy.getWhatThisDependsOn()

    def getDepends(self):
        """Returns a list of all depends this job is involved with
        @rtype:  list<Depend>
        @return: all depends involved with this job"""
        return self.proxy.getDepends()

    def dropDepends(self, target):
        """Drops the desired dependency target:
        Cue3.DependTarget.AnyTarget
        Cue3.DependTarget.External
        Cue3.DependTarget.Internal
        @type  target: DependTarget
        @param target: The desired dependency target to drop"""
        return self.proxy.dropDepends(target)

    def createDependencyOnJob(self, job):
        """Create and return a job on job dependency
        @type  job: Job
        @param job: the job you want this job to depend on
        @rtype:  Depend
        @return: The new dependency"""
        return self.proxy.createDependencyOnJob(job.proxy)

    def createDependencyOnLayer(self, layer):
        """Create and return a job on layer dependency
        @type  layer: Layer
        @param layer: the layer you want this job to depend on
        @rtype:  Depend
        @return: the new dependency"""
        return self.proxy.createDependencyOnLayer(layer.proxy)

    def createDependencyOnFrame(self, frame):
        """Create and return a job on frame dependency
        @type  frame: Frame
        @param frame: the frame you want this job to depend on
        @rtype:  Depend
        @return: the new dependency"""
        return self.proxy.createDependencyOnFrame(frame.proxy)

    def unbookProcs(self, subs, number, kill=False):
        """Unbook procs off job from specified allocations
        @type  subs: list<Subscription>
        @param subs: The subscriptions to unbook from
        @type  number: int
        @param number: the number of virtual procs to unbook
        @type  kill: bool
        @param kill: wheather or not to kill the frames as well"""
        self.proxy.unbookProcs([a.proxy for a in subs],number,kill)

    def addComment(self, subject, message):
        """Appends a comment to the job's comment list
        @type  subject: str
        @param subject: Subject data
        @type  message: str
        @param message: Message data"""
        c = CueClientIce.CommentData()
        c.user = os.getenv("USER","unknown")
        c.subject = subject
        c.message = message or " "
        c.timestamp = 0
        self.proxy.addComment(c)

    def getComments(self):
        """returns the jobs comments"""
        return self.proxy.getComments()

    def setGroup(self, group):
        """Sets the job to a new group
        @type  group: Group
        @param group: the group you want the job to be in."""
        self.proxy.setGroup(group.proxy)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this job.
        @type  range: string
        @param range: The frame range to reorder
        @type  order: Cue3.Order
        @param order: First, Last or Reverse"""
        self.proxy.reorderFrames(range, order)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this job.
        @type  range: string
        @param range: The frame range to stagger
        @type  stagger: int
        @param stagger: The amount to stagger by"""
        self.proxy.staggerFrames(range, stagger)

    def facility(self):
        """Returns the facility that the job must run in"""
        return self.data.facility

    def id(self):
        """Returns the uuid of the job
        @rtype:  str
        @return: Job uuid"""
        return self.proxy.ice_getIdentity().name

    def name(self):
        """Returns the name of the job
        @rtype:  str
        @return: Job name"""
        return self.data.name

    def show(self):
        """Returns the show name
        @rtype:  str
        @return: Show name"""
        return self.data.show

    def shot(self):
        """Returns the shot name
        @rtype:  str
        @return: Shot name"""
        return self.data.shot

    def logDir(self):
        """Returns the path to the log files
        @rtype:  str
        @return: Path of log files"""
        return self.data.logDir

    def uid(self):
        """Returns the uid of the person who owns the job
        @rtype:  int
        @return: Uid of job owner"""
        return self.data.uid

    def username(self):
        """Returns the username of the person who owns the job
        @rtype: str
        @return: Username of job owner"""
        return self.data.user

    def state(self):
        """Returns the job state
        @rtype:  JobState
        @return: Job state"""
        return self.data.state

    def priority(self):
        """Returns the job priority
        @rtype:  int
        @return: Job priority"""
        return self.data.priority

    def minCores(self):
        """Returns the job's minProcs
        @rtype:  int
        @return: Job's minCores"""
        return self.data.minCores

    def maxCores(self):
        """Returns the job's maxProcs
        @rtype:  int
        @return: Job's maxProcs"""
        return self.data.maxCores

    def startTime(self, format = None):
        """Returns the job start time in the desired format
        None                    => 1203634027
        "%m/%d %H:%M"           => 02/21 14:47
        "%a %b %d %H:%M:%S %Y"  => Thu Feb 21 14:47:07 2008
        See the format table on:
         - http://www.python.org/doc/current/lib/module-time.html
        @type  format: str
        @param format: Desired time format
        @rtype:  int
        @return: Job start time in epoch"""
        if not format:
            return self.data.startTime
        return time.strftime(format, time.localtime(self.data.startTime))

    def stopTime(self, format = None):
        """Returns the job stop time in the desired format
        None                    => 1203634027
        "%m/%d %H:%M"           => 02/21 14:47
        "%a %b %d %H:%M:%S %Y"  => Thu Feb 21 14:47:07 2008
        See the format table on:
         - http://www.python.org/doc/current/lib/module-time.html
        @type  format: str
        @param format: Desired time format
        @rtype:  int
        @return: Job stop time in epoch"""
        if not format:
            return self.data.stopTime
        return time.strftime(format, time.localtime(self.data.stopTime))

    def runTime(self):
        """Returns the number of seconds that the job has been (or was) running
        @rtype:  int
        @return: Job runtime in seconds"""
        if self.data.stopTime == 0:
            return int(time.time() - self.data.startTime)
        else:
            return self.data.stopTime - self.data.startTime

    def coreSecondsRemaining(self):
        """Returns the estimated number of core seconds reeded to finish all
        waiting frames.  Does note take into account running frames.
        @rtype:  long
        @return: core seconds remaining"""
        return self.stats.coreTimeRemain

    def age(self):
        """Returns the number of seconds since the job was launched
        @rtype:  int
        @return: Seconds since the job was launched"""
        return int(time.time() - self.data.startTime)

    def isPaused(self):
        """Returns true if the job is paused
        @rtype:  bool
        @return: Paused or not paused"""
        return self.data.isPaused;

    def isAutoEating(self):
        """Returns true if the job is eating all frames that become dead
        @rtype:  bool
        @return: If the job eating all frames that become dead"""
        return self.data.autoEat

    def isCommented(self):
        """Returns true if the job has a comment
        @rtype:  bool
        @return: If the job has a comment"""
        return self.data.hasComment

    def setAutoEat(self, value):
        """Changes the state of autoeating. When frames become eaten instead of dead.
        @type  value: bool
        @param value: The new state for autoEat"""
        self.proxy.setAutoEat(value)
        self.data.autoEat = value

    def coresReserved(self):
        """Returns the number of reserved cores
        @rtype: float
        @return: total number of reserved cores"""
        return self.stats.reservedCores

    def totalFrames(self):
        """Returns the total number of frames under this object
        @rtype:  int
        @return: Total number of frames"""
        return self.stats.totalFrames

    def totalLayers(self):
        """Returns the total number of frames under this object
        @rtype:  int
        @return: Total number of frames"""
        return self.stats.totalLayers

    def dependFrames(self):
        """Returns the total number of dependent frames under this object
        @rtype:  int
        @return: Total number of dependent frames"""
        return self.stats.dependFrames

    def succeededFrames(self):
        """Returns the total number of succeeded frames under this object
        @rtype:  int
        @return: Total number of succeeded frames"""
        return self.stats.succeededFrames

    def runningFrames(self):
        """Returns the total number of running frames under this object
        @rtype:  int
        @return: Total number of running frames"""
        return self.stats.runningFrames

    def deadFrames(self):
        """Returns the total number of deads frames under this object
        @rtype:  int
        @return: Total number of dead frames"""
        return self.stats.deadFrames

    def waitingFrames(self):
        """Returns the total number of waiting frames under this object
        @rtype:  int
        @return: Total number of waiting frames"""
        return self.stats.waitingFrames

    def eatenFrames(self):
        """Returns the total number of eaten frames under this object
        @rtype:  int
        @return: Total number of eaten frames"""
        return self.stats.eatenFrames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.
        @rtype:  int
        @return: Total number of pending (dependent and waiting) frames"""
        return self.stats.pendingFrames

    def frameStateTotals(self):
        """Returns a dictionary of frame states and the number of frames in each
        state. The states are available from Cue3.FrameState.*
        @rtype: dict
        @return: total number of frames in each state"""
        if not hasattr(self, "__frameStateTotals"):
            self.__frameStateTotals = dict((getattr(CueIce.FrameState,a),
                                            getattr(self.stats,"%sFrames" % a.lower(),0))
                                            for a in dir(CueIce.FrameState) if a[0] != "_")
        return self.__frameStateTotals

    def percentCompleted(self):
        """Returns the percent that the object's frames are completed
        @rtype:  float
        @return: Percentage of frame completion"""
        try:
            return self.stats.succeededFrames / float(self.stats.totalFrames) * 100.0
        except:
            return 0

    def group(self):
        """Returns the name of the group that the job is in
        @rtype:  str
        @return: Jobs group name"""
        return self.data.group

    def avgFrameTime(self):
        """Returns the average completed frame time in seconds
        @rtype:  int
        @return: Average completed frame time in seconds"""
        return self.stats.avgFrameSec

    def averageCoreTime(self):
        """Returns the average frame time
        @rtype:  int
        @return: Average frame time for entire job"""
        self.stats.avgCoreSec;

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this job used
        in kB. Value is within 5% of the actual highest frame.
        @rtype:  long
        @return: Most memory used by any frame in kB"""
        return self.stats.maxRss

class NestedJob(CueClientIce.NestedJob, Job):
    """This class contains information and actions related to a nested job."""
    def __init__(self):
        CueClientIce.NestedJob.__init__(self)
        ## job children are most likely empty but its possible to
        ## populate this with NesterLayer objects.
        self.__children = []

    def children(self):
        return self.__children

