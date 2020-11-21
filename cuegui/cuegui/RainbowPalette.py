"""
The rainbow widget color scheme used by image viewing applications.
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
    QtGui.qApp.setPalette(RainPalette())


def RainPalette():
    # rgb(245, 171, 198)
    # rgb(247, 207, 163)
    # rgb(250, 242, 185)
    # rgb(217, 250, 185)
    # rgb(217, 255, 252)
    # rgb(51, 51, 51)

    p = QtGui.QPalette()

    c = QtGui.QColor(49, 55, 61) # rgb(49, 55, 61) main window colour
    p.setColor(p.Window, c)
    p.setColor(p.Button, c)

    c = QtGui.QColor(184, 203, 209) # rgb(184, 203, 209)
    p.setColor(p.WindowText, c)
    p.setColor(p.Text, c)
    p.setColor(p.ButtonText, c)
    p.setColor(p.BrightText, c)

    c = QtGui.QColor(60, 60, 80) # rgb(60, 60, 80)
    p.setColor(p.Link, c)
    c = QtGui.QColor(80, 60, 80) # rgb(80, 60, 80)
    p.setColor(p.LinkVisited, c)

    c = QtGui.QColor(27, 31, 36) # rgb(27, 31, 36) Primary table lines
    p.setColor(p.Base, c)
    c = QtGui.QColor(38, 43, 48) # rgb(38, 43, 48) Secondary table lines
    p.setColor(p.AlternateBase, c)

    c = QtGui.QColor(51, 51, 51) # rgb(51, 51, 51)
    p.setColor(p.Shadow, c)

    c = QtGui.QColor(245, 171, 198) # rgb(245, 171, 198)
    p.setColor(p.Dark, c)

    c = QtGui.QColor(247, 207, 163) # rgb(247, 207, 163) I dont think this is being used
    p.setColor(p.Mid, c)

    c = QtGui.QColor(250, 242, 185)# rgb(250, 242, 185) I dont think this is being used
    p.setColor(p.Midlight, c)

    c = QtGui.QColor(217, 250, 185) #rgb(217, 250, 185)
    p.setColor(p.Light, c)

    c = QtGui.QColor(45, 48, 64) #rgb(45, 48, 64)
    p.setColor(QtGui.QPalette.Disabled, p.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, p.Text, c)
    p.setColor(QtGui.QPalette.Disabled, p.ButtonText, c)

    c = QtGui.QColor(28, 28, 28) # rgb(28, 28, 28)
    p.setColor(QtGui.QPalette.Disabled, p.BrightText, c)

    c = QtGui.QColor(137, 107, 156) # rgb(137, 107, 156) controls selected and progress bar colours
    p.setColor(QtGui.QPalette.Highlight, c)

    return p

COLOR_JOB_PAUSED_BACKGROUND = QtGui.QColor(30, 66, 102) # rgb(30, 66, 102)
COLOR_JOB_DYING_BACKGROUND = QtGui.QColor(130, 62, 62) # rgb(130, 62, 62)
COLOR_JOB_TIMEOUT_BACKGROUND = QtGui.QColor(199, 147, 80) # rgb(199, 147, 80)
COLOR_JOB_PROGRESS_BACKGROUND = QtGui.QColor(159, 199, 78) # rgb(159, 199, 78)
COLOR_JOB_FINISHED_BACKGROUND = QtGui.QColor(58, 180, 201) # rgb(58, 180, 201)
COLOR_JOB_FINISHED_BAD_BACKGROUND = QtGui.QColor(58, 151, 201) # rgb(58, 151, 201)

COLOR_JOB_WITHOUT_PROCS = QtGui.QColor(74, 82, 92) # rgb(74, 82, 92)
COLOR_JOB_DEPENDED = QtGui.QColor(67, 41, 89) # rgb(67, 41, 89)
COLOR_JOB_HIGH_MEMORY = QtGui.QColor(181, 119, 11) # rgb(181, 119, 11)

COLOR_GROUP_BACKGROUND = QtGui.QColor(115, 115, 115) # rgb(115, 115, 115)
COLOR_GROUP_FOREGROUND = QtGui.QColor(235, 235, 235) # #rgb(235, 235, 235)

COLOR_SHOW_BACKGROUND = QtGui.QColor(235, 235, 235) # rgb(235, 235, 235)
COLOR_SHOW_FOREGROUND = QtGui.QColor(59, 59, 59) # #rgb(59, 59, 59)

COLOR_JOB_FOREGROUND = QtGui.QColor(245, 233, 244) # rgb(245, 233, 244)

#Icons
EAT_ICON_COLOUR = QtGui.QColor(255, 201, 25) # rgb(255, 201, 25)
RETRY_ICON_COLOUR = QtGui.QColor(171, 214, 84) # rgb(171, 214, 84)
KILL_ICON_COLOUR = QtGui.QColor(245, 66, 66) # rgb(245, 66, 66)
PAUSE_ICON_COLOUR = QtGui.QColor(58, 197, 201) # rgb(58, 197, 201)
PLAY_ICON_COLOUR = QtGui.QColor(58, 197, 201) # rgb(58, 197, 201)
EJECT_ICON_COLOUR = QtGui.QColor(169, 222, 199) # rgb(169, 222, 199)
DEFAULT_ICON_COLOUR = QtGui.QColor(240, 237, 144) # rgb(240, 237, 144)
BRIGHT_ICON_COLOUR = QtGui.QColor(230, 230, 230) # rgb(230, 230, 230)
SHOW_ICON_COLOUR = QtGui.QColor(82, 183, 217) # rgb(82, 183, 217)

#Log file Colors
LOG_TIME = QtGui.QColor(169, 222, 199) # rgb(169, 222, 199)
LOG_ERROR = QtGui.QColor(224, 52, 52) # rgb(224, 52, 52)
LOG_WARNING = QtGui.QColor(217, 154, 28) # rgb(217, 154, 28)
LOG_INFO = QtGui.QColor(111, 140, 255) # rgb(111, 140, 255)
LOG_COMPLETE = QtGui.QColor(132, 201, 12) # rgb(132, 201, 12)

# Host bar colours
USED_COLOUR = QtGui.QColor(255, 201, 25) # rgb(255, 201, 25)
FREE_COLOUR = QtGui.QColor(96, 105, 115) # rgb(96, 105, 115)

def name_grouping_colour(name):
    code = int(hashlib.md5(name).hexdigest(), 16) % (10 ** 8)
    red = ((code >> 8) & 31) << 3
    green = ((code >> 21) & 31) << 3
    blue = ((code >> 16) & 31) << 3
    return QtGui.QColor(red, green, blue, 100)
