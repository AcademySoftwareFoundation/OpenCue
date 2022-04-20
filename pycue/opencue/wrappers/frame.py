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

"""Module for classes related to frames."""

import enum
import time
import os

from opencue import Cuebot
from opencue.compiled_proto import job_pb2
import opencue.wrappers.depend


class Frame(object):
    """This class contains the grpc implementation related to a Frame."""

    class CheckpointState(enum.IntEnum):
        """Possible states for a frame's checkpointing status, if it uses that."""
        DISABLED = job_pb2.DISABLED
        ENABLED = job_pb2.ENABLED
        COPYING = job_pb2.COPYING
        COMPLETE = job_pb2.COMPLETE

    class FrameExitStatus(enum.IntEnum):
        """Possible frame exit statuses."""
        SUCCESS = job_pb2.SUCCESS
        NO_RETRY = job_pb2.NO_RETRY
        SKIP_RETRY = job_pb2.SKIP_RETRY

    class FrameState(enum.IntEnum):
        """Possible frame states."""
        WAITING = job_pb2.WAITING
        SETUP = job_pb2.SETUP
        RUNNING = job_pb2.RUNNING
        SUCCEEDED = job_pb2.SUCCEEDED
        DEPEND = job_pb2.DEPEND
        DEAD = job_pb2.DEAD
        EATEN = job_pb2.EATEN
        CHECKPOINT = job_pb2.CHECKPOINT

    def __init__(self, frame=None):
        self.data = frame
        self.stub = Cuebot.getStub('frame')

    def eat(self):
        """Eats the frame."""
        if self.data.state != job_pb2.FrameState.Value('EATEN'):
            self.stub.Eat(job_pb2.FrameEatRequest(frame=self.data), timeout=Cuebot.Timeout)

    def kill(self):
        """Kills the frame."""
        if self.data.state == job_pb2.FrameState.Value('RUNNING'):
            self.stub.Kill(job_pb2.FrameKillRequest(frame=self.data), timeout=Cuebot.Timeout)

    def retry(self):
        """Retries the frame."""
        if self.data.state != job_pb2.FrameState.Value('WAITING'):
            self.stub.Retry(job_pb2.FrameRetryRequest(frame=self.data), timeout=Cuebot.Timeout)

    def addRenderPartition(self, hostname, threads, max_cores, num_mem, max_gpu):
        """Adds a render partition to the frame.

        :type  hostname: str
        :param hostname: hostname of the partition
        :type  threads: int
        :param threads: number of threads of the partition
        :type  max_cores: int
        :param max_cores: max cores enabled for the partition
        :type  num_mem: int
        :param num_mem: amount of memory reserved for the partition
        :type  max_gpu: int
        :param max_gpu: max gpu cores enabled for the partition
        """
        self.stub.AddRenderPartition(
            job_pb2.FrameAddRenderPartitionRequest(
                frame=self.data,
                host=hostname,
                threads=threads,
                max_cores=max_cores,
                max_memory=num_mem,
                max_gpu=max_gpu,
                username=os.getenv("USER", "unknown")))

    def getWhatDependsOnThis(self):
        """Returns a list of dependencies that depend directly on this frame.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: list of dependencies that depend directly on this frame
        """
        response = self.stub.GetWhatDependsOnThis(
            job_pb2.FrameGetWhatDependsOnThisRequest(frame=self.data),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.depend.Depend(dep) for dep in response.depends.depends]

    def getWhatThisDependsOn(self):
        """Returns a list of dependencies that this frame depends on.

        :rtype:  list<opencue.wrappers.depend.Depend>
        :return: list of dependencies that this frame depends on
        """
        response = self.stub.GetWhatThisDependsOn(
            job_pb2.FrameGetWhatThisDependsOnRequest(frame=self.data),
            timeout=Cuebot.Timeout)
        return [opencue.wrappers.depend.Depend(dep) for dep in response.depends.depends]

    def createDependencyOnJob(self, job):
        """Creates and returns a frame-on-job dependency.

        :type  job: opencue.wrappers.job.Job
        :param job: the job you want this frame to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: The new dependency
        """
        response = self.stub.CreateDependencyOnJob(
            job_pb2.FrameCreateDependencyOnJobRequest(frame=self.data, job=job.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnLayer(self, layer):
        """Creates and returns a frame-on-layer dependency.

        :type  layer: opencue.wrappers.layer.Layer
        :param layer: the layer you want this frame to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnLayer(
            job_pb2.FrameCreateDependencyOnLayerRequest(frame=self.data, layer=layer.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def createDependencyOnFrame(self, frame):
        """Creates and returns a frame-on-frame dependency.

        :type  frame: opencue.wrappers.frame.Frame
        :param frame: the frame you want this frame to depend on
        :rtype:  opencue.wrappers.depend.Depend
        :return: the new dependency
        """
        response = self.stub.CreateDependencyOnFrame(
            job_pb2.FrameCreateDependencyOnFrameRequest(frame=self.data,
                                                        depend_on_frame=frame.data),
            timeout=Cuebot.Timeout)
        return opencue.wrappers.depend.Depend(response.depend)

    def dropDepends(self, target):
        """Drops every dependency that is causing this frame not to run."""
        self.stub.DropDepends(
            job_pb2.FrameDropDependsRequest(frame=self.data, target=target),
            timeout=Cuebot.Timeout)

    def markAsWaiting(self):
        """Marks the frame as waiting; ready to run.

        Similar to dropDepends. The frame will be able to run even if the job has an external
        dependency."""
        self.stub.MarkAsWaiting(
            job_pb2.FrameMarkAsWaitingRequest(frame=self.data),
            timeout=Cuebot.Timeout)

    def setCheckpointState(self, checkPointState):
        """Sets the checkPointState of the frame.

        :type  checkPointState: job_pb.CheckpointState
        :param checkPointState: the checkpoint state of the frame
        """
        self.stub.SetCheckpointState(
            job_pb2.FrameSetCheckpointStateRequest(frame=self.data, state=checkPointState))

    def id(self):
        """Returns the id of the frame.

        :rtype:  str
        :return: id of the frame
        """
        return self.data.id

    def name(self):
        """Returns the name of the frame.

        :rtype:  str
        :return: name of the frame
        """
        return "%04d-%s" % (self.data.number, self.data.layer_name)

    def layer(self):
        """Returns the name of the layer name that the frame belongs to.

        :rtype:  str
        :return: name of the layer
        """
        return self.data.layer_name

    def frame(self):
        """Returns the frame number as a padded string.

        :rtype:  str
        :return: frame number padded to 4 digits
        """
        return "%04d" % self.data.number

    def number(self):
        """Returns the frame number, unpadded.

        :rtype:  int
        :return: frame number
        """
        return self.data.number

    def dispatchOrder(self):
        """Returns the frame's dispatch order.

        :rtype:  int
        :return: frame dispatch order
        """
        return self.data.dispatch_order

    def startTime(self):
        """Returns the epoch timestamp of the frame's start time.

        :rtype:  int
        :return: frame start time as an epoch
        """
        return self.data.start_time

    def stopTime(self):
        """Returns the epoch timestamp of the frame's stop time.

        :rtype:  int
        :return: frame stop time as an epoch
        """
        return self.data.stop_time

    def resource(self):
        """Returns the most recent resource that the frame has started running on.

        Ex: vrack999/1.0 = host/proc:cores

        :rtype:  str
        :return: most recent running resource
        """
        return self.data.last_resource

    def retries(self):
        """Returns the number of times the frame has been retried.

        :rtype:  int
        :return: number of retries
        """
        return self.data.retry_count

    def exitStatus(self):
        """Returns the frame's exit status.

        :rtype:  int
        :return: last exit status of the frame
        """
        return self.data.exit_status

    def maxRss(self):
        """Returns the frame's maxRss.

        :rtype:  long
        :return: max RSS in Kb
        """
        return self.data.max_rss

    def memUsed(self):
        """Returns the frame's currently used memory.

        :rtype:  long
        :return: currently used memory in Kb
        """
        return self.data.used_memory

    def memReserved(self):
        """Returns the frame's currently reserved memory.

        :rtype:  long
        :return: currently reserved memory in Kb
        """
        return self.data.reserved_memory

    def state(self): # call it status?
        """Returns the state of the frame.

        :rtype:  job_pb2.FrameState
        :return: state of the frame
        """
        return self.data.state

    def runTime(self):
        """Returns the number of seconds that the frame has been (or was) running.

        :rtype:  int
        :return: frame runtime in seconds
        """
        if self.data.start_time == 0:
            return 0
        if self.data.stop_time == 0:
            return int(time.time() - self.data.start_time)
        return self.data.stop_time - self.data.start_time
