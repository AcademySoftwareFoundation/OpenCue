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


import mock
import unittest
import os

import opencue
from opencue.cloud.gce_api import GoogleCloudGroup
from googleapiclient import discovery
from googleapiclient.http import HttpMock, HttpRequestMock

TEST_CLOUD_GROUP_NAME = "test-group-main"
PROJECT_NAME = "test-gce-project"
ZONE_NAME = "test-zone-name"
GOOGLE_RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "google-test-resources")
TEST_INSTANCE_TEMPLATE_NAME = "test-instance-template"


class GoogleCloudGroupTest(unittest.TestCase):

    def setUp(self):
        # Use the HttpMock module to build the mock service object
        self.http = HttpMock(os.path.join(GOOGLE_RESOURCES_DIR, "compute-discovery.json"),
                             {'status': '200'})
        api_key = "test_api_key"
        self.service = discovery.build('compute', 'v1', http=self.http, developerKey=api_key)

    # Mock proc call for the HttpRequestMock
    def mock_exec_instancegroup_list(self, resp, content):
        request = self.service.instanceGroupManagers().list(project=PROJECT_NAME, zone=ZONE_NAME)
        http_request = HttpMock(os.path.join(GOOGLE_RESOURCES_DIR, "compute-instancegroups.json"),
                                {'status': '200'})
        response = request.execute(http=http_request)
        return response

    def mock_exec_templates_list(self, resp, content):
        request = self.service.instanceGroupManagers().list(project=PROJECT_NAME, zone=ZONE_NAME)
        http_request = HttpMock(os.path.join(GOOGLE_RESOURCES_DIR, "compute-instancetemplates.json"),
                                {'status': '200'})
        response = request.execute(http=http_request)
        return response

    @mock.patch('opencue.cloud.gce_api.service')
    def test_get_all(self, serviceMock):
        serviceMock.instanceGroupManagers().list.return_value = HttpRequestMock(resp=None,
                                                                                content="",
                                                                                postproc=self.mock_exec_instancegroup_list)
        serviceMock.instanceGroupManagers().list_next.return_value = None
        gce_groups = GoogleCloudGroup.get_all()

        # Test name and id data
        self.assertEqual(["test-group-main"], [c.name for c in gce_groups])
        self.assertEqual(["7460673806684034108"], [c.id() for c in gce_groups])

    @mock.patch('opencue.cloud.gce_api.service')
    def test_list_templates(self, serviceMock):
        serviceMock.instanceTemplates().list.return_value = HttpRequestMock(resp=None,
                                                                            content="",
                                                                            postproc=self.mock_exec_templates_list)
        serviceMock.instanceTemplates().list_next.return_value = None
        instance_templates = GoogleCloudGroup.list_templates()

        self.assertEqual([TEST_INSTANCE_TEMPLATE_NAME], [template["name"] for template in instance_templates])