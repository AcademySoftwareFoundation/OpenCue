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


"""Plugin for general administration of the show/job hierarchy."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
import os
import re
import weakref

from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets

import opencue

import cuegui.AbstractDockWidget
import cuegui.Action
import cuegui.Constants
import cuegui.CueJobMonitorTree
import cuegui.CueStateBarWidget
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

PLUGIN_NAME = "Monitor Cue"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "An improved tree listing of shows, groups and jobs"
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "MonitorCueDockWidget"


class MonitorCueDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """Plugin for general administration of the show/job hierarchy."""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__showMenuActions = None

        self.__monitorCue = cuegui.CueJobMonitorTree.CueJobMonitorTree(self)
        self.__toolbar = QtWidgets.QToolBar(self)
        self.__showMenuSetup()
        self.__expandAllSetup()
        self.__collapseAllSetup()
        self.__toolbar.addSeparator()
        self.__selectJobsSetup()
        self.__buttonSetup(self.__toolbar)
        spacer = QtWidgets.QLabel(self)
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                             QtWidgets.QSizePolicy.Ignored)
        self.__toolbar.addWidget(spacer)
        self.__jobSelectedSetup()

        self.layout().addWidget(self.__toolbar)
        self.__hlayout = QtWidgets.QHBoxLayout()
        self.__cueStateBarSetup(self.__hlayout)
        self.__hlayout.addWidget(self.__monitorCue)

        self.layout().addLayout(self.__hlayout)

        self.__monitorCue.view_object.connect(self.app.view_object.emit)

        self.pluginRegisterSettings([("shows",
                                      self.__monitorCue.getShowNames,
                                      self.addShows),
                                      ("columnVisibility",
                                       self.__monitorCue.getColumnVisibility,
                                       self.__monitorCue.setColumnVisibility),
                                      ("columnWidths",
                                       self.__monitorCue.getColumnWidths,
                                       self.__monitorCue.setColumnWidths),
                                       ("columnOrder",
                                       self.__monitorCue.getColumnOrder,
                                       self.__monitorCue.setColumnOrder)])

        self.addShows([os.getenv('SHOW')])

        # pylint: disable=protected-access
        QtWidgets.QShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key_Space),
            self,
            self.__monitorCue._update
        )
        # pylint: enable=protected-access

    def __cueStateBarSetup(self, layout):
        cueStateBarEnabled = self.app.settings.value("CueStateBar", False)
        if cueStateBarEnabled:
            self.__cueStateBar = cuegui.CueStateBarWidget.CueStateBarWidget(self.__monitorCue, self)
            layout.addWidget(self.__cueStateBar)

    def __expandAllSetup(self):
        """Sets up the expand all button"""
        btn = QtWidgets.QPushButton()
        self.__toolbar.addWidget(btn)
        btn.setIcon(QtGui.QIcon(":down.png"))
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setToolTip("Expand all groups")
        btn.clicked.connect(self.__monitorCue.expandAll)  # pylint: disable=no-member

    def __collapseAllSetup(self):
        """Sets up the collapse all button"""
        btn = QtWidgets.QPushButton()
        self.__toolbar.addWidget(btn)
        btn.setIcon(QtGui.QIcon(":up.png"))
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setToolTip("Collapse all groups")
        btn.clicked.connect(self.__monitorCue.collapseAll)  # pylint: disable=no-member

    def __buttonSetup(self, layout):
        btn = QtWidgets.QPushButton(QtGui.QIcon(":eat.png"), "")
        btn.setToolTip("Eats all dead frames for selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        btn.clicked.connect(self.__monitorCue.actionEatSelectedItems)  # pylint: disable=no-member

        btn = QtWidgets.QPushButton(QtGui.QIcon(":retry.png"), "")
        btn.setToolTip("Retries all dead frames for selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        btn.clicked.connect(self.__monitorCue.actionRetrySelectedItems)  # pylint: disable=no-member

        btn = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "")
        btn.setToolTip("Kill selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        btn.clicked.connect(self.__monitorCue.actionKillSelectedItems)  # pylint: disable=no-member

        btn = QtWidgets.QPushButton(QtGui.QIcon(":pause.png"), "")
        btn.setToolTip("Pause selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        btn.clicked.connect(self.__monitorCue.actionPauseSelectedItems)  # pylint: disable=no-member

        btn = QtWidgets.QPushButton(QtGui.QIcon(":unpause.png"), "")
        btn.setToolTip("Unpause selected jobs")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        btn.clicked.connect(self.__monitorCue.actionResumeSelectedItems)  # pylint: disable=no-member

        btn = QtWidgets.QPushButton(QtGui.QIcon(":reload.png"), "")
        btn.setToolTip("Refresh monitor cue")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setFlat(True)
        layout.addWidget(btn)
        # pylint: disable=protected-access
        btn.clicked.connect(self.__monitorCue._update)
        # pylint: enable=protected-access



    ################################################################################
    # Show selection menu
    ################################################################################

    def __showMenuSetup(self):
        """Sets up the show selection menu"""
        self.__showMenuBtn = QtWidgets.QPushButton("Shows ",self)
        self.__showMenuBtn.setIcon(QtGui.QIcon(":show.png"))
        self.__showMenuBtn.pressed.connect(self.__showMenuCheck)  # pylint: disable=no-member
        self.__toolbar.addWidget(self.__showMenuBtn)

        self.__showMenu = QtWidgets.QMenu(self)
        self.__showMenuBtn.setMenu(self.__showMenu)
        self.__showMenuBtn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__showMenu.setFont(cuegui.Constants.STANDARD_FONT)
        self.__showMenu.triggered.connect(self.__showMenuHandle)  # pylint: disable=no-member
        self.app.facility_changed.connect(self.__showMenuUpdate)

        self.__showMenuUpdate()

    def __showMenuHandle(self, action):
        """Handles adding or removing shows via the show selection menu
        @type  action: QAction
        @param action: Click action"""
        if action.text() == 'All Shows':
            try:
                shows = sorted([show.name() for show in opencue.api.getActiveShows()])
            except opencue.CueException as e:
                logger.critical(e)
                shows = []
            for show in shows:
                self.__monitorCue.addShow(show)
            self.__showMenuUpdate()
        elif action.text() == 'Clear':
            self.__monitorCue.removeAllShows()
            self.__showMenuUpdate()
        elif action.isChecked():
            self.__monitorCue.addShow(action.text())
        else:
            self.__monitorCue.removeShow(action.text())

    def __showMenuUpdate(self):
        """Updates the show selection menu with the known shows"""
        self.__showMenu.clear()
        self.__showMenuActions = {}

        action = QtWidgets.QAction('All Shows', self.__showMenu)
        self.__showMenu.addAction(action)
        self.__showMenuActions['All Shows'] = action

        action = QtWidgets.QAction('Clear', self.__showMenu)
        self.__showMenu.addAction(action)
        self.__showMenuActions['Clear'] = action
        self.__showMenu.addSeparator()

        try:
            shows = sorted([show.name() for show in opencue.api.getActiveShows()])
        except opencue.exception.CueException as e:
            logger.critical(e)
            shows = []

        monitored = [show.name() for show in self.__monitorCue.getShows()]

        for show in shows:
            action = QtWidgets.QAction(show, self.__showMenu)
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

        select_btn = QtWidgets.QPushButton("Select:")
        select_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__toolbar.addWidget(select_btn)
        select_btn.clicked.connect(self.__selectJobsHandle)  # pylint: disable=no-member

        self._selectJobsEditBox = JobSelectEditBox(self)
        self.__toolbar.addWidget(self._selectJobsEditBox)
        self._selectJobsEditBox.returnPressed.connect(self.__selectJobsHandle)  # pylint: disable=no-member

        clear_btn = QtWidgets.QPushButton("Clr")
        clear_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        clear_btn.setFixedWidth(24)
        self.__toolbar.addWidget(clear_btn)
        clear_btn.clicked.connect(self._selectJobsEditBox.actionClear)  # pylint: disable=no-member

        mine_btn = QtWidgets.QPushButton("selectMine")
        mine_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        mine_btn.setFixedWidth(70)
        self.__toolbar.addWidget(mine_btn)
        mine_btn.clicked.connect(self.__selectJobsHandleMine)  # pylint: disable=no-member

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
                                          QtWidgets.QAbstractItemView.PositionAtTop)

    def __selectJobsHandleMine(self):
        self.__selectJobsHandle("-%s_" % cuegui.Utils.getUsername())

################################################################################
# Displays the last selected job name in a text box
################################################################################
    def __jobSelectedSetup(self):
        """Sets up the selected job edit box"""
        self.__jobSelectedLineEdit = QtWidgets.QLineEdit()
        self.__jobSelectedLineEdit.setMaximumWidth(300)
        self.__jobSelectedLineEdit.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__jobSelectedLineEdit.setFont(cuegui.Constants.STANDARD_FONT)
        self.__toolbar.addWidget(self.__jobSelectedLineEdit)
        self.__monitorCue.single_click.connect(self.__jobSelectedHandle)

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
        """Adds a list of shows to be monitored."""
        for show in shows:
            if show in self.__showMenuActions:
                self.__monitorCue.addShow(show, False)
                self.__showMenuActions[show].setChecked(True)

    def pluginRestoreState(self, saved_settings):
        """Called on plugin start with any previously saved state.
        @param saved_settings: Last state of the plugin instance
        @type  saved_settings: any"""
        cuegui.AbstractDockWidget.AbstractDockWidget.pluginRestoreState(self, saved_settings)

        # pylint: disable=protected-access
        self.__monitorCue._update()
        # pylint: enable=protected-access
        QtCore.QTimer.singleShot(1000, self.__monitorCue.expandAll)


class JobSelectEditBox(QtWidgets.QLineEdit):
    """An edit box for selecting matching jobs."""

    def __init__(self, parent):
        QtWidgets.QLineEdit.__init__(self)
        self.parent = weakref.proxy(parent)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setFont(cuegui.Constants.STANDARD_FONT)
        self.setFixedWidth(200)
        self.setMaxLength(100)

    def contextMenuEvent(self, event):
        """Called when selection box is right clicked
        @type  event: QEvent
        @param event: Click QEvent"""
        menu = QtWidgets.QMenu(self)

        menu.addAction(cuegui.Action.create(self,
                                            "Select matching jobs (Enter)",
                                            "Select matching jobs",
                                            self._actionSelect))

        menu.addAction(cuegui.Action.create(self,
                                            "Clear",
                                            "Clear text",
                                            self.actionClear))

        menu.exec_(QtCore.QPoint(event.globalX(), event.globalY()))

    def actionClear(self):
        """Clears the edit box"""
        self.setText("")

    def _actionSelect(self):
        """Signals that a return was pressed"""
        self.returnPressed.emit()  # pylint: disable=no-member

    def keyPressEvent(self, event):
        """Let the parent handle any space key presses"""
        if event.key() == QtCore.Qt.Key_Space:
            self.parent.keyPressEvent(event)
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)
