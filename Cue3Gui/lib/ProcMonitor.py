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


from Manifest import os, QtCore, QtGui, Cue3

from MenuActions import MenuActions
import Utils
import Constants
import Logger

from ProcMonitorTree import ProcMonitorTree

log = Logger.getLogger(__file__)

FILTER_HEIGHT = 20

class ProcMonitor(QtGui.QWidget):
    """This contains the frame list table with controls at the top"""
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.procMonitorTree = ProcMonitorTree(self)

        # Setup main vertical layout
        layout = QtGui.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(4)

        # This hlayout would contain any filter/control buttons
        hlayout = QtGui.QHBoxLayout()
        self.__filterByHostNameSetup(hlayout)   # Menu to filter by proc name
        hlayout.addStretch()
        self.__refreshToggleCheckBoxSetup(hlayout) # Checkbox to disable auto refresh
        self.__refreshButtonSetup(hlayout)    # Button to refresh
        self.__clearButtonSetup(hlayout)      # Button to clear all filters

        self.layout().addLayout(hlayout)
        self.layout().addWidget(self.procMonitorTree)

        self.__viewProcsSetup()               # For view_hosts signal
        self.__hostDoubleClickedSetup()       # Views procs when a host is double clicked

        self.__viewHostsSetup()               # For view_hosts signal

    def updateRequest(self):
        self.procMonitorTree.updateRequest()

    def getColumnVisibility(self):
        return self.procMonitorTree.getColumnVisibility()

    def setColumnVisibility(self, settings):
        self.procMonitorTree.setColumnVisibility(settings)

# ==============================================================================
# Text box to load procs by hostname
# ==============================================================================
    def __filterByHostNameSetup(self, layout):
        btn = QtGui.QLineEdit(self)
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFixedWidth(155)
        btn.setFocusPolicy(QtCore.Qt.StrongFocus)
        layout.addWidget(btn)
        self.__filterByHostName = btn

        btn = QtGui.QPushButton("Clr")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(24)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__filterByHostNameClear)
        self.__filterByHostNameClearBtn = btn

        self.__filterByHostNameLastInput = None

        QtCore.QObject.connect(self.__filterByHostName,
                               QtCore.SIGNAL('editingFinished()'),
                               self.__filterByHostNameHandle)

    def __filterByHostNameHandle(self):
        hosts = str(self.__filterByHostName.text()).split()
        if hosts and hosts != self.__filterByHostNameLastInput:
            self.__filterByHostNameLastInput = hosts
            self.procMonitorTree.procSearch.hosts = hosts
            self.procMonitorTree.updateRequest()

    def __filterByHostNameClear(self):
        self.__filterByHostNameLastInput = ""
        self.__filterByHostName.setText("")
        self.procMonitorTree.procSearch.hosts = []

# ==============================================================================
# Checkbox to toggle auto-refresh
# ==============================================================================
    def __refreshToggleCheckBoxSetup(self, layout):
        checkBox = QtGui.QCheckBox("Auto-refresh", self)
        layout.addWidget(checkBox)
        if self.procMonitorTree.enableRefresh:
            checkBox.setCheckState(QtCore.Qt.Checked)
        QtCore.QObject.connect(checkBox,
                               QtCore.SIGNAL('stateChanged(int)'),
                               self.__refreshToggleCheckBoxHandle)
        __refreshToggleCheckBoxCheckBox = checkBox

    def __refreshToggleCheckBoxHandle(self, state):
        self.procMonitorTree.enableRefresh = bool(state)

# ==============================================================================
# Button to refresh
# ==============================================================================
    def __refreshButtonSetup(self, layout):
        """Sets up the refresh button, adds it to the given layout
        @param layout: The layout to add the button to
        @type  layout: QLayout"""
        self.btn_refresh = QtGui.QPushButton("Refresh")
        self.btn_refresh.setMaximumHeight(FILTER_HEIGHT)
        self.btn_refresh.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.btn_refresh)
        QtCore.QObject.connect(self.btn_refresh,
                               QtCore.SIGNAL('clicked()'),
                               self.procMonitorTree.updateRequest)

        QtCore.QObject.connect(self.procMonitorTree,
                               QtCore.SIGNAL("updated()"),
                               self.__refreshButtonDisableHandle)

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
        btn = QtGui.QPushButton("Clear")
        btn.setMaximumHeight(FILTER_HEIGHT)
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.__clearButtonHandle)

    def __clearButtonHandle(self):
        """Called when the clear button is clicked"""
        self.procMonitorTree.ticksWithoutUpdate = -1
        self.__filterByHostNameClear()
        self.procMonitorTree.clearFilters()

# ==============================================================================
# Monitors and handles the view_procs signal
# ==============================================================================
    def __viewProcsSetup(self):
        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('view_procs(PyQt_PyObject)'),
                               self.__viewProcsHandle)

    def __viewProcsHandle(self, hosts):
        self.procMonitorTree.procSearch.hosts = hosts
        self.procMonitorTree.updateRequest()

# ==============================================================================
# Views procs when a host is double clicked
# ==============================================================================
    def __hostDoubleClickedSetup(self):
        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('view_object(PyQt_PyObject)'),
                               self.__hostDoubleClickedHandle)

    def __hostDoubleClickedHandle(self, rpcObject):
        if Utils.isHost(rpcObject):
            self.procMonitorTree.procSearch.hosts = [rpcObject.data.name]
            self.procMonitorTree.updateRequest()

# ==============================================================================
# Monitors and handles the view_hosts signal
# ==============================================================================
    def __viewHostsSetup(self):
        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('view_hosts(PyQt_PyObject)'),
                               self.__viewHostsHandle)

    def __viewHostsHandle(self, hosts):
        if hosts:
            self.__clearButtonHandle()
            self.procMonitorTree.procSearch.hosts = hosts
            self.__filterByHostName.setText(" ".join(hosts))
            self.procMonitorTree.updateRequest()
