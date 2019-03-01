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


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from builtins import str

from PySide2 import QtCore
from PySide2 import QtWidgets


class AbstractDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

    def _newCheckBoxSelectionMatrix(self,
                                    title,
                                    allowedOptions,
                                    checkedOptions,
                                    parent=None):
        return CheckBoxSelectionMatrix(title,
                                       allowedOptions,
                                       checkedOptions,
                                       parent)

    def _newDialogButtonBox(self, buttons, orientation=QtCore.Qt.Horizontal):
        buttonBox = QtWidgets.QDialogButtonBox(buttons, orientation, self)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        return buttonBox

    def _addWidgetRow(self, *widgets):
        __hlayout = QtWidgets.QHBoxLayout()
        for widget in widgets:
            __hlayout.addWidget(widget)
        self.layout().addLayout(__hlayout)


class CheckBoxSelectionMatrix(QtWidgets.QWidget):
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
        return [cb for cb in self.__checkBoxes if cb.isChecked()]

    def checkedOptions(self):
        return [str(cb.text()) for cb in self.__checkBoxes if cb.isChecked()]

    def checkBoxes(self, names):
        for box in self.__checkBoxes:
            box.setChecked(str(box.text()) in names)
