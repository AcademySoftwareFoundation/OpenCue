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


"""The dark widget color scheme used by image viewing applications."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import platform

from qtpy import QtGui
from qtpy import QtWidgets

import cuegui.Constants


def init():
    """Convenience function that takes the QApplication object for the
    application and configures the palette and style for the Plastique
    color scheme"""
    app = cuegui.app()
    app.setPalette(DarkPalette())
    if platform.system() in ['Darwin', 'Linux']:
        setDarkStyleSheet()
    elif platform.system() == 'Windows':
        app.setStyle('Fusion')
    else:
        app.setStyle(QtWidgets.QStyleFactory.create(cuegui.Constants.COLOR_THEME))


def setDarkStyleSheet():
    """Sets the stylesheet."""
    with open(cuegui.Constants.DARK_STYLE_SHEET, encoding='utf-8') as fp:
        cuegui.app().setStyleSheet(fp.read())


def DarkPalette():
    """The dark widget color scheme used by image viewing applications."""
    p = QtGui.QPalette()

    c = GreyF(0.175)
    p.setColor(QtGui.QPalette.Window, c)
    p.setColor(QtGui.QPalette.Button, c)

    c = GreyF(0.79)
    p.setColor(QtGui.QPalette.WindowText, c)
    p.setColor(QtGui.QPalette.Text, c)
    p.setColor(QtGui.QPalette.ButtonText, c)
    p.setColor(QtGui.QPalette.BrightText, c)

    c = ColorF(0.6, 0.6, 0.8)
    p.setColor(QtGui.QPalette.Link, c)
    c = ColorF(0.8, 0.6, 0.8)
    p.setColor(QtGui.QPalette.LinkVisited, c)

    c = GreyF(0.215)
    p.setColor(QtGui.QPalette.Base, c)
    c = GreyF(0.25)
    p.setColor(QtGui.QPalette.AlternateBase, c)

    c = GreyF(0.0)
    p.setColor(QtGui.QPalette.Shadow, c)

    c = GreyF(0.13)
    p.setColor(QtGui.QPalette.Dark, c)

    c = GreyF(0.21)
    p.setColor(QtGui.QPalette.Mid, c)

    c = GreyF(0.25)
    p.setColor(QtGui.QPalette.Midlight, c)

    c = GreyF(0.40)
    p.setColor(QtGui.QPalette.Light, c)

    c = ColorF(0.31, 0.31, 0.25)
    p.setColor(QtGui.QPalette.Highlight, c)

    c = GreyF(0.46)
    p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, c)
    p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, c)

    c = GreyF(0.55)
    p.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, c)

    return p


def GreyF(value):
    """Creates a grey color."""
    c = QtGui.QColor()
    c.setRgbF(value, value, value)
    return c


def ColorF(r, g, b):
    """Creates an RGB color."""
    c = QtGui.QColor()
    c.setRgbF(r, g, b)
    return c


COLOR_JOB_PAUSED_BACKGROUND = QtGui.QColor(49, 75, 87)
COLOR_JOB_DYING_BACKGROUND = QtGui.QColor(94, 33, 33)
COLOR_JOB_FINISHED_BACKGROUND = QtGui.QColor(55, 125, 55, 100)
COLOR_JOB_WITHOUT_PROCS = QtGui.QColor(68, 172, 65, 100)
COLOR_JOB_DEPENDED = QtGui.QColor(238, 130, 238, 100)
COLOR_JOB_HIGH_MEMORY = QtGui.QColor(132, 132, 26)

COLOR_GROUP_BACKGROUND = GreyF(0.18)
COLOR_GROUP_FOREGROUND = GreyF(0.79)
COLOR_SHOW_BACKGROUND = GreyF(0.13)
COLOR_SHOW_FOREGROUND = GreyF(0.79)
COLOR_JOB_FOREGROUND = GreyF(0.79)

#Log file Colors
LOG_TIME = QtGui.QColor(170, 149, 171)
LOG_ERROR = QtGui.QColor(224, 52, 52)
LOG_WARNING = QtGui.QColor(255, 201, 25)
LOG_INFO = QtGui.QColor(111, 140, 255)
LOG_COMPLETE = QtGui.QColor(132, 201, 12)

KILL_ICON_COLOUR = QtGui.QColor(224, 52, 52)
PAUSE_ICON_COLOUR = QtGui.QColor(88, 163, 209)
