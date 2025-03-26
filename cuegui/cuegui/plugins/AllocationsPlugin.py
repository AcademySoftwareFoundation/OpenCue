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


"""Plugin for managing allocations."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import map

from qtpy import QtWidgets

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
    """Widget that lists allocations and allows management of them."""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__monitorAllocations = MonitorAllocations(self)
        self.layout().addWidget(self.__monitorAllocations)

        self.pluginRegisterSettings([("columnVisibility",
                                      self.__monitorAllocations.getColumnVisibility,
                                      self.__monitorAllocations.setColumnVisibility),
                                      ("columnOrder",
                                      self.__monitorAllocations.getColumnOrder,
                                      self.__monitorAllocations.setColumnOrder)])


################################################################################
# Allocations
################################################################################


class MonitorAllocations(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Inner widget that builds and displays the allocation list."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_ALLOC)
        self.addColumn("Name", 150, id=1,
                       data=lambda alloc: alloc.data.name)

        self.addColumn("Tag", 100, id=2,
                       data=lambda alloc: alloc.data.tag)

        self.addColumn("Cores", 50, id=3,
                       data=lambda allocation: int(allocation.data.stats.cores),
                       sort=lambda allocation: allocation.data.stats.cores)

        self.addColumn("Idle", 50, id=4,
                       data=lambda allocation: (int(allocation.totalAvailableCores())),
                       sort=lambda allocation: allocation.totalAvailableCores())

        self.addColumn("Locked", 65, id=5,
                       data=lambda allocation: int(allocation.totalLockedCores()),
                       sort=lambda allocation: allocation.totalLockedCores())

        self.addColumn("Down", 55, id=6,
                       data=lambda allocation: sum(int(host.cores())
                                                   for host in allocation.getHosts()
                                                   if host.state() == 1),
                       sort=lambda allocation: sum(int(host.cores())
                                                   for host in allocation.getHosts()
                                                   if host.state() == 1))

        self.addColumn("Repair", 65, id=7,
                       data=lambda allocation: sum(int(host.cores())
                                                   for host in allocation.getHosts()
                                                   if host.state() == 4),
                       sort=lambda allocation: sum(int(host.cores())
                                                   for host in allocation.getHosts()
                                                   if host.state() == 4))

        self.addColumn("Hosts", 55, id=8,
                       data=lambda alloc: alloc.data.stats.hosts,
                       sort=lambda alloc: alloc.data.stats.hosts)

        self.addColumn("Locked", 65, id=9,
                       data=lambda alloc: alloc.totalLockedHosts()
                                          + len([host for host in alloc.getHosts()
                                                     if host.lockState() == 2]),
                       sort=lambda alloc: alloc.totalLockedHosts()
                                          + len([host for host in alloc.getHosts()
                                                     if host.lockState() == 2]))

        self.addColumn("Down", 55, id=10,
                       data=lambda alloc: alloc.totalDownHosts(),
                       sort=lambda alloc: alloc.totalDownHosts())

        self.addColumn("Repair", 50, id=11,
                       data=lambda allocation: len([host
                                                    for host in allocation.getHosts()
                                                    if host.state() == 4]),
                       sort=lambda allocation: len([host
                                                    for host in allocation.getHosts()
                                                    if host.state() == 4]))

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        # pylint: disable=unused-private-member
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        self.app.facility_changed.connect(self._update)

        self.setUpdateInterval(60)

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        return AllocationWidgetItem(rpcObject, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return opencue.api.getAllocations()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""

    def dragEnterEvent(self, event):
        """Drag enter event"""
        cuegui.Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        """Drag move event"""
        cuegui.Utils.dragMoveEvent(event, "application/x-host-ids")

    def dropEvent(self, event):
        """Drop event"""
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

    def tick(self):
        """no-op"""


class AllocationWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget element representing a single allocation."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_ALLOC, rpcObject, parent)
