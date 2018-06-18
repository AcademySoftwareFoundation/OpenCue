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


import os
import Cue3Gui
import Cue3

from PyQt4 import QtGui, QtCore

from decimal import Decimal

PLUGIN_NAME = "Subscriptions"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to subscriptions"
PLUGIN_REQUIRES = "CueCommander3"
PLUGIN_PROVIDES = "SubscriptionDockWidget"

class SubscriptionDockWidget(Cue3Gui.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        Cue3Gui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__splitter = QtGui.QSplitter(QtCore.Qt.Horizontal)
        self.layout().addWidget(self.__splitter)

        self.__subscriptionsWidget = Cue3Gui.SubscriptionsWidget(self)
        #self.__graphSubscriptionsWidget = Cue3Gui.GraphSubscriptionsWidget(self)

        self.__splitter.addWidget(self.__subscriptionsWidget)
        #self.__splitter.addWidget(self.__graphSubscriptionsWidget)

        self.pluginRegisterSettings([("splitterSize",
                                      self.__splitter.sizes,
                                      self.__splitter.setSizes),
                                     ("show",
                                      self.__subscriptionsWidget.getShowName,
                                      self.__subscriptionsWidget.setShow),
                                     ("columnVisibility",
                                      self.__subscriptionsWidget.getColumnVisibility,
                                      self.__subscriptionsWidget.setColumnVisibility)])
