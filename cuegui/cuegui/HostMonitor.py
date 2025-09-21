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

from qtpy import QtCore
from qtpy import QtWidgets

import opencue

import cuegui.HostMonitorTree
import cuegui.Logger


log = cuegui.Logger.getLogger(__file__)


FILTER_HEIGHT = 20


class HostMonitor(QtWidgets.QWidget):
    """Widget for displaying a list of hosts with admin controls."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.app = cuegui.app()

        self.__filterByHostNameLastInput = None
        self.__filterOSList = []
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
        self.__filterLockStateSetup(hlayout)
        self.__filterOSSetup(hlayout)
        hlayout.addStretch()
        self.__refreshToggleCheckBoxSetup(hlayout)
        self.__refreshButtonSetup(hlayout)
        self.__clearButtonSetup(hlayout)

        self.layout().addLayout(hlayout)
        self.layout().addWidget(self.hostMonitorTree)

        self.__viewHostsSetup()

        if bool(int(self.app.settings.value("AutoRefreshMonitorHost", 1))):
            self.updateRequest()

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
        btn.setMinimumWidth(155)
        btn.setMaximumWidth(345)
        btn.sizeHint().setWidth(345)
        btn.setFocusPolicy(QtCore.Qt.StrongFocus)
        layout.addWidget(btn)
        self.__filterByHostName = btn

        self.__filterByHostNameLastInput = None

        self.__filterByHostName.editingFinished.connect(self.__filterByHostNameHandle)  # pylint: disable=no-member

        btn = QtWidgets.QPushButton("Clr")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(24)
        layout.addWidget(btn)
        # pylint: disable=no-member
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__filterByHostNameClear)
        # pylint: disable=unused-private-member
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
        # pylint: disable=no-member
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

        # pylint: disable=no-member
        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        QtCore.QObject.connect(menu,
                               QtCore.SIGNAL("triggered(QAction*)"),
                               self.__filterHardwareStateHandle)
        # pylint: enable=no-member
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
    # Menu to filter by lock state
    # ==============================================================================
    def __filterLockStateSetup(self, layout):
        self.__filterLockStateList = sorted(opencue.api.host_pb2.LockState.keys())

        btn = QtWidgets.QPushButton("Filter LockState")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0, 0, 0, 0)
        btn.setFlat(True)

        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        QtCore.QObject.connect(menu,
                               QtCore.SIGNAL("triggered(QAction*)"),
                               self.__filterLockStateHandle)

        for item in ["Clear", None] + self.__filterLockStateList:
            if item:
                a = QtWidgets.QAction(menu)
                a.setText(str(item))
                if item != "Clear":
                    a.setCheckable(True)
                menu.addAction(a)
            else:
                menu.addSeparator()

        layout.addWidget(btn)
        self.__filterLockStateButton = btn

    def __filterLockStateClear(self):
        """Clears the currently selected lock state menu items"""
        btn = self.__filterLockStateButton
        menu = btn.menu()
        for action in menu.actions():
            action.setChecked(False)
        self.hostMonitorTree.hostSearch.options['lock_state'] = []

    def __filterLockStateHandle(self, action):
        """Called when an option in the filter lock state menu is triggered.
        Tells the HostMonitorTree widget what lock state to filter by.
        @param action: Defines the menu item selected
        @type  action: QAction"""
        __hostSearch = self.hostMonitorTree.hostSearch
        if action.text() == "Clear":
            self.__clearLockStateFilter(__hostSearch)
        else:
            self.__updateLockStateFilter(__hostSearch, action)

        self.hostMonitorTree.updateRequest()

    def __clearLockStateFilter(self, __hostSearch):
        """
        Clears the currently selected lock state menu items and updates the search options.
        @param __hostSearch: The host search criteria object to update.
        @type __hostSearch: HostSearchCriteria
        """
        for item in self.__filterLockStateButton.menu().actions():
            if item.isChecked() and item.text() != "Clear":
                # Remove the lock state from the search options
                __hostSearch.options['lock_state'].remove(
                    getattr(opencue.api.host_pb2, str(item.text())))
            # Uncheck the menu item
            item.setChecked(False)

    def __updateLockStateFilter(self, __hostSearch, action):
        """
        Updates the lock state filter based on the selected action.
        @param __hostSearch: The host search criteria object to update.
        @type __hostSearch: HostSearchCriteria
        @param action: The action that was triggered.
        @type action: QAction
        """
        # Get the current lock states from the search options
        lock_states = __hostSearch.options.get('lock_state', [])
        # Get the lock state corresponding to the action text
        lock_state = getattr(opencue.api.host_pb2, str(action.text()))

        if action.isChecked():
            # Add the lock state if the action is checked
            lock_states.append(lock_state)
        else:
            # Remove the lock state if the action is unchecked
            lock_states.remove(lock_state)

        # Update the search options with the new lock states
        __hostSearch.options['lock_state'] = lock_states

    # ==============================================================================
    # Menu to filter by OS
    # ==============================================================================
    def __filterOSSetup(self, layout):
        """Sets up the OS filter dropdown menu.
        Creates a dropdown filter for operating systems that dynamically populates
        with OS values from actual hosts via updateOSFilterList.
        @param layout: The layout to add the filter button to
        @type  layout: QLayout"""

        # Initial placeholder - will be populated dynamically by updateOSFilterList()
        # when hosts are loaded. This shows a clear indication that real OS values
        # haven't been loaded yet.
        self.__filterOSList = ["Not Loaded"]

        btn = QtWidgets.QPushButton("Filter OS")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0, 0, 0, 0)
        btn.setFlat(True)

        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        QtCore.QObject.connect(menu,
                               QtCore.SIGNAL("triggered(QAction*)"),
                               self.__filterOSHandle)

        for item in ["Clear", None] + self.__filterOSList:
            if item:
                a = QtWidgets.QAction(menu)
                a.setText(str(item))
                if item != "Clear":
                    a.setCheckable(True)
                menu.addAction(a)
            else:
                menu.addSeparator()

        layout.addWidget(btn)
        self.__filterOSButton = btn

    def __filterOSClear(self):
        """Clears the currently selected OS menu items"""
        btn = self.__filterOSButton
        menu = btn.menu()
        for action in menu.actions():
            action.setChecked(False)
        self.hostMonitorTree.hostSearch.options['os_filter'] = []

    def __filterOSHandle(self, action):
        """Called when an option in the filter OS menu is triggered.
        Tells the HostMonitorTree widget what OS to filter by.
        @param action: Defines the menu item selected
        @type  action: QAction"""
        __hostSearch = self.hostMonitorTree.hostSearch
        if action.text() == "Clear":
            self.__clearOSFilter(__hostSearch)
        else:
            self.__updateOSFilter(__hostSearch, action)

        self.hostMonitorTree.updateRequest()

    def __clearOSFilter(self, __hostSearch):
        """
        Clears the currently selected OS menu items and updates the search options.
        @param __hostSearch: The host search criteria object to update.
        @type __hostSearch: HostSearchCriteria
        """
        for item in self.__filterOSButton.menu().actions():
            if item.isChecked() and item.text() != "Clear":
                # Remove the OS from the search options
                __hostSearch.options['os_filter'].remove(str(item.text()))
            # Uncheck the menu item
            item.setChecked(False)

    def __updateOSFilter(self, __hostSearch, action):
        """
        Updates the OS filter based on the selected action.
        @param __hostSearch: The host search criteria object to update.
        @type __hostSearch: HostSearchCriteria
        @param action: The action that was triggered.
        @type action: QAction
        """
        # Get the current OS filters from the search options
        os_filters = __hostSearch.options.get('os_filter', [])
        # Get the OS corresponding to the action text
        os_name = str(action.text())

        if action.isChecked():
            # Add the OS if the action is checked
            os_filters.append(os_name)
        else:
            # Remove the OS if the action is unchecked
            os_filters.remove(os_name)

        # Update the search options with the new OS filters
        __hostSearch.options['os_filter'] = os_filters

    def updateOSFilterList(self, os_values):
        """Updates the OS filter list with values from actual hosts.
        @param os_values: Set of OS values found in hosts
        @type  os_values: set"""
        if not os_values:
            return

        # Convert set to sorted list and update the filter list
        new_os_list = sorted(os_values)
        if new_os_list != self.__filterOSList:
            self.__filterOSList = new_os_list

            # Rebuild the menu with new OS values
            menu = self.__filterOSButton.menu()
            menu.clear()

            # Add Clear option and separator
            clear_action = QtWidgets.QAction(menu)
            clear_action.setText("Clear")
            menu.addAction(clear_action)
            menu.addSeparator()

            # Add OS options
            for os_name in self.__filterOSList:
                action = QtWidgets.QAction(menu)
                action.setText(str(os_name))
                action.setCheckable(True)
                menu.addAction(action)

    # ==============================================================================
    # Checkbox to toggle auto-refresh
    # ==============================================================================
    def __refreshToggleCheckBoxSetup(self, layout):
        # pylint: disable=no-member
        checkBox = QtWidgets.QCheckBox("Auto-refresh", self)
        layout.addWidget(checkBox)
        if self.hostMonitorTree.enableRefresh:
            checkBox.setCheckState(QtCore.Qt.Checked)
        QtCore.QObject.connect(checkBox,
                               QtCore.SIGNAL('stateChanged(int)'),
                               self.__refreshToggleCheckBoxHandle)
        __refreshToggleCheckBoxCheckBox = checkBox
        # pylint: enable=no-member

    def __refreshToggleCheckBoxHandle(self, state):
        self.hostMonitorTree.enableRefresh = bool(state)
        self.app.settings.setValue("AutoRefreshMonitorHost", int(bool(state)))

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
        self.btn_refresh.clicked.connect(self.hostMonitorTree.updateRequest)  # pylint: disable=no-member
        self.hostMonitorTree.updated.connect(self.__refreshButtonDisableHandle)

    def __refreshButtonEnableHandle(self):
        """Called when the refresh button should be enabled"""
        self.btn_refresh.setEnabled(True)

    def __refreshButtonDisableHandle(self):
        """Called when the refresh button should be disabled"""
        self.btn_refresh.setEnabled(False)
        QtCore.QTimer.singleShot(5000, self.__refreshButtonEnableHandle) # pylint: disable=no-member

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
        btn.clicked.connect(self.__clearButtonHandle)  # pylint: disable=no-member

    def __clearButtonHandle(self):
        """Called when the clear button is clicked"""
        self.hostMonitorTree.ticksWithoutUpdate = -1
        self.__filterAllocationClear()
        self.__filterHardwareStateClear()
        self.__filterLockStateClear()
        self.__filterOSClear()
        self.__filterByHostNameClear()
        self.hostMonitorTree.clearFilters()

    # ==============================================================================
    # Monitors and handles the view_hosts signal
    # ==============================================================================
    def __viewHostsSetup(self):
        self.app.view_hosts.connect(self.__viewHostsHandle)

    def __viewHostsHandle(self, hosts):
        self.__clearButtonHandle()
        self.hostMonitorTree.hostSearch.options['host'] = hosts
        self.__filterByHostName.setText(" ".join(hosts))
        self.hostMonitorTree.updateRequest()
