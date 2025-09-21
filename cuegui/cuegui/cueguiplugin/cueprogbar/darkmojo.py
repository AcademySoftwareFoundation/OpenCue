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
DarkMojo: Custom dark UI palette for CueGUI plugins

This module defines the "DarkMojo" dark color theme. It can be applied to any
Qt application or plugin to provide a clean, modern dark-mode aesthetic.

Usage:
    from .darkmojo import DarkMojoPalette
    app.setPalette(DarkMojoPalette())
    app.setStyle('DarkMojo')  # Optional custom style name

Exports:
    - DarkMojoPalette(): Returns a QtGui.QPalette object with custom dark colors
"""

from qtpy import QtGui

__all__ = ["DarkMojoPalette"]

def DarkMojoPalette() -> QtGui.QPalette:
    """
    Creates and returns a QtGui.QPalette using the DarkMojo color scheme.

    Returns:
        QtGui.QPalette: The fully customized dark theme palette.
    """
    palette = QtGui.QPalette()

    # Core widget background colors
    palette.setColor(QtGui.QPalette.Window, GreyF(0.175))
    palette.setColor(QtGui.QPalette.Button, GreyF(0.175))

    # Text and labels
    palette.setColor(QtGui.QPalette.WindowText, GreyF(0.70))
    palette.setColor(QtGui.QPalette.Text, GreyF(0.70))
    palette.setColor(QtGui.QPalette.ButtonText, GreyF(0.70))
    palette.setColor(QtGui.QPalette.BrightText, GreyF(0.70))

    # Links
    palette.setColor(QtGui.QPalette.Link, ColorF(0.6, 0.6, 0.8))
    palette.setColor(QtGui.QPalette.LinkVisited, ColorF(0.8, 0.6, 0.8))

    # Input fields, lists, and alternate rows
    palette.setColor(QtGui.QPalette.Base, GreyF(0.215))
    palette.setColor(QtGui.QPalette.AlternateBase, GreyF(0.25))

    # Shadows and 3D effects
    palette.setColor(QtGui.QPalette.Shadow, GreyF(0.0))
    palette.setColor(QtGui.QPalette.Dark, GreyF(0.13))
    palette.setColor(QtGui.QPalette.Mid, GreyF(0.21))
    palette.setColor(QtGui.QPalette.Midlight, GreyF(0.25))
    palette.setColor(QtGui.QPalette.Light, GreyF(0.40))

    # Selection highlight
    palette.setColor(QtGui.QPalette.Highlight, ColorF(0.31, 0.31, 0.25))

    # Disabled state styling
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, GreyF(0.46))
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, GreyF(0.46))
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, GreyF(0.46))
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, GreyF(0.55))

    return palette

def GreyF(value: float) -> QtGui.QColor:
    """
    Returns a QtGui.QColor with equal RGB values (grayscale) from a float.

    Args:
        value (float): Grayscale value from 0.0 (black) to 1.0 (white)

    Returns:
        QtGui.QColor: A grayscale color
    """
    color = QtGui.QColor()
    color.setRgbF(value, value, value)
    return color

def ColorF(r: float, g: float, b: float) -> QtGui.QColor:
    """
    Returns a QtGui.QColor from red, green, and blue float components.

    Args:
        r (float): Red component (0.0–1.0)
        g (float): Green component (0.0–1.0)
        b (float): Blue component (0.0–1.0)

    Returns:
        QtGui.QColor: A color with the given RGB values
    """
    color = QtGui.QColor()
    color.setRgbF(r, g, b)
    return color
