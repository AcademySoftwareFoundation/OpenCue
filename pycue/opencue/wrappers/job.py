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
Project: opencue Library

Module: job.py - opencue Library implementation of a job

"""

import os
import time

import comment
import depend
import frame
import layer
from opencue import Cuebot
from opencue.compiled_proto import comment_pb2
from opencue.compiled_proto import job_pb2
from ..search import FrameSearch


class Job(object):
    """This class contains the ice implementation related to a job."""
    def __init__(self, job=None):
        """_Job class initialization"""
        self.data = job
        self.stub = Cuebot.getStub('job')

    def kill(self):
        """Kills the job"""
        self.stub.Kill(job_pb2.JobKillRequest(job=self.data), timeout=Cuebot.Timeout)

    def pause(self):
        """Pauses the job"""
        self.stub.Pause(job_pb2.JobPauseRequest(job=self.data), timeout=Cuebot.Timeout)

    def resume(self):
        """Resumes the job"""
        self.stub.Resume(job_pb2.JobResumeRequest(job=self.data), timeout=Cuebot.Timeout)

    def killFrames(self, **request):
        """Kills all frames that match the FrameSearch
        @type  request: Dict
        @param request: FrameSearch parameters"""
        criteria = FrameSearch.criteriaFromOptions(**request)
        self.stub.KillFrames(job_pb2.JobKillFramesRequest(job=self.data, req=criteria),
                             timeout=Cuebot.Timeout)

    def eatFrames(self, **request):
        """Eats all frames that match the FrameSearch
        @type  request: Dict
        @param request: FrameSearch parameters"""
        criteria = FrameSearch.criteriaFromOptions(**request)
        return self.stub.EatFrames(job_pb2.JobEatFramesRequest(job=self.data, req=criteria),
                                   timeout=Cuebot.Timeout)

    def retryFrames(self, **request):
        """Retries all frames that match the FrameSearch
        @type  request: Dict
        @param request: FrameSearch parameters"""
        criteria = FrameSearch.criteriaFromOptions(**request)
        return self.stub.RetryFrames(job_pb2.JobRetryFramesRequest(job=self.data, req=criteria),
                                     timeout=Cuebot.Timeout)

    def markdoneFrames(self, **request):
        """Drops any dependency that requires any frame that matches the
        FrameSearch
        @type  request: Dict
        @param request: FrameSearch parameters"""
        criteria = FrameSearch.criteriaFromOptions(**request)
        return self.stub.MarkDoneFrames(
            job_pb2.JobMarkDoneFramesRequest(job=self.data, req=criteria),
            timeout=Cuebot.Timeout)

    def markAsWaiting(self, **request):
        """Changes the matching frames from the depend state to the waiting state
        @type  request: Dict
        @param request: FrameSearch parameters"""
        criteria = FrameSearch.criteriaFromOptions(**request)
        return self.stub.MarkAsWaiting(
            job_pb2.JobMarkAsWaitingRequest(job=self.data, req=criteria),
            timeout=Cuebot.Timeout)

    def setMinCores(self, minCores):
        """Sets the minimum procs value
        @type  minCores: int
        @param minCores: New minimum cores value"""
        self.stub.SetMinCores(job_pb2.JobSetMinCoresRequest(job=self.data, val=minCores),
                              timeout=Cuebot.Timeout)

    def setMaxCores(self, maxCores):
        """Sets the maximum procs value
        @type  maxCores: int
        @param maxCores: New maximum cores value"""
        self.stub.SetMaxCores(job_pb2.JobSetMaxCoresRequest(job=self.data, val=maxCores),
                              timeout=Cuebot.Timeout)

    def setPriority(self, priority):
        """Sets the priority number
        @type  priority: int
        @param priority: New priority number"""
        self.stub.SetPriority(job_pb2.JobSetPriorityRequest(job=self.data, val=priority),
                              timeout=Cuebot.Timeout)

    def setMaxRetries(self, maxRetries):
        """Sets the number of retries before a frame goes dead
        @type  maxRetries: int
        @param maxRetries: New max retries"""
        self.stub.SetMaxRetries(
            job_pb2.JobSetMaxRetriesRequest(job=self.data, max_retries=maxRetries),
            timeout=Cuebot.Timeout)

    def getLayers(self):
        """Returns the list of layers
        @rtype:  list<Layer>
        @return: List of layers"""
        response = self.stub.GetLayers(job_pb2.JobGetLayersRequest(job=self.data),
                                       timeout=Cuebot.Timeout)
        layerSeq = response.layers
        return [layer.Layer(lyr) for lyr in layerSeq.layers]

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the job.
        frames = job.getFrames(show=["edu","beo"],user="jwelborn")
        frames = job.getFrames(show="edu",shot="bs.012")
        Allowed: offset, limit, states+, layers+. frameset, changedate
        @rtype:  list<Frame>
        @return: List of frames"""
        criteria = FrameSearch.criteriaFromOptions(**options)
        response = self.stub.GetFrames(job_pb2.JobGetFramesRequest(job=self.data, req=criteria),
                                       timeout=Cuebot.Timeout)
        frameSeq = response.frames
        return [frame.Frame(frm) for frm in frameSeq.frames]

    def getUpdatedFrames(self, lastCheck, layers=None):
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
        if layers is not None:
            layerSeq = job_pb2.LayerSeq()
            layerSeq.layers.extend(layers)
        else:
            layerSeq = None
        return self.stub.GetUpdatedFrames(
            job_pb2.JobGetUpdatedFramesRequest(job=self.data, last_check=lastCheck,
                                               layer_filter=layerSeq),
            timeout=Cuebot.Timeout)

    def setAutoEating(self, value):
        """If set to true, any frames that would become dead, will become eaten
        @type  value: bool
        @param value: State of autoeat"""
        self.stub.SetAutoEat(job_pb2.JobSetAutoEatRequest(job=self.data, value=value),
                             timeout=Cuebot.Timeout)

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this job
        @rtype:  list<Depend>
        @return: List of dependencies that depend directly on this job"""
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.JobGetWhatDependsOnThisRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [depend.Depend(dep) for dep in dependSeq.depends]

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this job depends on
        @rtype:  list<Depend>
        @return: dependencies that this job depends on"""
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.JobGetWhatThisDependsOnRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [depend.Depend(dep) for dep in dependSeq.depends]

    def getDepends(self):
        """Returns a list of all depends this job is involved with
        @rtype:  list<Depend>
        @return: all depends involved with this job"""
        response = self.stub.GetDepends(
            job_pb2.JobGetDependsRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [depend.Depend(dep) for dep in dependSeq.depends]

    def dropDepends(self, target):
        """Drops the desired dependency target:
        opencue.DependTarget.AnyTarget
        opencue.DependTarget.External
        opencue.DependTarget.Internal
        @type  target: DependTarget
        @param target: The desired dependency target to drop"""
        return self.stub.DropDepends(job_pb2.JobDropDependsRequest(job=self.data, target=target),
                                     timeout=Cuebot.Timeout)

    def createDependencyOnJob(self, job):
        """Create and return a job on job dependency
        @type  job: Job
        @param job: the job you want this job to depend on
        @rtype:  Depend
        @return: The new dependency"""
        response = self.stub.CreateDependencyOnJob(
            job_pb2.JobCreateDependencyOnJobRequest(job=self.data, on_job=job),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Create and return a job on layer dependency
        @type  layer: Layer
        @param layer: the layer you want this job to depend on
        @rtype:  Depend
        @return: the new dependency"""
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.JobCreateDependencyOnLayerRequest(job=self.data, layer=layer),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Create and return a job on frame dependency
        @type  frame: Frame
        @param frame: the frame you want this job to depend on
        @rtype:  Depend
        @return: the new dependency"""
        response = self.stub.CreateDependencyOnFrame(
            job_pb2.JobCreateDependencyOnFrameRequest(job=self.data, frame=frame),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    # TODO(gregdenton) Is this needed? (Issue #71)
    # def unbookProcs(self, subs, number, kill=False):
    #     """Unbook procs off job from specified allocations
    #     @type  subs: list<Subscription>
    #     @param subs: The subscriptions to unbook from
    #     @type  number: int
    #     @param number: the number of virtual procs to unbook
    #     @type  kill: bool
    #     @param kill: wheather or not to kill the frames as well"""
    #     self.proxy.unbookProcs([a.proxy for a in subs],number,kill)

    def addComment(self, subject, message):
        """Appends a comment to the job's comment list
        @type  subject: str
        @param subject: Subject data
        @type  message: str
        @param message: Message data"""
        comment = comment_pb2.Comment(
            user=os.getenv("USER", "unknown"),
            subject=subject,
            message=message or " ",
            timestamp=0)
        self.stub.AddComment(job_pb2.JobAddCommentRequest(job=self.data, new_comment=comment),
                             timeout=Cuebot.Timeout)

    def getComments(self):
        """returns the jobs comments"""
        response = self.stub.GetComments(job_pb2.JobGetCommentsRequest(job=self.data),
                                         timeout=Cuebot.Timeout)
        commentSeq = response.comments
        return [comment.Comment(cmt) for cmt in commentSeq.comments]

    def setGroup(self, group):
        """Sets the job to a new group
        @type  group: Group
        @param group: the group you want the job to be in."""
        self.stub.SetGroup(job_pb2.JobSetGroupRequest(job=self.data, group_id=group.id),
                           timeout=Cuebot.Timeout)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this job.
        @type  range: string
        @param range: The frame range to reorder
        @type  order: job_pb2.Order
        @param order: First, Last or Reverse"""
        self.stub.ReorderFrames(
            job_pb2.JobReorderFramesRequest(job=self.data, range=range, order=order),
            timeout=Cuebot.Timeout)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this job.
        @type  range: string
        @param range: The frame range to stagger
        @type  stagger: int
        @param stagger: The amount to stagger by"""
        self.stub.StaggerFrames(
            job_pb2.JobStaggerFramesRequest(job=self.data, range=range, stagger=stagger),
            timeout=Cuebot.Timeout)

    def facility(self):
        """Returns the facility that the job must run in"""
        return self.data.facility

    def id(self):
        """Returns the uuid of the job
        @rtype:  str
        @return: Job uuid"""
        return self.data.id

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
        return self.data.log_dir

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
        return self.data.min_cores

    def maxCores(self):
        """Returns the job's maxProcs
        @rtype:  int
        @return: Job's maxProcs"""
        return self.data.max_cores

    def startTime(self, format=None):
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
            return self.data.start_time
        return time.strftime(format, time.localtime(self.data.start_time))

    def stopTime(self, format=None):
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
            return self.data.stop_time
        return time.strftime(format, time.localtime(self.data.stop_time))

    def runTime(self):
        """Returns the number of seconds that the job has been (or was) running
        @rtype:  int
        @return: Job runtime in seconds"""
        if self.data.stop_time == 0:
            return int(time.time() - self.data.start_time)
        else:
            return self.data.stop_time - self.data.start_time

    def coreSecondsRemaining(self):
        """Returns the estimated number of core seconds reeded to finish all
        waiting frames.  Does note take into account running frames.
        @rtype:  long
        @return: core seconds remaining"""
        return self.data.job_stats.remaining_core_sec

    def age(self):
        """Returns the number of seconds since the job was launched
        @rtype:  int
        @return: Seconds since the job was launched"""
        return int(time.time() - self.data.start_time)

    def isPaused(self):
        """Returns true if the job is paused
        @rtype:  bool
        @return: Paused or not paused"""
        return self.data.is_paused

    def isAutoEating(self):
        """Returns true if the job is eating all frames that become dead
        @rtype:  bool
        @return: If the job eating all frames that become dead"""
        return self.data.auto_eat

    def isCommented(self):
        """Returns true if the job has a comment
        @rtype:  bool
        @return: If the job has a comment"""
        return self.data.has_comment

    def setAutoEat(self, value):
        """Changes the state of autoeating. When frames become eaten instead of dead.
        @type  value: bool
        @param value: The new state for autoEat"""
        self.setAutoEating(value)
        self.data.auto_eat = value

    def coresReserved(self):
        """Returns the number of reserved cores
        @rtype: float
        @return: total number of reserved cores"""
        return self.data.job_stats.reserved_cores

    def totalFrames(self):
        """Returns the total number of frames under this object
        @rtype:  int
        @return: Total number of frames"""
        return self.data.job_stats.total_frames

    def totalLayers(self):
        """Returns the total number of frames under this object
        @rtype:  int
        @return: Total number of frames"""
        return self.data.job_stats.total_layers

    def dependFrames(self):
        """Returns the total number of dependent frames under this object
        @rtype:  int
        @return: Total number of dependent frames"""
        return self.data.job_stats.depend_frames

    def succeededFrames(self):
        """Returns the total number of succeeded frames under this object
        @rtype:  int
        @return: Total number of succeeded frames"""
        return self.data.job_stats.succeeded_frames

    def runningFrames(self):
        """Returns the total number of running frames under this object
        @rtype:  int
        @return: Total number of running frames"""
        return self.data.job_stats.running_frames

    def deadFrames(self):
        """Returns the total number of deads frames under this object
        @rtype:  int
        @return: Total number of dead frames"""
        return self.data.job_stats.dead_frames

    def waitingFrames(self):
        """Returns the total number of waiting frames under this object
        @rtype:  int
        @return: Total number of waiting frames"""
        return self.data.job_stats.waiting_frames

    def eatenFrames(self):
        """Returns the total number of eaten frames under this object
        @rtype:  int
        @return: Total number of eaten frames"""
        return self.data.job_stats.eaten_frames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.
        @rtype:  int
        @return: Total number of pending (dependent and waiting) frames"""
        return self.data.job_stats.pending_frames

    def frameStateTotals(self):
        """Returns a dictionary of frame states and the number of frames in each
        state. The states are available from opencue.FrameState.*
        @rtype: dict
        @return: total number of frames in each state"""
        if not hasattr(self, "__frameStateTotals"):
            self.__frameStateTotals = {
                (a, getattr(self.data.job_stats, "%s_frames" % a.lower(), 0))
                for a in job_pb2.FrameState.keys()}
        return self.__frameStateTotals

    def percentCompleted(self):
        """Returns the percent that the object's frames are completed
        @rtype:  float
        @return: Percentage of frame completion"""
        try:
            return self.data.job_stats.succeeded_frames /\
                   float(self.data.job_stats.total_frames) * 100.0
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
        return self.data.job_stats.avg_frame_sec

    def averageCoreTime(self):
        """Returns the average frame time
        @rtype:  int
        @return: Average frame time for entire job"""
        return self.data.job_stats.avg_core_sec

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this job used
        in kB. Value is within 5% of the actual highest frame.
        @rtype:  long
        @return: Most memory used by any frame in kB"""
        return self.data.job_stats.max_rss

class NestedJob(Job):
    """This class contains information and actions related to a nested job."""
    def __init__(self, nestedJob=None):
        super(NestedJob, self).__init__(nestedJob)
        ## job children are most likely empty but its possible to
        ## populate this with NesterLayer objects.
        self.__children = []

    def children(self):
        return self.__children

