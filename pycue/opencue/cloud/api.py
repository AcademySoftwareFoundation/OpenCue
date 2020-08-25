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
        :type size: int
        :param size: The target size of group to be scaled up/down to
        """

    @abc.abstractmethod
    def name(self):
        """
        :return: Name of the cloud group
        """

    @abc.abstractmethod
    def status(self):
        """
        :return: Returns the status of any operation made on the group. By default "STABLE"
        Each provider has it's own way of implementing status of a particular group
        """

    @abc.abstractmethod
    def id(self):
        """
        :return: Used to treat a CloudInstanceGroup object similar to a gRPC object for threadpool usage
        """

    @abc.abstractmethod
    def delete_cloud_group(self):
        """
        Delete the cloud group from the provider
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
        :return: (list) Returns the list of registered cloud provider's manager classes
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
        :return: Returns the name of the provider
        """

    @abc.abstractmethod
    def create_managed_group(self, name, size, template):
        """
        Creates a cloud group with the given template/image from cloud
        :type name: str
        :param name: A unique name that is to be associated with the cloud group
        :type size: int
        :param size: The initial number of instances for the cloud group
        :type: template: str/template/vm image object according to the implementation API
        :param template: Template/Image needed to create the group
        """

    @abc.abstractmethod
    def get_all_groups(self):
        """
        Get all the cloud groups associated with the provider
        :return: list of cloud provider's instance group objects
        """

    @abc.abstractmethod
    def connect(self, cloud_resources_config):
        """
        Abstract method that will implement connecting to the cloud provider
        :type cloud_resources_config: dict
        :param cloud_resources_config: YAML config object as a dictionary to access cloud API setup information
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
