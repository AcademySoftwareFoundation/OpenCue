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


"""Tree widget for displaying a list of shows."""


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


logger = cuegui.Logger.getLogger(__file__)


class ShowsWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of shows."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_SHOW)
        self.addColumn("Show Name", 90, id=1,
                       data=lambda show: (show.data.name))
        self.addColumn("Cores Run", 80, id=2,
                       data=lambda show: ("%.2f" % show.data.show_stats.reserved_cores),
                       sort=lambda show: (show.data.show_stats.reserved_cores))
        self.addColumn("Frames Run", 80, id=3,
                       data=lambda show: (show.data.show_stats.running_frames),
                       sort=lambda show: (show.data.show_stats.running_frames))
        self.addColumn("Frames Pending", 80, id=4,
                       data=lambda show: (show.data.show_stats.pending_frames),
                       sort=lambda show: (show.data.show_stats.pending_frames))
        self.addColumn("Jobs", 80, id=5,
                       data=lambda show: (show.data.show_stats.pending_jobs),
                       sort=lambda show: (show.data.show_stats.pending_jobs))

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
        item = ShowWidgetItem(rpcObject, self)
        return item

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return opencue.api.getActiveShows()
        except opencue.exception.CueException as e:
            logger.critical(e)
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""

        count = len(self.selectedObjects())
        menu = QtWidgets.QMenu()

        if count:
            self.__menuActions.shows().addAction(menu, "properties")
            if count == 1:
                menu.addSeparator()
                self.__menuActions.shows().addAction(menu, "createSubscription")

            menu.exec_(QtCore.QPoint(e.globalX(), e.globalY())) # pylint: disable=no-member

    def tick(self):
        pass


class ShowWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item representing a single show."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_SHOW, rpcObject, parent)
