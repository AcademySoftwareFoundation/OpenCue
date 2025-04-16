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

"""
CueProgBar - OpenCue job progress bar widget

Usage:
    cueprogbar <job_name>

This module provides a window to visually monitor the frame status
of an OpenCue job in real time. Each frame state is color-coded, and the window
provides context actions to pause, unpause, or kill the job.

It can be launched standalone via:
    cd Opencue/
    python -m cuegui.cueguiplugin.cueprogbar <job_name>
"""

import getpass
import signal
import sys
from math import ceil
from time import sleep

from qtpy import QtCore, QtGui, QtWidgets
from opencue import api as Opencue

from .darkmojo import DarkMojoPalette

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------

RGB_FRAME_STATE = {
    Opencue.Frame.FrameState.SUCCEEDED: QtGui.QColor(55, 200, 55),
    Opencue.Frame.FrameState.RUNNING: QtGui.QColor(200, 200, 55),
    Opencue.Frame.FrameState.WAITING: QtGui.QColor(135, 207, 235),
    Opencue.Frame.FrameState.DEPEND: QtGui.QColor(160, 32, 240),
    Opencue.Frame.FrameState.DEAD: QtGui.QColor(255, 0, 0),
    Opencue.Frame.FrameState.EATEN: QtGui.QColor(150, 0, 0),
}

STATES_TYPE_FRAME = tuple(RGB_FRAME_STATE.keys())
NORMAL_ICON = './images/cueprogbar_icon.png'
UPDATE_DELAY = 5000  # milliseconds
DEFAULT_JOB_KILL_REASON = f"Manual Job Kill Request in CueProgBar by {getpass.getuser()}"

# ------------------------------------------------------------------------------
# Widgets
# ------------------------------------------------------------------------------

class JobProgressBar(QtWidgets.QWidget):
    """
    Custom QWidget that paints a horizontal progress bar representing
    job frame states using color blocks. Also supports right-click
    job controls like pause, unpause, and kill.
    """
    def __init__(self, job, parent=None):
        """
        Initializes the progress bar widget with job data and context menu actions.

        Args:
            job (opencue.Job): The job object to visualize.
            parent (QWidget, optional): Optional parent widget.
        """
        super().__init__(parent)
        self._job = job
        self._menu = None
        self.setMouseTracking(True)
        self.setContentsMargins(1, 1, 1, 1)
        self.setMinimumSize(200, 14)

        # Context menu actions
        self.action_unpause = QtWidgets.QAction("Unpause Job", self)
        self.action_unpause.setToolTip("Unpause the job")
        self.action_unpause.triggered.connect(self._unpause)

        self.action_pause = QtWidgets.QAction("Pause Job", self)
        self.action_pause.setToolTip("Pause the job")
        self.action_pause.triggered.connect(self._pause)

        self.action_kill = QtWidgets.QAction("Kill Job", self)
        self.action_kill.setToolTip("Kill the job")
        self.action_kill.triggered.connect(self._kill)

    def paintEvent(self, _event):
        """
        Draws a bar of frame status colors across the widget.
        Each state is shown in a proportionate colored block.
        """
        try:
            self._job = Opencue.getJobs(id=[self._job.id()], include_finished=True)[0]
            p = QtGui.QPainter(self)
            rect = self.contentsRect()
            total = self._job.totalFrames()
            ratio = rect.width() / float(total)
            frame_counts = self._job.frameStateTotals()

            for state in STATES_TYPE_FRAME:
                length = int(ceil(ratio * frame_counts[state]))
                if length > 0:
                    rect.setWidth(length)
                    p.fillRect(rect, RGB_FRAME_STATE[state])
                    rect.setX(rect.x() + length)

            if self._job.state() == Opencue.Job.JobState.FINISHED:
                p.setPen(QtCore.Qt.black)
                p.drawText(1, 11, "COMPLETE")
            elif self._job.isPaused():
                p.setPen(QtCore.Qt.blue)
                p.drawText(1, 11, "Paused")

        except Exception as e:
            print(f"[CueProgBar] paintEvent error: {e}")
            p.setPen(QtCore.Qt.red)
            p.drawText(60, 10, "Job Not Found")

    def mousePressEvent(self, event):
        """
        Show job status or control menu on mouse click.
        Left click = show frame counts.
        Right click = pause/unpause/kill options.
        """
        self._menu = QtWidgets.QMenu(self)
        self._menu.addAction(self._job.name())
        self._menu.addSeparator()

        if event.button() == QtCore.Qt.LeftButton:
            for state in STATES_TYPE_FRAME:
                count = self._job.frameStateTotals()[state]
                if count > 0:
                    icon = XanacueColorIcon(RGB_FRAME_STATE[state])
                    label = f"{count}   {state}"
                    self._menu.addAction(icon, label)
        else:
            if self._job.state() != Opencue.Job.JobState.FINISHED:
                action = self.action_unpause if self._job.isPaused() else self.action_pause
                self._menu.addAction(action)
                self._menu.addSeparator()
                self._menu.addAction(self.action_kill)

        self._menu.exec_(event.globalPos())

    def _unpause(self):
        """
        Resume the paused job and refresh the UI.
        """
        self._job.resume()
        self.update()

    def _pause(self):
        """
        Pause the running job and refresh the UI.
        """
        self._job.pause()
        self.update()

    def _kill(self):
        """
        Prompt user confirmation and kill the job if confirmed.
        """
        confirm = QtWidgets.QMessageBox.question(
            self, "Kill Confirmation",
            f"Are you sure you want to kill this job?\n{self._job.name()}",
            QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.No
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            self._job.kill(reason=DEFAULT_JOB_KILL_REASON)

class XanacueColorIcon(QtGui.QIcon):
    """
    Small square icon filled with a given color.
    Used in the left-click menu to represent frame state.
    """
    def __init__(self, color):
        super().__init__()
        pixmap = QtGui.QPixmap(22, 22)
        pixmap.fill(color)
        self.addPixmap(pixmap)

class CueProgBar(QtWidgets.QWidget):
    """
    Main window that contains the job progress bar and labels.
    Displays real-time job progress and updates the status based on frame states.
    """
    def __init__(self, job, parent=None):
        """
       Initializes the progress bar UI with labels and update timer.

       Args:
           job (opencue.Job): The job object to track.
           parent (QWidget, optional): Optional parent widget.
       """
        super().__init__(parent)
        self._job = job
        self._error = None

        self.progress_bar = JobProgressBar(job, self)
        self.label1 = QtWidgets.QLabel()
        self.label2 = QtWidgets.QLabel(job.name())

        # Tooltip consistency
        for widget in (self.progress_bar, self.label1, self.label2):
            widget.setToolTip(job.name())

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.label1)
        layout.addWidget(self.label2)
        layout.setContentsMargins(6, 6, 6, 6)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(UPDATE_DELAY)

    def _update(self):
        """
        Updates the job data periodically to reflect real-time changes.
        Handles job errors gracefully.
        """
        try:
            if self._job.state() != Opencue.Job.JobState.FINISHED:
                self._job = Opencue.getJobs(id=[self._job.id()], include_finished=True)[0]
                self._error = None
                self.update()
        except Exception as e:
            self._error = str(e)

    def paintEvent(self, event):
        """
        Paints the window, updates labels and title with job status.

        Args:
            event (QPaintEvent): Paint event triggering the UI update.
        """
        total = self._job.totalFrames()
        done = self._job.succeededFrames() + self._job.eatenFrames()
        running = self._job.runningFrames()
        dead = self._job.deadFrames()

        if self._error:
            self.label1.setText(self._error)
        else:
            self.label1.setText(f"{done} of {total} done, {running} running")

        if self._job.state() == Opencue.Job.JobState.FINISHED:
            status = "DONE"
        elif dead > 0 or total == 0:
            status = "ERR"
        else:
            status = f"{int((done / total) * 100)}%"

        self.setWindowTitle(f"{status} {self._job.name()}")
        super().paintEvent(event)

# ------------------------------------------------------------------------------
# Entry Point
# ------------------------------------------------------------------------------

def run(argv):
    """
    Launch the CueProgBar window for the given job name.

    Args:
        argv (List[str]): Command line arguments. Expects one job name.
    """
    if len(argv) != 2:
        print(__doc__)
        sys.exit(1)

    job_name = argv[1]
    attempts = 0
    job = None

    # Retry loop in case job is not immediately resolvable
    while attempts < 10 and not job:
        try:
            job = Opencue.findJob(job_name)
        except Exception:
            job = None
            attempts += 1
            sleep(2)

    if job:
        app = QtWidgets.QApplication(sys.argv)
        app.setPalette(DarkMojoPalette())
        app.setStyle('DarkMojo')

        # Enable Ctrl+C to exit
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        widget = CueProgBar(job)
        widget.setMinimumSize(210, 65)
        widget.setWindowTitle(job_name)
        widget.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(NORMAL_ICON)))
        widget.show()

        app.exec_()
    else:
        print(f"Unable to find job: {job_name}")
