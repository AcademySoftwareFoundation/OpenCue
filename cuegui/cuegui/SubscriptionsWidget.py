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


"""Widget for listing and managing subscriptions."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import str

import opencue

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.MenuActions
import cuegui.ShowDialog
import cuegui.Utils


class SubscriptionsWidget(QtWidgets.QWidget):
    """Widget for listing and managing subscriptions."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.app = cuegui.app()

        self.__show = None
        self.__shows = None

        self.__comboShows = QtWidgets.QComboBox(self)
        self.__comboShows.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__btnShowProperties = QtWidgets.QPushButton("Show Properties", self)
        self.__btnShowProperties.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__btnAddSubscription = QtWidgets.QPushButton("Add Subscription", self)
        self.__btnAddSubscription.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__monitorSubscriptions = SubscriptionsTreeWidget(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__comboShows, 0, 0)
        layout.addWidget(self.__btnShowProperties, 0, 2)
        layout.addWidget(self.__btnAddSubscription, 0, 3)
        layout.addWidget(self.__monitorSubscriptions, 2, 0, 3, 4)

        # pylint: disable=no-member
        self.__btnShowProperties.clicked.connect(self.__showProperties)
        self.__btnAddSubscription.clicked.connect(self.__addSubscription)
        self.__comboShows.currentIndexChanged.connect(self.setShow)
        # pylint: enable=no-member
        self.app.view_object.connect(self.setShow)
        self.app.facility_changed.connect(self.changeFacility)

        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.changeFacility()

    def changeFacility(self):
        """Changes the active facility."""
        try:
            self.__shows = {show.name(): show for show in opencue.api.getActiveShows()}
        except opencue.exception.CueException:
            self.__shows = {}
        self.__comboShows.clear()
        self.__comboShows.addItems(["Select Show:"] + sorted(self.__shows.keys()))
        self.setShow()

    def setShow(self, show=""):
        """Sets the active show.

        @type  show: str or Show
        @param show: The show to monitor"""
        if isinstance(show, int):
            show = str(self.__comboShows.currentText())
        if cuegui.Utils.isShow(show):
            if self.__show and self.__show.name() == show.name():
                return
            self.__show = show
            show = show.name()
        elif isinstance(show, str):
            if self.__show and self.__show.name() == show:
                return
            if show in self.__shows:
                self.__show = self.__shows[show]
            else:
                show = ""
        else:
            return

        if show == "":
            self.__show = None
            index = 0
        else:
            index = sorted(self.__shows.keys()).index(show) + 1

        self.__comboShows.setCurrentIndex(index)
        self.__monitorSubscriptions.setShow(self.__show)

    def getShow(self):
        """Gets the active show."""
        return self.__show

    def getShowName(self):
        """Gets the active show name."""
        if self.__show:
            return self.__show.data.name
        return None

    def updateSoon(self):
        """Requests an update of the subscriptions list."""
        # pylint: disable=protected-access
        self.__monitorSubscriptions._update()

    def selectedObjects(self):
        """Gets a list of the active show(s)."""
        return [opencue.api.findShow(self.__show.name())]

    def __showProperties(self):
        if self.__show:
            dialog = cuegui.ShowDialog.ShowDialog(opencue.api.findShow(self.__show.name()), self)
            dialog.exec_()
        else:
            self.__comboShows.showPopup()

    def __addSubscription(self):
        if self.__show:
            self.__menuActions.shows().createSubscription([self.__show])
            self.updateSoon()

    def getColumnVisibility(self):
        """Gets the table column visibility."""
        return self.__monitorSubscriptions.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets the table column visibility."""
        self.__monitorSubscriptions.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets the table column order."""
        return self.__monitorSubscriptions.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets the table column order."""
        self.__monitorSubscriptions.setColumnOrder(settings)


class SubscriptionsTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of subscriptions."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_SUB)
        self.addColumn("Alloc", 160, id=1,
                       data=lambda sub: sub.data.allocation_name)
        self.addColumn("Usage", 70, id=2,
                       data=lambda sub: (
                               sub.data.size and
                               ("%.2f%%" % (sub.data.reserved_cores / sub.data.size * 100))
                               or 0),
                       sort=lambda sub: (sub.data.size and
                                         sub.data.reserved_cores / sub.data.size or 0))
        self.addColumn("Size", 70, id=3,
                       data=lambda sub: (sub.data.size/100.0),
                       sort=lambda sub: (sub.data.size/100.0))
        self.addColumn("Burst", 70, id=4,
                       data=lambda sub: (sub.data.burst/100.0),
                       sort=lambda sub: (sub.data.burst/100.0))
        self.addColumn("Used", 70, id=5,
                       data=lambda sub: ("%.2f" % (sub.data.reserved_cores/100.0)),
                       sort=lambda sub: (sub.data.reserved_cores/100.0))

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.__show = None

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects, self.getShow)

        self.setUpdateInterval(30)

    def setShow(self, show=None):
        """Sets the active show."""
        self._itemsLock.lockForWrite()
        try:
            if not show:
                self.__show = None
            elif cuegui.Utils.isShow(show):
                self.__show = show
            elif isinstance(show, str):
                try:
                    self.__show = opencue.api.findShow(show)
                except opencue.exception.CueException:
                    pass
            self._update()
        finally:
            self._itemsLock.unlock()

    def getShow(self):
        """Gets the active show."""
        return self.__show

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        return SubscriptionWidgetItem(rpcObject, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        self._itemsLock.lockForWrite()
        try:
            if self.__show:
                return self.__show.getSubscriptions()
            return []
        finally:
            self._itemsLock.unlock()

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""

        menu = QtWidgets.QMenu()
        self.__menuActions.subscriptions().addAction(menu, "editSize")
        self.__menuActions.subscriptions().addAction(menu, "editBurst")
        menu.addSeparator()
        self.__menuActions.subscriptions().addAction(menu, "delete")
        menu.exec_(QtCore.QPoint(e.globalX(),e.globalY())) # pylint: disable=no-member

    def tick(self):
        pass


class SubscriptionWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item representing a single subscription."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_SUB, rpcObject, parent)
