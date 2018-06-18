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

PLUGIN_NAME = "Monitor Cue"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An improved tree listing of shows, groups and jobs"
PLUGIN_REQUIRES = "CueCommander3"
PLUGIN_PROVIDES = "MonitorCueDockWidget"

class MonitorCueDockWidget(Cue3Gui.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""
    def __init__(self, parent):
        Cue3Gui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__monitorCue = Cue3Gui.CueJobMonitorTree(self)
        self.__toolbar = QtGui.QToolBar(self)
        self.__showMenuSetup()
        self.__expandAllSetup()
        self.__collapseAllSetup()
        self.__toolbar.addSeparator()
        self.__selectJobsSetup()
        self.__buttonSetup(self.__toolbar)
        spacer = QtGui.QLabel(self)
        spacer.setSizePolicy(QtGui.QSizePolicy.Expanding,
                             QtGui.QSizePolicy.Ignored)
        self.__toolbar.addWidget(spacer)
        self.__jobSelectedSetup()

        self.layout().addWidget(self.__toolbar)
        self.__hlayout = QtGui.QHBoxLayout()
        self.__cueStateBarSetup(self.__hlayout)
        self.__hlayout.addWidget(self.__monitorCue)

        self.layout().addLayout(self.__hlayout)

        QtCore.QObject.connect(self.__monitorCue,
                               QtCore.SIGNAL('view_object(PyQt_PyObject)'),
                               QtGui.qApp,
                               QtCore.SIGNAL('view_object(PyQt_PyObject)'))

        self.pluginRegisterSettings([("shows",
                                      self.__monitorCue.getShowNames,
                                      self.addShows),
                                      ("columnVisibility",
                                       self.__monitorCue.getColumnVisibility,
                                       self.__monitorCue.setColumnVisibility),
                                      ("columnWidths",
                                       self.__monitorCue.getColumnWidths,
                                       self.__monitorCue.setColumnWidths)])

        self.addShows([os.getenv('SHOW')])

    def __cueStateBarSetup(self, layout):
        if QtGui.qApp.settings.value("CueStateBar",
                                     QtCore.QVariant(False)).toBool():
            self.__cueStateBar = Cue3Gui.CueStateBarWidget(self.__monitorCue,
                                                           self)
            layout.addWidget(self.__cueStateBar)

    def __expandAllSetup(self):
        """Sets up the expand all button"""
        btn = QtGui.QPushButton()
        self.__toolbar.addWidget(btn)
        btn.setIcon(QtGui.QIcon(":down.png"))
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setToolTip("Expand all groups")
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.expandAll)

    def __collapseAllSetup(self):
        """Sets up the collapse all button"""
        btn = QtGui.QPushButton()
        self.__toolbar.addWidget(btn)
        btn.setIcon(QtGui.QIcon(":up.png"))
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setToolTip("Collapse all groups")
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.collapseAll)

    def __buttonSetup(self, layout):
        btn = QtGui.QPushButton(QtGui.QIcon(":eat.png"), "")
        btn.setToolTip("Eats all dead frames for selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.actionEatSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":retry.png"), "")
        btn.setToolTip("Retries all dead frames for selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.actionRetrySelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":kill.png"), "")
        btn.setToolTip("Kill selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.actionKillSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":pause.png"), "")
        btn.setToolTip("Pause selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.actionPauseSelectedItems)

        btn = QtGui.QPushButton(QtGui.QIcon(":unpause.png"), "")
        btn.setToolTip("Unpause selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__monitorCue.actionResumeSelectedItems)


################################################################################
# Show selection menu
################################################################################
    def __showMenuSetup(self):
        """Sets up the show selection menu"""
        self.__showMenuBtn = QtGui.QPushButton("Shows ",self)
        self.__showMenuBtn.setIcon(QtGui.QIcon(":show.png"))
        QtCore.QObject.connect(self.__showMenuBtn,
                               QtCore.SIGNAL("pressed()"),
                               self.__showMenuCheck)
        self.__toolbar.addWidget(self.__showMenuBtn)

        self.__showMenu = QtGui.QMenu(self)
        self.__showMenuBtn.setMenu(self.__showMenu)
        self.__showMenuBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__showMenu.setFont(Cue3Gui.Constants.STANDARD_FONT)
        QtCore.QObject.connect(self.__showMenu,
                               QtCore.SIGNAL("triggered(QAction*)"),
                               self.__showMenuHandle)
        QtCore.QObject.connect(QtGui.qApp,
                               QtCore.SIGNAL('facility_changed()'),
                               self.__showMenuUpdate)

        self.__showMenuUpdate()

    def __showMenuHandle(self, action):
        """Handles adding or removing shows via the show selection menu
        @type  action: QAction
        @param action: Click action"""
        if action.isChecked():
            self.__monitorCue.addShow(action.text())
        else:
            self.__monitorCue.removeShow(action.text())

    def __showMenuUpdate(self):
        """Updates the show selection menu with the known shows"""
        self.__showMenu.clear()
        self.__showMenuActions = {}

        try:
            shows = sorted([show.name() for show in Cue3.getActiveShows()])
        except Exception, e:
            logger.critical(e)
            shows = []

        monitored = [show.name() for show in self.__monitorCue.getShows()]

        for show in shows:
            action = QtGui.QAction(show, self.__showMenu)
            action.setCheckable(True)
            if show in monitored:
                action.setChecked(True)
            self.__showMenu.addAction(action)
            self.__showMenuActions[show] = action

    def __showMenuCheck(self):
        """Populate the list of shows if it is empty"""
        if not self.__showMenuActions:
            self.__showMenuUpdate()

################################################################################
# Select jobs by substring
################################################################################
    def __selectJobsSetup(self):
        """Selects jobs by name substring.
        Requires: self._selectJobsHandle() and class JobSelectEditBox"""

        btn = QtGui.QPushButton("Select:")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__toolbar.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__selectJobsHandle)

        self._selectJobsEditBox = JobSelectEditBox(self)
        self.__toolbar.addWidget(self._selectJobsEditBox)
        QtCore.QObject.connect(self._selectJobsEditBox,
                               QtCore.SIGNAL('returnPressed()'),
                               self.__selectJobsHandle)

        btn = QtGui.QPushButton("Clr")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(24)
        self.__toolbar.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self._selectJobsEditBox.actionClear)

        btn = QtGui.QPushButton("selectMine")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFixedWidth(70)
        self.__toolbar.addWidget(btn)
        QtCore.QObject.connect(btn,
                               QtCore.SIGNAL('clicked()'),
                               self.__selectJobsHandleMine)

    def __selectJobsHandle(self, value = None):
        """This will select all jobs that have a name that contain the substring
        in self._selectJobsEditBox.text() and scroll to the first match"""

        if not value:
            value = str(self._selectJobsEditBox.text())

        if value:
            self.__monitorCue.clearSelection()

            # Allow simple substring searching as well as full regex
            if not re.search('[^A-Za-z0-9_.|-]', value):
                value = ".*%s.*" % value.replace("|", ".*|.*")

            items = self.__monitorCue.findItems(value,
                                                QtCore.Qt.MatchRegExp |
                                                QtCore.Qt.MatchWrap |
                                                QtCore.Qt.MatchRecursive,
                                                0)

            if items:
                # Select and show all found items
                for item in items:
                    item.setSelected(True)
                    if not item.isExpanded():
                        parent = item.parent()
                        while parent:
                            parent.setExpanded(True)
                            parent = parent.parent()

                # Scroll to the first item
                self.__monitorCue.scrollToItem(items[0],
                                          QtGui.QAbstractItemView.PositionAtTop)

    def __selectJobsHandleMine(self):
        self.__selectJobsHandle("-%s_" % Cue3Gui.Utils.getUsername())

################################################################################
# Displays the last selected job name in a text box
################################################################################
    def __jobSelectedSetup(self):
        """Sets up the selected job edit box"""
        self.__jobSelectedLineEdit = QtGui.QLineEdit()
        self.__jobSelectedLineEdit.setMaximumWidth(300)
        self.__jobSelectedLineEdit.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__jobSelectedLineEdit.setFont(Cue3Gui.Constants.STANDARD_FONT)
        self.__toolbar.addWidget(self.__jobSelectedLineEdit)
        QtCore.QObject.connect(self.__monitorCue,
                               QtCore.SIGNAL('single_click(PyQt_PyObject)'),
                               self.__jobSelectedHandle)

    def __jobSelectedHandle(self, job):
        """Updates the selected job edit box with the provided job
        @type  job: job
        @param job: The selected job object"""
        if job:
            self.__jobSelectedLineEdit.setText(job.name())
        else:
            self.__jobSelectedLineEdit.setText("")
################################################################################
    def addShows(self, shows):
        for show in shows:
            if self.__showMenuActions.has_key(show):
                self.__monitorCue.addShow(show, False)
                self.__showMenuActions[show].setChecked(True)

    def pluginRestoreState(self, settings):
        """Called on plugin start with any previously saved state.
        @param settings: Last state of the plugin instance
        @type  settings: any"""
        Cue3Gui.AbstractDockWidget.pluginRestoreState(self, settings)

        self.__monitorCue._update()
        QtCore.QTimer.singleShot(1000, self.__monitorCue.expandAll)

class JobSelectEditBox(QtGui.QLineEdit):
    """An edit box intended for selecting matching jobs"""
    def __init__(self, parent):
        QtGui.QLineEdit.__init__(self)
        self.parent = weakref.proxy(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFont(Cue3Gui.Constants.STANDARD_FONT)
        self.setFixedWidth(200)
        self.setMaxLength(100)

    def contextMenuEvent(self, event):
        """Called when selection box is right clicked
        @type  event: QEvent
        @param event: Click QEvent"""
        menu = QtGui.QMenu(self)

        menu.addAction(Cue3Gui.Action.create(self,
                                             "Select matching jobs (Enter)",
                                             "Select matching jobs",
                                             self._actionSelect))

        menu.addAction(Cue3Gui.Action.create(self,
                                             "Clear",
                                             "Clear text",
                                             self.actionClear))

        menu.exec_(QtCore.QPoint(event.globalX(), event.globalY()))

    def actionClear(self):
        """Clears the edit box"""
        self.setText("")

    def _actionSelect(self):
        """Signals that a return was pressed"""
        self.emit(QtCore.SIGNAL("returnPressed()"))

    def keyPressEvent(self, event):
        """Let the parent handle any space key presses"""
        if event.key() == QtCore.Qt.Key_Space:
            self.parent.keyPressEvent(event)
        else:
            QtGui.QLineEdit.keyPressEvent(self, event)
