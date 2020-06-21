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
from __future__ import print_function
from __future__ import division

from PySide2 import QtCore
from PySide2 import QtWidgets

import opencue.cloud.api as cloud_api

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions


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



    def getColumnVisibility(self):
        self.__viewCloudGroups.getColumnVisibility()

    def setColumnVisibility(self):
        self.__viewCloudGroups.setColumnVisibility()


class CloudManagerTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_CLOUDGROUP)
        self.addColumn("Cloud Group Name", 90, id=1,
                       data=lambda cig: (cig.name))
        self.addColumn("Cloud Provider", 20, id=2,
                       data=lambda cig: (cig.cloud_provider))
        self.addColumn("Number of instances", 40, id=3,
                       data=lambda cig: (len(cig.instances)))
        self.addColumn("Status", 20, id=4,
                       data=lambda cig: (cig.status()))
        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.__registeredCloudProviders = cloud_api.CloudManager.get_registered_providers()

        self.setUpdateInterval(60)

    def _createItem(self, object):
        """Creates and returns the proper item"""
        item = CloudManagerWidgetItem(object, self)
        return item

    def _getUpdate(self):
        cloud_groups = []

        for provider in self.__registeredCloudProviders:
            cloud_groups.extend(provider.get_all())

        return cloud_groups

    def tick(self):
        pass

class CloudManagerWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    def __init__(self, object, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_CLOUDGROUP, object, parent)