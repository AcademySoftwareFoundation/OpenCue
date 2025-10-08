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


"""A progress dialog that accepts a list of work units and displays the progress."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
from builtins import range

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


class ProgressDialog(QtWidgets.QDialog):
    """A progress dialog that accepts a list of work units and displays the progress."""

    def __init__(self, title, function, work, concurrent, cancelTitle,
                 cancelText, parent=None):
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
        self.app = cuegui.app()

        self.__work = work
        self.__function = function

        self.__workLock = QtCore.QReadWriteLock()
        self.__count = 0
        self.__isCompleted = False

        # Add a safety timer to prevent hanging dialogs
        self.__safetyTimer = QtCore.QTimer(self)
        self.__safetyTimer.timeout.connect(self.__checkCompletion)
        self.__safetyTimer.start(1000)  # Check every second

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

        self.__btn_cancel.clicked.connect(self.cancel)  # pylint: disable=no-member

        self.show()

        # Submit a new unit of work to the threadpool for each concurrent thread.
        for _ in range(max(concurrent, 1)):
            self._submitWork()

    def closeEvent(self, event):
        """Handle dialog close attempts"""
        if self.__isCompleted:
            # Work is done, allow closing
            self.__safetyTimer.stop()
            event.accept()
            super(ProgressDialog, self).closeEvent(event)
        else:
            # Work is in progress, show cancel confirmation
            event.ignore()
            self.cancel()

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == QtCore.Qt.Key_Escape:
            # ESC key should close the dialog
            if self.__isCompleted:
                self.close()
            else:
                self.cancel()
        else:
            super(ProgressDialog, self).keyPressEvent(event)

    def cancel(self):
        """Called when the user wishes to cancel the work. Work already
        in threadpool will complete and the progress bar will exit"""
        self.__cancelConfirmation = \
            QtWidgets.QMessageBox(QtWidgets.QMessageBox.Warning,
                                  self.__cancelTitle,
                                  self.__cancelText,
                                  QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No,
                                  self)
        result = self.__cancelConfirmation.exec_()
        self.__cancelConfirmation = None

        if result == QtWidgets.QMessageBox.Yes:
            self.__workLock.lockForWrite()
            try:
                self.__work = []
            finally:
                self.__workLock.unlock()
            # Mark as completed and close the dialog when user confirms cancellation
            self.__isCompleted = True
            self.__safetyTimer.stop()
            self.close()

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
            # pylint: disable=broad-except
            try:
                self.__function(*work)
            except Exception as e:
                logger.warning("Work unit returned exception:")
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
                # Even if work fails, we need to ensure proper count management
                # The __doneWork callback will still be called by the threadpool

    def __doneWork(self, work, result):
        """Called when a work unit is done, updates progress, exits if done
        @type  work:
        @param work: From threadpool (unused)
        @type  result:
        @param result: From threadpool (unused)"""
        del work
        del result

        self.__count -= 1

        self.__bar.setValue(self.__bar.value() + 1)

        self.__workLock.lockForWrite()
        try:
            if self.__work:
                self._submitWork()
            else:
                # Check if all work is completed - both no work left AND count is 0
                # or if progress bar shows 100% completion
                if self.__count <= 0 or self.__bar.value() >= self.__bar.maximum():
                    if self.__cancelConfirmation:
                        self.__cancelConfirmation.close()
                    self.__isCompleted = True
                    # Use QTimer to ensure proper cleanup in the main thread
                    QtCore.QTimer.singleShot(0, self.close)
        finally:
            self.__workLock.unlock()

    def __checkCompletion(self):
        """Safety check to ensure dialog completion detection works properly"""
        if self.__isCompleted:
            self.__safetyTimer.stop()
            return

        # Check if we should be completed based on progress
        if (not self.__work and self.__count <= 0) or self.__bar.value() >= self.__bar.maximum():
            logger.debug("Safety timer detected completion - closing dialog")
            if self.__cancelConfirmation:
                self.__cancelConfirmation.close()
            self.__isCompleted = True
            self.__safetyTimer.stop()
            self.close()

    def _submitWork(self):
        """Submits a new unit of work to threadpool"""
        self.__count += 1

        if self.app.threadpool is not None:
            self.app.threadpool.queue(
                self.__doWork, self.__doneWork, "getting data for %s" % self.__class__)
        else:
            logger.warning("threadpool not found, doing work in gui thread")
            self.__doneWork(None, self.__doWork())
