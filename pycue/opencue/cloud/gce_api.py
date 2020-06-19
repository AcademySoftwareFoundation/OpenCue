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

credentials = GoogleCredentials.get_application_default()
service = discovery.build('compute', 'v1', credentials=credentials)
project = 'gsoc-opencue-test-bed'
zone = 'us-central1-a'


class GoogleCloudGroup(CloudInstanceGroup):

    def __init__(self, data):
        data["cloud_provider"] = "google"
        super(GoogleCloudGroup, self).__init__(data=data)

    @staticmethod
    def get_all():
        cigs = []
        request = service.instanceGroupManagers().list(project=project, zone=zone)
        while request is not None:
            response = request.execute()
            for instance_group_manager in response['items']:
                cigs.append(GoogleCloudGroup(data=instance_group_manager))
            request = service.instanceGroupManagers().list_next(previous_request=request, previous_response=response)

        return cigs

    @staticmethod
    def create_managed_group():
        pass

    def get_instances(self):
        pass

    def resize(self, number=None):
        pass

    def status(self):
        pass


