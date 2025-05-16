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

"""Module for classes related to procs."""

import enum

from opencue_proto import host_pb2
from opencue.cuebot import Cuebot
import opencue.wrappers.frame
import opencue.wrappers.host
import opencue.wrappers.job
import opencue.wrappers.layer


class Proc(object):
    """This class contains the grpc implementation related to a Proc.

    A proc is a bookable unit of a host. Hosts may contain many procs; each proc can be assigned
    a different frame to work on."""

    class RedirectType(enum.IntEnum):
        """Represents the type of a proc redirect."""
        JOB_REDIRECT = host_pb2.JOB_REDIRECT
        GROUP_REDIRECT = host_pb2.GROUP_REDIRECT

    class RunState(enum.IntEnum):
        """Represents the current state of a proc."""
        IDLE = host_pb2.IDLE
        BOOKED = host_pb2.BOOKED

    def __init__(self, proc=None):
        self.data = proc
        self.stub = Cuebot.getStub('proc')

    def kill(self):
        """Kills the frame running on this proc."""
        response = self.stub.Kill(host_pb2.ProcKillRequest(proc=self.data), timeout=Cuebot.Timeout)
        return response

    def unbook(self, kill=False):
        """Unbooks the current frame from this proc.

        :type kill: bool
        :param kill: if true, the frame will be immediately killed
        """
        response = self.stub.Unbook(
            host_pb2.ProcUnbookRequest(proc=self.data, kill=kill), timeout=Cuebot.Timeout)
        return response

    def redirectToJob(self, job, kill=False):
        """Unbooks the current frame from this proc and redirects the proc to a specific job.

        :type job: opencue.wrappers.job.Job
        :param job: job which the proc should be booked to
        :type kill: bool
        :param kill: if true, the frame will be immediately killed
        """
        self.stub.RedirectToJob(
            host_pb2.ProcRedirectToJobRequest(proc=self.data, job_id=job.data.id, kill=kill),
            timeout=Cuebot.Timeout)

    def redirectToGroup(self, group, kill=False):
        """Unbooks the current frame from this proc and redirects the proc to another group.

        :type group: opencue.wrappers.group.Group
        :param group: group which the proc should be booked to
        :type kill: bool
        :param kill: if true, the frame will be immediately killed
        """
        self.stub.RedirectToGroup(
            host_pb2.ProcRedirectToGroupRequest(proc=self.data, group_id=group.data.id, kill=kill),
            timeout=Cuebot.Timeout)

    def getHost(self):
        """Returns the host this proc is allocated from.

        :rtype:  opencue.wrappers.host.Host
        :return: the host this proc is allocated from
        """
        response = self.stub.GetHost(host_pb2.ProcGetHostRequest(proc=self.data),
                                     timeout=Cuebot.Timeout)
        return opencue.wrappers.host.Host(response.host)

    def getFrame(self):
        """Returns the frame this proc is running.

        :rtype:  opencue.wrappers.frame.Frame
        :return: the frame this proc is running
        """
        response = self.stub.GetFrame(host_pb2.ProcGetFrameRequest(proc=self.data),
                                      timeout=Cuebot.Timeout)
        return opencue.wrappers.frame.Frame(response.frame)

    def getLayer(self):
        """Returns the layer this proc is running.

        :rtype:  opencue.wrappers.layer.Layer
        :return: the layer this proc is running
        """
        response = self.stub.GetLayer(host_pb2.ProcGetLayerRequest(proc=self.data),
                                      timeout=Cuebot.Timeout)
        return opencue.wrappers.layer.Layer(response.layer)

    def getJob(self):
        """Returns the job this proc is running.

        :rtype:  opencue.wrappers.job.Job
        :return: the job this proc is running
        """
        response = self.stub.GetJob(host_pb2.ProcGetJobRequest(proc=self.data),
                                    timeout=Cuebot.Timeout)
        return opencue.wrappers.job.Job(response.job)

    def id(self):
        """Returns the id of the proc.

        :rtype:  str
        :return: id of the proc
        """
        return self.data.id

    def name(self):
        """Returns the name of the proc.

        :rtype:  str
        :return: name of the proc
        """
        return self.data.name

    def jobName(self):
        """Returns the name of the job of the frame running on the proc.

        :rtype:  str
        :return: name of the current job"""
        return self.data.job_name

    def frameName(self):
        """Returns the name of the frame on the proc.

        :rtype:  str
        :return: name of the current frame
        """
        return self.data.frame_name

    def showName(self):
        """Returns the name of the show of the frame running on the proc.

        :rtype:  str
        :return: name of the current show
        """
        return self.data.show_name

    def coresReserved(self):
        """The number of cores reserved for this frame.

        :rtype:  float
        :return: cores reserved for the running frame
        """
        return self.data.reserved_cores

    def memReserved(self):
        """The amount of memory reserved for the running frame.

        :rtype:  int
        :return: memory reserved for the running frame in kB
        """
        return self.data.reserved_memory

    def memUsed(self):
        """The amount of memory used by the running frame.

        :rtype:  int
        :return: memory used by the running frame in kB
        """
        return self.data.used_memory

    def bookedTime(self):
        """The last time this proc was booked to a job.

        :rtype: int
        :return: last time booked as an epoch
        """
        return self.data.booked_time

    def dispatchTime(self):
        """The last time this proc was dispatched work.

        :rtype: int
        :return: last time dispatched as an epoch
        """
        return self.data.dispatch_time

    def isUnbooked(self):
        """Returns whether this proc is unbooked.

        :rtype: bool
        :return: whether the proc is unbooked
        """
        return self.data.unbooked


class NestedProc(Proc):
    """This class contains information and actions related to a nested job."""

    def __init__(self, nestedProc):
        super(NestedProc, self).__init__(nestedProc)
        # job children are most likely empty but its possible to
        # populate this with NestedLayer objects.
        self.__children = []

    def children(self):
        """Returns children of the proc."""
        return self.__children
