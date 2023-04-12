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


"""Splash screen displayed on initial application launch."""


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from builtins import object
import os
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets


__all__ = ["SplashWindow"]


class SplashWindow(object):
    """Splash screen displayed on initial application launch."""

    def __init__(self, app, app_name, version, resource_path):
        self.app = app

        self.WIDTH = 640
        self.HEIGHT = 346
        self.COLOR_TEXT = QtGui.QColor(180, 180, 180)
        self.MSG_FLAGS = QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom

        image = self._findSplash(app_name, version, resource_path)
        if image:
            pixmap = QtGui.QPixmap.fromImage(image)
            self.splash = QtWidgets.QSplashScreen(pixmap, QtCore.Qt.WindowStaysOnTopHint)
            self.splash.show()
            self.app.processEvents()

    def _findSplash(self, app_name, version, resource_path):
        """Returns the image for the splash screen.
           Checks: [RESOURCE_PATH]/Images/splash.[tag].png
           tag = Jan09 (current date), Jan10 (tomorrow) or 01
        """
        now = time.time()
        splashTags = [time.strftime("%b%d", time.localtime(now)),
                      time.strftime("%b%d", time.localtime(now + 86400)),
                      "01"]

        image = None
        for tag in splashTags:
            splashImage = os.path.join(resource_path,
                                       "splash.%s.png" % tag)
            image = self._generateSplashFromImage(splashImage)
            if image is not None:
                break

        if image is None:
            # pylint: disable=broad-except
            try:
                image = self._GenerateMissingSplash(app_name)
            except Exception:
                return None

        # pylint: disable=broad-except
        try:
            self._StampVersion(image, version)
        except Exception:
            pass
        return image

    @staticmethod
    def _generateSplashFromImage(imagePath):
        if os.path.isfile(imagePath):
            # pylint: disable=broad-except
            try:
                return imagePath and QtGui.QImage(imagePath)
            except Exception:
                pass
        return None

    def _GenerateMissingSplash(self, app_name):
        image = QtGui.QImage(self.WIDTH, self.HEIGHT, QtGui.QImage.Format_RGB32)
        painter = QtGui.QPainter(image)
        painter.fillRect(image.rect(), QtGui.QBrush(QtGui.QColor(50, 50, 50)))
        font = QtGui.QFont("serif",
                           min(self.WIDTH / len(app_name) * 1.4, 250), 75, True)
        painter.setFont(font)
        painter.setPen(QtGui.QColor(80, 80, 80))
        painter.drawText(30, image.height() - 60, app_name)
        return image

    def _StampVersion(self, image, version):
        if version:
            painter = QtGui.QPainter(image)
            painter.setPen(self.COLOR_TEXT)
            flags = QtCore.Qt.AlignRight | QtCore.Qt.AlignTop
            painter.drawText(image.rect(), flags, "Version " + version)

    def msg(self, message):
        """Display a message on the bottom right corner of the splash screen"""
        self.splash.showMessage(message, self.MSG_FLAGS, self.COLOR_TEXT)
        self.app.processEvents()

    def hide(self):
        """Hide the splash screen"""
        self.splash.hide()
