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
Cue3 layer module

implementation of a layer in cue3
"""
import time

import cue.CueClientIce as CueClientIce
from ..search import *


class Layer(CueClientIce.Layer):
    """This class contains the ice implementation related to a layer."""
    def __init__(self):
        """_Layer class initialization"""
        CueClientIce.Layer.__init__(self)

    def kill(self):
        """Kill entire layer"""
        self.proxy.killFrames()

    def eat(self):
        """Eat entire layer"""
        self.proxy.eatFrames()

    def retry(self):
        """Retry entire layer"""
        self.proxy.retryFrames()

    def markdone(self):
        """Drops any dependency that requires this layer or requires any frame
        in the layer"""
        self.proxy.markdoneFrames()

    def getFrames(self, **options):
        """Returns the list of up to 1000 frames from within the layer.
        @rtype:  list<Frame>
        @return: List of frames"""
        return self.proxy.getFrames(FrameSearch(**options))

    def setTags(self, tags):
        """Sets the tags, TODO: update description of tag structure
        @type  tags: str
        @param tags: Layer tags"""
        self.proxy.setTags(tags)

    def setMinCores(self, cores):
        """Sets the minimum number of cores that this layer requires.
        Use 100 to reserve 1 core.
        @type  cores: int
        @param cores: Core units, 100 reserves 1 core"""
        self.proxy.setMinCores(cores/100.0)

    def setMinMemory(self, memory):
        """Sets the minimum amount of memory that this layer requires. in Kb
        @type  memory: int
        @param memory: Minimum Kb memory reserved by each frame"""
        self.proxy.setMinMemory(memory)

    def getWhatDependsOnThis(self):
        """Gets a list of dependencies that depend directly on this layer
        @rtype:  list<Cue3.depend.Depend>
        @return: List of dependencies that depend directly on this layer"""
        return self.proxy.getWhatDependsOnThis()

    def getWhatThisDependsOn(self):
        """Get a list of dependencies that this layer depends on
        @rtype:  list<Cue3.depend.Depend>
        @return: List of dependences that this layer depends on"""
        return self.proxy.getWhatThisDependsOn()

    def createDependencyOnJob(self, job):
        """Create and return a layer on job dependency
        @type  job: Job
        @param job: the job you want this job to depend on
        @rtype:  Cue3.depend.Depend
        @return: the new dependency"""
        return self.proxy.createDependencyOnJob(job.proxy)

    def createDependencyOnLayer(self, layer):
        """Create and return a layer on layer dependency
        @type  layer: Layer
        @param layer: the layer you want this layer to depend on
        @rtype:  Cue3.depend.Depend
        @return: the new dependency"""
        return self.proxy.createDependencyOnLayer(layer.proxy)

    def createDependencyOnFrame(self, frame):
        """Create and return a layer on frame dependency
        @type  frame: Frame
        @param frame: the frame you want this layer to depend on
        @rtype:  Cue3.depend.Depend
        @return: the new dependency"""
        return self.proxy.createDependencyOnFrame(frame.proxy)

    def createFrameByFrameDependency(self, layer):
        """Create and return a frame by frame frame dependency
        @param layer: the layer you want this layer to depend on
        @type  layer: Layer
        @rtype:  Cue3.depend.Depend
        @return: the new dependency"""
        # anyframe is hard coded right now, this option should be moved
        # to LayerOnLayer for better efficiency.
        return self.proxy.createFrameByFrameDependency(layer.proxy, False)

    def unbookProcs(self, subs, number, kill=False):
        """Unbook procs off layer from specified subscriptions
        @type  subs: list<Subscription>
        @param subs: the subscriptions to unbook from
        @type  number: int
        @param number: the number of virtual procs to unbook
        @type  kill: bool
        @param kill: wheather or not to kill the frames as well"""
        self.proxy.unbookProcs([a.proxy for a in subs], number, kill)

    def reorderFrames(self, range, order):
        """Reorders the specified frame range on this layer.
        @type  range: string
        @param range: The frame range to reorder
        @type  order: Cue3.Order
        @param order: First, Last or Reverse"""
        self.proxy.reorderFrames(range, order)

    def staggerFrames(self, range, stagger):
        """Staggers the specified frame range on this layer.
        @type  range: string
        @param range: The frame range to stagger
        @type  stagger: int
        @param stagger: The amount to stagger by"""
        self.proxy.staggerFrames(range, stagger)

    def id(self):
        """Returns the uuid of the layer
        @rtype:  str
        @return: Layer uuid"""
        return self.proxy.ice_getIdentity().name

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
        return self.data.dispatchOrder

    def coresReserved(self):
        """Returns the number of cores reserved on this layer
        @rtype: float
        @return: cores reserved"""
        return self.stats.reservedCores

    def minCores(self):
        """Returns the minimum number of cores that frames in this layer require
        @rtype:  int
        @return: Minimum number of cores required"""
        return self.data.minCores

    def minMemory(self):
        """Returns the minimum about of memory that frames in this layer require
        @rtype:  int
        @return: Minimum Kb memory required by frames in this layer"""
        return self.data.minMemory

    def maxRss(self):
        """Returns the highest amount of memory that any frame in this layer
        used in kB. Value is within 5% of the actual highest frame.
        @rtype:  long
        @return: Most memory used by any frame in this layer in kB"""
        return self.stats.maxRss

    def type(self):
        """Returns the type of layer. Ex: Pre, Post, Render
        @rtype:  Cue3.LayerType
        @return: Type of layer"""
        return self.data.type

    def totalFrames(self):
        """Returns the total number of frames under this object
        @rtype:  int
        @return: Total number of frames"""
        return self.stats.totalFrames

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

    def percentCompleted(self):
        """Returns the percent that the object's frames are completed
        @rtype:  float
        @return: Percentage of frame completion"""
        try:
            return self.stats.succeededFrames / float(self.stats.totalFrames) * 100.0
        except:
            return 0

    def avgFrameTimeSeconds(self):
        """Returns the average frame completion time in seconds
        @rtype:  int
        @return: Average frame completion time in seconds"""
        return self.stats.avgFrameSec;

    def avgCoreSeconds(self):
        """Returns the average core time used in seconds
        @rtype:  int
        @return: Average core time in seconds"""
        return self.stats.avgCoreSec

    def coreSecondsRemaining(self):
        """Returns the estimated core time that is remnainining to complete
        all waiting frames.
        @rtype:  int
        @return: the number of seconds of estimated core time remaining"""
        return self.stats.remainingCoreSec


