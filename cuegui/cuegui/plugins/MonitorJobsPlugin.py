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


"""Plugin for listing active jobs and managing them."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import map
import datetime
import re
import weakref

from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets

import opencue

import cuegui.AbstractDockWidget
import cuegui.Action
import cuegui.Constants
import cuegui.JobMonitorTree
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

PLUGIN_NAME = "Monitor Jobs"
PLUGIN_CATEGORY = "Cuetopia"
PLUGIN_DESCRIPTION = "Monitors a list of jobs"
PLUGIN_PROVIDES = "MonitorJobsDockWidget"
JOB_RESTORE_THRESHOLD_DAYS = 3
JOB_RESTORE_THRESHOLD_LIMIT = 200

class MonitorJobsDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin for listing active jobs and managing them."""

    view_object = QtCore.Signal(object)

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__loadFinishedJobsCheckBox = None

        self.jobMonitor = cuegui.JobMonitorTree.JobMonitorTree(self)

        self.__toolbar = QtWidgets.QToolBar(self)
        self._regexLoadJobsSetup(self.__toolbar)
        self._buttonSetup(self.__toolbar)

        self.layout().addWidget(self.__toolbar)
        self.layout().addWidget(self.jobMonitor)

        # Signals in
        self.app.view_object.connect(self.addJob)
        self.app.facility_changed.connect(self.jobMonitor.removeAllItems)

        # Signals out
        self.jobMonitor.view_object.connect(self.view_object.emit)

        self.pluginRegisterSettings([("regexText",
                                      self.__regexLoadJobsEditBox.text,
                                      self.__regexLoadJobsEditBox.setText),
                                     ("jobs",
                                      self.getJobIds,
                                      self.restoreJobIds),
                                     ("userColors",
                                      self.jobMonitor.getUserColors,
                                      self.jobMonitor.setUserColors),
                                     ("columnVisibility",
                                      self.jobMonitor.getColumnVisibility,
                                      self.jobMonitor.setColumnVisibility),
                                     ("columnWidths",
                                      self.jobMonitor.getColumnWidths,
                                      self.jobMonitor.setColumnWidths),
                                     ("columnOrder",
                                      self.jobMonitor.getColumnOrder,
                                      self.jobMonitor.setColumnOrder),
                                     ("loadFinished",
                                      self.__loadFinishedJobsCheckBox.isChecked,
                                      self.__loadFinishedJobsCheckBox.setChecked),
                                      ("grpDependentCb",
                                      self.getGrpDependent,
                                      self.setGrpDependent),
                                      ("autoLoadMineCb",
                                      self.getAutoLoadMine,
                                      self.setAutoLoadMine)])

    def addJob(self, rpcObject):
        """Adds a job to be monitored."""
        if cuegui.Utils.isProc(rpcObject):
            rpcObject = cuegui.Utils.findJob(rpcObject.data.job_name)
        elif not cuegui.Utils.isJob(rpcObject):
            return
        self.jobMonitor.addJob(rpcObject, loading_from_config=True)
        self.raise_()

    def getJobIds(self):
        """Returns a list of the IDs of all jobs being monitored."""
        return list(map(opencue.id, self.jobMonitor.getJobProxies()))

    def restoreJobIds(self, jobIds):
        """Restore monitored jobs from previous saved state
        Only load jobs that have a timestamp less than or equal to the time a job lives on the farm
        (jobs are moved to historical database)

        :param jobIds: monitored jobs ids and their timestamp from previous working state
                       (loaded from config.ini file)
                       ex: [("Job.f156be87-987a-48b9-b9da-774cd58674a3", 1612482716.170947),...
        :type jobIds: list[tuples]
        """
        today = datetime.datetime.now()
        limit = JOB_RESTORE_THRESHOLD_LIMIT if len(jobIds) > \
                                                JOB_RESTORE_THRESHOLD_LIMIT else len(jobIds)
        msg = ('Unable to load previously loaded job since it was moved '
                   'to the historical database: {0}')

        try:
            for jobId, timestamp in jobIds[:limit]:
                loggedTime = datetime.datetime.fromtimestamp(timestamp)
                if (today - loggedTime).days <= JOB_RESTORE_THRESHOLD_DAYS:
                    try:
                        self.jobMonitor.addJob(jobId, timestamp)
                    except opencue.EntityNotFoundException:
                        logger.info(msg, jobId)
        except ValueError:
            # load older format
            for jobId in jobIds[:limit]:
                try:
                    self.jobMonitor.addJob(jobId)
                except opencue.EntityNotFoundException:
                    logger.info(msg, jobId)

    def pluginRestoreState(self, saved_settings):
        """Called on plugin start with any previously saved state.

        @param saved_settings: Last state of the plugin instance
        @type  saved_settings: any"""
        if isinstance(saved_settings, dict):
            cuegui.AbstractDockWidget.AbstractDockWidget.pluginRestoreState(self, saved_settings)

        elif saved_settings:
            # old method that needs to go away
            if len(saved_settings) >= 1:
                self.__regexLoadJobsEditBox.setText(saved_settings[0])
            if len(saved_settings) >= 2 and saved_settings[1]:
                for jobId in saved_settings[1]:
                    try:
                        self.jobMonitor.addJob(jobId)
                    except opencue.EntityNotFoundException:
                        logger.warning("Unable to load previously loaded job since"
                                       "it was moved to the historical "
                                       "database: %s", jobId)

    def _regexLoadJobsSetup(self, layout):
        """Selects jobs by name substring.
        Requires: self._regexLoadJobsHandle() and class JobRegexLoadEditBox
        @param layout: The layout that the widgets will be placed in
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Load:")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(btn)
        btn.clicked.connect(self._regexLoadJobsHandle)  # pylint: disable=no-member

        self.__regexLoadJobsEditBox = JobRegexLoadEditBox(self)
        layout.addWidget(self.__regexLoadJobsEditBox)
        self.__regexLoadJobsEditBox.returnPressed.connect(self._regexLoadJobsHandle)  # pylint: disable=no-member

    def _loadFinishedJobsSetup(self, layout):
        """Ensures that when querying jobs that finished jobs are included.
        Requires: self._regexLoadJobsHandle() and class JobLoadFinishedCheckBox
        @param layout: The layout that the widgets will be placed in
        @type  layout: QLayout"""
        self.__loadFinishedJobsCheckBox = JobLoadFinishedCheckBox(self)
        layout.addWidget(self.__loadFinishedJobsCheckBox)
        self.__loadFinishedJobsCheckBox.stateChanged.connect(self._regexLoadJobsHandle)  # pylint: disable=no-member

    def _regexLoadJobsHandle(self):
        """This will select all jobs that have a name that contains the substring
        in self.__regexLoadJobsEditBox.text() and scroll to the first match."""
        substring = str(self.__regexLoadJobsEditBox.text()).strip()
        load_finished_jobs = self.__loadFinishedJobsCheckBox.isChecked()

        # Only clear the existing jobs if SEARCH_JOBS_APPEND_RESULTS is False
        if not cuegui.Constants.SEARCH_JOBS_APPEND_RESULTS:
            self.jobMonitor.removeAllItems()

        if substring:
            # Load job if a uuid is provided
            if cuegui.Utils.isStringId(substring):
                self.jobMonitor.addJob(substring)
            # Load if show and shot are provided or if the "load finished" checkbox is checked
            elif load_finished_jobs or re.search(
                r"^([a-z0-9_]+)\-([a-z0-9\.]+)\-", substring, re.IGNORECASE):
                for job in opencue.api.getJobs(regex=[substring], include_finished=True):
                    self.jobMonitor.addJob(job)
            # Otherwise, just load current matching jobs (except for the empty string)
            else:
                for job in opencue.api.getJobs(regex=[substring]):
                    self.jobMonitor.addJob(job)

    def getGrpDependent(self):
        """Is group dependent checked"""
        return bool(self.grpDependentCb.isChecked())

    def setGrpDependent(self, state):
        """Set group dependent"""
        self.grpDependentCb.setChecked(bool(state))

    def getAutoLoadMine(self):
        """Is autoload mine checked"""
        return bool(self.autoLoadMineCb.isChecked())

    def setAutoLoadMine(self, state):
        """Set autoload mine"""
        self.autoLoadMineCb.setChecked(bool(state))

    def _buttonSetup(self, layout):
        clearButton = QtWidgets.QPushButton("Clr")
        clearButton.setFocusPolicy(QtCore.Qt.NoFocus)
        clearButton.setFixedWidth(24)
        layout.addWidget(clearButton)
        clearButton.clicked.connect(self.__regexLoadJobsEditBox.actionClear)  # pylint: disable=no-member

        spacer = QtWidgets.QWidget()
        spacer.setFixedWidth(20)
        layout.addWidget(spacer)

        self.autoLoadMineCb = QtWidgets.QCheckBox("Autoload Mine")
        self.autoLoadMineCb.setFocusPolicy(QtCore.Qt.NoFocus)
        self.autoLoadMineCb.setChecked(True)
        layout.addWidget(self.autoLoadMineCb)
        self.autoLoadMineCb.stateChanged.connect(self.jobMonitor.setLoadMine)  # pylint: disable=no-member

        self._loadFinishedJobsSetup(self.__toolbar)

        self.grpDependentCb = QtWidgets.QCheckBox("Group Dependent")
        self.grpDependentCb.setFocusPolicy(QtCore.Qt.NoFocus)
        self.grpDependentCb.setChecked(True)
        layout.addWidget(self.grpDependentCb)
        # pylint: disable=no-member
        self.grpDependentCb.stateChanged.connect(self.jobMonitor.setGroupDependent)
        # pylint: enable=no-member

        finishedButton = QtWidgets.QPushButton(QtGui.QIcon(":eject.png"), "Finished")
        finishedButton.setToolTip("Unmonitor finished jobs")
        finishedButton.setFocusPolicy(QtCore.Qt.NoFocus)
        finishedButton.setFlat(True)
        layout.addWidget(finishedButton)
        finishedButton.clicked.connect(self.jobMonitor.removeFinishedItems)  # pylint: disable=no-member

        allButton = QtWidgets.QPushButton(QtGui.QIcon(":eject.png"), "All")
        allButton.setToolTip("Unmonitor all jobs")
        allButton.setFocusPolicy(QtCore.Qt.NoFocus)
        allButton.setFlat(True)
        layout.addWidget(allButton)
        allButton.clicked.connect(self.jobMonitor.removeAllItems)  # pylint: disable=no-member

        removeSelectedButton = QtWidgets.QPushButton(QtGui.QIcon(":eject.png"), "")
        removeSelectedButton.setToolTip("Unmonitor selected jobs")
        removeSelectedButton.setFocusPolicy(QtCore.Qt.NoFocus)
        removeSelectedButton.setFlat(True)
        layout.addWidget(removeSelectedButton)
        removeSelectedButton.clicked.connect(self.jobMonitor.actionRemoveSelectedItems)  # pylint: disable=no-member

        eatSelectedButton = QtWidgets.QPushButton(QtGui.QIcon(":eat.png"), "")
        eatSelectedButton.setToolTip("Eats all dead frames for selected jobs")
        eatSelectedButton.setFocusPolicy(QtCore.Qt.NoFocus)
        eatSelectedButton.setFlat(True)
        layout.addWidget(eatSelectedButton)
        eatSelectedButton.clicked.connect(self.jobMonitor.actionEatSelectedItems)  # pylint: disable=no-member

        retryButton = QtWidgets.QPushButton(QtGui.QIcon(":retry.png"), "")
        retryButton.setToolTip("Retries all dead frames for selected jobs")
        retryButton.setFocusPolicy(QtCore.Qt.NoFocus)
        retryButton.setFlat(True)
        layout.addWidget(retryButton)
        retryButton.clicked.connect(self.jobMonitor.actionRetrySelectedItems)  # pylint: disable=no-member

        killButton = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "")
        killButton.setToolTip("Kill selected jobs")
        killButton.setFocusPolicy(QtCore.Qt.NoFocus)
        killButton.setFlat(True)
        layout.addWidget(killButton)
        killButton.clicked.connect(self.jobMonitor.actionKillSelectedItems)  # pylint: disable=no-member

        pauseButton = QtWidgets.QPushButton(QtGui.QIcon(":pause.png"), "")
        pauseButton.setToolTip("Pause selected jobs")
        pauseButton.setFocusPolicy(QtCore.Qt.NoFocus)
        pauseButton.setFlat(True)
        layout.addWidget(pauseButton)
        pauseButton.clicked.connect(self.jobMonitor.actionPauseSelectedItems)  # pylint: disable=no-member

        unpauseButton = QtWidgets.QPushButton(QtGui.QIcon(":unpause.png"), "")
        unpauseButton.setToolTip("Unpause selected jobs")
        unpauseButton.setFocusPolicy(QtCore.Qt.NoFocus)
        unpauseButton.setFlat(True)
        layout.addWidget(unpauseButton)
        unpauseButton.clicked.connect(self.jobMonitor.actionResumeSelectedItems)  # pylint: disable=no-member


class JobLoadFinishedCheckBox(QtWidgets.QCheckBox):
    """Checkbox for controlling whether finished jobs appear in the list."""

    def __init__(self, parent):
        QtWidgets.QCheckBox.__init__(self, 'Load Finished')
        self.parent = weakref.proxy(parent)

        toolTip = 'This ensures that all finished jobs<br>' \
                  'get included when querying the Cuebot server'

        self.setToolTip(toolTip)


class JobRegexLoadEditBox(QtWidgets.QLineEdit):
    """Textbox for searching for jobs to add to the list of monitored jobs."""

    def __init__(self, parent):
        QtWidgets.QLineEdit.__init__(self)
        self.parent = weakref.proxy(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFont(cuegui.Constants.STANDARD_FONT)
        self.setFixedWidth(200)
        self.setMaxLength(200)

        toolTip = 'This accepts regular expression.<br>' \
                  'Use .* to match any string<br>' \
                  'Example searches:<br>' \
                  '&nbsp;&nbsp;&nbsp;&nbsp;sm2.*comp<br>' \
                  '&nbsp;&nbsp;&nbsp;&nbsp;sm2-(madkisson|chung).*comp<br>' \
                  'Jobs finished for 3 days will no longer be available in cuetopia.<br>' \
                  'Load your finished jobs with at least: show-shot-username_'

        self.setToolTip(toolTip)

    def contextMenuEvent(self, e):
        """Handle context menu events"""
        menu = QtWidgets.QMenu(self)

        menu.addAction(cuegui.Action.create(self,
                                            "Load matching jobs (Enter)",
                                            "Load matching jobs",
                                            self._actionLoad))

        menu.addAction(cuegui.Action.create(self,
                                            "Lock/Unlock edit box",
                                            "Lock/Unlock edit box",
                                            self.toggleReadOnly))

        menu.addAction(cuegui.Action.create(self,
                                            "Clear",
                                            "Clear text",
                                            self.actionClear))

        menu.exec_(QtCore.QPoint(e.globalX(), e.globalY()))

    def actionClear(self):
        """Clears the textbox."""
        self.setText("")

    def _actionLoad(self):
        self.returnPressed.emit()  # pylint: disable=no-member

    def toggleReadOnly(self):
        """Toggles the textbox readonly setting."""
        self.setReadOnly(not self.isReadOnly())

    def keyPressEvent(self, event):
        """Let the parent handle any space key presses"""
        if event.key() == QtCore.Qt.Key_Space:
            self.parent.keyPressEvent(event)
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)
