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


"""Plugin for viewing the list of hosts and performing administrative tasks."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.AbstractDockWidget
import cuegui.HostMonitor
import cuegui.ProcMonitor


PLUGIN_NAME = "Monitor Hosts"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to hosts and procs"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "HostMonitorDockWidget"


class HostMonitorDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin for viewing the list of hosts and performing administrative tasks."""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__monitorHosts = cuegui.HostMonitor.HostMonitor(self)
        self.__monitorProcs = cuegui.ProcMonitor.ProcMonitor(self)
        self.__splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        self.layout().addWidget(self.__splitter)

        self.__splitter.addWidget(self.__monitorHosts)
        self.__splitter.addWidget(self.__monitorProcs)

        self.pluginRegisterSettings([("splitterSize",
                                      self.__splitter.sizes,
                                      self.__splitter.setSizes),
                                     ("hostColumnVisibility",
                                      self.__monitorHosts.getColumnVisibility,
                                      self.__monitorHosts.setColumnVisibility),
                                     ("procColumnVisibility",
                                      self.__monitorProcs.getColumnVisibility,
                                      self.__monitorProcs.setColumnVisibility),
                                      ("hostColumnOrder",
                                      self.__monitorHosts.getColumnOrder,
                                      self.__monitorHosts.setColumnOrder),
                                     ("procColumnOrder",
                                      self.__monitorProcs.getColumnOrder,
                                      self.__monitorProcs.setColumnOrder)])
