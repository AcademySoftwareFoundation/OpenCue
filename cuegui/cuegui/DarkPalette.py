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
The dark widget color scheme used by image viewing applications.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import platform

from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Constants


def init():
    """Convenience function that takes the QApplication object for the
    application and configures the palette and style for the Plastique
    color scheme"""
    QtGui.qApp.setPalette(DarkPalette())
    if platform.system() in ['Darwin', 'Linux']:
        setDarkStyleSheet()
    elif platform.system() == 'Windows':
        QtGui.qApp.setStyle('Fusion')
    else:
        QtGui.qApp.setStyle(QtWidgets.QStyleFactory.create(cuegui.Constants.COLOR_THEME))


def setDarkStyleSheet():
    QtGui.qApp.setStyleSheet(open(cuegui.Constants.DARK_STYLE_SHEET).read())


def DarkPalette():
    """The dark widget color scheme used by image viewing applications
    at Imageworks.
    """
    p = QtGui.QPalette()

    c = GreyF(0.175)
    p.setColor(p.Window, c)
    p.setColor(p.Button, c)

    c = GreyF(0.79)
    p.setColor(p.WindowText, c)
    p.setColor(p.Text, c)
    p.setColor(p.ButtonText, c)
    p.setColor(p.BrightText, c)

    c = ColorF(0.6, 0.6, 0.8)
    p.setColor(p.Link, c)
    c = ColorF(0.8, 0.6, 0.8)
    p.setColor(p.LinkVisited, c)

    c = GreyF(0.215)
    p.setColor(p.Base, c)
    c = GreyF(0.25)
    p.setColor(p.AlternateBase, c)

    c = GreyF(0.0)
    p.setColor(p.Shadow, c)

    c = GreyF(0.13)
    p.setColor(p.Dark, c)

    c = GreyF(0.21)
    p.setColor(p.Mid, c)

    c = GreyF(0.25)
    p.setColor(p.Midlight, c)

    c = GreyF(0.40)
    p.setColor(p.Light, c)

    c = ColorF(0.31, 0.31, 0.25)
    p.setColor(p.Highlight, c)

    c = GreyF(0.46)
    p.setColor(QtGui.QPalette.Disabled, p.WindowText, c)
    p.setColor(QtGui.QPalette.Disabled, p.Text, c)
    p.setColor(QtGui.QPalette.Disabled, p.ButtonText, c)

    c = GreyF(0.55)
    p.setColor(QtGui.QPalette.Disabled, p.BrightText, c)

    return p


def GreyF(value):
    c = QtGui.QColor()
    c.setRgbF(value, value, value)
    return c


def ColorF(r, g, b):
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
