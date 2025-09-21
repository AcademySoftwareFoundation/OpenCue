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

"""Module for classes related to job layers."""

import enum
import getpass
import os
import platform

from opencue_proto import job_pb2
import opencue.api
from opencue.cuebot import Cuebot
import opencue.search
import opencue.wrappers.depend
import opencue.wrappers.frame
import opencue.wrappers.limit


class Layer(object):
    """This class contains the grpc implementation related to a Layer."""

    class LayerType(enum.IntEnum):
        """Represents the type of layer."""
        PRE = job_pb2.PRE
        POST = job_pb2.POST
        RENDER = job_pb2.RENDER
        UTIL = job_pb2.UTIL

    class Order(enum.IntEnum):
        """Represents the order of a layer."""
        FIRST = job_pb2.FIRST
        LAST = job_pb2.LAST
        REVERSE = job_pb2.REVERSE

    def __init__(self, layer=None):
        self.data = layer
        self.stub = Cuebot.getStub('layer')

    def kill(self, username=None, pid=None, host_kill=None, reason=None):
        """Kills the entire layer."""
        username = username if username else getpass.getuser()
        pid = pid if pid else os.getpid()
        host_kill = host_kill if host_kill else platform.uname()[1]
        return self.stub.KillFrames(job_pb2.LayerKillFramesRequest(layer=self.data,
                                                                   username=username,
                                                                   pid=str(pid),
                                                                   host_kill=host_kill,
                                                                   reason=reason),
                                    timeout=Cuebot.Timeout)

    def eat(self):
        """Eats the entire layer."""
        return self.stub.EatFrames(job_pb2.LayerEatFramesRequest(layer=self.data),
                                   timeout=Cuebot.Timeout)

    def retry(self):
        """Retries the entire layer."""
        return self.stub.RetryFrames(job_pb2.LayerRetryFramesRequest(layer=self.data),
                                     timeout=Cuebot.Timeout)

    def markdone(self):
        """Drops any dependency that requires this layer or requires any frame in the layer."""
        return self.stub.MarkdoneFrames(job_pb2.LayerMarkdoneFramesRequest(layer=self.data),
                                        timeout=Cuebot.Timeout)

    def addLimit(self, limit_id):
        """Adds a limit to the current layer."""
        return self.stub.AddLimit(job_pb2.LayerAddLimitRequest(layer=self.data, limit_id=limit_id),
                                  timeout=Cuebot.Timeout)

    def dropLimit(self, limit_id):
        """Removes a limit on the current layer."""
        return self.stub.DropLimit(
            job_pb2.LayerDropLimitRequest(layer=self.data, limit_id=limit_id),
            timeout=Cuebot.Timeout)

    def enableMemoryOptimizer(self, value):
        """Enables or disables the memory optimizer.

        :type  value: bool
        :param value: whether memory optimizer is enabled
        """
        return self.stub.EnableMemoryOptimizer(job_pb2.LayerEnableMemoryOptimizerRequest(
            layer=self.data, value=value),
            timeout=Cuebot.Timeout)

    def getFrames(self, **options):
        """Returns a list of up to 1000 frames from within the layer.

        :type  options: dict
        :param options: FrameSearch options
        :rtype:  list<opencue.wrappers.frame.Frame>
        :return: sequence of matching frames
        """
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**options)
        response = self.stub.GetFrames(job_pb2.LayerGetFramesRequest(layer=self.data, s=criteria),
                                       timeout=Cuebot.Timeout)
        return [opencue.wrappers.frame.Frame(frameData) for frameData in response.frames.frames]

    def getOutputPaths(self):
        """Return the output paths for this layer.

        :rtype: list<str>
        :return: list of output paths
        """
        return self.stub.GetOutputPaths(job_pb2.LayerGetOutputPathsRequest(layer=self.data),
                                        timeout=Cuebot.Timeout).output_paths

    def setTags(self, tags):
        """Sets the layer tags.

        :type  tags: list<str>
        :param tags: layer tags
        """
        return self.stub.SetTags(job_pb2.LayerSetTagsRequest(layer=self.data, tags=tags),
                                 timeout=Cuebot.Timeout)

    def setMaxCores(self, cores):
        """Sets the maximum number of cores that this layer requires.

        :type  cores: float
        :param cores: Core units, 100 reserves 1 core
        """
        return self.stub.SetMaxCores(
            job_pb2.LayerSetMaxCoresRequest(layer=self.data, cores=cores/100.0),
            timeout=Cuebot.Timeout)

    def setMinCores(self, cores):
        """Sets the minimum number of cores that this layer requires.

        Use 100 to reserve 1 core.

        :type  cores: int
        :param cores: core units, 100 reserves 1 core
        """
        return self.stub.SetMinCores(
            job_pb2.LayerSetMinCoresRequest(layer=self.data, cores=cores/100.0),
            timeout=Cuebot.Timeout)

    def setMaxGpus(self, max_gpus):
        """Sets the maximum number of gpus that this layer requires.
        :type  max_gpus: int
        :param max_gpus: gpu cores"""
        return self.stub.SetMaxGpus(
            job_pb2.LayerSetMaxGpusRequest(layer=self.data, max_gpus=max_gpus),
            timeout=Cuebot.Timeout)

    def setMinGpus(self, min_gpus):
        """Sets the minimum number of gpus that this layer requires.
        :type  min_gpus: int
        :param min_gpus: gou cores"""
        return self.stub.SetMinGpus(
            job_pb2.LayerSetMinGpusRequest(layer=self.data, min_gpus=min_gpus),
            timeout=Cuebot.Timeout)

    def setMinGpuMemory(self, gpu_memory):
        """Sets the minimum number of gpu memory that this layer requires.

        :type  gpu_memory: int
        :param gpu_memory: gpu_memory value
        """
        return self.stub.SetMinGpuMemory(
            job_pb2.LayerSetMinGpuMemoryRequest(layer=self.data, gpu_memory=gpu_memory),
            timeout=Cuebot.Timeout)

    def setMinMemory(self, memory):
        """Sets the minimum amount of memory that this layer requires.

        :type  memory: int
        :param memory: Minimum Kb memory reserved by each frame
        """
        return self.stub.SetMinMemory(
            job_pb2.LayerSetMinMemoryRequest(layer=self.data, memory=memory),
            timeout=Cuebot.Timeout)

    def setThreadable(self, threadable):
        """Sets the threadable field.

        :type  threadable: bool
        :param threadable: boolean to enable/disable threadable
        """
        return self.stub.SetThreadable(job_pb2.LayerSetThreadableRequest(
            layer=self.data, threadable=threadable),
            timeout=Cuebot.Timeout)

    def setTimeout(self, timeout):
        """Set time out to the value.
        :type timeout: int
        :param timeout: value for timeout in minutes"""
        return self.stub.SetTimeout(job_pb2.LayerSetTimeoutRequest(
            layer=self.data, timeout=timeout),
            timeout=Cuebot.Timeout)

    def setTimeoutLLU(self, timeout_llu):
        """Set LLU time out to the value.
        :type timeout: int
        :param timeout: value for timeout in minutes"""
        return self.stub.SetTimeoutLLU(job_pb2.LayerSetTimeoutLLURequest(
            layer=self.data, timeout_llu=timeout_llu),
            timeout=Cuebot.Timeout)

    def addRenderPartition(self, hostname, threads, max_cores, max_mem, max_gpu_memory, max_gpus):
        """Adds a render partition to the layer.

        :type  hostname: str
        :param hostname: hostname of the partition
        :type  threads: int
        :param threads: number of threads of the partition
        :type  max_cores: int
        :param max_cores: max cores enabled for the partition
        :type  max_mem: int
        :param max_mem: amount of memory reserved for the partition
        :type  max_gpu_memory: int
        :param max_gpu_memory: max gpu memory enabled for the partition
        :type  max_gpus: int
        :param max_gpus: max gpus enabled for the partition
        """
        self.stub.AddRenderPartition(
            job_pb2.LayerAddRenderPartitionRequest(layer=self.data,
                                                   host=hostname,
                                                   threads=threads,
                                                   max_cores=max_cores,
                                                   max_memory=max_mem,
                                                   max_gpu_memory=max_gpu_memory,
                                                   username=os.getenv("USER", "unknown"),
                                                   max_gpus=max_gpus))

    def getWhatDependsOnThis(self):
        """Gets a list of dependencies that depend directly on this layer.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: list of dependencies that depend directly on this layer
        """
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.LayerGetWhatDependsOnThisRequest(layer=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this layer depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: list of dependences that this layer depends on
        """
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.LayerGetWhatThisDependsOnRequest(layer=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def createDependencyOnJob(self, job):
        """Creates and returns a layer-on-job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnJob(
            job_pb2.LayerCreateDependOnJobRequest(layer=self.data, job=job.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Creates and returns a layer-on-layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this layer to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.LayerCreateDependOnLayerRequest(layer=self.data, depend_on_layer=layer.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Creates and returns a layer-on-frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this layer to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnFrame(
            job_pb2.LayerCreateDependOnFrameRequest(layer=self.data, frame=frame.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createFrameByFrameDependency(self, layer):
        """Creates and returns a frame-by-frame layer dependency.

        :param layer: the layer you want this layer to depend on
        :type  layer: opencue.wrappers.layer.Layer
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        # anyframe is hard coded right now, this option should be moved
        # to LayerOnLayer for better efficiency.
        response = self.stub.CreateFrameByFrameDependency(
            job_pb2.LayerCreateFrameByFrameDependRequest(
                layer=self.data, depend_layer=layer.data, any_frame=False),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    # TODO(gregdenton) Determine if this is needed. (Issue #71)
    # def unbookProcs(self, subs, number, kill=False):
    #     """Unbook procs off layer from specified subscriptions
    #     :type  subs: list<Subscription>
    #     :param subs: the subscriptions to unbook from
    #     :type  number: int
    #     :param number: the number of virtual procs to unbook
    #     :type  kill: bool
    #     :param kill: wheather or not to kill the frames as well"""
    #     self.proxy.unbookProcs([a.proxy for a in subs], number, kill)

    def registerOutputPath(self, outputPath):
        """Registers an output path for the layer.

        Output paths are included in OpenCue alert emails.

        :type  outputPath: str
        :param outputPath: output path to register
        """
        self.stub.RegisterOutputPath(
            job_pb2.LayerRegisterOutputPathRequest(layer=self.data, spec=outputPath),
            timeout=Cuebot.Timeout)

    def reorderFrames(self, frameRange, order):
        """Reorders the specified frame range on this layer.

        :type  frameRange: string
        :param frameRange: the frame range to reorder
        :type  order: opencue.wrapper.layer.Layer.Order
        :param order: First, Last or Reverse
        """
        self.stub.ReorderFrames(
            job_pb2.LayerReorderFramesRequest(layer=self.data, range=frameRange, order=order),
            timeout=Cuebot.Timeout)

    def staggerFrames(self, frameRange, stagger):
        """Staggers the specified frame range on this layer.

        :type  frameRange: string
        :param frameRange: the frame range to stagger
        :type  stagger: int
        :param stagger: the amount to stagger by
        """
        self.stub.StaggerFrames(
            job_pb2.LayerStaggerFramesRequest(layer=self.data, range=frameRange, stagger=stagger),
            timeout=Cuebot.Timeout)

    def getLimitDetails(self):
        """Returns the Limit objects for the given layer.

        :rtype:  list<opencue.wrappers.limit.Limit>
        :return: list of limits on this layer
        """
        return [opencue.wrappers.limit.Limit(limit) for limit in self.stub.GetLimits(
            job_pb2.LayerGetLimitsRequest(layer=self.data), timeout=Cuebot.Timeout).limits]

    def id(self):
        """Returns the id of the layer.

        :rtype:  str
        :return: layer id
        """
        return self.data.id

    def name(self):
        """Returns the name of the layer.

        :rtype:  str
        :return: layer name
        """
        return self.data.name

    def range(self):
        """Returns the frame range of the layer.

        :rtype:  str
        :return: layer frame range
        """
        return self.data.range

    def chunkSize(self):
        """Returns the number of frames per task.

        :rtype:  int
        :return: layer chunk size
        """
        return self.data.chunk_size

    def tags(self):
        """Returns the tags applied to the layer.

        TODO: Document syntax

        :rtype:  str
        :return: layer tags"""
        return self.data.tags

    def dispatchOrder(self):
        """Returns the layer dispatch order.

        :rtype:  int
        :return: layer dispatch order
        """
        return self.data.dispatch_order

    def coresReserved(self):
        """Returns the number of cores reserved on this layer.

        :rtype: float
        :return: cores reserved
        """
        return self.data.layer_stats.reserved_cores

    def gpusReserved(self):
        """Returns the number of gpus reserved on this layer
        :rtype: float
        :return: gpus reserved"""
        return self.data.layer_stats.reserved_gpus

    def minCores(self):
        """Returns the minimum number of cores that frames in this layer require.

        :rtype:  int
        :return: minimum number of cores required
        """
        return self.data.min_cores

    def minGpus(self):
        """Returns the minimum number of gpus that frames in this layer require
        :rtype:  int
        :return: Minimum number of gpus required"""
        return self.data.min_gpus

    def minMemory(self):
        """Returns the minimum amount of memory that frames in this layer require.

        :rtype:  int
        :return: minimum kB of memory required by frames in this layer
        """
        return self.data.min_memory

    def limits(self):
        """Returns the limit names for this layer.

        :rtype: list<str>
        :return: names of the limits on this layer
        """
        return self.data.limits

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this layer used.

        Value is within 5% of the actual highest frame.

        :rtype:  long
        :return: most memory used by any frame in this layer in kB"""
        return self.data.layer_stats.max_rss

    def type(self):
        """Returns the type of layer.

        Ex: Pre, Post, Render

        :rtype:  job_pb2.LayerType
        :return: type of layer
        """
        return self.data.type

    def totalFrames(self):
        """Returns the total number of frames in the layer.

        :rtype:  int
        :return: total number of frames
        """
        return self.data.layer_stats.total_frames

    def dependFrames(self):
        """Returns the total number of dependent frames in the layer.

        :rtype:  int
        :return: total number of dependent frames
        """
        return self.data.layer_stats.depend_frames

    def succeededFrames(self):
        """Returns the total number of succeeded frames in the layer.

        :rtype:  int
        :return: total number of succeeded frames
        """
        return self.data.layer_stats.succeeded_frames

    def runningFrames(self):
        """Returns the total number of running frames in the layer.

        :rtype:  int
        :return: total number of running frames
        """
        return self.data.layer_stats.running_frames

    def deadFrames(self):
        """Returns the total number of dead frames in the layer.

        :rtype:  int
        :return: total number of dead frames
        """
        return self.data.layer_stats.dead_frames

    def waitingFrames(self):
        """Returns the total number of waiting frames in the layer.

        :rtype:  int
        :return: total number of waiting frames
        """
        return self.data.layer_stats.waiting_frames

    def eatenFrames(self):
        """Returns the total number of eaten frames in the layer.

        :rtype:  int
        :return: total number of eaten frames
        """
        return self.data.layer_stats.eaten_frames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames in the layer.

        :rtype:  int
        :return: total number of pending (dependent and waiting) frames
        """
        return self.data.layer_stats.pending_frames

    def percentCompleted(self):
        """Returns the percent that the layer's frames are completed.

        :rtype:  float
        :return: percentage of frame completion
        """
        try:
            return self.data.layer_stats.succeeded_frames / \
                   float(self.data.layer_stats.total_frames) * 100.0
        except ZeroDivisionError:
            return 0

    def avgFrameTimeSeconds(self):
        """Returns the average frame completion time in seconds.

        :rtype:  int
        :return: average frame completion time in seconds
        """
        return self.data.layer_stats.avg_frame_sec

    def avgCoreSeconds(self):
        """Returns the average core time used in seconds.

        :rtype:  int
        :return: average core time in seconds
        """
        return self.data.layer_stats.avg_core_sec

    def coreSecondsRemaining(self):
        """Returns the estimated core time that is remaining to complete all waiting frames.

        :rtype:  int
        :return: the number of seconds of estimated core time remaining
        """
        return self.data.layer_stats.remaining_core_sec

    def parent(self):
        """Gets the parent of the layer; its job.

        :rtype: opencue.wrappers.job.Job
        :return: the layer's parent job
        """
        return opencue.api.getJob(self.data.parent_id)

    def services(self):
        """Returns list of services applied to this layer
        :rtype: opencue.wrappers.service.Service
        :return: the layer's services
        """
        return [opencue.api.getService(service) for service in self.data.services]
