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
Handles the dialog to display/modify a show's filters, matchers and actions
"""
from __future__ import absolute_import


from builtins import map
from builtins import str
import re

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue
from . import Logger
from . import Constants
from . import Utils
from .MenuActions import MenuActions
from .AbstractTreeWidget import AbstractTreeWidget
from .AbstractWidgetItem import AbstractWidgetItem
from .TextEditDialog import TextEditDialog
from opencue.compiled_proto.filter_pb2 import ActionType
from opencue.compiled_proto.filter_pb2 import FilterType
from opencue.compiled_proto.filter_pb2 import MatchSubject
from opencue.compiled_proto.filter_pb2 import MatchType


logger = Logger.getLogger(__file__)


MATCHSUBJECT = [match for match in dir(MatchSubject)
                if type(getattr(MatchSubject, match)) == MatchSubject]
DEFAULT_MATCHSUBJECT = MATCHSUBJECT.index("Shot")
MATCHTYPE = [match for match in dir(MatchType) if type(getattr(MatchType, match)) == MatchType]
DEFAULT_MATCHTYPE = MATCHTYPE.index("Is")
ACTIONTYPE = [action for action in dir(ActionType)
              if type(getattr(ActionType, action)) == ActionType]
FILTERTYPE = [filter_ for filter_ in dir(FilterType)
              if type(getattr(FilterType, filter_)) == FilterType]
PAUSETYPE = ["Pause", "Unpause"]
MEMOPTTYPE = ["Enabled", "Disabled"]


class FilterDialog(QtWidgets.QDialog):
    def __init__(self, show, parent=None):
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

    def __createFilter(self):
        """Prompts the user to create a new filter"""
        (value, choice) = QtWidgets.QInputDialog.getText(self, "Add filter", "Filter name?",
                                                     QtWidgets.QLineEdit.Normal, "")
        if choice:
            self.__filters.addObject(self.__show.createFilter(str(value)))

    def __refresh(self):
        """Calls update on the widgets"""
        self.__filters._update()
        self.__matchers._update()
        self.__actions._update()

    def __itemSingleClicked(self, item, col):
        filter = item.rpcObject
        self.__matchers.setObject(filter)
        self.__actions.setObject(filter)

class FilterMonitorTree(AbstractTreeWidget):
    def __init__(self, show, parent):
        self.startColumnsForType(Constants.TYPE_FILTER)
        self.addColumn("Order", 100, id=1,
                       data=lambda filter:(filter.data.order),
                       sort=lambda filter:(filter.data.order))
        self.addColumn("Enabled", 70, id=2)
        self.addColumn("Filter Name", 270, id=3,
                       data=lambda filter:(filter.data.name))
        self.addColumn("Type", 100, id=4)

        self.__show = show

        AbstractTreeWidget.__init__(self, parent)

        self.hideColumn(0)
        self.setSortingEnabled(False)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)
        self._timer.stop()

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return FilterWidgetItem(object, self)

    def _update(self):
        """Adds the feature of forcing the items to be sorted by the first
        column"""
        AbstractTreeWidget._update(self)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return self.__show.getFilters()
        except Exception as e:
            list(map(logger.warning, Utils.exceptionOutput(e)))
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

class MatcherMonitorTree(AbstractTreeWidget):
    def __init__(self, filter, parent):
        self.startColumnsForType(Constants.TYPE_MATCHER)
        self.addColumn("Matcher Subject", 130, id=1,
                       data=lambda matcher:(matcher.subject()))
        self.addColumn("Type", 130, id=2,
                       data=lambda matcher:(matcher.type()))
        self.addColumn("Input", 130, id=3,
                       data=lambda matcher:(matcher.input()))
        self.addColumn("", 20, id=4)

        self.__filter = filter

        AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)
        self._timer.stop()

    def setObject(self, object):
        """Sets the Matcher object to monitor
        @type  object: Matcher
        @param object: The Matcher object to monitor"""
        self.__filter = object
        self.sortByColumn(2, QtCore.Qt.AscendingOrder)
        self._update()

    def _createItem(self, object):
        """Creates and returns the proper item"""
        item = MatcherWidgetItem(object, self)

        return item

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            if self.__filter:
                return self.__filter.getMatchers()
        except Exception as e:
            list(map(logger.warning, Utils.exceptionOutput(e)))
        return []

    def __getMatcherSubjectDialog(self):
        return QtWidgets.QInputDialog.getItem(self, "Create Matcher",
                                          "Please select the type of item to match",
                                          MATCHSUBJECT, DEFAULT_MATCHSUBJECT, False)

    def __getMatcherTypeDialog(self):
        return QtWidgets.QInputDialog.getItem(self, "Create Matcher",
                                          "Please select the type of match to perform",
                                          MATCHTYPE, DEFAULT_MATCHTYPE, False)

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

        (input, choice) = QtWidgets.QInputDialog.getText(self, "Create Matcher",
                                                     "Please enter the string to match",
                                                     QtWidgets.QLineEdit.Normal, "")
        if not choice:
            return

        self.addObject(self.__filter.createMatcher(
            getattr(opencue.api.filter_pb2, str(matchSubject)),
            getattr(opencue.api.filter_pb2, str(matchType)),
            str(input)))

    def deleteAllMatchers(self):
        """Prompts the user and then deletes all matchers"""
        if self.__filter:
            result = QtWidgets.QMessageBox.question(self,
                                                "Delete All Matchers?",
                                                "Are you sure you want to delete all matchers?",
                                                QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
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

        dialog = TextEditDialog(title,
                                "Paste in a list, I will try to clean it up first.",
                                "", self)
        if not dialog.exec_():
            return

        shots = self.__parseShotList(dialog.results().toAscii())

        if not shots:
            return

        if Utils.questionBoxYesNo(self, "%s?" % title,
                                  "Are these correct?\nMatching: \"%s %s\"" % (matchSubject, matchType),
                                  shots):
            if deleteExisting:
                oldMatchers = self.__filter.getMatchers()
            else:
                oldMatchers = []

            for shot in shots:
                self.__filter.createMatcher(getattr(MatchSubject, str(matchSubject)),
                                            getattr(MatchType, str(matchType)),
                                            shot)
            if deleteExisting:
                for matcher in oldMatchers:
                    matcher.delete()

            self._update()

    def __parseShotList(self, text):
        return [line.split()[0].strip().lower() for line in str(text).splitlines() if line.split()]

class ActionMonitorTree(AbstractTreeWidget):
    def __init__(self, show, filter, parent):
        self.startColumnsForType(Constants.TYPE_ACTION)
        self.addColumn("Action Type", 210, id=1,
                       data=lambda action:(addSpaces(str(action.type()))))
        self.addColumn("", 180, id=2)
        self.addColumn("", 20, id=3)

        self.__show = show
        self.__filter = filter

        AbstractTreeWidget.__init__(self, parent)

        self.groupNames = {}
        self.groupIds = {}
        for group in show.getGroups():
            self.groupNames[group.data.name] = group
            self.groupIds[opencue.util.id(group)] = group

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)
        self._timer.stop()

    def setObject(self, object):
        """Sets the Action object to monitor
        @type  object: Action
        @param object: The Action object to monitor"""
        self.__filter = object
        self._update()

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return ActionWidgetItem(object, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            if self.__filter:
                return self.__filter.getActions()
        except Exception as e:
            list(map(logger.warning, Utils.exceptionOutput(e)))
        return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()

        menu.addSeparator()
        self.__menuActions.actions().addAction(menu, "delete")

        menu.exec_(e.globalPos())

    def createAction(self):
        """Prompts the user to create a new action"""
        if self.__filter:
            (actionType, choice) = QtWidgets.QInputDialog.getItem(
                self, "Create Action", "Please select the type of action to add:",
                [addSpaces(action) for action in ACTIONTYPE], 0, False)
            if choice:
                value = None
                actionType = getattr(opencue.api.filter_pb2, str(actionType).replace(" ", ""))

                # Give the proper prompt for the desired action type
                if actionType in (opencue.api.filter_pb2.PAUSE_JOB,):
                    (value, choice) = QtWidgets.QInputDialog.getItem(
                        self,
                        "Create Action",
                        "Should the job be paused or unpaused?",
                        PAUSETYPE,
                        0,
                        False)
                    value = PAUSETYPE.index(str(value)) == 0

                elif actionType in (opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                    opencue.api.filter_pb2.SET_JOB_MIN_CORES):
                    (value, choice) = QtWidgets.QInputDialog.getDouble(
                        self,
                        "Create Action",
                        "What value should this property be set to?",
                        0,
                        0,
                        50000,
                        2)
                    value = float(value)

                elif actionType in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
                    (value, choice) = QtWidgets.QInputDialog.getInteger(
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
                        47.0,
                        2)
                    value = int(value * 1048576)

                elif actionType in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_CORES,):
                    (value, choice) = QtWidgets.QInputDialog.getDouble(
                        self,
                        "Create Action",
                        "How many cores should every render layer require?",
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
                        MEMOPTTYPE,
                        0,
                        False)
                    value = MEMOPTTYPE.index(str(value)) == 0

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

################################################################################

class FilterWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        self.__widgets = {}
        AbstractWidgetItem.__init__(self, Constants.TYPE_FILTER, object, parent)
        self.updateWidgets()

    def update(self, object = None, parent = None):
        """Adds a call to updateWidgets()"""
        AbstractWidgetItem.update(self, object, parent)
        self.updateWidgets()

    def setType(self, text):
        self.rpcObject.setType(getattr(opencue.api.filter_pb2, str(text)))

    def setEnabled(self, value):
        self.rpcObject.setEnabled(bool(value))

    def delete(self):
        result = QtWidgets.QMessageBox.question(self.treeWidget(),
                                           "Delete Filter?",
                                           "Are you sure you want to delete this filter?\n\n%s" %
                                                self.rpcObject.name(),
                                           QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.rpcObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def updateWidgets(self):
        if not self.__widgets:
            combo = QtWidgets.QCheckBox(self.parent())
            combo.setFocusPolicy(QtCore.Qt.NoFocus)
            self.treeWidget().setItemWidget(self, 1, combo)
            combo.stateChanged.connect(self.setEnabled)
            self.__widgets["enabled"] = combo

            combo = NoWheelComboBox(self.parent())
            combo.addItems(FILTERTYPE)
            self.treeWidget().setItemWidget(self, 3, combo)
            combo.currentIndexChanged.connect(self.setType)
            self.__widgets["type"] = combo

        self.__widgets["type"].setCurrentIndex(FILTERTYPE.index(str(self.rpcObject.type())))
        if self.rpcObject.isEnabled():
            state = QtCore.Qt.Checked
        else:
            state = QtCore.Qt.Unchecked
        self.__widgets["enabled"].setCheckState(state)

class MatcherWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        self.__widgets = {}
        AbstractWidgetItem.__init__(self, Constants.TYPE_MATCHER, object, parent)
        self.updateWidgets()

    def update(self, object = None, parent = None):
        """Adds a call to updateWidgets()"""
        AbstractWidgetItem.update(self, object, parent)
        self.updateWidgets()

    def setType(self, text):
        self.rpcObject.setType(getattr(opencue.api.filter_pb2, str(text)))

    def setSubject(self, text):
        self.rpcObject.setSubject(getattr(opencue.api.filter_pb2, str(text)))

    def setInput(self):
        text = str(self.__widgets["input"].text())
        if self.rpcObject.input() != text:
            self.rpcObject.setInput(text)

    def delete(self, checked = False):
        result = QtWidgets.QMessageBox.question(self.treeWidget(),
                                           "Delete Matcher?",
                                           "Are you sure you want to delete this matcher?\n\n%s" %
                                                self.rpcObject.name(),
                                           QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.rpcObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def updateWidgets(self):
        if not self.__widgets:
            parent = self.parent()
            treeWidget = self.treeWidget()

            combo = NoWheelComboBox(parent)
            combo.addItems(MATCHSUBJECT)
            treeWidget.setItemWidget(self, 0, combo)
            combo.currentIndexChanged.connect(self.setSubject)
            self.__widgets["subject"] = combo

            combo = NoWheelComboBox(parent)
            combo.addItems(MATCHTYPE)
            treeWidget.setItemWidget(self, 1, combo)
            combo.currentIndexChanged.connect(self.setType)
            self.__widgets["type"] = combo

            edit = QtWidgets.QLineEdit("", parent)
            treeWidget.setItemWidget(self, 2, edit)
            edit.editingFinished.connect(self.setInput)
            self.__widgets["input"] = edit

            btn = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "", parent)
            treeWidget.setItemWidget(self, 3, btn)
            btn.clicked.connect(self.delete)
            self.__widgets["delete"]  = btn

        self.__widgets["subject"].setCurrentIndex(MATCHSUBJECT.index(str(self.rpcObject.subject())))
        self.__widgets["type"].setCurrentIndex(MATCHTYPE.index(str(self.rpcObject.type())))
        # Only update input if user is not currently editing the value
        if not self.__widgets["input"].hasFocus() or \
           not self.__widgets["input"].isModified():
            self.__widgets["input"].setText(self.rpcObject.input())

class ActionWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        self.__widgets = {}
        AbstractWidgetItem.__init__(self, Constants.TYPE_ACTION, object, parent)
        self.updateWidgets()

    def update(self, object = None, parent = None):
        """Adds a call to updateWidgets()"""
        AbstractWidgetItem.update(self, object, parent)
        self.updateWidgets()

    def delete(self, checked = False):
        result = QtWidgets.QMessageBox.question(self.treeWidget(),
                                           "Delete Action?",
                                           "Are you sure you want to delete this action?\n\n%s" %
                                                self.rpcObject.name(),
                                           QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        if result == QtWidgets.QMessageBox.Yes:
            self.rpcObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def __setValue(self, value = None):
        """Sets the value from the widget"""
        widget = self.__widgets["ActionValue"]

        # Get the proper value from the widget
        if self.rpcObject.type() in (opencue.api.filter_pb2.PAUSE_JOB,):
            value = PAUSETYPE.index(str(value)) == 0

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
            value = widget.value()

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY,):
            value = int(widget.value() * 1048576)

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                       opencue.api.filter_pb2.SET_JOB_MIN_CORES,
                                       opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_CORES):
            value = float(widget.value())

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS,):
            value = str(widget.text())

        elif self.rpcObject.type() in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
            group = self.treeWidget().groupNames[str(value)]
            if self.rpcObject.value() != group:
                self.rpcObject.setTypeAndValue(self.rpcObject.type(), group)
            return

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
            value = MEMOPTTYPE.index(str(value)) == 0

        # Set the new value
        if self.rpcObject.value() != value:
            self.rpcObject.setTypeAndValue(self.rpcObject.type(), value)

    def updateWidgets(self):
        if not self.__widgets:
            widget = None

            # Create the proper widget depending on the action type
            if self.rpcObject.type() in (opencue.api.filter_pb2.PAUSE_JOB,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(PAUSETYPE)
                widget.currentIndexChanged.connect(self.__setValue)

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_PRIORITY,):
                widget = NoWheelSpinBox(self.parent())
                widget.setMaximum(99999)
                widget.editingFinished.connect(self.__setValue)

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_MEMORY,
                                           opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_CORES):
                widget = NoWheelDoubleSpinBox(self.parent())
                widget.setDecimals(2)
                widget.setSingleStep(.10)
                widget.editingFinished.connect(self.__setValue)

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                           opencue.api.filter_pb2.SET_JOB_MIN_CORES):
                widget = NoWheelDoubleSpinBox(self.parent())
                widget.setDecimals(0)
                widget.setSingleStep(1)
                widget.setMaximum(1000)
                widget.editingFinished.connect(self.__setValue)

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_TAGS,):
                widget = QtWidgets.QLineEdit("", self.parent())
                widget.editingFinished.connect(self.__setValue)

            elif self.rpcObject.type() in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(list(self.treeWidget().groupNames.keys()))
                widget.currentIndexChanged.connect(self.__setValue)

            elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(MEMOPTTYPE)
                widget.currentIndexChanged.connect(self.__setValue)

            if widget:
                self.treeWidget().setItemWidget(self, 1, widget)
                self.__widgets["ActionValue"] = widget

            btn = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "", self.parent())
            self.treeWidget().setItemWidget(self, 2, btn)
            btn.clicked.connect(self.delete)
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

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_ALL_RENDER_LAYER_CORES,
                                       opencue.api.filter_pb2.SET_JOB_MAX_CORES,
                                       opencue.api.filter_pb2.SET_JOB_MIN_CORES):
            self.__widgets["ActionValue"].setValue(float(str(self.rpcObject.value())))

        elif self.rpcObject.type() in (opencue.api.filter_pb2.MOVE_JOB_TO_GROUP,):
            name = self.treeWidget().groupIds[self.rpcObject.value()].name()
            index = list(self.treeWidget().groupNames.keys()).index(name)
            self.__widgets["ActionValue"].setCurrentIndex(index)

        elif self.rpcObject.type() in (opencue.api.filter_pb2.SET_MEMORY_OPTIMIZER,):
            self.__widgets["ActionValue"].setCurrentIndex(int(not self.rpcObject.value()))

class NoWheelComboBox(QtWidgets.QComboBox):
    """Provides a QComboBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtWidgets.QComboBox.__init__(self, parent)

    def wheelEvent(self, event):
        event.ignore()

class NoWheelDoubleSpinBox(QtWidgets.QDoubleSpinBox):
    """Provides a QDoubleSpinBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtWidgets.QDoubleSpinBox.__init__(self, parent)

    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(QtWidgets.QSpinBox):
    """Provides a QSpinBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtWidgets.QSpinBox.__init__(self, parent)

    def wheelEvent(self, event):
        event.ignore()

def addSpaces(value):
    return re.sub(r'([a-z]*)([A-Z])',r'\1 \2', value).strip()
