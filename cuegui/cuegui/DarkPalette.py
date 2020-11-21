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
The dark widget color scheme used by image viewing applications.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import platform
import hashlib

from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Constants


def init():
    """Convenience function that takes the QApplication object for the
    application and configures the palette and style for the Plastique
    color scheme"""
    QtGui.qApp.setPalette(DarkPalette())
    # if platform.system() in ['Darwin', 'Linux']:
    #     setDarkStyleSheet()
    # else:
    #     QtGui.qApp.setStyle(QtWidgets.QStyleFactory.create(cuegui.Constants.COLOR_THEME))


# def setDarkStyleSheet():
#     QtGui.qApp.setStyleSheet(open(cuegui.Constants.DARK_STYLE_SHEET).read())


def DarkPalette():
    """The dark widget color scheme used by image viewing applications
    at Imageworks.
    """
    # The 5 greys:
    # rgb(31, 31, 31)
    # rgb(38, 38, 38)
    # rgb(46, 46, 46)
    # rgb(71, 71, 71)
    # rgb(133, 133, 133)
    # rgb(153, 153, 153)
    p = QtGui.QPalette()

    c = QtGui.QColor(46, 46, 46) # rgb(46, 46, 46) main window colour
    p.setColor(p.Window, c)
    p.setColor(p.Button, c)

    c = QtGui.QColor(153, 153, 153) # rgb(153, 153, 153)
    p.setColor(p.WindowText, c)
    p.setColor(p.Text, c)
    p.setColor(p.ButtonText, c)
    p.setColor(p.BrightText, c)

    c = QtGui.QColor(60, 60, 80) # rgb(60, 60, 80)
    p.setColor(p.Link, c)
    c = QtGui.QColor(80, 60, 80) # rgb(80, 60, 80)
    p.setColor(p.LinkVisited, c)

    c = QtGui.QColor(31, 31, 31) # rgb(31, 31, 31) Primary table lines
    p.setColor(p.Base, c)
    c = QtGui.QColor(38, 38, 38) # rgb(38, 38, 38) Secondary table lines
    p.setColor(p.AlternateBase, c)

    c = QtGui.QColor(0, 0, 0) # rgb(0, 0, 0)
    p.setColor(p.Shadow, c)

    c = QtGui.QColor(31, 31, 31) # rgb(31, 31, 31)
    p.setColor(p.Dark, c)

    c = QtGui.QColor(38, 38, 38) # rgb(38, 38, 38) I dont think this is being used
    p.setColor(p.Mid, c)

    c = QtGui.QColor(46, 46, 46)# rgb(46, 46, 46) I dont think this is being used
    p.setColor(p.Midlight, c)

    c = QtGui.QColor(71, 71, 71) #rgb(71, 71, 71)
    p.setColor(p.Light, c)

    c = QtGui.QColor(46, 46, 46) #rgb(71, 71, 71)
    p.setColor(QtGui.QPalette.Disabled, p.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, p.Text, c)
    p.setColor(QtGui.QPalette.Disabled, p.ButtonText, c)

    c = QtGui.QColor(153, 153, 153) # rgb(200, 200, 200)
    p.setColor(QtGui.QPalette.Disabled, p.BrightText, c)

    c = QtGui.QColor(37, 72, 77) # rgb(37, 72, 77) controls selected and progress bar colours
    p.setColor(QtGui.QPalette.Highlight, c)

    return p

COLOR_JOB_PAUSED_BACKGROUND = QtGui.QColor(47, 56, 64) # rgb(47, 56, 64)
COLOR_JOB_DYING_BACKGROUND = QtGui.QColor(64, 21, 21) # rgb(64, 21, 21)
COLOR_JOB_TIMEOUT_BACKGROUND = QtGui.QColor(92, 61, 11) # rgb(92, 61, 11)
COLOR_JOB_PROGRESS_BACKGROUND = QtGui.QColor(65, 94, 42) # rgb(65, 94, 42)
COLOR_JOB_FINISHED_BACKGROUND = QtGui.QColor(10, 106, 130) # rgb(10, 106, 130)
COLOR_JOB_FINISHED_BAD_BACKGROUND = QtGui.QColor(10, 84, 130) # rgb(10, 84, 130)

COLOR_JOB_WITHOUT_PROCS = QtGui.QColor(23, 23, 23) # rgb(23, 23, 23)
COLOR_JOB_DEPENDED = QtGui.QColor(65, 41, 74, 100) # rgb(65, 41, 74, 100)
COLOR_JOB_HIGH_MEMORY = QtGui.QColor(181, 119, 11) # rgb(181, 119, 11)

COLOR_GROUP_BACKGROUND = QtGui.QColor(46, 46, 46) # rgb(46, 46, 46)
COLOR_GROUP_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_SHOW_BACKGROUND = QtGui.QColor(71, 71, 71) # rgb(71, 71, 71)
COLOR_SHOW_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_JOB_FOREGROUND = QtGui.QColor(153, 153, 153) # rgb(153, 153, 153)

#Icons
EAT_ICON_COLOUR = QtGui.QColor(255, 201, 25) # rgb(255, 201, 25)
RETRY_ICON_COLOUR = QtGui.QColor(140, 196, 29) # rgb(140, 196, 29)
KILL_ICON_COLOUR = QtGui.QColor(224, 52, 52) # rgb(224, 52, 52)
PAUSE_ICON_COLOUR = QtGui.QColor(88, 163, 209) # rgb(88, 163, 209)
PLAY_ICON_COLOUR = QtGui.QColor(88, 163, 209) # rgb(88, 163, 209)
EJECT_ICON_COLOUR = QtGui.QColor(207, 219, 227) # rgb(207, 219, 227)
DEFAULT_ICON_COLOUR = QtGui.QColor(135, 135, 135) # rgb(135, 135, 135)
BRIGHT_ICON_COLOUR = QtGui.QColor(230, 230, 230) # rgb(230, 230, 230)
SHOW_ICON_COLOUR = QtGui.QColor(230, 230, 230) # rgb(230, 230, 230)

#Log file Colors
LOG_TIME = QtGui.QColor(170, 149, 171) # rgb(170, 149, 171)
LOG_ERROR = QtGui.QColor(224, 52, 52) # rgb(224, 52, 52)
LOG_WARNING = QtGui.QColor(255, 201, 25) # rgb(255, 201, 25)
LOG_INFO = QtGui.QColor(111, 140, 255) # rgb(111, 140, 255)
LOG_COMPLETE = QtGui.QColor(132, 201, 12) # rgb(132, 201, 12)

# Host bar colours
USED_COLOUR = QtGui.QColor(255, 201, 25) # rgb(255, 201, 25)
FREE_COLOUR = QtGui.QColor(87, 87, 87) # rgb(87, 87, 87)

def name_grouping_colour(name):
    code = int(hashlib.md5(name).hexdigest(), 16) % (10 ** 8)
    red = ((code >> 27) & 31) << 3
    green = ((code >> 21) & 31) << 3
    blue = ((code >> 16) & 31) << 3
    return QtGui.QColor(red, green, blue, 100)
