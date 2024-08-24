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


"""Dialog for subscribing to job updates"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import getpass

from builtins import map

from qtpy import QtCore
from qtpy import QtWidgets
import cuegui.Constants
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class SubscribeToJobDialog(QtWidgets.QDialog):
    """Dialog for email subscription to jobs"""

    def __init__(self, jobs, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.__jobs = jobs

        job_names = ', '.join(map(lambda job: job.data.name, jobs))

        self.setWindowTitle("Subscribe to jobs %s" % job_names)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setFixedSize(600, 400)

        self.__treeSubjects = QtWidgets.QTreeWidget(self)
        self.__treeSubjects.setHeaderLabels(["Job name"])

        self.__email = EmailInfoWidget(jobs, self)

        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addWidget(self.__treeSubjects)
        vlayout.addWidget(self.__email)

        self.__email.save.connect(self.accept)
        self.__email.cancel.connect(self.reject)

        self.refreshJobList()

    def refreshJobList(self):
        """Refresh the list of jobs"""
        jobs = self.__jobs
        self.__treeSubjects.clear()
        for job in jobs:
            item = Job(job)
            self.__treeSubjects.addTopLevelItem(item)

class EmailInfoWidget(QtWidgets.QWidget):
    """Widget for displaying an email form."""

    save = QtCore.Signal()
    cancel = QtCore.Signal()

    def __init__(self, jobs, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.__jobs = jobs

        __default_to = "%s@%s" % (getpass.getuser(), cuegui.Constants.EMAIL_DOMAIN)

        __default_from = "opencue-noreply@imageworks.com"

        self.__btnSave = QtWidgets.QPushButton("Save", self)
        self.__btnCancel = QtWidgets.QPushButton("Cancel", self)

        # Body Widgets
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding,
                                           QtWidgets.QSizePolicy.Minimum)

        self.__email_from = QtWidgets.QLabel(__default_from, self)
        self.__email_to = QtWidgets.QLineEdit(__default_to, self)

        # Main Vertical Layout
        vlayout = QtWidgets.QVBoxLayout(self)

        # Top Grid Layout
        glayout = QtWidgets.QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)

        glayout.addWidget(QtWidgets.QLabel("From:", self), 0, 0)
        glayout.addWidget(self.__email_from, 0, 1)

        glayout.addWidget(QtWidgets.QLabel("To:", self), 1, 0)
        glayout.addWidget(self.__email_to, 1, 1)

        vlayout.addLayout(glayout)

        # Bottom Horizontal Layout
        hlayout = QtWidgets.QHBoxLayout()
        hlayout.addItem(spacerItem)
        hlayout.addWidget(self.__btnSave)
        hlayout.addWidget(self.__btnCancel)
        vlayout.addLayout(hlayout)

        # pylint: disable=no-member
        self.__btnSave.clicked.connect(self.addSubscriber)
        self.__btnCancel.clicked.connect(self.cancel.emit)
        # pylint: enable=no-member

    def email_to(self):
        """Gets the email recipient."""
        return "%s" % self.__email_to.text()

    def addSubscriber(self):
        """Adds subscriber to jobs."""
        for job in self.__jobs:
            job.addSubscriber(self.email_to())
        self.save.emit()

class Job(QtWidgets.QTreeWidgetItem):
    """A widget to represent a job in the job list"""
    def __init__(self, job):
        QtWidgets.QTreeWidgetItem.__init__(
            self,
            [job.name(),
             ])
