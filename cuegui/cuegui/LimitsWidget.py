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


"""Widget for managing limits."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

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


class LimitsWidget(QtWidgets.QWidget):
    """Widget for managing limits."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddLimit = QtWidgets.QPushButton("Add Limit", self)
        self.__btnAddLimit.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__monitorLimits = LimitsTreeWidget(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__btnAddLimit, 0, 3)
        layout.addWidget(self.__btnRefresh, 0, 2)
        layout.addWidget(self.__monitorLimits, 2, 0, 3, 4)

        # pylint: disable=no-member
        self.__btnAddLimit.clicked.connect(self.__addLimit)
        self.__btnRefresh.clicked.connect(self.updateSoon)
        # pylint: enable=no-member

        self.__menuActions = cuegui.MenuActions.MenuActions(self, self.updateSoon, list)

    def updateSoon(self):
        """Requests a refresh of the limits list."""
        # pylint: disable=protected-access
        self.__monitorLimits._update()

    def __addLimit(self):
        self.__menuActions.limits().create()
        self.updateSoon()

    def getColumnVisibility(self):
        """Gets the table column visibility."""
        return self.__monitorLimits.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets the table column visibility."""
        self.__monitorLimits.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets the table column order."""
        return self.__monitorLimits.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets the table column order."""
        self.__monitorLimits.setColumnOrder(settings)


class LimitsTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of limits."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_LIMIT)
        self.addColumn("Limit Name", 90, id=1,
                       data=lambda limit: limit.name())
        self.addColumn("Max Value", 80, id=2,
                       data=lambda limit: ("%d" % limit.maxValue()),
                       sort=lambda limit: limit.maxValue())
        self.addColumn("Current Running", 80, id=2,
                       data=lambda limit: ("%d" % limit.currentRunning()),
                       sort=lambda limit: limit.currentRunning())

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.itemClicked.connect(self.__itemSingleClickedToDouble)  # pylint: disable=no-member
        self.app.facility_changed.connect(self.__facilityChanged)

        self.setUpdateInterval(60)

    def __facilityChanged(self):
        """Called when the facility is changed"""
        self.removeAllItems()
        self._update()

    def __itemSingleClickedToDouble(self, item, col):
        """Called when an item is clicked on. Causes single clicks to be treated
        as double clicks.
        @type  item: QTreeWidgetItem
        @param item: The item single clicked on
        @type  col: int
        @param col: Column number single clicked on"""
        self.itemDoubleClicked.emit(item, col)

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        item = LimitWidgetItem(rpcObject, self)
        return item

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return opencue.api.getLimits()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.limits().addAction(menu, "editMaxValue")
        menu.addSeparator()
        self.__menuActions.limits().addAction(menu, "delete")
        self.__menuActions.limits().addAction(menu, "rename")
        menu.exec_(QtCore.QPoint(e.globalX(), e.globalY())) # pylint: disable=no-member

    def tick(self):
        pass


class LimitWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single limit."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_LIMIT, rpcObject, parent)
