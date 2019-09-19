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

Module: proc.py - opencue Library implementation of a proc

"""

import enum

from opencue.compiled_proto import host_pb2
from opencue.cuebot import Cuebot
import opencue.wrappers.frame
import opencue.wrappers.host
import opencue.wrappers.job
import opencue.wrappers.layer


class Proc(object):

    class RedirectType(enum.IntEnum):
        JOB_REDIRECT = host_pb2.JOB_REDIRECT
        GROUP_REDIRECT = host_pb2.GROUP_REDIRECT

    class RunState(enum.IntEnum):
        IDLE = host_pb2.IDLE
        BOOKED = host_pb2.BOOKED

    def __init__(self, proc=None):
        self.data = proc
        self.stub = Cuebot.getStub('proc')

    def kill(self):
        """Kill the frame running on this proc"""
        response = self.stub.Kill(host_pb2.ProcKillRequest(proc=self.data), timeout=Cuebot.Timeout)
        return response

    def unbook(self, kill=False):
        """Unbook the current frame.  If the value of kill is true, 
           the frame will be immediately killed.
        """
        response = self.stub.Unbook(host_pb2.ProcUnbookRequest(proc=self.data, kill=kill),
                                    timeout=Cuebot.Timeout)
        return response

    def getHost(self):
        """Return the host this proc is allocated from.
        @rtype:  opencue.wrappers.host.Host
        @return: The host this proc is allocated from."""
        response = self.stub.GetHost(host_pb2.ProcGetHostRequest(proc=self.data),
                                     timeout=Cuebot.Timeout)
        return opencue.wrappers.host.Host(response.host)

    def getFrame(self):
        """Return the frame this proc is running.
        @rtype:  opencue.wrappers.frame.Frame
        @return: The fame this proc is running."""
        response = self.stub.GetFrame(host_pb2.ProcGetFrameRequest(proc=self.data),
                                      timeout=Cuebot.Timeout)
        return opencue.wrappers.frame.Frame(response.frame)

    def getLayer(self):
        """Return the layer this proc is running.
        @rtype:  opencue.wrappers.layer.Layer
        @return: The layer this proc is running."""
        response = self.stub.GetLayer(host_pb2.ProcGetLayerRequest(proc=self.data),
                                      timeout=Cuebot.Timeout)
        return opencue.wrappers.layer.Layer(response.layer)

    def getJob(self):
        """Return the job this proc is running.
        @rtype:  opencue.wrappers.job.Job
        @return: The job this proc is running."""
        response = self.stub.GetJob(host_pb2.ProcGetJobRequest(proc=self.data),
                                    timeout=Cuebot.Timeout)
        return opencue.wrappers.job.Job(response.job)

    def id(self):
        """Returns the id of the proc
        @rtype:  str
        @return: Proc uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the proc
        @rtype:  str
        @return: Proc name"""
        return self.data.name

    def jobName(self):
        """Returns the job name of the frame running on the proc
        @rtype:  str
        @return: Job name"""
        return self.data.job_name

    def frameName(self):
        """Returns the name of the frame on the proc
        @rtype:  str
        @return: Frame name"""
        return self.data.frame_name

    def showName(self):
        """Returns the name of the show whos frame is running on the proc
        @rtype:  str
        @return: Frames show name"""
        return self.data.show_name

    def coresReserved(self):
        """The number of cores reserved for this frame
        @rtype:  float
        @return: Cores reserved for the running frame"""
        return self.data.reserved_cores

    def memReserved(self):
        """The amount of memory reserved for the running frame
        @rtype:  int
        @return: Kb memory reserved for the running frame"""
        return self.data.reserved_memory

    def memUsed(self):
        """The amount of memory used by the running frame
        @rtype:  int
        @return: Kb memory used by the running frame"""
        return self.data.used_memory
     
    def bookedTime(self):
        """The last time this proc was assigned to a job in epoch seconds.
        @rtype: int"""
        return self.data.booked_time

    def dispatchTime(self):
        """The last time this proc was assigned to a job in epoch seconds.
        @rtype: int"""
        return self.data.dispatch_time
    
    def isUnbooked(self):
        """Returns true if this proc is unbooked
        @rtype: boolean"""
        return self.data.unbooked


class NestedProc(Proc):
    """This class contains information and actions related to a nested job."""
    def __init__(self, nestedProc):
        super(NestedProc, self).__init__(nestedProc)
        ## job children are most likely empty but its possible to
        ## populate this with NestedLayer objects.
        self.__children = []

    def children(self):
        return self.__children
