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


"""
Application constants.
"""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue


VERSION = "1.3.0"

STARTUP_NOTICE_DATE = 0
STARTUP_NOTICE_MSG = ""

JOB_UPDATE_DELAY = 10000  # msec
LAYER_UPDATE_DELAY = 10000  # msec
FRAME_UPDATE_DELAY = 10000  # msec
HOST_UPDATE_DELAY = 20000  # msec
AFTER_ACTION_UPDATE_DELAY = 1000  # msec

MAX_LOG_POPUPS = 5
MINIMUM_UPDATE_INTERVAL = 5  # sec

FONT_SIZE = 10  # 8
STANDARD_FONT = QtGui.QFont("Luxi Sans", FONT_SIZE)
STANDARD_ROW_HEIGHT = 16  # 14

MEMORY_WARNING_LEVEL = 5242880

RESOURCE_PATH = os.path.dirname(__file__) + "/images"
DEFAULT_INI_PATH = os.getenv('CUEGUI_DEFAULT_INI_PATH', os.path.dirname(__file__) + '/config')

DEFAULT_PLUGIN_PATHS = [os.path.dirname(__file__) + "/plugins"]

LOGGER_FORMAT = "%(levelname)-9s %(module)-10s %(message)s"
LOGGER_LEVEL = "WARNING"

EMAIL_SUBJECT_PREFIX = "cuemail: please check "
EMAIL_BODY_PREFIX = "Your PSTs request that you check "
EMAIL_BODY_SUFFIX = "\n\n"
EMAIL_DOMAIN = ""

URL_USERGUIDE = "https://www.opencue.io/docs/"
URL_SUGGESTION = "https://github.com/AcademySoftwareFoundation/OpenCue/issues/new?labels=enhancement&template=enhancement.md"
URL_BUG = "https://github.com/AcademySoftwareFoundation/OpenCue/issues/new?labels=bug&template=bug_report.md"

DEFAULT_EDITOR = "gview -R -m -M -U %s/gvimrc +" % DEFAULT_INI_PATH

EMPTY_INDEX = QtCore.QModelIndex()

QVARIANT_CENTER = QtCore.Qt.AlignCenter
QVARIANT_RIGHT = QtCore.Qt.AlignRight
QVARIANT_NULL = None
QVARIANT_BLACK = QtGui.QColor(QtCore.Qt.black)
QVARIANT_GREY = QtGui.QColor(QtCore.Qt.gray)

ALLOWED_TAGS = ("general", "desktop", "playblast", "util", "preprocess", "wan", "cuda", "splathw",
                'naiad', 'massive')

RGB_FRAME_STATE = {opencue.api.job_pb2.DEAD: QtGui.QColor(255, 0, 0),
                   opencue.api.job_pb2.DEPEND: QtGui.QColor(160, 32, 240),
                   opencue.api.job_pb2.EATEN: QtGui.QColor(150, 0, 0),
                   opencue.api.job_pb2.RUNNING:  QtGui.QColor(200, 200, 55),
                   opencue.api.job_pb2.SETUP: QtGui.QColor(160, 32, 240),
                   opencue.api.job_pb2.SUCCEEDED: QtGui.QColor(55, 200, 55),
                   opencue.api.job_pb2.WAITING: QtGui.QColor(135, 207, 235),
                   opencue.api.job_pb2.CHECKPOINT: QtGui.QColor(61, 98, 247)}
QVARIANT_FRAME_STATE = \
    dict((key, RGB_FRAME_STATE[key]) for key in list(RGB_FRAME_STATE.keys()))

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

COLUMN_INFO_DISPLAY = 2

DARK_STYLE_SHEET = os.path.join(DEFAULT_INI_PATH, "darkpalette.qss")
COLOR_THEME = "plastique"
COLOR_USER_1 = QtGui.QColor(50, 50, 100)
COLOR_USER_2 = QtGui.QColor(100, 100, 50)
COLOR_USER_3 = QtGui.QColor(0, 50, 0)
COLOR_USER_4 = QtGui.QColor(50, 30, 0)
