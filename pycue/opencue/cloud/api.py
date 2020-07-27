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

import abc


class CloudInstanceGroup(object):
    def __init__(self, data):
        self.data = data
        self.name = self.data["name"]
        self.instances = []

    @staticmethod
    @abc.abstractmethod
    def get_all():
        """
        Get all the cloud groups associated with the provider
        :return:
        """


    @staticmethod
    @abc.abstractmethod
    def create_managed_group(name, size, template):
        """
        Creates a cloud group with the given template/image from cloud
        :return:
        """

    @abc.abstractmethod
    def get_instances(self):
        """
        Get all instances of the current group
        :return: List of instances
        TODO: Check how to make it a consistent format across CSPs
        """

    @abc.abstractmethod
    def resize(self, size=None):
        """
        Resizes the group to the given number of instances
        :return:
        """

    @abc.abstractmethod
    def status(self):
        """

        :return:
        """

    @abc.abstractmethod
    def id(self):
        """
        Used to treat a CloudInstanceGroup object similar to a gRPC object for threadpool usage
        :return:
        """

    @abc.abstractmethod
    def delete_cloud_group(self):
        """
        Delete the cloud group from the provider
        :return:
        """

    @abc.abstractmethod
    def current_group_size_info(self):
        """
        Implement this method to show the state of the instances for the group
        If resizing ongoing: current_size -> target_size
        If not: current_size (or) just the len(instances)
        :return:
        """


class CloudManager(object):
    def __init__(self):
        pass

    @staticmethod
    def get_registered_providers():
        """

        :return:
        """
        # TODO : Better way to register plugins
        # For now just return the GCE group class
        from .gce_api import GoogleCloudGroup
        return [GoogleCloudGroup]
