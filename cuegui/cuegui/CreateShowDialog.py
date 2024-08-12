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


"""A dialog for creating new shows."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


from qtpy import QtCore
from qtpy import QtWidgets

import opencue


class CreateShowDialog(QtWidgets.QDialog):
    """A dialog for creating new shows.
    _________________________________________________
    | Show name    |__Enter show name here__|       |
    |                                               |
    | subscriptions_______________________________  |
    | |_| local.general  size |_____| burst |____|  |
    | |_| local.desktop  size |_____| burst |____|  |
    | |_| cloud.general  size |_____| burst |____|  |
    |                                               |
    |                    |_create_|     |_cancel_|  |
    |_______________________________________________|
    """

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.subscription_fields = []

        self.setWindowTitle("Create New Show")
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)

        self.__create_btn = QtWidgets.QPushButton("Create", self)
        self.__cancel_btn = QtWidgets.QPushButton("Close", self)

        self.__name_label = QtWidgets.QLabel("Show name")
        self.__name_field = QtWidgets.QLineEdit()
        self.__name_field.setPlaceholderText("Enter show name here")

        self.__subscription_grpbox = self.__createSubscriptionWidget()

        QtWidgets.QGridLayout(self)
        self.layout().addWidget(self.__name_label, 0, 0, 1, 1)
        self.layout().addWidget(self.__name_field, 0, 1, 1, 2)
        self.layout().addWidget(self.__subscription_grpbox, 1, 0, 4, 3)
        self.layout().addWidget(self.__create_btn, 5, 1)
        self.layout().addWidget(self.__cancel_btn, 5, 2)

        # pylint: disable=no-member
        self.__create_btn.clicked.connect(self.__createShow)
        self.__cancel_btn.clicked.connect(self.__cancelDialog)
        # pylint: enable=no-member
        self.adjustSize()

    def __createSubscriptionWidget(self):
        """Create the groupbox widget containing subscription fields"""
        widget = QtWidgets.QGroupBox("Subscriptions")
        layout = QtWidgets.QGridLayout()

        layout.addWidget(QtWidgets.QLabel("Allocation"), 0, 0 , 1, 1)
        layout.addWidget(QtWidgets.QLabel("Size"), 0, 1 , 1, 1)
        layout.addWidget(QtWidgets.QLabel("Burst"), 0, 2 , 1, 1)

        row = 1
        for allocation in opencue.api.getAllocations():
            alloc_checkbox = QtWidgets.QCheckBox(allocation.name())
            layout.addWidget(alloc_checkbox, row, 0 , 1, 1)

            size_spinbox = QtWidgets.QDoubleSpinBox(self)
            size_spinbox.setMaximum(1000000)
            size_spinbox.setValue(100)
            layout.addWidget(size_spinbox, row, 1 , 1, 1)

            burst_spinbox = QtWidgets.QDoubleSpinBox(self)
            burst_spinbox.setMaximum(1000000)
            burst_spinbox.setValue(100)
            layout.addWidget(burst_spinbox, row, 2 , 1, 1)

            self.subscription_fields.append({
                "allocation": allocation,
                "enabled": alloc_checkbox,
                "size": size_spinbox,
                "burst": burst_spinbox
            })

            row += 1

        widget.setLayout(layout)
        return widget

    def __createShow(self):
        """Create the show and specified subscriptions"""
        if not self.__validate():
            return

        show = self.tryCreateShow()
        if not show:
            return

        for subscription in self.subscription_fields:
            self.tryCreateSubscription(show, subscription)

        self.accept()

    def __cancelDialog(self):
        """Abort creating a new show"""
        self.reject()

    def __validate(self):
        """Validate fields before creating a show"""
        if not self.__validateName():
            return False

        if not self.__validateNoDuplicateShow():
            return False

        return True

    def __validateName(self):
        """Validate the name field"""
        show_name = self.__name_field.text()
        if not show_name:
            QtWidgets.QMessageBox.critical(
                self,
                "Invalid Show Name",
                "Please enter a valid show name.",
                QtWidgets.QMessageBox.Ok
            )
            return False
        return True

    def __validateNoDuplicateShow(self):
        """Validate an existing show with the same name doesn't exist"""
        show_name = self.__name_field.text()
        try:
            opencue.api.findShow(show_name)
        except opencue.EntityNotFoundException:
            return True

        QtWidgets.QMessageBox.critical(
            self,
            "Show Already Exists",
            "A show with that name already exists, please enter a unique show name.",
            QtWidgets.QMessageBox.Ok
        )

        return False

    # pylint: disable=inconsistent-return-statements
    def tryCreateShow(self):
        """Try to create the show in OpenCue

        @return: An opencue.wrappers.show.Show if successful
        """
        try:
            show = opencue.api.createShow(self.__name_field.text())
            return show
        except opencue.exception.CueException as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Failed To Create Show",
                str(e),
                QtWidgets.QMessageBox.Ok
            )

    def tryCreateSubscription(self, show, subscription):
        """Try to create a subscription for the show in OpenCue

        @type  show: opencue.wrappers.show.Show
        @param show: The show to create a subscription for.
        @type  subscription: dict
        @param subscription: A dictionary containing the Allocation instance
                             along with the other subscription field widgets.
        """
        if not subscription["enabled"].isChecked():
            return

        try:
            show.createSubscription(
                subscription["allocation"],
                float(subscription["size"].value()),
                float(subscription["burst"].value())
            )
        except opencue.exception.CueException as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Failed To Create Subscription",
                str(e),
                QtWidgets.QMessageBox.Ok
            )
