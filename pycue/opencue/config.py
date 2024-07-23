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

import logging
import os
import platform

import yaml


logger = logging.getLogger("opencue")


# Config file from which default settings are loaded. This file is distributed with the
# opencue Python library.
__DEFAULT_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'default.yaml')

# Environment variables which can be used to define a custom config file. Any settings
# defined in this file will be used instead of the defaults.
__CONFIG_FILE_ENV_VARS = [
    # OPENCUE_CONFIG_FILE is the preferred setting to use.
    'OPENCUE_CONFIG_FILE',
    # OPENCUE_CONF is deprecated, but kept for now for backwards compatibility.
    'OPENCUE_CONF',
]


def config_base_directory():
    """Returns the OpenCue config base directory.

    This platform-dependent directory, stored within your user profile, is used by
    OpenCue components as the default location for various configuration files. Typically
    if you store your config files in this location, there is no need to set environment
    variables to indicate where your config files are located -- OpenCue should recognize
    them automatically.

    NOTE: This work is ongoing. Over time more OpenCue components will start using this
    base directory. See https://github.com/AcademySoftwareFoundation/OpenCue/issues/785.

    :rtype: str
    :return: config file base directory
    """
    if platform.system() == 'Windows':
        return os.path.join(os.path.expandvars('%APPDATA%'), 'opencue')
    return os.path.join(os.path.expanduser('~'), '.config', 'opencue')


def load_config_from_file():
    """Loads configuration settings from config file on the local system.

    Default settings are read from default.yaml which is distributed with the opencue library.
    User-provided config is then read from disk, in order of preference:
    - Path defined by the OPENCUE_CONFIG_FILE environment variable.
    - Path defined by the OPENCUE_CONF environment variable.
    - Path within the config base directory (i.e. ~/.config/opencue/opencue.yaml)

    :rtype: dict
    :return: config settings
    """
    with open(__DEFAULT_CONFIG_FILE, encoding="utf-8") as file_object:
        config = yaml.load(file_object, Loader=yaml.SafeLoader)

    user_config_file = None

    for config_file_env_var in __CONFIG_FILE_ENV_VARS:
        logger.debug('Checking for opencue config file path in %s', config_file_env_var)
        config_file_from_env = os.environ.get(config_file_env_var)
        if config_file_from_env and os.path.exists(config_file_from_env):
            user_config_file = config_file_from_env
            break

    if not user_config_file:
        config_from_user_profile = os.path.join(config_base_directory(), 'opencue.yaml')
        logger.debug('Checking for opencue config at %s', config_from_user_profile)
        if os.path.exists(config_from_user_profile):
            user_config_file = config_from_user_profile

    if user_config_file:
        logger.info('Loading opencue config from %s', user_config_file)
        with open(user_config_file, encoding="utf-8") as file_object:
            config.update(yaml.load(file_object, Loader=yaml.SafeLoader))

    return config
