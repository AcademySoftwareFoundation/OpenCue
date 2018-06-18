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

Module: subscription.py - Cue3 Library implementation of a subscription

Created: March 3, 2008

Contact: Middle-Tier Group 

SVN: $Id$
"""

import cue.CueClientIce as CueClientIce

class Subscription(CueClientIce.Subscription):
    """This class contains the ice implementation related to a subscription."""
    def __init__(self):
        """_Subscription class initialization"""
        CueClientIce.Subscription.__init__(self)

    def setName(self, name):
        self.proxy.setName(name)

    def setSize(self, size):
        self.proxy.setSize(float(size))

    def setBurst(self, burst):
        self.proxy.setBurst(float(burst))

    def delete(self):
        self.proxy.delete()

    def id(self):
        """Returns the id of the subscription
        @rtype:  str
        @return: Frame uuid"""
        return self.proxy.ice_getIdentity().name

    def name(self):
        """Returns the name of the subscription
        @rtype:  str
        @return: Subscription name"""
        return self.data.name

    def size(self):
        """Returns the subscription size
        @rtype:  int
        @return: Subscription size"""
        return self.data.size

    def burst(self):
        """Returns the subscription burst
        @rtype:  int
        @return: Allowed burst"""
        return self.data.burst

    def reservedCores(self):
        """Returns the current number reserved in this subscription
        @rtype:  float
        @return: Total running cores"""
        return self.data.reservedCores

    def show(self):
        """Returns the show that this subscription is for
        @rtype:  str
        @return: The show that this subscription is for"""
        return self.data.showName

    def allocation(self):
        """Returns the allocation that this subscription is subscribed to
        @rtype:  str
        @return: The allocation subscribed to"""
        return self.data.allocationName

