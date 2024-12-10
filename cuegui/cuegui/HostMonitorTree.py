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


"""Tree widget for displaying a list of hosts."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import map
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import opencue
from opencue.compiled_proto.host_pb2 import HardwareState
from opencue.compiled_proto.host_pb2 import LockState
from opencue.compiled_proto.host_pb2 import ThreadMode

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.ItemDelegate
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Style
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

COMMENT_COLUMN = 1


class HostMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of hosts."""

    def __init__(self, parent):

        self.startColumnsForType(cuegui.Constants.TYPE_HOST)
        self.addColumn("Name", 150, id=1,
                       data=lambda host: host.data.name,
                       tip="The hostname.")
        self.addColumn("_Comment", 20, id=2,
                       sort=lambda host: host.data.has_comment,
                       tip="A comment icon will appear if a host has a comment. You\n"
                           "may click on it to view the comments.")
        self.addColumn("Load %", 55, id=3,
                       data=lambda host: ("%3.0f%%" % (host.data.load / host.data.cores)),
                       sort=lambda host: (host.data.load / host.data.cores),
                       tip="The host load average compared to the number of cores\n"
                           "as a percent. Meaning a load of 8 on an 8 core machine\n"
                           "will show 100%. A percentage much over 100% is an\n"
                           "indication that a frame is using more cores than it\n"
                           "reserved. If all cores are reserved and the percentage\n"
                           "is way below 100% then the cpu is underutilized.")
        self.addColumn("Swap", 70, id=4,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_swap),
                       sort=lambda host: host.data.free_swap,
                       delegate=cuegui.ItemDelegate.HostSwapBarDelegate,
                       tip="The amount of used swap (red) vs available swap (green)")
        self.addColumn("Physical", 70, id=5,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_memory),
                       sort=lambda host: host.data.free_memory,
                       delegate=cuegui.ItemDelegate.HostMemBarDelegate,
                       tip="The amount of used memory (red) vs available phys memory (green)")
        self.addColumn("GPU Memory", 70, id=6,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_gpu_memory),
                       sort=lambda host: host.data.free_gpu_memory,
                       delegate=cuegui.ItemDelegate.HostGpuBarDelegate,
                       tip="The amount of used gpu memory (red) vs available gpu memory (green)")
        self.addColumn("Total Memory", 60, id=7,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.memory),
                       sort=lambda host: host.data.total_memory,
                       tip="The total amount of available memory.\n\n"
                           "Takes into consideration free memory and cached memory.")
        self.addColumn("Idle Memory", 60, id=8,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.idle_memory),
                       sort=lambda host: host.data.idle_memory,
                       tip="The amount of unreserved memory.")
        self.addColumn("Temp available", 70, id=9,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_mcp),
                       sort=lambda host: host.data.free_mcp,
                       tip="The amount of free space in /mcp/")
        self.addColumn("Cores", 60, id=10,
                       data=lambda host: "%.2f" % host.data.cores,
                       sort=lambda host: host.data.cores,
                       tip="The total number of cores.\n\n"
                           "On a frame it is the number of cores reserved.")
        self.addColumn("Idle Cores", 60, id=11,
                       data=lambda host: "%.2f" % host.data.idle_cores,
                       sort=lambda host: host.data.idle_cores,
                       tip="The number of cores that are not reserved.")
        self.addColumn("GPUs", 50, id=12,
                       data=lambda host: "%d" % host.data.gpus,
                       sort=lambda host: host.data.gpus,
                       tip="The total number of gpus.\n\n"
                           "On a frame it is the number of gpus reserved.")
        self.addColumn("Idle GPUs", 50, id=13,
                       data=lambda host: "%d" % host.data.idle_gpus,
                       sort=lambda host: host.data.idle_gpus,
                       tip="The number of gpus that are not reserved.")
        self.addColumn("GPU Mem", 50, id=14,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.gpu_memory),
                       sort=lambda host: host.data.gpu_memory,
                       tip="The total amount of reservable gpu memory.\n\n"
                           "On a frame it is the amount of gpu memory reserved.")
        self.addColumn("Gpu Mem Idle", 50, id=15,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.idle_gpu_memory),
                       sort=lambda host: host.data.idle_gpu_memory,
                       tip="The amount of unreserved gpu memory.")
        self.addColumn("Ping", 50, id=16,
                       data=lambda host: int(time.time() - host.data.ping_time),
                       sort=lambda host: host.data.ping_time,
                       tip="The number of seconds since the cuebot last received\n"
                           "a report from the host. A host is configured to report\n"
                           "in every 60 seconds so a number larger than this\n"
                           "indicates a problem")
        self.addColumn("Hardware", 70, id=17,
                       data=lambda host: HardwareState.Name(host.data.state),
                       tip="The state of the hardware as Up or Down.\n\n"
                           "On a frame it is the amount of memory used.")
        self.addColumn("Locked", 90, id=18,
                       data=lambda host: LockState.Name(host.data.lock_state),
                       tip="A host can be:\n"
                           "Locked \t\t It was manually locked to prevent booking\n"
                           "Open \t\t It is available to be booked if resources are idle\n"
                           "NimbyLocked \t It is a desktop machine and there is\n"
                           "\t\t someone actively using it or not enough \n"
                           "\t\t resources are available on a desktop.")
        self.addColumn("ThreadMode", 80, id=19,
                       data=lambda host: ThreadMode.Name(host.data.thread_mode),
                       tip="A frame that runs on this host will:\n"
                           "All:  Use all cores.\n"
                           "Auto: Use the number of cores as decided by the cuebot.\n")
        self.addColumn("OS", 50, id=20,
                       data=lambda host: host.data.os,
                       tip="Host operational system or distro.")
        self.addColumn("Tags/Job", 50, id=21,
                       data=lambda host: ",".join(host.data.tags),
                       tip="The tags applied to the host.\n\n"
                           "On a frame it is the name of the job.")

        self.hostSearch = opencue.search.HostSearch()

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)

        # pylint: disable=no-member
        self.itemClicked.connect(self.__itemSingleClickedCopy)
        self.itemClicked.connect(self.__itemSingleClickedComment)
        # pylint: enable=no-member

        # Don't use the standard space bar to refresh
        self.app.request_update.connect(self.updateRequest)

        self.startTicksUpdate(40)
        # Don't start refreshing until the user sets a filter or hits refresh
        self.ticksWithoutUpdate = -1

        self.enableRefresh = bool(int(self.app.settings.value("AutoRefreshMonitorHost", 1)))

    def tick(self):
        if self.ticksWithoutUpdate >= self.updateInterval and \
           not self.window().isMinimized():
            self.ticksWithoutUpdate = 0
            self._update()
            return

        if self.enableRefresh and self.updateInterval + 1 >= self.ticksWithoutUpdate >= 0:
            self.ticksWithoutUpdate += 1

    def updateSoon(self):
        """Returns immediately. Causes an update to happen
        Constants.AFTER_ACTION_UPDATE_DELAY after calling this function."""
        QtCore.QTimer.singleShot(cuegui.Constants.AFTER_ACTION_UPDATE_DELAY,
                                 self.updateRequest)

    def facilityChanged(self):
        """Called when the facility is changed and removes then updates the host
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
        selected = [host.data.name for host in self.selectedObjects() if cuegui.Utils.isHost(host)]
        if selected:
            QtWidgets.QApplication.clipboard().setText(",".join(selected))

    def __itemSingleClickedComment(self, item, col):
        """If the comment column is clicked on, and there is a comment on the
        host, this pops up the comments dialog
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        host = item.rpcObject
        if col == COMMENT_COLUMN and cuegui.Utils.isHost(host) and host.data.has_comment:
            self.__menuActions.hosts().viewComments([host])

    def clearFilters(self):
        """Clears any sorting and filtering, restoring the default view."""
        self.clearSelection()
        self.hostSearch = opencue.search.HostSearch()
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.removeAllItems()

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 999

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            hosts = opencue.api.getHosts(**self.hostSearch.options)
            # Sorting by name here incase that makes displaying it faster
            hosts.sort(key=lambda host: host.data.name)
            return hosts
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def _createItem(self, rpcObject, parent=None):
        """Creates and returns the proper item
        @type  rpcObject: Host
        @param rpcObject: The object for this item
        @type  parent: QTreeWidgetItem
        @param parent: Optional parent for this item
        @rtype:  QTreeWidgetItem
        @return: The created item"""
        if not parent:
            parent = self
        return HostWidgetItem(rpcObject, parent)

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.hosts().addAction(menu, "viewComments")
        self.__menuActions.hosts().addAction(menu, "viewProc")
        self.__menuActions.hosts().addAction(menu, "lock")
        self.__menuActions.hosts().addAction(menu, "unlock")
        self.__menuActions.hosts().addAction(menu, "addTags")
        self.__menuActions.hosts().addAction(menu, "removeTags")
        self.__menuActions.hosts().addAction(menu, "renameTag")
        self.__menuActions.hosts().addAction(menu, "changeAllocation")
        self.__menuActions.hosts().addAction(menu, "delete")
        self.__menuActions.hosts().addAction(menu, "rebootWhenIdle")
        self.__menuActions.hosts().addAction(menu, "setRepair")
        self.__menuActions.hosts().addAction(menu, "clearRepair")
        menu.exec_(e.globalPos())

    def startDrag(self, dropActions):
        """Called when a drag begins"""
        cuegui.Utils.startDrag(self, dropActions, self.selectedObjects())

    def dragEnterEvent(self, event):
        """Enter drag event"""
        cuegui.Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        """Move drag event"""
        cuegui.Utils.dragMoveEvent(event, "application/x-host-ids")


class HostWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item representing a single host."""

    __initialized = False

    # pylint: disable=protected-access
    def __init__(self, rpcObject, parent):
        if not self.__initialized:
            cuegui.Style.init()
            self.__class__.__initialized = True
            self.__class__.__commentIcon = QtGui.QIcon(":comment.png")
            self.__class__.__backgroundColor = cuegui.app().palette().color(QtGui.QPalette.Base)
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND
            self.__class__.__pausedColor = cuegui.Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND
            self.__class__.__dyingColor = cuegui.Style.ColorTheme.COLOR_JOB_DYING_BACKGROUND
            self.__class__.__type = cuegui.Constants.TYPE_HOST
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_HOST, rpcObject, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            if col not in self._cache:
                self._cache[col] = \
                    self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](self.rpcObject)
            return self._cache.get(col, cuegui.Constants.QVARIANT_NULL)

        if role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        if role == QtCore.Qt.BackgroundRole:
            if not self.rpcObject.data.state == opencue.api.host_pb2.UP:
                return self.__dyingColor
            if self.rpcObject.data.lock_state == opencue.api.host_pb2.LOCKED:
                return self.__pausedColor
            return self.__backgroundColor

        if role == QtCore.Qt.DecorationRole:
            if col == COMMENT_COLUMN and self.rpcObject.data.has_comment:
                return self.__commentIcon

        if role == QtCore.Qt.UserRole:
            return self.__type

        if role == QtCore.Qt.UserRole + 1:
            return [self.rpcObject.data.total_swap - self.rpcObject.data.free_swap,
                    self.rpcObject.data.total_swap]

        if role == QtCore.Qt.UserRole + 2:
            return [self.rpcObject.data.total_memory - self.rpcObject.data.free_memory,
                    self.rpcObject.data.total_memory]

        if role == QtCore.Qt.UserRole + 3:
            return [self.rpcObject.data.total_gpu_memory -
                    self.rpcObject.data.free_gpu_memory,
                    self.rpcObject.data.total_gpu_memory]

        return cuegui.Constants.QVARIANT_NULL
