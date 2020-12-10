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


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import map
import re
import weakref

from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

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


class MonitorJobsDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""

    view_object = QtCore.Signal(object)

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.jobMonitor = cuegui.JobMonitorTree.JobMonitorTree(self)

        self.__toolbar = QtWidgets.QToolBar(self)
        self._regexLoadJobsSetup(self.__toolbar)
        #self.__toolbar.addSeparator()
        self._buttonSetup(self.__toolbar)

        self.layout().addWidget(self.__toolbar)
        self.layout().addWidget(self.jobMonitor)

        #Signals in:
        QtGui.qApp.view_object.connect(self.addJob)
        QtGui.qApp.facility_changed.connect(self.jobMonitor.removeAllItems)
        #Signals out:
        self.jobMonitor.view_object.connect(self.view_object.emit)

        self.pluginRegisterSettings([("regexText",
                                      self.__regexLoadJobsEditBox.text,
                                      self.__regexLoadJobsEditBox.setText),
                                     ("jobs",
                                      self.getJobIds,
                                      self.restoreJobIds),
                                     ("columnVisibility",
                                      self.jobMonitor.getColumnVisibility,
                                      self.jobMonitor.setColumnVisibility),
                                     ("columnWidths",
                                      self.jobMonitor.getColumnWidths,
                                      self.jobMonitor.setColumnWidths),
                                     ("grpDependentCb",
                                      self.getGrpDependent,
                                      self.setGrpDependent),
                                     ("autoLoadMineCb",
                                      self.getAutoLoadMine,
                                      self.setAutoLoadMine)
                                     ("columnOrder",
                                      self.jobMonitor.getColumnOrder,
                                      self.jobMonitor.setColumnOrder)])

    def addJob(self, object):
        if cuegui.Utils.isProc(object):
            object = cuegui.Utils.findJob(object.data.job_name)
        elif not cuegui.Utils.isJob(object):
            return
        self.jobMonitor.addJob(object, loading_from_config=True)
        self.raise_()

    def getJobIds(self):
        return list(map(opencue.id, self.jobMonitor.getJobProxies()))

    def restoreJobIds(self, jobIds):
        for jobId in jobIds:
            try:
                self.jobMonitor.addJob(jobId)
            except opencue.EntityNotFoundException as e:
                logger.warning("Unable to load previously loaded job since "
                               "it was moved to the historical "
                               "database: %s" % jobId)

    def pluginRestoreState(self, settings):
        """Called on plugin start with any previously saved state.
        @param settings: Last state of the plugin instance
        @type  settings: any"""
        if isinstance(settings, dict):
            cuegui.AbstractDockWidget.AbstractDockWidget.pluginRestoreState(self, settings)

        elif settings:
            # old method that needs to go away
            if len(settings) >= 1:
                self.__regexLoadJobsEditBox.setText(settings[0])
            if len(settings) >= 2 and settings[1]:
                for jobId in settings[1]:
                    try:
                        self.jobMonitor.addJob(jobId)
                    except opencue.EntityNotFoundException as e:
                        logger.warning("Unable to load previously loaded job since"
                                       "it was moved to the historical "
                                       "database: %s" % jobId)

    def _regexLoadJobsSetup(self, layout):
        """Selects jobs by name substring.
        Requires: self._regexLoadJobsHandle() and class JobRegexLoadEditBox
        @param layout: The layout that the widgets will be placed in
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Load:")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(btn)
        btn.clicked.connect(self._regexLoadJobsHandle)

        self.__regexLoadJobsEditBox = JobRegexLoadEditBox(self)
        layout.addWidget(self.__regexLoadJobsEditBox)
        self.__regexLoadJobsEditBox.returnPressed.connect(self._regexLoadJobsHandle)

    def _loadFinishedJobsSetup(self, layout):
        """Ensures that when querying jobs that finished jobs are included.
        Requires: self._regexLoadJobsHandle() and class JobLoadFinishedCheckBox
        @param layout: The layout that the widgets will be placed in
        @type  layout: QLayout"""
        self.__loadFinishedJobsCheckBox = JobLoadFinishedCheckBox(self)
        layout.addWidget(self.__loadFinishedJobsCheckBox)
        self.__loadFinishedJobsCheckBox.stateChanged.connect(self._regexLoadJobsHandle)

    def _regexLoadJobsHandle(self):
        """This will select all jobs that have a name that contain the substring
        in self.__regexLoadJobsEditBox.text() and scroll to the first match"""
        substring = str(self.__regexLoadJobsEditBox.text()).strip()
        load_finished_jobs = self.__loadFinishedJobsCheckBox.isChecked()

        if cuegui.Utils.isStringId(substring):
            # If a uuid is provided, load it
            self.jobMonitor.addJob(substring)
        elif load_finished_jobs or re.search("^([a-z0-9_]+)\-([a-z0-9\.]+)\-", substring, re.IGNORECASE):
            # If show and shot is provided, or if "load finished" checkbox is checked, load all jobs
            for job in opencue.api.getJobs(substr=[substring], include_finished=True):
                self.jobMonitor.addJob(job)
        else:
            # Otherwise, just load current matching jobs
            for job in opencue.api.getJobs(regex=[substring]):
                self.jobMonitor.addJob(job)

    def getGrpDependent(self):
        return bool(self.grpDependentCb.isChecked())

    def setGrpDependent(self, state):
        self.grpDependentCb.setChecked(bool(state))

    def getAutoLoadMine(self):
        return bool(self.autoLoadMineCb.isChecked())

    def setAutoLoadMine(self, state):
        self.autoLoadMineCb.setChecked(bool(state))

    def _buttonSetup(self, layout):
        clearButton = QtWidgets.QPushButton("Clr")
        clearButton.setFocusPolicy(QtCore.Qt.NoFocus)
        clearButton.setFixedWidth(24)
        layout.addWidget(clearButton)
        clearButton.clicked.connect(self.__regexLoadJobsEditBox.actionClear)

        spacer = QtWidgets.QWidget()
        spacer.setFixedWidth(20)
        layout.addWidget(spacer)

        self.autoLoadMineCb = QtWidgets.QCheckBox("Autoload Mine")
        self.autoLoadMineCb.setFocusPolicy(QtCore.Qt.NoFocus)
        self.autoLoadMineCb.setChecked(True)
        layout.addWidget(self.autoLoadMineCb)
        self.autoLoadMineCb.stateChanged.connect(self.jobMonitor.setLoadMine)


        self._loadFinishedJobsSetup(self.__toolbar)

        self.grpDependentCb = QtWidgets.QCheckBox("Group Dependent")
        self.grpDependentCb.setFocusPolicy(QtCore.Qt.NoFocus)
        self.grpDependentCb.setChecked(True)
        layout.addWidget(self.grpDependentCb)
        self.grpDependentCb.stateChanged.connect(self.jobMonitor.setGroupDependent)

        finishedButton = QtWidgets.QPushButton(QtGui.QIcon(":eject.png"), "Finished")
        finishedButton.setToolTip("Unmonitor finished jobs")
        finishedButton.setFocusPolicy(QtCore.Qt.NoFocus)
        finishedButton.setFlat(True)
        layout.addWidget(finishedButton)
        finishedButton.clicked.connect(self.jobMonitor.removeFinishedItems)

        allButton = QtWidgets.QPushButton(QtGui.QIcon(":eject.png"), "All")
        allButton.setToolTip("Unmonitor all jobs")
        allButton.setFocusPolicy(QtCore.Qt.NoFocus)
        allButton.setFlat(True)
        layout.addWidget(allButton)
        allButton.clicked.connect(self.jobMonitor.removeAllItems)

        removeSelectedButton = QtWidgets.QPushButton(QtGui.QIcon(":eject.png"), "")
        removeSelectedButton.setToolTip("Unmonitor selected jobs")
        removeSelectedButton.setFocusPolicy(QtCore.Qt.NoFocus)
        removeSelectedButton.setFlat(True)
        layout.addWidget(removeSelectedButton)
        removeSelectedButton.clicked.connect(self.jobMonitor.actionRemoveSelectedItems)

        eatSelectedButton = QtWidgets.QPushButton(QtGui.QIcon(":eat.png"), "")
        eatSelectedButton.setToolTip("Eats all dead frames for selected jobs")
        eatSelectedButton.setFocusPolicy(QtCore.Qt.NoFocus)
        eatSelectedButton.setFlat(True)
        layout.addWidget(eatSelectedButton)
        eatSelectedButton.clicked.connect(self.jobMonitor.actionEatSelectedItems)

        retryButton = QtWidgets.QPushButton(QtGui.QIcon(":retry.png"), "")
        retryButton.setToolTip("Retries all dead frames for selected jobs")
        retryButton.setFocusPolicy(QtCore.Qt.NoFocus)
        retryButton.setFlat(True)
        layout.addWidget(retryButton)
        retryButton.clicked.connect(self.jobMonitor.actionRetrySelectedItems)

        killButton = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "")
        killButton.setToolTip("Kill selected jobs")
        killButton.setFocusPolicy(QtCore.Qt.NoFocus)
        killButton.setFlat(True)
        layout.addWidget(killButton)
        killButton.clicked.connect(self.jobMonitor.actionKillSelectedItems)

        pauseButton = QtWidgets.QPushButton(QtGui.QIcon(":pause.png"), "")
        pauseButton.setToolTip("Pause selected jobs")
        pauseButton.setFocusPolicy(QtCore.Qt.NoFocus)
        pauseButton.setFlat(True)
        layout.addWidget(pauseButton)
        pauseButton.clicked.connect(self.jobMonitor.actionPauseSelectedItems)

        unpauseButton = QtWidgets.QPushButton(QtGui.QIcon(":unpause.png"), "")
        unpauseButton.setToolTip("Unpause selected jobs")
        unpauseButton.setFocusPolicy(QtCore.Qt.NoFocus)
        unpauseButton.setFlat(True)
        layout.addWidget(unpauseButton)
        unpauseButton.clicked.connect(self.jobMonitor.actionResumeSelectedItems)

class JobLoadFinishedCheckBox(QtWidgets.QCheckBox):
    def __init__(self, parent):
        QtWidgets.QCheckBox.__init__(self, 'Load Finished')
        self.parent = weakref.proxy(parent)

        toolTip = 'This ensures that all finished jobs<br>' \
                  'get included when querying the Cuebot server'

        self.setToolTip(toolTip)

class JobRegexLoadEditBox(QtWidgets.QLineEdit):
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
        self.setText("")

    def _actionLoad(self):
        self.returnPressed.emit()

    def toggleReadOnly(self):
        self.setReadOnly(not self.isReadOnly())

    def keyPressEvent(self, event):
        """Let the parent handle any space key presses"""
        if event.key() == QtCore.Qt.Key_Space:
            self.parent.keyPressEvent(event)
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)
