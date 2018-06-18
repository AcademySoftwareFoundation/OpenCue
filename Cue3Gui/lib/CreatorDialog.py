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


from Manifest import os, QtCore, QtGui, Cue3


class SubscriptionCreator(QtGui.QWidget):
    def __init__(self, show=None, parent=None):
        QtGui.QWidget.__init__(self, parent)
        show_name = ""
        if show:
            try:
                show_name = show.data.name
            except Exception:
                show_name = str(show)

        self.__shows = Cue3.getShows()
        self.__allocs = Cue3.getAllocations()

        layout = QtGui.QFormLayout(self)

        self.showBox = QtGui.QComboBox(self)
        self.allocBox = QtGui.QComboBox(self)
        self.sizeBox = QtGui.QDoubleSpinBox(self)
        self.burstBox = QtGui.QDoubleSpinBox(self)

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
        try:
            showMap = dict(zip([s.data.name for s in self.__shows], self.__shows))
            allocMap = dict(zip([a.data.name for a in self.__allocs], self.__allocs))

            show = showMap[str(self.showBox.currentText())]
            alloc = allocMap[str(self.allocBox.currentText())]

            show.proxy.createSubscription(alloc.proxy,
                float(self.sizeBox.value()), float(self.burstBox.value()))
        except Exception, e:
            QtGui.QMessageBox.warning(self,
                "Create Subscription",
                "An exception occured while creating a subscription: %s" % e,
                QtGui.QMessageBox.Ok)


class SubscriptionCreatorDialog(QtGui.QDialog):
    def __init__(self, show=None, parent=None):
        QtGui.QDialog.__init__(self)

        self.__creator = SubscriptionCreator(show, self)
        self.__buttons = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.__creator)
        layout.addWidget(self.__buttons)

        self.resize(400,0)

        QtCore.QObject.connect(self.__buttons, QtCore.SIGNAL("accepted()"), self.create)
        QtCore.QObject.connect(self.__buttons, QtCore.SIGNAL("rejected()"), self.close)

    def create(self):
        self.__creator.create()
        self.close()
