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


"""Dialog to display/modify a show's filters, matchers and actions."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
from builtins import str

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import opencue
import opencue_proto.filter_pb2

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.MenuActions
import cuegui.TextEditDialog
import cuegui.Utils

from cuegui.Constants import DISABLED_ACTION_TYPES

logger = cuegui.Logger.getLogger(__file__)

MATCHSUBJECT = opencue_proto.filter_pb2.MatchSubject.keys()
DEFAULT_MATCHSUBJECT = MATCHSUBJECT.index('SHOT')
MATCHTYPE = opencue_proto.filter_pb2.MatchType.keys()
DEFAULT_MATCHTYPE = MATCHTYPE.index('IS')
ACTIONTYPES = opencue_proto.filter_pb2.ActionType.keys()
FILTERTYPES = opencue_proto.filter_pb2.FilterType.keys()
PAUSETYPES = ["Pause", "Unpause"]
MEMOPTTYPES = ["Enabled", "Disabled"]
MAX_RENDER_MEM = 251.0
ALLOWED_ACTION_TYPES = [action_type
                        for action_type in ACTIONTYPES
                        if action_type not in DISABLED_ACTION_TYPES]

class FilterDialog(QtWidgets.QDialog):
    """Dialog to display/modify a show's filters, matchers and actions."""

    def __init__(self, show, parent=None):
        """
        Creates an instance of the FilterDialog.

        Filters are segmented by show, so a show must be provided.

        :type show: opencue.wrappers.show.Show
        :param show: the show to manage filters for
        :type parent: qtpy.QtWidgets.QWidget.QWidget
        :param parent: the parent widget
        """
        QtWidgets.QDialog.__init__(self, parent)
        self.__show = show

        self.__filters = FilterMonitorTree(show, self)
        self.__matchers = MatcherMonitorTree(None, self)
        self.__actions = ActionMonitorTree(show, None, self)
        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddFilter = QtWidgets.QPushButton("Add Filter", self)
        self.__btnAddFilter.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddMultipleMatchers = QtWidgets.QPushButton("Add Multiple Matchers", self)
        self.__btnAddMultipleMatchers.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnReplaceAllMatchers = QtWidgets.QPushButton("Replace All Matchers", self)
        self.__btnReplaceAllMatchers.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDeleteAllMatchers = QtWidgets.QPushButton("Delete All Matchers", self)
        self.__btnDeleteAllMatchers.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddMatcher = QtWidgets.QPushButton("Add Matcher", self)
        self.__btnAddMatcher.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDeleteAllActions = QtWidgets.QPushButton("Delete All Actions", self)
        self.__btnDeleteAllActions.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddAction = QtWidgets.QPushButton("Add Action", self)
        self.__btnAddAction.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDone = QtWidgets.QPushButton("Done", self)
        self.__btnDone.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowTitle("Filters for: %s" % show.name())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(1000, 600)

        glayout = QtWidgets.QGridLayout(self)
        glayout.addWidget(self.__filters, 0, 0, 8, 4)
        glayout.addWidget(self.__matchers, 0, 4, 3, 4)
        glayout.addWidget(self.__actions, 4, 4, 3, 4)
        glayout.addWidget(self.__btnRefresh, 8, 0, 1, 1)
        glayout.addWidget(self.__btnAddFilter, 8, 3, 1, 1)
        glayout.addWidget(self.__btnAddMultipleMatchers, 3, 4, 1, 1)
        glayout.addWidget(self.__btnReplaceAllMatchers, 3, 5, 1, 1)
        glayout.addWidget(self.__btnDeleteAllMatchers, 3, 6, 1, 1)
        glayout.addWidget(self.__btnAddMatcher, 3, 7, 1, 1)
        glayout.addWidget(self.__btnDeleteAllActions, 7, 6, 1, 1)
        glayout.addWidget(self.__btnAddAction, 7, 7, 1, 1)
        glayout.addWidget(self.__btnDone, 8, 7, 1, 1)

        # pylint: disable=no-member
        self.__filters.itemClicked.connect(self.__itemSingleClicked)
        self.__btnRefresh.clicked.connect(self.__refresh)
        self.__btnAddFilter.clicked.connect(self.__createFilter)
        self.__btnAddMultipleMatchers.clicked.connect(self.__matchers.addMultipleMatchers)
        self.__btnReplaceAllMatchers.clicked.connect(self.__matchers.replaceAllMatchers)
        self.__btnDeleteAllMatchers.clicked.connect(self.__matchers.deleteAllMatchers)
        self.__btnAddMatcher.clicked.connect(self.__matchers.createMatcher)
        self.__btnDeleteAllActions.clicked.connect(self.__actions.deleteAllActions)
        self.__btnAddAction.clicked.connect(self.__actions.createAction)
        self.__btnDone.clicked.connect(self.accept)
        # pylint: enable=no-member

    def __createFilter(self):
        """Prompts the user to create a new filter"""
        (value, choice) = QtWidgets.QInputDialog.getText(
            self, "Add filter", "Filter name?", QtWidgets.QLineEdit.Normal, "")
        if choice:
            self.__filters.addObject(self.__show.createFilter(str(value)))

    def __refresh(self):
        """Calls update on the widgets"""
        # pylint: disable=protected-access
        self.__filters._update()
        self.__matchers._update()
        self.__actions._update()

    def __itemSingleClicked(self, item, col):
        del col
        self.__matchers.setObject(item.rpcObject)
        self.__actions.setObject(item.rpcObject)


class FilterMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree displaying a list of filters."""

    def __init__(self, show, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_FILTER)
        self.addColumn("Order", 100, id=1,
                       data=lambda filter:(filter.data.order),
                       sort=lambda filter:(filter.data.order))
        self.addColumn("Enabled", 70, id=2)
        self.addColumn("Filter Name", 270, id=3,
                       data=lambda filter:(filter.data.name))
        self.addColumn("Type", 100, id=4)

        self.__show = show

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.hideColumn(0)
        self.setSortingEnabled(False)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)
        self._timer.stop()

    def _createItem(self, filter_object):
        """Creates and returns a widget item for the given filter."""
        return FilterWidgetItem(filter_object, self)

    def _processUpdate(self, work, rpcObjects):
        """Adds the feature of forcing the items to be sorted by the first
        column"""
        # pylint: disable=protected-access
        cuegui.AbstractTreeWidget.AbstractTreeWidget._processUpdate(self, work, rpcObjects)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return self.__show.getFilters()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.filters().addAction(menu, "raiseOrder")
        self.__menuActions.filters().addAction(menu, "lowerOrder")
        menu.addSeparator()
        self.__menuActions.filters().addAction(menu, "orderFirst")
        self.__menuActions.filters().addAction(menu, "orderLast")
        menu.addSeparator()
        self.__menuActions.filters().addAction(menu, "rename")
        self.__menuActions.filters().addAction(menu, "setOrder")
        menu.addSeparator()
        self.__menuActions.filters().addAction(menu, "delete")

        menu.exec_(e.globalPos())

    def tick(self):
        pass


class MatcherMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree for displaying a list of filter matchers."""

    def __init__(self, parent_filter, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_MATCHER)
        self.addColumn("Matcher Subject", 130, id=1,
                       data=lambda matcher:(matcher.subject()))
        self.addColumn("Type", 130, id=2,
                       data=lambda matcher:(matcher.type()))
        self.addColumn("Input", 130, id=3,
                       data=lambda matcher:(matcher.input()))
        self.addColumn("", 20, id=4)

        self.__filter = parent_filter

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        # pylint: disable=unused-private-member
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)
        self._timer.stop()

    def setObject(self, matcher_object):
        """Sets the Matcher object to monitor
        @type  matcher_object: Matcher
        @param matcher_object: The Matcher object to monitor"""
        self.__filter = matcher_object
        self.sortByColumn(2, QtCore.Qt.AscendingOrder)
        self._update()

    def _createItem(self, matcher_object):
        """Creates and returns a widget item for the given matcher."""
        item = MatcherWidgetItem(matcher_object, self)
        return item

    def _getUpdate(self):
        """Returns the selected filter's matchers."""
        try:
            if self.__filter:
                return self.__filter.getMatchers()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
        return []

    def __getMatcherSubjectDialog(self):
        return QtWidgets.QInputDialog.getItem(
            self, "Create Matcher", "Please select the type of item to match",
            opencue_proto.filter_pb2.MatchSubject.keys(), DEFAULT_MATCHSUBJECT, False)

    def __getMatcherTypeDialog(self):
        return QtWidgets.QInputDialog.getItem(
            self, "Create Matcher", "Please select the type of match to perform",
            opencue_proto.filter_pb2.MatchType.keys(), DEFAULT_MATCHTYPE, False)

    def createMatcher(self):
        """Prompts the user to create a new Matcher"""
        if not self.__filter:
            return

        (matchSubject, choice) = self.__getMatcherSubjectDialog()
        if not choice:
            return

        (matchType, choice) = self.__getMatcherTypeDialog()
        if not choice:
            return

        (matchQuery, choice) = QtWidgets.QInputDialog.getText(
            self,
            "Create Matcher",
            "Please enter the string to match",
            QtWidgets.QLineEdit.Normal,
            "")
        if not choice:
            return

        self.addObject(self.__filter.createMatcher(
            opencue_proto.filter_pb2.MatchSubject.Value(str(matchSubject)),
            opencue_proto.filter_pb2.MatchType.Value(str(matchType)),
            str(matchQuery)))

    def deleteAllMatchers(self):
        """Deletes all matchers."""
        if self.__filter:
            result = QtWidgets.QMessageBox.question(
                self,
                "Delete All Matchers?",
                "Are you sure you want to delete all matchers?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if result == QtWidgets.QMessageBox.Yes:
                self._itemsLock.lockForWrite()
                try:
                    for item in list(self._items.values()):
                        item.rpcObject.delete()
                finally:
                    self._itemsLock.unlock()
                self.removeAllItems()

    def addMultipleMatchers(self):
        """Adds new matchers defined by the user"""
        self.__bulkAddMatchers("Add Multiple Matchers", False)

    def replaceAllMatchers(self):
        """Replaces all of the matchers with new matchers defined by the user"""
        self.__bulkAddMatchers("Replace all Matchers", True)

    def __bulkAddMatchers(self, title, deleteExisting):
        """Adds new matchers defined by the user, with the given dialog title and
        optionally delete existing matchers"""
        if not self.__filter:
            return

        (matchSubject, choice) = self.__getMatcherSubjectDialog()
        if not choice:
            return

        (matchType, choice) = self.__getMatcherTypeDialog()
        if not choice:
            return

        dialog = cuegui.TextEditDialog.TextEditDialog(
            title, "Paste in a list, I will try to clean it up first.", "", self)
        if not dialog.exec_():
            return

        shots = self.__parseShotList(dialog.results())

        if not shots:
            return

        if cuegui.Utils.questionBoxYesNo(
                self, "%s?" % title,
                "Are these correct?\nMatching: \"%s %s\"" % (matchSubject, matchType),
                shots):
            if deleteExisting:
                oldMatchers = self.__filter.getMatchers()
            else:
                oldMatchers = []

            for shot in shots:
                self.__filter.createMatcher(
                    opencue_proto.filter_pb2.MatchSubject.Value(matchSubject),
                    opencue_proto.filter_pb2.MatchType.Value(matchType),
                    shot)
            if deleteExisting:
                for matcher in oldMatchers:
                    matcher.delete()

            self._update()

    @staticmethod
    def __parseShotList(text):
        return [line.split()[0].strip().lower() for line in str(text).splitlines() if line.split()]

    def tick(self):
        pass


class ActionMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree for displaying a list of actions."""

    def __init__(self, show, parent_filter, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_ACTION)
        self.addColumn(
            "Action Type",
            210,
            id=1,
            data=lambda action: (opencue_proto.filter_pb2.ActionType.Name(action.type())))
        self.addColumn("", 180, id=2)
        self.addColumn("", 20, id=3)

        self.__show = show
        self.__filter = parent_filter

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.groupNames = {}
        self.groupIds = {}
        for group in show.getGroups():
            self.groupNames[group.data.name] = group
            self.groupIds[opencue.util.id(group)] = group

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)
        self._timer.stop()

    def setObject(self, action_object):
        """Sets the Action object to monitor
        @type  action_object: Action
        @param action_object: The Action object to monitor"""
        self.__filter = action_object
        self._update()

    def _createItem(self, action_object):
        """Creates and returns the item associated with the given object."""
        return ActionWidgetItem(action_object, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            if self.__filter:
                return self.__filter.getActions()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
        return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu."""
        menu = QtWidgets.QMenu()

        menu.addSeparator()
        self.__menuActions.actions().addAction(menu, "delete")

        menu.exec_(e.globalPos())

    def createAction(self):
        """Prompts the user to create a new action."""
        if self.__filter:
            (actionType, choice) = QtWidgets.QInputDialog.getItem(
                self,
                "Create Action",
                "Please select the type of action to add:",
                ALLOWED_ACTION_TYPES,
                0,
                False)
            if choice:
                value = None
                actionType = getattr(opencue.api.filter_pb2, str(actionType).replace(" ", ""))

                # Give the proper prompt for the desired action type
                if actionType in (opencue.api.filter_pb2.PAUSE_JOB,):
                    (value, choice) = QtWidgets.QInputDialog.getItem(
                        self,
                        "Create Action",
                        "Should the job be paused or unpaused?",
                        PAUSETYPES,
                        0,
                        False)
                    value = PAUSETYPES.index(str(value)) == 0

                elif actionType in (opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                    opencue.api.filter_pb2.SET_JOB_MIN_CORES):
                    (value, choice) = QtWidgets.QInputDialog.getDouble(
                        self,
                        "Create Action",
                        "What value should this property be set to?",
                        0,
                        -8,  # Minimum core value can be <=0, booking all cores minus this value.
                        50000,
                        2)
                    value = float(value)

                elif actionType in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
                    (value, choice) = QtWidgets.QInputDialog.getInt(
                        self,
                        "Create Action",
                        "What value should this property be set to?",
                        0,
                        0,
                        50000,
                        1)

                elif actionType in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY,):
                    (value, choice) = QtWidgets.QInputDialog.getDouble(
                        self,
                        "Create Action",
                        "How much memory (in GB) should each render layer require?",
                        4.0,
                        0.1,
                        MAX_RENDER_MEM,
                        2)
                    value = int(value * 1048576)

                elif actionType in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MIN_CORES,):
                    (value, choice) = QtWidgets.QInputDialog.getDouble(
                        self,
                        "Create Action",
                        "How many min cores should every render layer require?",
                        1,
                        0.1,
                        100,
                        2)
                    value = float(value)

                elif actionType in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MAX_CORES,):
                    (value, choice) = QtWidgets.QInputDialog.getDouble(
                        self,
                        "Create Action",
                        "How many max cores should every render layer require?",
                        1,
                        0.1,
                        100,
                        2)
                    value = float(value)

                elif actionType in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS,):
                    (value, choice) = QtWidgets.QInputDialog.getText(
                        self,
                        "Create Action",
                        "What tags should all render layers be set to?")
                    value = str(value)

                elif actionType in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
                    groups = {}
                    for group in self.__show.getGroups():
                        groups[group.name()] = group
                    (group, choice) = QtWidgets.QInputDialog.getItem(
                        self,
                        "Create Action",
                        "What group should it move to?",
                        list(groups.keys()),
                        0,
                        False)
                    value = groups[str(group)]

                elif actionType in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
                    (value, choice) = QtWidgets.QInputDialog.getItem(
                        self,
                        "Create Action",
                        "Should the memory optimizer be enabled or disabled?",
                        MEMOPTTYPES,
                        0,
                        False)
                    value = MEMOPTTYPES.index(str(value)) == 0

                if choice:
                    self.addObject(self.__filter.createAction(actionType, value))

    def deleteAllActions(self):
        """Prompts the user and then deletes all actions"""
        if self.__filter:
            result = QtWidgets.QMessageBox.question(self,
                                                "Delete All Actions?",
                                                "Are you sure you want to delete all actions?",
                                                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
            if result == QtWidgets.QMessageBox.Yes:
                self._itemsLock.lockForWrite()
                try:
                    for item in list(self._items.values()):
                        item.rpcObject.delete()
                finally:
                    self._itemsLock.unlock()
                self.removeAllItems()

    def tick(self):
        pass


class FilterWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single filter."""

    def __init__(self, filter_object, parent):
        self.__widgets = {}
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_FILTER, filter_object, parent)
        self.updateWidgets()

    def update(self, rpcObject=None, parent=None):
        """Adds a call to updateWidgets()"""
        cuegui.AbstractWidgetItem.AbstractWidgetItem.update(self, rpcObject, parent)
        self.updateWidgets()

    def setType(self, filter_type):
        """Sets the filter's type."""
        self.rpcObject.setType(filter_type)

    def setEnabled(self, value):
        """Enables or disables the filter."""
        self.rpcObject.setEnabled(bool(value))

    def delete(self):
        """Deletes the filter."""
        result = QtWidgets.QMessageBox.question(
            self.treeWidget(),
            "Delete Filter?",
            "Are you sure you want to delete this filter?\n\n%s" % self.rpcObject.name(),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.rpcObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def updateWidgets(self):
        """Refreshes the displayed information."""
        if not self.__widgets:
            combo = QtWidgets.QCheckBox(self.parent())
            combo.setFocusPolicy(QtCore.Qt.NoFocus)
            self.treeWidget().setItemWidget(self, 1, combo)
            combo.stateChanged.connect(self.setEnabled)  # pylint: disable=no-member
            self.__widgets["enabled"] = combo

            combo = NoWheelComboBox(self.parent())
            combo.addItems(FILTERTYPES)
            self.treeWidget().setItemWidget(self, 3, combo)
            combo.currentIndexChanged.connect(self.setType)  # pylint: disable=no-member
            self.__widgets["type"] = combo

        self.__widgets["type"].setCurrentIndex(self.rpcObject.type())
        if self.rpcObject.isEnabled():
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.Unchecked
        self.__widgets["enabled"].setCheckState(state)


class MatcherWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single matcher."""

    def __init__(self, rpcObject, parent):
        self.__widgets = {}
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_MATCHER, rpcObject, parent)
        self.updateWidgets()

    def update(self, rpcObject=None, parent=None):
        """Refreshes the widget display."""
        cuegui.AbstractWidgetItem.AbstractWidgetItem.update(self, rpcObject, parent)
        self.updateWidgets()

    def setType(self, matcherType):
        """Sets the matcher type."""
        self.rpcObject.setType(matcherType)

    def setSubject(self, matcherSubject):
        """Sets the matcher subject."""
        self.rpcObject.setSubject(matcherSubject)

    def setInput(self):
        """Sets the matcher input."""
        text = str(self.__widgets["input"].text())
        if self.rpcObject.input() != text:
            self.rpcObject.setInput(text)

    def delete(self, checked=False):
        """Deletes the matcher."""
        del checked
        result = QtWidgets.QMessageBox.question(
            self.treeWidget(),
            "Delete Matcher?",
            "Are you sure you want to delete this matcher?\n\n%s" % self.rpcObject.name(),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.rpcObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def updateWidgets(self):
        """Refreshes the widget display."""
        if not self.__widgets:
            parent = self.parent()
            treeWidget = self.treeWidget()

            combo = NoWheelComboBox(parent)
            combo.addItems(MATCHSUBJECT)
            treeWidget.setItemWidget(self, 0, combo)
            combo.currentIndexChanged.connect(self.setSubject)  # pylint: disable=no-member
            self.__widgets["subject"] = combo

            combo = NoWheelComboBox(parent)
            combo.addItems(MATCHTYPE)
            treeWidget.setItemWidget(self, 1, combo)
            combo.currentIndexChanged.connect(self.setType)  # pylint: disable=no-member
            self.__widgets["type"] = combo

            edit = QtWidgets.QLineEdit("", parent)
            treeWidget.setItemWidget(self, 2, edit)
            edit.editingFinished.connect(self.setInput)  # pylint: disable=no-member
            self.__widgets["input"] = edit

            btn = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "", parent)
            treeWidget.setItemWidget(self, 3, btn)
            btn.clicked.connect(self.delete)  # pylint: disable=no-member
            self.__widgets["delete"]  = btn

        self.__widgets["subject"].setCurrentIndex(self.rpcObject.subject())
        self.__widgets["type"].setCurrentIndex(self.rpcObject.type())
        # Only update input if user is not currently editing the value
        if not self.__widgets["input"].hasFocus() or \
           not self.__widgets["input"].isModified():
            self.__widgets["input"].setText(self.rpcObject.input())


class ActionWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single action."""

    def __init__(self, action_object, parent):
        self.__widgets = {}
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_ACTION, action_object, parent)
        self.updateWidgets()

    def update(self, rpcObject=None, parent=None):
        """Updates the displayed content."""
        cuegui.AbstractWidgetItem.AbstractWidgetItem.update(self, rpcObject, parent)
        self.updateWidgets()

    def delete(self, checked=False):
        """Deletes an action."""
        del checked
        result = QtWidgets.QMessageBox.question(
            self.treeWidget(),
            "Delete Action?",
            "Are you sure you want to delete this action?\n\n%s" % self.rpcObject.name(),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.rpcObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def __setValue(self, value=None):
        """Sets the action value."""
        widget = self.__widgets["ActionValue"]

        # Get the proper value from the widget
        if self.rpcObject.type() in (opencue.api.filter_pb2.PAUSE_JOB,):
            value = PAUSETYPES.index(str(value)) == 0

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
            value = widget.value()

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY,):
            widget.setMaximum(MAX_RENDER_MEM)
            value = int(widget.value() * 1048576)

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                       opencue.api.filter_pb2.SET_JOB_MIN_CORES,
                                       opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MIN_CORES,
                                       opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MAX_CORES):
            value = float(widget.value())

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS,):
            value = str(widget.text())

        elif self.rpcObject.type() in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
            groupName = list(self.treeWidget().groupNames.keys())[value]
            group = self.treeWidget().groupNames[groupName]
            if self.rpcObject.value() != group.id():
                self.rpcObject.setTypeAndValue(self.rpcObject.type(), group.data)
            return

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
            value = MEMOPTTYPES.index(str(value)) == 0

        # Set the new value
        if self.rpcObject.value() != value:
            self.rpcObject.setTypeAndValue(self.rpcObject.type(), value)

    def updateWidgets(self):
        """Updates the action display."""
        if not self.__widgets:
            widget = None

            # Create the proper widget depending on the action type
            if self.rpcObject.type() in (opencue.api.filter_pb2.PAUSE_JOB,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(PAUSETYPES)
                widget.currentIndexChanged.connect(self.__setValue)  # pylint: disable=no-member

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
                widget = NoWheelSpinBox(self.parent())
                widget.setMaximum(99999)
                widget.editingFinished.connect(self.__setValue)  # pylint: disable=no-member

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY,
                                           opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MIN_CORES,
                                           opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MAX_CORES):
                widget = NoWheelDoubleSpinBox(self.parent())
                widget.setDecimals(2)
                widget.setSingleStep(.10)
                widget.setMaximum(MAX_RENDER_MEM)
                widget.editingFinished.connect(self.__setValue)  # pylint: disable=no-member

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                           opencue.api.filter_pb2.SET_JOB_MIN_CORES):
                widget = NoWheelDoubleSpinBox(self.parent())
                widget.setDecimals(0)
                widget.setSingleStep(1)
                widget.setMaximum(1000)
                widget.editingFinished.connect(self.__setValue)  # pylint: disable=no-member

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS,):
                widget = QtWidgets.QLineEdit("", self.parent())
                widget.editingFinished.connect(self.__setValue)  # pylint: disable=no-member

            elif self.rpcObject.type() in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(list(self.treeWidget().groupNames.keys()))
                widget.currentIndexChanged.connect(self.__setValue)  # pylint: disable=no-member

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(MEMOPTTYPES)
                widget.currentIndexChanged.connect(self.__setValue)  # pylint: disable=no-member

            if widget:
                self.treeWidget().setItemWidget(self, 1, widget)
                self.__widgets["ActionValue"] = widget

            btn = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "", self.parent())
            self.treeWidget().setItemWidget(self, 2, btn)
            btn.clicked.connect(self.delete)  # pylint: disable=no-member
            self.__widgets["delete"] = btn

        # Update the widget with the current value

        if self.rpcObject.type() in (opencue.api.filter_pb2.PAUSE_JOB,):
            self.__widgets["ActionValue"].setCurrentIndex(int(not self.rpcObject.value()))

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
            self.__widgets["ActionValue"].setValue(self.rpcObject.value())

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY,):
            self.__widgets["ActionValue"].setValue(float(self.rpcObject.value()) / 1048576)

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS,):
            self.__widgets["ActionValue"].setText(self.rpcObject.value())

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MIN_CORES,
                                       opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MAX_CORES,
                                       opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                       opencue.api.filter_pb2.SET_JOB_MIN_CORES):
            self.__widgets["ActionValue"].setValue(float(str(self.rpcObject.value())))

        elif self.rpcObject.type() in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
            groupName = self.treeWidget().groupIds[self.rpcObject.value()].name()
            listIndex = list(self.treeWidget().groupNames.keys()).index(groupName)
            self.__widgets["ActionValue"].setCurrentIndex(listIndex)

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
            self.__widgets["ActionValue"].setCurrentIndex(int(not self.rpcObject.value()))

class NoWheelComboBox(QtWidgets.QComboBox):
    """Provides a QComboBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtWidgets.QComboBox.__init__(self, parent)

    def wheelEvent(self, event):
        """Handle wheel scroll event"""
        event.ignore()

class NoWheelDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """Provides a QDoubleSpinBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtWidgets.QDoubleSpinBox.__init__(self, parent)

    def wheelEvent(self, event):
        """Handle wheel scroll event"""
        event.ignore()

class NoWheelSpinBox(QtWidgets.QSpinBox):
    """Provides a QSpinBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtWidgets.QSpinBox.__init__(self, parent)

    def wheelEvent(self, event):
        """Handle wheel scroll event"""
        event.ignore()
