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
Displays the show dialog with show configuration options
"""
from Manifest import os, QtCore, QtGui, Cue3

import Utils

from AbstractTreeWidget import *
from AbstractWidgetItem import *

class ShowDialog(QtGui.QDialog):
    def __init__(self, show, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle("%s Properties" % show.name())
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.resize(500, 400)

        self.__show = show

        self.__btnSave = QtGui.QPushButton("Save", self)
        self.__btnSave.setEnabled(False)
        self.__btnClose = QtGui.QPushButton("Close", self)

        self.__tabWidget = QtGui.QTabWidget(self)
        self.__tabWidget.addTab(self.__createSettingsPage(), "Settings")
        self.__tabWidget.addTab(self.__createBookingPage(), "Booking")
        self.__tabWidget.addTab(self.__createStatisticsPage(), "Statistics")
        self.__tabWidget.addTab(self.__createRawShowDataPage(), "Raw Show Data")

        QtGui.QGridLayout(self)
        self.layout().addWidget(self.__tabWidget, 0, 0, 4, 3)
        self.layout().addWidget(self.__btnSave, 5, 1)
        self.layout().addWidget(self.__btnClose, 5, 2)

        QtCore.QObject.connect(self.__btnSave,
                               QtCore.SIGNAL("clicked()"),
                               self.__saveChanges)

        QtCore.QObject.connect(self.__btnClose,
                               QtCore.SIGNAL("clicked()"),
                               self.__closeDialog)

    def __createSettingsPage(self):
        """Settings Page"""
        page = QtGui.QWidget()
        page.setLayout(QtGui.QGridLayout())
        page.layout().setRowStretch(10, 100)

        label = QtGui.QLabel("Default maximum cores", self)
        ctrl = QtGui.QDoubleSpinBox(self)
        ctrl.setRange(0, 10000)
        ctrl.setDecimals(2)
        ctrl.setValue(self.__show.data.defaultMaxCores)
        page.layout().addWidget(ctrl, 0, 0)
        page.layout().addWidget(label, 0, 1, 1, 4)
        QtCore.QObject.connect(ctrl, QtCore.SIGNAL("valueChanged(double)"),
                               self.__valueChanged)
        self.__defaultMaxCores = ctrl

        label = QtGui.QLabel("Default minimum cores", self)
        ctrl = QtGui.QDoubleSpinBox(self)
        ctrl.setRange(0, 10000)
        ctrl.setDecimals(2)
        ctrl.setValue(self.__show.data.defaultMinCores)
        page.layout().addWidget(ctrl, 1, 0)
        page.layout().addWidget(label, 1, 1, 1, 4)
        QtCore.QObject.connect(ctrl, QtCore.SIGNAL("valueChanged(double)"),
                               self.__valueChanged)
        self.__defaultMinCores = ctrl

        label = QtGui.QLabel("Comment Notification Email", self)
        text = QtGui.QLineEdit(self)
        text.setText(self.__show.data.commentEmail)
        page.layout().addWidget(text, 2, 0)
        page.layout().addWidget(label, 2, 1, 1, 4)
        QtCore.QObject.connect(text, QtCore.SIGNAL("textChanged(QString)"),
                               self.__valueChanged)
        self.__show_email = text
        return page

    def __createBookingPage(self):
        """Booking Page"""
        page = QtGui.QWidget()
        page.setLayout(QtGui.QGridLayout())
        page.layout().setRowStretch(10, 100)

        label = QtGui.QLabel("Enable booking", self)
        ctrl = QtGui.QCheckBox(self)
        ctrl.setChecked(self.__show.data.bookingEnabled)
        page.layout().addWidget(ctrl, 0, 0)
        page.layout().addWidget(label, 0, 1, 1, 4)
        QtCore.QObject.connect(ctrl, QtCore.SIGNAL("stateChanged(int)"),
                               self.__valueChanged)
        self.__bookingEnabled = ctrl

        label = QtGui.QLabel("Enable dispatch", self)
        ctrl = QtGui.QCheckBox(self)
        ctrl.setChecked(self.__show.data.bookingEnabled)
        page.layout().addWidget(ctrl, 1, 0)
        page.layout().addWidget(label, 1, 1, 1, 4)
        QtCore.QObject.connect(ctrl, QtCore.SIGNAL("stateChanged(int)"),
                               self.__valueChanged)
        self.__dispatchEnabled = ctrl

        return page

    def __createStatisticsPage(self):
        """Statistics Page"""
        page = QtGui.QWidget()
        page.setLayout(QtGui.QGridLayout())
        text = QtGui.QTextEdit(page)
        text.setReadOnly(True)
        text.setPlainText("%s" % self.__show.stats)
        page.layout().addWidget(text)

        #page.layout().setRowStretch(10, 100)

        return page

    def __createRawShowDataPage(self):
        """Raw Show Data Page"""
        page = QtGui.QWidget()
        page.setLayout(QtGui.QVBoxLayout())
        text = QtGui.QTextEdit(page)
        text.setReadOnly(True)
        text.setPlainText("Show: %s%s\n%s\n%s" % (self.__show.name(),
                                                  self.__show.data,
                                                  self.__show.stats,
                                                  self.__show.proxy))
        page.layout().addWidget(text)

        return page

    def __valueChanged(self, value = None):
        """Called when something changes to enable the save button"""
        self.__btnSave.setEnabled(True)

    def __closeDialog(self):
        """Prompts to allow the user to save changes before exit"""
        if self.__btnSave.isEnabled():
            if Utils.questionBoxYesNo(self, "Save Changes?",
                                      "Do you want to save your changes?"):
                self.__saveChanges()
        self.accept()

    def __saveChanges(self):
        """If the save button is enabled, any changed values will be saved"""
        self.__btnSave.setEnabled(False)

        if self.__show.data.commentEmail != str(self.__show_email.text()):
            self.__show.proxy.setCommentEmail(str(self.__show_email.text()))

        if self.__show.data.defaultMinCores != self.__defaultMaxCores.value():
            self.__show.proxy.setDefaultMaxCores(self.__defaultMaxCores.value())

        if self.__show.data.defaultMinCores != self.__defaultMinCores.value():
            self.__show.proxy.setDefaultMinCores(self.__defaultMinCores.value())

        if self.__show.data.bookingEnabled != self.__bookingEnabled.isChecked():
            self.__show.proxy.enableBooking(self.__bookingEnabled.isChecked())

        if self.__show.data.dispatchEnabled != self.__dispatchEnabled.isChecked():
            self.__show.proxy.enableDispatching(self.__dispatchEnabled.isChecked())
