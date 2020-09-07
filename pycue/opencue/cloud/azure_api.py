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

from azure.common.client_factory import get_client_from_cli_profile
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

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
        self.sku = self.data.sku

    def get_instances(self):
        instance_view = self.compute_client.virtual_machine_scale_sets.\
            get_instance_view(resource_group_name=self.resource_group, vm_scale_set_name=self.name())
        if instance_view.virtual_machine.statuses_summary:
            self.current_instances_size = instance_view.virtual_machine.statuses_summary[0].count
        else:
            self.current_instances_size = 0

    def resize(self, size=None):
        update_parameters = {
            "sku": {
                "name": self.sku.name,
                "tier": self.sku.tier,
                "capacity": size
            },
            "location": self.data.location
        }

        scale_set_update = self.compute_client.virtual_machine_scale_sets.create_or_update(
            self.resource_group,
            self.name(),
            update_parameters
        )

    def name(self):
        return self.scale_set_object.name

    def status(self):
        return str(self.scale_set_object.provisioning_state)

    def id(self):
        return self.scale_set_object.unique_id

    def current_group_size_info(self):
        return self.current_instances_size

    def delete_cloud_group(self):
        self.compute_client.virtual_machine_scale_sets.delete(
            resource_group_name=self.resource_group,
            vm_scale_set_name=self.name()
        )


class AzureCloudManager(opencue.cloud.api.CloudManager):

    def __init__(self):
        super(AzureCloudManager, self).__init__()
        self.credentials = None
        self.subscription_id = None
        self.compute_client = None
        self.resource_group_name = None
        self.network_client = None

    def signature(self):
        return "azure"

    def connect(self, cloud_resources_config):
        self.subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
        self.credentials = ServicePrincipalCredentials(client_id=os.environ['AZURE_CLIENT_ID'],
                                                       secret=os.environ['AZURE_CLIENT_SECRET'],
                                                       tenant=os.environ['AZURE_TENANT_ID'])
        self.compute_client = ComputeManagementClient(self.credentials, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credentials, self.subscription_id)
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

        virtual_networks = []
        for virtual_network in self.network_client.virtual_networks.list(self.resource_group_name):
            virtual_networks.append(virtual_network)

        subnets = []
        for subnet in self.network_client.subnets.list(self.resource_group_name, virtual_networks[0].name):
            subnets.append(subnet)

        naming_infix = "{}_Infix".format(template.name)
        vmss_parameters = {
            "sku": {
                "name": "Standard_DS1_v2",
                "tier": "Standard",
                "capacity": size
            },
            "upgrade_policy": {
                "mode": "Manual"
            },
            "location": template.location,
            "virtual_machine_profile": {
                "storage_profile": {
                    "image_reference": {
                        "id": template.id,
                        "resource_group": self.resource_group_name
                    }
                },
                "network_profile": {
                    "network_interface_configurations": [{
                        "name": naming_infix + "nic",
                        "primary": True,
                        "ip_configurations": [{
                            "name": naming_infix + "ipconfig",
                            "subnet": {
                                "id": subnets[0].id
                            }
                        }]
                    }]
                }
            }
        }

        scale_set_update = self.compute_client.virtual_machine_scale_sets.create_or_update(
            self.resource_group_name,
            name,
            vmss_parameters
        )

        # TODO: Poller in Azure is much different from GCE. It's a blocking call if we have to return the result
        return 1

    def list_templates(self):
        pass

    def list_galleries_in_resource_group(self):
        galleries = []
        for gallery in self.compute_client.galleries.list_by_resource_group(self.resource_group_name):
            galleries.append(gallery)

        return galleries

    def list_image_definitions_by_gallery(self, gallery_name):
        image_definitions = []
        for image_definition in self.compute_client.gallery_images.list_by_gallery(self.resource_group_name,
                                                                                   gallery_name):
            image_definitions.append(image_definition)

        return image_definitions
