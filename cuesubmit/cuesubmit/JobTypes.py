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


"""Base Job Types available in the UI.

Plugin apps can subclass this to change out the mapping to enable customized settings widgets."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
from cuesubmit.ui import SettingsWidgets
from cuesubmit import Constants
from cuesubmit import Util

class JobTypes(object):
    """Base Job Types available in the UI.

    Plugin apps can subclass this to change out the mapping to enable customized
    settings widgets."""

    SHELL = 'Shell'
    MAYA = 'Maya'
    NUKE = 'Nuke'
    BLENDER = 'Blender'
    FROM_CONFIG_FILE = Constants.RENDER_CMDS.keys()

    SETTINGS_MAP = {
        SHELL: SettingsWidgets.ShellSettings,
        MAYA: SettingsWidgets.BaseMayaSettings,
        NUKE: SettingsWidgets.BaseNukeSettings,
        BLENDER: SettingsWidgets.BaseBlenderSettings,
    }
    for jobType in FROM_CONFIG_FILE:
        SETTINGS_MAP[jobType] = SettingsWidgets.DynamicSettingsWidget

    def __init__(self):
        pass

    @classmethod
    def build(cls, jobType, *args, **kwargs):
        """Factory method for creating a settings widget."""
        if jobType in cls.FROM_CONFIG_FILE:
            jobOptions = Constants.RENDER_CMDS[jobType].get('options')
            parameters = Util.convertCommandOptions(options=jobOptions)
            kwargs.update({'tool_name': jobType,
                           'parameters': parameters})
        return cls.SETTINGS_MAP[jobType](*args, **kwargs)

    @classmethod
    def types(cls):
        """return a list of available types."""
        return list(cls.SETTINGS_MAP.keys())

    @classmethod
    def services(cls, jobType):
        """return a list of services for a given jobType. (the "services" key in your yaml file)"""
        return Constants.RENDER_CMDS[jobType].get('services', [])

    @classmethod
    def limits(cls, jobType):
        """return a list of limits for a given jobType. (the "limits" key in your yaml file)"""
        return Constants.RENDER_CMDS[jobType].get('limits', [])
