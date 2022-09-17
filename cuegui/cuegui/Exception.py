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

"""Custom exception classes for CueGUI application errors."""


class CueGuiException(Exception):
    """Base class for all CueGUI exceptions.

    Note that this class does NOT inherit from opencue.exception.CueException, so that error handling
    code can easily distinguish between API errors and CueGUI errors.
    """


class ApplicationNotRunningException(CueGuiException):
    """Raised when the CueGUI application has not been instantiated but is required to be."""

    def __init__(self, message='the CueGUI application has not been initialized, create_app() must be called first'):
        super().__init__(message)
