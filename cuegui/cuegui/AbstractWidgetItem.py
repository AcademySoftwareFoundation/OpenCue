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


"""Base class for CueGUI widget items.

Provides extended QWidgetItem functionality."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Constants
import cuegui.Logger
import cuegui.Style


logger = cuegui.Logger.getLogger(__file__)

NAME = 0
WIDTH = 1
DISPLAY_LAMBDA = 2
SORT_LAMBDA = 3


class AbstractWidgetItem(QtWidgets.QTreeWidgetItem):
    """Base class for CueGUI widget items.

    Provides extended QWidgetItem functionality."""

    def __init__(self, itemType, rpcObject, parent, source=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent, itemType)
        self.app = cuegui.app()
        self.column_info = self.treeWidget().getColumnInfo(itemType)
        self._cache = {}
        self._source = source
        self.rpcObject = rpcObject

    def update(self, rpcObject=None, parent=None):
        """Updates visual representation with latest data
        @type  rpcObject: Object
        @param rpcObject: The object that contains updated information
        @type  parent: QTreeWidgetItem
        @param parent: Changes the current parent to this parent if different"""
        # Changes parent if needed
        if parent and self.parent() and parent != self.parent():
            self.parent().removeChild(self)
            parent.addChild(self)

        if rpcObject:
            self.rpcObject = rpcObject
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

        if role == QtCore.Qt.ForegroundRole:
            if cuegui.Style.ColorTheme is None:
                cuegui.Style.init()
            return cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND

        if role == QtCore.Qt.UserRole:
            return self.type()

        return cuegui.Constants.QVARIANT_NULL

    def __lt__(self, other):
        """Custom sorting for columns that have a function defined for sorting
           (uses the sort lambda function defined in the subclasses' addColumn definition)."""
        sortLambda = self.column_info[self.treeWidget().sortColumn()][SORT_LAMBDA]
        column = self.treeWidget().sortColumn()

        if sortLambda:
            # pylint: disable=broad-except
            try:
                return sortLambda(self.rpcObject) < sortLambda(other.rpcObject)
            except Exception:
                logger.info("Sort failed on column %s, using text sort.", column)
        return str(self.text(column)) < str(other.text(column))
