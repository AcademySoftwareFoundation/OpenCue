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


from __future__ import absolute_import

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue

from .AbstractTreeWidget import AbstractTreeWidget
from .AbstractWidgetItem import AbstractWidgetItem
from . import Constants
from . import Logger
from .MenuActions import MenuActions


logger = Logger.getLogger(__file__)


class ShowsWidget(AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(Constants.TYPE_SHOW)
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

        AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)

        self.itemClicked.connect(self.__itemSingleClickedToDouble)
        QtGui.qApp.facility_changed.connect(self.__facilityChanged)

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

    def _createItem(self, object):
        """Creates and returns the proper item"""
        item = ShowWidgetItem(object, self)
        return item

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return opencue.api.getActiveShows()
        except Exception as e:
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

            menu.exec_(QtCore.QPoint(e.globalX(), e.globalY()))


class ShowWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        AbstractWidgetItem.__init__(self, Constants.TYPE_SHOW, object, parent)
