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

"""OpenCue configuration."""

import os

import yaml


# Config file from which default settings are loaded. This file is distributed with the
# opencue Python library.
DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'default.yaml')

# Environment variables which can be used to define a custom config file. Any settings
# defined in this file will be used instead of the defaults.
CONFIG_FILE_ENV_VARS = [
    # OPENCUE_CONFIG_FILE is the preferred setting to use.
    'OPENCUE_CONFIG_FILE',
    # OPENCUE_CONF is deprecated, but kept for now for backwards compatibility.
    'OPENCUE_CONF',
]


def load_config_from_file():
    """Loads configuration settings from config file on the local system.

    Configuration is loaded using the following logic:
    - Default settings are read from default.yaml which is distributed with the opencue library.
    - If OPENCUE_CONF is set, that yaml file will be read in and any defined settings will
      override the default settings.

    :rtype dict
    :return config settings
    """
    with open(DEFAULT_CONFIG_FILE) as file_object:
        config = yaml.load(file_object, Loader=yaml.SafeLoader)

    for config_file_env_var in CONFIG_FILE_ENV_VARS:
        user_config_file = os.environ.get(config_file_env_var)
        if user_config_file and os.path.exists(user_config_file):
            with open(user_config_file) as file_object:
                config.update(yaml.load(file_object, Loader=yaml.SafeLoader))
            break

    return config
