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


"""Outline exception hierarchy"""

__all__ = ["OutlineException",
           "LayerException",
           "ShellCommandFailureException",
           "SessionException",
           "FileSpecException",
           "FailImmediately"]

class OutlineException(Exception):
    """A General outline base exception."""
    pass

class LayerException(OutlineException):
    """Layer exception

    This exception is raised when there is a problem
    setting up or executing a layer entity.
    """
    pass

class ShellCommandFailureException(OutlineException):
    """ShellCommandFailureException

    Thrown when layer.system() fails with an exit
    status greater than 1.
    """
    def __init__(self, msg, status):
        OutlineException.__init__(self)
        self.message = msg
        self.exit_status = status

class SessionException(OutlineException):
    """Session exception.

    This exception is raised when there is a problem
    reading/writing/finding the job session.
    """
    pass

class FailImmediately(OutlineException):
    """
    Throwing this exception will fail the frame immediately,
    even from within a plugin
    """
    pass

class FileSpecException(Exception):
    """
    An exception to describe issues with the io.FileSpec class.
    """
    pass
