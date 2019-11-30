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


"""
A frame list based on AbstractTreeWidget
"""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import map
from builtins import str
import time

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.ItemDelegate
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Style
import cuegui.Utils

from opencue.compiled_proto.host_pb2 import HardwareState
from opencue.compiled_proto.host_pb2 import LockState
from opencue.compiled_proto.host_pb2 import ThreadMode


logger = cuegui.Logger.getLogger(__file__)

COMMENT_COLUMN = 1


class HostMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
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
        self.addColumn("Swap", 60, id=4,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_swap),
                       sort=lambda host: host.data.free_swap,
                       delegate=cuegui.ItemDelegate.HostSwapBarDelegate,
                       tip="The amount of used swap (red) vs available swap (green)")
        self.addColumn("Memory", 60, id=5,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_memory),
                       sort=lambda host: host.data.free_memory,
                       tip="The amount of used memory (red) vs available gpu memory (green)")
        self.addColumn("GPU", 60, id=6,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_gpu),
                       sort=lambda host: host.data.free_gpu,
                       delegate=cuegui.ItemDelegate.HostGpuBarDelegate,
                       tip="The amount of used gpu memory (red) vs available gpu memory (green)")
        self.addColumn("freeScratch", 60, id=7,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.free_scratch),
                       sort=lambda host: host.data.free_scratch,
                       tip="The amount of free space in /tmp/")
        self.addColumn("Cores", 45, id=8,
                       data=lambda host: "%.2f" % host.data.cores,
                       sort=lambda host: host.data.cores,
                       tip="The total number of cores.\n\n"
                           "On a frame it is the number of cores reserved.")
        self.addColumn("Idle", 40, id=9,
                       data=lambda host: "%.2f" % host.data.idle_cores,
                       sort=lambda host: host.data.idle_cores,
                       tip="The number of cores that are not reserved.")
        self.addColumn("Mem", 50, id=10,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.memory),
                       sort=lambda host: host.data.memory,
                       tip="The total amount of reservable memory.\n\n"
                           "On a frame it is the amount of memory reserved.")
        self.addColumn("Idle", 50, id=11,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.idle_memory),
                       sort=lambda host: host.data.idle_memory,
                       tip="The amount of unreserved memory.")
        self.addColumn("GPU", 50, id=12,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.gpu),
                       sort=lambda host: host.data.gpu,
                       tip="The total amount of reservable gpu memory.\n\n"
                           "On a frame it is the amount of gpu memory reserved.")
        self.addColumn("Idle", 50, id=13,
                       data=lambda host: cuegui.Utils.memoryToString(host.data.idle_gpu),
                       sort=lambda host: host.data.idle_gpu,
                       tip="The amount of unreserved gpu memory.")
        self.addColumn("Ping", 50, id=14,
                       data=lambda host: int(time.time() - host.data.ping_time),
                       sort=lambda host: host.data.ping_time,
                       tip="The number of seconds since the cuebot last received\n"
                           "a report from the host. A host is configured to report\n"
                           "in every 60 seconds so a number larger than this\n"
                           "indicates a problem")
        self.addColumn("Hardware", 70, id=15,
                       data=lambda host: HardwareState.Name(host.data.state),
                       tip="The state of the hardware as Up or Down.\n\n"
                           "On a frame it is the amount of memory used.")
        self.addColumn("Locked", 90, id=16,
                       data=lambda host: LockState.Name(host.data.lock_state),
                       tip="A host can be:\n"
                           "Locked \t\t It was manually locked to prevent booking\n"
                           "Open \t\t It is available to be booked if resources are idle\n"
                           "NimbyLocked \t It is a desktop machine and there is\n"
                           "\t\t someone actively using it or not enough \n"
                           "\t\t resources are available on a desktop.")
        self.addColumn("ThreadMode", 80, id=17,
                       data=lambda host: ThreadMode.Name(host.data.thread_mode),
                       tip="A frame that runs on this host will:\n"
                           "All:  Use all cores.\n"
                           "Auto: Use the number of cores as decided by the cuebot.\n")
        self.addColumn("Tags/Job", 50, id=18,
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

        self.itemClicked.connect(self.__itemSingleClickedCopy)
        self.itemClicked.connect(self.__itemSingleClickedComment)

        # Don't use the standard space bar to refresh
        QtGui.qApp.request_update.connect(self.updateRequest)

        self.startTicksUpdate(40)
        # Don't start refreshing until the user sets a filter or hits refresh
        self.ticksWithoutUpdate = -1
        self.enableRefresh = bool(int(QtGui.qApp.settings.value("AutoRefreshMonitorHost", 1)))

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
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def _createItem(self, object, parent=None):
        """Creates and returns the proper item
        @type  object: Host
        @param object: The object for this item
        @type  parent: QTreeWidgetItem
        @param parent: Optional parent for this item
        @rtype:  QTreeWidgetItem
        @return: The created item"""
        if not parent:
            parent = self
        return HostWidgetItem(object, parent)

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.hosts().addAction(menu, "viewComments")
        self.__menuActions.hosts().addAction(menu, "viewProc")
        self.__menuActions.hosts().addAction(menu, "hinv")
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
        cuegui.Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        cuegui.Utils.dragMoveEvent(event, "application/x-host-ids")


class HostWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    __initialized = False

    def __init__(self, object, parent):
        if not self.__initialized:
            cuegui.Style.init()
            self.__class__.__initialized = True
            self.__class__.__commentIcon = QtGui.QIcon(":comment.png")
            self.__class__.__backgroundColor = QtGui.qApp.palette().color(QtGui.QPalette.Base)
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND
            self.__class__.__pausedColor = cuegui.Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND
            self.__class__.__dyingColor = cuegui.Style.ColorTheme.COLOR_JOB_DYING_BACKGROUND
            self.__class__.__type = cuegui.Constants.TYPE_HOST
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_HOST, object, parent)

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

        elif role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        elif role == QtCore.Qt.BackgroundRole:
            if not self.rpcObject.data.state == opencue.api.host_pb2.UP:
                return self.__dyingColor
            if self.rpcObject.data.lock_state == opencue.api.host_pb2.LOCKED:
                return self.__pausedColor
            return self.__backgroundColor

        elif role == QtCore.Qt.DecorationRole:
            if col == COMMENT_COLUMN and self.rpcObject.data.has_comment:
                return self.__commentIcon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        elif role == QtCore.Qt.UserRole + 1:
            return [self.rpcObject.data.total_swap - self.rpcObject.data.free_swap,
                    self.rpcObject.data.total_swap]

        elif role == QtCore.Qt.UserRole + 2:
            return [self.rpcObject.data.total_memory - self.rpcObject.data.free_memory,
                    self.rpcObject.data.total_memory]

        elif role == QtCore.Qt.UserRole + 3:
            return [self.rpcObject.data.total_gpu - self.rpcObject.data.free_gpu,
                    self.rpcObject.data.total_gpu]

        return cuegui.Constants.QVARIANT_NULL
