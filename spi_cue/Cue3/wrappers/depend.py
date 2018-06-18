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

Module: depend.py - Cue3 Library implementation of a allocation

Created: June 2, 2008

Contact: Middle-Tier Group 

SVN: $Id$
"""
import cue.CueClientIce as CueClientIce

class Depend(CueClientIce.Depend):
    """This class contains the ice implementation related to a Dependency"""
    def __init__(self):
        """_Depend class initialization"""
        CueClientIce.Depend.__init__(self)

    def satisfy(self):
        self.proxy.satisfy()

    def id(self):
        """Returns the depdendency's unique id.  Dependencies are one of the only
        entities without a unique name so the unique ID is exposed to act
        as the name.  This is mainly to make command line tools easier to use.
        @rtype: str
        @return: the dependencies unique id"""
        return self.proxy.ice_getIdentity().name

    def isInternal(self):
        """Returns true if the dependency is internal to the depender job, false if not.
        @rtype: bool
        @returns: true"""
        if self.data.dependErJob == self.data.dependOnJob:
            return True
        return False

    def type(self):
        return self.data.type

    def target(self):
        return self.data.target

    def chunkSize(self):
        return self.data.chunkSize

    def anyFrame(self):
        return self.data.anyFrame

    def isActive(self):
        return self.data.active

    def dependErJob(self):
        return self.data.dependErJob

    def dependErLayer(self):
        return self.data.dependErLayer

    def dependErFrame(self):
        return self.data.dependErFrame

    def dependOnJob(self):
        return self.data.dependOnJob

    def dependOnLayer(self):
        return self.data.dependOnLayer

    def dependOnFrame(self):
        return self.data.dependOnFrame

