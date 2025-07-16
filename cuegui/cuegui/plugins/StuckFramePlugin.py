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


"""Plugin for managing stuck frames."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import map
from future.utils import iteritems
import datetime
import getpass
import os
import re
import signal
import socket
import time
import yaml

from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets

import opencue.wrappers.frame

import cuegui.AbstractDockWidget
import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Action
import cuegui.Constants
import cuegui.JobMonitorTree
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Style
import cuegui.Utils

logger = cuegui.Logger.getLogger(__file__)

PLUGIN_NAME = "Stuck Frame"
PLUGIN_CATEGORY = "Cuecommander"
PLUGIN_DESCRIPTION = "Work with stuck frames."
PLUGIN_REQUIRES = "CueCommander"
PLUGIN_PROVIDES = "StuckWidget"
CUE_SLEEP = 30

NAME_COLUMN = 0
COMMENT_COLUMN = 1
FRAME_COLUMN = 2
LLU_COLUMN = 3
RUNTIME_COLUMN = 4
LASTLINE_COLUMN = 7
DEFAULT_FRAME_KILL_REASON = "Manual Frame Kill Request in Cuegui by " + getpass.getuser()

class StuckWidget(cuegui.AbstractDockWidget.AbstractDockWidget):
    """This builds what is displayed on the dock widget"""

    def __init__(self, parent):
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)
        self.__stuckWidget = StuckFrameWidget(self)
        self.layout().addWidget(self.__stuckWidget)

    def pluginSaveState(self):
        """Saves current state of the plugin and returns it as dict"""
        filters = self.__stuckWidget.getControls().getFilters()
        save = {}
        for frame_filter in filters:
            save[frame_filter.getServiceBoxText()] = [frame_filter.getRegexText(),
                                                        frame_filter.getTime(),
                                                        frame_filter.getMinLLu(),
                                                        frame_filter.getAvgCompTime(),
                                                        frame_filter.getRunTime(),
                                                        frame_filter.getEnabled().isChecked()]
        return save

    def pluginRestoreState(self, saved_settings):
        """Restores state based on the saved settings."""
        if saved_settings:
            if len(saved_settings) > 1:
                current_settings = saved_settings["All Other Types"]
                frame_filter = self.__stuckWidget.getControls().getFilters()[0]
                frame_filter.getServiceBox().setText("All Other Types")
                frame_filter.getRegex().setText(current_settings[0])
                frame_filter.getEnabled().setChecked(current_settings[5])
                frame_filter.getLLUFilter().setValue(current_settings[2])
                frame_filter.getPercentFilter().setValue(current_settings[1])
                frame_filter.getCompletionFilter().setValue(current_settings[3])
                frame_filter.getRunFilter().setValue(current_settings[4])
                top_filter = self.__stuckWidget.getControls().getFilters()[0]
            else:
                settings_text = "All (Click + to Add Specific Filter)"
                current_settings = saved_settings[settings_text]
                frame_filter = self.__stuckWidget.getControls().getFilters()[0]
                frame_filter.getServiceBox().setText(settings_text)
                frame_filter.getRegex().setText(current_settings[0])
                frame_filter.getEnabled().setChecked(current_settings[5])
                frame_filter.getLLUFilter().setValue(current_settings[2])
                frame_filter.getPercentFilter().setValue(current_settings[1])
                frame_filter.getCompletionFilter().setValue(current_settings[3])
                frame_filter.getRunFilter().setValue(current_settings[4])
                return

            for frame_filter in saved_settings.keys():
                if (not frame_filter == "All Other Types" and
                        not frame_filter == "All (Click + to Add Specific Filter)"):
                    current_settings = saved_settings[frame_filter]
                    new_filter = top_filter.addFilter()
                    new_filter.getServiceBox().setText(frame_filter)
                    new_filter.getRegex().setText(current_settings[0])
                    new_filter.getEnabled().setChecked(current_settings[5])
                    new_filter.getLLUFilter().setValue(current_settings[2])
                    new_filter.getPercentFilter().setValue(current_settings[1])
                    new_filter.getCompletionFilter().setValue(current_settings[3])
                    new_filter.getRunFilter().setValue(current_settings[4])
        return


class ShowCombo(QtWidgets.QComboBox):
    """Combobox with show names"""

    def __init__(self, selected="pipe", parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.refresh()
        self.setCurrentIndex(self.findText(selected))

    def refresh(self):
        """Refreshes the show list."""
        self.clear()
        shows = opencue.api.getActiveShows()
        shows.sort(key=lambda s: s.data.name)

        for show in shows:
            self.addItem(show.data.name, show)

    def getShow(self):
        """Returns show name."""
        return str(self.setCurrentText())


class StuckFrameControls(QtWidgets.QWidget):
    """
    A widget that contains all search options for stuck frames
    """

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.__current_show = opencue.api.findShow(os.getenv("SHOW", "pipe"))
        self.__show_combo = ShowCombo(self.__current_show.data.name, self)
        self.__show_label = QtWidgets.QLabel("Show:", self)
        self.__show_label.setToolTip("The show you want to find stuck frames for.")

        self.__clear_btn = QtWidgets.QPushButton("Clear")
        self.__clear_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__clear_btn.setMaximumWidth(150)
        self.__clear_btn.setMinimumWidth(150)

        self.__search_btn = QtWidgets.QPushButton("Refresh", self)
        self.__search_btn.setMinimumWidth(150)
        self.__search_btn.setMaximumWidth(150)
        self.__search_btn.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__auto_refresh_btn = QtWidgets.QCheckBox("Auto-refresh", self)
        self.__auto_refresh_btn.setToolTip("""Automatically get a new set of
                                            frames approximately every 30 minutes.""")
        self.__notification_btn = QtWidgets.QCheckBox("Notification", self)
        self.__notification_btn.setEnabled(False)
        self.__notification_btn.setToolTip("Get a notification when an auto-refresh has completed.")

        self.__progress = QtWidgets.QProgressBar(self)
        self.__progress.setRange(0, 1000)
        self.__progress.setMaximumWidth(150)
        self.__progress.setMinimumWidth(150)
        self.__progress.setMinimumHeight(20)
        self.__progress.setMaximumHeight(20)
        self.__progress.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__progressLabel = QtWidgets.QLabel(self)
        self.__progressLabel.setText("Progress:  ")

        self.__group_filters = QtWidgets.QGroupBox("Search Filters")

        controls = QtWidgets.QHBoxLayout()
        controls.addSpacing(10)
        controls.addWidget(self.__show_label)
        controls.addWidget(self.__show_combo)
        controls.addWidget(self.__search_btn)
        controls.addWidget(self.__clear_btn)
        controls.addWidget(self.__auto_refresh_btn)
        controls.addWidget(self.__notification_btn)
        controls.addStretch()
        controls.addWidget(self.__progressLabel)
        controls.addWidget(self.__progress)
        controls.addSpacing(10)

        self.__service_label = QtWidgets.QLabel("Layer Service", self)
        self.__service_label.setToolTip("Apply filters to only this service.")

        self.__percent_label = QtWidgets.QLabel("% of Run Since LLU", self)
        self.__percent_label.setToolTip("Percentage of the frame's running time spent" +
                                        " with the same last log update.")

        self.__llu_label = QtWidgets.QLabel("Min LLU", self)
        self.__llu_label.setToolTip("Only show frames whose last log update is more " +
                                    "than this many minutes ago.")

        self.__completion_label = QtWidgets.QLabel("% of Average Completion Time ", self)
        self.__completion_label.setToolTip("""
                Only show frames who are running at this percentage of
                the average completion time for the same layer. If there is no
                average yet, all frames will qualify.
        """)

        self.__run_label = QtWidgets.QLabel("Total Runtime", self)
        self.__run_label.setToolTip("Only show frames running for this long")

        self.__exclude_label = QtWidgets.QLabel("Exclude Keywords", self)
        self.__exclude_label.setToolTip("Keywords to exclude certain layers or jobs. " +
                                        "Separate by commas.")

        self.__enable_label = QtWidgets.QLabel("Enable", self)
        self.__enable_label.setToolTip("Uncheck to disable a filter")

        self.__remove_btn = QtWidgets.QPushButton(QtGui.QIcon(":up.png"), "")
        self.__remove_btn.setToolTip("Remove Filter")
        self.__remove_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__remove_btn.setFlat(True)

        self.__labels = QtWidgets.QHBoxLayout()
        self.__labels.addSpacing(30)
        self.__labels.addWidget(self.__service_label)
        self.__labels.addSpacing(90)
        self.__labels.addWidget(self.__exclude_label)
        self.__labels.addSpacing(10)
        self.__labels.addWidget(self.__percent_label)
        self.__labels.addWidget(self.__llu_label)
        self.__labels.addSpacing(30)
        self.__labels.addWidget(self.__completion_label)
        self.__labels.addWidget(self.__run_label)
        self.__labels.addWidget(self.__enable_label)
        self.__labels.addWidget(self.__remove_btn)
        self.__labels.addStretch()

        filters = StuckFrameBar(True, self)
        self.__all_filters = [filters]
        self.showing = True

        filters3 = QtWidgets.QVBoxLayout()
        self.filters4 = QtWidgets.QVBoxLayout()
        self.filters4.addLayout(self.__labels)
        self.filters4.addWidget(filters)
        self.filters4.setSpacing(0)

        filters3.addLayout(self.filters4)

        self.__group_filters.setLayout(filters3)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__group_filters)
        layout.addLayout(controls)

        self.connect(self.__show_combo,
                     QtCore.SIGNAL("currentIndexChanged(QString)"),
                     self.showChanged)

        self.connect(self.__remove_btn,
                     QtCore.SIGNAL("clicked()"),
                     self.hideButtonRequest)

    def addFilter(self):
        """Adds new filter."""
        newFilter = StuckFrameBar(self)
        self.__all_filters.append(newFilter)
        self.filters4.addWidget(newFilter)

    def showChanged(self, show):
        """Sets current show the one provided."""
        self.__current_show = opencue.api.findShow(str(show))

    def getFilterBar(self):
        """Returns filter bar."""
        return self.filters4

    def getAllFilters(self):
        """Returns all filters."""
        return self.__all_filters

    def hideButtonRequest(self):
        """If filters are showed, hides all filters except the first and sets the remove
        button icon as downward facing arrow. Otherwise, shows all filters."""
        if self.showing:
            self.showing = False
            for frame_filter in self.__all_filters:
                if not frame_filter.isFirst():
                    frame_filter.hide()
            self.__remove_btn.setIcon(QtGui.QIcon(":down.png"))
        else:
            self.openAll()

    def openAll(self):
        """Shows all filters and sets the remove button icon as upward facing arrow."""
        self.showing = True
        for frame_filter in self.__all_filters:
            frame_filter.show()
        self.__remove_btn.setIcon(QtGui.QIcon(":up.png"))

    def getRegexString(self):
        """Returns regex string."""
        return str(self.__exclude_regex.text()).strip()

    def getSearchButton(self):
        """Returns search button."""
        return self.__search_btn

    def getProgress(self):
        """Returns progress bar."""
        return self.__progress

    def getClearButton(self):
        """Returns clear button."""
        return self.__clear_btn

    def getAutoRefresh(self):
        """Returns auto refresh button."""
        return self.__auto_refresh_btn

    def getNotification(self):
        """Returns notification button."""
        return self.__notification_btn

    def getShow(self):
        """Returns current show."""
        return self.__current_show

    def getFilters(self):
        """Returns all filters"""
        return self.__all_filters

    def add(self):
        """Adds new filter"""
        return self.__all_filters


class StuckFrameBar(QtWidgets.QWidget):
    """Bar with filters"""

    def __init__(self, first, parent=None):
        self.defaults = {'preprocess': [1, 1, 115, 10], 'nuke': [50, 5, 115, 10],
                         'arnold': [50, 60, 115, 120]}

        QtWidgets.QWidget.__init__(self, parent)

        self.__percent_spin = QtWidgets.QSpinBox(self)
        self.__percent_spin.setRange(1, 100)
        self.__percent_spin.setValue(50)
        self.__percent_spin.setMaximumWidth(100)
        self.__percent_spin.setMinimumWidth(100)
        self.__percent_spin.setSuffix("%")
        self.__percent_spin.setAlignment(QtCore.Qt.AlignRight)

        self.__run_sping = QtWidgets.QSpinBox(self)
        self.__run_sping.setRange(1, 50000)
        self.__run_sping.setValue(60)
        self.__run_sping.setSuffix("min")
        self.__run_sping.setAlignment(QtCore.Qt.AlignRight)

        self.__llu_spin = QtWidgets.QSpinBox(self)
        self.__llu_spin.setRange(1, 50000)
        self.__llu_spin.setValue(30)
        self.__llu_spin.setSuffix(" min")
        self.__llu_spin.setAlignment(QtCore.Qt.AlignRight)

        self.__completion_spin = QtWidgets.QSpinBox(self)
        self.__completion_spin.setRange(1, 50000)
        self.__completion_spin.setValue(115)
        self.__completion_spin.setMaximumWidth(175)
        self.__completion_spin.setMinimumWidth(175)
        self.__completion_spin.setSuffix("%")
        self.__completion_spin.setAlignment(QtCore.Qt.AlignRight)

        self.__exclude_regex = QtWidgets.QLineEdit(self)
        self.__exclude_regex.setMaximumWidth(150)
        self.__exclude_regex.setMinimumWidth(150)

        self.__service_type = ServiceBox(self)
        self.__service_type.setMaximumWidth(200)
        self.__service_type.setMinimumWidth(200)
        self.__service_type.setTextMargins(5, 0, 0, 0)

        self.__enable = QtWidgets.QCheckBox(self)
        self.__enable.setChecked(True)

        self.__filters = QtWidgets.QHBoxLayout(self)
        self.__filters.addWidget(self.__service_type)
        self.__filters.addWidget(self.__exclude_regex)
        self.__filters.addWidget(self.__percent_spin)
        self.__filters.addSpacing(30)
        self.__filters.addWidget(self.__llu_spin)
        self.__filters.addWidget(self.__completion_spin)
        self.__filters.addSpacing(35)
        self.__filters.addWidget(self.__run_sping)
        self.__filters.addSpacing(25)
        self.__filters.addWidget(self.__enable)

        if not first:
            self.__remove_btn = QtWidgets.QPushButton(QtGui.QIcon(":kill.png"), "")
            self.__remove_btn.setToolTip("Remove Filter")
            self.__remove_btn.setFocusPolicy(QtCore.Qt.NoFocus)
            self.__remove_btn.setFlat(True)

            self.connect(self.__remove_btn,
                         QtCore.SIGNAL("clicked()"),
                         self.removeFilter)
            self.__filters.addWidget(self.__remove_btn)
            self.__isFirst = False
        else:
            self.__service_type.setText("All (Click + to Add Specific Filter)")
            self.__service_type.setReadOnly(True)
            self.__add_btn = QtWidgets.QPushButton(QtGui.QIcon('%s/add.png' %
                                                               cuegui.Constants.RESOURCE_PATH), "")
            self.__add_btn.setToolTip("Add Filter")
            self.__add_btn.setFocusPolicy(QtCore.Qt.NoFocus)
            self.__add_btn.setFlat(True)

            self.connect(self.__add_btn,
                         QtCore.SIGNAL("clicked()"),
                         self.addFilter)
            self.__filters.addWidget(self.__add_btn)
            self.__isFirst = True

        self.__filters.addStretch()

    def getServiceBox(self):
        """Returns service box."""
        return self.__service_type

    def getRegex(self):
        """Returns regex."""
        return self.__exclude_regex

    def getServiceBoxText(self):
        """Returns service box text."""
        return str(self.__service_type.text()).strip()

    def getRegexText(self):
        """Returns regex text."""
        return str(self.__exclude_regex.text()).strip()

    def getEnabled(self):
        """Returns enable checkbox."""
        return self.__enable

    def removeFilter(self):
        """Removes filter."""
        self.parent().parent().getFilterBar().removeWidget(self)
        self.parent().parent().getAllFilters().remove(self)
        if len(self.parent().parent().getAllFilters()) == 1:
            self.parent().parent().getAllFilters()[0]\
                .getServiceBox().setText("All (Click + to Add Specific Filter)")
        self.hide()

    def addFilter(self):
        """Adds new filter."""
        newFilter = StuckFrameBar(False, self.parent())
        self.parent().parent().getFilterBar().addWidget(newFilter)
        self.parent().parent().getAllFilters().append(newFilter)
        self.parent().parent().getAllFilters()[0].getServiceBox().setText("All Other Types")
        self.parent().parent().openAll()
        self.parent().parent().parent().addConnections(newFilter)
        return newFilter

    def isFirst(self):
        """Returns true if first."""
        return self.__isFirst

    def getFilters(self):
        """Returns filters."""
        return self.__filters

    def getTime(self):
        """Returns time value as int"""
        return int(self.__percent_spin.value())

    def getMinLLu(self):
        """Returns min LLU."""
        return int(self.__llu_spin.value())

    def getAvgCompTime(self):
        """Returns average completion time as int."""
        return int(self.__completion_spin.value())

    def getMVTime(self):
        """Returns MV time as int."""
        return int(self.__mkvid_spin.value())

    def getPrepTime(self):
        """Returns preparation time as int."""
        return int(self.__prep_spin.value())

    def getLLUFilter(self):
        """Returns LLU filter."""
        return self.__llu_spin

    def getPercentFilter(self):
        """Returns percent filter."""
        return self.__percent_spin

    def getCompletionFilter(self):
        """Return completion filter."""
        return self.__completion_spin

    def getRunFilter(self):
        """Returns run filter."""
        return self.__run_sping

    def getRunTime(self):
        """Returns run time as int."""
        return int(self.__run_sping.value())

    def enable(self):
        """Enables filters."""
        self.__percent_spin.setEnabled(not self.__percent_spin.isEnabled())
        self.__run_sping.setEnabled(not self.__run_sping.isEnabled())
        self.__llu_spin.setEnabled(not self.__llu_spin.isEnabled())
        self.__completion_spin.setEnabled(not self.__completion_spin.isEnabled())
        self.__exclude_regex.setEnabled(not self.__exclude_regex.isEnabled())
        self.__service_type.setEnabled(not self.__service_type.isEnabled())

    def checkForDefaults(self):
        """If service is in defaults, the filter values will be set to the service."""
        service = str(self.__service_type.text()).strip()
        if service in self.defaults:
            self.__percent_spin.setValue(self.defaults[service][0])
            self.__llu_spin.setValue(self.defaults[service][1])
            self.__completion_spin.setValue(self.defaults[service][2])
            self.__run_sping.setValue(self.defaults[service][3])


class ServiceBox(QtWidgets.QLineEdit):
    """
    A text box that auto-completes job names.
    """

    def __init__(self, parent=None):
        QtWidgets.QLineEdit.__init__(self, parent)
        self.__c = None
        self.refresh()

    def refresh(self):
        """Refreshes the show list."""
        slist = opencue.api.getDefaultServices()
        slist.sort(key=lambda s: s.name())
        self.__c = QtWidgets.QCompleter(list(slist), self)
        self.__c.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setCompleter(self.__c)


class StuckFrameWidget(QtWidgets.QWidget):
    """
    Displays controls for finding stuck frames and a tree of the findings.
    """

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.controls = StuckFrameControls(self)
        self.tree = StuckFrameMonitorTree(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.controls)
        layout.addWidget(self.tree)

        if self.tree.enableRefresh:
            self.controls.getAutoRefresh().setCheckState(QtCore.Qt.Checked)

        self.connect(self.controls.getAutoRefresh(),
                     QtCore.SIGNAL('stateChanged(int)'),
                     self.__refreshToggleCheckBoxHandle)

        self.connect(self.controls.getNotification(),
                     QtCore.SIGNAL('stateChanged(int)'),
                     self.__refreshNotificationCheckBoxHandle)

        self.connect(self.tree,
                     QtCore.SIGNAL("updated()"),
                     self._refreshButtonDisableHandle)

        self.connect(self.controls.getSearchButton(),
                     QtCore.SIGNAL("clicked()"),
                     self.updateRequest)
        filters = self.controls.getFilters()
        for frame_filter in filters:
            self.addConnections(frame_filter)

        self.connect(self.controls.getClearButton(),
                     QtCore.SIGNAL("clicked()"),
                     self.clearButtonRequest)

    def addConnections(self, frame_filter):
        """Connects to the widget based on the filter provided"""
        self.connect(frame_filter.getLLUFilter(),
                     QtCore.SIGNAL("valueChanged(int)"),
                     self.updateFilters)

        self.connect(frame_filter.getPercentFilter(),
                     QtCore.SIGNAL("valueChanged(int)"),
                     self.updateFilters)

        self.connect(frame_filter.getCompletionFilter(),
                     QtCore.SIGNAL("valueChanged(int)"),
                     self.updateFilters)

        self.connect(frame_filter.getRunFilter(),
                     QtCore.SIGNAL("valueChanged(int)"),
                     self.updateFilters)

        self.connect(frame_filter.getRegex(),
                     QtCore.SIGNAL("textChanged(QString)"),
                     self.updateFilters)

        self.connect(frame_filter.getServiceBox(),
                     QtCore.SIGNAL("textChanged(QString)"),
                     self.updateFilters)

        self.connect(frame_filter.getEnabled(),
                     QtCore.SIGNAL("stateChanged(int)"),
                     self.updateFilters)

        self.connect(frame_filter.getEnabled(),
                     QtCore.SIGNAL("stateChanged(int)"),
                     frame_filter.enable)

        self.connect(frame_filter.getServiceBox(),
                     QtCore.SIGNAL("textChanged(QString)"),
                     frame_filter.checkForDefaults)

    def __refreshToggleCheckBoxHandle(self, state):
        self.tree.enableRefresh = bool(state)
        self.controls.getNotification().setEnabled(bool(state))

    def __refreshNotificationCheckBoxHandle(self, state):
        self.tree.enableNotification = bool(state)

    def _refreshButtonEnableHandle(self):
        self.controls.getSearchButton().setEnabled(True)

    def _refreshButtonDisableHandle(self):
        self.controls.getSearchButton().setEnabled(False)
        QtCore.QTimer.singleShot(5000, self._refreshButtonEnableHandle)

    def updateRequest(self):
        """Updates filter list with only enabled filters and then updates the tree widget."""
        allFilters = {}
        filters = self.controls.getFilters()
        for frame_filter in filters:
            if frame_filter.getEnabled().isChecked():
                allFilters[frame_filter.getServiceBoxText()] = [frame_filter.getRegexText(),
                                                                frame_filter.getTime(),
                                                                frame_filter.getMinLLu(),
                                                                frame_filter.getAvgCompTime(),
                                                                frame_filter.getRunTime()]

        self.tree.updateFilters(allFilters, self.controls.getShow())
        self.tree.setCompleteRefresh(True)
        self.tree.updateRequest()

    def updateFilters(self):
        """Updates filter list with only enabled filters."""
        allFilters = {}
        filters = self.controls.getFilters()
        for frame_filter in filters:
            if frame_filter.getEnabled().isChecked():
                allFilters[frame_filter.getServiceBoxText()] = [
                    frame_filter.getRegexText(),
                    frame_filter.getTime(),
                    frame_filter.getMinLLu(),
                    frame_filter.getAvgCompTime(),
                    frame_filter.getRunTime()
                ]
        self.tree.updateFilters(allFilters, self.controls.getShow())

    def clearButtonRequest(self):
        """Clears tree widget."""
        self.tree.clearItems()
        self.tree.enableRefresh = False
        self.controls.getAutoRefresh().setCheckState(QtCore.Qt.Unchecked)

    def getControls(self):
        """Returns controls."""
        return self.controls


class StuckFrameMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget with stuck frames"""

    _updateProgress = QtCore.Signal(int)
    _updateProgressMax = QtCore.Signal(int)
    _itemSingleClickedComment = QtCore.Signal(QtWidgets.QTreeWidgetItem, int)

    def __init__(self, parent):
        self.parent = parent
        self.startColumnsForType(cuegui.Constants.TYPE_FRAME)
        self.addColumn("Name", 300, id=1,
                       data=lambda item: (item.data.name or ""),
                       tip="The job name.")
        self.addColumn("_Comment", 20, id=2,
                       tip="A comment icon will appear if a job has a comment. You\n"
                           "may click on it to view the comments.")
        self.addColumn("Frame", 40, id=3,
                       data=lambda item: (item.number or ""),
                       tip="Frame number")
        self.addColumn("Host", 120, id=4,
                       data=lambda item: (item.lastResource or ""),
                       tip="Host the frame is currently running on")
        self.addColumn("LLU", 60, id=5,
                       data=lambda item: (self.numFormat(item.lastLogUpdate, "t") or ""),
                       tip="Last Log Update")
        self.addColumn("Runtime", 60, id=6,
                       data=lambda item: (self.numFormat(item.timeRunning, "t") or ""),
                       tip="Length the Frame has been running")
        self.addColumn("% Stuck", 50, id=7,
                       data=lambda item: (self.numFormat(item.stuckness, "f") or ""),
                       tip="Percent of frame's total runtime that the log has not been updated")
        self.addColumn("Average", 60, id=8,
                       data=lambda item: (self.numFormat(item.averageFrameTime, "t") or ""),
                       tip="Average time for a frame of this type to complete")
        self.addColumn("Last Line", 250, id=9,
                       data=lambda item: (cuegui.Utils.getLastLine(item.log_path) or ""),
                       tip="The last line of a running frame's log file.")

        self.startColumnsForType(cuegui.Constants.TYPE_GROUP)
        self.addColumn("", 0, id=1,
                       data=lambda group: (group.data.name), sort=lambda group: (group.data.name))
        self.addColumn("", 0, id=2)
        self.addColumn("", 0, id=3)
        self.addColumn("", 0, id=4)
        self.addColumn("", 0, id=5)
        self.addColumn("", 0, id=6)
        self.addColumn("", 0, id=7)
        self.addColumn("", 0, id=8)
        self.addColumn("", 0, id=9)

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)
        self.procSearch = opencue.search.ProcSearch()

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(self, self.updateSoon,
                                                            self.selectedObjects, self.getJob)

        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)

        self.layer_cache = {}
        self.jobs_created = {}
        self.groups_created = {}
        self.currentHosts = []
        self.show = None

        # Bring Up a comment if it exists
        self._itemSingleClickedComment.connect(self.__itemSingleClickedComment)
        # Set progress bar current value
        self._updateProgress.connect(self.updateProgress)

        # Set total number of procs for the progress bar max
        self._updateProgressMax.connect(self.updateProgressMax)

        # Don't use the standard space bar to refres
        self.disconnect(self.app,
                        QtCore.SIGNAL('request_update()'),
                        self.updateRequest)

        self.run_log = LogFinal()
        self.frames = {}
        self.ticksSinceLogFlush = 0
        self.startTicksUpdate(2000)

        # Don't start refreshing until the user sets a filter or hits refresh
        self.ticksWithoutUpdate = -1
        self.enableRefresh = False
        self.completeRefresh = False
        self.enableNotification = False

        self.runtime_filter = None
        self.min_llu_filter = None
        self.time_filter = None
        self.avg_comp_filter = None
        self.excludes = None
        self.groups = None
        self.showData = None
        self.filters = None

    def logIt(self):
        """Logs cache to a file."""
        if self.app.threadpool is not None:
            print("Stuck Frame Log cache is being written to file.")
            self.app.threadpool.queue(
                self.run_log.finalize, self.logResult, "Writing out log", self.frames, self.show)
        else:
            logger.warning("threadpool not found, doing work in gui thread")

    # pylint: disable=missing-function-docstring,unused-argument
    def logResult(self, work, rpcObjects):
        self.frames = {}

    # pylint: disable=redefined-builtin,inconsistent-return-statements
    def numFormat(self, num, type):
        """Returns string formatting based on the number"""
        if num == "" or num < .001 or num is None:
            return ""
        if type == "t":
            return cuegui.Utils.secondsToHHMMSS(int(num))
        if type == "f":
            return "%.2f" % float(num)

    def setCompleteRefresh(self, value):
        """Sets complete refresh based on given value."""
        self.completeRefresh = value

    def tick(self):
        """Handles update on single tick."""
        if self.ticksSinceLogFlush >= 400 and len(self.frames) > 0:
            self.ticksSinceLogFlush = 0
            self.logIt()

        if self.completeRefresh:
            self.ticksWithoutUpdate = 0
            self.completeRefresh = False
            self._update()
            return

        if (self.ticksWithoutUpdate % 40 == 0 and
                self.ticksWithoutUpdate != self.updateInterval and not self.window().isMinimized()):
            self.ticksWithoutUpdate += 1
            if len(self.currentHosts) > 0:
                self.confirm(1)
            return

        if (self.ticksWithoutUpdate >= self.updateInterval and
                self.enableRefresh and not self.window().isMinimized()):
            self.ticksWithoutUpdate = 0
            self._update()
            if self.enableNotification:
                message = QtWidgets.QMessageBox(self)
                message.setText("Stuck Frames have refreshed!.")
                message.exec_()
            return

        self.ticksSinceLogFlush += 1
        if not self.window().isMinimized():
            self.ticksWithoutUpdate += 1

    def __itemSingleClickedComment(self, item, col):
        """If the comment column is clicked on, and there is a comment on the
        host, this pops up the comments dialog
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        commentItem = item.rpcObject
        if (col == COMMENT_COLUMN and
                cuegui.Utils.isJob(commentItem) and commentItem.data.hasComment):
            self.__menuActions.jobs().viewComments([commentItem])
        self.update()

    def updateProgressMax(self, newMax):
        """Send an update to the progress bar of the new maximum value"""
        self.parent.getControls().getProgress().setMaximum(newMax)

    def updateProgress(self, currentValue):
        """Send an update of the current value for the progress bar"""
        self.parent.getControls().getProgress().setValue(currentValue)

    def updateSoon(self):
        """Returns immediately. Causes an update to happen
        Constants.AFTER_ACTION_UPDATE_DELAY after calling this function."""
        QtCore.QTimer.singleShot(cuegui.Constants.AFTER_ACTION_UPDATE_DELAY,
                                 self.updateRequest)

    def getJob(self):
        """Returns the current job
        @return: The current job
        @rtype:  job"""
        return cuegui.Utils.findJob(self.selectedObjects()[0].data.name)

    def clearItems(self):
        """Clears all items"""
        self.clearSelection()
        self.removeAllItems()
        self.currentHosts = []

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 999
        self.completeRefresh = True

    def get_frame_run_time(self, item):
        """Returns frame run time."""
        if cuegui.Utils.isProc(item):
            start_time = item.data.dispatch_time
        elif cuegui.Utils.isFrame(item):
            start_time = item.data.start_time
        else:
            return ""
        current_time = time.time()
        run_time = current_time - start_time
        return run_time

    def get_llu_time(self, item):
        """Returns LLU time."""
        if cuegui.Utils.isProc(item):
            log_file = item.data.log_path
        elif cuegui.Utils.isFrame(item):
            log_file = item.log_path
        else:
            return ""
        # pylint: disable=broad-except
        try:
            stat_info = os.path.getmtime(log_file)
        except Exception:
            return "None"
        current_time = time.time()
        llu_time = current_time - stat_info

        return llu_time

    def find_layer(self, proc):
        """Return layer based on proc."""
        jobName = proc.data.job_name
        layerName = proc.data.frame_name.split("-")[1]
        key = "%s/%s" % (jobName, layerName)

        if not self.layer_cache.get(key, None):
            # pylint: disable=broad-except
            try:
                self.layer_cache[key] = proc.getLayer()
            except Exception:
                return "None"

        return self.layer_cache[key]

    def confirm(self, update):
        """Confirm frame filter."""
        currentHostsNew = []
        nextIndex = 2
        # pylint: disable=consider-using-enumerate
        for index in range(len(self.currentHosts)):
            if index == nextIndex:
                frame = self.currentHosts[index]
                nextIndex = nextIndex + 3

                if frame.service in self.filters.keys():
                    self.runtime_filter = self.filters[frame.service][4]
                    self.min_llu_filter = self.filters[frame.service][2]
                    self.time_filter = self.filters[frame.service][1]
                    self.avg_comp_filter = self.filters[frame.service][3]
                    self.excludes = [x.strip() for x in self.filters[frame.service][0].split(',')
                                     if x != ""]
                else:
                    if "All (Click + to Add Specific Filter)" in self.filters.keys():
                        key = "All (Click + to Add Specific Filter)"
                    elif "All Other Types" in self.filters.keys():
                        key = "All Other Types"
                    else:
                        continue
                    self.runtime_filter = self.filters[key][4]
                    self.min_llu_filter = self.filters[key][2]
                    self.time_filter = self.filters[key][1]
                    self.avg_comp_filter = self.filters[key][3]
                    self.excludes = [x.strip() for x in self.filters[key][0].split(',') if x != ""]

                # layerName = frame.data.layer_name
                frameRunTime = self.get_frame_run_time(frame)
                # jobName = frame.data.name
                lluTime = self.get_llu_time(frame)
                avgFrameTime = frame.averageFrameTime
                percentStuck = lluTime / frameRunTime

                frame.stuckness = percentStuck
                frame.lastLogUpdate = lluTime
                frame.timeRunning = frameRunTime

                if ((lluTime > (self.min_llu_filter * 60)) and
                        (percentStuck * 100 > self.time_filter) and
                        (frameRunTime > (avgFrameTime * self.avg_comp_filter / 100) and
                         percentStuck < 1.1 and frameRunTime > 500)):
                    currentHostsNew.append(self.currentHosts[index - 2])
                    currentHostsNew.append(self.currentHosts[index - 1])
                    currentHostsNew.append(frame)

        self.currentHosts[:] = []
        self.currentHosts = currentHostsNew

        if update == 1:
            self._processUpdate(None, self.currentHosts)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        # pylint: disable=broad-except,too-many-nested-blocks
        try:
            treeItems = []
            self.groups = []
            self.procSearch.hosts = []
            self.procSearch.shows = [self.show]
            procs = []
            shows = opencue.api.getShows()
            for show in shows:
                procs.extend(opencue.api.getProcs(show=[show.name()]))

            current_prog = 0
            self.emit(QtCore.SIGNAL("updatedProgressMax"), (len(procs)))
            self._updateProgressMax.emit(len(procs))
            for proc in procs:
                if proc.data.services[0] in self.filters.keys():
                    self.runtime_filter = self.filters[proc.data.services[0]][4]
                    self.min_llu_filter = self.filters[proc.data.services[0]][2]
                    self.time_filter = self.filters[proc.data.services[0]][1]
                    self.avg_comp_filter = self.filters[proc.data.services[0]][3]
                    self.excludes = [x.strip()
                                     for x in self.filters[proc.data.services[0]][0].split(',')
                                     if x != ""]
                else:
                    if "All (Click + to Add Specific Filter)" in self.filters.keys():
                        key = "All (Click + to Add Specific Filter)"
                    elif "All Other Types" in self.filters.keys():
                        key = "All Other Types"
                    else:
                        continue
                    self.runtime_filter = self.filters[key][4]
                    self.min_llu_filter = self.filters[key][2]
                    self.time_filter = self.filters[key][1]
                    self.avg_comp_filter = self.filters[key][3]
                    self.excludes = [x.strip() for x in self.filters[key][0].split(',') if x != ""]

                jobName = proc.data.job_name
                (frameNumber, layerName) = proc.data.frame_name.split("-")

                frameRunTime = self.get_frame_run_time(proc)

                if frameRunTime >= self.runtime_filter * 60:
                    # Get average completion time of the layer
                    layer = self.find_layer(proc)
                    # Skip processing if the layer obj doesn't exist. i.e frame finished
                    if layer == "None":
                        continue
                    avgFrameTime = layer.avgFrameTimeSeconds()

                    if frameRunTime > (avgFrameTime * self.avg_comp_filter / 100):
                        # log_path = proc.data.log_path  # Get the log file path for last line
                        lluTime = self.get_llu_time(proc)
                        if lluTime == "None":
                            # Skip processing if there was any error with reading
                            # the log file(path did not exist,permissions)
                            continue
                        if lluTime > self.min_llu_filter * 60:
                            percentStuck = 0
                            if frameRunTime > 0:
                                percentStuck = lluTime / frameRunTime

                            if percentStuck * 100 > self.time_filter and percentStuck < 1.1:
                                please_exclude = False
                                for exclude in self.excludes:
                                    if (exclude in layerName or
                                            exclude in jobName):
                                        please_exclude = True
                                        continue

                                if please_exclude:
                                    continue

                                # Job may have finished/killed put in a try
                                # Injecting into rpcObjects extra data not available via client API
                                # to support cue3 iceObject backwards capability
                                try:
                                    frame = opencue.api.findFrame(jobName,
                                                                  layerName, int(frameNumber))
                                    frame.data.layer_name = layerName
                                    frame.__dict__['job_name'] = jobName
                                    frame.__dict__['log_path'] = proc.data.log_path
                                    frame.__dict__['number'] = frame.data.number
                                    frame.__dict__['lastLogUpdate'] = lluTime
                                    frame.__dict__['averageFrameTime'] = avgFrameTime
                                    frame.__dict__['stuckness'] = percentStuck
                                    frame.__dict__['timeRunning'] = frameRunTime
                                    frame.__dict__['lastResource'] = frame.data.last_resource
                                    frame.__dict__['service'] = proc.data.services[0]

                                    job = opencue.api.findJob(jobName)
                                    job.__dict__['log_path'] = job.data.log_dir
                                    job.__dict__['lastLogUpdate'] = ""
                                    job.__dict__['averageFrameTime'] = ""
                                    job.__dict__['number'] = ""
                                    job.__dict__['stuckness'] = ""
                                    job.__dict__['timeRunning'] = ""
                                    job.__dict__['lastResource'] = ""
                                    job.__dict__['hostUsage'] = ""
                                    job.__dict__['service'] = proc.data.services[0]
                                    if self.show == job.data.show:
                                        group = opencue.api.findGroup(self.show, job.data.group)

                                        treeItems.append(group)
                                        treeItems.append(job)
                                        treeItems.append(frame)
                                except Exception:
                                    # Can safely ignore if a Job has already completed
                                    pass

                current_prog = current_prog + 1
                self._updateProgress.emit(current_prog)

            self._updateProgress.emit(len(procs))
            self.currentHosts[:] = []
            self.currentHosts = treeItems

            self.confirm(0)

            return self.currentHosts
        except Exception as e:
            print(cuegui.Utils.exceptionOutput(e))
            return []

    def _createItem(self, object, parent=None):
        """Creates and returns the proper item
        @type  object: Host
        @param object: The object for this item
        @type  parent: QTreeWidgetItem
        @param parent: Optional parent for this item
        @rtype:  QTreeWidgetItem
        @return: The created item"""

        if cuegui.Utils.isGroup(object):
            groupWidget = GroupWidgetItem(object, self)
            self.groups_created[object.data.name] = groupWidget  # Store parents created
            groupWidget.setExpanded(True)
            return groupWidget
        if cuegui.Utils.isJob(object):
            jobWidget = HostWidgetItem(object, self.groups_created[object.data.group])
            self.jobs_created[object.data.name] = jobWidget  # Store parents created
            jobWidget.setExpanded(True)
            return jobWidget
        if cuegui.Utils.isFrame(object):
            frameWidget = HostWidgetItem(object,
                                         # Find the Job to serve as its parent
                                         self.jobs_created[object.job_name])
            return frameWidget

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""

        menu = QtWidgets.QMenu()

        # Since we want different menu options based on what is chosen, we need to figure this out
        isJob = False
        isFrame = False
        sameJob = True
        jobName = None
        for item in self.selectedObjects():
            if cuegui.Utils.isJob(item):
                isJob = True
            elif cuegui.Utils.isFrame(item):
                isFrame = True
            if not jobName:
                jobName = item.data.name
            else:
                if item.data.name != jobName:
                    sameJob = False

        if isJob and not isFrame and sameJob:
            self.__menuActions.jobs().addAction(menu, "viewComments")
            self.__menuActions.jobs().addAction(menu, "emailArtist")
            self.__menuActions.jobs().addAction(menu, "subscribeToJob")
            menu.addAction(cuegui.Action.create(self, "Email and Comment", "Email and Comment",
                                                self.emailComment, "mail"))
            menu.addSeparator()
            menu.addAction(cuegui.Action.create(self, "Job Not Stuck", "Job Not Stuck",
                                                self.RemoveJob, "warning"))
            menu.addAction(
                cuegui.Action.create(self, "Add Job to Excludes", "Add Job to Excludes",
                                     self.AddJobToExcludes, "eject"))
            menu.addAction(cuegui.Action.create(self, "Exclude and Remove Job",
                                                "Exclude and Remove Job",
                                                self.AddJobToExcludesandRemove, "unbookkill"))
            menu.addSeparator()
            menu.addAction(cuegui.Action.create(self, "Core Up", "Core Up", self.coreup, "up"))
            menu.exec_(e.globalPos())

        if isFrame and not isJob and sameJob:
            count = len(self.selectedItems())

            self.__menuActions.frames().addAction(menu, "tail")
            self.__menuActions.frames().addAction(menu, "view")

            if count == 1:
                if self.selectedObjects()[0].data.retry_count >= 1:
                    self.__menuActions.frames().addAction(menu, "viewLastLog")

            if count >= 3:
                self.__menuActions.frames().addAction(menu, "xdiff3")
            elif count == 2:
                self.__menuActions.frames().addAction(menu, "xdiff2")

            if count == 1:
                menu.addSeparator()
                menu.addAction(cuegui.Action.create(self, "Top Machine", "Top Machine",
                                                    self.topMachine, "up"))
                if self.app.applicationName() == "CueCommander3":
                    self.__menuActions.frames().addAction(menu, "viewHost")

            menu.addSeparator()
            menu.addAction(cuegui.Action.create(self, "Retry", "Retry", self.retryFrame, "retry"))
            menu.addAction(cuegui.Action.create(self, "Eat", "Eat", self.eatFrame, "eat"))
            menu.addAction(cuegui.Action.create(self, "Kill", "Kill", self.killFrame, "kill"))
            menu.addSeparator()
            if count == 1:
                menu.addAction(cuegui.Action.create(self, "Log Stuck Frame", "Log Stuck Frame",
                                                    self.log, "loglast"))
            elif count > 1:
                menu.addAction(cuegui.Action.create(self, "Log Stuck Frames", "Log Stuck Frames",
                                                    self.log, "loglast"))
            menu.addAction(cuegui.Action.create(self, "Log and Retry", "Log and Retry",
                                                self.logRetry, "retry"))
            menu.addAction(cuegui.Action.create(self, "Log and Eat", "Log and Eat",
                                                self.logEat, "eat"))
            menu.addAction(cuegui.Action.create(self, "Log and Kill", "Log and Kill",
                                                self.logKill, "kill"))
            menu.addSeparator()
            menu.addAction(cuegui.Action.create(self, "Frame Not Stuck", "Frame Not Stuck",
                                                self.remove, "warning"))
            menu.addAction(
                cuegui.Action.create(self, "Add Job to Excludes", "Add Job to Excludes",
                                     self.AddJobToExcludes, "eject"))
            menu.addAction(cuegui.Action.create(self, "Exclude and Remove Job",
                                                "Exclude and Remove Job",
                                                self.AddJobToExcludesandRemove, "unbookkill"))
            menu.addSeparator()
            menu.addAction(cuegui.Action.create(self, "Core Up", "Core Up", self.coreup, "up"))

            menu.exec_(e.globalPos())

    def coreup(self):
        """PST Menu Plugin entry point."""
        job = self.getJob()
        win = CoreUpWindow(self, {job: job.getLayers()})
        win.show()

    def _processUpdate(self, work, rpcObjects):
        """A generic function that Will:
        Create new TreeWidgetItems if an item does not exist for the object.
        Update existing TreeWidgetItems if an item already exists for the object.
        Remove items that were not updated with rpcObjects.
        @param work:
        @type  work: from ThreadPool
        @param rpcObjects: A list of ice objects
        @type  rpcObjects: list<ice object> """
        self._itemsLock.lockForWrite()
        try:
            updated = []
            for rpcObject in rpcObjects:
                updated.append(cuegui.Utils.getObjectKey(rpcObject))  # rpcObject)
                # If id already exists, update it
                if cuegui.Utils.getObjectKey(rpcObject) in self._items:
                    self._items[cuegui.Utils.getObjectKey(rpcObject)].update(rpcObject)
                # If id does not exist, create it
                else:
                    self._items[cuegui.Utils.getObjectKey(rpcObject)] = self._createItem(rpcObject)
            # Remove any items that were not updated
            for rpcObject in list(set(self._items.keys()) - set(updated)):
                self._removeItem(rpcObject)
            self.redraw()
        finally:
            self._itemsLock.unlock()

    def topMachine(self):
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(int(30))

        job = self.selectedObjects()[0]

        command = (' xhost ' + job.lastResource.split('/')[0] + '; rsh ' +
                   job.lastResource.split('/')[0] + ' \"setenv DISPLAY ' +
                   str(socket.gethostname()).split('.', maxsplit=1)[0] + ':0; xterm -e top\" &')
        os.system(command)
        signal.alarm(0)

    def remove(self):
        currentHostsNew = []
        nextIndex = 2
        # pylint: disable=consider-using-enumerate
        for index in range(len(self.currentHosts)):
            if index == nextIndex:

                nextIndex = nextIndex + 3

                if self.currentHosts[index] not in self.selectedObjects():
                    currentHostsNew.append(self.currentHosts[index - 2])
                    currentHostsNew.append(self.currentHosts[index - 1])
                    currentHostsNew.append(self.currentHosts[index])
        self.currentHosts[:] = []
        self.currentHosts = currentHostsNew
        # self.currentHosts = [x for x in self.currentHosts if x not in self.selectedObjects()  ] -

        self._processUpdate(None, self.currentHosts)

    def emailComment(self):
        job = self.getJob()
        self.__menuActions.jobs().emailArtist([job])
        job.addComment("Emailed artists", "Emailed Artist but took no further action")

    def logRetry(self):
        names = [frame.name() for frame in self.selectedObjects()]

        if cuegui.Utils.questionBoxYesNo(self, "Confirm", "Retry selected frames?", names):
            self.log()
            for frame in self.selectedObjects():
                frame.retry()
            self.remove()

    def logEat(self):
        names = [frame.name() for frame in self.selectedObjects()]

        if cuegui.Utils.questionBoxYesNo(self, "Confirm", "Eat selected frames?", names):
            self.log()
            for frame in self.selectedObjects():
                frame.eat()
            self.remove()

    def logKill(self):
        names = [frame.name() for frame in self.selectedObjects()]

        if cuegui.Utils.questionBoxYesNo(self, "Confirm", "Kill selected frames?", names):
            self.log()
            for frame in self.selectedObjects():
                frame.kill(reason=DEFAULT_FRAME_KILL_REASON)
            self.remove()

    def retryFrame(self):
        names = [frame.name() for frame in self.selectedObjects()]

        if cuegui.Utils.questionBoxYesNo(self, "Confirm", "Retry selected frames?", names):
            for frame in self.selectedObjects():
                frame.retry()
            self.remove()

    def eatFrame(self):
        names = [frame.name() for frame in self.selectedObjects()]

        if cuegui.Utils.questionBoxYesNo(self, "Confirm", "Eat selected frames?", names):
            for frame in self.selectedObjects():
                frame.eat()
            self.remove()

    def killFrame(self):
        names = [frame.name() for frame in self.selectedObjects()]

        if cuegui.Utils.questionBoxYesNo(self, "Confirm", "Kill selected frames?", names):
            for frame in self.selectedObjects():
                frame.kill()
            self.remove()

    def handler(self):
        message = QtWidgets.QMessageBox(self)
        message.setText("""Unable to connect to host after 30 sec.
                        It may need to be put into repair state. """)
        message.exec_()

    def log(self):
        self.ticksSinceLogFlush = 0
        currentJob = self.selectedObjects()[0].data.name
        framesForJob = {}
        for frame in self.selectedObjects():
            frameData = {}
            frameData['layer'] = frame.job_name
            frameData['host'] = frame.lastResource
            frameData['llu'] = self.get_llu_time(frame)
            frameData['runtime'] = self.get_frame_run_time(frame)
            frameData['average'] = frame.averageFrameTime
            frameData['log'] = cuegui.Utils.getLastLine(frame.log_path)
            framesForJob[str(frame.data.number) + '-' + str(time.time())] = frameData

        self.frames[currentJob] = framesForJob

    def AddJobToExcludes(self):
        currentJob = self.selectedObjects()[0]
        currentJobName = currentJob.data.name
        currentJobService = currentJob.service
        filters = self.parent().getControls().getFilters()

        key = ""
        for filter in filters:
            if currentJobService == filter.getServiceBoxText():
                key = currentJobService
                filterChange = filter
                break
        if key == "":
            for filter in filters:
                if filter.getServiceBoxText() == "All (Click + to Add Specific Filter)":
                    key = "All (Click + to Add Specific Filter)"
                    filterChange = filter
                break
        if key == "":
            for filter in filters:
                if filter.getServiceBoxText() == "All Other Types":
                    key = "All Other Types"
                    filterChange = filter
                break

        if len(filterChange.getRegexText()) > 0:
            filterChange.getRegex().setText(filterChange.getRegexText() + ", " + currentJobName)
        else:
            filterChange.getRegex().setText(currentJobName)

        return currentJobName

    def AddJobToExcludesandRemove(self):
        self.AddJobToExcludes()
        self.RemoveJob()

    def RemoveJob(self):
        jobName = self.selectedObjects()[0].data.name
        currentHostsNew = []
        nextIndex = 2
        # pylint: disable=consider-using-enumerate
        for index in range(len(self.currentHosts)):
            if index == nextIndex:

                nextIndex = nextIndex + 3

                if self.currentHosts[index].data.name != jobName:
                    currentHostsNew.append(self.currentHosts[index - 2])
                    currentHostsNew.append(self.currentHosts[index - 1])
                    currentHostsNew.append(self.currentHosts[index])
        self.currentHosts[:] = []
        self.currentHosts = currentHostsNew

        self._processUpdate(None, self.currentHosts)

    def startDrag(self, dropActions):
        """Drag start action"""
        cuegui.Utils.startDrag(self, dropActions, self.selectedObjects())

    def dragEnterEvent(self, event):
        """Drag enter action"""
        cuegui.Utils.dragEnterEvent(event, "application/x-host-ids")

    def dragMoveEvent(self, event):
        """Drag move event"""
        cuegui.Utils.dragMoveEvent(event, "application/x-host-ids")

    def updateFilters(self, filters, show):
        """Update filters"""
        self.showData = show
        self.show = show.data.name
        self.filters = filters

    def _removeItem(self, item):
        """Removes an item from the TreeWidget without locking
        @type  item: AbstractTreeWidgetItem or String
        @param item: A tree widget item or the string with the id of the item"""

        if item in self._items:
            item = self._items[item]
        elif not isinstance(item, cuegui.AbstractWidgetItem.AbstractWidgetItem):
            # if the parent was already deleted, then this one was too
            return

        # If it has children, they must be deleted first
        if item.childCount() > 0:
            for child in item.takeChildren():
                self._removeItem(child)

        if item.isSelected():
            item.setSelected(False)

        if item.parent():
            self.invisibleRootItem().removeChild(item)
        self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        objectClass = item.rpcObject.__class__.__name__
        objectId = item.rpcObject.id()
        try:
            del self._items['{}.{}'.format(objectClass, objectId)]
        except KeyError:
            # Dependent jobs are not stored in as keys the main self._items
            # dictionary, trying to remove dependent jobs from self._items
            # raises a KeyError, which we can safely ignore
            pass

    def finalize(self, frames):

        dict = frames
        yaml_path = "/shots/" + self.show + "/home/etc/stuck_frames_db.yaml"

        if not os.path.exists(yaml_path):

            with open(yaml_path, 'w', encoding='utf-8') as yaml_ob:
                yaml.dump(dict, yaml_ob)

        else:
            with open(yaml_path, 'r', encoding='utf-8') as yaml_ob:
                old_dict = yaml.load(yaml_ob, Loader=yaml.SafeLoader)

            with open(yaml_path, 'w', encoding='utf-8') as yaml_ob:

                for key in dict:  # updates old dict
                    old_dict[key] = dict[key]

                yaml.dump(old_dict, yaml_ob)


class CommentWidget(QtWidgets.QWidget):
    """Represents a comment."""
    def __init__(self, subject, message, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        # pylint: disable=unused-private-member
        self.__textSubject = subject
        self.__textMessage = message

        # def getSubject(self):
        #     return str(self.__textSubject.text())
        #
        # def getMessage(self):
        #     return str(self.__textMessage.toPlainText())


class GroupWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Represents a group entry in the MonitorCue widget."""
    __initialized = False

    def __init__(self, rpcObject, parent):
        # pylint: disable=protected-access
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__icon = QtGui.QIcon(":group.png")
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_GROUP_FOREGROUND
            self.__class__.__backgroundColor = cuegui.Style.ColorTheme.COLOR_GROUP_BACKGROUND
            self.__class__.__type = cuegui.Constants.TYPE_GROUP

        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_GROUP, rpcObject, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  QtCore.QVariant
        @return: The desired data wrapped in a QVariant"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](self.rpcObject)

        if role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        if role == QtCore.Qt.BackgroundRole:
            return self.__backgroundColor

        if role == QtCore.Qt.DecorationRole and col == 0:
            return self.__icon

        if role == QtCore.Qt.UserRole:
            return self.__type

        return cuegui.Constants.QVARIANT_NULL


class LogFinal():
    """Utility class for logging to yaml."""
    def finalize(self, frames, show):
        """Saves logs to yaml. If file not created, will create one."""
        frames_dict = frames

        yaml_path = "/shots/" + show + "/home/etc/stuck_frames_db.yaml"
        if not os.path.exists(yaml_path):
            with open(yaml_path, 'w', encoding='utf-8') as yaml_ob:
                yaml.dump(frames_dict, yaml_ob)

        else:
            with open(yaml_path, 'r', encoding='utf-8') as yaml_ob:
                old_dict = yaml.load(yaml_ob, Loader=yaml.SafeLoader)
            with open(yaml_path, 'w', encoding='utf-8') as yaml_ob:
                for key in frames_dict:  # updates old dict
                    old_dict[key] = frames_dict[key]

                yaml.dump(old_dict, yaml_ob)


class HostWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Represents a host widget."""
    __initialized = False
    # pylint: disable=redefined-builtin,protected-access
    def __init__(self, object, parent):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__commentIcon = QtGui.QIcon(":comment.png")
            self.__class__.__backgroundColor = cuegui.app().palette().color(QtGui.QPalette.Base)
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND

        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(self, cuegui.Constants.TYPE_FRAME,
                                                              object, parent)

    def data(self, col, role):
        if role == QtCore.Qt.DisplayRole:
            if col not in self._cache:
                self._cache[col] = self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](
                    self.rpcObject)
            return self._cache.get(col, cuegui.Constants.QVARIANT_NULL)
        if role == QtCore.Qt.DecorationRole:
            if col == COMMENT_COLUMN and cuegui.Utils.isJob(self.rpcObject):
                return self.__commentIcon
        elif role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor
        return cuegui.Constants.QVARIANT_NULL


class CoreUpWindow(QtWidgets.QDialog):
    """A dialog box for adding more cores to a job."""

    # pylint: disable=non-parent-init-called,super-init-not-called
    def __init__(self, parent, jobs, selected=False):
        QtWidgets.QWidget.__init__(self, parent)
        self.setWindowTitle('Core Up')
        self.jobs = jobs
        self.dj = DJArnold()
        self.setupUI(selected)

    def setupUI(self, selected=False):
        """Setup the initial dialog box layout."""
        # Create initial layout
        build_times = {}
        for job, layers in iteritems(self.jobs):
            build_times[job] = self.dj.getBuildTimes(job, layers)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        self.listWidget = QtWidgets.QListWidget(self)
        self._layers = {}
        for job, layers in iteritems(self.jobs):
            for layer in layers:
                self._layers[layer.name()] = (job, layer)
                layer_label = layer.name()
                # if build_times.has_key(layer.name()):
                #    layer_label += ' - %s' % build_times[layer.name()]
                listItem = QtWidgets.QListWidgetItem(layer_label)
                self.listWidget.addItem(listItem)
        self.listWidget.setSelectionMode(3)  # Multi Selection Mode
        layout.addWidget(self.listWidget)

        buttonLayout = QtWidgets.QHBoxLayout()
        self.core2btn = QtWidgets.QPushButton('2 Cores')
        self.connect(self.core2btn, QtCore.SIGNAL('clicked()'), self.core2btn_callback)
        self.core4btn = QtWidgets.QPushButton('4 Cores')
        self.connect(self.core4btn, QtCore.SIGNAL('clicked()'), self.core4btn_callback)
        self.core8btn = QtWidgets.QPushButton('8 Cores')
        self.connect(self.core8btn, QtCore.SIGNAL('clicked()'), self.core8btn_callback)
        buttonLayout.addWidget(self.core2btn)
        buttonLayout.addWidget(self.core4btn)
        buttonLayout.addWidget(self.core8btn)
        layout.addLayout(buttonLayout)

        coreLayout = QtWidgets.QHBoxLayout()
        self.coreSpinner = QtWidgets.QSpinBox()
        self.coreSpinner.setRange(1, 16)
        self.coreSpinner.setWrapping(True)
        self.coreSpinner.setSingleStep(1)
        self.coreUpButton = QtWidgets.QPushButton('Core Up')
        self.connect(self.coreUpButton, QtCore.SIGNAL('clicked()'), self.coreUpbtn_callback)
        coreLayout.addWidget(self.coreSpinner)
        coreLayout.addWidget(self.coreUpButton)
        layout.addLayout(coreLayout)

        controlLayout = QtWidgets.QHBoxLayout()
        self.retryFramesCB = QtWidgets.QCheckBox('Retry Frames')
        self.retryThresholdSpinner = QtWidgets.QSpinBox()
        self.retryThresholdSpinner.setRange(0, 100)
        self.retryThresholdSpinner.setWrapping(True)
        self.retryThresholdSpinner.setSingleStep(5)
        self.retryThresholdSpinner.setSuffix('%')
        self.retryThresholdSpinner.setEnabled(False)
        self.retryThresholdSpinner.setValue(70)
        controlLayout.addWidget(self.retryFramesCB)
        controlLayout.addWidget(self.retryThresholdSpinner)
        layout.addLayout(controlLayout)

        self.connect(self.retryFramesCB, QtCore.SIGNAL('stateChanged(int)'),
                     self.retryFrameCB_callback)

        if selected:
            self.listWidget.selectAll()

    def selectedLayers(self):
        """Return a list of selected layer rpcObjects."""
        indexs = map(lambda x: str(x.text()), self.listWidget.selectedItems())
        return [self._layers[index] for index in indexs]

    def coreup(self, cores):
        """Set Min Cores to cores for all selected layers of job."""
        for job, layer in self.selectedLayers():
            print("Setting max cores to %d for %s" % (cores, layer.name()))
            layer.setMinCores(cores * 1.0)
            time.sleep(CUE_SLEEP)
            if self.retryFramesCB.isChecked():
                fs = opencue.search.FrameSearch()
                fs.state = [opencue.wrappers.frame.Frame().FrameState(2)]
                frames = layer.getFrames(fs)
                for frame in frames:
                    precentage = self.dj.getCompletionAmount(job, frame)
                    if precentage >= 0:
                        if precentage < self.retryThresholdSpinner.value():
                            print('Retrying frame %s %s' % (job.name(), frame.frame()))
                            frame.kill()
                            time.sleep(CUE_SLEEP)
        self.close()

    def core2btn_callback(self):
        """2 Core Button Callback."""
        self.coreup(2)

    def core4btn_callback(self):
        """4 Core Button Callback."""
        self.coreup(4)

    def core8btn_callback(self):
        """8 Core Button Callback."""
        self.coreup(8)

    def coreUpbtn_callback(self):
        """Core Up Button Callback."""
        cores = int(self.coreSpinner.value())
        self.coreup(cores)

    def retryFrameCB_callback(self, value):
        """Retries frame if value is given."""
        if value:
            self.retryThresholdSpinner.setEnabled(True)
        else:
            self.retryThresholdSpinner.setEnabled(False)


class DJArnold(object):
    """Represents arnold engine."""
    completion_pattern = re.compile(
        # pylint: disable=line-too-long
        r'[INFO BatchMain]:  [0-9][0-9]:[0-9][0-9]:[0-9][0-9] [0-9]{1,8}mb         |    (?P<total>[0-9]{1,3})% done - [0-9]{1,5} rays/pixel')

    def __init__(self, show=None):
        if not show:
            show = os.environ.get('SHOW')
        self.show = show

    def getLog(self, job, frame):
        """Return the contents of a log given a job and a frame."""
        log_dir = job.logDir()
        log_name = '%s.%s.rqlog' % (job.name(), frame.data.name)
        log_file = os.path.join(log_dir, log_name)
        if not os.path.exists(log_file):
            return []
        with open(log_file, 'r', encoding='utf-8') as f:
            log_lines = [line.strip() for line in f.readlines() if line.strip()]

            return log_lines

    def getBuildTimes(self, job, layers=None):
        """Return a dictionary with layer names as keys, and build tiems as
         values.
         """
        results = {}
        if not layers:
            layers = job.getLayers()
        for layer in layers:
            if isinstance(layer, str):
                layer = job.getLayer(layer)
            if 'preprocess' in layer.name():
                continue
            built_frames = []
            cores = 0
            cores_list = []
            fs = opencue.search.FrameSearch()
            fs.states = [opencue.wrappers.frame.Frame().FrameState(3)]
            frames = layer.getFrames(fs)
            if not frames:
                fs.states = [opencue.wrappers.frame.Frame().FrameState(2)]
                frames = layer.getFrames(fs)
            for frame in frames:
                frame_cores = float(frame.lastResource.split('/')[1])
                if frame_cores != cores:
                    if frame_cores not in cores_list:
                        built_frames.append((frame, frame_cores))
                        cores_list.append(frame_cores)
            build_times = []
            for frame, cores in built_frames:
                log_lines = self.getLog(job, frame)
                for line in log_lines:
                    if "[kat] Building scene done." in line:
                        line = line.replace('[INFO BatchMain]:  ', '')
                        build_time = line.split()[0]
                        hours, minutes, seconds = build_time.split(':')
                        seconds = int(seconds)
                        seconds += (int(minutes) * 60)
                        seconds += (int(hours) * 360)
                        build_times.append(seconds)
                if build_times:
                    avg = sum(build_times) / len(build_times)
                    seconds = int(avg % 60)
                    minutes = int((avg / 60) % 60)
                    hours = int(avg / 3600)
                    results[layer.name()] = (layer, datetime.time(hours, minutes, seconds))
        return results

    def getCompletionAmount(self, job, frame):
        """Return a integer representing the last reported completed percenatge on arnold job."""
        log_lines = self.getLog(job, frame)
        log_lines.reverse()
        complete = -1
        for line in log_lines:
            if line.startswith('[INFO BatchMain]:'):
                matches = self.completion_pattern.search(line)
                if matches:
                    complete = int(matches.group('total'))
                    break
        return complete
