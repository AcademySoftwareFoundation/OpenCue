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

import os

from azure.mgmt.compute import ComputeManagementClient
from azure.common.credentials import ServicePrincipalCredentials

import opencue.cloud.api


class AzureCloudGroup(opencue.cloud.api.CloudInstanceGroup):
    __signature__ = "azure"

    def __init__(self, data, resource_group, compute_client):
        super(AzureCloudGroup, self).__init__(data=data)
        self.scale_set_object = data
        self.current_instances_size = 0
        self.target_size = 0
        self.compute_client = compute_client
        self.resource_group = resource_group
        self.current_instances_size = 0

    def get_instances(self):
        instance_view = self.compute_client.virtual_machine_scale_sets.\
            get_instance_view(resource_group_name=self.resource_group, vm_scale_set_name=self.name())
        if instance_view.virtual_machine.statuses_summary:
            self.current_instances_size = instance_view.virtual_machine.statuses_summary[0].count
        else:
            self.current_instances_size = 0

    def resize(self, size=None):
        pass

    def name(self):
        return self.scale_set_object.name

    def status(self):
        return str(self.scale_set_object.provisioning_state)

    def id(self):
        return self.scale_set_object.unique_id

    def current_group_size_info(self):
        return self.current_instances_size


class AzureCloudManager(opencue.cloud.api.CloudManager):

    def __init__(self):
        super(AzureCloudManager, self).__init__()
        self.credentials = None
        self.subscription_id = None
        self.compute_client = None
        self.resource_group_name = None

    def signature(self):
        return "azure"

    def connect(self):
        self.subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
        self.credentials = ServicePrincipalCredentials(client_id=os.environ['AZURE_CLIENT_ID'],
                                                       secret=os.environ['AZURE_CLIENT_SECRET'],
                                                       tenant=os.environ['AZURE_TENANT_ID'])
        self.compute_client = ComputeManagementClient(self.credentials, self.subscription_id)
        self.resource_group_name = os.environ["AZURE_RESOURCE_GROUP_NAME"]

    def get_all_groups(self):
        scale_sets = []
        for scale_set in self.compute_client.virtual_machine_scale_sets.list(resource_group_name=
                                                                             self.resource_group_name):
            new_scale_set = AzureCloudGroup(data=scale_set,
                                            resource_group=self.resource_group_name,
                                            compute_client=self.compute_client)
            new_scale_set.get_instances()
            scale_sets.append(new_scale_set)

        return scale_sets

    def create_managed_group(self, name, size, template):
        pass

    def list_templates(self):
        pass
