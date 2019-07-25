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

Module: depend.py - opencue Library implementation of a allocation
"""


import enum

from opencue.compiled_proto import depend_pb2
from opencue.cuebot import Cuebot


class Depend(object):

    class DependType(enum.IntEnum):
        JOB_ON_JOB = depend_pb2.JOB_ON_JOB
        JOB_ON_LAYER = depend_pb2.JOB_ON_LAYER
        JOB_ON_FRAME = depend_pb2.JOB_ON_FRAME
        LAYER_ON_JOB = depend_pb2.LAYER_ON_JOB
        LAYER_ON_LAYER = depend_pb2.LAYER_ON_LAYER
        LAYER_ON_FRAME = depend_pb2.LAYER_ON_FRAME
        FRAME_ON_JOB = depend_pb2.FRAME_ON_JOB
        FRAME_ON_LAYER = depend_pb2.FRAME_ON_LAYER
        FRAME_ON_FRAME = depend_pb2.FRAME_ON_FRAME
        FRAME_BY_FRAME = depend_pb2.FRAME_BY_FRAME
        PREVIOUS_FRAME = depend_pb2.PREVIOUS_FRAME
        LAYER_ON_SIM_FRAME = depend_pb2.LAYER_ON_SIM_FRAME

    class DependTarget(enum.IntEnum):
        INTERNAL = depend_pb2.INTERNAL
        EXTERNAL = depend_pb2.EXTERNAL
        ANY_TARGET = depend_pb2.ANY_TARGET

    def __init__(self, depend=None):
        self.data = depend
        self.stub = Cuebot.getStub('depend')

    def satisfy(self):
        self.stub.Satisfy(
            depend_pb2.DependSatisfyRequest(depend=self.data), timeout=Cuebot.Timeout)

    def unsatisfy(self):
        self.stub.Unsatisfy(
            depend_pb2.DependUnsatisfyRequest(depend=self.data), timeout=Cuebot.Timeout)

    def id(self):
        """Returns the depdendency's unique id.  Dependencies are one of the only
        entities without a unique name so the unique ID is exposed to act
        as the name.  This is mainly to make command line tools easier to use.
        @rtype: str
        @return: the dependencies unique id"""
        return self.data.id

    def isInternal(self):
        """Returns true if the dependency is internal to the depender job, false if not.
        @rtype: bool
        @returns: true"""
        if self.data.depend_er_job == self.data.depend_on_job:
            return True
        return False

    def type(self):
        return self.data.type

    def target(self):
        return self.data.target

    def chunkSize(self):
        return self.data.chunk_size

    def anyFrame(self):
        return self.data.any_frame

    def isActive(self):
        return self.data.active

    def dependErJob(self):
        return self.data.depend_er_job

    def dependErLayer(self):
        return self.data.depend_er_layer

    def dependErFrame(self):
        return self.data.depend_er_frame

    def dependOnJob(self):
        return self.data.depend_on_job

    def dependOnLayer(self):
        return self.data.depend_on_layer

    def dependOnFrame(self):
        return self.data.depend_on_frame
