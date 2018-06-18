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


"""
A frame list based on AbstractTreeWidget
"""
from Manifest import os, QtCore, QtGui, Cue3

import Constants
import Logger
import Style
import Utils

from MenuActions import MenuActions
from AbstractTreeWidget import *
from AbstractWidgetItem import *
from ItemDelegate import HostSwapBarDelegate, HostMemBarDelegate, HostGpuBarDelegate

import time

logger = Logger.getLogger(__file__)

COMMENT_COLUMN = 1

class HostMonitorTree(AbstractTreeWidget):
    def __init__(self, parent):

        self.startColumnsForType(Constants.TYPE_HOST)
        self.addColumn("Name", 150, id=1,
                        data=lambda host:(host.data.name),
                        tip="The hostname.")
        self.addColumn("_Comment", 20, id=2,
                        sort=lambda host:(host.data.hasComment),
                        tip="A comment icon will appear if a host has a comment. You\n"
                            "may click on it to view the comments.")
        self.addColumn("Load %", 55, id=3,
                        data=lambda host:("%3.0f%%" % (host.data.load/host.data.cores)),
                        sort=lambda host:(host.data.load/host.data.cores),
                        tip="The host load average compared to the number of cores\n"
                            "as a percent. Meaning a load of 8 on an 8 core machine\n"
                            "will show 100%. A percentage much over 100% is an\n"
                            "indication that a frame is using more cores than it\n"
                            "reserved. If all cores are reserved and the percentage\n"
                            "is way below 100% then the cpu is underutilized.")
        self.addColumn("Swap", 60, id=4,
                        data=lambda host:(Utils.memoryToString(host.data.freeSwap)),
                        sort=lambda host:(host.data.freeSwap),
                        delegate=HostSwapBarDelegate,
                        tip="The amount of used swap (red) vs available swap (green)")
        self.addColumn("Memory", 60, id=5,
                        data=lambda host:(Utils.memoryToString(host.data.freeMemory)),
                        sort=lambda host:(host.data.freeMemory),
                        delegate=HostMemBarDelegate,
                        tip="The amount of used memory (red) vs available gpu memory (green)")
        self.addColumn("GPU", 60, id=6,
                        data=lambda host:(Utils.memoryToString(host.data.freeGpu)),
                        sort=lambda host:(host.data.freeGpu),
                        delegate=HostGpuBarDelegate,
                        tip="The amount of used gpu memory (red) vs available gpu memory (green)")
        self.addColumn("freeMcp", 60, id=7,
                        data=lambda host:(Utils.memoryToString(host.data.freeMcp)),
                        sort=lambda host:(host.data.freeMcp),
                        tip="The amount of free space in /mcp/")
        self.addColumn("Cores", 45, id=8,
                        data=lambda host: ("%.2f" % host.data.cores),
                        sort=lambda host: (host.data.cores),
                        tip="The total number of cores.\n\n"
                            "On a frame it is the number of cores reserved.")
        self.addColumn("Idle", 40, id=9,
                        data=lambda host: ("%.2f" % host.data.idleCores),
                        sort=lambda host: (host.data.idleCores),
                        tip="The number of cores that are not reserved.")
        self.addColumn("Mem", 50, id=10,
                        data=lambda host:(Utils.memoryToString(host.data.memory)),
                        sort=lambda host:(host.data.memory),
                        tip="The total amount of reservable memory.\n\n"
                            "On a frame it is the amount of memory reserved.")
        self.addColumn("Idle", 50, id=11,
                        data=lambda host:(Utils.memoryToString(host.data.idleMemory)),
                        sort=lambda host:(host.data.idleMemory),
                        tip="The amount of unreserved memory.")
        self.addColumn("GPU", 50, id=12,
                        data=lambda host:(Utils.memoryToString(host.data.gpu)),
                        sort=lambda host:(host.data.gpu),
                        tip="The total amount of reservable gpu memory.\n\n"
                            "On a frame it is the amount of gpu memory reserved.")
        self.addColumn("Idle", 50, id=13,
                        data=lambda host:(Utils.memoryToString(host.data.idleGpu)),
                        sort=lambda host:(host.data.idleGpu),
                        tip="The amount of unreserved gpu memory.")
        self.addColumn("Ping", 50, id=14,
                        data=lambda host:(int(time.time() - host.data.pingTime)),
                        sort=lambda host:(host.data.pingTime),
                        tip="The number of seconds since the cuebot last received\n"
                            "a report from the host. A host is configured to report\n"
                            "in every 60 seconds so a number larger than this\n"
                            "indicates a problem")
        self.addColumn("Hardware", 70, id=15,
                        data=lambda host:(str(host.data.state)),
                        tip="The state of the hardware as Up or Down.\n\n"
                            "On a frame it is the amount of memory used.")
        self.addColumn("Locked", 90, id=16,
                        data=lambda host:(str(host.data.lockState)),
                        tip="A host can be:\n"
                            "Locked \t\t It was manually locked to prevent booking\n"
                            "Open \t\t It is available to be booked if resources are idle\n"
                            "NimbyLocked \t It is a desktop machine and there is\n"
                            "\t\t someone actively using it or not enough \n"
                            "\t\t resources are available on a desktop.")
                       #["History", 90, None, None, HostHistoryDelegate)
        self.addColumn("ThreadMode", 80, id=17,
                        data=lambda host:(str(host.data.threadMode)),
                        tip="A frame that runs on this host will:\n"
                            "All:  Use all cores.\n"
                            "Auto: Use the number of cores as decided by the cuebot.\n")
        self.addColumn("Tags/Job", 50, id=18,
                       data=lambda host:(",".join(host.data.tags)),
                       tip="The tags applied to the host.\n\n"
                            "On a frame it is the name of the job.")

        self.hostSearch = Cue3.HostSearch()

        AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)

        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)

        QtCore.QObject.connect(self,
                               QtCore.SIGNAL('itemClicked(QTreeWidgetItem*,int)'),
                               self.__itemSingleClickedCopy)

        QtCore.QObject.connect(self,
                               QtCore.SIGNAL('itemClicked(QTreeWidgetItem*,int)'),
                               self.__itemSingleClickedComment)

        # Don't use the standard space bar to refresh
        QtCore.QObject.disconnect(QtGui.qApp,
                                  QtCore.SIGNAL('request_update()'),
                                  self.updateRequest)

        self.startTicksUpdate(40)
        # Don't start refreshing until the user sets a filter or hits refresh
        self.ticksWithoutUpdate = -1
        self.enableRefresh = False

    def tick(self):
        if self.ticksWithoutUpdate >= self.updateInterval and \
           not self.window().isMinimized():
            self.ticksWithoutUpdate = 0
            self._update()
            return

        if self.enableRefresh and \
           self.ticksWithoutUpdate <= self.updateInterval + 1 and \
           self.ticksWithoutUpdate >= 0:
            self.ticksWithoutUpdate += 1

    def updateSoon(self):
        """Returns immediately. Causes an update to happen
        Constants.AFTER_ACTION_UPDATE_DELAY after calling this function."""
        QtCore.QTimer.singleShot(Constants.AFTER_ACTION_UPDATE_DELAY,
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
        selected = [host.data.name for host in self.selectedObjects() if Utils.isHost(host)]
        if selected:
            QtGui.QApplication.clipboard().setText(",".join(selected),
                                                   QtGui.QClipboard.Selection)

    def __itemSingleClickedComment(self, item, col):
        """If the comment column is clicked on, and there is a comment on the
        host, this pops up the comments dialog
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        host = item.iceObject
        if col == COMMENT_COLUMN and Utils.isHost(host) and host.data.hasComment:
            self.__menuActions.hosts().viewComments([host])

    def clearFilters(self):
        self.clearSelection()
        self.hostSearch = Cue3.HostSearch()
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.removeAllItems()

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 999

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            hosts = Cue3.Cuebot.Proxy.getHosts(self.hostSearch)
            # Sorting by name here incase that makes displaying it faster
            hosts.sort(key=lambda host:(host.data.name))
            return hosts
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
            return []

    def _createItem(self, object, parent = None):
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
        menu = QtGui.QMenu()
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
        Utils.startDrag(self, dropActions, self.selectedObjects())

    def dragEnterEvent(self, event):
        Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        Utils.dragMoveEvent(event, "application/x-host-ids")

class HostWidgetItem(AbstractWidgetItem):
    __initialized = False
    def __init__(self, object, parent):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__commentIcon = \
                                    QtCore.QVariant(QtGui.QIcon(":comment.png"))
            self.__class__.__backgroundColor = \
                QtCore.QVariant(QtGui.qApp.palette().color(QtGui.QPalette.Base))
            self.__class__.__foregroundColor = \
                          QtCore.QVariant(Style.ColorTheme.COLOR_JOB_FOREGROUND)
            self.__class__.__pausedColor = \
                   QtCore.QVariant(Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND)
            self.__class__.__dyingColor = \
                    QtCore.QVariant(Style.ColorTheme.COLOR_JOB_DYING_BACKGROUND)
            self.__class__.__type = QtCore.QVariant(Constants.TYPE_HOST)
        AbstractWidgetItem.__init__(self, Constants.TYPE_HOST, object, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  QtCore.QVariant
        @return: The desired data wrapped in a QVariant"""
        if role == QtCore.Qt.DisplayRole:
            if not self._cache.has_key(col):
                self._cache[col] = QtCore.QVariant(self.column_info[col][Constants.COLUMN_INFO_DISPLAY](self.iceObject))
            return self._cache.get(col, Constants.QVARIANT_NULL)

        elif role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        elif role == QtCore.Qt.BackgroundRole:
            if not self.iceObject.data.state == Cue3.HardwareState.Up:
                return self.__dyingColor
            if self.iceObject.data.lockState == Cue3.LockState.Locked:
                return self.__pausedColor
            return self.__backgroundColor

        elif role == QtCore.Qt.DecorationRole:
            if col == COMMENT_COLUMN and self.iceObject.data.hasComment:
                return self.__commentIcon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        elif role == QtCore.Qt.UserRole + 1:
            return QtCore.QVariant([self.iceObject.data.totalSwap - self.iceObject.data.freeSwap,
                                    self.iceObject.data.totalSwap])

        elif role == QtCore.Qt.UserRole + 2:
            return QtCore.QVariant([self.iceObject.data.totalMemory - self.iceObject.data.freeMemory,
                                    self.iceObject.data.totalMemory])

        elif role == QtCore.Qt.UserRole + 3:
            return QtCore.QVariant([self.iceObject.data.totalGpu - self.iceObject.data.freeGpu,
                                    self.iceObject.data.totalGpu])

        return Constants.QVARIANT_NULL
