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
A progress dialog that accepts a list of work units and displays the progress.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
from builtins import range

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, title, function, work, concurrent, cancelTitle,
                 cancelText, parent = None):
        """Creates, displays and starts the progress bar.
        @type  title: str
        @param title: The title for the progress bar
        @type  function: callable
        @param function: The function that the work units should be passed to
        @type  work: list<sequence>
        @param work: A list of sequences to pass to the function
        @type  concurrent: int
        @param concurrent: The number of units to submit to threadpool at once
        @type  cancelTitle: string
        @param cancelTitle: This is displayed as the title of the confirmation
                            dialog box if the user attempts to cancel
        @type  cancelText: string
        @param cancelText: This is displayed as the text of the confirmation
                           dialog box if the user attempts to cancel
        @type  parent: QObject
        @param parent: The parent for this object"""
        QtWidgets.QDialog.__init__(self, parent)

        self.__work = work
        self.__function = function

        self.__workLock = QtCore.QReadWriteLock()
        self.__count = 0

        self.__bar = QtWidgets.QProgressBar(self)
        self.__bar.setRange(0, len(self.__work))
        self.__bar.setValue(0)
        self.__btn_cancel = QtWidgets.QPushButton("Cancel", self)
        self.__cancelConfirmation = None
        self.__cancelTitle = cancelTitle
        self.__cancelText = cancelText

        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addWidget(self.__bar)
        vlayout.addWidget(self.__btn_cancel)
        self.setLayout(vlayout)

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setFixedSize(300, 100)
        self.setWindowTitle(title)

        self.__btn_cancel.clicked.connect(self.cancel)

        self.show()

        for thread in range(max(concurrent, 1)):
            self._submitWork()

    def closeEvent(self, event):
        """Trying to close the dialog is the same as clicking cancel"""
        event.ignore()
        self.cancel()

    def cancel(self):
        """Called when the user wishes to cancel the work. Work already
        in threadpool will complete and the progress bar will exit"""
        self.__cancelConfirmation = \
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning,
                                  self.__cancelTitle,
                                  self.__cancelText,
                                  QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No,
                                  self)
        if self.__cancelConfirmation.exec_() == QtWidgets.QMessageBox.Yes:
            self.__workLock.lockForWrite()
            try:
                self.__work = []
            finally:
                self.__workLock.unlock()
        self.__cancelConfirmation = None

    def __doWork(self):
        """Performs the next unit of work available"""
        work = None

        self.__workLock.lockForWrite()
        try:
            if self.__work:
                work = self.__work.pop()
        finally:
            self.__workLock.unlock()

        if work:
            try:
                self.__function(*work)
            except Exception as e:
                logger.warning("Work unit returned exception:")
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def __doneWork(self, work, result):
        """Called when a work unit is done, updates progress, exits if done
        @type  work:
        @param work: From threadpool (unused)
        @type  result:
        @param result: From threadpool (unused)"""
        self.__count -= 1

        self.__bar.setValue(self.__bar.value() + 1)

        self.__workLock.lockForWrite()
        try:
            if self.__work:
                self._submitWork()
            else:
                if self.__count == 0:
                    if self.__cancelConfirmation:
                        self.__cancelConfirmation.close()
                    self.accept()
        finally:
            self.__workLock.unlock()

    def _submitWork(self):
        """Submits a new unit of work to threadpool"""
        self.__count += 1

        if hasattr(QtGui.qApp, "threadpool"):
            QtGui.qApp.threadpool.queue(self.__doWork,
                                        self.__doneWork,
                                        "getting data for %s" % self.__class__)
        else:
            logger.warning("threadpool not found, doing work in gui thread")
            self.__doneWork(None, self.__doWork())
