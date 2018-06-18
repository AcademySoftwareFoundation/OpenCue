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

Created: February 12, 2008

Contact: Middle-Tier Group 

SVN: $Id$
"""
import os
import time
import cue.CueClientIce as CueClientIce
import cue.CueIce as CueIce
from proc import Proc

class Host(CueClientIce.Host):
    """This class contains the ice implementation related to a host."""
    def __init__(self):
        """_Host class initialization"""
        CueClientIce.Host.__init__(self)

    def lock(self):
        """Locks the host so that it no longer accepts new frames"""
        self.proxy.lock()

    def unlock(self):
        """Unlocks the host and cancels any actions that were waiting for all
        running frames to finish."""
        self.proxy.unlock()

    def delete(self):
        """Delete the host from the cuebot"""
        self.proxy.delete()

    def rebootWhenIdle(self):
        """Causes the host to no longer accept new frames and
        when the machine is idle it will reboot."""
        self.proxy.rebootWhenIdle()

    def reboot(self):
        """Causes the host to kill all running frames and reboot the machine."""
        self.proxy.reboot()

    def addTags(self, tags):
        """Adds tags to a host
        @type  tags: list<str>
        @param tags: The tags to add"""
        self.proxy.addTags(tags)

    def removeTags(self, tags):
        """Remove tags from this host
        @type  tags: list<str>
        @param tags: The tags to remove"""
        self.proxy.removeTags(tags)

    def renameTag(self, oldTag, newTag):
        """Renames a tag
        @type  oldTag: str
        @param oldTag: The old tag to rename
        @type  newTag: str
        @param newTag: The new name for the tag"""
        self.proxy.renameTag(oldTag, newTag)

    def setAllocation(self, allocation):
        """Sets the host to the given allocation
        @type  allocation: Allocation
        @param allocation: An allocation object"""
        self.proxy.setAllocation(allocation.proxy)

    def addComment(self, subject, message):
        """Appends a comment to the hosts's comment list
        @type  subject: str
        @param subject: Subject data
        @type  message: str
        @param message: Message data"""
        c = CueClientIce.CommentData()
        c.user = os.getenv("USER","unknown")
        c.subject = subject
        c.message = message or " "
        c.timestamp = 0
        self.proxy.addComment(c)

    def getComments(self):
        """returns the hosts comments"""
        return self.proxy.getComments()

    def id(self):
        """Returns the id of the host
        @rtype:  str
        @return: Host uuid"""
        if not hasattr(self, "__id"):
            self.__id = self.proxy.ice_getIdentity().name
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
        return self.data.nimbyEnabled

    def isUp(self):
        """Returns True if the host is up
        @rtype:  bool
        @return: True if the host is up"""
        return self.data.state == CueIce.HardwareState.Up

    def isLocked(self):
        """Returns True if the host is locked
        @rtype:  bool
        @return: True if the host is locked"""
        return self.data.lockState == CueIce.LockState.Locked

    def isCommented(self):
        """Returns true if the host has a comment
        @rtype:  bool
        @return: If the job has a comment"""
        return self.data.hasComment

    def cores(self):
        """
        @rtype:  float
        @return: """
        return self.data.cores

    def coresReserved(self):
        """
        @rtype:  float
        @return: """
        return self.data.cores - self.data.idleCores

    def coresIdle(self):
        """
        @rtype:  float
        @return: """
        return self.data.idleCores

    def mem(self):
        """
        @rtype:  int
        @return: """
        return self.data.memory

    def memReserved(self):
        """
        @rtype:  int
        @return: """
        return self.data.memory - self.data.idleMemory

    def memIdle(self):
        """
        @rtype:  int
        @return: """
        return self.data.idleMemory

    def memUsed(self):
        """
        @rtype:  int
        @return: """
        return self.data.totalMemory - self.data.freeMemory

    def memTotal(self):
        """
        @rtype:  int
        @return: """
        return self.data.totalMemory

    def memFree(self):
        """
        @rtype:  int
        @return: """
        return self.data.freeMemory

    def swapUsed(self):
        """
        @rtype:  int
        @return: """
        return self.data.totalSwap - self.data.freeSwap

    def swapTotal(self):
        """
        @rtype:  int
        @return: """
        return self.data.totalSwap

    def swapFree(self):
        """
        @rtype:  int
        @return: """
        return self.data.freeSwap

    def mcpUsed(self):
        """
        @rtype:  int
        @return: """
        return self.data.totalMcp - self.data.freeMcp

    def mcpTotal(self):
        """
        @rtype:  int
        @return: """
        return self.data.totalMcp
    def mcpFree(self):
        """
        @rtype:  int
        @return: """
        return self.data.freeMcp

    def load(self):
        """Returns the load on the host
        @rtype:  int
        @return: Host load average * 100"""
        return self.data.load

    def bootTime(self):
        """
        @rtype:  int
        @return: Boot time epoch"""
        return self.data.bootTime

    def pingTime(self):
        """
        @rtype:  int
        @return: Ping time epoch"""
        return self.data.pingTime

    def pingLast(self):
        """
        @rtype:  int
        @return: Seconds since last ping"""
        return int(time.time() - self.data.pingTime)

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
        return self.data.lockState

    def getProcs(self):
        """Returns a list of procs under this host.
        @rtype:  list<Proc>
        @return: A list of procs under this host"""
        return self.proxy.getProcs()

class NestedHost(CueClientIce.NestedHost, Host):
    """This class contains information and actions related to a nested job."""
    def __init__(self):
        CueClientIce.NestedHost.__init__(self)
        Host.__init__(self)

    def children(self):
        """The procs running on this host
        @rtype:  list<Proc>
        @return: The procs running on this host"""
        return self.procs

