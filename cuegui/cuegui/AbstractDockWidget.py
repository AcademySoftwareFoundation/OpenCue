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


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from PySide2 import QtCore
from PySide2 import QtWidgets

import cuegui.Plugins


class AbstractDockWidget(cuegui.Plugins.Plugin, QtWidgets.QDockWidget):

    closed = QtCore.Signal(object)
    enabled = QtCore.Signal()

    def __init__(self, parent, name, area = QtCore.Qt.LeftDockWidgetArea):
        QtWidgets.QDockWidget.__init__(self, name, parent)
        cuegui.Plugins.Plugin.__init__(self)

        self.parent = parent

        self.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetClosable | QtWidgets.QDockWidget.DockWidgetMovable)
        self.setObjectName(name)
        parent.addDockWidget(area, self)

        # Setup main vertical layout
        self.__layout = QtWidgets.QVBoxLayout()
        self.__layout.setContentsMargins(0, 0, 0, 0)

        # Required to get layout on DockWidget
        self.setWidget(QtWidgets.QWidget())
        self.widget().setLayout(self.__layout)

    def closeEvent(self, event):
        self.closed.emit(self)

    def showEvent(self, event):
        self.enabled.emit()

    def layout(self):
        return self.__layout
