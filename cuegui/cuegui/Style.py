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


"""a module for handling global style setup"""


from PySide2 import QtGui


DEFAULT_COLOR = "DarkPalette"
DEFAULT_ICON = "crystal"
DEFAULT_FONT = "Luxi Sans"
DEFAULT_FONT_SIZE = 10.0

ColorTheme = None
IconTheme = None
Font = None


def loadColorTheme(name):
    """changes the running color scheme of the app"""
    global ColorTheme
    ColorTheme = __import__("%s" % name, globals(), locals())
    ColorTheme.init()


def setIconTheme(name):
    """stes the icon theme for the app, not sure if this
    can be changed on the fly yet"""
    global IconTheme
    module = "images.%s.icons_rcc" % name
    IconTheme = __import__(module,  globals(), locals())


def setFont(font):
    """sets the application font"""
    global Font
    Font = font
    QtGui.qApp.setFont(font)


def init():
    """initialize the global style settings"""
    settings = QtGui.qApp.settings
    loadColorTheme(settings.value("Style/colorTheme", DEFAULT_COLOR))
    setIconTheme(settings.value("Style/iconTheme", DEFAULT_ICON))

    font = QtGui.QFont(settings.value("Style/font", DEFAULT_FONT))
    fontSize = settings.value("Style/fontSize", DEFAULT_FONT_SIZE)
    font.setPointSizeF(fontSize)
    setFont(font)
