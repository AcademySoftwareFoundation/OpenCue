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


"""A dialog displaying show configuration options."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Utils


class ShowDialog(QtWidgets.QDialog):
    """A dialog displaying show configuration options."""

    def __init__(self, show, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle("%s Properties" % show.name())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(500, 400)

        self.__show = show

        self.__btnSave = QtWidgets.QPushButton("Save", self)
        self.__btnSave.setEnabled(False)
        self.__btnClose = QtWidgets.QPushButton("Close", self)

        self.__tabWidget = QtWidgets.QTabWidget(self)
        self.__tabWidget.addTab(self.__createSettingsPage(), "Settings")
        self.__tabWidget.addTab(self.__createBookingPage(), "Booking")
        self.__tabWidget.addTab(self.__createStatisticsPage(), "Statistics")
        self.__tabWidget.addTab(self.__createRawShowDataPage(), "Raw Show Data")

        QtWidgets.QGridLayout(self)
        self.layout().addWidget(self.__tabWidget, 0, 0, 4, 3)
        self.layout().addWidget(self.__btnSave, 5, 1)
        self.layout().addWidget(self.__btnClose, 5, 2)

        # pylint: disable=no-member
        self.__btnSave.clicked.connect(self.__saveChanges)
        self.__btnClose.clicked.connect(self.__closeDialog)
        # pylint: enable=no-member

    def __createSettingsPage(self):
        """Settings Page"""
        page = QtWidgets.QWidget()
        page.setLayout(QtWidgets.QGridLayout())
        page.layout().setRowStretch(10, 100)

        label = QtWidgets.QLabel("Default maximum cores", self)
        ctrl = QtWidgets.QDoubleSpinBox(self)
        ctrl.setRange(0, 10000)
        ctrl.setDecimals(2)
        ctrl.setValue(self.__show.data.default_max_cores)
        page.layout().addWidget(ctrl, 0, 0)
        page.layout().addWidget(label, 0, 1, 1, 4)
        ctrl.valueChanged.connect(self.__valueChanged)  # pylint: disable=no-member
        self.__defaultMaxCores = ctrl

        label = QtWidgets.QLabel("Default minimum cores", self)
        ctrl = QtWidgets.QDoubleSpinBox(self)
        ctrl.setRange(0, 10000)
        ctrl.setDecimals(2)
        ctrl.setValue(self.__show.data.default_min_cores)
        page.layout().addWidget(ctrl, 1, 0)
        page.layout().addWidget(label, 1, 1, 1, 4)
        ctrl.valueChanged.connect(self.__valueChanged)  # pylint: disable=no-member
        self.__defaultMinCores = ctrl

        label = QtWidgets.QLabel("Comment Notification Email", self)
        text = QtWidgets.QLineEdit(self)
        text.setText(self.__show.data.comment_email)
        page.layout().addWidget(text, 2, 0)
        page.layout().addWidget(label, 2, 1, 1, 4)
        text.textChanged.connect(self.__valueChanged)  # pylint: disable=no-member
        self.__show_email = text
        return page

    def __createBookingPage(self):
        """Booking Page"""
        page = QtWidgets.QWidget()
        page.setLayout(QtWidgets.QGridLayout())
        page.layout().setRowStretch(10, 100)

        label = QtWidgets.QLabel("Enable booking", self)
        ctrl = QtWidgets.QCheckBox(self)
        ctrl.setChecked(self.__show.data.booking_enabled)
        page.layout().addWidget(ctrl, 0, 0)
        page.layout().addWidget(label, 0, 1, 1, 4)
        ctrl.stateChanged.connect(self.__valueChanged)  # pylint: disable=no-member
        self.__bookingEnabled = ctrl

        label = QtWidgets.QLabel("Enable dispatch", self)
        ctrl = QtWidgets.QCheckBox(self)
        ctrl.setChecked(self.__show.data.dispatch_enabled)
        page.layout().addWidget(ctrl, 1, 0)
        page.layout().addWidget(label, 1, 1, 1, 4)
        ctrl.stateChanged.connect(self.__valueChanged)  # pylint: disable=no-member
        self.__dispatchEnabled = ctrl

        return page

    def __createStatisticsPage(self):
        """Statistics Page"""
        page = QtWidgets.QWidget()
        page.setLayout(QtWidgets.QGridLayout())
        text = QtWidgets.QTextEdit(page)
        text.setReadOnly(True)
        text.setPlainText("%s" % self.__show.data.show_stats)
        page.layout().addWidget(text)

        return page

    def __createRawShowDataPage(self):
        """Raw Show Data Page"""
        page = QtWidgets.QWidget()
        page.setLayout(QtWidgets.QVBoxLayout())
        text = QtWidgets.QTextEdit(page)
        text.setReadOnly(True)
        text.setPlainText("Show: %s%s\n%s\n%s" % (self.__show.name(),
                                                  self.__show.data,
                                                  self.__show.data.show_stats,
                                                  self.__show.id()))
        page.layout().addWidget(text)

        return page

    def __valueChanged(self, value=None):
        """Called when something changes to enable the save button"""
        del value
        self.__btnSave.setEnabled(True)

    def __closeDialog(self):
        """Prompts to allow the user to save changes before exit"""
        if self.__btnSave.isEnabled():
            if cuegui.Utils.questionBoxYesNo(self, "Save Changes?",
                                      "Do you want to save your changes?"):
                self.__saveChanges()
        self.accept()

    def __saveChanges(self):
        """If the save button is enabled, any changed values will be saved"""
        self.__btnSave.setEnabled(False)

        if self.__show.data.comment_email != str(self.__show_email.text()):
            self.__show.setCommentEmail(str(self.__show_email.text()))

        if self.__show.data.default_max_cores != self.__defaultMaxCores.value():
            self.__show.setDefaultMaxCores(self.__defaultMaxCores.value())

        if self.__show.data.default_min_cores != self.__defaultMinCores.value():
            self.__show.setDefaultMinCores(self.__defaultMinCores.value())

        if self.__show.data.booking_enabled != self.__bookingEnabled.isChecked():
            self.__show.enableBooking(self.__bookingEnabled.isChecked())

        if self.__show.data.dispatch_enabled != self.__dispatchEnabled.isChecked():
            self.__show.enableDispatching(self.__dispatchEnabled.isChecked())
