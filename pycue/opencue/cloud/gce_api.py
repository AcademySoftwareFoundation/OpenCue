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

import googleapiclient.discovery
import oauth2client.client

import opencue.cloud.api
import opencue.cloud.gce_exception_util


class GoogleCloudGroup(opencue.cloud.api.CloudInstanceGroup):
    __signature__ = "google"

    def __init__(self, data, connection_manager):
        super(GoogleCloudGroup, self).__init__(data=data)
        self.current_instances_size = 0
        self.target_size = 0
        self.connection_manager = connection_manager

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def delete_cloud_group(self):
        request = self.connection_manager.service.instanceGroupManagers().delete(
            project=self.connection_manager.project, zone=self.connection_manager.zone,
            instanceGroupManager=self.name())
        response = request.execute()

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def get_instances(self):
        """
        :return: (list) of dictionaries. Currently only the size of the list matters
        """
        request = self.connection_manager.service.instanceGroupManagers().listManagedInstances(
            project=self.connection_manager.project, zone=self.connection_manager.zone,
            instanceGroupManager=self.name())
        response = request.execute()
        self.instances = response.get("managedInstances", [])

    def current_group_size_info(self):
        """
        Used by the widget to show the current state of the number of instances
        Default : len(self.instances)
        If currentActions has "creating" key more than 0 -> Resizing up
        If currentActions has "deleting" key more than 0 -> Resizing down
        :return:
        """

        if self.data["currentActions"]["creating"] > 0:
            self.current_instances_size = self.data["currentActions"]["none"]
        elif self.data["currentActions"]["deleting"] > 0:
            self.current_instances_size = 0
            for action in self.data["currentActions"]:
                self.current_instances_size += self.data["currentActions"][action]
        else:
            self.current_instances_size = len(self.instances)

        self.target_size = self.data["targetSize"]

        if self.current_instances_size == self.target_size:
            return self.current_instances_size
        else:
            return "{current_size} -> {target_size}".format(current_size=self.current_instances_size,
                                                            target_size=self.target_size)

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def resize(self, size=None):
        """
        :param size: (int)
        :return:
        """
        request = self.connection_manager.service.instanceGroupManagers().resize(
            project=self.connection_manager.project, zone=self.connection_manager.zone,
            instanceGroupManager=self.name(), size=size)
        response = request.execute()

    def name(self):
        return self.data["name"]

    def status(self):
        """
        Use the info gained from group size info to customize status column
        :return: (str) Of the descriptive status
        """
        if self.data["status"].get("isStable"):
            return "STABLE"
        else:
            if self.target_size > self.current_instances_size:
                return "BUSY: SCALING UP"
            elif self.target_size < self.current_instances_size:
                return "BUSY: SCALING DOWN"

            return "BUSY: IN OPERATION"

    def id(self):
        return self.data["id"]


class GoogleCloudManager(opencue.cloud.api.CloudManager):

    def __init__(self):
        super(GoogleCloudManager, self).__init__()
        self.project = None
        self.zone = None
        self.credentials = None
        self.service = None

    def signature(self):
        return "google"

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def connect(self, cloud_resources_config):
        """
        Connect to the GCE : For now with application defaults
        :return:
        """

        self.project = cloud_resources_config.get('gce_project_name', '')
        self.zone = cloud_resources_config.get('gce_project_zone_name', '')
        self.credentials = oauth2client.client.GoogleCredentials.get_application_default()
        self.service = googleapiclient.discovery.build('compute', 'v1', credentials=self.credentials)

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def get_all_groups(self):
        cigs = []
        request = self.service.instanceGroupManagers().list(project=self.project, zone=self.zone)
        while request is not None:
            response = request.execute()
            for instance_group_manager in response['items']:
                new_cig = GoogleCloudGroup(data=instance_group_manager, connection_manager=self)
                # Call get_instances to update the actual
                # number of instances running for the group
                new_cig.get_instances()
                cigs.append(new_cig)
            request = self.service.instanceGroupManagers().list_next(previous_request=request,
                                                                     previous_response=response)

        return cigs

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def create_managed_group(self, name, size, template):
        """

        :param name: (str) name from input
        :param size: (int) size from input
        :param template: (dict) of the template object
        :return:
        """
        template_url = template.get("selfLink")
        request_body = {
            "baseInstanceName": "{}-instance".format(name),
            "name": name,
            "targetSize": size,
            "instanceTemplate": template_url
        }
        request = self.service.instanceGroupManagers().insert(project=self.project, zone=self.zone, body=request_body)
        response = request.execute()
        return response

    @opencue.cloud.gce_exception_util.googleRequestExceptionParser
    def list_templates(self):
        """
        :return: (list) of template objects
        """
        templates = []
        request = self.service.instanceTemplates().list(project=self.project)
        while request is not None:
            response = request.execute()

            for instance_template in response['items']:
                templates.append(instance_template)

            request = self.service.instanceTemplates().list_next(previous_request=request, previous_response=response)

        return templates

