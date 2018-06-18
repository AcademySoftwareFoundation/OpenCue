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
Handles the dialog to display/modify a show's tasks
"""
from Manifest import os, QtCore, QtGui, Cue3

import re
import Logger
logger = Logger.getLogger(__file__)

import Utils
from MenuActions import MenuActions
from AbstractTreeWidget import *
from AbstractWidgetItem import *


MANAGED_CORES_PREFIX = "Minimum Cores: "
class TasksDialog(QtGui.QDialog):
    def __init__(self, show, parent = None):
        QtGui.QDialog.__init__(self, parent)

        self.__show = show

        self.__comboDepartments = QtGui.QComboBox(self)
        self.__tasks = TaskMonitorTree(None, self)
        self.__btnMinCores = QtGui.QPushButton(MANAGED_CORES_PREFIX, self)
        self.__btnMinCores.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__checkManaged = QtGui.QCheckBox("Managed", self)
        self.__checkManaged.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddTask = QtGui.QPushButton("Add Task", self)
        self.__btnAddTask.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnRefresh = QtGui.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDone = QtGui.QPushButton("Done", self)
        self.__btnDone.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowTitle("Tasks for: %s" % show.name())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(500, 600)

        glayout = QtGui.QGridLayout(self)
        glayout.addWidget(self.__comboDepartments, 0, 0)
        glayout.addWidget(self.__checkManaged, 0, 1)
        glayout.addWidget(self.__btnMinCores, 0, 2)
        glayout.addWidget(self.__tasks, 1, 0, 3, 3)
        glayout.addWidget(self.__btnAddTask, 4, 0)
        glayout.addWidget(self.__btnRefresh, 4, 1)
        glayout.addWidget(self.__btnDone, 4, 2)

        QtCore.QObject.connect(self.__btnMinCores,
                               QtCore.SIGNAL("clicked()"),
                               self.setMinCores)

        QtCore.QObject.connect(self.__checkManaged,
                               QtCore.SIGNAL("clicked(bool)"),
                               self.setManaged)

        QtCore.QObject.connect(self.__btnAddTask,
                               QtCore.SIGNAL("clicked()"),
                               self.__tasks.createTask)

        QtCore.QObject.connect(self.__btnRefresh,
                               QtCore.SIGNAL("clicked()"),
                               self.refresh)

        QtCore.QObject.connect(self.__comboDepartments,
                               QtCore.SIGNAL("currentIndexChanged(QString)"),
                               self.setDepartment)

        QtCore.QObject.connect(self.__btnDone, QtCore.SIGNAL("clicked()"), self.accept)

        self.getDepartments()

    def getDepartments(self):
        selected = self.__comboDepartments.currentText()

        self.__departments = self.__show.proxy.getDepartments()
        departmentNames = sorted([dept.data.name for dept in self.__departments])
        self.__comboDepartments.clear()
        self.__comboDepartments.addItems(departmentNames)
        if selected:
            self.__comboDepartments.setCurrentIndex(departmentNames.index(selected))

    def setDepartment(self, departmentName):
        for department in self.__departments:
            if department.data.name == departmentName:
                self.__tasks.setDepartment(department)
                self.__btnAddTask.setEnabled(not department.data.tiManaged)
                self.__checkManaged.setChecked(department.data.tiManaged)
                self.__btnMinCores.setText(MANAGED_CORES_PREFIX  + "%.02f" % department.data.minCores)
                return

    def setMinCores(self):
        __department = self.__tasks.department()
        if __department:
            (managedCores, choice) = self.__askManagedCores(__department)
            if choice:
                __department.proxy.setManagedCores(managedCores)
                self.__btnMinCores.setText(MANAGED_CORES_PREFIX + "%.02f" % managedCores)
                self.getDepartments()

    def setManaged(self, checked):
        __department = self.__tasks.department()
        if not __department.data.tiManaged and checked:
            title = "Manage Department"
            body = "What tiTask should be used to manage the %s department?" % __department.data.name
            (tiTask, choice) = QtGui.QInputDialog.getText(self,
                                                          title, body,
                                                          QtGui.QLineEdit.Normal,
                                                          __department.data.tiTask)
            if choice:
                (managedCores, choice) = self.__askManagedCores(__department)
                if choice:
                    __department.proxy.enableTiManaged(str(tiTask), managedCores)

        if __department.data.tiManaged and not checked:
            if Utils.questionBoxYesNo(self,
                                      "Confirm",
                                      "Disable management of the %s department?" % __department.data.name):
                __department.proxy.disableTiManaged()

        self.getDepartments()

    def __askManagedCores(self, department):
        title = "Set Managed Cores"
        body = "Please enter the new managed cores value:"
        (managedCores, choice) = QtGui.QInputDialog.getDouble(self,
                                                              title, body,
                                                              department.data.minCores,
                                                              0, 50000, 0)
        return (managedCores, choice)

    def refresh(self):
        self.__tasks.updateRequest()

class TaskMonitorTree(AbstractTreeWidget):
    def __init__(self, department, parent):
        self.startColumnsForType(Constants.TYPE_TASK)
        self.addColumn("Shot", 100, id=1,
                       data=lambda task:(task.data.shot))
        self.addColumn("Department", 100, id=2,
                       data=lambda task:(task.data.dept))
        self.addColumn("Minimum Cores", 100, id=3,
                       data=lambda task:(task.data.minCores))
        self.addColumn("Adjust Cores", 100, id=4,
                       data=lambda task:(task.data.adjustCores))

        AbstractTreeWidget.__init__(self, parent)

        self.setSortingEnabled(False)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)
        self._timer.stop()
        self.setDepartment(department)

    def department(self):
        return self.__department

    def setDepartment(self, department):
        self.__department = department
        self._update()

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return TaskWidgetItem(object, self)

    def _update(self):
        """Adds the feature of forcing the items to be sorted by the first
        column"""
        AbstractTreeWidget._update(self)
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            if self.__department:
                return self.__department.proxy.getTasks()
            else:
                return []
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        if not self.__department:
            return

        __managed = self.__department.data.tiManaged

        menu = QtGui.QMenu()
        self.__menuActions.tasks().addAction(menu, "setMinCores")
        self.__menuActions.tasks().addAction(menu, "clearAdjustment")
        if not __managed:
            menu.addSeparator()
            self.__menuActions.tasks().addAction(menu, "delete")
        menu.exec_(e.globalPos())

    def createTask(self):
        if self.__department:
            title = "Create Task"
            body = "What shot is this task for? "
            (shot, choice) = QtGui.QInputDialog.getText(self, title, body,
                                                        QtGui.QLineEdit.Normal, "")
            if choice:
                title = "Set Minimum Cores"
                body = "Please enter the new minimum cores value:"
                (minCores, choice) = QtGui.QInputDialog.getDouble(self,
                                                                  title, body,
                                                                  1,
                                                                  0, 50000, 0)
                if choice:
                    self.__department.proxy.addTask(str(shot), float(minCores))
                    self._update()

class TaskWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        AbstractWidgetItem.__init__(self, Constants.TYPE_TASK, object, parent)
