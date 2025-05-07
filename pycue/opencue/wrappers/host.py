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
from builtins import input
import grpc

from opencue_proto import comment_pb2
from opencue_proto import host_pb2
from opencue import Cuebot
from opencue import util
from opencue import search
import opencue.wrappers.comment
# pylint: disable=cyclic-import
import opencue.wrappers.proc
import opencue.wrappers.render_partition


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
        return [opencue.wrappers.render_partition.RenderPartition(p)
            for p in response.render_partitions.render_partitions]

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

    @util.grpcExceptionParser
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

    @staticmethod
    def hasHostRebootedSince(host, start_time):
        """
        Returns whether a host has rebooted since `start_time` or is in process of
        rebooting (`state = REBOOT_WHEN_IDLE`)

        :param host: Host wrapper
        :param start_time: epoch time
        :return: True if host booted after start_time or is rebooting
        """
        return (host.state() == host_pb2.HardwareState.Value('REBOOT_WHEN_IDLE') or
                (host.state() == host_pb2.HardwareState.Value('UP') and
                 host.bootTime() < start_time))

    @staticmethod
    def rebootFarmSafely(group_size, start_time=None, **options):
        """Requests an idle reboot for nodes found using the
        options search criteria. For safety, workstations are always excluded.

        Method can only be called interactively

        For example::
        from opencue.wrappers.host import Host
        Host.rebootFarmSafely(5, 1, alloc=["lax.ngp"])

        Uses the hostSearch module to find hosts and requests a reboot for each
        of them in groups defined by the arg `group_size`. If `start_time` is
        provided the function will only target hosts that have
        `boot_time` > `start_time`.

        Possible hostSearch args:
           - host: host names - list
           - match: host name substring match - str
           - regex: a host name search by regular expression - str
           - id: a search by unique id - str
           - alloc: search by allocation. - list

        :param group_size: Reboot hosts in groups limited to this size
        :param start_time: if not none, only hosts with boot_time<start_time will be targeted
        :param options: HostSearch params
        """
        hosts = search.HostSearch.byOptions(**options)
        # Workstations are marked as Nimby, ignore those.
        hosts = [host for host in hosts if not host.isNimbyEnabled() and host.isUp()]
        check_hosts_interval_seconds = 30

        if len(hosts) == 0:
            print("No hosts found")
            return

        print("Rebooting hosts:\n%s.\n\n"
              "Are you sure hosts on this list are safe to be rebooted? [Y/n]" %
              [str(host.name()) for host in hosts])
        while True:
            choice = input()
            if choice == "Y":
                break
            if choice == "n":
                return

        groups = [hosts[x:x+group_size] for x in range(0, len(hosts), group_size)]

        host_still_rebooting = []

        if start_time is None:
            start_time = int(time.time())
        for group in groups:
            group_host_names = []
            for host in group:
                if host.bootTime() < start_time:
                    try:
                        host.rebootWhenIdle()
                    except grpc.RpcError as rpc_error:
                        # pylint: disable=no-member
                        if rpc_error.code() in [grpc.StatusCode.UNAVAILABLE,
                                                grpc.StatusCode.CANCELLED]:
                            # Wait and Retry
                            time.sleep(5)
                            host.rebootWhenIdle()
                        else:
                            raise rpc_error
                        # pylint: enable=no-member

                group_host_names.append(str(host.name()))
            print("Requesting reboot for %s. Waiting for completion." % group_host_names)

            # Wait until 80% of a group gets upgraded to jump to the next group
            while True:
                try:
                    hosts = search.HostSearch.byName(group_host_names)
                    rebooting_hosts = [str(host.name()) for host in hosts
                                       if Host.hasHostRebootedSince(host, start_time)]
                    if len(rebooting_hosts) <= len(hosts) * 0.2:
                        host_still_rebooting.extend(rebooting_hosts)
                        print("Moving to the next group, left behind %s..\n" % rebooting_hosts)
                        break
                    print("Still waiting on %s.." % rebooting_hosts)
                    time.sleep(check_hosts_interval_seconds)
                except grpc.RpcError as rpc_error:
                    # Ignore rpc unavailable to survive short service outages on the server side
                    # pylint: disable=no-member
                    if rpc_error.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.CANCELLED]:
                        continue
                    # pylint: enable=no-member

        # Wait for remaining hosts to finish (20% not awaited for)
        if host_still_rebooting:
            print("Waiting on remaining hosts to reboot")
            while True:
                try:
                    hosts = search.HostSearch.byName(host_still_rebooting)
                    rebooting_hosts = [str(host.name()) for host in hosts
                                       if Host.hasHostRebootedSince(host, start_time)]
                    if len(rebooting_hosts) == 0:
                        break
                    host_still_rebooting = rebooting_hosts
                    print("Still waiting on %s.." % rebooting_hosts)
                    time.sleep(check_hosts_interval_seconds)
                except grpc.RpcError as rpc_error:
                    # Ignore rpc unavailable to survive short service outages on the server side
                    # pylint: disable=no-member
                    if rpc_error.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.CANCELLED]:
                        continue
                    # pylint: enable=no-member
        print("Finished rebooting requested hosts")

    @staticmethod
    def monitorRebootFarm(start_time, **options):
        """Monitor hosts rebooting

        Possible args:
           - host: host names - list
           - match: host name substring match - str
           - regex: a host name search by regular expression - str
           - id: a search by unique id - str
           - alloc: search by allocation. - list

        :param start_time: if not none only hosts with boot_time<start_time will be targeted
        :param options: HostSearch params
        """
        hosts = search.HostSearch.byOptions(**options)
        # Workstations are marked as Nimby, ignore those.
        hosts_names = [host.name() for host in hosts if not host.isNimbyEnabled() and host.isUp()]
        check_hosts_interval_seconds = 30

        if len(hosts) == 0:
            print("No hosts found")
            return

        if start_time is None:
            start_time = int(time.time())

        # Wait until 80% of a group gets upgraded to jump to the next group
        while True:
            try:
                hosts = search.HostSearch.byName(hosts_names)
                rebooting_hosts = [str(host.name()) for host in hosts
                                   if Host.hasHostRebootedSince(host, start_time)]
                if len(rebooting_hosts) == 0:
                    break
                print("Still waiting on %s hosts: %s.." % (len(rebooting_hosts), rebooting_hosts))
                time.sleep(check_hosts_interval_seconds)
            except grpc.RpcError as rpc_error:
                # Ignore rpc unavailable to survive short service outages on the server side
                # pylint: disable=no-member
                if rpc_error.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.CANCELLED]:
                    continue
                # pylint: enable=no-member

        print("Finished rebooting hosts")

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
        return self.data.cores - self.data.idle_cores

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
