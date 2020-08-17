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

import ast
import functools

import googleapiclient.errors

import opencue.cloud.api


class GoogleCloudRequestException(opencue.cloud.api.CloudProviderException):
    """
    Handle all google cloud request related exceptions
    """

    def __init__(self, error_code, message):
        self.error_code = error_code
        self.message = message
        self.provider = "google"
        super(GoogleCloudRequestException, self).__init__(self.error_code, self.message, self.provider)


def googleRequestExceptionParser(request_function):

    def _decorator(*args, **kwargs):
        try:
            return request_function(*args, **kwargs)
        except googleapiclient.errors.HttpError as exception:
            content = ast.literal_eval(exception.content.decode("UTF-8"))
            raise GoogleCloudRequestException(error_code=content["error"]["code"],
                                              message=content["error"]["message"])

    return functools.wraps(request_function)(_decorator)
