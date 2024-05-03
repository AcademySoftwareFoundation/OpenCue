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


"""
Application constants.
"""

from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import logging
import os
import platform

from qtpy import QtGui
from qtpy import QtWidgets
import yaml

import opencue
import opencue.config


__CONFIG_FILE_ENV_VAR = 'CUEGUI_CONFIG_FILE'
__DEFAULT_INI_PATH_ENV_VAR = 'CUEGUI_DEFAULT_INI_PATH'
__DEFAULT_CONFIG_FILE_NAME = 'cuegui.yaml'
__DEFAULT_CONFIG_FILE = os.path.join(
    os.path.dirname(__file__), 'config', __DEFAULT_CONFIG_FILE_NAME)


def __getLogger():
    """Other code should use cuegui.Logger to get a logger; we avoid using that module here
    to avoid creating a circular dependency."""
    logger_format = logging.Formatter("%(levelname)-9s %(module)-10s %(message)s")
    logger_stream = logging.StreamHandler()
    logger_stream.setLevel(logging.INFO)
    logger_stream.setFormatter(logger_format)
    logger = logging.getLogger(__file__)
    logger.addHandler(logger_stream)
    return logger


def __loadConfigFromFile():
    logger = __getLogger()
    with open(__DEFAULT_CONFIG_FILE) as fp:
        config = yaml.load(fp, Loader=yaml.SafeLoader)

    user_config_file = None

    logger.debug('Checking for cuegui config file path in %s', __CONFIG_FILE_ENV_VAR)
    config_file_from_env = os.environ.get(__CONFIG_FILE_ENV_VAR)
    if config_file_from_env and os.path.exists(config_file_from_env):
        user_config_file = config_file_from_env

    if not user_config_file:
        config_file_from_user_profile = os.path.join(
            opencue.config.config_base_directory(), __DEFAULT_CONFIG_FILE_NAME)
        logger.debug('Checking for cuegui config at %s', config_file_from_user_profile)
        if os.path.exists(config_file_from_user_profile):
            user_config_file = config_file_from_user_profile

    if user_config_file:
        logger.info('Loading cuegui config from %s', user_config_file)
        with open(user_config_file, 'r') as fp:
            config.update(yaml.load(fp, Loader=yaml.SafeLoader))

    return config


def __packaged_version():
    possible_version_path = os.path.join(
        os.path.abspath(os.path.join(__file__, "../../..")), 'VERSION.in')
    if os.path.exists(possible_version_path):
        with open(possible_version_path) as fp:
            default_version = fp.read().strip()
        return default_version
    return "1.3.0"


__config = __loadConfigFromFile()

VERSION = __config.get('version', __packaged_version())

STARTUP_NOTICE_DATE = __config.get('startup_notice.date')
STARTUP_NOTICE_MSG = __config.get('startup_notice.msg')

JOB_UPDATE_DELAY = __config.get('refresh.job_update_delay')
LAYER_UPDATE_DELAY = __config.get('refresh.layer_update_delay')
FRAME_UPDATE_DELAY = __config.get('refresh.frame_update_delay')
HOST_UPDATE_DELAY = __config.get('refresh.host_update_delay')
AFTER_ACTION_UPDATE_DELAY = __config.get('refresh.after_action_update_delay')
MINIMUM_UPDATE_INTERVAL = __config.get('refresh.min_update_interval') // 1000

FONT_FAMILY = __config.get('style.font.family')
FONT_SIZE = __config.get('style.font.size')
STANDARD_FONT = QtGui.QFont(FONT_FAMILY, FONT_SIZE)

RESOURCE_PATH = __config.get('paths.resources')
if not os.path.isabs(RESOURCE_PATH):
    RESOURCE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), RESOURCE_PATH))

CONFIG_PATH = __config.get('paths.config')
if not os.path.isabs(CONFIG_PATH):
    CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), CONFIG_PATH))


EMAIL_SUBJECT_PREFIX = "cuemail: please check "
EMAIL_BODY_PREFIX = "Your PSTs request that you check:\n"
EMAIL_BODY_SUFFIX = "\n\n"
EMAIL_DOMAIN = ""

DEFAULT_INI_PATH = os.getenv('CUEGUI_DEFAULT_INI_PATH', __config.get('paths.default_ini_path'))
if not os.path.isabs(DEFAULT_INI_PATH):
    DEFAULT_INI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), DEFAULT_INI_PATH))

DEFAULT_PLUGIN_PATHS = __config.get('paths.plugins')
for i, path in enumerate(DEFAULT_PLUGIN_PATHS):
    if not os.path.isabs(path):
        DEFAULT_PLUGIN_PATHS[i] = os.path.abspath(os.path.join(os.path.dirname(__file__), path))

LOGGER_FORMAT = __config.get('logger.format')
LOGGER_LEVEL = __config.get('logger.level')

EMAIL_SUBJECT_PREFIX = __config.get('email.subject_prefix')
EMAIL_BODY_PREFIX = __config.get('email.body_prefix')
EMAIL_BODY_SUFFIX = __config.get('email.body_suffix')
EMAIL_DOMAIN = __config.get('email.domain')

GITHUB_CREATE_ISSUE_URL = __config.get('links.issue.create')
URL_USERGUIDE = __config.get('links.user_guide')
URL_SUGGESTION = GITHUB_CREATE_ISSUE_URL + __config.get('links.issue.suggestion')
URL_BUG = GITHUB_CREATE_ISSUE_URL + __config.get('links.issue.bug')

if platform.system() == 'Windows':
    DEFAULT_EDITOR = __config.get('editor.windows')
elif platform.system() == 'Darwin':
    DEFAULT_EDITOR = __config.get('editor.mac')
else:
    DEFAULT_EDITOR = __config.get('editor.linux')
DEFAULT_EDITOR = DEFAULT_EDITOR.format(config_path=CONFIG_PATH)

LOG_ROOT_OS = __config.get('render_logs.root')

ALLOWED_TAGS = tuple(__config.get('allowed_tags'))

DARK_STYLE_SHEET = os.path.join(CONFIG_PATH, __config.get('style.style_sheet'))
COLOR_THEME = __config.get('style.color_theme')
__bg_colors = __config.get('style.colors.background')
COLOR_USER_1 = QtGui.QColor(*__bg_colors[0])
COLOR_USER_2 = QtGui.QColor(*__bg_colors[1])
COLOR_USER_3 = QtGui.QColor(*__bg_colors[2])
COLOR_USER_4 = QtGui.QColor(*__bg_colors[3])

__frame_colors = __config.get('style.colors.frame_state')
RGB_FRAME_STATE = {
    opencue.api.job_pb2.DEAD: QtGui.QColor(*__frame_colors.get('DEAD')),
    opencue.api.job_pb2.DEPEND: QtGui.QColor(*__frame_colors.get('DEPEND')),
    opencue.api.job_pb2.EATEN: QtGui.QColor(*__frame_colors.get('EATEN')),
    opencue.api.job_pb2.RUNNING:  QtGui.QColor(*__frame_colors.get('RUNNING')),
    opencue.api.job_pb2.SETUP: QtGui.QColor(*__frame_colors.get('SETUP')),
    opencue.api.job_pb2.SUCCEEDED: QtGui.QColor(*__frame_colors.get('SUCCEEDED')),
    opencue.api.job_pb2.WAITING: QtGui.QColor(*__frame_colors.get('WAITING')),
    opencue.api.job_pb2.CHECKPOINT: QtGui.QColor(*__frame_colors.get('CHECKPOINT')),
}

MEMORY_WARNING_LEVEL = __config.get('memory_warning_level')

LOG_HIGHLIGHT_ERROR = __config.get('render_logs.highlight.error')
LOG_HIGHLIGHT_WARN = __config.get('render_logs.highlight.warning')
LOG_HIGHLIGHT_INFO = __config.get('render_logs.highlight.info')

RESOURCE_LIMITS = __config.get('resources')

TYPE_JOB = QtWidgets.QTreeWidgetItem.UserType + 1
TYPE_LAYER = QtWidgets.QTreeWidgetItem.UserType + 2
TYPE_FRAME = QtWidgets.QTreeWidgetItem.UserType + 3
TYPE_SHOW = QtWidgets.QTreeWidgetItem.UserType + 4
TYPE_ROOTGROUP = QtWidgets.QTreeWidgetItem.UserType + 5
TYPE_GROUP = QtWidgets.QTreeWidgetItem.UserType + 6
TYPE_ALLOC = QtWidgets.QTreeWidgetItem.UserType + 7
TYPE_HOST = QtWidgets.QTreeWidgetItem.UserType + 8
TYPE_PROC = QtWidgets.QTreeWidgetItem.UserType + 9
TYPE_FILTER = QtWidgets.QTreeWidgetItem.UserType + 10
TYPE_MATCHER = QtWidgets.QTreeWidgetItem.UserType + 11
TYPE_ACTION = QtWidgets.QTreeWidgetItem.UserType + 12
TYPE_DEPEND = QtWidgets.QTreeWidgetItem.UserType + 13
TYPE_SUB = QtWidgets.QTreeWidgetItem.UserType + 14
TYPE_TASK = QtWidgets.QTreeWidgetItem.UserType + 15
TYPE_LIMIT = QtWidgets.QTreeWidgetItem.UserType + 16

QVARIANT_NULL = None
QT_MAX_INT = 2147483647

COLUMN_INFO_DISPLAY = 2
