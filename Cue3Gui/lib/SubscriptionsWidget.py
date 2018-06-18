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

from decimal import Decimal

import Utils
import Constants
import Style
import Logger

from MenuActions import MenuActions
from AbstractTreeWidget import *
from AbstractWidgetItem import *
from ShowDialog import ShowDialog

class SubscriptionsWidget(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self, parent)

        self.__show = None

        self.__comboShows = QtGui.QComboBox(self)
        self.__comboShows.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__btnShowProperties = QtGui.QPushButton("Show Properties", self)
        self.__btnShowProperties.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__btnAddSubscription = QtGui.QPushButton("Add Subscription", self)
        self.__btnAddSubscription.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__monitorSubscriptions = SubscriptionsTreeWidget(self)

        layout = QtGui.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__comboShows, 0, 0)
        layout.addWidget(self.__btnShowProperties, 0, 2)
        layout.addWidget(self.__btnAddSubscription, 0, 3)
        layout.addWidget(self.__monitorSubscriptions, 2, 0, 3, 4)

        QtCore.QObject.connect(self.__btnShowProperties,
                               QtCore.SIGNAL("clicked()"),
                               self.__showProperties)
        QtCore.QObject.connect(self.__btnAddSubscription,
                               QtCore.SIGNAL("clicked()"),
                               self.__addSubscription)

        QtCore.QObject.connect(self.__comboShows,
                               QtCore.SIGNAL("currentIndexChanged(QString)"),
                               self.setShow)
        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('view_object(PyQt_PyObject)'),
                               self.setShow)
        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('facility_changed()'),
                               self.changeFacility)

        self.__menuActions = MenuActions(self,
                                         self.updateSoon,
                                         self.selectedObjects)

        self.changeFacility()

    def changeFacility(self):
        try:
            self.__shows = dict([(show.name(), show) for show in Cue3.getActiveShows()])
        except Exception, e:
            self.__shows = {}
        self.__comboShows.clear()
        self.__comboShows.addItems(["Select Show:"] +
                                   sorted(self.__shows.keys()))
        self.setShow()

    def setShow(self, show = ""):
        """Sets the show for the subscription list and combo box
        @type  show: QString or str or Show
        @param show: The show to monitor"""

        if isinstance(show, QtCore.QString):
            show = str(show)

        if Utils.isShow(show):
            if self.__show and self.__show.name() == show.name():
                return
            self.__show = show
            show = show.name()
        elif isinstance(show, str):
            if self.__show and self.__show.name() == show:
                return
            if self.__shows.has_key(show):
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
        return self.__show

    def getShowName(self):
        if self.__show:
            return self.__show.data.name
        return None

    def updateSoon(self):
        self.__monitorSubscriptions._update()

    def selectedObjects(self):
        return [Cue3.findShow(self.__show.name())]

    def __showProperties(self):
        if self.__show:
            dialog = ShowDialog(Cue3.findShow(self.__show.name()), self)
            dialog.exec_()
        else:
            self.__comboShows.showPopup()

    def __addSubscription(self):
        if self.__show:
            self.__menuActions.shows().createSubscription([self.__show])
            self.updateSoon()

    def getColumnVisibility(self):
        return self.__monitorSubscriptions.getColumnVisibility()

    def setColumnVisibility(self, settings):
        self.__monitorSubscriptions.setColumnVisibility(settings)

class SubscriptionsTreeWidget(AbstractTreeWidget):
    def __init__(self, parent):

        self.startColumnsForType(Constants.TYPE_SUB)
        self.addColumn("Alloc", 160, id=1,
                       data=lambda sub:(sub.data.allocationName))
        self.addColumn("Usage", 70, id=2,
                       data=lambda sub:(sub.data.size and ("%.2f%%" % (sub.data.reservedCores/sub.data.size * 100)) or 0),
                       sort=lambda sub:(sub.data.size and sub.data.reservedCores/sub.data.size or 0))
        self.addColumn("Size", 70, id=3,
                       data=lambda sub:(sub.data.size),
                       sort=lambda sub:(sub.data.size))
        self.addColumn("Burst", 70, id=4,
                       data=lambda sub:(sub.data.burst),
                       sort=lambda sub:(sub.data.burst))
        self.addColumn("Used", 70, id=5,
                       data=lambda sub:("%.2f" % sub.data.reservedCores),
                       sort=lambda sub:(sub.data.reservedCores))

        AbstractTreeWidget.__init__(self, parent)

        self.__show = None

        # Used to build right click context menus
        self.__menuActions = MenuActions(self,
                                         self.updateSoon,
                                         self.selectedObjects,
                                         self.getShow)

        self.setUpdateInterval(30)

    def setShow(self, show = None):
        self._itemsLock.lockForWrite()
        try:
            if not show:
                self.__show = None
            elif Utils.isShow(show):
                self.__show = show
            elif isinstance(show, str):
                try:
                    self.__show = Cue3.findShow(show)
                except:
                    pass
            self._update()
        finally:
            self._itemsLock.unlock()

    def getShow(self):
        return self.__show

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return SubscriptionWidgetItem(object, self)

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

        menu = QtGui.QMenu()
        self.__menuActions.subscriptions().addAction(menu, "editSize")
        self.__menuActions.subscriptions().addAction(menu, "editBurst")
        menu.addSeparator()
        self.__menuActions.subscriptions().addAction(menu, "delete")
        menu.exec_(QtCore.QPoint(e.globalX(),e.globalY()))

class SubscriptionWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        AbstractWidgetItem.__init__(self, Constants.TYPE_SUB, object, parent)
