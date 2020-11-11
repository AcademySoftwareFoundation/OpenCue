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
Main interface functions for interacting with outline.versions.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os

from .session import Session, Settings


__all__ = ["require",
           "unrequire",
           "get_version",
           "set_repos",
           "get_repos",
           "get_session",
           "set_module_repos"]


class VersionsException(Exception):
    """
    Raised when there was a problem configuring the repository path.
    """


def require(module, version="latest"):
    """
    Adds the given module/version into the repository.
    """
    return get_session().require(module, version)


def unrequire(module):
    """
    Removes the given module from the repository.
    """
    return get_session().unrequire(module)


def get_version(module, default="latest"):
    """
    Returns the currently loaded version of the given module.
    """
    return get_session().get_version(module, default)


def get_session():
    """
    Returns the singleton session instance.
    """
    return Session()


def get_repos():
    """
    Returns the repository path.
    """
    return Settings.repos_path


def set_repos(path):
    """
    Set the versions repository path.
    """
    path = os.path.abspath(path)
    if path == Settings.repos_path:
        return False
    if os.path.exists(path):
        Settings.repos_path = path
        return True
    raise VersionsException("Cannot set the repos path to a non existent directory. %s" % path)


def set_module_repos(module, path):
    """
    Sets the repository path for a specific module
    """
    if os.path.exists(path):
        Settings.module_repos[module] = path
    else:
        raise VersionsException("Cannot set the repos path to a non existent directory.")
