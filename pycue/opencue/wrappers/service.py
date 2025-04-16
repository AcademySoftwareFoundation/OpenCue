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

"""Module for classes related to services."""

import grpc

from opencue_proto import service_pb2
from opencue.cuebot import Cuebot


class Service(object):
    """This class contains the grpc implementation related to a Service."""

    def __init__(self, service=None):
        self.data = service or service_pb2.Service()
        self.stub = Cuebot.getStub('service')

    def create(self):
        """Creates a service in the database using the current instance data."""
        # min_memory_increase has to be greater than 0.
        if self.data.min_memory_increase <= 0:
            raise ValueError("Minimum memory increase must be > 0")

        response = self.stub.CreateService(
            service_pb2.ServiceCreateServiceRequest(data=self.data),
            timeout=Cuebot.Timeout)
        return Service(response.service)

    def delete(self):
        """Deletes the service."""
        return self.stub.Delete(
            service_pb2.ServiceDeleteRequest(service=self.data),
            timeout=Cuebot.Timeout)

    @staticmethod
    def getDefaultServices():
        """Returns the default services."""
        response = Cuebot.getStub('service').GetDefaultServices(
            service_pb2.ServiceGetDefaultServicesRequest(),
            timeout=Cuebot.Timeout)
        return [Service(data) for data in response.services.services]

    @staticmethod
    def getService(name):
        """Returns a service by name.

        :type  name: str
        :param name: service name to find
        """
        try:
            response = Cuebot.getStub('service').GetService(
                service_pb2.ServiceGetServiceRequest(name=name),
                timeout=Cuebot.Timeout)
        except grpc.RpcError as e:
            # pylint: disable=no-member
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            # pylint: enable=no-member
            raise e
        return Service(response.service)

    def update(self):
        """Updates the service database record with the current instance data."""
        # min_memory_increase has to be greater than 0.
        if self.data.min_memory_increase <= 0:
            raise ValueError("Minimum memory increase must be > 0")

        return self.stub.Update(
            service_pb2.ServiceUpdateRequest(service=self.data),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the service.

        :rtype:  str
        :return: service id
        """
        return self.data.id

    def name(self):
        """Returns the name of the service.

        :rtype:  str
        :return: service name
        """
        return self.data.name

    def setName(self, name):
        """Sets the service name.

        :type: string
        :param: new service name
        """
        self.data.name = name

    def threadable(self):
        """Returns whether the service is threadable.

        :rtype:  bool
        :return: whether service is threadable
        """
        return self.data.threadable

    def setThreadable(self, threadable):
        """Sets the threadable field of the service.

        :type:  bool
        :param: whether or not the service should be threadable
        """
        self.data.threadable = threadable

    def minCores(self):
        """Returns the minimum cores of the service.

        :rtype:  int
        :return: min cores
        """
        return self.data.min_cores

    def setMinCores(self, minCores):
        """Sets the minimum cores of the service.

        :type: int
        :param: new min cores
        """
        self.data.min_cores = minCores

    def maxCores(self):
        """Returns the maximum cores of the service.

        :rtype:  int
        :return: max cores
        """
        return self.data.max_cores

    def setMaxCores(self, maxCores):
        """Sets the maximum cores of the service.

        :type: int
        :param: new max cores
        """
        self.data.max_cores = maxCores

    def minMemory(self):
        """Returns the minimum memory of the service.

        :rtype:  int
        :return: min memory
        """
        return self.data.min_memory

    def setMinMemory(self, minMemory):
        """Sets the minimum memory field of the service.

        :type: int
        :param: new min memory
        """
        self.data.min_memory = minMemory

    def minGpus(self):
        """Returns the minimum gpus of the service.

        :rtype:  int
        :return: min gpus
        """
        return self.data.min_gpus

    def setMinGpus(self, minGpus):
        """Sets the minimum gpus of the service.

        :type: int
        :param: new min gpus
        """
        self.data.min_gpus = minGpus

    def maxGpus(self):
        """Returns the maximum gpus of the service.

        :rtype:  int
        :return: max gpus
        """
        return self.data.max_gpus

    def setMaxGpus(self, maxGpus):
        """Sets the maximum gpus of the service.

        :type: int
        :param: new max gpus
        """
        self.data.max_gpus = maxGpus

    def minGpuMemory(self):
        """Returns the minimum gpu memory of the service.

        :rtype:  int
        :return: min gpu memory
        """
        return self.data.min_gpu_memory

    def setMinGpuMemory(self, minGpuMemory):
        """Sets the minimum gpu memory of the service.

        :type: int
        :param: new min gpu memory
        """
        self.data.min_gpu_memory = minGpuMemory

    def tags(self):
        """Returns the list of tags for the service.

        :rtype:  list<string>
        :return: list of service tags
        """
        return self.data.tags

    def setTags(self, tags):
        """Clears and sets the service tags.

        :type:  list<string>
        :param: new list of service tags
        """
        self.data.tags[:] = tags

    def timeout(self):
        """Gets the default service timeout."""
        return self.data.timeout

    def setTimeout(self, timeout):
        """Sets the default service timeout."""
        self.data.timeout = timeout

    def timeoutLLU(self):
        """Gets the default service LLU timeout."""
        return self.data.timeout

    def setTimeoutLLU(self, timeout_llu):
        """Sets the default service LLU timeout."""
        self.data.timeout_llu = timeout_llu

    def minMemoryIncrease(self):
        """Gets the default service minimum memory increment"""
        return self.data.min_memory_increase

    def setMinMemoryIncrease(self, min_memory_increase):
        """Sets the default service minimum memory increment"""
        if min_memory_increase > 0:
            self.data.min_memory_increase = min_memory_increase
        else:
            raise ValueError("Minimum memory increase must be > 0")

class ServiceOverride(object):
    """Represents a display override of a service assigned to a show"""
    def __init__(self, serviceOverride=None):
        defaultServiceOverride = service_pb2.ServiceOverride()
        # pylint: disable=no-member
        self.id = defaultServiceOverride.id
        self.data = defaultServiceOverride.data
        if serviceOverride:
            self.id = serviceOverride.id
            self.data = serviceOverride.data or service_pb2.Service().data
        self.stub = Cuebot.getStub("serviceOverride")
        # pylint: enable=no-member

    def delete(self):
        """Remove service override"""
        self.stub.Delete(
            service_pb2.ServiceOverrideDeleteRequest(service=self.data),
            timeout=Cuebot.Timeout)

    def update(self):
        """Commit a ServiceOverride change to the database"""
        self.stub.Update(
            service_pb2.ServiceOverrideUpdateRequest(service=self.data),
            timeout=Cuebot.Timeout)
