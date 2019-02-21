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
from __future__ import absolute_import


from builtins import map
from builtins import str
from PySide2 import QtCore
from PySide2 import QtWidgets

from .AbstractTreeWidget import AbstractTreeWidget
from .AbstractWidgetItem import AbstractWidgetItem
from . import Constants
from . import Logger
from .MenuActions import MenuActions
from . import Utils


logger = Logger.getLogger(__file__)

MANAGED_CORES_PREFIX = "Minimum Cores: "


class TasksDialog(QtWidgets.QDialog):
    def __init__(self, show, parent = None):
        QtWidgets.QDialog.__init__(self, parent)

        self.__show = show

        self.__comboDepartments = QtWidgets.QComboBox(self)
        self.__tasks = TaskMonitorTree(None, self)
        self.__btnMinCores = QtWidgets.QPushButton(MANAGED_CORES_PREFIX, self)
        self.__btnMinCores.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__checkManaged = QtWidgets.QCheckBox("Managed", self)
        self.__checkManaged.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddTask = QtWidgets.QPushButton("Add Task", self)
        self.__btnAddTask.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnDone = QtWidgets.QPushButton("Done", self)
        self.__btnDone.setFocusPolicy(QtCore.Qt.NoFocus)

        self.setWindowTitle("Tasks for: %s" % show.name())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(500, 600)

        glayout = QtWidgets.QGridLayout(self)
        glayout.addWidget(self.__comboDepartments, 0, 0)
        glayout.addWidget(self.__checkManaged, 0, 1)
        glayout.addWidget(self.__btnMinCores, 0, 2)
        glayout.addWidget(self.__tasks, 1, 0, 3, 3)
        glayout.addWidget(self.__btnAddTask, 4, 0)
        glayout.addWidget(self.__btnRefresh, 4, 1)
        glayout.addWidget(self.__btnDone, 4, 2)

        self.__btnMinCores.clicked.connect(self.setMinCores)
        self.__checkManaged.clicked.connect(self.setManaged)
        self.__btnAddTask.clicked.connect(self.__tasks.createTask)
        self.__btnRefresh.clicked.connect(self.refresh)
        self.__comboDepartments.currentIndexChanged.connect(self.setDepartment)
        self.__btnDone.clicked.connect(self.accept)

        self.getDepartments()

    def getDepartments(self):
        selected = self.__comboDepartments.currentText()

        self.__departments = self.__show.getDepartments()
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
                __department.setManagedCores(managedCores)
                self.__btnMinCores.setText(MANAGED_CORES_PREFIX + "%.02f" % managedCores)
                self.getDepartments()

    def setManaged(self, checked):
        __department = self.__tasks.department()
        if not __department.data.tiManaged and checked:
            title = "Manage Department"
            body = "What tiTask should be used to manage the %s department?" % __department.data.name
            (tiTask, choice) = QtWidgets.QInputDialog.getText(self,
                                                          title, body,
                                                          QtWidgets.QLineEdit.Normal,
                                                          __department.data.tiTask)
            if choice:
                (managedCores, choice) = self.__askManagedCores(__department)
                if choice:
                    __department.enableTiManaged(str(tiTask), managedCores)

        if __department.data.tiManaged and not checked:
            if Utils.questionBoxYesNo(self,
                                      "Confirm",
                                      "Disable management of the %s department?" % __department.data.name):
                __department.disableTiManaged()

        self.getDepartments()

    def __askManagedCores(self, department):
        title = "Set Managed Cores"
        body = "Please enter the new managed cores value:"
        (managedCores, choice) = QtWidgets.QInputDialog.getDouble(self,
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
                return self.__department.getTasks()
            else:
                return []
        except Exception as e:
            list(map(logger.warning, Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        if not self.__department:
            return

        __managed = self.__department.data.tiManaged

        menu = QtWidgets.QMenu()
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
            (shot, choice) = QtWidgets.QInputDialog.getText(self, title, body,
                                                        QtWidgets.QLineEdit.Normal, "")
            if choice:
                title = "Set Minimum Cores"
                body = "Please enter the new minimum cores value:"
                (minCores, choice) = QtWidgets.QInputDialog.getDouble(self,
                                                                  title, body,
                                                                  1,
                                                                  0, 50000, 0)
                if choice:
                    self.__department.addTask(str(shot), float(minCores))
                    self._update()

class TaskWidgetItem(AbstractWidgetItem):
    def __init__(self, object, parent):
        AbstractWidgetItem.__init__(self, Constants.TYPE_TASK, object, parent)
