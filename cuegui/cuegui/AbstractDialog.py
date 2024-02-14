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


"""Base class for dialog windows."""


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from builtins import str

from qtpy import QtCore
from qtpy import QtWidgets


class AbstractDialog(QtWidgets.QDialog):
    """Base class for dialog windows."""

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

    @staticmethod
    def _newCheckBoxSelectionMatrix(title, allowedOptions, checkedOptions, parent=None):
        return CheckBoxSelectionMatrix(title, allowedOptions, checkedOptions, parent)

    def _newDialogButtonBox(self, buttons, orientation=QtCore.Qt.Horizontal):
        buttonBox = QtWidgets.QDialogButtonBox(buttons, orientation, self)
        # pylint: disable=no-member
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        # pylint: enable=no-member
        return buttonBox

    def _addWidgetRow(self, *widgets):
        __hlayout = QtWidgets.QHBoxLayout()
        for widget in widgets:
            __hlayout.addWidget(widget)
        self.layout().addLayout(__hlayout)


class CheckBoxSelectionMatrix(QtWidgets.QWidget):
    """Widget for displaying a matrix of checkboxes."""

    def __init__(self, title, allowedOptions, checkedOptions, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.__group = QtWidgets.QGroupBox(title, self)
        self.__group_layout = QtWidgets.QGridLayout()

        self.__checkBoxes = []
        for index, item in enumerate(allowedOptions):
            box = QtWidgets.QCheckBox(item, self.__group)
            box.setChecked(item in checkedOptions)
            self.__checkBoxes.append(box)
            self.__group_layout.addWidget(box, index // 2, index % 2)

        self.__group.setLayout(self.__group_layout)
        layout.addWidget(self.__group)
        layout.setContentsMargins(0,0,0,0)
        layout.addStretch()

    def checkedBoxes(self):
        """Gets all checked boxes."""
        return [cb for cb in self.__checkBoxes if cb.isChecked()]

    def checkedOptions(self):
        """Gets text value of all checked boxes."""
        return [str(cb.text()) for cb in self.__checkBoxes if cb.isChecked()]

    def checkBoxes(self, names):
        """Sets checked state for checkboxes representing the named values."""
        for box in self.__checkBoxes:
            box.setChecked(str(box.text()) in names)
