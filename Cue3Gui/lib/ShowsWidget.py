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


from Manifest import os, QtCore, QtGui, Cue3

import Utils
import Constants

from MenuActions import MenuActions
from AbstractTreeWidget import *
from AbstractWidgetItem import *

class ShowsWidget(AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(Constants.TYPE_SHOW)
        self.addColumn("Show Name", 90, id=1,
                       data=lambda show:(show.data.name))
        self.addColumn("Cores Run", 80, id=2,
                       data=lambda show:("%.2f" % show.stats.reservedCores),
                       sort=lambda show:(show.stats.reservedCores))
        self.addColumn("Frames Run", 80, id=3,
                       data=lambda show:(show.stats.runningFrames),
                       sort=lambda show:(show.stats.runningFrames))
        self.addColumn("Frames Pending", 80, id=4,
                       data=lambda show:(show.stats.pendingFrames),
                       sort=lambda show:(show.stats.pendingFrames))
        self.addColumn("Jobs", 80, id=5,
                       data=lambda show:(show.stats.pendingJobs),
                       sort=lambda show:(show.stats.pendingJobs))

        AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)

        QtCore.QObject.connect(self,
                               QtCore.SIGNAL('itemClicked(QTreeWidgetItem*,int)'),
                               self.__itemSingleClickedToDouble)

        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL('facility_changed()'), self.__facilityChanged)

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
        self.emit(QtCore.SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'), item, col)

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return ShowWidgetItem(object, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return Cue3.getActiveShows()
        except Exception, e:
            log.critical(e)
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""

        count = len(self.selectedObjects())
        menu = QtGui.QMenu()

        if count:
            self.__menuActions.shows().addAction(menu, "properties")
            if count == 1:
                menu.addSeparator()
                self.__menuActions.shows().addAction(menu, "createSubscription")

            menu.exec_(QtCore.QPoint(e.globalX(),e.globalY()))

class ShowWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        AbstractWidgetItem.__init__(self, Constants.TYPE_SHOW, object, parent)
