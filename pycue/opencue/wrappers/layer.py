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
opencue layer module

implementation of a layer in opencue
"""

import depend
from opencue.compiled_proto import job_pb2
from opencue.cuebot import Cuebot
from ..search import FrameSearch


class Layer(object):
    def __init__(self, layer):
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

    def enableMemoryOptimizer(self, value):
        """Set enableMemoryOptimizer to the value.
        @type value: bool
        @param value: boolean to enable/disable memory optimizer"""
        return self.stub.EnableMemoryOptimizer(job_pb2.LayerEnableMemoryOptimizerRequest(
            layer=self.data, value=value),
            timeout=Cuebot.Timeout)

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the layer.
        @rtype:  list<Frame>
        @return: Sequence of Frame obejcts"""
        criteria = FrameSearch.criteriaFromOptions(**options)
        response = self.stub.GetFrames(job_pb2.LayerGetFramesRequest(layer=self.data, r=criteria),
                                       timeout=Cuebot.Timeout)
        return [frame.Frame(frame) for frame in response.frames]

    def getOutputPaths(self):
        """Return the output paths for this layer.
        @rtype: list<String>
        @return: list of output paths"""
        return self.stub.GetOutputPaths(job_pb2.LayerGetOutputPathsRequest(layer=self.data),
                                        timeout=Cuebot.Timeout)

    def setTags(self, tags):
        """Sets the tags, TODO: update description of tag structure
        @type  tags: str
        @param tags: Layer tags"""
        return self.stub.SetTags(job_pb2.LayerSetTagsRequest(layer=self.data, tags=tags),
                                 timeout=Cuebot.Timeout)

    def setMaxCores(self, cores):
        """Sets the maximum number of cores that this layer requires.
        @type  cores: float
        @param cores: Core units, 100 reserves 1 core"""
        return self.stub.SetMaxCores(
            job_pb2.LayerSetMaxCoresRequest(layer=self.data, cores=cores/100.0),
            timeout=Cuebot.Timeout)

    def setMinCores(self, cores):
        """Sets the minimum number of cores that this layer requires.
        Use 100 to reserve 1 core.
        @type  cores: int
        @param cores: Core units, 100 reserves 1 core"""
        return self.stub.SetMinCores(
            job_pb2.LayerSetMinCoresRequest(layer=self.data, cores=cores/100.0),
            timeout=Cuebot.Timeout)

    def setMinGpu(self, gpu):
        """Sets the minimum number of gpu memory that this layer requires.
        @type  gpu: int
        @param gpu: gpu value"""
        return self.stub.SetMinGpu(
            job_pb2.LayerSetMinGpuRequest(layer=self.data, gpu=gpu),
            timeout=Cuebot.Timeout)

    def setMinMemory(self, memory):
        """Sets the minimum amount of memory that this layer requires. in Kb
        @type  memory: int
        @param memory: Minimum Kb memory reserved by each frame"""
        return self.stub.SetMinMemory(
            job_pb2.LayerSetMinMemoryRequest(layer=self.data, memory=memory),
            timeout=Cuebot.Timeout)

    def setThreadable(self, threadable):
        """Set enableMemoryOptimizer to the value.
        @type threadable: bool
        @param threadable: boolean to enable/disable threadable"""
        return self.stub.SetThreadable(job_pb2.LayerSetThreadableRequest(
            layer=self.data, threadable=threadable),
            timeout=Cuebot.Timeout)

    def getWhatDependsOnThis(self):
        """Gets a list of dependencies that depend directly on this layer
        @rtype:  list<opencue.depend.Depend>
        @return: List of dependencies that depend directly on this layer"""
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.LayerGetWhatDependsOnThisRequest(layer=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [depend.Depend(depend) for depend in dependSeq.depends]

    def getWhatThisDependsOn(self):
        """Get a list of dependencies that this layer depends on
        @rtype:  list<opencue.depend.Depend>
        @return: List of dependences that this layer depends on"""
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.LayerGetWhatThisDependsOnRequest(layer=self.data),
            timeout=Cuebot.Timeout)
        dependSeq = response.depends
        return [depend.Depend(depend) for depend in dependSeq.depends]

    def createDependencyOnJob(self, job):
        """Create and return a layer on job dependency
        @type  job: Job
        @param job: the job you want this job to depend on
        @rtype:  opencue.depend.Depend
        @return: the new dependency"""
        response = self.stub.CreateDependOnJob(
            job_pb2.LayerCreateDependOnJobRequest(layer=self.data, job=job),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Create and return a layer on layer dependency
        @type  layer: Layer
        @param layer: the layer you want this layer to depend on
        @rtype:  opencue.depend.Depend
        @return: the new dependency"""
        response = self.stub.CreateDependOnLayer(
            job_pb2.LayerCreateDependOnLayerRequest(layer=self.data, depend_on_layer=layer),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Create and return a layer on frame dependency
        @type  frame: Frame
        @param frame: the frame you want this layer to depend on
        @rtype:  opencue.depend.Depend
        @return: the new dependency"""
        response = self.stub.CreateDependOnFrame(
            job_pb2.LayerCreateDependOnFrameRequest(layer=self.data, frame=frame),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    def createFrameByFrameDependency(self, layer):
        """Create and return a frame by frame frame dependency
        @param layer: the layer you want this layer to depend on
        @type  layer: Layer
        @rtype:  opencue.depend.Depend
        @return: the new dependency"""
        # anyframe is hard coded right now, this option should be moved
        # to LayerOnLayer for better efficiency.
        response = self.stub.CreateFrameByFrameDepend(
            job_pb2.LayerCreateFrameByFrameDependRequest(
                layer=self.data, depend_layer=layer, any_frame=False),
            timeout=Cuebot.Timeout)
        return depend.Depend(response.depend)

    # TODO(gregdenton) Determine if this is needed. (Issue #71)
    # def unbookProcs(self, subs, number, kill=False):
    #     """Unbook procs off layer from specified subscriptions
    #     @type  subs: list<Subscription>
    #     @param subs: the subscriptions to unbook from
    #     @type  number: int
    #     @param number: the number of virtual procs to unbook
    #     @type  kill: bool
    #     @param kill: wheather or not to kill the frames as well"""
    #     self.proxy.unbookProcs([a.proxy for a in subs], number, kill)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this layer.
        @type  range: string
        @param range: The frame range to reorder
        @type  order: opencue.Order
        @param order: First, Last or Reverse"""
        self.stub.ReorderFrames(
            job_pb2.LayerReorderFramesRequest(layer=self.data, range=range, order=order),
            timeout=Cuebot.Timeout)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this layer.
        @type  range: string
        @param range: The frame range to stagger
        @type  stagger: int
        @param stagger: The amount to stagger by"""
        self.stub.StaggerFrames(
            job_pb2.LayerStaggerFramesRequest(layer=self.data, range=range, stagger=stagger),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the uuid of the layer
        @rtype:  str
        @return: Layer uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the layer
        @rtype:  str
        @return: Layer name"""
        return self.data.name

    def range(self):
        """Returns the frame range for the layer
        @rtype:  str
        @return: Layer frame range"""
        return self.data.range

    def tags(self):
        """Returns the tags applied to the layer
        TODO: Document syntax
        @rtype:  str
        @return: Layer tags"""
        return self.data.tags

    def dispatchOrder(self):
        """Returns the layers dispatch order
        @rtype:  int
        @return: Layer dispatch order"""
        return self.data.dispatch_order

    def coresReserved(self):
        """Returns the number of cores reserved on this layer
        @rtype: float
        @return: cores reserved"""
        return self.data.layer_stats.reserved_cores

    def minCores(self):
        """Returns the minimum number of cores that frames in this layer require
        @rtype:  int
        @return: Minimum number of cores required"""
        return self.data.min_cores

    def minMemory(self):
        """Returns the minimum about of memory that frames in this layer require
        @rtype:  int
        @return: Minimum Kb memory required by frames in this layer"""
        return self.data.min_memory

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this layer
        used in kB. Value is within 5% of the actual highest frame.
        @rtype:  long
        @return: Most memory used by any frame in this layer in kB"""
        return self.data.layer_stats.max_rss

    def type(self):
        """Returns the type of layer. Ex: Pre, Post, Render
        @rtype:  opencue.LayerType
        @return: Type of layer"""
        return self.data.type

    def totalFrames(self):
        """Returns the total number of frames under this object
        @rtype:  int
        @return: Total number of frames"""
        return self.data.layer_stats.total_frames

    def dependFrames(self):
        """Returns the total number of dependent frames under this object
        @rtype:  int
        @return: Total number of dependent frames"""
        return self.data.layer_stats.depend_frames

    def succeededFrames(self):
        """Returns the total number of succeeded frames under this object
        @rtype:  int
        @return: Total number of succeeded frames"""
        return self.data.layer_stats.succeeded_frames

    def runningFrames(self):
        """Returns the total number of running frames under this object
        @rtype:  int
        @return: Total number of running frames"""
        return self.data.layer_stats.running_frames

    def deadFrames(self):
        """Returns the total number of deads frames under this object
        @rtype:  int
        @return: Total number of dead frames"""
        return self.data.layer_stats.dead_frames

    def waitingFrames(self):
        """Returns the total number of waiting frames under this object
        @rtype:  int
        @return: Total number of waiting frames"""
        return self.data.layer_stats.waiting_frames

    def eatenFrames(self):
        """Returns the total number of eaten frames under this object
        @rtype:  int
        @return: Total number of eaten frames"""
        return self.data.layer_stats.eaten_frames

    def pendingFrames(self):
        """Returns the total number of pending (dependent and waiting) frames
        under this object.
        @rtype:  int
        @return: Total number of pending (dependent and waiting) frames"""
        return self.data.layer_stats.pending_frames

    def percentCompleted(self):
        """Returns the percent that the object's frames are completed
        @rtype:  float
        @return: Percentage of frame completion"""
        try:
            return self.data.layer_stats.succeeded_frames / \
                   float(self.data.layer_stats.total_frames) * 100.0
        except:
            return 0

    def avgFrameTimeSeconds(self):
        """Returns the average frame completion time in seconds
        @rtype:  int
        @return: Average frame completion time in seconds"""
        return self.data.layer_stats.avg_frame_sec

    def avgCoreSeconds(self):
        """Returns the average core time used in seconds
        @rtype:  int
        @return: Average core time in seconds"""
        return self.data.layer_stats.avg_core_sec

    def coreSecondsRemaining(self):
        """Returns the estimated core time that is remnainining to complete
        all waiting frames.
        @rtype:  int
        @return: the number of seconds of estimated core time remaining"""
        return self.data.layer_stats.remaining_core_sec
