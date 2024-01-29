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


"""Miscellaneous dialogs."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from qtpy import QtWidgets

import cuegui.AbstractDialog


class RunLocalDialog(cuegui.AbstractDialog.AbstractDialog):
    """Dialog for running a job on the user's local desktop cores."""

    def __init__(self, job, parent=None):
        cuegui.AbstractDialog.AbstractDialog.__init__(self, parent)
        layout = QtWidgets.QVBoxLayout(self)

        title = "Use local desktop cores"
        body = "Please enter the number of local desktop cores to provide" \
               " to this job. \nThey will run even if you are using your" \
               " computer!\n(Only one machine per job is currently" \
               " allowed)\n%s" % job.data.name

        self.setWindowTitle(title)
        self.__descriptionLabel = QtWidgets.QLabel(body, self)

        # The number to allow booking
        self.__amountLabel = QtWidgets.QLabel("Number of local cores to use:", self)
        self.__amountSpinBox = QtWidgets.QSpinBox(self)
        self.__amountSpinBox.setRange(0, 16)
        self.__amountSpinBox.setValue(1)

        # The option to only use local cores
        self.__localOnlyLabel = QtWidgets.QLabel("Only use local cores for this job?", self)
        self.__localOnlyCheckBox = QtWidgets.QCheckBox(self)

        self.__buttons = self._newDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        layout.addWidget(self.__descriptionLabel)
        self._addWidgetRow(self.__amountLabel, self.__amountSpinBox)
        self._addWidgetRow(self.__localOnlyLabel, self.__localOnlyCheckBox)

        layout.addWidget(self.__buttons)

    def results(self):
        """Gets the user input results."""
        return self.__amountSpinBox.value(), self.__localOnlyCheckBox.isChecked()
