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

"""Module for classes related to hosts."""

import enum
import os
import time

from opencue import Cuebot
from opencue.compiled_proto import comment_pb2
from opencue.compiled_proto import host_pb2
import opencue.wrappers.comment
# pylint: disable=cyclic-import
import opencue.wrappers.proc


class Host(object):
    """This class contains the grpc implementation related to a Host."""

    class HardwareState(enum.IntEnum):
        """Enum representing the hardware state of the host."""
        UP = host_pb2.UP
        DOWN = host_pb2.DOWN
        REBOOTING = host_pb2.REBOOTING
        REBOOT_WHEN_IDLE = host_pb2.REBOOT_WHEN_IDLE
        REPAIR = host_pb2.REPAIR

    class HostTagType(enum.IntEnum):
        """Enum representing the type of a host tag."""
        MANUAL = host_pb2.MANUAL
        HARDWARE = host_pb2.HARDWARE
        ALLOC = host_pb2.ALLOC
        HOSTNAME = host_pb2.HOSTNAME

    class LockState(enum.IntEnum):
        """Enum representing whether the host is locked."""
        OPEN = host_pb2.OPEN
        LOCKED = host_pb2.LOCKED
        NIMBY_LOCKED = host_pb2.NIMBY_LOCKED

    class ThreadMode(enum.IntEnum):
        """Enum representing the thread mode of the host."""
        AUTO = host_pb2.AUTO
        ALL = host_pb2.ALL
        VARIABLE = host_pb2.VARIABLE

    def __init__(self, host=None):
        self.data = host
        self.__id = host.id
        self.stub = Cuebot.getStub('host')

    def lock(self):
        """Locks the host so that it no longer accepts new frames"""
        self.stub.Lock(host_pb2.HostLockRequest(host=self.data), timeout=Cuebot.Timeout)

    def unlock(self):
        """Unlocks the host.

        Cancels any actions that were waiting for all running frames to finish."""
        self.stub.Unlock(host_pb2.HostUnlockRequest(host=self.data), timeout=Cuebot.Timeout)

    def delete(self):
        """Deletes the host from the cuebot"""
        self.stub.Delete(host_pb2.HostDeleteRequest(host=self.data), timeout=Cuebot.Timeout)

    def getProcs(self):
        """Returns a list of procs under this host.

        :rtype: list<opencue.wrappers.proc.Proc>
        :return: A list of procs under this host
        """
        response = self.stub.GetProcs(host_pb2.HostGetProcsRequest(host=self.data),
                                      timeout=Cuebot.Timeout)
        return [opencue.wrappers.proc.Proc(p) for p in response.procs.procs]

    def redirectToJob(self, procs, job):
        """Unbooks and redirects the proc to the specified job.  Optionally
        kills the proc immediately.

        :param procs: list<opencue.wrappers.proc.Proc>
        :param job: job id
        """
        self.stub.RedirectToJob(
            host_pb2.HostRedirectToJobRequest(host=self.data,
                                              proc_names=[proc.data.id for proc in procs],
                                              job_id=job.data.id), timeout=Cuebot.Timeout)

    def getRenderPartitions(self):
        """Returns a list of render partitions associated with this host

        :rtype:  list<renderPartition_pb2.RenderPartition>
        :return: list of render partitions under this host
        """
        response = self.stub.GetRenderPartitions(host_pb2.HostGetRenderPartitionsRequest(
            host=self.data), timeout=Cuebot.Timeout)
        partitionSeq = response.render_partitions
        return partitionSeq.render_partitions

    def rebootWhenIdle(self):
        """Sets the machine to reboot once idle.

        The host will no longer accept new frames."""
        self.stub.RebootWhenIdle(host_pb2.HostRebootWhenIdleRequest(host=self.data),
                                 timeout=Cuebot.Timeout)

    def reboot(self):
        """Causes the host to kill all running frames and reboot the machine."""
        self.stub.Reboot(host_pb2.HostRebootRequest(host=self.data), timeout=Cuebot.Timeout)

    def addTags(self, tags):
        """Adds tags to a host.

        :type  tags: list<str>
        :param tags: The tags to add
        """
        self.stub.AddTags(host_pb2.HostAddTagsRequest(host=self.data, tags=tags),
                          timeout=Cuebot.Timeout)

    def removeTags(self, tags):
        """Removes tags from this host.

        :type  tags: list<str>
        :param tags: The tags to remove
        """
        self.stub.RemoveTags(host_pb2.HostRemoveTagsRequest(host=self.data, tags=tags),
                             timeout=Cuebot.Timeout)

    def renameTag(self, oldTag, newTag):
        """Renames a tag.

        :type  oldTag: str
        :param oldTag: old tag to rename
        :type  newTag: str
        :param newTag: new name for the tag
        """
        self.stub.RenameTag(
            host_pb2.HostRenameTagRequest(host=self.data, old_tag=oldTag, new_tag=newTag),
            timeout=Cuebot.Timeout)

    def setAllocation(self, allocation):
        """Sets the host to the given allocation.

        :type  allocation: opencue.wrappers.allocation.Allocation
        :param allocation: allocation to put the host under
        """
        self.stub.SetAllocation(
            host_pb2.HostSetAllocationRequest(host=self.data, allocation_id=allocation.id()),
            timeout=Cuebot.Timeout)

    def addComment(self, subject, message):
        """Appends a comment to the host's comment list.

        :type  subject: str
        :param subject: Subject data
        :type  message: str
        :param message: Message data
        """
        comment = comment_pb2.Comment(
            user=os.getenv("USER", "unknown"),
            subject=subject,
            message=message or " ",
            timestamp=0
        )
        self.stub.AddComment(host_pb2.HostAddCommentRequest(host=self.data, new_comment=comment),
                             timeout=Cuebot.Timeout)

    def getComments(self):
        """Returns the host's comment list.

        :rtype:  list<opencue.wrappers.comment.Comment>
        :return: the comment list of the host
        """
        response = self.stub.GetComments(host_pb2.HostGetCommentsRequest(host=self.data),
                                         timeout=Cuebot.Timeout)
        commentSeq = response.comments
        return [opencue.wrappers.comment.Comment(c) for c in commentSeq.comments]

    def setHardwareState(self, state):
        """Sets the host hardware state.

        :type  state: host_pb2.HardwareState
        :param state: state to set host to
        """
        self.stub.SetHardwareState(
            host_pb2.HostSetHardwareStateRequest(host=self.data, state=state),
            timeout=Cuebot.Timeout)

    def setOs(self, osName):
        """Sets the host operating system.

        :type  osName: string
        :param osName: os value to set host to
        """
        self.stub.SetOs(host_pb2.HostSetOsRequest(host=self.data, os=osName),
                        timeout=Cuebot.Timeout)

    def setThreadMode(self, mode):
        """Sets the host thread mode.

        :type  mode: host_pb2.ThreadMode
        :param mode: ThreadMode to set host to
        """
        self.stub.SetThreadMode(host_pb2.HostSetThreadModeRequest(host=self.data, mode=mode),
                                timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the host.

        :rtype:  str
        :return: id of the host
        """
        if not hasattr(self, "__id"):
            self.__id = self.data.id
        return self.__id

    def name(self):
        """Returns the name of the host.

        :rtype:  str
        :return: name of the host
        """
        return self.data.name

    def isNimbyEnabled(self):
        """Returns true if nimby is enabled.

        :rtype:  bool
        :return: True if nimby is enabled
        """
        return self.data.nimby_enabled

    def isUp(self):
        """Returns True if the host hardware state indicates the machine is up.

        :rtype:  bool
        :return: True if the host is up
        """
        return self.data.state == host_pb2.HardwareState.Value('UP')

    def isLocked(self):
        """Returns True if the host is locked.

        :rtype:  bool
        :return: True if the host is locked
        """
        return self.data.lock_state == host_pb2.LockState.Value('LOCKED')

    def isCommented(self):
        """Returns true if the host has a comment.

        :rtype:  bool
        :return: whether the host has a comment
        """
        return self.data.has_comment

    def cores(self):
        """Returns the total number of cores the host has.

        :rtype: float
        :return: total number of host cores
        """
        return self.data.cores

    def coresReserved(self):
        """Returns the number of cores the host has which are currently reserved.

        :rtype: float
        :return: number of cores reserved
        """
        return self.data.cores - self.data.idle_ores

    def coresIdle(self):
        """Returns the number of cores the host currently has idel.

        :rtype: float
        :return: number of cores idle
        """
        return self.data.idle_cores

    def mem(self):
        """Returns the amount of memory the host has in kb.

        :rtype:  int
        :return: amount of memory in kb
        """
        return self.data.memory

    def memReserved(self):
        """Returns the amount of memory the host has currently reserved.

        :rtype:  int
        :return: amount of memory reserved in kb
        """
        return self.data.memory - self.data.idle_memory

    def memIdle(self):
        """Returns the amount of memory the host currently has idle.

        :rtype:  int
        :return: amount of idle memory in kb
        """
        return self.data.idle_memory

    def memUsed(self):
        """Returns the amount of memory the host currently has in use.

        :rtype:  int
        :return: amount of in-use memory in kb
        """
        return self.data.total_memory - self.data.free_memory

    def memTotal(self):
        """Returns the total amount of memory the host has.

        :rtype:  int
        :return: total amount of memory on host
        """
        return self.data.total_memory

    def memFree(self):
        """Returns the amount of memory the host currently has free.

        :rtype:  int
        :return: amount of free memory in kb
        """
        return self.data.free_memory

    def swapUsed(self):
        """Returns the amount of swap space the host has in use.

        :rtype:  int
        :return: amount of swap used in kb
        """
        return self.data.total_swap - self.data.free_swap

    def swapTotal(self):
        """Returns the total amount of swap space the host has.

        :rtype:  int
        :return: total amount of swap space in kb
        """
        return self.data.total_swap

    def swapFree(self):
        """Returns the amount of free swap space the host has.

        :rtype:  int
        :return: amount of free swap space in kb
        """
        return self.data.free_swap

    def mcpUsed(self):
        """Returns the amount of /mcp space the host is using.

        :rtype:  int
        :return: amount of mcp used in kb
        """
        return self.mcpTotal() - self.mcpFree()

    def mcpTotal(self):
        """Returns the total amount of /mcp space the host has.

        :rtype:  int
        :return: total amount of mcp in kb
        """
        return self.data.total_mcp

    def mcpFree(self):
        """Returns the amount of free /mcp space the host has.

        :rtype:  int
        :return: amount of mcp free in kb
        """
        return self.data.free_mcp

    def load(self):
        """Returns the host load average.

        :rtype:  int
        :return: host load average * 100
        """
        return self.data.load

    def bootTime(self):
        """Returns the time the host was booted.

        :rtype:  int
        :return: host boot time as an epoch
        """
        return self.data.boot_time

    def pingTime(self):
        """Returns the last time the host sent a status report.

        :rtype:  int
        :return: last ping time as an epoch
        """
        return self.data.ping_time

    def pingLast(self):
        """Returns the number of seconds since the last time the host sent a status report.

        :rtype:  int
        :return: seconds since last ping
        """
        return int(time.time() - self.pingTime())

    def tags(self):
        """Returns the tags the host has.

        :rtype:  list<str>
        :return: list of tags applied to the host
        """
        return self.data.tags

    def state(self):
        """Returns the hardware state of the host.

        :rtype:  host_pb2.HardwareState
        :return: the hardware state of the host
        """
        return self.data.state

    def lockState(self):
        """Returns the lock state of the host.

        :rtype:  host_pb2.LockState
        :return: the lock state of the host
        """
        return self.data.lock_state

    def os(self):
        """
        :rtype: str
        :return: the operating system of the host
        """
        return self.data.os

class NestedHost(Host):
    """This class contains information and actions related to a nested host."""

    def __init__(self, host):
        super(NestedHost, self).__init__(host)

    def children(self):
        """The procs running on this host.

        :rtype:  host_pb2.NestedProcSeq
        :return: the procs running on this host
        """
        return self.data.procs
