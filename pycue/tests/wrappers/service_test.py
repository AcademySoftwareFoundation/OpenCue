#!/usr/bin/env python

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

"""Tests for `opencue.wrappers.service`."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest

import mock

from opencue_proto import service_pb2
import opencue.wrappers.service


TEST_SERVICE_NAME = 'testService'
TEST_MIN_GPUS = 2
TEST_MAX_GPUS = 7
TEST_MIN_GPU_MEMORY = 8 * 1024 * 1024 * 1024


@mock.patch('opencue.cuebot.Cuebot.getStub')
class ServiceTests(unittest.TestCase):

    def testDelete(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Delete.return_value = service_pb2.ServiceDeleteResponse()
        getStubMock.return_value = stubMock

        service = opencue.wrappers.service.Service(
            service_pb2.Service(name=TEST_SERVICE_NAME))
        service.delete()

        stubMock.Delete.assert_called_with(
            service_pb2.ServiceDeleteRequest(service=service.data), timeout=mock.ANY)

    def testCreateService(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.CreateService.return_value = service_pb2.ServiceCreateServiceResponse(
            service=service_pb2.Service(name=TEST_SERVICE_NAME, min_memory_increase=2097152))
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.service.Service(
            service_pb2.Service(name=TEST_SERVICE_NAME, min_memory_increase=2097152))
        service = wrapper.create()

        stubMock.CreateService.assert_called_with(
            service_pb2.ServiceCreateServiceRequest(data=wrapper.data), timeout=mock.ANY)
        self.assertEqual(wrapper.name(), service.name())
        self.assertEqual(wrapper.minMemoryIncrease(), service.minMemoryIncrease())

    def testCreateServiceMemError(self, getStubMock):
        service = opencue.wrappers.service.Service(service_pb2.Service(
            name=TEST_SERVICE_NAME))

        self.assertRaises(ValueError, service.create)

    def testGetDefaultServices(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetDefaultServices.return_value = service_pb2.ServiceGetDefaultServicesResponse(
            services=service_pb2.ServiceSeq(
                services=[service_pb2.Service(name=TEST_SERVICE_NAME)]))
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.service.Service()
        services = wrapper.getDefaultServices()

        stubMock.GetDefaultServices.assert_called_with(
            service_pb2.ServiceGetDefaultServicesRequest(), timeout=mock.ANY)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0].name(), TEST_SERVICE_NAME)

    def testGetService(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=service_pb2.Service(name=TEST_SERVICE_NAME))
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.service.Service()
        service = wrapper.getService(name=TEST_SERVICE_NAME)

        stubMock.GetService.assert_called_with(
            service_pb2.ServiceGetServiceRequest(name=TEST_SERVICE_NAME), timeout=mock.ANY)
        self.assertEqual(service.name(), TEST_SERVICE_NAME)

    def testUpdate(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.Update.return_value = service_pb2.ServiceUpdateResponse()
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.service.Service(service=service_pb2.Service(
            name=TEST_SERVICE_NAME, min_memory_increase=302))
        wrapper.update()

        stubMock.Update.assert_called_with(
            service_pb2.ServiceUpdateRequest(service=wrapper.data), timeout=mock.ANY)

    def testGpus(self, getStubMock):
        stubMock = mock.Mock()
        stubMock.GetService.return_value = service_pb2.ServiceGetServiceResponse(
            service=service_pb2.Service(name=TEST_SERVICE_NAME))
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.service.Service()
        service = wrapper.getService(name=TEST_SERVICE_NAME)
        self.assertEqual(service.minGpus(), 0)
        self.assertEqual(service.maxGpus(), 0)
        self.assertEqual(service.minGpuMemory(), 0)
        service.setMinGpus(TEST_MIN_GPUS)
        service.setMaxGpus(TEST_MAX_GPUS)
        service.setMinGpuMemory(TEST_MIN_GPU_MEMORY)
        self.assertEqual(service.minGpus(), TEST_MIN_GPUS)
        self.assertEqual(service.maxGpus(), TEST_MAX_GPUS)
        self.assertEqual(service.minGpuMemory(), TEST_MIN_GPU_MEMORY)

        stubMock.GetService.assert_called_with(
            service_pb2.ServiceGetServiceRequest(name=TEST_SERVICE_NAME), timeout=mock.ANY)
        self.assertEqual(service.name(), TEST_SERVICE_NAME)

    def testUpdateMemError(self, getStubMock):
        service = opencue.wrappers.service.Service(service=service_pb2.Service(
            name=TEST_SERVICE_NAME))

        self.assertRaises(ValueError, service.update)

    def testSetMinMemIncrease(self, getStubMock):
        service = opencue.wrappers.service.Service(
            service_pb2.Service(name=TEST_SERVICE_NAME,
                                min_memory_increase=2097152))

        self.assertRaises(ValueError, service.setMinMemoryIncrease, -1)
        self.assertRaises(ValueError, service.setMinMemoryIncrease, 0)

        service.setMinMemoryIncrease(12345678)
        self.assertEqual(service.minMemoryIncrease(), 12345678)


if __name__ == '__main__':
    unittest.main()
