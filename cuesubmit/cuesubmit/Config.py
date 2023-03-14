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


"""Provides custom configuration to override default CueSubmit functionality.

Uses a YAML config file to override Constant.py values. Path is specified using the
"CUESUBMIT_CONFIG_FILE" environment variable. An example config file is contained in the
top level cuesubmit folder."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import yaml

import opencue.config


CONFIG_FILE_ENV_VAR = 'CUESUBMIT_CONFIG_FILE'


def getConfigValues():
    """Reads the config file from disk and returns the values it defines."""
    configFile = os.environ.get(CONFIG_FILE_ENV_VAR)
    if not configFile:
        configFile = os.path.join(opencue.config.config_base_directory(), 'cuesubmit.yaml')
    configData = _load_yaml_file(yaml_file=configFile)
    if 'RENDER_CMDS' in configData:
        configData['RENDER_CMDS'] = _expand_render_config_values(configData['RENDER_CMDS'])
    return configData

def _load_yaml_file(yaml_file):
    """ Load config yaml as dict
    :param yaml_file: path to a config.yaml file (path can be an env var)
    :type yaml_file: str
    :returns: yaml content as dict
    :rtype: dict
    """
    _yaml_file = os.path.expandvars(yaml_file)
    if not os.path.exists(_yaml_file):
        raise RuntimeError(f'{yaml_file=} not found')
    config_data = {}
    with open(_yaml_file, 'r') as data:
        try:
            config_data = yaml.load(data, Loader=yaml.SafeLoader)
        except yaml.YAMLError:
            raise CuesubmitConfigError("Could not load yaml file: {}. Please check its "
                                       "formatting".format(_yaml_file))
    return config_data

def _expand_render_config_values(RENDER_CMDS):
    """ Looks through each render command and loads their 'config_file' if any
    :param RENDER_CMDS: all render commands from the cuesubmit_config.yaml file
    :type RENDER_CMDS: dict
    :returns: Updated RENDER_CMDS dict
    :rtype: dict
    """
    for job_type, _options in RENDER_CMDS.items():
        _sub_config_file = _options.get('config_file')
        if not _sub_config_file:
            continue
        RENDER_CMDS[job_type] = _load_yaml_file(yaml_file=_sub_config_file)

    return RENDER_CMDS

class CuesubmitConfigError(Exception):
    """Thrown when an error occurs reading the config file."""
