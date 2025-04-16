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

"""Module for classes related to Render Partition."""

from opencue_proto import renderPartition_pb2
from opencue.cuebot import Cuebot


class RenderPartition(object):
    """This class contains the grpc implementation related to a Task."""

    def __init__(self, render_partition=None):
        self.data = render_partition
        self.stub = Cuebot.getStub('renderPartition')

    def delete(self):
        """Deletes the render partition."""
        self.stub.Delete(renderPartition_pb2.RenderPartDeleteRequest(
            render_partition=self.data), timeout=Cuebot.Timeout)


    def setMaxResources(self, cores, memory, gpuMemory, gpuCores):
        """Deletes the render partition."""
        self.stub.SetMaxResources(renderPartition_pb2.RenderPartSetMaxResourcesRequest(
            render_partition=self.data,
            cores=cores,
            memory=memory,
            gpu_memory=gpuMemory,
            gpus=gpuCores
        ), timeout=Cuebot.Timeout)
