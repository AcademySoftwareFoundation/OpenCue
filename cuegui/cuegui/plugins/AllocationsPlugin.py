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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import map

from PySide2 import QtGui, QtWidgets

import opencue

import cuegui.AbstractDockWidget
import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

PLUGIN_NAME = "Allocations"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to allocations"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "AllocationsDockWidget"

class AllocationsDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__monitorAllocations = MonitorAllocations(self)
        self.layout().addWidget(self.__monitorAllocations)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__monitorAllocations.getColumnVisibility,
                                      self.__monitorAllocations.setColumnVisibility)])

################################################################################
# Allocations
################################################################################

class MonitorAllocations(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_ALLOC)
        self.addColumn("Name", 150, id=1,
                       data=lambda alloc: alloc.data.name)

        self.addColumn("Tag", 100, id=2,
                       data=lambda alloc: alloc.data.tag)

        self.addColumn("Cores", 45, id=3,
                       data=lambda allocation: allocation.data.stats.cores,
                       sort=lambda allocation: allocation.data.stats.cores)

        self.addColumn("Idle",45, id=4,
                       data=lambda allocation: (int(allocation.data.stats.available_cores)),
                       sort=lambda allocation: allocation.data.stats.available_cores)

        self.addColumn("Hosts", 45, id=5,
                       data=lambda alloc: alloc.data.stats.hosts,
                       sort=lambda alloc: alloc.data.stats.hosts)

        # It would be nice to display this again:
        #self.addColumn("Nimby", 40, id=6,
        #               data=lambda alloc:(alloc.totalNimbyLockedHosts()))

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        QtGui.qApp.facility_changed.connect(self._update)

        self.setUpdateInterval(60)

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return AllocationWidgetItem(object, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return opencue.api.getAllocations()
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        pass

    def dragEnterEvent(self, event):
        cuegui.Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        cuegui.Utils.dragMoveEvent(event, "application/x-host-ids")

    def dropEvent(self, event):
        item = self.itemAt(event.pos())

        if item.type() == cuegui.Constants.TYPE_ALLOC:
            hostIds = cuegui.Utils.dropEvent(event, "application/x-host-ids")
            hostNames = cuegui.Utils.dropEvent(event, "application/x-host-names")
            if hostIds and \
               cuegui.Utils.questionBoxYesNo(self, "Move hosts to new allocation?",
                                             "Move the hosts into the allocation: \"%s\"?" %
                                             item.rpcObject.data.name,
                                             hostNames):
                item.rpcObject.reparentHostIds(hostIds)
                self.updateSoon()

class AllocationWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    def __init__(self, object, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_ALLOC, object, parent)
