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


import mock
import unittest
import os

import opencue
import opencue.cloud.gce_api

TEST_CLOUD_GROUP_NAME = "test-group-main"
TEST_INSTANCE_TEMPLATE_NAME = "test-instance-template"


class GoogleCloudManagerTest(unittest.TestCase):

    def setUp(self):
        pass

    @mock.patch.object(opencue.cloud.gce_api.GoogleCloudManager, "connect", autospec=True)
    def test_get_all_groups(self, connectMock):
        test_response = {
            "items": [
                {
                    "name": TEST_CLOUD_GROUP_NAME,
                    "id": 1234
                }
            ]
        }
        connectMock.return_value = None
        manager = opencue.cloud.gce_api.GoogleCloudManager()
        manager.service = mock.MagicMock()
        manager.service.instanceGroupManagers().list.return_value.execute().__getitem__.side_effect =\
            test_response.__getitem__
        manager.service.instanceGroupManagers().list_next.return_value = None
        groups = manager.get_all_groups()

        self.assertEqual([TEST_CLOUD_GROUP_NAME], [g.name for g in groups])
        self.assertEqual([1234], [g.id() for g in groups])

