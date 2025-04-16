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

"""Module for classes related to jobs."""

import enum
import getpass
import os
import platform
import time

from opencue_proto import comment_pb2
from opencue_proto import job_pb2
from opencue import Cuebot
import opencue.api
import opencue.search
import opencue.wrappers.comment
import opencue.wrappers.depend
import opencue.wrappers.frame
import opencue.wrappers.layer


class Job(object):
    """This class contains the ice implementation related to a job."""

    class JobState(enum.IntEnum):
        """Enum representing the state of a job."""
        PENDING = job_pb2.PENDING
        FINISHED = job_pb2.FINISHED
        STARTUP = job_pb2.STARTUP
        SHUTDOWN = job_pb2.SHUTDOWN
        POSTED = job_pb2.POSTED

    def __init__(self, job=None):
        self.data = job
        self.stub = Cuebot.getStub('job')
        self.__frameStateTotals = {}

    def kill(self, username=None, pid=None, host_kill=None, reason=None):
        """Kills the job."""
        username = username if username else getpass.getuser()
        pid = pid if pid else os.getpid()
        host_kill = host_kill if host_kill else platform.uname()[1]
        self.stub.Kill(job_pb2.JobKillRequest(job=self.data,
                                              username=username,
                                              pid=str(pid),
                                              host_kill=host_kill,
                                              reason=reason),
                       timeout=Cuebot.Timeout)

    def pause(self):
        """Pauses the job."""
        self.stub.Pause(job_pb2.JobPauseRequest(job=self.data), timeout=Cuebot.Timeout)

    def resume(self):
        """Resumes the job."""
        self.stub.Resume(job_pb2.JobResumeRequest(job=self.data), timeout=Cuebot.Timeout)

    def killFrames(self, username=None, pid=None, host_kill=None, reason=None, **request):
        """Kills all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        username = username if username else getpass.getuser()
        pid = pid if pid else os.getpid()
        host_kill = host_kill if host_kill else platform.uname()[1]
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        self.stub.KillFrames(job_pb2.JobKillFramesRequest(job=self.data,
                                                          req=criteria,
                                                          username=username,
                                                          pid=str(pid),
                                                          host_kill=host_kill,
                                                          reason=reason),
                            timeout=Cuebot.Timeout)

    def eatFrames(self, **request):
        """Eats all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.EatFrames(job_pb2.JobEatFramesRequest(job=self.data, req=criteria),
                                   timeout=Cuebot.Timeout)

    def retryFrames(self, **request):
        """Retries all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.RetryFrames(job_pb2.JobRetryFramesRequest(job=self.data, req=criteria),
                                     timeout=Cuebot.Timeout)

    def markdoneFrames(self, **request):
        """Drops any dependency that requires any frame that matches the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.MarkDoneFrames(
            job_pb2.JobMarkDoneFramesRequest(job=self.data, req=criteria),
            timeout=Cuebot.Timeout)

    def markAsWaiting(self, **request):
        """Changes the matching frames from the depend state to the waiting state.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**request)
        return self.stub.MarkAsWaiting(
            job_pb2.JobMarkAsWaitingRequest(job=self.data, req=criteria),
            timeout=Cuebot.Timeout)

    def setMinCores(self, minCores):
        """Sets the minimum number of cores the job needs.

        :type  minCores: int
        :param minCores: new minimum cores value
        """
        self.stub.SetMinCores(job_pb2.JobSetMinCoresRequest(job=self.data, val=minCores),
                              timeout=Cuebot.Timeout)

    def setMaxCores(self, maxCores):
        """Sets the maximum number of cores the job will use.

        :type  maxCores: int
        :param maxCores: new maximum cores value
        """
        self.stub.SetMaxCores(job_pb2.JobSetMaxCoresRequest(job=self.data, val=maxCores),
                              timeout=Cuebot.Timeout)

    def setMinGpus(self, minGpus):
        """Sets the minimum procs value
        :type  minGpus: int
        :param minGpus: New minimum cores value"""
        self.stub.SetMinGpus(job_pb2.JobSetMinGpusRequest(job=self.data, val=minGpus),
                             timeout=Cuebot.Timeout)

    def setMaxGpus(self, maxGpus):
        """Sets the maximum procs value
        :type  maxGpus: int
        :param maxGpus: New maximum cores value"""
        self.stub.SetMaxGpus(job_pb2.JobSetMaxGpusRequest(job=self.data, val=maxGpus),
                             timeout=Cuebot.Timeout)

    def setPriority(self, priority):
        """Sets the job priority.

        :type  priority: int
        :param priority: new job priority number
        """
        self.stub.SetPriority(job_pb2.JobSetPriorityRequest(job=self.data, val=priority),
                              timeout=Cuebot.Timeout)

    def setMaxRetries(self, maxRetries):
        """Sets the number of retries before a frame goes dead.

        :type  maxRetries: int
        :param maxRetries: new max retries
        """
        self.stub.SetMaxRetries(
            job_pb2.JobSetMaxRetriesRequest(job=self.data, max_retries=maxRetries),
            timeout=Cuebot.Timeout)

    def getLayers(self):
        """Returns the list of layers in the job.

        :rtype:  list<opencue.wrappers.layer.Layer>
        :return: list of layers in the job
        """
        response = self.stub.GetLayers(job_pb2.JobGetLayersRequest(job=self.data),
                                       timeout=Cuebot.Timeout)
        layerSeq = response.layers
        return [opencue.wrappers.layer.Layer(lyr) for lyr in layerSeq.layers]

    def getLayer(self, layerName):
        """ Returns the layer with the specified name
        :type:   layername: str
        :rtype:  opencue.wrappers.layer.Layer
        :return: specific layer in the job
        """
        return opencue.api.findLayer(self.name(), layerName)

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the job.

        For example::

            # Allowed: offset, limit, states+, layers+. frameset, changedate
            frames = job.getFrames(show=["edu","beo"],user="jwelborn")
            frames = job.getFrames(show="edu",shot="bs.012")

        :rtype:  list<opencue.wrappers.frame.Frame>
        :return: list of frames
        """
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**options)
        response = self.stub.GetFrames(job_pb2.JobGetFramesRequest(job=self.data, req=criteria),
                                       timeout=Cuebot.Timeout)
        frameSeq = response.frames
        return [opencue.wrappers.frame.Frame(frm) for frm in frameSeq.frames]

    def getUpdatedFrames(self, lastCheck, layers=None):
        """Returns a list of state information for frames that have been recently updated.

        This includes any frames that have changed since the last update time as well as the
        current state of the job. If layer proxies are provided in the layers list, only frames
        from those layers will be returned.

        :type  lastCheck: int
        :param lastCheck: epoch when last updated
        :type  layers: list<job_pb2.Layer>
        :param layers: list of layers to check, empty list checks all
        :rtype:  job_pb2.JobGetUpdatedFramesResponse
        :return: job state and a list of updated frames
        """
        if layers is not None:
            layerSeq = job_pb2.LayerSeq()
            # pylint: disable=no-member
            layerSeq.layers.extend(layers)
            # pylint: enable=no-member
        else:
            layerSeq = None
        return self.stub.GetUpdatedFrames(
            job_pb2.JobGetUpdatedFramesRequest(job=self.data, last_check=lastCheck,
                                               layer_filter=layerSeq),
            timeout=Cuebot.Timeout)

    def setAutoEating(self, value):
        """Sets the job autoeat field.

        If set to true, any frames that would become dead will become eaten.

        :type  value: bool
        :param value: whether job should autoeat
        """
        self.stub.SetAutoEat(job_pb2.JobSetAutoEatRequest(job=self.data, value=value),
                             timeout=Cuebot.Timeout)

    def addRenderPartition(self, hostname, threads, max_cores, num_mem, max_gpus, max_gpu_memory):
        """Adds a render partition to the job.

        :type  hostname: str
        :param hostname: hostname of the partition
        :type  threads: int
        :param threads: number of threads of the partition
        :type  max_cores: int
        :param max_cores: max cores enabled for the partition
        :type  num_mem: int
        :param num_mem: amount of memory reserved for the partition
        :type  max_gpus: int
        :param max_gpus: max gpu cores enabled for the partition
        :type  max_gpu_memory: int
        :param max_gpu_memory: amount of gpu memory reserved for the partition
        """
        self.stub.AddRenderPartition(
            job_pb2.JobAddRenderPartRequest(job=self.data,
                                            host=hostname,
                                            threads=threads,
                                            max_cores=max_cores,
                                            max_memory=num_mem,
                                            max_gpus=max_gpus,
                                            max_gpu_memory=max_gpu_memory,
                                            username=os.getenv("USER", "unknown")))

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this job.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: list of dependencies that depend directly on this job
        """
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.JobGetWhatDependsOnThisRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this job depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: dependencies that this job depends on
        """
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.JobGetWhatThisDependsOnRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def getDepends(self):
        """Returns a list of all depends this job is involved with.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: all depends involved with this job
        """
        response = self.stub.GetDepends(
            job_pb2.JobGetDependsRequest(job=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def dropDepends(self, target):
        """Drops the desired dependency target.

        :type  target: depend_pb2.DependTarget
        :param target: the desired dependency target to drop
        """
        return self.stub.DropDepends(job_pb2.JobDropDependsRequest(job=self.data, target=target),
                                     timeout=Cuebot.Timeout)

    def createDependencyOnJob(self, job):
        """Creates and returns a job-on-job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnJob(
            job_pb2.JobCreateDependencyOnJobRequest(job=self.data, on_job=job.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Create and return a job-on-layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this job to depend on
        :rtype:  opencue.wrappers.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.JobCreateDependencyOnLayerRequest(job=self.data, layer=layer.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Creates and returns a job-on-frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
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
        :param subject: comment subject
        :type  message: str
        :param message: comment message body
        """
        comment = comment_pb2.Comment(
            user=os.getenv("USER", "unknown"),
            subject=subject,
            message=message or " ",
            timestamp=0)
        self.stub.AddComment(job_pb2.JobAddCommentRequest(job=self.data, new_comment=comment),
                             timeout=Cuebot.Timeout)

    def getComments(self):
        """Returns the job's comment list.

        :rtype: list<opencue.wrappers.comment.Comment>
        :return: the job's comment list
        """
        response = self.stub.GetComments(job_pb2.JobGetCommentsRequest(job=self.data),
                                         timeout=Cuebot.Timeout)
        commentSeq = response.comments
        return [opencue.wrappers.comment.Comment(cmt) for cmt in commentSeq.comments]

    def setGroup(self, group):
        """Sets the job to a new group.

        :type  group: opencue.wrappers.group.Group
        :param group: the group you want the job to be in
        """
        self.stub.SetGroup(job_pb2.JobSetGroupRequest(job=self.data, group_id=group.id()),
                           timeout=Cuebot.Timeout)

    def reorderFrames(self, frame_range, order):
        """Reorders the specified frame range on this job.

        :type  frame_range: string
        :param frame_range: The frame range to reorder
        :type  order: job_pb2.Order
        :param order: First, Last or Reverse
        """
        self.stub.ReorderFrames(
            job_pb2.JobReorderFramesRequest(job=self.data, range=frame_range, order=order),
            timeout=Cuebot.Timeout)

    def staggerFrames(self, frame_range, stagger):
        """Staggers the specified frame range on this job.

        :type  frame_range: string
        :param frame_range: the frame range to stagger
        :type  stagger: int
        :param stagger: the amount to stagger by
        """
        self.stub.StaggerFrames(
            job_pb2.JobStaggerFramesRequest(job=self.data, range=frame_range, stagger=stagger),
            timeout=Cuebot.Timeout)

    def addSubscriber(self, subscriber):
        """Adds email subscriber to status change for the job

        :type subscriber: string
        :param subscriber: email address to send update when the job finishes
        """
        self.stub.AddSubscriber(job_pb2.JobAddSubscriberRequest(job=self.data,
                                                                subscriber=subscriber))

    def facility(self):
        """Returns the facility that the job must run in.

        :rtype: str
        :return: the job facility
        """
        return self.data.facility

    def id(self):
        """Returns the id of the job.

        :rtype:  str
        :return: id of the job
        """
        return self.data.id

    def name(self):
        """Returns the name of the job.

        :rtype:  str
        :return: name of the job
        """
        return self.data.name

    def show(self):
        """Returns the show name of the job.

        :rtype:  str
        :return: show name of the job
        """
        return self.data.show

    def shot(self):
        """Returns the shot name of the job.

        :rtype:  str
        :return: shot name of the job
        """
        return self.data.shot

    def logDir(self):
        """Returns the path to the job log files.

        :rtype:  str
        :return: path of job log files
        """
        return self.data.log_dir

    def uid(self):
        """Returns the uid of the person who owns the job.

        :rtype:  Optional[int]
        :return: uid of job owner
        """
        return self.data.uid if self.data.HasField("uid") else None

    def user(self):
        """Returns the username of the person who owns the job.

        :rtype: str
        :return: username of job owner
        """
        return self.data.user

    def username(self):
        """Returns the username of the person who owns the job.

        :rtype: str
        :return: username of job owner"""
        return self.user()

    def state(self):
        """Returns the job state.

        :rtype:  job_pb2.JobState
        :return: job state
        """
        return self.data.state

    def priority(self):
        """Returns the job priority.

        :rtype:  int
        :return: job priority
        """
        return self.data.priority

    def minCores(self):
        """Returns the minimum number of cores the job needs.

        :rtype:  int
        :return: job's min cores
        """
        return self.data.min_cores

    def maxCores(self):
        """Returns the maximum number of cores the job will use.

        :rtype:  int
        :return: job's max cores
        """
        return self.data.max_cores

    def minGpus(self):
        """Returns the minimum number of gpus the job needs.
        :rtype:  int
        :return: job's min gpus
        """
        return self.data.min_gpus

    def maxGpus(self):
        """Returns the maximum number of gpus the job will use.
        :rtype:  int
        :return: job's max gpus
        """
        return self.data.max_gpus

    def os(self):
        """Returns the job's operating system.

        :rtype:  str
        :return: operating system name of the job
        """
        return self.data.os

    # pylint: disable=redefined-builtin
    def startTime(self, format=None):
        """Returns the job start time in the desired format.

        Examples:
            None                    => 1203634027
            "%m/%d %H:%M"           => 02/21 14:47
            "%a %b %d %H:%M:%S %Y"  => Thu Feb 21 14:47:07 2008

        See the format table at:
        https://docs.python.org/3/library/time.html

        :type  format: str
        :param format: desired time format
        :rtype:  int/str
        :return: job start time in epoch, or string version of that timestamp if format given"""
        if not format:
            return self.data.start_time
        return time.strftime(format, time.localtime(self.data.start_time))

    # pylint: disable=redefined-builtin
    def stopTime(self, format=None):
        """Returns the job stop time in the desired format.

        Examples:
            None                    => 1203634027
            "%m/%d %H:%M"           => 02/21 14:47
            "%a %b %d %H:%M:%S %Y"  => Thu Feb 21 14:47:07 2008

        See the format table at:
        https://docs.python.org/3/library/time.html

        :type  format: str
        :param format: desired time format
        :rtype:  int/str
        :return: job stop time in epoch, or string version of that timestamp if format given"""
        if not format:
            return self.data.stop_time
        return time.strftime(format, time.localtime(self.data.stop_time))

    def runTime(self):
        """Returns the number of seconds that the job has been (or was) running.

        :rtype:  int
        :return: job runtime in seconds
        """
        if self.data.stop_time == 0:
            return int(time.time() - self.data.start_time)
        return self.data.stop_time - self.data.start_time

    def coreSecondsRemaining(self):
        """Returns the estimated number of core seconds needed to finish all waiting frames.

        Does not take into account running frames.

        :rtype:  long
        :return: core seconds remaining
        """
        return self.data.job_stats.remaining_core_sec

    def age(self):
        """Returns the number of seconds since the job was launched.

        :rtype:  int
        :return: seconds since the job was launched
        """
        return int(time.time() - self.data.start_time)

    def isPaused(self):
        """Returns true if the job is paused.

        :rtype:  bool
        :return: paused or not paused"""
        return self.data.is_paused

    def isAutoEating(self):
        """Returns true if the job is eating all frames that become dead.

        :rtype:  bool
        :return: if the job eating all frames that become dead
        """
        return self.data.auto_eat

    def isCommented(self):
        """Returns true if the job has a comment.

        :rtype:  bool
        :return: if the job has a comment
        """
        return self.data.has_comment

    def setAutoEat(self, value):
        """Sets a new autoeat value for the job.

        Autoeat means job frames, when they would become dead, are eaten instead.

        :type  value: bool
        :param value: new state for autoeat
        """
        self.setAutoEating(value)
        self.data.auto_eat = value

    def coresReserved(self):
        """Returns the number of reserved cores the job has.

        :rtype:  float
        :return: number of reserved cores
        """
        return self.data.job_stats.reserved_cores

    def totalFrames(self):
        """Returns the total number of frames the job has.

        :rtype:  int
        :return: total number of frames
        """
        return self.data.job_stats.total_frames

    def totalLayers(self):
        """Returns the total number of layers the job has.

        :rtype:  int
        :return: total number of layers
        """
        return self.data.job_stats.total_layers

    def dependFrames(self):
        """Returns the total number of dependent frames the job has.

        :rtype:  int
        :return: total number of dependent frames
        """
        return self.data.job_stats.depend_frames

    def succeededFrames(self):
        """Returns the total number of succeeded frames the job has.

        :rtype:  int
        :return: total number of succeeded frames
        """
        return self.data.job_stats.succeeded_frames

    def runningFrames(self):
        """Returns the total number of running frames the job has.

        :rtype:  int
        :return: total number of running frames
        """
        return self.data.job_stats.running_frames

    def deadFrames(self):
        """Returns the total number of deads frames the job has.

        :rtype:  int
        :return: total number of dead frames
        """
        return self.data.job_stats.dead_frames

    def waitingFrames(self):
        """Returns the total number of waiting frames the job has.

        :rtype:  int
        :return: total number of waiting frames
        """
        return self.data.job_stats.waiting_frames

    def eatenFrames(self):
        """Returns the total number of eaten frames the job has.

        :rtype:  int
        :return: total number of eaten frames
        """
        return self.data.job_stats.eaten_frames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames the job has.

        :rtype:  int
        :return: total number of pending (dependent and waiting) frames
        """
        return self.data.job_stats.pending_frames

    def frameStateTotals(self):
        """Returns a dictionary of frame states and the number of frames in each state.

        The states are available from job_pb2.FrameState.

        :rtype:  dict
        :return: total number of frames in each state
        """
        if not self.__frameStateTotals:
            self.__frameStateTotals.clear()
            for state in job_pb2.FrameState.keys():
                frameCount = getattr(self.data.job_stats, '{}_frames'.format(state.lower()), 0)
                self.__frameStateTotals[getattr(job_pb2, state)] = frameCount
        return self.__frameStateTotals

    def percentCompleted(self):
        """Returns the percent that the job's frames are completed.

        :rtype:  float
        :return: percentage of frame completion
        """
        try:
            return self.data.job_stats.succeeded_frames /\
                   float(self.data.job_stats.total_frames) * 100.0
        except ZeroDivisionError:
            return 0

    def group(self):
        """Returns the name of the group that the job is in.

        :rtype:  str
        :return: job group name
        """
        return self.data.group

    def avgFrameTime(self):
        """Returns the average completed frame time in seconds.

        :rtype:  int
        :return: average completed frame time in seconds
        """
        return self.data.job_stats.avg_frame_sec

    def averageCoreTime(self):
        """Returns the average frame core time.

        :rtype:  int
        :return: average frame core time for entire job
        """
        return self.data.job_stats.avg_core_sec

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this job used.

        Value is within 5% of the actual highest frame.

        :rtype:  long
        :return: most memory used by any frame in kB"""
        return self.data.job_stats.max_rss

    def shutdownIfCompleted(self):
        """Shutdown the job if it is completed."""
        self.stub.ShutdownIfCompleted(job_pb2.JobShutdownIfCompletedRequest(job=self.data),
                                      timeout=Cuebot.Timeout)

    def lokiURL(self):
        """Returns url for loki server on the job

        :rtype: str
        :return: Return URL of loki server of the job
        """
        return self.data.loki_url

class NestedJob(Job):
    """This class contains information and actions related to a nested job."""
    def __init__(self, nestedJob=None):
        super(NestedJob, self).__init__(nestedJob)
        # job children are most likely empty but its possible to
        # populate this with NestedLayer objects.
        self.__children = []

    def children(self):
        """Returns all job children."""
        return self.__children

    def kill(self, username=None, pid=None, host_kill=None, reason=None):
        """Kills the job."""
        self.asJob().kill(username, pid, host_kill, reason)

    def pause(self):
        """Pauses the job."""
        self.asJob().pause()

    def resume(self):
        """Resumes the job."""
        self.asJob().resume()

    def killFrames(self, username=None, pid=None, host_kill=None, reason=None, **request):
        """Kills all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        self.asJob().killFrames(username, pid, host_kill, reason, **request)

    def eatFrames(self, **request):
        """Eats all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        self.asJob().eatFrames(**request)

    def retryFrames(self, **request):
        """Retries all frames that match the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        self.asJob().retryFrames(**request)

    def markdoneFrames(self, **request):
        """Drops any dependency that requires any frame that matches the FrameSearch.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        self.asJob().markdoneFrames(**request)

    def markAsWaiting(self, **request):
        """Changes the matching frames from the depend state to the waiting state.

        :type  request: Dict
        :param request: FrameSearch parameters
        """
        self.asJob().markAsWaiting(**request)

    def setMinCores(self, minCores):
        """Sets the minimum cores value.

        :type  minCores: int
        :param minCores: new minimum cores value
        """
        self.asJob().setMinCores(minCores)

    def setMaxCores(self, maxCores):
        """Sets the maximum cores value.

        :type  maxCores: int
        :param maxCores: new maximum cores value
        """
        self.asJob().setMaxCores(maxCores)

    def setMinGpus(self, minGpus):
        """Sets the minimum gpus value
        :type  minGpus: int
        :param minGpus: New minimum gpus value"""
        self.asJob().setMinGpus(minGpus)

    def setMaxGpus(self, maxGpus):
        """Sets the maximum gpus value
        :type  maxGpus: int
        :param maxGpus: New maximum gpus value"""
        self.asJob().setMaxGpus(maxGpus)

    def setPriority(self, priority):
        """Sets the job priority.

        :type  priority: int
        :param priority: new priority number
        """
        self.asJob().setPriority(priority)

    def setMaxRetries(self, maxRetries):
        """Sets the number of retries before a frame goes dead.

        :type  maxRetries: int
        :param maxRetries: new max retries
        """
        self.asJob().setMaxRetries(maxRetries)

    def getLayers(self):
        """Returns the list of job layers.

        :rtype:  list<opencue.wrappers.layer.Layer>
        :return: list of layers in the job
        """
        return self.asJob().getLayers()

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the job.

        frames = job.getFrames(show=["edu","beo"],user="jwelborn")
        frames = job.getFrames(show="edu",shot="bs.012")
        Allowed: offset, limit, states+, layers+. frameset, changedate

        :rtype:  list<opencue.wrappers.frame.Frame>
        :return: list of matching frames"""
        return self.asJob().getFrames(**options)

    def getUpdatedFrames(self, lastCheck, layers=None):
        """Returns a list of state information for frames that have been recently updated.

        This includes any frames that have changed since the last update time as well as the
        current state of the job. If layer proxies are provided in the layers list, only frames
        from those layers will be returned.

        :type  lastCheck: int
        :param lastCheck: epoch when last updated
        :type  layers: list<job_pb2.Layer>
        :param layers: list of layers to check, empty list checks all
        :rtype:  job_pb2.JobGetUpdatedFramesResponse
        :return: job state and a list of updated frames
        """
        return self.asJob().getUpdatedFrames(lastCheck, layers)

    def setAutoEating(self, value):
        """If set to true, any frames that would become dead, will become eaten.

        :type  value: bool
        :param value: state of autoeat
        """
        self.asJob().setAutoEating(value)

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this job.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: list of dependencies that depend directly on this job
        """
        return self.asJob().getWhatDependsOnThis()

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this job depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: dependencies that this job depends on
        """
        return self.asJob().getWhatThisDependsOn()

    def getDepends(self):
        """Returns a list of all depends this job is involved with.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: all depends involved with this job
        """
        return self.asJob().getDepends()

    def dropDepends(self, target):
        """Drops the desired dependency target.

            depend_pb2.DependTarget.AnyTarget
            depend_pb2.DependTarget.External
            depend_pb2.DependTarget.Internal

        :type  target: depend_pb2.DependTarget
        :param target: The desired dependency target to drop
        """
        return self.asJob().dropDepends(target)

    def createDependencyOnJob(self, job):
        """Creates and returns a job-on-job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency
        """
        return self.asJob().createDependencyOnJob(job)

    def createDependencyOnLayer(self, layer):
        """Creates and returns a job-on-layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        return self.asJob().createDependencyOnLayer(layer)

    def createDependencyOnFrame(self, frame):
        """Creates and returns a job-on-frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        return self.asJob().createDependencyOnFrame(frame)

    def addComment(self, subject, message):
        """Appends a comment to the job's comment list.

        :type  subject: str
        :param subject: comment subject
        :type  message: str
        :param message: comment message body
        """
        self.asJob().addComment(subject, message)

    def getComments(self):
        """Returns the job's comment list."""
        return self.asJob().getComments()

    def setGroup(self, group):
        """Sets the job to a new group.

        :type  group: opencue.wrappers.group.Group
        :param group: the group you want the job to be in.
        """
        self.asJob().setGroup(group)

    def reorderFrames(self, frame_range, order):
        """Reorders the specified frame range on this job.

        :type  frame_range: string
        :param frame_range: The frame range to reorder
        :type  order: job_pb2.Order
        :param order: First, Last or Reverse
        """
        self.asJob().reorderFrames(frame_range, order)

    def staggerFrames(self, frame_range, stagger):
        """Staggers the specified frame range on this job.

        :type  frame_range: string
        :param frame_range: the frame range to stagger
        :type  stagger: int
        :param stagger: the amount to stagger by
        """
        self.asJob().staggerFrames(frame_range, stagger)

    def asJob(self):
        """Returns a Job object from this NestedJob.

        :rtype: opencue.wrappers.job.Job
        :return: Job version of this NestedJob
        """
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
