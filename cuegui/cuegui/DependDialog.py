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


from __future__ import absolute_import

from PySide2 import QtCore
from PySide2 import QtWidgets

from .DependMonitorTree import DependMonitorTree
from . import Logger
from . import Utils


logger = Logger.getLogger(__file__)


class DependDialog(QtWidgets.QDialog):
    def __init__(self, object, parent=None):
        super(DependDialog, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)

        self.resize(1000, 600)

        name = "Dependencies for "
        if Utils.isJob(object):
            name +=  "Job: %s" % object.data.name
        elif Utils.isLayer(object):
            name +=  "Layer: %s" % object.data.name
        elif Utils.isFrame(object):
            name +=  "Frame: %s" % object.data.name

        self.setWindowTitle(name)

        self.hlayout = QtWidgets.QHBoxLayout(self)

        self._depend = DependMonitorTree(self, object)
        self.hlayout.addWidget(self._depend)

        self.setLayout(self.hlayout)
