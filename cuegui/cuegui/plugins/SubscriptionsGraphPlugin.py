from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from PySide2 import QtCore
from PySide2 import QtWidgets

import cuegui.AbstractDockWidget
import cuegui.SubscriptionGraphWidget

PLUGIN_NAME = 'Subscription Graphs'
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An administrator interface to subscriptions"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = 'SubscriptionGraphDockWidget'


class SubscriptionGraphDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.layout().addWidget(self.__splitter)

        self.__subgraph_widget = cuegui.SubscriptionGraphWidget.SubscriptionGraphWidget(self)
        self.__splitter.addWidget(self.__subgraph_widget)

        self.setMinimumSize(500, 190)
