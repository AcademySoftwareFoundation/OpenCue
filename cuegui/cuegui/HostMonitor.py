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


"""Widget for displaying a list of hosts with admin controls."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue

import cuegui.HostMonitorTree
import cuegui.Logger


log = cuegui.Logger.getLogger(__file__)


FILTER_HEIGHT = 20


class HostMonitor(QtWidgets.QWidget):
    """Widget for displaying a list of hosts with admin controls."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.hostMonitorTree = cuegui.HostMonitorTree.HostMonitorTree(self)

        # Setup main vertical layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(4)

        # This hlayout would contain any filter/control buttons
        hlayout = QtWidgets.QHBoxLayout()
        self.__filterByHostNameSetup(hlayout)
        self.__filterAllocationSetup(hlayout)
        self.__filterHardwareStateSetup(hlayout)
        hlayout.addStretch()
        self.__refreshToggleCheckBoxSetup(hlayout)
        self.__refreshButtonSetup(hlayout)
        self.__clearButtonSetup(hlayout)

        self.layout().addLayout(hlayout)
        self.layout().addWidget(self.hostMonitorTree)

        self.__viewHostsSetup()

        # pylint: disable=no-member
        if bool(int(QtGui.qApp.settings.value("AutoRefreshMonitorHost", 1))):
            self.updateRequest()
        # pylint: enable=no-member

        self.__filterByHostNameLastInput = None

    def updateRequest(self):
        """Requests an update of the displayed information."""
        self.hostMonitorTree.updateRequest()

    def getColumnVisibility(self):
        """Gets table column visibility."""
        return self.hostMonitorTree.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets table column visibility."""
        self.hostMonitorTree.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets the table column order."""
        return self.hostMonitorTree.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets the table column order."""
        self.hostMonitorTree.setColumnOrder(settings)

    # ==============================================================================
    # Text box to filter by host name
    # ==============================================================================
    def __filterByHostNameSetup(self, layout):
        btn = QtWidgets.QLineEdit(self)
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFixedWidth(155)
        btn.setFocusPolicy(QtCore.Qt.StrongFocus)
        layout.addWidget(btn)
        self.__filterByHostName = btn

        self.__filterByHostNameLastInput = None

        self.__filterByHostName.editingFinished.connect(self.__filterByHostNameHandle)

        btn = QtWidgets.QPushButton("Clr")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(24)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__filterByHostNameClear)

        self.__filterByHostNameClearBtn = btn

    def __filterByHostNameHandle(self):
        regex = str(self.__filterByHostName.text()).split()
        if regex:
            self.hostMonitorTree.hostSearch.options['regex'] = regex
        else:
            self.hostMonitorTree.hostSearch.options['regex'] = []
        if regex != self.__filterByHostNameLastInput:
            self.__filterByHostNameLastInput = regex
            self.hostMonitorTree.updateRequest()

    def __filterByHostNameClear(self):
        self.__filterByHostNameLastInput = ""
        self.__filterByHostName.setText("")
        self.hostMonitorTree.hostSearch.options['regex'] = []

    # ==============================================================================
    # Menu to filter by allocation
    # ==============================================================================
    def __filterAllocationSetup(self, layout):
        self.__filterAllocationList = sorted(
            [alloc.name() for alloc in opencue.api.getAllocations()])

        btn = QtWidgets.QPushButton("Filter Allocation")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        btn.setFlat(True)

        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        QtCore.QObject.connect(menu,
                               QtCore.SIGNAL("triggered(QAction*)"),
                               self.__filterAllocationHandle)

        for item in ["Clear", None] + self.__filterAllocationList:
            if item:
                a = QtWidgets.QAction(menu)
                a.setText(str(item))
                if item != "Clear":
                    a.setCheckable(True)
                menu.addAction(a)
            else:
                menu.addSeparator()

        layout.addWidget(btn)
        self.__filterAllocationButton = btn

    def __filterAllocationClear(self):
        """Clears the currently selected status menu items"""
        btn = self.__filterAllocationButton
        menu = btn.menu()
        for action in menu.actions():
            action.setChecked(False)
        self.hostMonitorTree.hostSearch.allocs = []

    def __filterAllocationHandle(self, action):
        """Called when an option in the filter status menu is triggered.
        Tells the HostMonitorTree widget what status to filter by.
        @param action: Defines the menu item selected
        @type  action: QAction"""
        __hostSearch = self.hostMonitorTree.hostSearch
        if action.text() == "Clear":
            for item in self.__filterAllocationButton.menu().actions():
                if item.isChecked():
                    if item.text() != "Clear":
                        __hostSearch.options['alloc'].remove(str(item.text()))
                    item.setChecked(False)
        else:
            allocs = __hostSearch.options.get('alloc', [])
            if action.isChecked():
                allocs.append(str(action.text()))
            elif allocs is not None:
                allocs.remove(str(action.text()))
            else:
                allocs = []
            __hostSearch.options['alloc'] = allocs

        self.hostMonitorTree.updateRequest()

    # ==============================================================================
    # Menu to filter by hardware state
    # ==============================================================================
    def __filterHardwareStateSetup(self, layout):
        self.__filterHardwareStateList = sorted(opencue.api.host_pb2.HardwareState.keys())

        btn = QtWidgets.QPushButton("Filter HardwareState")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0, 0, 0, 0)
        btn.setFlat(True)

        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        QtCore.QObject.connect(menu,
                               QtCore.SIGNAL("triggered(QAction*)"),
                               self.__filterHardwareStateHandle)

        for item in ["Clear", None] + self.__filterHardwareStateList:
            if item:
                a = QtWidgets.QAction(menu)
                a.setText(str(item))
                if item != "Clear":
                    a.setCheckable(True)
                menu.addAction(a)
            else:
                menu.addSeparator()

        layout.addWidget(btn)
        self.__filterHardwareStateButton = btn

    def __filterHardwareStateClear(self):
        """Clears the currently selected status menu items"""
        btn = self.__filterHardwareStateButton
        menu = btn.menu()
        for action in menu.actions():
            action.setChecked(False)
        self.hostMonitorTree.hostSearch.options['state'] = []

    def __filterHardwareStateHandle(self, action):
        """Called when an option in the filter status menu is triggered.
        Tells the HostMonitorTree widget what status to filter by.
        @param action: Defines the menu item selected
        @type  action: QAction"""
        __hostSearch = self.hostMonitorTree.hostSearch
        if action.text() == "Clear":
            for item in self.__filterHardwareStateButton.menu().actions():
                if item.isChecked():
                    if item.text() != "Clear":
                        __hostSearch.options['state'].remove(
                            getattr(opencue.api.host_pb2, str(item.text())))
                    item.setChecked(False)
        else:
            states = __hostSearch.options.get('state', [])
            if action.isChecked():
                states.append(getattr(opencue.api.host_pb2, str(action.text())))
            elif states is not None:
                states.remove(getattr(opencue.api.host_pb2, str(action.text())))
            else:
                states = []
            __hostSearch.options['state'] = states

        self.hostMonitorTree.updateRequest()

    # ==============================================================================
    # Checkbox to toggle auto-refresh
    # ==============================================================================
    def __refreshToggleCheckBoxSetup(self, layout):
        checkBox = QtWidgets.QCheckBox("Auto-refresh", self)
        layout.addWidget(checkBox)
        if self.hostMonitorTree.enableRefresh:
            checkBox.setCheckState(QtCore.Qt.Checked)
        QtCore.QObject.connect(checkBox,
                               QtCore.SIGNAL('stateChanged(int)'),
                               self.__refreshToggleCheckBoxHandle)
        __refreshToggleCheckBoxCheckBox = checkBox

    def __refreshToggleCheckBoxHandle(self, state):
        self.hostMonitorTree.enableRefresh = bool(state)
        # pylint: disable=no-member
        QtGui.qApp.settings.setValue("AutoRefreshMonitorHost", int(bool(state)))
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
        self.btn_refresh.clicked.connect(self.hostMonitorTree.updateRequest)
        self.hostMonitorTree.updated.connect(self.__refreshButtonDisableHandle)

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
        self.hostMonitorTree.ticksWithoutUpdate = -1
        self.__filterAllocationClear()
        self.__filterHardwareStateClear()
        self.__filterByHostNameClear()
        self.hostMonitorTree.clearFilters()

    # ==============================================================================
    # Monitors and handles the view_hosts signal
    # ==============================================================================
    def __viewHostsSetup(self):
        # pylint: disable=no-member
        QtGui.qApp.view_hosts.connect(self.__viewHostsHandle)
        # pylint: enable=no-member

    def __viewHostsHandle(self, hosts):
        self.__clearButtonHandle()
        self.hostMonitorTree.hostSearch.options['host'] = hosts
        self.__filterByHostName.setText(" ".join(hosts))
        self.hostMonitorTree.updateRequest()
