#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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
import yaml

"""
Overwrite Constant.py values with a yaml config file, with it's path specified with the
"CUESUBMIT_CONFIG_FILE" environment variable. An example config file is contained in the
top level cuesubmit folder.
"""

CONFIG_FILE_ENV_VAR = 'CUESUBMIT_CONFIG_FILE'


def getConfigValues():
    configData = {}
    configFile = os.environ.get(CONFIG_FILE_ENV_VAR)
    if configFile and os.path.exists(configFile):
        with open(configFile, 'r') as data:
            try:
                configData = yaml.load(data, Loader=yaml.SafeLoader)
            except yaml.YAMLError:
                raise CuesubmitConfigError("Could not load yaml file: {}. Please check its "
                                           "formatting".format(configFile))
    return configData


class CuesubmitConfigError(Exception):
    """Thrown when an error occurs reading the config file."""
    pass
