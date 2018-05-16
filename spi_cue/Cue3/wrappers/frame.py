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

Module: frame.py - Cue3 Library implementation of a frame

Created: February 12, 2008

Contact: Middle-Tier Group (middle-tier@imageworks.com)

SVN: $Id$
"""

import cue.CueClientIce as CueClientIce
import cue.CueIce as CueIce
import time

class Frame(CueClientIce.Frame):
    """This class contains the ice implementation related to a frame."""
    def __init__(self):
        """_Frame class initialization"""
        CueClientIce.Frame.__init__(self)

    def eat(self):
        """Eat frame"""
        if self.data.state != CueIce.FrameState.Eaten:
            self.proxy.eat()

    def kill(self):
        """Kill frame"""
        if self.data.state == CueIce.FrameState.Running:
            self.proxy.kill()

    def retry(self):
        """Retry frame"""
        if self.data.state != CueIce.FrameState.Waiting:
            self.proxy.retry()

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this frame
        @rtype:  list<Depend>
        @return: List of dependencies that depend directly on this frame"""
        return self.proxy.getWhatDependsOnThis()

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this frame depends on
        @rtype:  list<Depend>
        @return: List of dependencies that this frame depends on"""
        return self.proxy.getWhatThisDependsOn()

    def createDependencyOnJob(self, job):
        """Create and return a frame on job dependency
        @type  job: Job
        @param job: the job you want this frame to depend on
        @rtype:  Depend
        @return: The new dependency"""
        return self.proxy.createDependencyOnJob(job.proxy)

    def createDependencyOnLayer(self, layer):
        """Create and return a frame on layer dependency
        @type layer: Layer
        @param layer: the layer you want this frame to depend on
        @rtype:  Depend
        @return: The new dependency"""
        return self.proxy.createDependencyOnLayer(layer.proxy)

    def createDependencyOnFrame(self, frame):
        """Create and return a frame on frame dependency
        @type frame: Frame
        @param frame: the frame you want this frame to depend on
        @rtype:  Depend
        @return: The new dependency"""
        return self.proxy.createDependencyOnFrame(frame.proxy)

    def markAsWaiting(self):
        """Mark the frame as waiting, similar to drop depends. The frame will be
        able to run even if the job has an external dependency."""
        self.proxy.markAsWaiting()

    def id(self):
        """Returns the id of the frame
        @rtype:  str
        @return: Frame uuid"""
        return self.proxy.ice_getIdentity().name

    def name(self):
        """Returns the name of the frame
        @rtype:  str
        @return: Frame name"""
        return "%04d-%s" % (self.data.number, self.data.layerName)

    def layer(self):
        """Returns the name of the layer name that the frame belongs to
        @rtype:  str
        @return: Layer name"""
        return self.data.layerName

    def frame(self):
        """Returns the frames number as a padded string
        @rtype:  str
        @return: Frame number string"""
        return "%04d" % self.data.number

    def number(self):
        """Returns the frames number
        @rtype:  int
        @return: Frame number"""
        return self.data.number

    def dispatchOrder(self):
        """Returns the frames dispatch order
        @rtype:  int
        @return: Frame dispatch order"""
        return self.data.dispatchOrder

    def startTime(self):
        """Returns the epoch timestamp of the frame's start time
        @rtype:  int
        @return: Job start time in epoch"""
        return self.data.startTime

    def stopTime(self):
        """Returns the epoch timestamp of the frame's stop time
        @rtype:  int
        @return: Frame stop time in epoch"""
        return self.data.stopTime

    def resource(self):
        """Returns the most recent resource that the frame has started running on.
        Ex: vrack999/1.0 = host/proc:cores
        @rtype:  str
        @return: Most recent running resource"""
        return self.data.lastResource

    def retries(self):
        """Returns the number of retries
        @rtype:  int
        @return: Number of retries"""
        return self.data.retryCount

    def exitStatus(self):
        """Returns the frame's exitStatus
        @rtype:  int
        @return: Frames last exit status"""
        return self.data.exitStatus

    def maxRss(self):
        """Returns the frame's maxRss
        @rtype:  long
        @return: Max RSS in Kb"""
        return self.data.maxRss

    def memUsed(self):
        """Returns the frame's currently used memory
        @rtype:  long
        @return: Current used memory in Kb"""
        return self.data.usedMemory

    def memReserved(self):
        """Returns the frame's currently reserved memory
        @rtype:  long
        @return: Current used memory in Kb"""
        return self.data.reservedMemory

    def state(self): # call it status?
        """Returns the state of the frame
        @rtype:  Cue3.FrameState
        @return: Frame state"""
        return self.data.state

    def runTime(self):
        """Returns the number of seconds that the frame has been (or was) running
        @rtype:  int
        @return: Job runtime in seconds"""
        if self.data.startTime == 0:
            return 0
        if self.data.stopTime == 0:
            return int(time.time() - self.data.startTime)
        else:
            return self.data.stopTime - self.data.startTime

