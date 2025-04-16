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


"""Tree for displaying a list of depends."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map

from qtpy import QtWidgets

from opencue_proto import depend_pb2
import opencue.exception

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class DependMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree for displaying a list of depends."""

    def __init__(self, parent, rpcObject):
        self.startColumnsForType(cuegui.Constants.TYPE_DEPEND)
        self.addColumn("Type", 130, id=1,
                       data=lambda depend: depend_pb2.DependType.Name(depend.type()))
        self.addColumn("Target", 60, id=2,
                       data=lambda depend: depend_pb2.DependTarget.Name(depend.target()))
        self.addColumn("Active", 50, id=3,
                       data=lambda depend: (depend.isActive()))
        self.addColumn("OnJob", 300, id=7,
                       data=lambda depend: (depend.dependOnJob()))
        self.addColumn("OnLayer", 200, id=8,
                       data=lambda depend: (depend.dependOnLayer()))
        self.addColumn("OnFrame", 100, id=9,
                       data=lambda depend: (depend.dependOnFrame()))

        self.rpcObject = rpcObject

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.setUpdateInterval(60)

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        return DependWidgetItem(rpcObject, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            if hasattr(self.rpcObject, "getDepends"):
                return self.rpcObject.getDepends()
            return self.rpcObject.getWhatThisDependsOn()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""

        menu = QtWidgets.QMenu()

        self.__menuActions.dependencies().addAction(menu, "satisfy")

        menu.exec_(e.globalPos())

    def tick(self):
        pass


class DependWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single depend."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_DEPEND, rpcObject, parent)
