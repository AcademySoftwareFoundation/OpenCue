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


"""Widget showing a tree view of a job and its layers."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import range
from qtpy import QtCore, QtGui, QtWidgets

from cuesubmit import Layer
from cuesubmit.ui import Style


class CueJobWidget(QtWidgets.QWidget):
    """Job tree view allowing users create additional layers and control their settings."""

    selectionChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(CueJobWidget, self).__init__(parent=parent)

        self.table = CueJobTree()
        self.table.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                 QtWidgets.QSizePolicy.MinimumExpanding)
        self.model = CueJobModel()
        self.jobRow = QtGui.QStandardItem('')
        self.jobRow.setEditable(False)
        self.currentLayerData = Layer.LayerData()
        self.layers = [self.currentLayerData]

        self.addLayerButton = QtWidgets.QToolButton()
        self.deleteLayerButton = QtWidgets.QToolButton()
        self.downButton = QtWidgets.QToolButton()
        self.upButton = QtWidgets.QToolButton()

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.buttonLayout = QtWidgets.QHBoxLayout()

        self.setupButtons()
        self.setupUi()
        self.setupConnections()
        self.selected = self.jobRow.child(0)

    def setupUi(self):
        """Creates the widget layout."""
        self.setLayout(self.mainLayout)
        self.table.setModel(self.model)
        header = self.table.header()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setStyleSheet(Style.HEADER_VIEW)
        self.model.appendRow(self.jobRow)
        self.mainLayout.addWidget(self.table)
        self.buttonLayout.addWidget(self.addLayerButton)
        self.buttonLayout.addWidget(self.deleteLayerButton)
        self.buttonLayout.addWidget(self.downButton)
        self.buttonLayout.addWidget(self.upButton)
        self.mainLayout.addLayout(self.buttonLayout)
        self.table.expandAll()
        self.initLayers()

    def setupConnections(self):
        """Sets up widget signals."""
        self.table.selectionModel().selectionChanged.connect(self.updateSelection)
        # pylint: disable=no-member
        self.addLayerButton.clicked.connect(self.newLayer)
        self.deleteLayerButton.clicked.connect(self.removeRow)
        self.upButton.clicked.connect(self.moveUp)
        self.downButton.clicked.connect(self.moveDown)
        # pylint: enable=no-member

    def setupButtons(self):
        """Creates buttons working with job layers."""
        self.addLayerButton.setAccessibleName('editLayer')
        self.addLayerButton.setText('+')
        self.deleteLayerButton.setAccessibleName('editLayer')
        self.deleteLayerButton.setText('-')
        self.downButton.setArrowType(QtCore.Qt.DownArrow)
        self.upButton.setArrowType(QtCore.Qt.UpArrow)
        self.addLayerButton.setToolTip('Add a new Layer to the Job.')
        self.deleteLayerButton.setToolTip('Delete the selected Layer from the Job.')
        self.downButton.setToolTip('Move the selected Layer down in the Job.')
        self.upButton.setToolTip('Move the selected Layer up in the Job.')

    @staticmethod
    def createRowData(data):
        """Create and setup items. Return them as a row array.
        @type data: Layer.LayerData
        @param data: data object containing the settings for row to create
        """
        name = QtGui.QStandardItem(data.name)
        name.setData(data, QtCore.Qt.UserRole)
        name.layerData = data
        job = QtGui.QStandardItem(data.layerType)
        frames = QtGui.QStandardItem(data.layerRange)
        depend = QtGui.QStandardItem(data.dependType)
        return [name, job, frames, depend]

    def addRow(self, data):
        """Add a new row to the list of layers
        @type data: Layer.LayerData
        @param data: data object containing the settings for row to create
        """
        self.jobRow.appendRow(self.createRowData(data))

    def insertRow(self, row, data):
        """Create a new row at the given index.
        @type row: int
        @param row: index of where to insert the row
        @type data: Layer.LayerData
        @param data: data object containing the settings for row to create
        """
        newRowData = self.createRowData(data)
        self.jobRow.insertRow(row, newRowData)

    def removeRow(self):
        """Remove the current selected Row.
        @rtype: Layer.LayerData
        @return: the layer date that was removed
        """
        row = self.getCurrentRow()
        self.jobRow.removeRow(row)
        return self.layers.pop(row)

    def moveUp(self):
        """Move the currently selected row up one index."""
        currentRow = self.getCurrentRow()
        if currentRow > 0:
            rowData = self.removeRow()
            self.insertRow(currentRow - 1, rowData)
            self.layers.insert(currentRow - 1, rowData)
        if currentRow == 1:
            layer = self.layers[0]
            layer.dependType = ''
        self.updateDependLabels()

    def moveDown(self):
        """Move the currently selected row down one index."""
        currentRow = self.getCurrentRow()
        if currentRow < (self.jobRow.rowCount() - 1):
            rowData = self.removeRow()
            self.insertRow(currentRow + 1, rowData)
            self.layers.insert(currentRow + 1, rowData)
        self.updateDependLabels()

    def selectRow(self, rowNum):
        """Select the given row index.
        @type rowNum: int
        @param rowNum: row index to select
        """
        selectionModel = self.table.selectionModel()
        selectionModel.setCurrentIndex(
            self.model.indexFromItem(self.jobRow.child(rowNum)),
            QtCore.QItemSelectionModel.ClearAndSelect)
        for col in range(1, self.jobRow.columnCount()):
            selectionModel.setCurrentIndex(
                self.model.indexFromItem(self.jobRow.child(rowNum, col)),
                QtCore.QItemSelectionModel.Select)

    def clearLayers(self):
        """Clear all layers from the tree."""
        for _ in range(self.jobRow.rowCount()):
            self.jobRow.removeRow(0)

    def getAllLayers(self):
        """Return all layer data from tree.
        @rtype: list<Layer.LayerData>
        @return: list of all layers in the job tree
        """
        layersData = []
        for row in range(self.jobRow.rowCount()):
            nameItem = self.jobRow.child(row, 0)
            data = nameItem.data(QtCore.Qt.UserRole)
            layersData.append(data)
        return layersData

    def getCurrentRow(self):
        """Return the current selected row number.
        @rtype: int
        @return: row number
        """
        item = self.getSelectedItem()
        if item:
            return item.row()
        return None

    def getDependOnItem(self):
        """Return the layer that the current layer depends on.
        @rtype: QStandardItem
        @return: the item from the job tree that the current layer depends on.
        """
        currentRow = self.getCurrentRow()
        if currentRow == 0:
            return None
        return self.jobRow.child(currentRow - 1, 0)

    def getSelectedItem(self):
        """Return the selected item from the tree.
        @rtype: QStandardItem
        @return: selected item from the job tree
        """
        currentIndex = self.table.selectionModel().currentIndex()
        return self.model.itemFromIndex(currentIndex)

    def initLayers(self):
        """Initialize the job tree, adding an empty layer."""
        self.addRow(self.currentLayerData)
        self.selected = self.jobRow.child(0)
        self.setSelectedFromItem(self.selected)

    def newLayer(self):
        """Create a new Layer and add it to the job tree."""
        self.currentLayerData = Layer.LayerData()
        self.layers.append(self.currentLayerData)
        self.addRow(self.currentLayerData)
        self.selected = self.jobRow.child(self.getCurrentRow() + 1)
        self.setSelectedFromItem(self.selected)
        self.updateDependLabels()

    def setSelectedFromItem(self, item):
        """Given an item, select it's row.
        @type item: QStandardItem
        @param item: Item to select """
        row = self.model.indexFromItem(item).row()
        self.selectRow(row)

    def updateJobData(self, jobName):
        """Update the job tree with a new job name.
        @type jobName: str
        @param jobName: new job name to update to
        """
        self.jobRow.setText(jobName)
        self.updateSelectedLayer()

    def updateLayerData(self, **kwargs):
        """Update the tree and labels with new data.
        See Layer.LayerData.update for params."""
        self.currentLayerData = self.layers[self.getCurrentRow()]
        self.currentLayerData.update(**kwargs)
        self.layers[self.getCurrentRow()] = self.currentLayerData
        self.updateSelectedLayer()

    def updateSelectedLayer(self):
        """Update the selected layer in the tree with the current layer's data."""
        currentRow = self.getCurrentRow()
        nameItem = self.jobRow.child(currentRow, 0)
        typeItem = self.jobRow.child(currentRow, 1)
        rangeItem = self.jobRow.child(currentRow, 2)
        dependTypeItem = self.jobRow.child(currentRow, 3)

        nameItem.setText(self.currentLayerData.name)
        nameItem.setData(self.currentLayerData, QtCore.Qt.UserRole)
        typeItem.setText(self.currentLayerData.layerType)
        rangeItem.setText(self.currentLayerData.layerRange)
        if self.currentLayerData.dependType:
            dependOnItem = self.getDependOnItem()
            dependOnText = '{} ({})'.format(self.currentLayerData.dependType, dependOnItem.text())
        else:
            dependOnText = ''
        dependTypeItem.setText(dependOnText)
        self.updateDependLabels()

    def updateDependLabels(self):
        """Update the dependency labels for all layers in tree."""
        for row in range(self.jobRow.rowCount()):
            layer = self.layers[row]
            dependTypeItem = self.jobRow.child(row, 3)
            if layer.dependType:
                dependOnItem = self.jobRow.child(row - 1, 0)
                dependOnText = '{} ({})'.format(layer.dependType, dependOnItem.text())
            else:
                dependOnText = ''
            dependTypeItem.setText(dependOnText)

    def updateSelection(self, selectionItem):
        """Update the selection to the given item.
        Called when a selection change occurs in the table.
        @type selectionItem: QItemSelection
        @param selectionItem: item selection passed in by the selection change event
        """
        self.currentLayerData = self.layers[self.getCurrentRow()]
        if self.model.indexFromItem(self.jobRow) == selectionItem.indexes()[0]:
            # Job Row is selected. Update selection to the last selected or first layer.
            if self.selected is None:
                self.selected = self.jobRow.child(0)
            self.setSelectedFromItem(self.selected)
        else:
            currentRow = self.getCurrentRow()
            self.selected = self.jobRow.child(currentRow)
            self.selectionChanged.emit(self.currentLayerData)


class CueJobTree(QtWidgets.QTreeView):
    """Inner table for displaying job data."""

    def __init__(self, parent=None):
        super(CueJobTree, self).__init__(parent=parent)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setUniformRowHeights(True)
        self.setMinimumHeight(100)
        self.setStyleSheet(Style.TREE_VIEW)


class CueJobModel(QtGui.QStandardItemModel):
    """Data model for a job, in Qt format."""

    def __init__(self):
        super(CueJobModel, self).__init__()
        self.setHorizontalHeaderLabels(['Layer Name', 'Job Type', 'Frames', 'Depend Type'])

    def getAllLayers(self):
        """Return the layer objects for all layers in the model"""
        jobItem = self.item(0, 0)
        layerObjects = [jobItem.child(row, 0).data(QtCore.Qt.UserRole)
                        for row in range(jobItem.rowCount())]
        return layerObjects
