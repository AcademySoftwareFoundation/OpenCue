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
import re

import opencue
from cuesubmit import Constants


def getLimits():
    """Returns a list of limit names from cuebot."""
    return [limit.name() for limit in opencue.api.getLimits()]


def getServices():
    """Returns a list of service names from cuebot."""
    try:
        services = opencue.api.getDefaultServices()
    except opencue.exception.ConnectionException:
        return []
    else:
        return [service.name() for service in services]


def getServiceOption(serviceName, option):
    """Returns the value of a service property."""
    service = next(iter(service for service in opencue.api.getDefaultServices()
                        if service.name() == serviceName))
    if service and hasattr(service, option):
        return getattr(service, option)()
    print(f'{service.name()} service has no {option} option.')
    return None


def getShows():
    """Returns a list of show names from cuebot."""
    return [show.name() for show in opencue.api.getShows()]


def getDefaultShow():
    """Returns the default show defined via environment variable or config file, if set."""
    default_show = next(iter([show for show in getShows()
                              if re.match(show, Constants.DEFAULT_SHOW, re.IGNORECASE)]),
                        'no default show')
    return default_show


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


def convertCommandOptions(options):
    """ Parse command options from the config file
    and return parameters to feed the UI (name, type, value)

    :param options: All options for a given command (ex:{"-flag {Nice Name}": "default_value"})
    :type options: dict
    :return: list of dict of parameters
    """
    parameters = []
    for option_line, value in options.items():
        parse_option = re.search(Constants.REGEX_COMMAND_OPTIONS,
                                 option_line)
        cmd_options = {
            'option_line': option_line,
            'label': parse_option.group('label'),
            'command_flag': parse_option.group('command_flag'),
            'value': value,
            'type': type(value),
            'hidden': bool(parse_option.group('hidden'))
                      or re.match(Constants.REGEX_CUETOKEN, str(value)),
            'mandatory': bool(parse_option.group('mandatory')),
            'browsable': parse_option.group('browsable'),
            }
        if isinstance(value, (tuple, list))\
                and len(value) in (3, 4)\
                and isinstance(value[0], (int, float)):
            cmd_options.update({
                'type': range,
                'min': value[0],
                'max': value[1],
                'value': value[2],
                'float_precision': value[3] if len(value)==4 else None
                })
        parameters.append(cmd_options)
    return parameters
