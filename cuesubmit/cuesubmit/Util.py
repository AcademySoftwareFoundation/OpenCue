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

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os

import opencue
from cuesubmit import Constants


def getLimits():
    """Return a list of limit names from cuebot."""
    return [limit.name() for limit in opencue.api.getLimits()]


def getServices():
    """Return a list of service names from cuebot."""
    return [service.name() for service in opencue.api.getDefaultServices()]


def getShows():
    """Return a list of show names from cuebot."""
    return [show.name() for show in opencue.api.getShows()]


def getAllocations():
    """Return a list of Allocations from cuebot."""
    return opencue.api.getAllocations()


def getPresetFacility():
    if os.getenv('RENDER_TO', None):
        return os.environ['RENDER_TO']
    if os.getenv('FACILITY', None):
        return os.environ['FACILITY']
    return None


def getFacilities(allocations):
    """Return a list of facility names from the allocations."""
    default_facilities = [Constants.DEFAULT_FACILITY_TEXT]
    facilities = set(alloc.data.facility for alloc in allocations)
    return default_facilities + list(facilities)
