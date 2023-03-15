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


"""Utility functions used throughout the application."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import importlib.util
import inspect

import opencue
from cuesubmit import Constants


def getLimits():
    """Returns a list of limit names from cuebot."""
    return [limit.name() for limit in opencue.api.getLimits()]


def getServices():
    """Returns a list of service names from cuebot."""
    return [service.name() for service in opencue.api.getDefaultServices()]


def getShows():
    """Returns a list of show names from cuebot."""
    return [show.name() for show in opencue.api.getShows()]


def getAllocations():
    """Returns a list of Allocations from cuebot."""
    return opencue.api.getAllocations()


def getPresetFacility():
    """Returns the default facility defined via environment variable, if set."""
    if os.getenv('RENDER_TO', None):
        return os.environ['RENDER_TO']
    if os.getenv('FACILITY', None):
        return os.environ['FACILITY']
    return None


def getFacilities(allocations):
    """Returns a list of facility names from the allocations."""
    default_facilities = [Constants.DEFAULT_FACILITY_TEXT]
    facilities = set(alloc.data.facility for alloc in allocations)
    return default_facilities + list(facilities)

def get_python_script_parameters(script_path):
    """ Inspects a script file's opencue_render() function to analyse its parameters.

    This function must have type hints, ex houdini_prman.py :
    opencue_render(hipFile: str,
                   ropPath: str,
                   startFrame: str='#FRAME_START#',
                   endFrame: str='#FRAME_END#',
                   halfRes: bool=0,
                   logLevel: tuple=(0, 5, 3))

    note: here we declared start/endFrame as a str with a default value. This is to get the frame token.
    Type hints are not strict constraints, just hints aiming at finding a matching widget.
    Supports simple types (str, int, bool and 3-4 int-tuples for min/max/default /precision)

    :type script_path: str
    :param script_path: Path to a custom script with an inspectable opencue_render() function
                        It can contain env variables.
    :rtype: (str, dict)
    :return: Name of the tool / dict of parameters (name, type, value) from opencue_render()
    """
    tool_name, _script_module = _get_module_from_file(script_path=script_path)
    script_parameters = _get_opencue_render_parameters(script_module=_script_module)
    return tool_name, script_parameters

def convert_command_options(options):
    """ Parse command options from the config file and return parameters to feed the UI (name, type, value)

    :param options: All options for a given command (ex:{"-flag {Nice Name}": "default_value"})
    :type options: dict
    :return: list of dict of parameters
    """
    import re
    parameters = []
    for option_line, value in options.items():
        # flag, label, _, _ = next(iter(string.Formatter().parse(arg)))
        parse_option = re.search(r'(?P<command_flag>-\w*)?' # -optionFlag
                                 r'\s?'
                                 r'({'
                                    r'(?P<label>(\w*\s*)*)' # {Option Label}
                                    r'(?P<browse_flag>\*?\/?)' # {browseFile*} or {browseFolder/}
                                 r'})?',
                                 option_line)
        options = {
            'label': parse_option.group('label'), #not used
            'command_flag': parse_option.group('command_flag'),
            'value': value,
            'type': type(value),
            'browsable': parse_option.group('browse_flag'),
            }
        if isinstance(value, (tuple, list))\
                and len(value) in (3, 4)\
                and isinstance(value[0], (int, float)):
            options.update({
                'type': range,
                'min': value[0],
                'max': value[1],
                'value': value[2],
                'float_precision': value[3] if len(value)==4 else None
                })
        parameters.append(options)
    return parameters

def _get_opencue_render_parameters(script_module):
    """ From a custom python module with an opencue_render() function, returns its parameters names, values and types
    TODO: potential bug: we are importing a script that can have unavailable dependencies

    :param script_module: A python module with an inspectable opencue_render() function
    :type script_module: module
    :rtype: dict
    :return: dict of parameters (name, value, type) from opencue_render()
    """
    parameters = []
    signature = inspect.signature(script_module.opencue_render)
    for param in signature.parameters.values():
        default_value = param.default
        if default_value is inspect.Parameter.empty:
            default_value = param.annotation()  # evaluates the param type, ex: str()
        options = {'name': param.name,
                   'label': param.name,
                   'value': default_value,
                   'type': param.annotation}
        if param.annotation in (tuple, list)\
                and len(default_value) in (3, 4)\
                and isinstance(default_value[0], (int, float)):
            options.update({'type': range,
                            'min': default_value[0],
                            'max': default_value[1],
                            'value': default_value[2],
                            'float_precision': default_value[3] if len(default_value)==4 else None})
        parameters.append(options)
    return parameters

def _get_module_from_file(script_path):
    """ Loads the script as a module

    :type script_path: str
    :param script_path: Path to a python script containing an opencue_render() function.
                        It can contain env variables.
    :rtype: str, module
    :return: Name of the script, module object from the script
    :raises FileExistsError: The provided script does not exist or is not a file
    :raises NameError: The provided script does not contain an opencue_render() function
    """
    _script_path = os.path.expandvars(script_path)
    if not os.path.isfile(_script_path):
        raise FileExistsError(f'File does not exist {script_path=}')

    _script_dir, script_name = os.path.split(os.path.splitext(_script_path)[0])

    spec = importlib.util.spec_from_file_location('temp_openCue_inspectable', _script_path)
    script_as_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script_as_module)
    if 'opencue_render' not in dir(script_as_module):
        raise NameError(f'Script {script_name} from {_script_dir} does not contain an opencue_render() function')

    return script_name, script_as_module
