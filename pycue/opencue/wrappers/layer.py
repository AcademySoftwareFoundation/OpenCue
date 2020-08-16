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
opencue layer module

implementation of a layer in opencue
"""

import enum
import os

from opencue.compiled_proto import job_pb2
from opencue.cuebot import Cuebot
import opencue.search
import opencue.wrappers.depend
import opencue.wrappers.frame
import opencue.wrappers.limit
import opencue.api


class Layer(object):
    """This class contains the grpc implementation related to a Layer."""

    class LayerType(enum.IntEnum):
        PRE = job_pb2.PRE
        POST = job_pb2.POST
        RENDER = job_pb2.RENDER
        UTIL = job_pb2.UTIL

    class Order(enum.IntEnum):
        FIRST = job_pb2.FIRST
        LAST = job_pb2.LAST
        REVERSE = job_pb2.REVERSE

    def __init__(self, layer=None):
        self.data = layer
        self.stub = Cuebot.getStub('layer')

    def kill(self):
        """Kill entire layer"""
        return self.stub.KillFrames(job_pb2.LayerKillFramesRequest(layer=self.data),
                                    timeout=Cuebot.Timeout)

    def eat(self):
        """Eat entire layer"""
        return self.stub.EatFrames(job_pb2.LayerEatFramesRequest(layer=self.data),
                                   timeout=Cuebot.Timeout)

    def retry(self):
        """Retry entire layer"""
        return self.stub.RetryFrames(job_pb2.LayerRetryFramesRequest(layer=self.data),
                                     timeout=Cuebot.Timeout)

    def markdone(self):
        """Drops any dependency that requires this layer or requires any frame
        in the layer"""
        return self.stub.MarkdoneFrames(job_pb2.LayerMarkdoneFramesRequest(layer=self.data),
                                        timeout=Cuebot.Timeout)

    def addLimit(self, limit_id):
        """Add a limit to the current layer."""
        return self.stub.AddLimit(job_pb2.LayerAddLimitRequest(layer=self.data, limit_id=limit_id),
                                  timeout=Cuebot.Timeout)
    
    def dropLimit(self, limit_id):
        """Remove a limit on the current layer."""
        return self.stub.DropLimit(
            job_pb2.LayerDropLimitRequest(layer=self.data, limit_id=limit_id),
            timeout=Cuebot.Timeout)

    def enableMemoryOptimizer(self, value):
        """Set enableMemoryOptimizer to the value.

        :type value: bool
        :param value: boolean to enable/disable memory optimizer"""
        return self.stub.EnableMemoryOptimizer(job_pb2.LayerEnableMemoryOptimizerRequest(
            layer=self.data, value=value),
            timeout=Cuebot.Timeout)

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the layer.

        :rtype:  list<opencue.wrappers.frame.Frame>
        :return: Sequence of Frame obejcts"""
        criteria = opencue.search.FrameSearch.criteriaFromOptions(**options)
        response = self.stub.GetFrames(job_pb2.LayerGetFramesRequest(layer=self.data, s=criteria),
                                       timeout=Cuebot.Timeout)
        return [opencue.wrappers.frame.Frame(frameData) for frameData in response.frames.frames]

    def getOutputPaths(self):
        """Return the output paths for this layer.

        :rtype: list<str>
        :return: list of output paths"""
        return self.stub.GetOutputPaths(job_pb2.LayerGetOutputPathsRequest(layer=self.data),
                                        timeout=Cuebot.Timeout).output_paths

    def setTags(self, tags):
        """Sets the tags, TODO: update description of tag structure.

        :type  tags: list<str>
        :param tags: Layer tags"""
        return self.stub.SetTags(job_pb2.LayerSetTagsRequest(layer=self.data, tags=tags),
                                 timeout=Cuebot.Timeout)

    def setMaxCores(self, cores):
        """Sets the maximum number of cores that this layer requires.

        :type  cores: float
        :param cores: Core units, 100 reserves 1 core"""
        return self.stub.SetMaxCores(
            job_pb2.LayerSetMaxCoresRequest(layer=self.data, cores=cores/100.0),
            timeout=Cuebot.Timeout)

    def setMinCores(self, cores):
        """Sets the minimum number of cores that this layer requires.
        Use 100 to reserve 1 core.

        :type  cores: int
        :param cores: Core units, 100 reserves 1 core"""
        return self.stub.SetMinCores(
            job_pb2.LayerSetMinCoresRequest(layer=self.data, cores=cores/100.0),
            timeout=Cuebot.Timeout)

    def setMaxGpu(self, gpu):
        """Sets the maximum number of gpu that this layer requires.
        :type  gpu: float
        :param gpu: Core units, 100 reserves 1 core"""
        return self.stub.SetMaxGpu(
            job_pb2.LayerSetMaxGpuRequest(layer=self.data, gpu=int(gpu)),
            timeout=Cuebot.Timeout)

    def setMinGpu(self, gpu):
        """Sets the minimum number of gpu that this layer requires.
        Use 100 to reserve 1 core.
        :type  gpu: int
        :param gpu: Core units, 100 reserves 1 core"""
        return self.stub.SetMinGpu(
            job_pb2.LayerSetMinGpuRequest(layer=self.data, gpu=int(gpu)),
            timeout=Cuebot.Timeout)

    def setMinGpuMemory(self, memory):
        """Sets the minimum number of memory memory that this layer requires.
        :type  memory: int
        :param memory: memory value"""
        return self.stub.SetMinGpuMemory(
            job_pb2.LayerSetMinGpuMemoryRequest(layer=self.data, memory=memory),
            timeout=Cuebot.Timeout)

    def setMinMemory(self, memory):
        """Sets the minimum amount of memory that this layer requires. in Kb

        :type  memory: int
        :param memory: Minimum Kb memory reserved by each frame"""
        return self.stub.SetMinMemory(
            job_pb2.LayerSetMinMemoryRequest(layer=self.data, memory=memory),
            timeout=Cuebot.Timeout)

    def setThreadable(self, threadable):
        """Set enableMemoryOptimizer to the value.

        :type threadable: bool
        :param threadable: boolean to enable/disable threadable"""
        return self.stub.SetThreadable(job_pb2.LayerSetThreadableRequest(
            layer=self.data, threadable=threadable),
            timeout=Cuebot.Timeout)

    def addRenderPartition(self, hostname, threads, max_cores, num_mem, max_gpu):
        """Add a render partition to the layer.
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
            job_pb2.LayerAddRenderPartitionRequest(layer=self.data,
                                                   host=hostname,
                                                   threads=threads,
                                                   max_cores=max_cores,
                                                   max_memory=num_mem,
                                                   max_gpu=max_gpu,
                                                   username=os.getenv("USER", "unknown")))

    def getWhatDependsOnThis(self):
        """Gets a list of dependencies that depend directly on this layer.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: List of dependencies that depend directly on this layer"""
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.LayerGetWhatDependsOnThisRequest(layer=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def getWhatThisDependsOn(self):
        """Get a list of dependencies that this layer depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: List of dependences that this layer depends on"""
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.LayerGetWhatThisDependsOnRequest(layer=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [opencue.wrappers.depend.Depend(dep) for dep in dependSeq.depends]

    def createDependencyOnJob(self, job):
        """Create and return a layer on job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this job to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
        response = self.stub.CreateDependencyOnJob(
            job_pb2.LayerCreateDependOnJobRequest(layer=self.data, job=job.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Create and return a layer on layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this layer to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.LayerCreateDependOnLayerRequest(layer=self.data, depend_on_layer=layer.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Create and return a layer on frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this layer to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
        response = self.stub.CreateDependencyOnFrame(
            job_pb2.LayerCreateDependOnFrameRequest(layer=self.data, frame=frame.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createFrameByFrameDependency(self, layer):
        """Create and return a frame by frame frame dependency.

        :param layer: the layer you want this layer to depend on
        :type  layer: opencue.wrappers.layer.Layer
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency"""
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
        """Register an output with the given layer. The output paths are sent in the opencue email.

        :type outputPath: str
        :param outputPath: Output path to register
        """
        self.stub.RegisterOutputPath(
            job_pb2.LayerRegisterOutputPathRequest(layer=self.data, spec=outputPath),
            timeout=Cuebot.Timeout)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this layer.

        :type  range: string
        :param range: The frame range to reorder
        :type  order: opencue.wrapper.layer.Layer.Order
        :param order: First, Last or Reverse"""
        self.stub.ReorderFrames(
            job_pb2.LayerReorderFramesRequest(layer=self.data, range=range, order=order),
            timeout=Cuebot.Timeout)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this layer.

        :type  range: string
        :param range: The frame range to stagger
        :type  stagger: int
        :param stagger: The amount to stagger by"""
        self.stub.StaggerFrames(
            job_pb2.LayerStaggerFramesRequest(layer=self.data, range=range, stagger=stagger),
            timeout=Cuebot.Timeout)
      
    def getLimitDetails(self):
        """Return the Limit objects for the given layer.

        :rtype: list<opencue.wrappers.limit.Limit>
        :return: The list of limits on this layer."""
        return [opencue.wrappers.limit.Limit(limit) for limit in self.stub.GetLimits(
            job_pb2.LayerGetLimitsRequest(layer=self.data), timeout=Cuebot.Timeout).limits]

    def id(self):
        """Returns the uuid of the layer.

        :rtype:  str
        :return: Layer uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the layer.

        :rtype:  str
        :return: Layer name"""
        return self.data.name

    def range(self):
        """Returns the frame range for the layer.

        :rtype:  str
        :return: Layer frame range"""
        return self.data.range

    def chunkSize(self):
        """Returns the number of frames per task.

        :rtype:  int
        :return: the chunks size"""
        return self.data.chunk_size

    def tags(self):
        """Returns the tags applied to the layer
        TODO: Document syntax

        :rtype:  str
        :return: Layer tags"""
        return self.data.tags

    def dispatchOrder(self):
        """Returns the layers dispatch order.

        :rtype:  int
        :return: Layer dispatch order"""
        return self.data.dispatch_order

    def coresReserved(self):
        """Returns the number of cores reserved on this layer.

        :rtype: float
        :return: cores reserved"""
        return self.data.layer_stats.reserved_cores

    def gpuReserved(self):
        """Returns the number of gpus reserved on this layer
        :rtype: float
        :return: gpu reserved"""
        return self.data.layer_stats.reserved_gpu

    def minCores(self):
        """Returns the minimum number of cores that frames in this layer require.

        :rtype:  int
        :return: Minimum number of cores required"""
        return self.data.min_cores

    def minGpu(self):
        """Returns the minimum number of gpu that frames in this layer require
        :rtype:  int
        :return: Minimum number of gpu required"""
        return self.data.min_gpu

    def minMemory(self):
        """Returns the minimum about of memory that frames in this layer require.

        :rtype:  int
        :return: Minimum Kb memory required by frames in this layer"""
        return self.data.min_memory
    
    def limits(self):
        """Returns the limit names for this layer.

        :rtype: list<str>
        :return: Names of the limits on this layer."""
        return self.data.limits

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this layer
        used in kB. Value is within 5% of the actual highest frame.

        :rtype:  long
        :return: Most memory used by any frame in this layer in kB"""
        return self.data.layer_stats.max_rss

    def type(self):
        """Returns the type of layer. Ex: Pre, Post, Render

        :rtype:  opencue.LayerType
        :return: Type of layer"""
        return self.data.type

    def totalFrames(self):
        """Returns the total number of frames under this object.

        :rtype:  int
        :return: Total number of frames"""
        return self.data.layer_stats.total_frames

    def dependFrames(self):
        """Returns the total number of dependent frames under this object.

        :rtype:  int
        :return: Total number of dependent frames"""
        return self.data.layer_stats.depend_frames

    def succeededFrames(self):
        """Returns the total number of succeeded frames under this object.

        :rtype:  int
        :return: Total number of succeeded frames"""
        return self.data.layer_stats.succeeded_frames

    def runningFrames(self):
        """Returns the total number of running frames under this object.

        :rtype:  int
        :return: Total number of running frames"""
        return self.data.layer_stats.running_frames

    def deadFrames(self):
        """Returns the total number of deads frames under this object.

        :rtype:  int
        :return: Total number of dead frames"""
        return self.data.layer_stats.dead_frames

    def waitingFrames(self):
        """Returns the total number of waiting frames under this object.

        :rtype:  int
        :return: Total number of waiting frames"""
        return self.data.layer_stats.waiting_frames

    def eatenFrames(self):
        """Returns the total number of eaten frames under this object.

        :rtype:  int
        :return: Total number of eaten frames"""
        return self.data.layer_stats.eaten_frames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.

        :rtype:  int
        :return: Total number of pending (dependent and waiting) frames"""
        return self.data.layer_stats.pending_frames

    def percentCompleted(self):
        """Returns the percent that the object's frames are completed.

        :rtype:  float
        :return: Percentage of frame completion"""
        try:
            return self.data.layer_stats.succeeded_frames / \
                   float(self.data.layer_stats.total_frames) * 100.0
        except:
            return 0

    def avgFrameTimeSeconds(self):
        """Returns the average frame completion time in seconds.

        :rtype:  int
        :return: Average frame completion time in seconds"""
        return self.data.layer_stats.avg_frame_sec

    def avgCoreSeconds(self):
        """Returns the average core time used in seconds.

        :rtype:  int
        :return: Average core time in seconds"""
        return self.data.layer_stats.avg_core_sec

    def coreSecondsRemaining(self):
        """Returns the estimated core time that is remnainining to complete
        all waiting frames.

        :rtype:  int
        :return: the number of seconds of estimated core time remaining"""
        return self.data.layer_stats.remaining_core_sec

    def parent(self):
        return opencue.api.getJob(self.data.parent_id)
