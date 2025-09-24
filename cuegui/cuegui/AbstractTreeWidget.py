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


"""Base class for CueGUI tree widgets.

Provides extended QTreeWidget functionality."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import map
from builtins import range
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.ItemDelegate
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


COLUMN_NAME = 0
COLUMN_WIDTH = 1
COLUMN_FUNCTION = 2
COLUMN_SORTBY = 3
COLUMN_DELEGATE = 4
COLUMN_TOOLTIP = 5
COLUMN_INFO_LENGTH = 6

DEFAULT_NAME = ""
DEFAULT_WIDTH = 0


# pylint: disable=unused-argument
def DEFAULT_LAMBDA(s):
    """Dummy function to return something"""
    return ""


class AbstractTreeWidget(QtWidgets.QTreeWidget):
    """Base class for CueGUI tree widgets.

    Provides extended QTreeWidget functionality."""

    itemDoubleClicked = QtCore.Signal(QtWidgets.QTreeWidgetItem, int)
    itemSingleClicked = QtCore.Signal(QtWidgets.QTreeWidgetItem, int)
    updated = QtCore.Signal()

    def __init__(self, parent):
        """Standard method to display a list or tree using QTreeWidget

        columnInfoByType is a dictionary of lists keyed to opencue.Constants.TYPE_*
        Each value is a list of lists that each define a column.
        [<column name>, <width>, <lambda function>, <function name for sorting>,
        <column delegate class>]
        Only supported on the primary column:
        <column name>, <column delegate class>, <width>

        @type  parent: QWidget
        @param parent: The widget to set as the parent"""
        QtWidgets.QTreeWidget.__init__(self, parent)
        self.app = cuegui.app()

        self._items = {}
        self._lastUpdate = 0

        self._itemsLock = QtCore.QReadWriteLock()
        self._timer = QtCore.QTimer(self)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.setUniformRowHeights(True)
        self.setAutoScroll(False)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAlternatingRowColors(True)

        self.setSortingEnabled(True)
        self.header().setSectionsMovable(True)
        self.header().setStretchLastSection(True)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)

        self.setItemDelegate(cuegui.ItemDelegate.ItemDelegate(self))

        self.__setupColumns()

        self.__setupColumnMenu()

        # pylint: disable=no-member
        self.itemClicked.connect(self.__itemSingleClickedEmitToApp)
        self.itemDoubleClicked.connect(self.__itemDoubleClickedEmitToApp)
        self._timer.timeout.connect(self.updateRequest)
        # pylint: enable=no-member
        self.app.request_update.connect(self.updateRequest)

        self.updateRequest()
        self.setUpdateInterval(10)

    def closeEvent(self, event):
        """Close Event"""
        if hasattr(self, '_timer'):
            self._timer.stop()
            del self._timer

        if hasattr(self, '__ticksTimer'):
            self.__ticksTimer.stop()
            del self.__ticksTimer

        event.accept()

    # pylint: disable=attribute-defined-outside-init
    def startColumnsForType(self, itemType):
        """Start column definitions for the given item type. The first call to
        this defines the primary column type used to populate the column headers.
        @type  itemType: int
        @param itemType: The id for the item type"""
        # First call defines the primary type
        if not hasattr(self, "columnPrimaryType"):
            self.columnPrimaryType = itemType
            self.__columnPrimaryType = itemType
            self.__columnInfoByType = {}

        self.__columnInfoByType[itemType] = []
        self.__columnCurrent = itemType

    # pylint: disable=redefined-builtin
    def addColumn(self, name, width, id=0, default=True,
                  data=DEFAULT_LAMBDA, sort=None,
                  delegate=None, tip=""):
        """Define a new column for the current item type.
        @type  name: str
        @param name: The name of the column.
        @type  width: int
        @param width: The width of the column.
        @type  id: int
        @param id: A unique id
        @type  default: bool
        @param default: Will determine if the column is displayed by default.
        @type  data: callable
        @param data: The callable to use when displaying.
        @type  sort: callable
        @param sort: The callable to use when sorting.
        @type  delegate: delegate
        @param delegate: The delegate that should draw the cells.
        @type  tip: str
        @param tip: A tooltip for the column."""
        assert isinstance(name, str), "Column name must be string"
        assert isinstance(width, int), "Column width must be int"
        assert hasattr(data, '__call__'), "Column data function must be callable"
        assert isinstance(tip, str), "Column tooltip must be string"

        columnsInfo = self.__columnInfoByType[self.__columnCurrent]
        columnsInfo.append([name, width, data, sort, delegate, tip, default, id])

    def __setupColumns(self):
        """Setup the QTreeWidget based on the column information"""
        primaryColumnInfo = self.__columnInfoByType[self.__columnPrimaryType]

        self.setColumnCount(len(primaryColumnInfo))

        columnNames = []
        for col, columnInfo in enumerate(primaryColumnInfo):
            # Set up column widths
            self.setColumnWidth(col, primaryColumnInfo[col][COLUMN_WIDTH])

            # Setup the column tooltips
            if columnInfo[COLUMN_TOOLTIP]:
                self.model().setHeaderData(col, QtCore.Qt.Horizontal,
                                           columnInfo[COLUMN_TOOLTIP],
                                           QtCore.Qt.ToolTipRole)

            # Setup column delegates
            if primaryColumnInfo[col][COLUMN_DELEGATE]:
                self.setItemDelegateForColumn(col, primaryColumnInfo[col][COLUMN_DELEGATE](self))

            # Setup column name list
            if columnInfo[COLUMN_NAME].startswith("_"):
                columnNames.append("")
            else:
                columnNames.append(columnInfo[COLUMN_NAME])

        self.setHeaderLabels(columnNames)


    def startTicksUpdate(self, updateInterval,
                         updateWhenMinimized=False,
                         maxUpdateInterval=None):
        """A method of updating the display on a one second timer to avoid
        multiple update requests and reduce excess cuebot calls.
        You will need to implement self.tick, You do not need to provide
        locking or unhandled error logging.
        You will need to implement tick.
        self.ticksWithoutUpdate = number of seconds since the last update.
        self.ticksLock = QMutex"""
        self.updateInterval = updateInterval
        self.__updateWhenMinimized = updateWhenMinimized
        self.__maxUpdateInterval = maxUpdateInterval

        # Stop the default update method
        if hasattr(self, "_timer"):
            self._timer.stop()

        self.ticksLock = QtCore.QMutex()
        self.__ticksTimer = QtCore.QTimer(self)
        self.__ticksTimer.timeout.connect(self.__tick)  # pylint: disable=no-member
        self.__ticksTimer.start(1000)
        self.ticksWithoutUpdate = 999

    def tickNeedsUpdate(self):
        """Gets whether enough time has passed for contents to need an update."""
        if self.ticksWithoutUpdate >= self.updateInterval:
            if self.window().isMinimized():
                if self.__maxUpdateInterval is not None and \
                   self.ticksWithoutUpdate >= self.__maxUpdateInterval:
                    # Sufficient maximum interval
                    return True
                if not self.__updateWhenMinimized:
                    # Sufficient interval, except minimized
                    return False
                # Sufficient interval, set to update when minimized
                return True
            # Sufficient interval, not minimized
            return True
        # Insufficient interval
        return False

    def __tick(self):
        """Provides locking and logging for the implementation of the tick
        function"""
        if not self.ticksLock.tryLock():
            return
        try:
            # pylint: disable=broad-except
            try:
                self.tick()
            except Exception as e:
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
        finally:
            self.ticksLock.unlock()

    def tick(self):
        """Determines whether an update is needed and initiates updating logic.

        Must be defined by inheriting classes."""
        raise NotImplementedError

    def getColumnInfo(self, columnType = None):
        """Returns the list that defines the column.
        @type  columnType: Constants.TYPE_*
        @param columnType: If given, the column information for that type will
                           be returned. Otherwise the primary column information
                           will be returned
        @rtype:  list
        @return: The list that defines the column,
                 (see AbstractTreeWidget.__init__() documentation)"""
        if columnType:
            return self.__columnInfoByType[columnType]
        return self.__columnInfoByType[self.__columnPrimaryType]

    @staticmethod
    def __itemSingleClickedEmitToApp(item, col):
        """When an item is single clicked on:
        emits "single_click(PyQt_PyObject)" to the app
        @type  item: QTreeWidgetItem
        @param item: The item single clicked on
        @type  col: int
        @param col: Column number single clicked on"""
        del col
        if hasattr(item, 'rpcObject'):
            cuegui.app().single_click.emit(item.rpcObject)

    @staticmethod
    def __itemDoubleClickedEmitToApp(item, col):
        """Handles when an item is double clicked on.
        emits "double_click(PyQt_PyObject)" to the app
        emits "view_object(PyQt_PyObject)" to the app
        @type  item: QTreeWidgetItem
        @param item: The item double clicked on
        @type  col: int
        @param col: Column number double clicked on"""
        del col
        cuegui.app().view_object.emit(item.rpcObject)
        cuegui.app().double_click.emit(item.rpcObject)

    def addObject(self, rpcObject):
        """Adds or updates an rpcObject in the list using the _createItem function
        and object.proxy as the key. Used when user is adding an item but will
        not want to wait for an update.
        @type  paramA: opencue object
        @param paramA: Object that provides .proxy"""
        self._itemsLock.lockForWrite()
        try:
            # If id already exists, update it
            objectKey = cuegui.Utils.getObjectKey(rpcObject)
            if objectKey in self._items:
                self._items[objectKey].update(rpcObject)
            # If id does not exist, create it
            else:
                self._items[objectKey] = self._createItem(rpcObject)
        finally:
            self._itemsLock.unlock()

    def removeItem(self, item):
        """Removes an item from the TreeWidget
        @param item: A tree widget item
        @type  item: AbstractTreeWidgetItem"""
        self._itemsLock.lockForWrite()
        try:
            self._removeItem(item)
        finally:
            self._itemsLock.unlock()

    def _removeItem(self, item):
        """Removes an item from the TreeWidget without locking
        @type  item: AbstractTreeWidgetItem or String
        @param item: A tree widget item or the string with the id of the item"""
        if item in self._items:
            item = self._items[item]
        elif not isinstance(item, cuegui.AbstractWidgetItem.AbstractWidgetItem):
            # if the parent was already deleted, then this one was too
            return

        # If it has children, they must be deleted first
        if item.childCount() > 0:
            for child in item.takeChildren():
                self._removeItem(child)

        if item.isSelected():
            item.setSelected(False)

        if item.parent():
            item.parent().removeChild(item)
        else:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        objectClass = item.rpcObject.__class__.__name__
        objectId = item.rpcObject.id()
        # Use pop with default value to avoid KeyError when item doesn't exist
        # This can happen with archived jobs or when items are already removed
        self._items.pop('{}.{}'.format(objectClass, objectId), None)

    def removeAllItems(self):
        """Removes all items from the tree."""
        self._itemsLock.lockForWrite()
        try:
            self._items = {}
            self.clear()
        finally:
            self._itemsLock.unlock()

    def selectedObjects(self):
        """Provides a list of all objects from selected items
        @return: A list of objects from selected items
        @rtype:  list<object>"""
        return [item.rpcObject for item in self.selectedItems()]

    def setUpdateInterval(self, seconds):
        """Changes the update interval
        @param seconds: Update interval in seconds
        @type  seconds: int"""
        self._timer.start(seconds * 1000)

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated and the user has not scrolled recently if
        self._limitUpdatesDuringScrollSetup() was called in the TreeWidget
        object init"""
        if time.time() - self._lastUpdate > cuegui.Constants.MINIMUM_UPDATE_INTERVAL:
            if self.__limitUpdatesDuringScrollAllowUpdate():
                self._update()

    def _update(self):
        """Updates the items in the TreeWidget without checking when it was last
        updated"""
        self._lastUpdate = time.time()
        if self.app.threadpool is not None:
            self.app.threadpool.queue(
                self._getUpdate, self._processUpdate, "getting data for %s" % self.__class__)
        else:
            logger.warning("threadpool not found, doing work in gui thread")
            self._processUpdate(None, self._getUpdate())

    def _processUpdate(self, work, rpcObjects):
        """A generic function that Will:
        Create new TreeWidgetItems if an item does not exist for the object.
        Update existing TreeWidgetItems if an item already exists for the object.
        Remove items that were not updated with rpcObjects.
        @param work:
        @type  work: from ThreadPool
        @param rpcObjects: A list of rpc objects
        @type  rpcObjects: list<rpc object> """
        del work
        self._itemsLock.lockForWrite()
        try:
            updated = []
            for rpcObject in rpcObjects:
                objectId = "{}.{}".format(rpcObject.__class__.__name__, rpcObject.id())
                updated.append(objectId)

                # If id already exists, update it
                if objectId in self._items:
                    self._items[objectId].update(rpcObject)
                # If id does not exist, create it
                else:
                    self._items[objectId] = self._createItem(rpcObject)

            # Remove any items that were not updated
            for proxy in list(set(self._items.keys()) - set(updated)):
                self._removeItem(proxy)
            self.redraw()
        finally:
            self._itemsLock.unlock()

    def updateSoon(self):
        """Returns immediately. Causes an update to happen
        Constants.AFTER_ACTION_UPDATE_DELAY after calling this function."""
        if hasattr(self, "ticksWithoutUpdate"):
            self.ticksWithoutUpdate = self.updateInterval - \
                                      cuegui.Constants.AFTER_ACTION_UPDATE_DELAY // 1000
        else:
            QtCore.QTimer.singleShot(cuegui.Constants.AFTER_ACTION_UPDATE_DELAY,
                                     self.updateRequest)

    def redraw(self):
        """Forces the displayed items to be redrawn"""
        if not self.window().isMinimized():
            # pylint: disable=broad-except
            try:
                self.scheduleDelayedItemsLayout()
            except Exception as e:
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def getColumnWidths(self):
        """Gets the column widths.
        @rtype: list<int>
        @return: A list of column widths"""
        return [self.columnWidth(index) for index in range(self.columnCount())]

    def setColumnWidths(self, widths):
        """Sets the column widths if the correct number are provided, but ignore
        the last one since it is stretched to the end.
        @type  widths: list<int>
        @param widths: The desired width for each column"""
        if len(widths) == self.columnCount():
            for index, width in enumerate(widths[:-1]):
                self.setColumnWidth(index, width)

    ################################################################################
    # Optionally limit updates when user scrolls
    ################################################################################

    def _limitUpdatesDuringScrollSetup(self, skipsAllowed = 1, delay = 1.0):
        """Allows the ability to skip updates when the user is scrolling
        @type  skipsAllowed: int
        @param skipsAllowed: Defines how many skips are allowed before ignoring
                             that the user is scrolling
        @type  delay: float
        @param delay: Defines how many seconds it must have been since the user
                      last scrolled before allowing an update."""
        self.limitUpdatesDuringScroll = True
        self.__lastScrollTime = 0
        self.__updateSkipCount = 0
        self.__allowedSkipCount = skipsAllowed
        self.__allowedSkipDelay = delay
        self.verticalScrollBar().valueChanged.connect(self.__userScrolled)

    def __userScrolled(self, val):
        """Stores the time when the user last scrolled"""
        del val
        self.__lastScrollTime = time.time()

    def __limitUpdatesDuringScrollAllowUpdate(self):
        """Returns False if the user recently scrolled and the table should not
        be updated.
        @rtype: bool
        @return: Returns true if it is ok to update the table"""
        if not hasattr(self, "limitUpdatesDuringScroll"):
            return True

        if (time.time() - self.__lastScrollTime > self.__allowedSkipDelay or
                self.__updateSkipCount >= self.__allowedSkipCount):
            self.__updateSkipCount = 0
            return True

        self.__updateSkipCount += 1
        return False

    ################################################################################
    # Allow the user to show or hide columns
    ################################################################################

    def __setupColumnMenu(self):
        self.__dropdown = QtWidgets.QToolButton(self)
        self.__dropdown.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__dropdown.setFixedHeight(self.header().height() - 10)
        self.__dropdown.setToolTip("Click to select columns to display")
        self.__dropdown.setIcon(QtGui.QIcon(":column_popdown.png"))
        self.__dropdown.clicked.connect(self.__displayColumnMenu)  # pylint: disable=no-member

        layout = QtWidgets.QHBoxLayout(self.header())
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignRight)
        layout.addWidget(self.__dropdown)

    def __displayColumnMenu(self):
        point = self.__dropdown.mapToGlobal(QtCore.QPoint(self.__dropdown.width(),
                                                          self.__dropdown.height()))

        menu = QtWidgets.QMenu(self)
        menu.triggered.connect(self.__handleColumnMenu)  # pylint: disable=no-member
        for col in range(self.columnCount()):
            if self.columnWidth(col) or self.isColumnHidden(col):
                name = self.__columnInfoByType[self.__columnPrimaryType][col][COLUMN_NAME]
                a = QtWidgets.QAction(menu)
                a.setText("%s. %s" % (col, name))
                a.setCheckable(True)
                a.setChecked(not self.isColumnHidden(col))
                menu.addAction(a)
        menu.exec_(point)

    def __handleColumnMenu(self, action):
        col = int(action.text().split(".")[0])
        self.setColumnHidden(col, not action.isChecked())

        if action.isChecked() and not self.columnWidth(col):
            width = self.__columnInfoByType[self.__columnPrimaryType][col][COLUMN_WIDTH]
            self.setColumnWidth(col, width)

    def getColumnVisibility(self):
        """Gets table column visibility."""
        settings = []
        for col in range(self.columnCount()):
            settings.append(self.isColumnHidden(col))
        return settings

    def setColumnVisibility(self, settings):
        """Sets table column visibility."""
        if settings:
            for col, setting in enumerate(settings):
                if col <= self.columnCount():
                    self.setColumnHidden(col, setting)

    ################################################################################
    # Allow the user to move columns and remember position
    ################################################################################

    def getColumnOrder(self):
        """Gets table column order."""
        settings = {}
        header = self.header()
        for col in range(header.count()):
            settings[col] = header.logicalIndex(col)
        return settings

    def setColumnOrder(self, settings):
        """Sets table column order."""
        header = self.header()
        # pylint: disable=unnecessary-lambda
        cols = sorted(settings.keys(), key=lambda x: int(x))
        for col in cols:
            old_col = header.visualIndex(settings[col])
            header.moveSection(int(old_col), int(col))
