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



"""
Project: opencue Library

Module: job.py - opencue Library implementation of a job

"""

import enum
import os
import time

from opencue import Cuebot
from opencue.compiled_proto import comment_pb2
from opencue.compiled_proto import job_pb2
import opencue.search
import opencue.wrappers.comment
import opencue.wrappers.depend
import opencue.wrappers.frame
import opencue.wrappers.layer


class Job(object):
    """This class contains the ice implementation related to a job."""

    class JobState(enum.IntEnum):
        PENDING = job_pb2.PENDING
        FINISHED = job_pb2.FINISHED
        STARTUP = job_pb2.STARTUP
        SHUTDOWN = job_pb2.SHUTDOWN
        POSTED = job_pb2.POSTED

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
        """Kills all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        self.stub.KillFrames(job_pb2.JobKillFramesRequest(job=self.data, req=criteria),
                             timeout=Cuebot.Timeout)

    def eatFrames(self, **request):
        """Eats all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.EatFrames(job_pb2.JobEatFramesRequest(job=self.data, req=criteria),
                                   timeout=Cuebot.Timeout)

    def retryFrames(self, **request):
        """Retries all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.RetryFrames(job_pb2.JobRetryFramesRequest(job=self.data, req=criteria),
                                     timeout=Cuebot.Timeout)

    def markdoneFrames(self, **request):
        """Drops any dependency that requires any frame that matches the
        FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.MarkDoneFrames(
            job_pb2.JobMarkDoneFramesRequest(job=self.data, req=criteria),
            timeout=Cuebot.Timeout)

    def markAsWaiting(self, **request):
        """Changes the matching frames from the depend state to the waiting state.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.MarkAsWaiting(
            job_pb2.JobMarkAsWaitingRequest(job=self.data, req=criteria),
            timeout=Cuebot.Timeout)

    def setMinCores(self, minCores):
        """Sets the minimum procs value.

        :type  minCores: int
        :param minCores: New minimum cores value"""
        self.stub.SetMinCores(job_pb2.JobSetMinCoresRequest(job=self.data, val=minCores),
                              timeout=Cuebot.Timeout)

    def setMaxCores(self, maxCores):
        """Sets the maximum procs value.

        :type  maxCores: int
        :param maxCores: New maximum cores value"""
        self.stub.SetMaxCores(job_pb2.JobSetMaxCoresRequest(job=self.data, val=maxCores),
                              timeout=Cuebot.Timeout)

    def setMinGpu(self, minGpu):
        """Sets the minimum procs value
        :type  minGpu: int
        :param minGpu: New minimum cores value"""
        self.stub.SetMinGpu(job_pb2.JobSetMinGpuRequest(job=self.data, val=minGpu),
                              timeout=Cuebot.Timeout)

    def setMaxGpu(self, maxGpu):
        """Sets the maximum procs value
        :type  maxGpu: int
        :param maxGpu: New maximum cores value"""
        self.stub.SetMaxGpu(job_pb2.JobSetMaxGpuRequest(job=self.data, val=maxGpu),
                              timeout=Cuebot.Timeout)

    def setPriority(self, priority):
        """Sets the priority number.

        :type  priority: int
        :param priority: New priority number"""
        self.stub.SetPriority(job_pb2.JobSetPriorityRequest(job=self.data, val=priority),
                              timeout=Cuebot.Timeout)

    def setMaxRetries(self, maxRetries):
        """Sets the number of retries before a frame goes dead.

        :type  maxRetries: int
        :param maxRetries: New max retries"""
        self.stub.SetMaxRetries(
            job_pb2.JobSetMaxRetriesRequest(job=self.data, max_retries=maxRetries),
            timeout=Cuebot.Timeout)

    def getLayers(self):
        """Returns the list of layers.

        :rtype:  list<Layer>
        :return: List of layers"""
        response = self.stub.GetLayers(job_pb2.JobGetLayersRequest(job=self.data),
                                       timeout=Cuebot.Timeout)
        layerSeq = response.layers
        return [opencue.wrappers.layer.Layer(lyr) for lyr in layerSeq.layers]

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the job.

        For example::

            # Allowed: offset, limit, states+, layers+. frameset, changedate
            frames = job.getFrames(show=["edu","beo"],user="jwelborn")
            frames = job.getFrames(show="edu",shot="bs.012")

        :rtype:  list<Frame>
        :return: List of frames"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**options)
        response = self.stub.GetFrames(job_pb2.JobGetFramesRequest(job=self.data, req=criteria),
                                       timeout=Cuebot.Timeout)
        frameSeq = response.frames
        return [opencue.wrappers.frame.Frame(frm) for frm in frameSeq.frames]

    def getUpdatedFrames(self, lastCheck, layers=None):
        """Returns a list of updated state information for frames that have
        changed since the last update time as well as the current state of the
        job. If layer proxies are provided in the layers list, only frames from
        those layers will be returned.

        UpdatedFrameCheckResult::

            CueIce::JobState state =
            int updated =
            UpdatedFrameSeq updatedFrames =

        :type  lastCheck: int
        :param lastCheck: Epoch when last updated
        :type  layers: list<job_pb2.Layer>
        :param layers: List of layers to check, empty list checks all
        :rtype:  job_pb2.UpdatedFrameCheckResult
        :return: Job state and a list of updatedFrames"""
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
        """If set to true, any frames that would become dead, will become eaten.

        :type  value: bool
        :param value: State of autoeat"""
        self.stub.SetAutoEat(job_pb2.JobSetAutoEatRequest(job=self.data, value=value),
                             timeout=Cuebot.Timeout)

    def addRenderPartition(self, hostname, threads, max_cores, num_mem, max_gpu):
        """Add a render partition to the job.
        @type  hostname: str
        @param hostname: hostname of the partition
        @type  threads: int
        @param threads: number of threads of the partition
        @type  max_cores: int
        @param max_cores: max cores enabled for the partition
        @type  num_mem: int
        @param num_mem: amount of memory reserved for the partition
        @type  max_gpu: int
        @param max_gpu: max gpu cores enabled for the partition
        """
        self.stub.AddRenderPartition(
            job_pb2.JobAddRenderPartRequest(job=self.data,
                                            host=hostname,
                                            threads=threads,
                                            max_cores=max_cores,
                                            max_memory=num_mem,
                                            max_gpu=max_gpu,
                                            username=os.getenv("USER", "unknown")))

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this job.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: List of dependencies that depend directly on this job"""
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.JobGetWhatDependsOnThisRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this job depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: dependencies that this job depends on"""
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.JobGetWhatThisDependsOnRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def getDepends(self):
        """Returns a list of all depends this job is involved with.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: all depends involved with this job"""
        response = self.stub.GetDepends(
            job_pb2.JobGetDependsRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def dropDepends(self, target):
        """Drops the desired dependency target:
        depend_pb2.DependTarget.AnyTarget
        depend_pb2.DependTarget.External
        depend_pb2.DependTarget.Internal
        :type  target: depend_pb2.DependTarget
        :param target: The desired dependency target to drop"""
        return self.stub.DropDepends(job_pb2.JobDropDependsRequest(job=self.data, target=target),
                                     timeout=Cuebot.Timeout)

    def createDependencyOnJob(self, job):
        """Create and return a job on job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency"""
        response = self.stub.CreateDependencyOnJob(
            job_pb2.JobCreateDependencyOnJobRequest(job=self.data, on_job=job.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Create and return a job on layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this job to depend on
        :rtype:  opencue.wrappers.Depend
        :return: the new dependency"""
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.JobCreateDependencyOnLayerRequest(job=self.data, layer=layer.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Create and return a job on frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
        response = self.stub.CreateDependencyOnFrame(
            job_pb2.JobCreateDependencyOnFrameRequest(job=self.data, frame=frame.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    # TODO(gregdenton) Is this needed? (Issue #71)
    # def unbookProcs(self, subs, number, kill=False):
    #     """Unbook procs off job from specified allocations
    #     :type  subs: list<Subscription>
    #     :param subs: The subscriptions to unbook from
    #     :type  number: int
    #     :param number: the number of virtual procs to unbook
    #     :type  kill: bool
    #     :param kill: wheather or not to kill the frames as well"""
    #     self.proxy.unbookProcs([a.proxy for a in subs],number,kill)

    def addComment(self, subject, message):
        """Appends a comment to the job's comment list.

        :type  subject: str
        :param subject: Subject data
        :type  message: str
        :param message: Message data"""
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
        return [opencue.wrappers.comment.Comment(cmt) for cmt in commentSeq.comments]

    def setGroup(self, group):
        """Sets the job to a new group.

        :type  group: opencue.wrappers.group.Group
        :param group: the group you want the job to be in."""
        self.stub.SetGroup(job_pb2.JobSetGroupRequest(job=self.data, group_id=group.id()),
                           timeout=Cuebot.Timeout)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this job.

        :type  range: string
        :param range: The frame range to reorder
        :type  order: job_pb2.Order
        :param order: First, Last or Reverse"""
        self.stub.ReorderFrames(
            job_pb2.JobReorderFramesRequest(job=self.data, range=range, order=order),
            timeout=Cuebot.Timeout)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this job.

        :type  range: string
        :param range: The frame range to stagger
        :type  stagger: int
        :param stagger: The amount to stagger by"""
        self.stub.StaggerFrames(
            job_pb2.JobStaggerFramesRequest(job=self.data, range=range, stagger=stagger),
            timeout=Cuebot.Timeout)

    def facility(self):
        """Returns the facility that the job must run in"""
        return self.data.facility

    def id(self):
        """Returns the uuid of the job.

        :rtype:  str
        :return: Job uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the job.

        :rtype:  str
        :return: Job name"""
        return self.data.name

    def show(self):
        """Returns the show name.

        :rtype:  str
        :return: Show name"""
        return self.data.show

    def shot(self):
        """Returns the shot name.

        :rtype:  str
        :return: Shot name"""
        return self.data.shot

    def logDir(self):
        """Returns the path to the log files.

        :rtype:  str
        :return: Path of log files"""
        return self.data.log_dir

    def uid(self):
        """Returns the uid of the person who owns the job.

        :rtype:  Optional[int]
        :return: Uid of job owner"""
        return self.data.uid if self.data.HasField("uid") else None

    def user(self):
        """Returns the username of the person who owns the job.

        :rtype: str
        :return: Username of job owner"""
        return self.data.user

    def username(self):
        """Returns the username of the person who owns the job.

        :rtype: str
        :return: Username of job owner"""
        return self.user()

    def state(self):
        """Returns the job state.

        :rtype:  JobState
        :return: Job state"""
        return self.data.state

    def priority(self):
        """Returns the job priority.

        :rtype:  int
        :return: Job priority"""
        return self.data.priority

    def minCores(self):
        """Returns the job's minProcs.

        :rtype:  int
        :return: Job's minCores"""
        return self.data.min_cores

    def maxCores(self):
        """Returns the job's maxProcs.

        :rtype:  int
        :return: Job's maxProcs"""
        return self.data.max_cores

    def minGpu(self):
        """Returns the job's minProcs
        :rtype:  int
        :return: Job's minGpu"""
        return self.data.min_gpu

    def maxGpu(self):
        """Returns the job's maxProcs
        :rtype:  int
        :return: Job's maxProcs"""
        return self.data.max_gpu

    def os(self):
        """Returns the job's operating system.

        :rtype: str
        :return: operating system name of the Job"""
        return self.data.os

    def startTime(self, format=None):
        """Returns the job start time in the desired format::

            None                    => 1203634027
            "%m/%d %H:%M"           => 02/21 14:47
            "%a %b %d %H:%M:%S %Y"  => Thu Feb 21 14:47:07 2008

        See the format table at:
        https://docs.python.org/3/library/time.html

        :type  format: str
        :param format: Desired time format
        :rtype:  int
        :return: Job start time in epoch"""
        if not format:
            return self.data.start_time
        return time.strftime(format, time.localtime(self.data.start_time))

    def stopTime(self, format=None):
        """Returns the job stop time in the desired format::

            None                    => 1203634027
            "%m/%d %H:%M"           => 02/21 14:47
            "%a %b %d %H:%M:%S %Y"  => Thu Feb 21 14:47:07 2008

        See the format table at:
        https://docs.python.org/3/library/time.html

        :type  format: str
        :param format: Desired time format
        :rtype:  int
        :return: Job stop time in epoch"""
        if not format:
            return self.data.stop_time
        return time.strftime(format, time.localtime(self.data.stop_time))

    def runTime(self):
        """Returns the number of seconds that the job has been (or was) running.

        :rtype:  int
        :return: Job runtime in seconds"""
        if self.data.stop_time == 0:
            return int(time.time() - self.data.start_time)
        else:
            return self.data.stop_time - self.data.start_time

    def coreSecondsRemaining(self):
        """Returns the estimated number of core seconds reeded to finish all
        waiting frames.  Does note take into account running frames.

        :rtype:  long
        :return: core seconds remaining"""
        return self.data.job_stats.remaining_core_sec

    def age(self):
        """Returns the number of seconds since the job was launched.

        :rtype:  int
        :return: Seconds since the job was launched"""
        return int(time.time() - self.data.start_time)

    def isPaused(self):
        """Returns true if the job is paused
        :rtype:  bool
        :return: Paused or not paused"""
        return self.data.is_paused

    def isAutoEating(self):
        """Returns true if the job is eating all frames that become dead.

        :rtype:  bool
        :return: If the job eating all frames that become dead"""
        return self.data.auto_eat

    def isCommented(self):
        """Returns true if the job has a comment.

        :rtype:  bool
        :return: If the job has a comment"""
        return self.data.has_comment

    def setAutoEat(self, value):
        """Changes the state of autoeating. When frames become eaten instead of dead.

        :type  value: bool
        :param value: The new state for autoEat"""
        self.setAutoEating(value)
        self.data.auto_eat = value

    def coresReserved(self):
        """Returns the number of reserved cores.

        :rtype: float
        :return: total number of reserved cores"""
        return self.data.job_stats.reserved_cores

    def totalFrames(self):
        """Returns the total number of frames under this object.

        :rtype:  int
        :return: Total number of frames"""
        return self.data.job_stats.total_frames

    def totalLayers(self):
        """Returns the total number of frames under this object.

        :rtype:  int
        :return: Total number of frames"""
        return self.data.job_stats.total_layers

    def dependFrames(self):
        """Returns the total number of dependent frames under this object.

        :rtype:  int
        :return: Total number of dependent frames"""
        return self.data.job_stats.depend_frames

    def succeededFrames(self):
        """Returns the total number of succeeded frames under this object.

        :rtype:  int
        :return: Total number of succeeded frames"""
        return self.data.job_stats.succeeded_frames

    def runningFrames(self):
        """Returns the total number of running frames under this object.

        :rtype:  int
        :return: Total number of running frames"""
        return self.data.job_stats.running_frames

    def deadFrames(self):
        """Returns the total number of deads frames under this object.

        :rtype:  int
        :return: Total number of dead frames"""
        return self.data.job_stats.dead_frames

    def waitingFrames(self):
        """Returns the total number of waiting frames under this object.

        :rtype:  int
        :return: Total number of waiting frames"""
        return self.data.job_stats.waiting_frames

    def eatenFrames(self):
        """Returns the total number of eaten frames under this object.

        :rtype:  int
        :return: Total number of eaten frames"""
        return self.data.job_stats.eaten_frames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.

        :rtype:  int
        :return: Total number of pending (dependent and waiting) frames"""
        return self.data.job_stats.pending_frames

    def frameStateTotals(self):
        """Returns a dictionary of frame states and the number of frames in each
        state. The states are available from opencue.FrameState.*

        :rtype: dict
        :return: total number of frames in each state"""
        if not hasattr(self, "__frameStateTotals"):
            self.__frameStateTotals = {}
            for state in job_pb2.FrameState.keys():
                frameCount = getattr(self.data.job_stats, '{}_frames'.format(state.lower()), 0)
                self.__frameStateTotals[getattr(job_pb2, state)] = frameCount
        return self.__frameStateTotals

    def percentCompleted(self):
        """Returns the percent that the object's frames are completed.

        :rtype:  float
        :return: Percentage of frame completion"""
        try:
            return self.data.job_stats.succeeded_frames /\
                   float(self.data.job_stats.total_frames) * 100.0
        except:
            return 0

    def group(self):
        """Returns the name of the group that the job is in.

        :rtype:  str
        :return: Jobs group name"""
        return self.data.group

    def avgFrameTime(self):
        """Returns the average completed frame time in seconds.

        :rtype:  int
        :return: Average completed frame time in seconds"""
        return self.data.job_stats.avg_frame_sec

    def averageCoreTime(self):
        """Returns the average frame time.

        :rtype:  int
        :return: Average frame time for entire job"""
        return self.data.job_stats.avg_core_sec

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this job used
        in kB. Value is within 5% of the actual highest frame.

        :rtype:  long
        :return: Most memory used by any frame in kB"""
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

    def kill(self):
        """Kills the job"""
        self.asJob().kill()

    def pause(self):
        """Pauses the job"""
        self.asJob().pause()

    def resume(self):
        """Resumes the job"""
        self.asJob().resume()

    def killFrames(self, **request):
        """Kills all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        self.asJob().killFrames(**request)

    def eatFrames(self, **request):
        """Eats all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        self.asJob().eatFrames(**request)

    def retryFrames(self, **request):
        """Retries all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        self.asJob().retryFrames(**request)

    def markdoneFrames(self, **request):
        """Drops any dependency that requires any frame that matches the
        FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        self.asJob().markdoneFrames(**request)

    def markAsWaiting(self, **request):
        """Changes the matching frames from the depend state to the waiting state.

        :type  request: Dict
        :param request: FrameSearch parameters"""
        self.asJob().markAsWaiting(**request)

    def setMinCores(self, minCores):
        """Sets the minimum procs value.

        :type  minCores: int
        :param minCores: New minimum cores value"""
        self.asJob().setMinCores(minCores)

    def setMaxCores(self, maxCores):
        """Sets the maximum procs value.

        :type  maxCores: int
        :param maxCores: New maximum cores value"""
        self.asJob().setMaxCores(maxCores)

    def setMinGpu(self, minGpu):
        """Sets the minimum procs value
        :type  minGpu: int
        :param minGpu: New minimum cores value"""
        self.asJob().setMinGpu(minGpu)

    def setMaxGpu(self, maxGpu):
        """Sets the maximum procs value
        :type  maxGpu: int
        :param maxGpu: New maximum cores value"""
        self.asJob().setMaxGpu(maxGpu)

    def setPriority(self, priority):
        """Sets the priority number.

        :type  priority: int
        :param priority: New priority number"""
        self.asJob().setPriority(priority)

    def setMaxRetries(self, maxRetries):
        """Sets the number of retries before a frame goes dead.

        :type  maxRetries: int
        :param maxRetries: New max retries"""
        self.asJob().setMaxRetries(maxRetries)

    def getLayers(self):
        """Returns the list of layers.

        :rtype:  list<opencue.wrappers.layer.Layer>
        :return: List of layers"""
        return self.asJob().getLayers()

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the job.

        frames = job.getFrames(show=["edu","beo"],user="jwelborn")
        frames = job.getFrames(show="edu",shot="bs.012")
        Allowed: offset, limit, states+, layers+. frameset, changedate
        :rtype:  list<opencue.wrappers.frame.Frame>
        :return: List of frames"""
        return self.asJob().getFrames(**options)

    def getUpdatedFrames(self, lastCheck, layers=None):
        """Returns a list of updated state information for frames that have
        changed since the last update time as well as the current state of the
        job. If layer proxies are provided in the layers list, only frames from
        those layers will be returned.

        UpdatedFrameCheckResult::

            CueIce::JobState state =
            int updated =
            UpdatedFrameSeq updatedFrames =

        :type  lastCheck: int
        :param lastCheck: Epoch when last updated
        :type  layers: list<Layer>
        :param layers: List of layers to check, empty list checks all
        :rtype:  UpdatedFrameCheckResult
        :return: Job state and a list of updatedFrames"""
        return self.asJob().getUpdatedFrames(lastCheck, layers)

    def setAutoEating(self, value):
        """If set to true, any frames that would become dead, will become eaten.

        :type  value: bool
        :param value: State of autoeat"""
        self.asJob().setAutoEating(value)


    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this job.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: List of dependencies that depend directly on this job"""
        return self.asJob().getWhatDependsOnThis()

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this job depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: dependencies that this job depends on"""
        return self.asJob().getWhatThisDependsOn()

    def getDepends(self):
        """Returns a list of all depends this job is involved with.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: all depends involved with this job"""
        return self.asJob().getDepends()

    def dropDepends(self, target):
        """Drops the desired dependency target::

            depend_pb2.DependTarget.AnyTarget
            depend_pb2.DependTarget.External
            depend_pb2.DependTarget.Internal

        :type  target: depend_pb2.DependTarget
        :param target: The desired dependency target to drop"""
        return self.asJob().dropDepends(target)

    def createDependencyOnJob(self, job):
        """Create and return a job on job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency"""
        return self.asJob().createDependencyOnJOb(job)

    def createDependencyOnLayer(self, layer):
        """Create and return a job on layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
        return self.asJob().createDependencyOnLayer(layer)

    def createDependencyOnFrame(self, frame):
        """Create and return a job on frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
        return self.asJob().createDependencyOnFrame(frame)

    def addComment(self, subject, message):
        """Appends a comment to the job's comment list.

        :type  subject: str
        :param subject: Subject data
        :type  message: str
        :param message: Message data"""
        self.asJob().addComment(subject, message)

    def getComments(self):
        """Returns the jobs comments."""
        return self.asJob().getComments()

    def setGroup(self, group):
        """Sets the job to a new group.

        :type  group: opencue.wrappers.group.Group
        :param group: the group you want the job to be in."""
        self.asJob().setGroup(group)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this job.

        :type  range: string
        :param range: The frame range to reorder
        :type  order: job_pb2.Order
        :param order: First, Last or Reverse"""
        self.asJob().reorderFrames(range, order)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this job.

        :type  range: string
        :param range: The frame range to stagger
        :type  stagger: int
        :param stagger: The amount to stagger by"""
        self.asJob().staggerFrames(range, stagger)

    def asJob(self):
        """Returns a Job object from this NestedJob"""
        return Job(job_pb2.Job(
            id=self.data.id,
            state=self.data.state,
            name=self.data.name,
            shot=self.data.shot,
            show=self.data.show,
            user=self.data.user,
            group=self.data.group,
            facility=self.data.facility,
            os=self.data.os,
            uid=self.data.uid if self.data.HasField("uid") else None,
            priority=self.data.priority,
            min_cores=self.data.min_cores,
            max_cores=self.data.max_cores,
            log_dir=self.data.log_dir,
            is_paused=self.data.is_paused,
            has_comment=self.data.has_comment,
            auto_eat=self.data.auto_eat,
            start_time=self.data.start_time,
            stop_time=self.data.stop_time,
            job_stats=self.data.stats
        ))
