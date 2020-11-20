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



"""
Project: opencue Library

Module: service.py - opencue Library implementation of a service

"""

import grpc

from opencue.compiled_proto import service_pb2
from opencue.cuebot import Cuebot


class Service(object):
    """This class contains the grpc implementation related to a Service."""

    def __init__(self, service=None):
        self.data = service or service_pb2.Service()
        self.stub = Cuebot.getStub('service')

    def create(self):
        response = self.stub.CreateService(
            service_pb2.ServiceCreateServiceRequest(data=self.data),
            timeout=Cuebot.Timeout)
        return Service(response.service)

    def delete(self):
        return self.stub.Delete(
            service_pb2.ServiceDeleteRequest(service=self.data),
            timeout=Cuebot.Timeout)

    @staticmethod
    def getDefaultServices():
        response = Cuebot.getStub('service').GetDefaultServices(
            service_pb2.ServiceGetDefaultServicesRequest(),
            timeout=Cuebot.Timeout)
        return [Service(data) for data in response.services.services]

    @staticmethod
    def getService(name):
        try:
            response = Cuebot.getStub('service').GetService(
                service_pb2.ServiceGetServiceRequest(name=name),
                timeout=Cuebot.Timeout)
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                return None
            raise e
        return Service(response.service)

    def update(self):
        return self.stub.Update(
            service_pb2.ServiceUpdateRequest(service=self.data),
            timeout=Cuebot.Timeout)

    def id(self):
        """Returns the id of the service.

        :rtype:  str
        :return: Frame uuid"""
        return self.data.id

    def name(self):
        """Returns the name of the service.

        :rtype:  str
        :return: service name"""
        return self.data.name

    def setName(self, name):
        """Set the name field of the message.

        :type: string
        :param: name to set"""
        self.data.name = name

    def threadable(self):
        """Returns if the service is threadable.

        :rtype:  bool
        :return: is service threadable"""
        return self.data.threadable

    def setThreadable(self, threadable):
        """Set the threadabel field of the message.

        :type: bool
        :param: whether or not the service should be threadable"""
        self.data.threadable = threadable

    def minCores(self):
        """Returns the min_cores of the service.

        :rtype:  int
        :return: min_cores"""
        return self.data.min_cores

    def setMinCores(self, minCores):
        """Set the minCores field of the message.

        :type: int
        :param: min_cores"""
        self.data.min_cores = minCores

    def maxCores(self):
        """Returns the max_cores of the service.

        :rtype:  int
        :return: max_cores"""
        return self.data.max_cores

    def setMaxCores(self, maxCores):
        """Set the maxCores field of the message.

        :type: int
        :param: max_cores"""
        self.data.max_cores = maxCores

    def minMemory(self):
        """Returns the min_memory of the service.

        :rtype:  int
        :return: min_memory"""
        return self.data.min_memory

    def setMinMemory(self, minMemory):
        """Set the minMemory field of the message.

        :type: int
        :param: min_memory"""
        self.data.min_memory = minMemory

    def minGpu(self):
        """Returns the min_gpu of the service.

        :rtype:  int
        :return: min_gpu"""
        return self.data.min_gpu

    def setMinGpu(self, minGpu):
        """Set the minGpu field of the message.

        :type: int
        :param: min_gpu"""
        self.data.min_gpu = minGpu

    def tags(self):
        """Returns the list of tags for the service.

        :rtype:  list<string>
        :return: tags"""
        return self.data.tags

    def setTags(self, tags):
        """Clear and set the tags.
        :type: list<string>
        :param: list of tags to set"""
        self.data.tags[:] = tags


class ServiceOverride(object):
    def __init__(self, serviceOverride=None):
        if serviceOverride:
            self.id = serviceOverride.id
            self.data = serviceOverride.data or service_pb2.Service().data
        else:
            defaultServiceOverride = service_pb2.ServiceOverride()
            self.id = defaultServiceOverride.id
            self.data = defaultServiceOverride.data
        
        self.stub = Cuebot.getStub("serviceOverride")

    def delete(self):
        self.stub.Delete(
            service_pb2.ServiceOverrideDeleteRequest(service=self.data),
            timeout=Cuebot.Timeout)
    
    def update(self):
        self.stub.Update(
            service_pb2.ServiceOverrideUpdateRequest(service=self.data),
            timeout=Cuebot.Timeout)
