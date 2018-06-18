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
Extends QDockWidget to provide a standard setup
"""

from Manifest import os, QtCore, QtGui

from Plugins import Plugin

class AbstractDockWidget(Plugin, QtGui.QDockWidget):
    def __init__(self, parent, name, area = QtCore.Qt.LeftDockWidgetArea):
        QtGui.QDockWidget.__init__(self, name, parent)
        Plugin.__init__(self)

        self.parent = parent

        self.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.setFeatures(QtGui.QDockWidget.DockWidgetClosable | QtGui.QDockWidget.DockWidgetMovable)
        self.setObjectName(name)
        parent.addDockWidget(area, self)

        # Setup main vertical layout
        self.__layout = QtGui.QVBoxLayout()
        self.__layout.setContentsMargins(0, 0, 0, 0)

        # Required to get layout on DockWidget
        self.setWidget(QtGui.QWidget())
        self.widget().setLayout(self.__layout)

    def closeEvent(self, event):
        self.emit(QtCore.SIGNAL("closed(PyQt_PyObject)"), self)

    def showEvent(self, event):
        self.emit(QtCore.SIGNAL("enabled()"))

    def layout(self):
        return self.__layout
