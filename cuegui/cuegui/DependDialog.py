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


"""Dialog displaying a list of dependencies for an object."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.DependMonitorTree
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class DependDialog(QtWidgets.QDialog):
    """Dialog displaying a list of dependencies for an object."""

    def __init__(self, rpcOject, parent=None):
        super(DependDialog, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)

        self.resize(1200, 800)

        name = "Dependencies for "
        if cuegui.Utils.isJob(rpcOject):
            name += "Job: %s" % rpcOject.data.name
        elif cuegui.Utils.isLayer(rpcOject):
            name += "Layer: %s" % rpcOject.data.name
        elif cuegui.Utils.isFrame(rpcOject):
            name += "Frame: %s" % rpcOject.data.name

        self.setWindowTitle(name)

        self.hlayout = QtWidgets.QHBoxLayout(self)

        self._depend = cuegui.DependMonitorTree.DependMonitorTree(self, rpcOject)
        self.hlayout.addWidget(self._depend)

        self.setLayout(self.hlayout)
