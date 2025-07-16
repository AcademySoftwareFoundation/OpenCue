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


"""An interface for redirecting resources from one job to another job.

The concept here is that there is a target job that needs procs. The user would choose the job.
The highest core/memory value would be detected and would populate 2 text boxes for cores and
memory. The user could then adjust these and hit search. The search will find all hosts that have
frames running that can be redirected to the target job."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str

from qtpy import QtGui
from qtpy import QtWidgets

from opencue_proto import report_pb2
import opencue

import cuegui.Utils

class ProcChildren(QtWidgets.QWidget):
    """Widget for displaying Host statistics for a Proc's child processes."""

    HEADERS = ["PID", "Name", "Start Time", "Rss (KB)", "VSize (KB)",
               "Statm Rss (KB)", "Statm Size (KB)", "Cmd line"]

    def __init__(self, job, layer, hosts, parent=None):
        """
        Initializes the list of procs for a given job to display

        :param job: job Object for this item (opencue.wrappers.job.Job)
        :param layer: job Object for this item (opencue.wrappers.layer.Layer)
        :param hosts: list of host Object for this item (List[opencue.wrappers.host.Host])
        :param parent: Optional parent for this item
        """
        QtWidgets.QWidget.__init__(self, parent)
        self._data = {}

        self._job = job
        self._layer = layer
        self._hosts = hosts
        self._model = QtGui.QStandardItemModel(self)
        self._model.setColumnCount(5)
        self._model.setHorizontalHeaderLabels(ProcChildren.HEADERS)

        self._tree = QtWidgets.QTreeView(self)
        self._tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._tree.setModel(self._model)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._tree)

    def update(self):
        """ Updates visual representation with latest data"""
        self._model.clear()
        self._model.setHorizontalHeaderLabels(ProcChildren.HEADERS)
        childrenProc = report_pb2.ChildrenProcStats()
        data = { }

        try:
            procs = opencue.api.getProcs(job=[self._job.name()],
                                         layer=[x.name() for x in self._job.getLayers()],
                                         host=self._hosts)
            for proc in procs:
                data['children_processes'] =\
                    childrenProc.FromString(proc.data.child_processes).children

                name = proc.data.name.split("/")[0]
                if name not in data:
                    cue_host = opencue.api.findHost(name)
                    data['host'] = cue_host
                self._addProc(data)

            self._data = data

        except opencue.exception.CueException:
            msg = ('No Proc Data available: \n%s '
                   % (self._job.name()))
            cuegui.Utils.showErrorMessageBox(msg)

    def _addProc(self, entry):
        host = entry["host"]

        checkbox = QtGui.QStandardItem(host.data.name)

        self._model.appendRow([checkbox])

        for proc in entry['children_processes']:
            checkbox.appendRow([QtGui.QStandardItem(proc.stat.pid),
                                QtGui.QStandardItem(proc.stat.name),
                                QtGui.QStandardItem(proc.start_time),
                                QtGui.QStandardItem(str(proc.stat.rss)),
                                QtGui.QStandardItem(str(proc.stat.vsize)),
                                QtGui.QStandardItem(str(proc.statm.rss)),
                                QtGui.QStandardItem(str(proc.statm.size)),
                                QtGui.QStandardItem(str(proc.cmdline))])

        self._tree.setExpanded(self._model.indexFromItem(checkbox), True)
        self._tree.resizeColumnToContents(0)


class ProcChildrenDialog(QtWidgets.QDialog):
    """
    Dialog for displaying Host statistics for a Proc's child processes
    """
    def __init__(self, job, layer, hosts, text, title, parent=None):
        """
        Initializes the data to be displayed
        :ptype job: opencue.wrappers.job.Job
        :param job: job Object for this item
        :ptype layer: opencue.wrappers.layer.Layer
        :param layer: layer Object for this item
        :ptype hosts: List[opencue.wrappers.host.Host]
        :param hosts: list of hosts Object for this item
        :ptype text: str
        :param text: Description of what is being displayed
        :ptype title: str
        :param title: Window Title
        :param parent: AbstractActions
        :param parent: The dialog's parent
        """

        QtWidgets.QDialog.__init__(self, parent)
        self.parent = parent
        self.job = job
        self.text = text
        self.title = title
        self.setWindowTitle(self.title)
        self._childProcStats = ProcChildren(job, layer, hosts, parent=parent)
        self.resize(920, 420)

        _labelText = QtWidgets.QLabel(text, self)
        _labelText.setWordWrap(True)
        _btnUpdate = QtWidgets.QPushButton("Refresh", self)
        _btnClose = QtWidgets.QPushButton("Close", self)

        _vlayout = QtWidgets.QVBoxLayout(self)
        _vlayout.addWidget(_labelText)
        _vlayout.addWidget(self._childProcStats)

        _hlayout = QtWidgets.QHBoxLayout()
        _hlayout.addWidget(_btnUpdate)
        _hlayout.addWidget(_btnClose)
        _vlayout.addLayout(_hlayout)

        self._childProcStats.update()
        # pylint: disable=no-member
        _btnClose.clicked.connect(self.accept)
        _btnUpdate.clicked.connect(self.refresh)
        # pylint: enable=no-member

    def refresh(self):
        """Update host report statistics"""
        self._childProcStats.update()

    def accept(self):
        """Exit"""
        self.close()
