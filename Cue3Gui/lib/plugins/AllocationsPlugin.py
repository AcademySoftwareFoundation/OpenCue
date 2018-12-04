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


import os
import Cue3Gui
import Cue3

from PySide2 import QtGui, QtCore, QtWidgets

from decimal import Decimal

PLUGIN_NAME = "Allocations"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to allocations"
PLUGIN_REQUIRES = "CueCommander3"
PLUGIN_PROVIDES = "AllocationsDockWidget"

class AllocationsDockWidget(Cue3Gui.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        Cue3Gui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__monitorAllocations = MonitorAllocations(self)
        self.layout().addWidget(self.__monitorAllocations)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__monitorAllocations.getColumnVisibility,
                                      self.__monitorAllocations.setColumnVisibility)])

################################################################################
# Allocations
################################################################################

class MonitorAllocations(Cue3Gui.AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(Cue3Gui.Constants.TYPE_ALLOC)
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

        Cue3Gui.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = Cue3Gui.MenuActions(self, self.updateSoon, self.selectedObjects)

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True);
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
            return Cue3.api.getAllocations()
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        pass

    def dragEnterEvent(self, event):
        Cue3Gui.Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        Cue3Gui.Utils.dragMoveEvent(event, "application/x-host-ids")

    def dropEvent(self, event):
        item = self.itemAt(event.pos())

        if item.type() == Cue3Gui.Constants.TYPE_ALLOC:
            hostIds = Cue3Gui.Utils.dropEvent(event, "application/x-host-ids")
            hostNames = Cue3Gui.Utils.dropEvent(event, "application/x-host-names")
            if hostIds and \
               Cue3Gui.Utils.questionBoxYesNo(self, "Move hosts to new allocation?",
                                              "Move the hosts into the allocation: \"%s\"?" % item.iceObject.data.name,
                                              hostNames):
                item.iceObject.reparentHosts(hostIds)
                self.updateSoon()

class AllocationWidgetItem(Cue3Gui.AbstractWidgetItem):
    def __init__(self, object, parent):
        Cue3Gui.AbstractWidgetItem.__init__(self, Cue3Gui.Constants.TYPE_ALLOC, object, parent)
