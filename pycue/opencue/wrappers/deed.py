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
Project: opencue

Module: deed.py - deed object

"""

import opencue.wrappers.host
from opencue.compiled_proto import host_pb2
from opencue.cuebot import Cuebot


class Deed(object):
    """This class contains the grpc implementation related to a Deed."""

    def __init__(self, comment=None):
        self.data = comment
        self.stub = Cuebot.getStub('comment')

    def delete(self):
        """Delete this comment"""
        self.stub.Delete(host_pb2.DeedDeleteRequest(deed=self.data), timeout=Cuebot.Timeout)

    def getHost(self):
        """Return the host for this deed.

        :rtype:  opencue.wrappers.host.Host Wrapper
        :return: Host associated with this deed"""
        return opencue.wrappers.host.Host(
            self.stub.GetHost(host_pb2.DeedGetHostRequest(deed=self.data),
                              timeout=Cuebot.Timeout).host)

    def getOwner(self):
        """Returns the owner for these settings.

        :rtype: opencue.wrappers.host.Host
        :return: Owner of this deed"""
        return opencue.wrappers.owner.Owner(
            self.stub.GetOwner(host_pb2.DeedGetOwnerRequest(deed=self.data),
                               timeout=Cuebot.Timeout).owner)

    def setBlackoutTime(self, startTime, stopTime):
        """Sets a blackout time for the host.

        :type startTime: int
        :param startTime: blackout start time
        :type stopTime: int
        :param stopTime: blackout stop time"""
        self.stub.SetBlackoutTime(
            host_pb2.DeedSetBlackoutTimeRequest(deed=self.data,
                                                start_time=startTime,
                                                stop_time=stopTime),
            timeout=Cuebot.Timeout)

    def setBlackoutTimeEnabled(self, enabled):
        """Enable/Disable blackout time without changing the times.

        :type enabled: bool
        :param enabled: enable/disable blackout time"""
        self.stub.SetBlackoutTimeEnabled(
            host_pb2.DeedSetBlackoutTimeEnabledRequest(deed=self.data,
                                                       enabled=enabled),
            timeout=Cuebot.Timeout)

    def id(self):
        return self.data.id

    def host(self):
        return self.data.host

    def owner(self):
        return self.data.owner

    def show(self):
        return self.data.show

    def blackout(self):
        return self.data.blackout

    def blackoutStartTime(self):
        return self.data.blackout_start_time

    def blackoutStopTime(self):
        return self.data.blackout_stop_time
