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


"""
Provides extended QWidgetItem functionality.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from PySide2 import QtCore
from PySide2 import QtWidgets

from cuegui import Constants
from cuegui import Logger
from cuegui import Style


logger = Logger.getLogger(__file__)

NAME = 0
WIDTH = 1
DISPLAY_LAMBDA = 2
SORT_LAMBDA = 3


class AbstractWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, itemType, object, parent, source=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent, itemType)
        self.column_info = self.treeWidget().getColumnInfo(itemType)
        self._cache = {}
        self._source = source
        self.rpcObject = object

    def update(self, object=None, parent=None):
        """Updates visual representation with latest data
        @type  object: Object
        @param object: The object that contains updated information
        @type  parent: QTreeWidgetItem
        @param parent: Changes the current parent to this parent if different"""
        # Changes parent if needed
        if parent and self.parent() and parent != self.parent():
            self.parent().removeChild(self)
            parent.addChild(self)

        if object:
            self.rpcObject = object
            self._cache = {}

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][DISPLAY_LAMBDA](self.rpcObject)

        elif role == QtCore.Qt.ForegroundRole:
            if Style.ColorTheme is None:
                Style.init()
            return Style.ColorTheme.COLOR_JOB_FOREGROUND

        elif role == QtCore.Qt.UserRole:
            return self.type()

        return Constants.QVARIANT_NULL

    def __lt__(self, other):
        """Custom sorting for columns that have a function defined for sorting"""
        sortLambda = self.column_info[self.treeWidget().sortColumn()][SORT_LAMBDA]
        column = self.treeWidget().sortColumn()
        if sortLambda:
            try:
                return sortLambda(self.rpcObject) > sortLambda(other.rpcObject)
            except:
                logger.warning("Sort failed on column {}, using text sort.".format(column))
        return str(self.text(column)) > str(other.text(column))
