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

Module: host.py - Cue3 Library implementation of a host

"""

import os
import time

import comment
import proc
from Cue3 import Cuebot
from Cue3.compiled_proto import comment_pb2
from Cue3.compiled_proto import host_pb2


class Host(object):
    def __init__(self, host):
        """Host class initialization"""
        self.data = host
        self.__id = host.id
        self.stub = Cuebot.getStub('host')

    def lock(self):
        """Locks the host so that it no longer accepts new frames"""
        self.stub.Lock(host_pb2.HostLockRequest(host=self.data), timeout=Cuebot.Timeout)

    def unlock(self):
        """Unlocks the host and cancels any actions that were waiting for all
        running frames to finish."""
        self.stub.Unlock(host_pb2.HostUnlockRequest(host=self.data), timeout=Cuebot.Timeout)

    def delete(self):
        """Delete the host from the cuebot"""
        self.stub.Delete(host_pb2.HostDeleteRequest(host=self.data), timeout=Cuebot.Timeout)

    def getProcs(self):
        """Returns a list of procs under this host.
        @rtype:  list<Proc>
        @return: A list of procs under this host"""
        response = self.stub.GetProcs(host_pb2.HostGetProcsRequest(host=self.data),
                                      timeout=Cuebot.Timeout)
        return [proc.Proc(p) for p in response.procs]

    def rebootWhenIdle(self):
        """Causes the host to no longer accept new frames and
        when the machine is idle it will reboot."""
        self.stub.RebootWhenIdle(host_pb2.HostRebootWhenIdleRequest(host=self.data),
                                 timeout=Cuebot.Timeout)

    def reboot(self):
        """Causes the host to kill all running frames and reboot the machine."""
        self.stub.Reboot(host_pb2.HostRebootRequest(host=self.data), timeout=Cuebot.Timeout)

    def addTags(self, tags):
        """Adds tags to a host
        @type  tags: list<str>
        @param tags: The tags to add"""
        self.stub.AddTags(host_pb2.HostAddTagsRequest(host=self.data, tags=tags),
                          timeout=Cuebot.Timeout)

    def removeTags(self, tags):
        """Remove tags from this host
        @type  tags: list<str>
        @param tags: The tags to remove"""
        self.stub.RemoveTags(host_pb2.HostRemoveTagsRequest(host=self.data, tags=tags),
                             timeout=Cuebot.Timeout)

    def renameTag(self, oldTag, newTag):
        """Renames a tag
        @type  oldTag: str
        @param oldTag: The old tag to rename
        @type  newTag: str
        @param newTag: The new name for the tag"""
        self.stub.RenameTag(
            host_pb2.HostRenameTagRequest(host=self.data, old_tag=oldTag, new_tag=newTag),
            timeout=Cuebot.Timeout)

    def setAllocation(self, allocation):
        """Sets the host to the given allocation
        @type  allocation: Allocation
        @param allocation: An allocation object"""
        self.stub.SetAllocation(
            host_pb2.HostSetAllocationRequest(host=self.data, allocation_name=allocation.id),
            timeout=Cuebot.Timeout)

    def addComment(self, subject, message):
        """Appends a comment to the hosts's comment list
        @type  subject: str
        @param subject: Subject data
        @type  message: str
        @param message: Message data"""
        comment = comment_pb2.Comment(
            user=os.getenv("USER", "unknown"),
            subject=subject,
            message=message or " ",
            timestamp=0
        )
        self.stub.AddComment(host_pb2.HostAddCommentRequest(host=self.data, new_comment=comment),
                             timeout=Cuebot.Timeout)

    def getComments(self):
        """returns the hosts comments"""
        response = self.stub.GetComments(host_pb2.HostGetCommentsRequest(host=self.data),
                                         timeout=Cuebot.Timeout)
        return [comment.Comment(c) for c in response.comments]

    def id(self):
        """Returns the id of the host
        @rtype:  str
        @return: Host uuid"""
        if not hasattr(self, "__id"):
            self.__id = self.data.id
        return self.__id

    def name(self):
        """Returns the name of the host
        @rtype:  str
        @return: Host name"""
        return self.data.name

    def isNimbyEnabled(self):
        """Returns true if nimby is enabled
        @rtype:  bool
        @return: True if nimby is enabled"""
        return self.data.nimby_enabled

    def isUp(self):
        """Returns True if the host is up
        @rtype:  bool
        @return: True if the host is up"""
        return self.data.state == host_pb2.HardwareState.Value('UP')

    def isLocked(self):
        """Returns True if the host is locked
        @rtype:  bool
        @return: True if the host is locked"""
        return self.data.lock_state == host_pb2.LockState.Value('LOCKED')

    def isCommented(self):
        """Returns true if the host has a comment
        @rtype:  bool
        @return: If the job has a comment"""
        return self.data.has_comment

    def cores(self):
        """
        @rtype:  float
        @return: """
        return self.data.cores

    def coresReserved(self):
        """
        @rtype:  float
        @return: """
        return self.data.cores - self.data.idle_ores

    def coresIdle(self):
        """
        @rtype:  float
        @return: """
        return self.data.idle_cores

    def mem(self):
        """
        @rtype:  int
        @return: """
        return self.data.memory

    def memReserved(self):
        """
        @rtype:  int
        @return: """
        return self.data.memory - self.data.idle_memory

    def memIdle(self):
        """
        @rtype:  int
        @return: """
        return self.data.idle_memory

    def memUsed(self):
        """
        @rtype:  int
        @return: """
        return self.data.total_memory - self.data.free_memory

    def memTotal(self):
        """
        @rtype:  int
        @return: """
        return self.data.total_memory

    def memFree(self):
        """
        @rtype:  int
        @return: """
        return self.data.free_memory

    def swapUsed(self):
        """
        @rtype:  int
        @return: """
        return self.data.total_swap - self.data.free_swap

    def swapTotal(self):
        """
        @rtype:  int
        @return: """
        return self.data.total_swap

    def swapFree(self):
        """
        @rtype:  int
        @return: """
        return self.data.free_swap

    def mcpUsed(self):
        """
        @rtype:  int
        @return: """
        return self.mcpTotal() - self.mcpFree()

    def mcpTotal(self):
        """
        @rtype:  int
        @return: """
        return self.data.total_mcp

    def mcpFree(self):
        """
        @rtype:  int
        @return: """
        return self.data.free_mcp

    def load(self):
        """Returns the load on the host
        @rtype:  int
        @return: Host load average * 100"""
        return self.data.load

    def bootTime(self):
        """
        @rtype:  int
        @return: Boot time epoch"""
        return self.data.boot_time

    def pingTime(self):
        """
        @rtype:  int
        @return: Ping time epoch"""
        return self.data.ping_time

    def pingLast(self):
        """
        @rtype:  int
        @return: Seconds since last ping"""
        return int(time.time() - self.pingTime())

    def tags(self):
        """
        @rtype:  list<str>
        @return: Tags applied to the host"""
        return self.data.tags

    def state(self):
        """
        @rtype:  Cue3.HardwareState
        @return: """
        return self.data.state

    def lockState(self):
        """
        @rtype:  Cue3.LockState
        @return: """
        return self.data.lock_state


class NestedHost(Host):
    """This class contains information and actions related to a nested job."""
    def __init__(self, host):
        super(NestedHost, self).__init__(host)

    def children(self):
        """The procs running on this host
        @rtype:  list<Proc>
        @return: The procs running on this host"""
        return self.procs
