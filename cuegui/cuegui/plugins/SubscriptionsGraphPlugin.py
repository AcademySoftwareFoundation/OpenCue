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


"""Plugin for listing a show's subscriptions and a visualization of what's being consumed."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.AbstractDockWidget
import cuegui.SubscriptionGraphWidget


PLUGIN_NAME = 'Subscription Graphs'
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to subscriptions"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = 'SubscriptionGraphDockWidget'


class SubscriptionGraphDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Containing widget for this plugin."""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.layout().addWidget(self.__splitter)

        self.__subgraph_widget = cuegui.SubscriptionGraphWidget.SubscriptionGraphWidget(self)
        self.__splitter.addWidget(self.__subgraph_widget)

        self.setMinimumSize(500, 190)
