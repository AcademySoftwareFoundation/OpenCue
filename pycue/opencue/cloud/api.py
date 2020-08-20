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

import abc


class CloudInstanceGroup(object):
    def __init__(self, data):
        self.data = data
        self.instances = []

    @abc.abstractmethod
    def get_instances(self):
        """
        Gets all instances of the current group
        :return: (list) List of instances
        """

    @abc.abstractmethod
    def resize(self, size=None):
        """
        Resizes the group to the given number of instances
        :param size: (int) The target size of group to be scaled up/down to
        :return:
        """

    @abc.abstractmethod
    def name(self):
        """
        Name of the cloud group
        :return:
        """

    @abc.abstractmethod
    def status(self):
        """
        Returns the status of any operation made on the group. By default "STABLE"
        Each provider has it's own way of implementing status of a particular group
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
        from .gce_api import GoogleCloudManager
        from .azure_api import AzureCloudManager
        providers = [GoogleCloudManager, AzureCloudManager]
        managers_instances = []
        for provider in providers:
            manager_object = provider()
            managers_instances.append(manager_object)

        return managers_instances

    @abc.abstractmethod
    def signature(self):
        """
        Returns the name of the provider
        :return:
        """

    @abc.abstractmethod
    def create_managed_group(self, name, size, template):
        """
        Creates a cloud group with the given template/image from cloud
        :param name: (str) A unique name that is to be associated with the cloud group
        :param size: (int) The initial number of instances for the cloud group
        :param template: (str/template/vm image object according to the implementation API) Template/Image needed to
        create the group
        :return:
        """

    @abc.abstractmethod
    def get_all_groups(self):
        """
        Get all the cloud groups associated with the provider
        :return:
        """

    @abc.abstractmethod
    def connect(self):
        """
        Abstract method that will implement connecting to the cloud provider
        :return:
        """


class CloudProviderException(Exception):
    """
    Base class for handling exceptions when making cloud requests
    """

    def __init__(self, error_code, message, provider=None):
        self.provider = provider
        self.message = message
        self.error_code = error_code

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "<Cloud Provider: {} {} exception: {}".format(self.provider, self.error_code, self.message)
