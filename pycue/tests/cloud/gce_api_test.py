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
    def test_get_all_groups(self, connect_mock):
        # __getitem__.side_effect is used to make the return value of mock
        # list call subscriptable since the actual code uses it like a dictionary
        test_response = {
            "items": [
                {
                    "name": TEST_CLOUD_GROUP_NAME,
                    "id": 1234
                }
            ]
        }
        connect_mock.return_value = None
        manager = opencue.cloud.gce_api.GoogleCloudManager()
        manager.service = mock.MagicMock()
        manager.service.instanceGroupManagers().list.return_value.execute().__getitem__.side_effect =\
            test_response.__getitem__
        manager.service.instanceGroupManagers().list_next.return_value = None
        groups = manager.get_all_groups()

        self.assertIsInstance(groups[0], opencue.cloud.gce_api.GoogleCloudGroup)
        self.assertEqual([TEST_CLOUD_GROUP_NAME], [g.name for g in groups])
        self.assertEqual([1234], [g.id() for g in groups])

    @mock.patch.object(opencue.cloud.gce_api.GoogleCloudManager, "connect", autospec=True)
    def test_list_templates(self, connect_mock):
        # Accessing the 'name' key should be possible
        test_response = {
            "items": [
                {
                    "name": "rqd-test"
                }
            ]
        }
        connect_mock.return_value = None
        manager = opencue.cloud.gce_api.GoogleCloudManager()
        manager.service = mock.MagicMock()
        manager.service.instanceTemplates().list.return_value.execute().__getitem__.side_effect =\
            test_response.__getitem__
        manager.service.instanceTemplates().list_next.return_value = None
        templates = manager.list_templates()

        self.assertEqual(["rqd-test"], [t["name"] for t in templates])

    def test_create_managed_group(self):
        # TODO: Test if create is called with the correct parameters
        pass


class GoogleCloudGroupTest(unittest.TestCase):

    def setUp(self):
        self.connection_manager_mock = mock.MagicMock()
        self.test_group_data = {
            "name": TEST_CLOUD_GROUP_NAME,
            "id": 1234
        }

    def test_get_instances(self):
        test_managed_instances_data = [
            {
                "name": "instance-1",
                "id": 4321
            },
            {
                "name": "instance-2",
                "id": 9876
            }
        ]

        self.connection_manager_mock.service.instanceGroupManagers().listManagedInstances.return_value.execute.return_value.\
            get.return_value = test_managed_instances_data

        test_group = opencue.cloud.gce_api.GoogleCloudGroup(data=self.test_group_data,
                                                            connection_manager=self.connection_manager_mock)
        test_group.get_instances()

        self.assertEqual(2, len(test_group.instances))
        self.assertEqual(["instance-1", "instance-2"], [i["name"] for i in test_group.instances])
        self.connection_manager_mock.service.instanceGroupManagers().listManagedInstances.assert_called_with(
            project=mock.ANY, zone=mock.ANY, instanceGroupManager=TEST_CLOUD_GROUP_NAME
        )

    def test_delete_cloud_group(self):

        test_group = opencue.cloud.gce_api.GoogleCloudGroup(data=self.test_group_data,
                                                            connection_manager=self.connection_manager_mock)

        test_group.delete_cloud_group()

        self.connection_manager_mock.service.instanceGroupManagers().delete.assert_called_with(
            project=mock.ANY, zone=mock.ANY, instanceGroupManager=TEST_CLOUD_GROUP_NAME
        )

    def test_resize(self):
        test_group = opencue.cloud.gce_api.GoogleCloudGroup(data=self.test_group_data,
                                                            connection_manager=self.connection_manager_mock)

        test_group.resize(size=3)

        self.connection_manager_mock.service.instanceGroupManagers().resize.assert_called_with(
            project=mock.ANY, zone=mock.ANY, instanceGroupManager=TEST_CLOUD_GROUP_NAME, size=3
        )

