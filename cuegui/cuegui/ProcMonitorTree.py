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


"""Tree widget for displaying a list of procs."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
import time

from qtpy import QtCore
from qtpy import QtWidgets

import opencue

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class ProcMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of procs."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_PROC)
        self.addColumn(
            "Name", 150, id=1, data=lambda proc: proc.data.name, tip="Name of the running proc.")
        self.addColumn(
            "Cores", 50, id=2, data=lambda proc: ("%.2f" % proc.data.reserved_cores),
            tip="The number of cores reserved.")
        self.addColumn(
            "Mem Reserved", 100, id=3,
            data=lambda proc: cuegui.Utils.memoryToString(proc.data.reserved_memory),
            tip="The amount of memory reserved.")
        self.addColumn(
            "Mem Used", 100, id=4,
            data=lambda proc: cuegui.Utils.memoryToString(proc.data.used_memory),
            tip="The amount of memory used.")
        self.addColumn(
            "GPU Used", 100, id=5,
            data=lambda proc: cuegui.Utils.memoryToString(proc.data.reserved_gpu_memory),
            tip="The amount of gpu memory used.")
        self.addColumn(
            "Age", 60, id=6,
            data=lambda proc: cuegui.Utils.secondsToHHHMM(time.time() - proc.data.dispatch_time),
            tip="The age of the running frame.")
        self.addColumn(
            "Unbooked", 80, id=7, data=lambda proc: proc.data.unbooked,
            tip="If the proc has been unbooked.\n If it is unbooked then"
                "when the frame finishes the job will stop using this proc")
        self.addColumn(
            "Name", 300, id=8, data=lambda proc: proc.data.frame_name,
            tip="The name of the proc, includes frame number and layer name.")
        self.addColumn(
            "Job", 50, id=9, data=lambda proc: proc.data.job_name,
            tip="The job that this proc is running on.")

        self.procSearch = opencue.search.ProcSearch()

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.itemClicked.connect(self.__itemSingleClickedCopy)  # pylint: disable=no-member
        self.itemDoubleClicked.connect(self.__itemDoubleClickedViewLog)

        # Don't use the standard space bar to refresh
        self.app.request_update.connect(self.updateRequest)

        self.startTicksUpdate(40)
        # Don't start refreshing until the user sets a filter or hits refresh
        self.ticksWithoutUpdate = -1

        self.enableRefresh = bool(int(self.app.settings.value("AutoRefreshMonitorProc", 1)))

    def tick(self):
        if self.ticksWithoutUpdate >= self.updateInterval and \
           not self.window().isMinimized():
            self.ticksWithoutUpdate = 0
            self._update()
            return

        if (self.enableRefresh and
                self.updateInterval + 1 >= self.ticksWithoutUpdate >= 0):
            self.ticksWithoutUpdate += 1

    def facilityChanged(self):
        """Called when the facility is changed and removes then updates the proc
        list"""
        self.removeAllItems()
        self._update()

    def __itemSingleClickedCopy(self, item, col):
        """Called when an item is clicked on. Copies selected object names to
        the middle click selection clip board.
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        del item
        del col
        selected = [proc.data.name for proc in self.selectedObjects() if cuegui.Utils.isProc(proc)]
        if selected:
            QtWidgets.QApplication.clipboard().setText(",".join(selected))

    def __itemDoubleClickedViewLog(self, item, col):
        """Called when a proc is double clicked
        @type  item: QTreeWidgetItem
        @param item: The item double clicked on
        @type  col: int
        @param col: Column number double clicked on"""
        del col
        job_name = item.rpcObject.data.job_name
        self.app.view_object.emit(opencue.api.findJob(job_name))

    def clearFilters(self):
        """Removes all sorting and filtering to restore default state."""
        self.clearSelection()
        self.procSearch = opencue.search.ProcSearch()
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.removeAllItems()

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 999

    # pylint: disable=too-many-boolean-expressions
    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            # Refuse to update if no search criteria is defined
            if not self.procSearch.options.get('max_results') and \
               not self.procSearch.options.get('host') and \
               not self.procSearch.options.get('job') and \
               not self.procSearch.options.get('layer') and \
               not self.procSearch.options.get('show') and \
               not self.procSearch.options.get('alloc') and \
               not self.procSearch.options.get('memory_range') and \
               not self.procSearch.options.get('durationRange'):
                return []
            return opencue.api.getProcs(**self.procSearch.options)
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def _createItem(self, rpcObject, parent=None):
        """Creates and returns the proper item
        @type  rpcObject: Proc
        @param rpcObject: The object for this item
        @type  parent: QTreeWidgetItem
        @param parent: Optional parent for this item
        @rtype:  QTreeWidgetItem
        @return: The created item"""
        if not parent:
            parent = self
        return ProcWidgetItem(rpcObject, parent)

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.procs().addAction(menu, "view")
        self.__menuActions.procs().addAction(menu, "unbook")
        self.__menuActions.procs().addAction(menu, "kill")
        self.__menuActions.procs().addAction(menu, "unbookKill")
        menu.exec_(e.globalPos())


class ProcWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item representing a single proc."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_PROC, rpcObject, parent)
