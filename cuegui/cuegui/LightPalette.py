"""
The light widget color scheme used by image viewing applications.
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
    QtGui.qApp.setPalette(LightPalette())


def LightPalette():
    """The light widget color scheme I just made up.
    """
    # The 5 greys:
    # rgb(31, 31, 31)
    # rgb(110, 110, 110)
    # rgb(128, 128, 128)
    # rgb(168, 168, 168)
    # rgb(184, 184, 184)
    # rgb(214, 214, 214)

    p = QtGui.QPalette()

    c = QtGui.QColor(214, 214, 214) # rgb(214, 214, 214) main window colour
    p.setColor(p.Window, c)
    p.setColor(p.Button, c)

    c = QtGui.QColor(31, 31, 31) # rgb(31, 31, 31)
    p.setColor(p.WindowText, c)
    p.setColor(p.Text, c)
    p.setColor(p.ButtonText, c)
    p.setColor(p.BrightText, c)

    c = QtGui.QColor(60, 60, 80) # rgb(60, 60, 80)
    p.setColor(p.Link, c)
    c = QtGui.QColor(80, 60, 80) # rgb(80, 60, 80)
    p.setColor(p.LinkVisited, c)

    c = QtGui.QColor(184, 184, 184) # rgb(184, 184, 184) Primary table lines
    p.setColor(p.Base, c)
    c = QtGui.QColor(168, 168, 168) # rgb(168, 168, 168) Secondary table lines
    p.setColor(p.AlternateBase, c)

    c = QtGui.QColor(0, 0, 0) # rgb(0, 0, 0)
    p.setColor(p.Shadow, c)

    c = QtGui.QColor(128, 128, 128) # rgb(128, 128, 128)
    p.setColor(p.Dark, c)

    c = QtGui.QColor(168, 168, 168) # rgb(168, 168, 168) I dont think this is being used
    p.setColor(p.Mid, c)

    c = QtGui.QColor(184, 184, 184)# rgb(184, 184, 184) I dont think this is being used
    p.setColor(p.Midlight, c)

    c = QtGui.QColor(214, 214, 214) #rgb(214, 214, 214)
    p.setColor(p.Light, c)

    c = QtGui.QColor(31, 31, 31) #rgb(31, 31, 31)
    p.setColor(QtGui.QPalette.Disabled, p.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, p.Text, c)
    p.setColor(QtGui.QPalette.Disabled, p.ButtonText, c)

    c = QtGui.QColor(31, 31, 31) # rgb(31, 31, 31)
    p.setColor(QtGui.QPalette.Disabled, p.BrightText, c)

    c = QtGui.QColor(112, 167, 179) # rgb(112, 167, 179) controls selected and progress bar colours
    p.setColor(QtGui.QPalette.Highlight, c)

    return p

COLOR_JOB_PAUSED_BACKGROUND = QtGui.QColor(146, 152, 161) # rgb(146, 152, 161)
COLOR_JOB_DYING_BACKGROUND = QtGui.QColor(166, 124, 124) # rgb(166, 124, 124)
COLOR_JOB_TIMEOUT_BACKGROUND = QtGui.QColor(209, 153, 79) # rgb(209, 153, 79)
COLOR_JOB_PROGRESS_BACKGROUND = QtGui.QColor(140, 166, 124) # rgb(140, 166, 124)
COLOR_JOB_FINISHED_BACKGROUND = QtGui.QColor(138, 175, 181) # rgb(138, 175, 181)
COLOR_JOB_FINISHED_BAD_BACKGROUND = QtGui.QColor(138, 154, 181) # rgb(138, 154, 181)

COLOR_JOB_WITHOUT_PROCS = QtGui.QColor(204, 169, 108) # rgb(204, 169, 108)
COLOR_JOB_DEPENDED = QtGui.QColor(166, 155, 171) # rgb(166, 155, 171)
COLOR_JOB_HIGH_MEMORY = QtGui.QColor(201, 200, 89) # rgb(201, 200, 89)

COLOR_GROUP_BACKGROUND = QtGui.QColor(64, 64, 64) # rgb(64, 64, 64)
COLOR_GROUP_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_SHOW_BACKGROUND = QtGui.QColor(38, 38, 38) # rgb(38, 38, 38)
COLOR_SHOW_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_JOB_FOREGROUND = QtGui.QColor(31, 31, 31) # rgb(31, 31, 31)

#Icons
EAT_ICON_COLOUR = QtGui.QColor(224, 145, 27) # rgb(224, 145, 27)
RETRY_ICON_COLOUR = QtGui.QColor(123, 191, 55) # rgb(123, 191, 55)
KILL_ICON_COLOUR = QtGui.QColor(219, 31, 31) # rgb(219, 31, 31)
PAUSE_ICON_COLOUR = QtGui.QColor(61, 127, 166) # rgb(61, 127, 166)
PLAY_ICON_COLOUR = QtGui.QColor(61, 127, 166) # rgb(61, 127, 166)
EJECT_ICON_COLOUR = QtGui.QColor(125, 139, 150) # rgb(125, 139, 150)
DEFAULT_ICON_COLOUR = QtGui.QColor(94, 94, 94) # rgb(94, 94, 94)
BRIGHT_ICON_COLOUR = QtGui.QColor(48, 48, 48) # rgb(48, 48, 48)
SHOW_ICON_COLOUR = QtGui.QColor(232, 164, 19) # rgb(232, 164, 19)

#Log file Colors
LOG_TIME = QtGui.QColor(117, 54, 113) # rgb(117, 54, 113)
LOG_ERROR = QtGui.QColor(148, 9, 9) # rgb(148, 9, 9)
LOG_WARNING = QtGui.QColor(181, 121, 0) # rgb(181, 121, 0)
LOG_INFO = QtGui.QColor(65, 128, 20) # rgb(65, 128, 20)
LOG_COMPLETE = QtGui.QColor(87, 138, 0) # rgb(87, 138, 0)

# Host bar colours
USED_COLOUR = QtGui.QColor(201, 73, 66) # rgb(201, 73, 66)
FREE_COLOUR = QtGui.QColor(168, 168, 168) # rgb(168, 168, 168)

def name_grouping_colour(name):
    code = int(hashlib.md5(name).hexdigest(), 16) % (10 ** 8)
    red = ((code >> 27) & 31) << 3
    green = ((code >> 21) & 31) << 3
    blue = ((code >> 16) & 31) << 3
    return QtGui.QColor(red, green, blue, 100)
