"""
The pink widget color scheme used by image viewing applications.
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
    QtGui.qApp.setPalette(PinkPalette())


def PinkPalette():
    # The 5 greys:
    # rgb(77, 22, 55)
    # rgb(191, 122, 163)
    # rgb(199, 145, 177)
    # rgb(204, 163, 187)
    # rgb(219, 186, 206)
    # rgb(235, 216, 227)

    p = QtGui.QPalette()

    c = QtGui.QColor(235, 216, 227) # rgb(235, 216, 227) main window colour
    p.setColor(p.Window, c)
    p.setColor(p.Button, c)

    c = QtGui.QColor(77, 22, 55) # rgb(77, 22, 55)
    p.setColor(p.WindowText, c)
    p.setColor(p.Text, c)
    p.setColor(p.ButtonText, c)
    p.setColor(p.BrightText, c)

    c = QtGui.QColor(60, 60, 80) # rgb(60, 60, 80)
    p.setColor(p.Link, c)
    c = QtGui.QColor(80, 60, 80) # rgb(80, 60, 80)
    p.setColor(p.LinkVisited, c)

    c = QtGui.QColor(219, 186, 206) # rgb(219, 186, 206) Primary table lines
    p.setColor(p.Base, c)
    c = QtGui.QColor(204, 163, 187) # rgb(204, 163, 187) Secondary table lines
    p.setColor(p.AlternateBase, c)

    c = QtGui.QColor(0, 0, 0) # rgb(0, 0, 0)
    p.setColor(p.Shadow, c)

    c = QtGui.QColor(199, 145, 177) # rgb(199, 145, 177)
    p.setColor(p.Dark, c)

    c = QtGui.QColor(204, 163, 187) # rgb(204, 163, 187) I dont think this is being used
    p.setColor(p.Mid, c)

    c = QtGui.QColor(219, 186, 206)# rgb(219, 186, 206) I dont think this is being used
    p.setColor(p.Midlight, c)

    c = QtGui.QColor(235, 216, 227) #rgb(235, 216, 227)
    p.setColor(p.Light, c)

    c = QtGui.QColor(77, 22, 55) #rgb(77, 22, 55)
    p.setColor(QtGui.QPalette.Disabled, p.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, p.Text, c)
    p.setColor(QtGui.QPalette.Disabled, p.ButtonText, c)

    c = QtGui.QColor(77, 22, 55) # rgb(77, 22, 55)
    p.setColor(QtGui.QPalette.Disabled, p.BrightText, c)

    c = QtGui.QColor(112, 167, 179) # rgb(112, 167, 179) controls selected and progress bar colours
    p.setColor(QtGui.QPalette.Highlight, c)

    return p

COLOR_JOB_PAUSED_BACKGROUND = QtGui.QColor(146, 152, 161) # rgb(146, 152, 161)
COLOR_JOB_DYING_BACKGROUND = QtGui.QColor(191, 105, 128) # rgb(191, 105, 128)
COLOR_JOB_TIMEOUT_BACKGROUND = QtGui.QColor(209, 153, 79) # rgb(209, 153, 79)
COLOR_JOB_PROGRESS_BACKGROUND = QtGui.QColor(140, 166, 124) # rgb(140, 166, 124)
COLOR_JOB_FINISHED_BACKGROUND = QtGui.QColor(138, 175, 181) # rgb(138, 175, 181)
COLOR_JOB_FINISHED_BAD_BACKGROUND = QtGui.QColor(138, 154, 181) # rgb(138, 154, 181)

COLOR_JOB_WITHOUT_PROCS = QtGui.QColor(204, 169, 108) # rgb(204, 169, 108)
COLOR_JOB_DEPENDED = QtGui.QColor(166, 155, 171) # rgb(166, 155, 171)
COLOR_JOB_HIGH_MEMORY = QtGui.QColor(201, 200, 89) # rgb(201, 200, 89)

COLOR_GROUP_BACKGROUND = QtGui.QColor(110, 13, 76) # rgb(110, 13, 76)
COLOR_GROUP_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_SHOW_BACKGROUND = QtGui.QColor(59, 10, 74) # rgb(59, 10, 74)
COLOR_SHOW_FOREGROUND = QtGui.QColor(212, 212, 212) # #rgb(212, 212, 212)

COLOR_JOB_FOREGROUND = QtGui.QColor(77, 22, 55) # rgb(77, 22, 55)

#Icons
EAT_ICON_COLOUR = QtGui.QColor(255, 200, 0) # rgb(255, 200, 0)
RETRY_ICON_COLOUR = QtGui.QColor(149, 199, 0) # rgb(149, 199, 0)
KILL_ICON_COLOUR = QtGui.QColor(219, 46, 115) # rgb(219, 46, 115)
PAUSE_ICON_COLOUR = QtGui.QColor(209, 177, 227) # rgb(209, 177, 227)
PLAY_ICON_COLOUR = QtGui.QColor(209, 177, 227) # rgb(209, 177, 227)
EJECT_ICON_COLOUR = QtGui.QColor(80, 140, 179) # rgb(80, 140, 179)
DEFAULT_ICON_COLOUR = QtGui.QColor(77, 22, 55) # rgb(77, 22, 55)
BRIGHT_ICON_COLOUR = QtGui.QColor(173, 69, 132) # rgb(173, 69, 132)
SHOW_ICON_COLOUR = QtGui.QColor(245, 197, 86) # rgb(245, 197, 86)

#Log file Colors
LOG_TIME = QtGui.QColor(217, 0, 217, 250) # rgb(217, 0, 217)
LOG_ERROR = QtGui.QColor(240, 25, 25, 250) # rgb(240, 25, 25)
LOG_WARNING = QtGui.QColor(249, 116, 0, 250) # rgb(249, 116, 0)
LOG_INFO = QtGui.QColor(111, 140, 255, 250) # rgb(111, 140, 255)
LOG_COMPLETE = QtGui.QColor(132, 201, 12) # rgb(132, 201, 12)

# Host bar colours
USED_COLOUR = QtGui.QColor(235, 195, 195) # rgb(235, 195, 195)
FREE_COLOUR = QtGui.QColor(150, 81, 81) # rgb(150, 81, 81)

def name_grouping_colour(name):
    code = int(hashlib.md5(name).hexdigest(), 16) % (10 ** 8)
    red = ((code >> 16) & 31) << 3
    green = ((code >> 21) & 31) << 3
    blue = ((code >> 27) & 31) << 3
    return QtGui.QColor(red, green, blue, 100)
