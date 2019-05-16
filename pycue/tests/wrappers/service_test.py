#!/usr/bin/env python

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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import mock
import unittest

import opencue
from opencue.compiled_proto import service_pb2


TEST_SERVICE_NAME = 'testService'


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
            service=service_pb2.Service(name=TEST_SERVICE_NAME))
        getStubMock.return_value = stubMock

        wrapper = opencue.wrappers.service.Service(
            service_pb2.Service(name=TEST_SERVICE_NAME))
        service = wrapper.create()

        stubMock.CreateService.assert_called_with(
            service_pb2.ServiceCreateServiceRequest(data=wrapper.data), timeout=mock.ANY)
        self.assertEqual(wrapper.name(), service.name())

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
            name=TEST_SERVICE_NAME))
        wrapper.update()

        stubMock.Update.assert_called_with(
            service_pb2.ServiceUpdateRequest(service=wrapper.data), timeout=mock.ANY)


if __name__ == '__main__':
    unittest.main()
