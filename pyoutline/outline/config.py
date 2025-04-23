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


"""Outline configuration"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str

# pylint: disable=wrong-import-position
from future import standard_library
standard_library.install_aliases()
# pylint: enable=wrong-import-position

import getpass
import logging
import os
import pathlib
import platform
import tempfile
import configparser

__all__ = ['config', 'read_config_from_disk']
__file_path__ = pathlib.Path(__file__)

# Environment variables which can be used to define a custom config file.
__CONFIG_FILE_ENV_VARS = [
    # OUTLINE_CONFIG_FILE is the preferred setting to use.
    'OUTLINE_CONFIG_FILE',
    # OL_CONFIG is deprecated, but kept for now for backwards compatibility.
    'OL_CONFIG',
]


logger = logging.getLogger("outline.config")


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


def read_config_from_disk():
    """Loads configuration settings from config file on the local system.

    The configuration file used is, in order of preference:
    - Path defined by the OUTLINE_CONFIG_FILE environment variable.
    - Path defined by the OL_CONFIG environment variable.
    - Path within the config base directory (i.e. ~/.config/opencue/outline.cfg)
    - The default outline.cfg file which is distributed with the outline library.

    :rtype: ConfigParser
    :return: config settings
    """
    pyoutline_root_dir = __file_path__.parent.parent
    default_user_dir = pathlib.Path(
        tempfile.gettempdir()) / 'opencue' / 'outline' / getpass.getuser()

    _config = configparser.ConfigParser()
    config_file = None

    for config_file_env_var in __CONFIG_FILE_ENV_VARS:
        logger.debug('Checking for outline config file path in %s', config_file_env_var)
        config_file_from_env = os.environ.get(config_file_env_var)
        if config_file_from_env and os.path.exists(config_file_from_env):
            config_file = config_file_from_env
            break

    if not config_file:
        config_from_user_profile = os.path.join(config_base_directory(), 'outline.cfg')
        logger.debug('Checking for outline config at %s', config_from_user_profile)
        if os.path.exists(config_from_user_profile):
            config_file = config_from_user_profile

    if not config_file:
        default_config_path = __file_path__.parent / 'outline.cfg'
        logger.info('Loading default outline config from %s', default_config_path)
        if default_config_path.exists():
            config_file = default_config_path

    if not config_file:
        raise FileNotFoundError('outline config file was not found')

    _config.read(str(config_file))

    # Add defaults to the config,if they were not specified.
    if not _config.get('outline', 'home'):
        _config.set('outline', 'home', str(pyoutline_root_dir))

    if not _config.get('outline', 'user_dir'):
        _config.set('outline', 'user_dir', str(default_user_dir))

    return _config


config = read_config_from_disk()
