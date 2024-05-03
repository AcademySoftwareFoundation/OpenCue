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


"""Module for handling global style setup."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import importlib

from qtpy import QtGui

import cuegui


DEFAULT_COLOR = "DarkPalette"
DEFAULT_ICON = "crystal"
DEFAULT_FONT = "Luxi Sans"
DEFAULT_FONT_SIZE = 10.0

# pylint: disable=global-statement

ColorTheme = None
IconTheme = None
Font = None


def loadColorTheme(name):
    """Changes the running color scheme of the app."""
    global ColorTheme
    ColorTheme = importlib.import_module('.%s' % name, package='cuegui')
    ColorTheme.init()


def setIconTheme(name):
    """Sets the icon theme for the app.

    Not sure if this can be changed on the fly yet."""
    global IconTheme
    IconTheme = importlib.import_module('.icons_rcc', package='cuegui.images.%s' % name)


def setFont(font):
    """Sets the application font."""
    global Font
    Font = font
    cuegui.app().setFont(font)


def init():
    """Initializes the global style settings."""
    settings = cuegui.app().settings
    loadColorTheme(settings.value("Style/colorTheme", DEFAULT_COLOR))
    setIconTheme(settings.value("Style/iconTheme", DEFAULT_ICON))

    font = QtGui.QFont(settings.value("Style/font", DEFAULT_FONT))
    fontSize = settings.value("Style/fontSize", DEFAULT_FONT_SIZE)
    font.setPointSizeF(fontSize)
    setFont(font)
