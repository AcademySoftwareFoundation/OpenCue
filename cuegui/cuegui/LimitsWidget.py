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
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions


logger = cuegui.Logger.getLogger(__file__)


class LimitsWidget(QtWidgets.QWidget):
  def __init__(self, parent):
    QtWidgets.QWidget.__init__(self, parent)
    
    self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
    self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
    self.__btnAddLimit = QtWidgets.QPushButton("Add Limit", self)
    self.__btnAddLimit.setFocusPolicy(QtCore.Qt.NoFocus)
    
    self.__monitorLimits = LimitsTreeWidget(self)
    
    layout = QtWidgets.QGridLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(self.__btnAddLimit, 0, 3)
    layout.addWidget(self.__btnRefresh, 0, 2)
    layout.addWidget(self.__monitorLimits, 2, 0, 3, 4)
    
    self.__btnAddLimit.clicked.connect(self.__addLimit)
    self.__btnRefresh.clicked.connect(self.updateSoon)
    
    self.__menuActions = cuegui.MenuActions.MenuActions(self, self.updateSoon, list)

  def updateSoon(self):
    self.__monitorLimits._update()
  
  def __addLimit(self):
    self.__menuActions.limits().create()
    self.updateSoon()
  
  def getColumnVisibility(self):
    return self.__monitorLimits.getColumnVisibility()
  
  def setColumnVisibility(self, settings):
    self.__monitorLimits.setColumnVisibility(settings)


class LimitsTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
  def __init__(self, parent):
    self.startColumnsForType(cuegui.Constants.TYPE_LIMIT)
    self.addColumn("Limit Name", 90, id=1,
                   data=lambda limit: limit.name())
    self.addColumn("Max Value", 80, id=2,
                   data=lambda limit: ("%d" % limit.maxValue()),
                   sort=lambda limit: limit.maxValue())
    self.addColumn("Current Running", 80, id=2,
                   data=lambda limit: ("%d" % limit.currentRunning()),
                   sort=lambda limit: limit.currentRunning())
    
    cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)
    
    # Used to build right click context menus
    self.__menuActions = cuegui.MenuActions.MenuActions(
      self, self.updateSoon, self.selectedObjects)
    
    self.itemClicked.connect(self.__itemSingleClickedToDouble)
    QtGui.qApp.facility_changed.connect(self.__facilityChanged)
    
    self.setUpdateInterval(60)
    
  def __facilityChanged(self):
    """Called when the facility is changed"""
    self.removeAllItems()
    self._update()
  
  def __itemSingleClickedToDouble(self, item, col):
    """Called when an item is clicked on. Causes single clicks to be treated
    as double clicks.
    @type  item: QTreeWidgetItem
    @param item: The item single clicked on
    @type  col: int
    @param col: Column number single clicked on"""
    self.itemDoubleClicked.emit(item, col)
  
  def _createItem(self, object):
    """Creates and returns the proper item"""
    item = LimitWidgetItem(object, self)
    return item
  
  def _getUpdate(self):
    """Returns the proper data from the cuebot"""
    try:
      return opencue.api.getLimits()
    except Exception as e:
      logger.critical(e)
      return []
  
  def contextMenuEvent(self, e):
    """When right clicking on an item, this raises a context menu"""
    menu = QtWidgets.QMenu()
    self.__menuActions.limits().addAction(menu, "editMaxValue")
    menu.addSeparator()
    self.__menuActions.limits().addAction(menu, "delete")
    self.__menuActions.limits().addAction(menu, "rename")
    menu.exec_(QtCore.QPoint(e.globalX(), e.globalY()))


class LimitWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
  def __init__(self, object, parent):
    cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
      self, cuegui.Constants.TYPE_LIMIT, object, parent)
