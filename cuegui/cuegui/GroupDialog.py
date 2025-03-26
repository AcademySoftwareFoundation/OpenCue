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


"""Dialog for creating or modifying a group."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str

from qtpy import QtCore
from qtpy import QtWidgets

import opencue


class GroupDialog(QtWidgets.QDialog):
    """Base class for group dialogs."""

    def __init__(self, parentGroup, modifyGroup, defaults, parent):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QGridLayout(self)

        self._parentGroup = parentGroup
        self._modifyGroup = modifyGroup
        __modify = modifyGroup is not None

        self._departments = opencue.api.getDepartmentNames()
        try:
            self._departments = opencue.api.getDepartmentNames()
        except opencue.exception.CueException:
            self._departments = ["Unknown"]

        __title = defaults["title"]
        __message = defaults["message"]
        __name = defaults["name"]
        __department = defaults["department"]
        __defaultJobPriority = defaults["defaultJobPriority"]
        __defaultJobMinCores = defaults["defaultJobMinCores"]
        __defaultJobMaxCores = defaults["defaultJobMaxCores"]
        __minCores = defaults["minCores"]
        __maxCores = defaults["maxCores"]

        __defaultJobMinGpus = defaults["defaultJobMinGpus"]
        __defaultJobMaxGpus = defaults["defaultJobMaxGpus"]
        __minGpus = defaults["minGpus"]
        __maxGpus = defaults["maxGpus"]

        self.setWindowTitle(__title)
        layout.addWidget(QtWidgets.QLabel(__message, self), 0, 1, 1, 3)

        layout.addWidget(QtWidgets.QLabel("Group Name:", self), 1, 1)
        self._nameValue = QtWidgets.QLineEdit(__name, self)
        layout.addWidget(self._nameValue, 1, 2)

        layout.addWidget(QtWidgets.QLabel("Department:", self), 2, 1)
        self._departmentValue = QtWidgets.QComboBox(self)
        self._departmentValue.addItems(self._departments)
        self._departmentValue.setCurrentIndex(self._departments.index(__department))
        layout.addWidget(self._departmentValue, 2, 2)

        (self._defaultJobPriorityCheck, self._defaultJobPriorityValue) = \
            self.__createToggleSpinBox("Job Default Priority", 3,
                                       __modify and __defaultJobPriority != -1,
                                       __defaultJobPriority)
        (self._defaultJobMinCoresCheck, self._defaultJobMinCoresValue) = \
            self.__createToggleDoubleSpinBox("Job Default Minimum Cores", 4,
                                             __modify and __defaultJobMinCores != -1.0,
                                             __defaultJobMinCores, 1)
        (self._defaultJobMaxCoresCheck, self._defaultJobMaxCoresValue) = \
            self.__createToggleDoubleSpinBox("Job Default Maximum Cores", 5,
                                             __modify and __defaultJobMaxCores != -1.0,
                                             __defaultJobMaxCores, 1)
        (self._minCoresCheck, self._minCoresValue) = \
            self.__createToggleDoubleSpinBox("Group Minimum Cores", 6,
                                             __modify and __minCores != 0.0,
                                             __minCores)
        (self._maxCoresCheck, self._maxCoresValue) = \
            self.__createToggleDoubleSpinBox("Group Maximum Cores", 7,
                                             __modify and __maxCores != -1.0,
                                             __maxCores, 1)

        (self._defaultJobMinGpusCheck, self._defaultJobMinGpusValue) = \
            self.__createToggleSpinBox("Job Default Minimum Gpus", 8,
                                             __modify and __defaultJobMinGpus != -1,
                                             __defaultJobMinGpus, 1)
        (self._defaultJobMaxGpusCheck, self._defaultJobMaxGpusValue) = \
            self.__createToggleSpinBox("Job Default Maximum Gpus", 9,
                                             __modify and __defaultJobMaxGpus != -1,
                                             __defaultJobMaxGpus, 1)
        (self._minGpusCheck, self._minGpusValue) = \
            self.__createToggleSpinBox("Group Minimum Gpus", 10,
                                             __modify and __minGpus != 0,
                                             __minGpus)
        (self._maxGpusCheck, self._maxGpusValue) = \
            self.__createToggleSpinBox("Group Maximum Gpus", 11,
                                             __modify and __maxGpus != -1,
                                             __maxGpus, 1)

        self.__createButtons(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel, 12, 3)

    def __createToggleDoubleSpinBox(
            self, text, row, startEnabled = False, currentValue = 0, minValue = 0):
        inputWidget = QtWidgets.QDoubleSpinBox(self)
        inputWidget.setEnabled(startEnabled)
        inputWidget.setRange(minValue, 30000)
        inputWidget.setDecimals(2)
        inputWidget.setValue(currentValue)
        return self.__createToggleInput(text, row, inputWidget, startEnabled)

    def __createToggleSpinBox(
            self, text, row, startEnabled = False, currentValue = 0, minValue = 0):
        inputWidget = QtWidgets.QSpinBox(self)
        inputWidget.setEnabled(startEnabled)
        inputWidget.setRange(minValue, 30000)
        inputWidget.setValue(currentValue)
        return self.__createToggleInput(text, row, inputWidget, startEnabled)

    def __createToggleInput(self, text, row, inputWidget, startEnabled):
        label = QtWidgets.QLabel(text, self)
        label.setEnabled(startEnabled)
        check = QtWidgets.QCheckBox(self)
        check.setChecked(startEnabled)
        self.layout().addWidget(check, row, 0)
        self.layout().addWidget(label, row, 1)
        self.layout().addWidget(inputWidget, row, 2)
        # pylint: disable=no-member
        check.stateChanged.connect(inputWidget.setEnabled)
        check.stateChanged.connect(label.setEnabled)
        # pylint: enable=no-member
        return (check, inputWidget)

    def __createButtons(self, buttons, row, width):
        self.__buttons = QtWidgets.QDialogButtonBox(buttons, QtCore.Qt.Horizontal, self)
        self.layout().addWidget(self.__buttons, row, 1, 1, width)
        # pylint: disable=no-member
        self.__buttons.accepted.connect(self.accept)
        self.__buttons.rejected.connect(self.reject)
        # pylint: enable=no-member

    def accept(self):
        """Accept action"""
        __name = str(self._nameValue.text())
        if not __name:
            return
        __modifyGroup = self._modifyGroup

        if __modifyGroup:
            __group = __modifyGroup
            __group.setName(__name)
        else:
            __group = self._parentGroup.createSubGroup(__name)

        __department = str(self._departmentValue.currentText())
        if not __modifyGroup or __modifyGroup.data.department != __department:
            __group.setDepartment(__department)

        self.__setValue(self._defaultJobPriorityCheck,
                        __group.setDefaultJobPriority,
                        int(self._defaultJobPriorityValue.value()),
                        __group.data.default_job_priority, -1)

        self.__setValue(self._defaultJobMinCoresCheck,
                        __group.setDefaultJobMinCores,
                        float(self._defaultJobMinCoresValue.value()),
                        __group.data.default_job_min_cores, float(-1))

        self.__setValue(self._defaultJobMaxCoresCheck,
                        __group.setDefaultJobMaxCores,
                        float(self._defaultJobMaxCoresValue.value()),
                        __group.data.default_job_max_cores, float(-1))

        self.__setValue(self._minCoresCheck,
                        __group.setMinCores,
                        float(self._minCoresValue.value()),
                        __group.data.min_cores, float(0.0))

        self.__setValue(self._maxCoresCheck,
                        __group.setMaxCores,
                        float(self._maxCoresValue.value()),
                        __group.data.max_cores, float(-1))

        self.__setValue(self._defaultJobMinGpusCheck,
                        __group.setDefaultJobMinGpus,
                        float(self._defaultJobMinGpusValue.value()),
                        __group.data.default_job_min_gpus, -1)

        self.__setValue(self._defaultJobMaxGpusCheck,
                        __group.setDefaultJobMaxGpus,
                        float(self._defaultJobMaxGpusValue.value()),
                        __group.data.default_job_max_gpus, -1)

        self.__setValue(self._minGpusCheck,
                        __group.setMinGpus,
                        float(self._minGpusValue.value()),
                        __group.data.min_gpus, 0)

        self.__setValue(self._maxGpusCheck,
                        __group.setMaxGpus,
                        float(self._maxGpusValue.value()),
                        __group.data.max_gpus, -1)

        self.close()

    @staticmethod
    def __setValue(checkBox, setter, newValue, currentValue, disableValue):
        if checkBox.isChecked():
            result = newValue
        else:
            result = disableValue
        if result is not None and result != currentValue:
            setter(result)


class ModifyGroupDialog(GroupDialog):
    """Dialog for modifying an existing group."""

    def __init__(self, modifyGroup, parent=None):
        modifyGroup = opencue.api.getGroup(modifyGroup.id())
        defaults = {
            "title": "Modify Group: %s" % modifyGroup.data.name,
            "message": "Modifying the group %s" % modifyGroup.data.name,
            "name": modifyGroup.data.name,
            "department": modifyGroup.data.department,
            "defaultJobPriority": modifyGroup.data.default_job_priority,
            "defaultJobMinCores": modifyGroup.data.default_job_min_cores,
            "defaultJobMaxCores": modifyGroup.data.default_job_max_cores,
            "minCores": modifyGroup.data.min_cores,
            "maxCores": modifyGroup.data.max_cores,
            "defaultJobMinGpus": modifyGroup.data.default_job_min_gpus,
            "defaultJobMaxGpus": modifyGroup.data.default_job_max_gpus,
            "minGpus": modifyGroup.data.min_gpus,
            "maxGpus": modifyGroup.data.max_gpus}
        GroupDialog.__init__(self, None, modifyGroup, defaults, parent)


class NewGroupDialog(GroupDialog):
    """Dialog for creating a new group."""

    def __init__(self, parentGroup, parent=None):
        defaults = {
            "title": "Create New Group",
            "message": "Group to be created as a child of the group %s" % parentGroup.name(),
            "name": "",
            "department": "Unknown",
            "defaultJobPriority": 0,
            "defaultJobMinCores": 1.0,
            "defaultJobMaxCores": 1.0,
            "minCores": 0.0,
            "maxCores": 1.0,
            "defaultJobMinGpus": 0,
            "defaultJobMaxGpus": 0,
            "minGpus": 0,
            "maxGpus": 0}
        GroupDialog.__init__(self, parentGroup, None, defaults, parent)
