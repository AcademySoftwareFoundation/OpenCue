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
allocation module
"""
import cue.CueClientIce as CueClientIce
from ..api import *

class Allocation(CueClientIce.Allocation):
    """This class contains the ice implementation related to an Allocation."""
    def __init__(self):
        """_Allocation class initialization"""
        CueClientIce.Allocation.__init__(self)

    def setName(self, name):
        """Sets a new name for the allocation.
        @type name: str
        @param name: the new name"""
        self.proxy.setName(name)

    def setTag(self, tag):
        """Sets a new tag for the allocation.
        @type name: str
        @param name: the new tag"""
        self.proxy.setTag(tag)

    def delete(self):
        """Delete the record of the allocation from the cuebot"""
        self.proxy.delete()

    def reparentHosts(self, hosts):
        """Moves the given hosts to the allocation
        @type  hosts: list<HostInterfacePrx or Host or id or str hostname>
        @param hosts: The hosts to move to this allocation"""
        proxies = proxy(hosts, "Host")
        if proxies:
            self.proxy.reparentHosts(proxies)

    def id(self):
        """Returns the id of the allocation
        @rtype:  str
        @return: Frame uuid"""
        return self.proxy.ice_getIdentity().name

    def name(self):
        """Returns the name of the allocation
        @rtype:  str
        @return: Allocation name"""
        return self.data.name

    def tag(self):
        """Returns the allocation tag
        @rtype:  str
        @return: Allocation tag"""
        return self.data.tag

    def totalCores(self):
        """Returns the total number of cores in the allocation.
        @rtype:  float
        @return: Total number of cores in the allocation"""
        return self.stats.cores

    def totalAvailableCores(self):
        """Returns the total number of cores available for
        booking in the allocation.
        @rtype:  float
        @return: Total number of cores in the allocation"""
        return self.stats.availableCores

    def totalIdleCores(self):
        """Returns the total number of idle cores in the allocation.
        @rtype:  float
        @return: Total number of idle cores in the allocation"""
        return self.stats.idleCores

    def totalRunningCores(self):
        """Returns the total number of running cores in the allocation.
        Each 100 returned is the same as 1 physical core.
        @rtype:  float
        @return: Total number of running cores in the allocation"""
        # All core reserved
        return self.stats.runningCores

    def totalLockedCores(self):
        """Returns the total number of locked cores in the allocation.
        Each 100 returned is the same as 1 physical core.
        @rtype:  float
        @return: Total number of locked cores in the allocation"""
        return self.stats.lockedCores

    def totalHosts(self):
        """Returns the total number of hosts in the allocation
        @rtype:  int
        @return: Total number of hosts in the allocation"""
        return self.stats.hosts

    def totalLockedHosts(self):
        """Returns the total number of locked hosts in the allocation
        @rtype:  int
        @return: Total number of locked hosts in the allocation"""
        return self.stats.lockedHosts

    def totalDownHosts(self):
        """Returns the total number of down hosts in the allocation
        @rtype:  int
        @return: Total number of down hosts in the allocation"""
        return self.stats.downHosts

