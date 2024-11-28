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


"""Dialog for creating a subscription."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import zip

from qtpy import QtWidgets

import opencue


class SubscriptionCreator(QtWidgets.QWidget):
    """Widget for creating a subscription."""

    def __init__(self, show=None, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        show_name = ""
        if show:
            show_name = show.data.name

        self.__shows = opencue.api.getShows()
        self.__allocs = opencue.api.getAllocations()

        layout = QtWidgets.QFormLayout(self)

        self.showBox = QtWidgets.QComboBox(self)
        self.allocBox = QtWidgets.QComboBox(self)
        self.sizeBox = QtWidgets.QDoubleSpinBox(self)
        self.burstBox = QtWidgets.QDoubleSpinBox(self)

        self.showBox.addItems([s.data.name for s in self.__shows])
        defaultIndex = self.showBox.findText(show_name)
        if defaultIndex >= 0:
            self.showBox.setCurrentIndex(defaultIndex)
        self.allocBox.addItems([a.data.name for a in self.__allocs])
        self.sizeBox.setMaximum(1000000)
        self.sizeBox.setValue(100)
        self.burstBox.setMaximum(1000000)
        self.burstBox.setValue(110)

        layout.addRow('Show:', self.showBox)
        layout.addRow('Alloc:', self.allocBox)
        layout.addRow('Size:', self.sizeBox)
        layout.addRow('Burst:', self.burstBox)

    def create(self):
        """Create Subscription"""
        try:
            showMap = dict(list(zip([s.data.name for s in self.__shows], self.__shows)))
            allocMap = dict(list(zip([a.data.name for a in self.__allocs], self.__allocs)))

            show = showMap[str(self.showBox.currentText())]
            alloc = allocMap[str(self.allocBox.currentText())]

            show.createSubscription(alloc, float(self.sizeBox.value()),
                                    float(self.burstBox.value()))
        except opencue.exception.CueException as e:
            QtWidgets.QMessageBox.warning(
                self,
                "Create Subscription",
                "An exception occured while creating a subscription: %s" % e,
                QtWidgets.QMessageBox.Ok)


class SubscriptionCreatorDialog(QtWidgets.QDialog):
    """Dialog for creating a subscription."""

    def __init__(self, show=None, parent=None):
        del parent

        QtWidgets.QDialog.__init__(self)

        self.__creator = SubscriptionCreator(show, self)
        self.__buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__creator)
        layout.addWidget(self.__buttons)

        self.resize(400, 0)
        # pylint: disable=no-member
        self.__buttons.accepted.connect(self.create)
        self.__buttons.rejected.connect(self.close)
        # pylint: enable=no-member

    def create(self):
        """Create subscription"""
        self.__creator.create()
        self.close()
