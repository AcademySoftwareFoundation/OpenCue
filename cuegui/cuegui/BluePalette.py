"""
The blue dark widget color scheme used by image viewing applications.
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
    QtGui.qApp.setPalette(BluePalette())


def BluePalette():
    # The 5 greys:
    # rgb(23, 24, 31)
    # rgb(35, 37, 48)
    # rgb(45, 48, 64)
    # rgb(58, 61, 77)
    # rgb(149, 151, 163)
    # rgb(187, 188, 196)

    p = QtGui.QPalette()

    c = QtGui.QColor(45, 48, 64) # rgb(45, 48, 64) main window colour
    p.setColor(p.Window, c)
    p.setColor(p.Button, c)

    c = QtGui.QColor(149, 151, 163) # rgb(149, 151, 163)
    p.setColor(p.WindowText, c)
    p.setColor(p.Text, c)
    p.setColor(p.ButtonText, c)
    p.setColor(p.BrightText, c)

    c = QtGui.QColor(60, 60, 80) # rgb(60, 60, 80)
    p.setColor(p.Link, c)
    c = QtGui.QColor(80, 60, 80) # rgb(80, 60, 80)
    p.setColor(p.LinkVisited, c)

    c = QtGui.QColor(23, 24, 31) # rgb(23, 24, 31) Primary table lines
    p.setColor(p.Base, c)
    c = QtGui.QColor(35, 37, 48) # rgb(35, 37, 48) Secondary table lines
    p.setColor(p.AlternateBase, c)

    c = QtGui.QColor(0, 0, 0) # rgb(0, 0, 0)
    p.setColor(p.Shadow, c)

    c = QtGui.QColor(23, 24, 31) # rgb(23, 24, 31)
    p.setColor(p.Dark, c)

    c = QtGui.QColor(35, 37, 48) # rgb(35, 37, 48) I dont think this is being used
    p.setColor(p.Mid, c)

    c = QtGui.QColor(45, 48, 64)# rgb(45, 48, 64) I dont think this is being used
    p.setColor(p.Midlight, c)

    c = QtGui.QColor(58, 61, 77) #rgb(58, 61, 77)
    p.setColor(p.Light, c)

    c = QtGui.QColor(45, 48, 64) #rgb(45, 48, 64)
    p.setColor(QtGui.QPalette.Disabled, p.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, p.Text, c)
    p.setColor(QtGui.QPalette.Disabled, p.ButtonText, c)

    c = QtGui.QColor(187, 188, 196) # rgb(187, 188, 196)
    p.setColor(QtGui.QPalette.Disabled, p.BrightText, c)

    c = QtGui.QColor(90, 109, 133) # rgb(90, 109, 133) controls selected and progress bar colours
    p.setColor(QtGui.QPalette.Highlight, c)

    return p

COLOR_JOB_PAUSED_BACKGROUND = QtGui.QColor(47, 56, 64) # rgb(47, 56, 64)
COLOR_JOB_DYING_BACKGROUND = QtGui.QColor(64, 21, 21) # rgb(64, 21, 21)
COLOR_JOB_TIMEOUT_BACKGROUND = QtGui.QColor(92, 61, 11) # rgb(92, 61, 11)
COLOR_JOB_PROGRESS_BACKGROUND = QtGui.QColor(65, 94, 42) # rgb(65, 94, 42)
COLOR_JOB_FINISHED_BACKGROUND = QtGui.QColor(10, 106, 130) # rgb(10, 106, 130)
COLOR_JOB_FINISHED_BAD_BACKGROUND = QtGui.QColor(10, 84, 130) # rgb(10, 84, 130)

COLOR_JOB_WITHOUT_PROCS = QtGui.QColor(145, 96, 28) # rgb(145, 96, 28)
COLOR_JOB_DEPENDED = QtGui.QColor(65, 41, 74, 100) # rgb(65, 41, 74, 100)
COLOR_JOB_HIGH_MEMORY = QtGui.QColor(132, 132, 26) # rgb(200, 132, 26)

COLOR_GROUP_BACKGROUND = QtGui.QColor(45, 48, 64) # rgb(45, 48, 64)
COLOR_GROUP_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_SHOW_BACKGROUND = QtGui.QColor(58, 61, 77) # rgb(58, 61, 77)
COLOR_SHOW_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_JOB_FOREGROUND = QtGui.QColor(153, 153, 153) # rgb(153, 153, 153)

#Icons
EAT_ICON_COLOUR = QtGui.QColor(255, 201, 25) # rgb(255, 201, 25)
RETRY_ICON_COLOUR = QtGui.QColor(124, 181, 110) # rgb(136, 181, 47)
KILL_ICON_COLOUR = QtGui.QColor(224, 52, 52) # rgb(224, 52, 52)
PAUSE_ICON_COLOUR = QtGui.QColor(88, 163, 209) # rgb(88, 163, 209)
PLAY_ICON_COLOUR = QtGui.QColor(88, 163, 209) # rgb(88, 163, 209)
EJECT_ICON_COLOUR = QtGui.QColor(207, 219, 227) # rgb(207, 219, 227)
DEFAULT_ICON_COLOUR = QtGui.QColor(135, 135, 135) # rgb(135, 135, 135)
BRIGHT_ICON_COLOUR = QtGui.QColor(230, 230, 230) # rgb(230, 230, 230)
SHOW_ICON_COLOUR = QtGui.QColor(204, 163, 187) # rgb(204, 163, 187)

#Log file Colors
LOG_TIME = QtGui.QColor(117, 146, 201) # rgb(117, 146, 201)
LOG_ERROR = QtGui.QColor(191, 77, 77) # rgb(191, 77, 77)
LOG_WARNING = QtGui.QColor(224, 182, 76) # rgb(224, 182, 76)
LOG_INFO = QtGui.QColor(163, 201, 197) # rgb(163, 201, 197)
LOG_COMPLETE = QtGui.QColor(132, 201, 12) # rgb(132, 201, 12)

# Host bar colours
USED_COLOUR = QtGui.QColor(201, 73, 66) # rgb(201, 73, 66)
FREE_COLOUR = QtGui.QColor(39, 73, 110) # rgb(39, 73, 110)

def name_grouping_colour(name):
    code = int(hashlib.md5(name).hexdigest(), 16) % (10 ** 8)
    red = ((code >> 27) & 31) << 3
    green = ((code >> 21) & 31) << 3
    blue = ((code >> 16) & 31) << 3
    return QtGui.QColor(red, green, blue, 100)
