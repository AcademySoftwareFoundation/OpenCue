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
import os

from Manifest import QtCore, QtGui, Cue3

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
DEFAULT_INI_PATH = os.path.dirname(__file__) + "/config"

DEFAULT_YAML = os.path.join(DEFAULT_INI_PATH, 'cue3.yaml')

DEFAULT_PLUGIN_PATHS = [os.path.dirname(__file__) + "/plugins"]

LOGGER_FORMAT = "%(levelname)-9s %(module)-10s %(message)s"
LOGGER_LEVEL = "WARNING"

EMAIL_SUBJECT_PREFIX = "cuemail: please check "
EMAIL_BODY_PREFIX = "Your PSTs request that you check "
EMAIL_BODY_SUFFIX = "\n\n"
EMAIL_DOMAIN = ""

URL_USERGUIDE = ""
URL_SUGGESTION = ""
URL_BUG = ""

DEFAULT_EDITOR = "gview -R -m -M -U %s/gvimrc +" % DEFAULT_INI_PATH

EMPTY_INDEX = QtCore.QModelIndex()

QVARIANT_CENTER = QtCore.QVariant(QtCore.Qt.AlignCenter)
QVARIANT_RIGHT = QtCore.QVariant(QtCore.Qt.AlignRight)
QVARIANT_NULL = QtCore.QVariant()
QVARIANT_BLACK = QtCore.QVariant(QtGui.QColor(QtCore.Qt.black))
QVARIANT_GREY = QtCore.QVariant(QtGui.QColor(QtCore.Qt.gray))

ALLOWED_TAGS = ("general", "desktop", "playblast", "util", "preprocess", "wan", "cuda", "splathw",
                'naiad', 'massive')

RGB_FRAME_STATE = {Cue3.api.job_pb2.DEAD: QtGui.QColor(255, 0, 0),
                   Cue3.api.job_pb2.DEPEND: QtGui.QColor(160, 32, 240),
                   Cue3.api.job_pb2.EATEN: QtGui.QColor(150, 0, 0),
                   Cue3.api.job_pb2.RUNNING:  QtGui.QColor(200, 200, 55),
                   Cue3.api.job_pb2.SETUP: QtGui.QColor(160, 32, 240),
                   Cue3.api.job_pb2.SUCCEEDED: QtGui.QColor(55, 200, 55),
                   Cue3.api.job_pb2.WAITING: QtGui.QColor(135, 207, 235),
                   Cue3.api.job_pb2.CHECKPOINT: QtGui.QColor(61, 98, 247)}
QVARIANT_FRAME_STATE = \
    dict((key, QtCore.QVariant(RGB_FRAME_STATE[key])) for key in RGB_FRAME_STATE.keys())

TYPE_JOB = QtGui.QTreeWidgetItem.UserType + 1
TYPE_LAYER = QtGui.QTreeWidgetItem.UserType + 2
TYPE_FRAME = QtGui.QTreeWidgetItem.UserType + 3
TYPE_SHOW = QtGui.QTreeWidgetItem.UserType + 4
TYPE_ROOTGROUP = QtGui.QTreeWidgetItem.UserType + 5
TYPE_GROUP = QtGui.QTreeWidgetItem.UserType + 6
TYPE_ALLOC = QtGui.QTreeWidgetItem.UserType + 7
TYPE_HOST = QtGui.QTreeWidgetItem.UserType + 8
TYPE_PROC = QtGui.QTreeWidgetItem.UserType + 9
TYPE_FILTER = QtGui.QTreeWidgetItem.UserType + 10
TYPE_MATCHER = QtGui.QTreeWidgetItem.UserType + 11
TYPE_ACTION = QtGui.QTreeWidgetItem.UserType + 12
TYPE_DEPEND = QtGui.QTreeWidgetItem.UserType + 13
TYPE_SUB = QtGui.QTreeWidgetItem.UserType + 14
TYPE_TASK = QtGui.QTreeWidgetItem.UserType + 15

COLUMN_INFO_DISPLAY = 2

COLOR_THEME = "plastique"
COLOR_USER_1 = QtGui.QColor(50, 50, 100)
COLOR_USER_2 = QtGui.QColor(100, 100, 50)
COLOR_USER_3 = QtGui.QColor(0, 50, 0)
COLOR_USER_4 = QtGui.QColor(50, 30, 0)
