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


from .api import CloudInstanceGroup

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials


# TODO : to be replaced with a better way to handle authentication
credentials = GoogleCredentials.get_application_default()
service = discovery.build('compute', 'v1', credentials=credentials)
project = 'gsoc-opencue-test-bed'
zone = 'us-central1-a'


class GoogleCloudGroup(CloudInstanceGroup):
    __signature__ = "google"

    def __init__(self, data):
        super(GoogleCloudGroup, self).__init__(data=data)
        self.operation_status = {}
        self.current_instances_size = 0
        self.target_size = 0

    @staticmethod
    def signature():
        return "google"

    @staticmethod
    def get_all():
        cigs = []
        request = service.instanceGroupManagers().list(project=project, zone=zone)
        while request is not None:
            response = request.execute()
            for instance_group_manager in response['items']:
                new_cig = GoogleCloudGroup(data=instance_group_manager)
                # Call get_instances to update the actual
                # number of instances running for the group
                new_cig.get_instances()
                cigs.append(new_cig)
            request = service.instanceGroupManagers().list_next(previous_request=request, previous_response=response)

        return cigs

    @staticmethod
    def create_managed_group(name, size, template):
        # TODO : Use request ID to handle multiple create button clicks
        template_url = template.get("selfLink")
        request_body = {
            "baseInstanceName": "{}-instance".format(name),
            "name": name,
            "targetSize": size,
            "instanceTemplate": template_url
        }
        request = service.instanceGroupManagers().insert(project=project, zone=zone, body=request_body)
        response = request.execute()
        return response

    def delete_cloud_group(self):
        request = service.instanceGroupManagers().delete(project=project, zone=zone,
                                                         instanceGroupManager=self.name)
        response = request.execute()
        self.operation_status["DELETION"] = "RUNNING"

    def get_instances(self):
        request = service.instanceGroupManagers().listManagedInstances(project=project, zone=zone,
                                                                       instanceGroupManager=self.name)
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

    @staticmethod
    def list_templates():
        templates = []
        request = service.instanceTemplates().list(project=project)
        while request is not None:
            response = request.execute()

            for instance_template in response['items']:
                templates.append(instance_template)

            request = service.instanceTemplates().list_next(previous_request=request, previous_response=response)

        return templates

    def resize(self, size=None):
        request = service.instanceGroupManagers().resize(project=project, zone=zone,
                                                         instanceGroupManager=self.name, size=size)
        response = request.execute()

    def status(self):
        """

        :return:
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
