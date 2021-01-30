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


from builtins import str

import opencue

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.CreatorDialog
import cuegui.ItemDelegate
import cuegui.MenuActions
import cuegui.ShowDialog
import cuegui.Utils


class SubscriptionGraphWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__shows = []
        self.__showMenuActions = {}
        self.__subBars = []
        self.__timer = QtCore.QTimer(self)
        self.__timer.timeout.connect(self.update_data)
        self.__timer.setInterval(1000 * 5)

        widget = QtWidgets.QWidget()
        self.mainLayout = QtWidgets.QHBoxLayout(widget)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        scroll = QtWidgets.QScrollArea()
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)

        showMenuBtn = QtWidgets.QPushButton(" Shows")
        showMenuBtn.setFixedWidth(100)
        showMenuBtn.pressed.connect(self.__showMenuCheck)

        self.__showMenu = QtWidgets.QMenu(self)
        showMenuBtn.setMenu(self.__showMenu)
        self.__showMenu.setStyleSheet("QMenu { menu-scrollable: 1; }")

        showMenuBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__showMenu.setFont(cuegui.Constants.STANDARD_FONT)
        self.__showMenu.triggered.connect(self.__showMenuHandle)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(showMenuBtn)
        layout.addWidget(scroll)

    def create_widgets(self):
        self.clearLayout(self.mainLayout)
        for show in self.__shows:
            widget = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(widget)

            show_label = QtWidgets.QLabel(show)
            layout.addWidget(show_label)

            sub_bar = SubGraphTreeWidget(self)
            sub_bar.setShow(show)
            layout.addWidget(sub_bar)
            self.__subBars.append(sub_bar)

            self.mainLayout.addWidget(widget)

        self.__timer.start()

    def clearLayout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if not item:
                continue
            w = item.widget()
            if w:
                w.deleteLater()

    def __showMenuHandle(self, action):
        if action.text() == 'All Shows':
            try:
                self.__shows = sorted(set([job.show() for job in opencue.api.getJobs(include_finished=True)]))
            except Exception as e:
                self.__shows = []
            self.__showMenuUpdate()
        elif action.text() == 'Clear':
            self.__shows = []
            self.__showMenuUpdate()
        elif action.isChecked():
            self.__shows.append(action.text())
            self.__showMenuUpdate()
        else:
            self.__shows.remove(action.text())
            self.__showMenuUpdate()

    def __showMenuUpdate(self):
        self.__showMenu.clear()
        self.__showMenuActions = {}

        # add all shows menu item
        action = QtWidgets.QAction('All Shows', self.__showMenu)
        self.__showMenu.addAction(action)
        self.__showMenuActions['All Shows'] = action
        action = QtWidgets.QAction('Clear', self.__showMenu)
        self.__showMenu.addAction(action)
        self.__showMenuActions['Clear'] = action
        self.__showMenu.addSeparator()

        try:
            shows = sorted(set([job.show() for job in opencue.api.getJobs(include_finished=True)]))
        except Exception as e:
            shows = []

        for show in shows:
            action = QtWidgets.QAction(show, self.__showMenu)
            action.setCheckable(True)
            if show in self.__shows:
                action.setChecked(True)
            self.__showMenu.addAction(action)
            self.__showMenuActions[show] = action

        self.create_widgets()

    def __showMenuCheck(self):
        """Populate the list of shows if it is empty"""
        if not self.__showMenuActions:
            self.__showMenuUpdate()

    def update_data(self):
        for sub_bar in self.__subBars:
            sub_bar._getUpdate()


class SubGraphTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_SUB)
        self.addColumn("_Name", 110, id=0,
                       data=lambda sub: sub.data.allocation_name)
        self.addColumn("_Booking Bar", 125, id=1,
                       delegate=cuegui.ItemDelegate.SubBookingBarDelegate,
                       data=lambda sub: opencue.api.findAllocation(sub.data.allocation_name))
        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.header().hide()
        self.__show = None

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects, self.getShow)

        self.setMinimumSize(240, 80)

        # self.setUpdateInterval(30)

    def setShow(self, show=None):
        self._itemsLock.lockForWrite()
        try:
            if not show:
                self.__show = None
            elif cuegui.Utils.isShow(show):
                self.__show = show
            elif isinstance(show, str):
                try:
                    self.__show = opencue.api.findShow(show)
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

        menu = QtWidgets.QMenu()
        self.__menuActions.subscriptions().addAction(menu, "editSize")
        self.__menuActions.subscriptions().addAction(menu, "editBurst")
        menu.addSeparator()
        self.__menuActions.subscriptions().addAction(menu, "delete")
        menu.addSeparator()
        if self.__show:
            new_action = QtWidgets.QAction('Add new subscription', self)
            new_action.triggered.connect(self.createSubscription)
            menu.addAction(new_action)
        menu.exec_(QtCore.QPoint(e.globalX(),e.globalY()))

    def createSubscription(self):
        d = cuegui.CreatorDialog.SubscriptionCreatorDialog(show=self.__show)
        d.exec_()


class SubscriptionWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    def __init__(self, object, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_SUB, object, parent)
