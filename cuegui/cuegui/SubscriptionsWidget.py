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
import cuegui.ActionRunner
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
        self.__shows = {}

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
        """Changes the active facility. The active shows are listed off the GUI
        thread."""
        cuegui.ActionRunner.submit(
            lambda: {show.name(): show for show in opencue.api.getActiveShows()},
            self.__changeFacilityDone, "Listing active shows")

    def __changeFacilityDone(self, shows, error):
        if error is not None:
            shows = {}
        # Keep the show if it was selected while the shows were being listed.
        current = self.__show.name() if self.__show else ""
        self.__show = None
        self.__shows = shows
        self.__fillComboShows()
        self.setShow(current if current in self.__shows else "")

    def __fillComboShows(self):
        # Changing the items changes the current index; do not treat that as
        # a show selection.
        self.__comboShows.blockSignals(True)
        try:
            self.__comboShows.clear()
            self.__comboShows.addItems(["Select Show:"] + sorted(self.__shows.keys()))
        finally:
            self.__comboShows.blockSignals(False)

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
            if show not in self.__shows:
                # The shows are not listed yet, or this one is not active.
                self.__shows[show] = self.__show
                self.__fillComboShows()
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
        return [self.__show] if self.__show else []

    def __showProperties(self):
        if self.__show:
            # Fetch the show again, off the GUI thread, so the dialog shows its
            # current settings.
            name = self.__show.name()
            cuegui.ActionRunner.submit(lambda: opencue.api.findShow(name),
                                       self.__showPropertiesDone, "Finding show %s" % name)
        else:
            self.__comboShows.showPopup()

    def __showPropertiesDone(self, show, error):
        if error is not None:
            QtWidgets.QMessageBox.critical(
                self, "Show Properties", str(error), QtWidgets.QMessageBox.Ok)
            return
        dialog = cuegui.ShowDialog.ShowDialog(show, self)
        dialog.exec_()

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

        # Set before AbstractTreeWidget.__init__, which requests the first
        # update.
        self.__show = None

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects, self.getShow)

        self.setUpdateInterval(30)

    def setShow(self, show=None):
        """Sets the active show."""
        newShow = self.__show
        if not show:
            newShow = None
        elif cuegui.Utils.isShow(show):
            newShow = show
        elif isinstance(show, str):
            try:
                newShow = opencue.api.findShow(show)
            except opencue.exception.CueException:
                pass
        self._itemsLock.lockForWrite()
        try:
            self.__show = newShow
        finally:
            self._itemsLock.unlock()
        self._update()

    def getShow(self):
        """Gets the active show."""
        return self.__show

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        return SubscriptionWidgetItem(rpcObject, self)

    def _getUpdate(self):
        """Returns the show and its subscriptions from the cuebot. The lock is
        not held during the call, so changing the show does not wait for it."""
        self._itemsLock.lockForRead()
        try:
            show = self.__show
        finally:
            self._itemsLock.unlock()
        if show:
            return show, show.getSubscriptions()
        return show, []

    def _processUpdate(self, work, rpcObjects):
        """Shows the subscriptions, unless the show changed since they were
        requested."""
        show, subscriptions = rpcObjects
        if show is not self.__show:
            return
        # pylint: disable=protected-access
        cuegui.AbstractTreeWidget.AbstractTreeWidget._processUpdate(self, work, subscriptions)

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
