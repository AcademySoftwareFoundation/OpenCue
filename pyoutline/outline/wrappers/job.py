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

"""
This module contains the job wrapper for the REST API.
"""

class Job(object):
    """This class contains the ice implementation related to a job."""

    def __init__(self, job=None):
        self.data = job

    def id(self):
        """Returns the id of the job.

        :rtype:  str
        :return: id of the job
        """
        if isinstance(self.data, dict):
            return self.data.get("id")
        return self.data.id

    def name(self):
        """Returns the name of the job.

        :rtype:  str
        :return: name of the job
        """
        if isinstance(self.data, dict):
            return self.data.get("name")
        return self.data.name
