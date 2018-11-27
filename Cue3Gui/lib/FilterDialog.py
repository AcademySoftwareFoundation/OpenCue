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
from Manifest import os, QtCore, QtGui, Cue3

import re
import Logger
logger = Logger.getLogger(__file__)

import Utils
from MenuActions import MenuActions
from AbstractTreeWidget import *
from AbstractWidgetItem import *
from TextEditDialog import TextEditDialog
from Cue3.compiled_proto.filter_pb2 import ActionType
from Cue3.compiled_proto.filter_pb2 import FilterType
from Cue3.compiled_proto.filter_pb2 import MatchSubject
from Cue3.compiled_proto.filter_pb2 import MatchType


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


class FilterDialog(QtGui.QDialog):
    def __init__(self, show, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.__show = show

        self.__filters = FilterMonitorTree(show, self)
        self.__matchers = MatcherMonitorTree(None, self)
        self.__actions = ActionMonitorTree(show, None, self)
        self.__btnRefresh = QtGui.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddFilter = QtGui.QPushButton("Add Filter", self)
        self.__btnAddFilter.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddMultipleMatchers = QtGui.QPushButton("Add Multiple Matchers", self)
        self.__btnAddMultipleMatchers.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnReplaceAllMatchers = QtGui.QPushButton("Replace All Matchers", self)
        self.__btnReplaceAllMatchers.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDeleteAllMatchers = QtGui.QPushButton("Delete All Matchers", self)
        self.__btnDeleteAllMatchers.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddMatcher = QtGui.QPushButton("Add Matcher", self)
        self.__btnAddMatcher.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDeleteAllActions = QtGui.QPushButton("Delete All Actions", self)
        self.__btnDeleteAllActions.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddAction = QtGui.QPushButton("Add Action", self)
        self.__btnAddAction.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDone = QtGui.QPushButton("Done", self)
        self.__btnDone.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowTitle("Filters for: %s" % show.name())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(1000, 600)

        glayout = QtGui.QGridLayout(self)
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

        QtCore.QObject.connect(self.__filters,
                               QtCore.SIGNAL('itemClicked(QTreeWidgetItem*,int)'),
                               self.__itemSingleClicked)
        QtCore.QObject.connect(self.__btnRefresh, QtCore.SIGNAL("clicked()"), self.__refresh)
        QtCore.QObject.connect(self.__btnAddFilter, QtCore.SIGNAL("clicked()"), self.__createFilter)
        QtCore.QObject.connect(self.__btnAddMultipleMatchers, QtCore.SIGNAL("clicked()"),
                               self.__matchers.addMultipleMatchers)
        QtCore.QObject.connect(self.__btnReplaceAllMatchers, QtCore.SIGNAL("clicked()"),
                               self.__matchers.replaceAllMatchers)
        QtCore.QObject.connect(self.__btnDeleteAllMatchers, QtCore.SIGNAL("clicked()"),
                               self.__matchers.deleteAllMatchers)
        QtCore.QObject.connect(self.__btnAddMatcher, QtCore.SIGNAL("clicked()"),
                               self.__matchers.createMatcher)
        QtCore.QObject.connect(self.__btnDeleteAllActions, QtCore.SIGNAL("clicked()"),
                               self.__actions.deleteAllActions)
        QtCore.QObject.connect(self.__btnAddAction, QtCore.SIGNAL("clicked()"),
                               self.__actions.createAction)
        QtCore.QObject.connect(self.__btnDone, QtCore.SIGNAL("clicked()"), self.accept)

    def __createFilter(self):
        """Prompts the user to create a new filter"""
        (value, choice) = QtGui.QInputDialog.getText(self, "Add filter", "Filter name?",
                                                     QtGui.QLineEdit.Normal, "")
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
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtGui.QMenu()
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
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
        return []

    def __getMatcherSubjectDialog(self):
        return QtGui.QInputDialog.getItem(self, "Create Matcher",
                                          "Please select the type of item to match",
                                          MATCHSUBJECT, DEFAULT_MATCHSUBJECT, False)

    def __getMatcherTypeDialog(self):
        return QtGui.QInputDialog.getItem(self, "Create Matcher",
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

        (input, choice) = QtGui.QInputDialog.getText(self, "Create Matcher",
                                                     "Please enter the string to match",
                                                     QtGui.QLineEdit.Normal, "")
        if not choice:
            return

        self.addObject(self.__filter.createMatcher(getattr(Cue3.MatchSubject, str(matchSubject)), getattr(Cue3.MatchType, str(matchType)), str(input)))

    def deleteAllMatchers(self):
        """Prompts the user and then deletes all matchers"""
        if self.__filter:
            result = QtGui.QMessageBox.question(self,
                                                "Delete All Matchers?",
                                                "Are you sure you want to delete all matchers?",
                                                QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
            if result == QtGui.QMessageBox.Yes:
                self._itemsLock.lockForWrite()
                try:
                    for item in self._items.values():
                        item.iceObject.delete()
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
            self.groupIds[Cue3.util.id(group)] = group

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
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
        return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtGui.QMenu()

        menu.addSeparator()
        self.__menuActions.actions().addAction(menu, "delete")

        menu.exec_(e.globalPos())

    def createAction(self):
        """Prompts the user to create a new action"""
        if self.__filter:
            (actionType, choice) = QtGui.QInputDialog.getItem(self, "Create Action", "Please select the type of action to add:", [addSpaces(action) for action in ACTIONTYPE], 0, False)
            if choice:
                value = None
                actionType = getattr(Cue3.ActionType, str(actionType).replace(" ", ""))

                # Give the proper prompt for the desired action type
                if actionType in (Cue3.ActionType.PauseJob,):
                    (value, choice) = QtGui.QInputDialog.getItem(self, "Create Action", "Should the job be paused or unpaused?", PAUSETYPE, 0, False)
                    value = PAUSETYPE.index(str(value)) == 0

                elif actionType in (Cue3.ActionType.SetJobMaxCores,
                                    Cue3.ActionType.SetJobMinCores):
                    (value, choice) = QtGui.QInputDialog.getDouble(self, "Create Action","What value should this property be set to?", 0, 0, 50000, 2)
                    value = float(value)

                elif actionType in (Cue3.ActionType.SetJobPriority,):
                    (value, choice) = QtGui.QInputDialog.getInteger(self, "Create Action","What value should this property be set to?", 0, 0, 50000, 1)

                elif actionType in (Cue3.ActionType.SetAllRenderLayerMemory,):
                    (value, choice) = QtGui.QInputDialog.getDouble(self, "Create Action", "How much memory (in GB) should each render layer require?", 4.0, 0.1, 47.0, 2)
                    value = int(value * 1048576)

                elif actionType in (Cue3.ActionType.SetAllRenderLayerCores,):
                    (value, choice) = QtGui.QInputDialog.getDouble(self, "Create Action", "How many cores should every render layer require?", 1, .1, 100, 2)
                    value = float(value)

                elif actionType in (Cue3.ActionType.SetAllRenderLayerTags,):
                    (value, choice) = QtGui.QInputDialog.getText(self, "Create Action", "What tags should all render layers be set to?")
                    value = str(value)

                elif actionType in (Cue3.ActionType.MoveJobToGroup,):
                    groups = {}
                    for group in self.__show.getGroups():
                        groups[group.name()] = group
                    (group, choice) = QtGui.QInputDialog.getItem(self, "Create Action", "What group should it move to?", groups.keys(), 0, False)
                    value = groups[str(group)]

                elif actionType in (Cue3.ActionType.SetMemoryOptimizer,):
                    (value, choice) = QtGui.QInputDialog.getItem(self, "Create Action", "Should the memory optimizer be enabled or disabled?", MEMOPTTYPE, 0, False)
                    value = MEMOPTTYPE.index(str(value)) == 0

                if choice:
                    self.addObject(self.__filter.createAction(actionType, value))

    def deleteAllActions(self):
        """Prompts the user and then deletes all actions"""
        if self.__filter:
            result = QtGui.QMessageBox.question(self,
                                                "Delete All Actions?",
                                                "Are you sure you want to delete all actions?",
                                                QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
            if result == QtGui.QMessageBox.Yes:
                self._itemsLock.lockForWrite()
                try:
                    for item in self._items.values():
                        item.iceObject.delete()
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
        self.iceObject.setType(getattr(Cue3.FilterType, str(text)))

    def setEnabled(self, value):
        self.iceObject.setEnabled(bool(value))

    def delete(self):
        result = QtGui.QMessageBox.question(self.treeWidget(),
                                           "Delete Filter?",
                                           "Are you sure you want to delete this filter?\n\n%s" % self.iceObject.name(),
                                           QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if result == QtGui.QMessageBox.Yes:
            self.iceObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def updateWidgets(self):
        if not self.__widgets:
            combo = QtGui.QCheckBox(self.parent())
            combo.setFocusPolicy(QtCore.Qt.NoFocus)
            self.treeWidget().setItemWidget(self, 1, combo)
            QtCore.QObject.connect(combo, QtCore.SIGNAL("stateChanged(int)"), self.setEnabled)
            self.__widgets["enabled"] = combo

            combo = NoWheelComboBox(self.parent())
            combo.addItems(FILTERTYPE)
            self.treeWidget().setItemWidget(self, 3, combo)
            QtCore.QObject.connect(combo, QtCore.SIGNAL("currentIndexChanged(QString)"), self.setType)
            self.__widgets["type"] = combo

        self.__widgets["type"].setCurrentIndex(FILTERTYPE.index(str(self.iceObject.type())))
        if self.iceObject.isEnabled():
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
        self.iceObject.setType(getattr(Cue3.MatchType, str(text)))

    def setSubject(self, text):
        self.iceObject.setSubject(getattr(Cue3.MatchSubject, str(text)))

    def setInput(self):
        text = str(self.__widgets["input"].text())
        if self.iceObject.input() != text:
            self.iceObject.setInput(text)

    def delete(self, checked = False):
        result = QtGui.QMessageBox.question(self.treeWidget(),
                                           "Delete Matcher?",
                                           "Are you sure you want to delete this matcher?\n\n%s" % self.iceObject.name(),
                                           QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if result == QtGui.QMessageBox.Yes:
            self.iceObject.delete()
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
            QtCore.QObject.connect(combo, QtCore.SIGNAL("currentIndexChanged(QString)"), self.setSubject)
            self.__widgets["subject"] = combo

            combo = NoWheelComboBox(parent)
            combo.addItems(MATCHTYPE)
            treeWidget.setItemWidget(self, 1, combo)
            QtCore.QObject.connect(combo, QtCore.SIGNAL("currentIndexChanged(QString)"), self.setType)
            self.__widgets["type"] = combo

            edit = QtGui.QLineEdit("", parent)
            treeWidget.setItemWidget(self, 2, edit)
            QtCore.QObject.connect(edit, QtCore.SIGNAL("editingFinished()"), self.setInput)
            self.__widgets["input"] = edit

            btn = QtGui.QPushButton(QtGui.QIcon(":kill.png"), "", parent)
            treeWidget.setItemWidget(self, 3, btn)
            QtCore.QObject.connect(btn, QtCore.SIGNAL("clicked(bool)"), self.delete)
            self.__widgets["delete"]  = btn

        self.__widgets["subject"].setCurrentIndex(MATCHSUBJECT.index(str(self.iceObject.subject())))
        self.__widgets["type"].setCurrentIndex(MATCHTYPE.index(str(self.iceObject.type())))
        # Only update input if user is not currently editing the value
        if not self.__widgets["input"].hasFocus() or \
           not self.__widgets["input"].isModified():
            self.__widgets["input"].setText(self.iceObject.input())

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
        result = QtGui.QMessageBox.question(self.treeWidget(),
                                           "Delete Action?",
                                           "Are you sure you want to delete this action?\n\n%s" % self.iceObject.name(),
                                           QtGui.QMessageBox.Yes|QtGui.QMessageBox.No)
        if result == QtGui.QMessageBox.Yes:
            self.iceObject.delete()
            QtCore.QTimer.singleShot(0, self.__delete)

    def __delete(self):
        self.treeWidget().removeItem(self)

    def __setValue(self, value = None):
        """Sets the value from the widget"""
        widget = self.__widgets["ActionValue"]

        # Get the proper value from the widget
        if self.iceObject.type() in (Cue3.ActionType.PauseJob,):
            value = PAUSETYPE.index(str(value)) == 0

        elif self.iceObject.type() in (Cue3.ActionType.SetJobPriority,):
            value = widget.value()

        elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerMemory,):
            value = int(widget.value() * 1048576)

        elif self.iceObject.type() in (Cue3.ActionType.SetJobMaxCores,
                                     Cue3.ActionType.SetJobMinCores,
                                     Cue3.ActionType.SetAllRenderLayerCores):
            value = float(widget.value())

        elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerTags,):
            value = str(widget.text())

        elif self.iceObject.type() in (Cue3.ActionType.MoveJobToGroup,):
            group = self.treeWidget().groupNames[str(value)]
            if self.iceObject.value() != group.proxy:
                self.iceObject.setTypeAndValue(self.iceObject.type(), group)
            return

        elif self.iceObject.type() in (Cue3.ActionType.SetMemoryOptimizer,):
            value = MEMOPTTYPE.index(str(value)) == 0

        # Set the new value
        if self.iceObject.value() != value:
            self.iceObject.setTypeAndValue(self.iceObject.type(), value)

    def updateWidgets(self):
        if not self.__widgets:
            widget = None

            # Create the proper widget depending on the action type
            if self.iceObject.type() in (Cue3.ActionType.PauseJob,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(PAUSETYPE)
                QtCore.QObject.connect(widget, QtCore.SIGNAL("currentIndexChanged(QString)"), self.__setValue)

            elif self.iceObject.type() in (Cue3.ActionType.SetJobPriority,):
                widget = NoWheelSpinBox(self.parent())
                widget.setMaximum(99999)
                QtCore.QObject.connect(widget, QtCore.SIGNAL("editingFinished()"), self.__setValue)

            elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerMemory,
                                         Cue3.ActionType.SetAllRenderLayerCores):
                widget = NoWheelDoubleSpinBox(self.parent())
                widget.setDecimals(2)
                widget.setSingleStep(.10)
                QtCore.QObject.connect(widget, QtCore.SIGNAL("editingFinished()"), self.__setValue)

            elif self.iceObject.type() in (Cue3.ActionType.SetJobMaxCores,
                                         Cue3.ActionType.SetJobMinCores):
                widget = NoWheelDoubleSpinBox(self.parent())
                widget.setDecimals(0)
                widget.setSingleStep(1)
                widget.setMaximum(1000)
                QtCore.QObject.connect(widget, QtCore.SIGNAL("editingFinished()"), self.__setValue)

            elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerTags,):
                widget = QtGui.QLineEdit("", self.parent())
                QtCore.QObject.connect(widget, QtCore.SIGNAL("editingFinished()"), self.__setValue)

            elif self.iceObject.type() in (Cue3.ActionType.MoveJobToGroup,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(self.treeWidget().groupNames.keys())
                QtCore.QObject.connect(widget, QtCore.SIGNAL("currentIndexChanged(QString)"), self.__setValue)

            elif self.iceObject.type() in (Cue3.ActionType.SetMemoryOptimizer,):
                widget = NoWheelComboBox(self.parent())
                widget.addItems(MEMOPTTYPE)
                QtCore.QObject.connect(widget, QtCore.SIGNAL("currentIndexChanged(QString)"), self.__setValue)

            if widget:
                self.treeWidget().setItemWidget(self, 1, widget)
                self.__widgets["ActionValue"] = widget

            btn = QtGui.QPushButton(QtGui.QIcon(":kill.png"), "", self.parent())
            self.treeWidget().setItemWidget(self, 2, btn)
            QtCore.QObject.connect(btn, QtCore.SIGNAL("clicked(bool)"), self.delete)
            self.__widgets["delete"]  = btn

        # Update the widget with the current value

        if self.iceObject.type() in (Cue3.ActionType.PauseJob,):
            self.__widgets["ActionValue"].setCurrentIndex(int(not self.iceObject.value()))

        elif self.iceObject.type() in (Cue3.ActionType.SetJobPriority,):
            self.__widgets["ActionValue"].setValue(self.iceObject.value())

        elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerMemory,):
            self.__widgets["ActionValue"].setValue(float(self.iceObject.value()) / 1048576)

        elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerTags,):
            self.__widgets["ActionValue"].setText(self.iceObject.value())

        elif self.iceObject.type() in (Cue3.ActionType.SetAllRenderLayerCores,
                                     Cue3.ActionType.SetJobMaxCores,
                                     Cue3.ActionType.SetJobMinCores):
            self.__widgets["ActionValue"].setValue(float(str(self.iceObject.value())))

        elif self.iceObject.type() in (Cue3.ActionType.MoveJobToGroup,):
            name = self.treeWidget().groupIds[self.iceObject.value()].name()
            index = self.treeWidget().groupNames.keys().index(name)
            self.__widgets["ActionValue"].setCurrentIndex(index)

        elif self.iceObject.type() in (Cue3.ActionType.SetMemoryOptimizer,):
            self.__widgets["ActionValue"].setCurrentIndex(int(not self.iceObject.value()))

class NoWheelComboBox(QtGui.QComboBox):
    """Provides a QComboBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtGui.QComboBox.__init__(self, parent)

    def wheelEvent(self, event):
        event.ignore()

class NoWheelDoubleSpinBox(QtGui.QDoubleSpinBox):
    """Provides a QDoubleSpinBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtGui.QDoubleSpinBox.__init__(self, parent)

    def wheelEvent(self, event):
        event.ignore()

class NoWheelSpinBox(QtGui.QSpinBox):
    """Provides a QSpinBox that does not respond to the mouse wheel to avoid
    accidental changes"""
    def __init__(self, parent):
        QtGui.QSpinBox.__init__(self, parent)

    def wheelEvent(self, event):
        event.ignore()

def addSpaces(value):
    return re.sub(r'([a-z]*)([A-Z])',r'\1 \2', value).strip()
