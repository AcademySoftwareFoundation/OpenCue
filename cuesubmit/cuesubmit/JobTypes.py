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
    CUSTOM = Constants.RENDER_CMDS.keys()

    SETTINGS_MAP = {
        SHELL: SettingsWidgets.ShellSettings,
        MAYA: SettingsWidgets.BaseMayaSettings,
        NUKE: SettingsWidgets.BaseNukeSettings,
        BLENDER: SettingsWidgets.BaseBlenderSettings,
    }
    SETTINGS_MAP.update(Constants.RENDER_CMDS)

    def __init__(self):
        pass

    @classmethod
    def build(cls, jobType, *args, **kwargs):
        """Factory method for creating a settings widget."""
        if jobType not in Constants.RENDER_CMDS.keys():
            return cls.SETTINGS_MAP[jobType](*args, **kwargs)

        _script_file = Constants.RENDER_CMDS[jobType].get('from_script')
        if _script_file:
            tool_name, parameters = Util.get_python_script_parameters(script_path=_script_file)
        else:
            _options = Constants.RENDER_CMDS[jobType].get('options')
            tool_name, parameters = jobType, Util.convert_command_options(options=_options)
        kwargs.update({'tool_name': tool_name, 'parameters': parameters})
        return SettingsWidgets.BaseDynamicSettings(*args, **kwargs)

    @classmethod
    def types(cls):
        """return a list of types available."""
        return [cls.SHELL, cls.MAYA, cls.NUKE, cls.BLENDER]
