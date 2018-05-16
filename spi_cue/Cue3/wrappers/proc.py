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

Module: proc.py - Cue3 Library implementation of a proc

Created: April, 15th, 2008

Contact: Middle-Tier Group (middle-tier@imageworks.com)

SVN: $Id$
"""

import time
import cue.CueClientIce as CueClientIce

class Proc(CueClientIce.Proc):
    """This class contains the ice implementation related to a proc."""
    def __init__(self):
        """_Proc class initialization"""
        CueClientIce.Proc.__init__(self)
   
    def kill(self):
        """Kill the frame running on this proc"""
        self.proxy.kill()

    def unbook(self, kill=False):
        """Unbook the current frame.  If the value of kill is true, 
           the frame will be immediately killed.
        """
        self.proxy.unbook(kill)

    def getHost(self):
        """Return the host this proc is allocated from.
        @rtype:  Host
        @return: The host this proc is allocated from."""
        return self.proxy.getHost()

    def getFrame(self):
        """Return the frame this proc is running.
        @rtype:  Frame
        @return: The fame this proc is running."""
        return self.proxy.getFrame()

    def getLayer(self):
        """Return the layer this proc is running.
        @rtype:  Layer
        @return: The layer this proc is running."""
        return self.proxy.getLayer()

    def getJob(self):
        """Return the job this proc is running.
        @rtype:  Job
        @return: The job this proc is running."""
        return self.proxy.getJob()

    def id(self):
        """Returns the id of the proc
        @rtype:  str
        @return: Proc uuid"""
        if not hasattr(self, "__id"):
            self.__id = self.proxy.ice_getIdentity().name
        return self.__id

    def name(self):
        """Returns the name of the proc
        @rtype:  str
        @return: Proc name"""
        return self.data.name

    def jobName(self):
        """Returns the job name of the frame running on the proc
        @rtype:  str
        @return: Job name"""
        return self.data.jobName

    def frameName(self):
        """Returns the name of the frame on the proc
        @rtype:  str
        @return: Frame name"""
        return self.data.frameName

    def showName(self):
        """Returns the name of the show whos frame is running on the proc
        @rtype:  str
        @return: Frames show name"""
        return self.data.showName

    def coresReserved(self):
        """The number of cores reserved for this frame
        @rtype:  float
        @return: Cores reserved for the running frame"""
        return self.data.reservedCores

    def memReserved(self):
        """The amount of memory reserved for the running frame
        @rtype:  int
        @return: Kb memory reserved for the running frame"""
        return self.data.reservedMemory

    def memUsed(self):
        """The amount of memory used by the running frame
        @rtype:  int
        @return: Kb memory used by the running frame"""
        return self.data.usedMemory
     
    def bookedTime(self):
        """The last time this proc was assigned to a job in epoch seconds.
        @rtype: int"""
        return self.data.bookedTime

    def dispatchTime(self):
        """The last time this proc was assigned to a job in epoch seconds.
        @rtype: int"""
        return self.data.dispatchTime
    
    def isUnbooked(self):
        """Returns true if this proc is unbooked
        @rtype: boolean"""
        return self.data.unbooked

class NestedProc(CueClientIce.NestedProc, Proc):
    """This class contains information and actions related to a nested job."""
    def __init__(self):
        CueClientIce.NestedProc.__init__(self)
        Proc.__init__(self)
        ## job children are most likely empty but its possible to
        ## populate this with NesterLayer objects.
        self.__children = []

    def children(self):
        return self.__children


