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


"""Functions for loading application layout and other state from disk."""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import shutil

from qtpy import QtCore

import cuegui.Constants
import cuegui.Logger

logger = cuegui.Logger.getLogger(__file__)


def startup(app_name):
    """
    Reads config from disk, restoring default config if necessary.

    :param app_name: application window name
    :type app_name: str
    :return: settings object containing the loaded settings
    :rtype: QtCore.QSettings
    """
    # E.g. ~/.config/.cuecommander/config.ini
    config_path = "/.%s/config" % app_name.lower()
    settings = QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, config_path) # pylint: disable=no-member
    logger.info('Reading config file from %s', settings.fileName())
    local = settings.fileName()

    # If the user has chose to revert the layout. delete the file and copy the default back.
    if settings.value('RevertLayout'):
        logger.warning('Found RevertLayout flag, will restore default config')
        os.remove(local)

    # If the config file does not exist, copy over the default
    if not os.path.exists(local):
        default = os.path.join(cuegui.Constants.DEFAULT_INI_PATH, "%s.ini" % app_name.lower())
        logger.warning('Local config file not found at %s', local)
        logger.warning('Copying %s to %s', default, local)
        os.makedirs(os.path.dirname(local), exist_ok=True)
        shutil.copy2(default, local)
        settings.sync()

    return settings
