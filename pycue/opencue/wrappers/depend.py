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

"""Module for classes related to dependencies."""

import enum

from opencue_proto import depend_pb2
from opencue.cuebot import Cuebot


class Depend(object):
    """This class contains the grpc implementation related to a Depend."""

    class DependType(enum.IntEnum):
        """Enum representing the type of dependency between subject and object."""
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
        """The type of target represented by this dependency."""
        INTERNAL = depend_pb2.INTERNAL
        EXTERNAL = depend_pb2.EXTERNAL
        ANY_TARGET = depend_pb2.ANY_TARGET

    def __init__(self, depend=None):
        self.data = depend
        self.stub = Cuebot.getStub('depend')

    def satisfy(self):
        """Satisfies the dependency.

        This sets any frames waiting on this dependency to the WAITING state.
        """
        self.stub.Satisfy(
            depend_pb2.DependSatisfyRequest(depend=self.data), timeout=Cuebot.Timeout)

    def unsatisfy(self):
        """Unsatisfies the dependency.

        This makes the dependency active again and sets matching frames to DEPEND.
        """
        self.stub.Unsatisfy(
            depend_pb2.DependUnsatisfyRequest(depend=self.data), timeout=Cuebot.Timeout)

    def id(self):
        """Returns the dependency's unique id.

        Dependencies are one of the only entities without a unique name so the unique ID is
        exposed to act as the name. This is mainly to make command line tools easier to use.

        :rtype:  str
        :return: the dependency's unique id"""
        return self.data.id

    def isInternal(self):
        """Returns whether the dependency is contained within a single job.

        :rtype:  bool
        :return: whether the dependency is contained within a single job
        """
        if self.data.depend_er_job == self.data.depend_on_job:
            return True
        return False

    def type(self):
        """Returns the type of dependency.

        :rtype: opencue_proto.depend_pb2.DependType
        :return: dependency type
        """
        return self.data.type

    def target(self):
        """Returns the target of the dependency, either internal or external.

        :rtype: opencue_proto.depend_pb2.DependTarget
        :return: dependency target type
        """
        return self.data.target

    def anyFrame(self):
        """Returns whether the depend is an any-frame depend.

        :rtype:  bool
        :return: whether the depend is an any-frame depend
        """
        return self.data.any_frame

    def isActive(self):
        """Returns whether the depend is active.

        :rtype:  bool
        :return: whether the depend is active
        """
        return self.data.active

    def dependErJob(self):
        """Returns the name of the job that is depending.

        :rtype:  str
        :return: name of the job that is depending"""
        return self.data.depend_er_job

    def dependErLayer(self):
        """Returns the name of the layer that is depending.

        :rtype:  str
        :return: name of the layer that is depending
        """
        return self.data.depend_er_layer

    def dependErFrame(self):
        """Returns the name of the frame that is depending.

        :rtype:  str
        :return: name of the frame that is depending
        """
        return self.data.depend_er_frame

    def dependOnJob(self):
        """Returns the name of the job to depend on.

        :rtype:  str
        :return: name of the job to depend on
        """
        return self.data.depend_on_job

    def dependOnLayer(self):
        """Returns the name of the layer to depend on.

        :rtype:  str
        :return: name of the layer to depend on
        """
        return self.data.depend_on_layer

    def dependOnFrame(self):
        """Returns the name of the frame to depend on.

        :rtype:  str
        :return: name of the frame to depend on
        """
        return self.data.depend_on_frame
