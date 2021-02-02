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


"""Widget for displaying a list of procs."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Logger
import cuegui.ProcMonitorTree
import cuegui.Utils


log = cuegui.Logger.getLogger(__file__)


FILTER_HEIGHT = 20


class ProcMonitor(QtWidgets.QWidget):
    """Widget for displaying a list of procs."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__filterByHostNameLastInput = None

        self.procMonitorTree = cuegui.ProcMonitorTree.ProcMonitorTree(self)

        # Setup main vertical layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(4)

        # This hlayout would contain any filter/control buttons
        hlayout = QtWidgets.QHBoxLayout()
        self.__filterByHostNameSetup(hlayout)
        hlayout.addStretch()
        self.__refreshToggleCheckBoxSetup(hlayout)
        self.__refreshButtonSetup(hlayout)
        self.__clearButtonSetup(hlayout)

        self.layout().addLayout(hlayout)
        self.layout().addWidget(self.procMonitorTree)

        self.__viewProcsSetup()
        self.__hostDoubleClickedSetup()

        self.__viewHostsSetup()

        # pylint: disable=no-member
        if bool(int(QtGui.qApp.settings.value("AutoRefreshMonitorProc", 1))):
            self.updateRequest()
        # pylint: enable=no-member

    def updateRequest(self):
        """Requests an update to the widget's contents."""
        self.procMonitorTree.updateRequest()

    def getColumnVisibility(self):
        """Gets a list of whether table columns are visible."""
        return self.procMonitorTree.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets whether table columns are visible."""
        self.procMonitorTree.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets table column order."""
        return self.procMonitorTree.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets table column order."""
        self.procMonitorTree.setColumnOrder(settings)

# ==============================================================================
# Text box to load procs by hostname
# ==============================================================================
    def __filterByHostNameSetup(self, layout):
        btn = QtWidgets.QLineEdit(self)
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFixedWidth(155)
        btn.setFocusPolicy(QtCore.Qt.StrongFocus)
        layout.addWidget(btn)
        self.__filterByHostName = btn

        btn = QtWidgets.QPushButton("Clr")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(24)
        layout.addWidget(btn)
        btn.clicked.connect(self.__filterByHostNameClear)
        self.__filterByHostNameClearBtn = btn

        self.__filterByHostNameLastInput = None
        self.__filterByHostName.editingFinished.connect(self.__filterByHostNameHandle)

    def __filterByHostNameHandle(self):
        hosts = str(self.__filterByHostName.text()).split()
        if hosts and hosts != self.__filterByHostNameLastInput:
            self.__filterByHostNameLastInput = hosts
            self.procMonitorTree.procSearch.options['host'] = hosts
            self.procMonitorTree.updateRequest()

    def __filterByHostNameClear(self):
        self.__filterByHostNameLastInput = ""
        self.__filterByHostName.setText("")
        self.procMonitorTree.procSearch.options['host'] = []

# ==============================================================================
# Checkbox to toggle auto-refresh
# ==============================================================================
    def __refreshToggleCheckBoxSetup(self, layout):
        checkBox = QtWidgets.QCheckBox("Auto-refresh", self)
        layout.addWidget(checkBox)
        if self.procMonitorTree.enableRefresh:
            checkBox.setCheckState(QtCore.Qt.Checked)
        checkBox.stateChanged.connect(self.__refreshToggleCheckBoxHandle)
        __refreshToggleCheckBoxCheckBox = checkBox

    def __refreshToggleCheckBoxHandle(self, state):
        self.procMonitorTree.enableRefresh = bool(state)
        # pylint: disable=no-member
        QtGui.qApp.settings.setValue("AutoRefreshMonitorProc", int(bool(state)))
        # pylint: enable=no-member

# ==============================================================================
# Button to refresh
# ==============================================================================
    def __refreshButtonSetup(self, layout):
        """Sets up the refresh button, adds it to the given layout
        @param layout: The layout to add the button to
        @type  layout: QLayout"""
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.setMaximumHeight(FILTER_HEIGHT)
        self.btn_refresh.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.btn_refresh)
        self.btn_refresh.clicked.connect(self.procMonitorTree.updateRequest)
        self.procMonitorTree.updated.connect(self.__refreshButtonDisableHandle)

    def __refreshButtonEnableHandle(self):
        """Called when the refresh button should be enabled"""
        self.btn_refresh.setEnabled(True)

    def __refreshButtonDisableHandle(self):
        """Called when the refresh button should be disabled"""
        self.btn_refresh.setEnabled(False)
        QtCore.QTimer.singleShot(5000, self.__refreshButtonEnableHandle)

# ==============================================================================
# Button to clear all filters
# ==============================================================================
    def __clearButtonSetup(self, layout):
        """Sets up the clear button, adds it to the given layout
        @param layout: The layout to add the button to
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Clear")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        layout.addWidget(btn)
        btn.clicked.connect(self.__clearButtonHandle)

    def __clearButtonHandle(self):
        """Called when the clear button is clicked"""
        self.procMonitorTree.ticksWithoutUpdate = -1
        self.__filterByHostNameClear()
        self.procMonitorTree.clearFilters()

# ==============================================================================
# Monitors and handles the view_procs signal
# ==============================================================================
    def __viewProcsSetup(self):
        # pylint: disable=no-member
        QtGui.qApp.view_procs.connect(self.__viewProcsHandle)
        # pylint: enable=no-member

    def __viewProcsHandle(self, hosts):
        self.procMonitorTree.procSearch.options['host'] = hosts
        self.procMonitorTree.updateRequest()

# ==============================================================================
# Views procs when a host is double clicked
# ==============================================================================
    def __hostDoubleClickedSetup(self):
        # pylint: disable=no-member
        QtGui.qApp.view_object.connect(self.__hostDoubleClickedHandle)
        # pylint: enable=no-member

    def __hostDoubleClickedHandle(self, rpcObject):
        if cuegui.Utils.isHost(rpcObject):
            self.procMonitorTree.procSearch.options['host'] = [rpcObject.data.name]
            self.procMonitorTree.updateRequest()

# ==============================================================================
# Monitors and handles the view_hosts signal
# ==============================================================================
    def __viewHostsSetup(self):
        # pylint: disable=no-member
        QtGui.qApp.view_hosts.connect(self.__viewHostsHandle)
        # pylint: enable=no-member

    def __viewHostsHandle(self, hosts):
        if hosts:
            self.__clearButtonHandle()
            self.procMonitorTree.procSearch.options['host'] = hosts
            self.__filterByHostName.setText(" ".join(hosts))
            self.procMonitorTree.updateRequest()
