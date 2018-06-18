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


import os
import re
import time
import weakref
import Cue3Gui
import Cue3

from PyQt4 import QtGui, QtCore

logger = Cue3Gui.Logger.getLogger(__file__)

PLUGIN_NAME = "Monitor Jobs"
PLUGIN_CATEGORY = "Cuetopia"
PLUGIN_DESCRIPTION = "Monitors a list of jobs"
PLUGIN_PROVIDES = "MonitorJobsDockWidget"

class MonitorJobsDockWidget(Cue3Gui.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        Cue3Gui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.jobMonitor = Cue3Gui.JobMonitorTree(self)

        self.__toolbar = QtGui.QToolBar(self)
        self._regexLoadJobsSetup(self.__toolbar)
        #self.__toolbar.addSeparator()
        self._buttonSetup(self.__toolbar)

        self.layout().addWidget(self.__toolbar)
        self.layout().addWidget(self.jobMonitor)

        #Signals in:
        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL('view_object(PyQt_PyObject)'), self.addJob)
        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL('facility_changed()'), self.jobMonitor.removeAllItems)
        #Signals out:
        QtCore.QObject.connect(self.jobMonitor, QtCore.SIGNAL('view_object(PyQt_PyObject)'), self, QtCore.SIGNAL('view_object(PyQt_PyObject)'))

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
                                      self.jobMonitor.setColumnWidths)])

    def addJob(self, object):
        if Cue3Gui.Utils.isProc(object):
            object = Cue3Gui.Utils.findJob(object.data.jobName)
        elif not Cue3Gui.Utils.isJob(object):
            return
        self.jobMonitor.addJob(object)
        self.raise_()

    def getJobIds(self):
        return map(Cue3.id, self.jobMonitor.getJobProxies())

    def restoreJobIds(self, jobIds):
        for jobId in jobIds:
            try:
                self.jobMonitor.addJob(jobId)
            except Cue3.EntityNotFoundException, e:
                logger.warning("Unable to load previously loaded job since "
                               "it was moved to the historical "
                               "database: %s" % jobId)

    def pluginRestoreState(self, settings):
        """Called on plugin start with any previously saved state.
        @param settings: Last state of the plugin instance
        @type  settings: any"""
        if isinstance(settings, dict):
            Cue3Gui.AbstractDockWidget.pluginRestoreState(self, settings)

        elif settings:
            # old method that needs to go away
            if len(settings) >= 1:
                self.__regexLoadJobsEditBox.setText(settings[0])
            if len(settings) >= 2 and settings[1]:
                for jobId in settings[1]:
                    try:
                        self.jobMonitor.addJob(jobId)
                    except Cue3.EntityNotFoundException, e:
                        logger.warning("Unable to load previously loaded job since"
                                       "it was moved to the historical "
                                       "database: %s" % jobId)

    def _regexLoadJobsSetup(self, layout):
        """Selects jobs by name substring.
        Requires: self._regexLoadJobsHandle() and class JobRegexLoadEditBox
        @param layout: The layout that the widgets will be placed in
        @type  layout: QLayout"""
        btn = QtGui.QPushButton("Load:")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self._regexLoadJobsHandle)

        self.__regexLoadJobsEditBox = JobRegexLoadEditBox(self)
        layout.addWidget(self.__regexLoadJobsEditBox)
        QtCore.QObject.connect(self.__regexLoadJobsEditBox, QtCore.SIGNAL('returnPressed()'), self._regexLoadJobsHandle)

    def _regexLoadJobsHandle(self):
        """This will select all jobs that have a name that contain the substring
        in self.__regexLoadJobsEditBox.text() and scroll to the first match"""
        substring = str(self.__regexLoadJobsEditBox.text()).strip()

        if not substring:
            return

        if Cue3Gui.Utils.isStringId(substring):
            # If a uuid is provided, load it
            self.jobMonitor.addJob(substring)
        elif re.search("^([a-z0-9]+)\-([a-z0-9\.]+)\-", substring, re.IGNORECASE):
            # If show and shot is provided, load all finished jobs
            jobSearch = Cue3.JobSearch(regex=[substring])
            jobSearch.includeFinished = True
            for job in Cue3.Cuebot.Proxy.getJobs(jobSearch):
                self.jobMonitor.addJob(job)
        else:
            # Otherwise, just load current matching jobs
            for job in Cue3.getJobs(regex=[substring]):
                self.jobMonitor.addJob(job)

    def _buttonSetup(self, layout):
        btn = QtGui.QPushButton("Clr")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(24)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.__regexLoadJobsEditBox.actionClear)

        spacer = QtGui.QWidget()
        spacer.setFixedWidth(20)
        layout.addWidget(spacer)

        btn = QtGui.QCheckBox("Autoload Mine")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setChecked(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('stateChanged(int)'), self.jobMonitor.setLoadMine)

        btn = QtGui.QPushButton(QtGui.QIcon(":eject.png"), "Finished")
        btn.setToolTip("Unmonitor finished jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.removeFinishedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":eject.png"), "All")
        btn.setToolTip("Unmonitor all jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.removeAllItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":eject.png"), "")
        btn.setToolTip("Unmonitor selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.actionRemoveSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":eat.png"), "")
        btn.setToolTip("Eats all dead frames for selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.actionEatSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":retry.png"), "")
        btn.setToolTip("Retries all dead frames for selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.actionRetrySelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":kill.png"), "")
        btn.setToolTip("Kill selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.actionKillSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":pause.png"), "")
        btn.setToolTip("Pause selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.actionPauseSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":unpause.png"), "")
        btn.setToolTip("Unpause selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn, QtCore.SIGNAL('clicked()'), self.jobMonitor.actionResumeSelectedItems)

class JobRegexLoadEditBox(QtGui.QLineEdit):
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self)
        self.parent = weakref.proxy(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFont(Cue3Gui.Constants.STANDARD_FONT)
        self.setFixedWidth(200)
        self.setMaxLength(200)

        toolTip = 'This accepts regular expression.<br>' \
                  'Use .* to match any string<br>' \
                  'Example searches:<br>' \
                  '&nbsp;&nbsp;&nbsp;&nbsp;sm2.*comp<br>' \
                  '&nbsp;&nbsp;&nbsp;&nbsp;sm2-(madkisson|chung).*comp<br>' \
                  'Jobs finished for 3 days will no longer be available in cuetopia.<br>' \
                  'Load your finished jobs with at least: show-shot-username_'

        self.setToolTip(QtCore.QString(toolTip))

    def contextMenuEvent(self, e):
        menu = QtGui.QMenu(self)

        menu.addAction(Cue3Gui.Action.create(self,
                                             "Load matching jobs (Enter)",
                                             "Load matching jobs",
                                             self._actionLoad))

        menu.addAction(Cue3Gui.Action.create(self,
                                             "Lock/Unlock edit box",
                                             "Lock/Unlock edit box",
                                             self.toggleReadOnly))

        menu.addAction(Cue3Gui.Action.create(self,
                                             "Clear",
                                             "Clear text",
                                             self.actionClear))

        menu.exec_(QtCore.QPoint(e.globalX(), e.globalY()))

    def actionClear(self):
        self.setText("")

    def _actionLoad(self):
        self.emit(QtCore.SIGNAL("returnPressed()"))

    def toggleReadOnly(self):
        self.setReadOnly(not self.isReadOnly())

    def keyPressEvent(self, event):
        """Let the parent handle any space key presses"""
        if event.key() == QtCore.Qt.Key_Space:
            self.parent.keyPressEvent(event)
        else:
            QtGui.QLineEdit.keyPressEvent(self, event)
