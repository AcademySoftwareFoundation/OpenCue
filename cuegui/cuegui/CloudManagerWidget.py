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

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from PySide2 import QtCore
from PySide2 import QtWidgets

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.CloudGroupDialog
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions
import opencue.cloud.api


logger = cuegui.Logger.getLogger(__file__)


class CloudManagerWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__btnAddCloudGroup = QtWidgets.QPushButton("Add Cloud Group", self)
        self.__btnAddCloudGroup.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__viewCloudGroups = CloudManagerTreeWidget(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.__btnAddCloudGroup, 0, 3)
        layout.addWidget(self.__viewCloudGroups, 2, 0, 3, 4)

        #TODO: Add a force refresh button ?

        self.__btnAddCloudGroup.clicked.connect(self._onAddCloudGroupClicked)

    def _onAddCloudGroupClicked(self):
        cuegui.CloudGroupDialog.CloudGroupCreateDialog(self).show()

    def getColumnVisibility(self):
        self.__viewCloudGroups.getColumnVisibility()

    def setColumnVisibility(self):
        self.__viewCloudGroups.setColumnVisibility()


class CloudManagerTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_CLOUDGROUP)
        self.addColumn("Cloud Group Name", 250, id=1,
                       data=lambda cig: cig.name())
        self.addColumn("Cloud Provider", 100, id=2,
                       data=lambda cig: cig.__signature__)
        self.addColumn("Number of instances", 160, id=3,
                       data=lambda cig: cig.current_group_size_info())
        self.addColumn("Status", 60, id=4,
                       data=lambda cig: (cig.status()))
        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # New manager objects instantiated here
        self.__registeredCloudProviders = opencue.cloud.api.CloudManager.get_registered_providers()

        # Connect for all the registered providers
        for provider in self.__registeredCloudProviders:
            provider.connect()

        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.setUpdateInterval(30)

    def _createItem(self, object):
        """Creates and returns the proper item"""
        item = CloudManagerWidgetItem(object, self)
        return item

    def _getUpdate(self):
        cloud_groups = []

        for manager_instance in self.__registeredCloudProviders:
            cloud_groups.extend(manager_instance.get_all_groups())

        return cloud_groups

    def tick(self):
        pass

    def contextMenuEvent(self, e):
        """
        Context menu for cloudgroup widget
        """

        count = len(self.selectedObjects())
        menu = QtWidgets.QMenu()

        if count:
            self.__menuActions.cloudgroups().addAction(menu, "removeGroup")
            if count == 1:
                self.__menuActions.cloudgroups().addAction(menu, "editInstances")

            menu.exec_(QtCore.QPoint(e.globalX(), e.globalY()))


class CloudManagerWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    def __init__(self, object, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_CLOUDGROUP, object, parent)
