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

Module: frame.py - opencue Library implementation of a frame
"""


import enum
import time

from opencue import Cuebot
from opencue.compiled_proto import job_pb2
import opencue.wrappers.depend


class Frame(object):
    """This class contains the grpc implementation related to a Frame."""

    class CheckpointState(enum.IntEnum):
        DISABLED = job_pb2.DISABLED
        ENABLED = job_pb2.ENABLED
        COPYING = job_pb2.COPYING
        COMPLETE = job_pb2.COMPLETE

    class FrameExitStatus(enum.IntEnum):
        SUCCESS = job_pb2.SUCCESS
        NO_RETRY = job_pb2.NO_RETRY
        SKIP_RETRY = job_pb2.SKIP_RETRY

    class FrameState(enum.IntEnum):
        WAITING = job_pb2.WAITING
        SETUP = job_pb2.SETUP
        RUNNING = job_pb2.RUNNING
        SUCCEEDED = job_pb2.SUCCEEDED
        DEPEND = job_pb2.DEPEND
        DEAD = job_pb2.DEAD
        EATEN = job_pb2.EATEN
        CHECKPOINT = job_pb2.CHECKPOINT

    def __init__(self, frame=None):
        """_Frame class initialization"""
        self.data = frame
        self.stub = Cuebot.getStub('frame')

    def eat(self):
        """Eat frame"""
        if self.data.state != job_pb2.FrameState.Value('EATEN'):
            self.stub.Eat(job_pb2.FrameEatRequest(frame=self.data), timeout=Cuebot.Timeout)

    def kill(self):
        """Kill frame"""
        if self.data.state == job_pb2.FrameState.Value('RUNNING'):
            self.stub.Kill(job_pb2.FrameKillRequest(frame=self.data), timeout=Cuebot.Timeout)

    def retry(self):
        """Retry frame"""
        if self.data.state != job_pb2.FrameState.Value('WAITING'):
            self.stub.Retry(job_pb2.FrameRetryRequest(frame=self.data), timeout=Cuebot.Timeout)

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this frame.

        :rtype:  list<Depend>
        :return: List of dependencies that depend directly on this frame"""
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.FrameGetWhatDependsOnThisRequest(frame=self.data),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.depend.Depend(dep) for dep in response.depends.depends]

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this frame depends on.

        :rtype:  list<Depend>
        :return: List of dependencies that this frame depends on"""
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.FrameGetWhatThisDependsOnRequest(frame=self.data),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.depend.Depend(dep) for dep in response.depends.depends]

    def createDependencyOnJob(self, job):
        """Create and return a frame on job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this frame to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency"""
        response = self.stub.CreateDependencyOnJob(
            job_pb2.FrameCreateDependencyOnJobRequest(frame=self.data, job=job.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Create and return a frame on layer dependency.

        :type layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this frame to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency"""
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.FrameCreateDependencyOnLayerRequest(frame=self.data, layer=layer.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Create and return a frame on frame dependency.

        :type frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this frame to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency"""
        response = self.stub.CreateDependencyOnFrame(
            job_pb2.FrameCreateDependencyOnFrameRequest(frame=self.data,
                                                        depend_on_frame=frame.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def markAsWaiting(self):
        """Mark the frame as waiting, similar to drop depends. The frame will be
        able to run even if the job has an external dependency."""
        self.stub.MarkAsWaiting(
            job_pb2.FrameMarkAsWaitingRequest(frame=self.data),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the frame.
        :rtype:  str
        :return: Frame uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the frame.
        :rtype:  str
        :return: Frame name"""
        return "%04d-%s" % (self.data.number, self.data.layer_name)

    def layer(self):
        """Returns the name of the layer name that the frame belongs to.

        :rtype:  str
        :return: Layer name"""
        return self.data.layer_name

    def frame(self):
        """Returns the frames number as a padded string.

        :rtype:  str
        :return: Frame number string"""
        return "%04d" % self.data.number

    def number(self):
        """Returns the frames number.

        :rtype:  int
        :return: Frame number"""
        return self.data.number

    def dispatchOrder(self):
        """Returns the frames dispatch order.

        :rtype:  int
        :return: Frame dispatch order"""
        return self.data.dispatch_order

    def startTime(self):
        """Returns the epoch timestamp of the frame's start time.

        :rtype:  int
        :return: Job start time in epoch"""
        return self.data.start_time

    def stopTime(self):
        """Returns the epoch timestamp of the frame's stop time.

        :rtype:  int
        :return: Frame stop time in epoch"""
        return self.data.stop_time

    def resource(self):
        """Returns the most recent resource that the frame has started running on.
        Ex: vrack999/1.0 = host/proc:cores

        :rtype:  str
        :return: Most recent running resource"""
        return self.data.last_resource

    def retries(self):
        """Returns the number of retries.

        :rtype:  int
        :return: Number of retries"""
        return self.data.retry_count

    def exitStatus(self):
        """Returns the frame's exitStatus.

        :rtype:  int
        :return: Frames last exit status"""
        return self.data.exit_status

    def maxRss(self):
        """Returns the frame's maxRss.

        :rtype:  long
        :return: Max RSS in Kb"""
        return self.data.max_rss

    def memUsed(self):
        """Returns the frame's currently used memory.

        :rtype:  long
        :return: Current used memory in Kb"""
        return self.data.used_memory

    def memReserved(self):
        """Returns the frame's currently reserved memory.

        :rtype:  long
        :return: Current used memory in Kb"""
        return self.data.reserved_memory

    def state(self): # call it status?
        """Returns the state of the frame.

        :rtype:  opencue.FrameState
        :return: Frame state"""
        return self.data.state

    def runTime(self):
        """Returns the number of seconds that the frame has been (or was) running.

        :rtype:  int
        :return: Job runtime in seconds"""
        if self.data.start_time == 0:
            return 0
        if self.data.stop_time == 0:
            return int(time.time() - self.data.start_time)
        else:
            return self.data.stop_time - self.data.start_time

