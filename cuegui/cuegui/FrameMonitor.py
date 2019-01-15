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


import math
from copy import deepcopy

import Logger
from FrameMonitorTree import FrameMonitorTree
from Manifest import QtCore, QtWidgets, opencue, FileSequence

log = Logger.getLogger(__file__)


class FrameMonitor(QtWidgets.QWidget):
    """This contains the frame list table with controls at the top"""

    handle_filter_layers_byLayer = QtCore.Signal(list)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.frameMonitorTree = FrameMonitorTree(self)
        self.page = self.frameMonitorTree.frameSearch.page
        # Setup main vertical layout
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(4)

        # This hlayout would contain any filter/control buttons
        hlayout = QtWidgets.QHBoxLayout()
        self._refreshButtonSetup(hlayout)    # Button to refresh
        self._clearButtonSetup(hlayout)      # Button to clear all filters
        self._pageButtonSetup(hlayout)  # Button to flip page
        self._selectStatusSetup(hlayout)  # Menu to select frames by status
        self._filterLayersSetup(hlayout)  # Menu to filter layers
        self._filterStatusSetup(hlayout)  # Menu to filter frames by status
        #For the filter range setup: self._filterRangeSetup(hlayout)
        hlayout.addStretch()
        hlayout.addWidget(QtWidgets.QLabel("(Limited to 1000 frames)"))
        hlayout.addStretch()
        self._displayJobNameSetup(hlayout)

        self.layout().addLayout(hlayout)
        self.layout().addWidget(self.frameMonitorTree)

        self._frameRangeSelectionFilterSetup(self.layout())

    def updateRequest(self):
        self.frameMonitorTree.updateRequest()

    def updateChangedRequest(self):
        self.frameMonitorTree.updateChangedRequest()

    def setJob(self, job):
        self.frameMonitorTree.setJob(job)

    def getColumnWidths(self):
        return self.frameMonitorTree.getColumnWidths()

    def setColumnWidths(self, widths):
        self.frameMonitorTree.setColumnWidths(widths)

    def getColumnVisibility(self):
        return self.frameMonitorTree.getColumnVisibility()

    def setColumnVisibility(self, settings):
        self.frameMonitorTree.setColumnVisibility(settings)

# ==============================================================================
# Frame range bar to filter by frame range
# ==============================================================================
    def _frameRangeSelectionFilterSetup(self, layout):
        from FrameRangeSelection import FrameRangeSelectionWidget
        widget = FrameRangeSelectionWidget(self)
        layout.addWidget(widget)
        widget.selectionChanged.connect(self._frameRangeSelectionFilterHandle)
        self.frameRangeSelection = widget
        self.frameMonitorTree.job_changed.connect(self._frameRangeSelectionFilterHandle)

    def _frameRangeSelectionFilterUpdate(self):
        if not self.frameMonitorTree.getJob():
            self.frameRangeSelection.setFrameRange(["1","10000"])
        else:
            layers = self.frameMonitorTree.getJob().getLayers()

            _min = None
            _max = None

            for layer in layers:
                seq = FileSequence.FrameSet(layer.range())
                seq.normalize()

                if _min is not None:
                    _min = min(_min, int(seq[0]))
                else:
                    _min = int(seq[0])

                if _max is not None:
                    _max = max(_max, int(seq[-1]))
                else:
                    _max = int(seq[-1])

            if _min == _max:
                _max += 1

            self.frameRangeSelection.default_select_size = 1000/len(layers)

            self.frameRangeSelection.setFrameRange(["%s" % _min,"%s" % _max])

    def _frameRangeSelectionFilterHandle(self, start, end):
        self.frameMonitorTree.frameSearch = opencue.search.FrameSearch.criteriaFromOptions(
            range="%s-%s" % (start, end))
        self.frameMonitorTree.updateRequest()

# ==============================================================================
# Widgets to filter by frame range
# ==============================================================================
    def _filterRangeSetup(self, layout):
        btn = QtWidgets.QSpinBox(self)
        btn.setValue(1)
        layout.addWidget(btn)
        self.filter_range_start_box = btn

        btn = QtWidgets.QSpinBox(self)
        btn.setValue(1000)
        layout.addWidget(btn)
        self.filter_range_end_box = btn

        btn = QtWidgets.QPushButton("Set Frame Range")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(btn)
        self.filter_range_btn = btn
        btn.clicked.connect(self._filterRangeHandle)

    def _filterRangeHandle(self):
        value = "%s-%s" % (self.filter_range_start_box.value(), self.filter_range_end_box.value())
        self.frameMonitorTree.frameSearch.setOptions(range=value)

# ==============================================================================
# Button to refresh
# ==============================================================================
    def _refreshButtonSetup(self, layout):
        """Sets up the refresh button, adds it to the given layout
        @param layout: The layout to add the button to
        @type  layout: QLayout"""
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        self.btn_refresh.setFocusPolicy(QtCore.Qt.NoFocus)
        layout.addWidget(self.btn_refresh)
        self.btn_refresh.clicked.connect(self.frameMonitorTree.updateRequest)
        self.frameMonitorTree.updated.connect(self._refreshButtonDisableHandle)

    def _refreshButtonEnableHandle(self):
        """Called when the refresh button should be enabled"""
        self.btn_refresh.setEnabled(True)

    def _refreshButtonDisableHandle(self):
        """Called when the refresh button should be disabled"""
        self.btn_refresh.setEnabled(False)
        QtCore.QTimer.singleShot(5000, self._refreshButtonEnableHandle)

# ==============================================================================
# Button to clear all filters
# ==============================================================================
    def _clearButtonSetup(self, layout):
        """Sets up the clear button, adds it to the given layout
        @param layout: The layout to add the button to
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Clear")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        layout.addWidget(btn)
        btn.clicked.connect(self._clearButtonHandle)

    def _clearButtonHandle(self):
        """Called when the clear button is clicked"""
        self._filterStatusClear()
        self._filterLayersUpdate()
        self._frameRangeSelectionFilterUpdate()
        self.frameMonitorTree.clearFilters()

# ==============================================================================
# Widgets to Load previous/next page
# ==============================================================================
    def _pageButtonSetup(self, layout):
        '''Sets up the page flipping buttons and the page # label
        @param layout: The layout to add the buttons & label to
        @type layout: QLayout'''

        # Previous page button
        self.prev_page_btn = QtWidgets.QPushButton("<")
        self.prev_page_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.prev_page_btn.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.prev_page_btn)
        self.prev_page_btn.clicked.connect(lambda: self._pageButtonsHandle(-1))

        # Next page button
        self.next_page_btn = QtWidgets.QPushButton(">")
        self.next_page_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.next_page_btn.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.next_page_btn)
        self.next_page_btn.clicked.connect(lambda: self._pageButtonsHandle(1))
        self.frameMonitorTree.job_changed.connect(self._updatePageButtonState)

        # Page number label
        self.page_label = QtWidgets.QLabel('')
        layout.addWidget(self.page_label)

        # Update Status
        self._updatePageButtonState()

    def _pageButtonsHandle(self, offset):
        '''Called When the "next page" or the "previous page" button is pressed.
        Updates the FrameSearch by adding the given "offset" value to the page
        attribute and updating the frameSearch result
        @param offset: The offset value to add to the page attribute in the
                       frameSearch
        @type offset: int'''
        self.page += offset
        self.frameMonitorTree.frameSearch.page = self.page
        self.frameMonitorTree.updateRequest()
        self._updatePageButtonState()

    def _updatePageButtonState(self):
        '''Called when a new job is selected, or when any of the frame filters
        is changed. Updates the "next page" & the "previous page" button state,
        as well as the page # label.
        '''
        self.prev_page_btn.setEnabled(not self.page == 1)
        self.next_page_btn.setEnabled(False)
        job = self.frameMonitorTree.getJob()
        if not job:
            self.page_label.setText('')
            return

        total_frames = job.totalFrames()
        if total_frames <= 1000:
            self.page_label.setText('<font color="gray">{0}</font>'
                                    .format('Page 1 of 1'))
            return

        has_filters = False
        for menu in [self._filterLayersButton.menu(),
                     self._filterStatusButton.menu()]:
            if menu and not has_filters:
                for item in menu.actions():
                    if item.isChecked():
                        has_filters = True
                        break
        total_pages = int(math.ceil(total_frames / 1000.0))
        page_label_text = 'Page {0}'.format(self.page)
        if has_filters:
            temp_search = deepcopy(self.frameMonitorTree.frameSearch)
            temp_search.page = self.page + 1
            temp_frames = job.getFrames(temp_search)
            self.next_page_btn.setEnabled(len(temp_frames) > 0)
        else:
            page_label_text += ' of {0}'.format(total_pages)
            self.next_page_btn.setEnabled(self.page < total_pages)

        self.page_label.setText('<font color="gray">{0}</font>'
                                .format(page_label_text))

# ==============================================================================
# Menu to select frames by status
# ==============================================================================
    def _selectStatusSetup(self, layout):
        """Sets up the select status menu, adds it to the given layout
        @param layout: The layout to add the menu to
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Select Status")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        btn.setFlat(True)

        layout.addWidget(btn)
        self.select_status_btn = btn

        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        menu.triggered.connect(self._selectStatusHandle)

        for item in ["Clear", None, "Succeeded", "Running", "Waiting", "Depend", "Dead", "Eaten"]:
            if item:
                menu.addAction(item)
            else:
                menu.addSeparator()

    def _selectStatusHandle(self, action):
        """Called when an option in the select status menu is triggered
        @param action: Defines the menu option that was selected
        @type  action: QAction"""
        if action.text() == "Clear":
            self.frameMonitorTree.clearSelection()
        else:
            self.frameMonitorTree.selectByStatus(action.text())

# ==============================================================================
# Menu to filter frames by layers
# ==============================================================================
    def _filterLayersSetup(self, layout):
        """Sets up the filter layers menu, adds it to the given layout
        @param layout: The layout to add the menu to
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Filter Layers")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        btn.setFlat(True)

        layout.addWidget(btn)
        self._filterLayersButton = btn

        self.frameMonitorTree.job_changed.connect(self._filterLayersUpdate)

        # For "Filter Selected Layers" on frame selection right click and double click
        self.frameMonitorTree.handle_filter_layers_byLayer.connect(
            self._filterLayersHandleByLayer)

    def _filterLayersUpdate(self):
        """Updates the filter layers menu with the layers in the current job"""
        btn = self._filterLayersButton
        menu = btn.menu()
        if menu:
            for action in menu.actions():
                menu.removeAction(action)
        else:
            menu = QtWidgets.QMenu(self)
            btn.setMenu(menu)
            menu.triggered[QtWidgets.QAction].connect(self._filterLayersHandle)

        if self.frameMonitorTree.getJob():
            layers = [x.data.name for x in self.frameMonitorTree.getJob().getLayers()]
        else:
            layers = []

        for item in ["Clear", None ] + sorted(layers):
            if item:
                a = QtWidgets.QAction(menu)
                a.setText(item)
                if item != "Clear":
                    a.setCheckable(True)
                menu.addAction(a)
            else:
                menu.addSeparator()

    def _filterLayersHandle(self, action):
        """Called when an option in the filter layers menu is triggered.
        Tells the FrameMonitorTree widget what layers to filter by.
        @param action: Defines the menu item selected
        @type  action: QAction"""
        if action.text() == "Clear":
            for item in self._filterLayersButton.menu().actions():
                if item.isChecked():
                    self.frameMonitorTree.frameSearch.layers.remove("%s" % item.text())
                    item.setChecked(False)
        else:
            if action.isChecked():
                self.frameMonitorTree.frameSearch.layers.append("%s" % action.text())
                self.page = 1
                self.frameMonitorTree.frameSearch.page = self.page
            else:
                self.frameMonitorTree.frameSearch.layers.remove("%s" % action.text())

        self.frameMonitorTree.updateRequest()
        self._updatePageButtonState()

    def _filterLayersHandleByLayer(self, layer_list):
        """When the FrameMonitorTree widget emits a:
        "handle_filter_layers_byLayer(PyQt_PyObject)"
        This function will be called and filter the display according to the
        layers provided by the signal.
        @param layer_list: A list of layers to filter by.
        @type  layer_list: list<string>"""
        for item in self._filterLayersButton.menu().actions():
            # If item is checked and not in list: remove
            if item.isChecked() and not item.text() in layer_list:
                self.frameMonitorTree.frameSearch.layers.remove(str(item.text()))
                item.setChecked(False)
            # if item is not checked, and item is in list: add
            elif not item.isChecked() and item.text() in layer_list:
                self.frameMonitorTree.frameSearch.layers.append(str(item.text()))
                item.setChecked(True)
                self.page = 1
                self.frameMonitorTree.frameSearch.page = self.page

        self.frameMonitorTree.updateRequest()
        self._updatePageButtonState()

# ==============================================================================
# Menu to filter frames by status
# ==============================================================================
    def _filterStatusSetup(self, layout):
        """Sets up the filter status menu, adds it to the given layout
        @param layout: The layout to add the menu to
        @type  layout: QLayout"""
        btn = QtWidgets.QPushButton("Filter Status")
        btn.setFocusPolicy(QtCore.Qt.NoFocus)
        btn.setContentsMargins(0,0,0,0)
        btn.setFlat(True)

        menu = QtWidgets.QMenu(self)
        btn.setMenu(menu)
        menu.triggered.connect(self._filterStatusHandle)

        for item in [("Clear", QtCore.Qt.ALT + QtCore.Qt.Key_QuoteLeft),
                     None,
                     ("Succeeded", QtCore.Qt.ALT + QtCore.Qt.Key_1),
                     ("Running", QtCore.Qt.ALT + QtCore.Qt.Key_2),
                     ("Waiting", QtCore.Qt.ALT + QtCore.Qt.Key_3),
                     ("Depend", QtCore.Qt.ALT + QtCore.Qt.Key_4),
                     ("Dead", QtCore.Qt.ALT + QtCore.Qt.Key_5),
                     ("Eaten", QtCore.Qt.ALT + QtCore.Qt.Key_6)]:
            if item:
                a = QtWidgets.QAction(item[0], menu)
                if item[0] != "Clear":
                    a.setCheckable(True)
                if item[1]:
                    a.setShortcut(item[1])
                menu.addAction(a)
            else:
                menu.addSeparator()

        layout.addWidget(btn)
        self._filterStatusButton = btn

        self.frameMonitorTree.job_changed.connect(self._filterStatusClear)

    def _filterStatusClear(self):
        """Clears the currently selected status menu items"""
        btn = self._filterStatusButton
        menu = btn.menu()
        for action in menu.actions():
            action.setChecked(False)

    def _filterStatusHandle(self, action):
        """Called when an option in the filter status menu is triggered.
        Tells the FrameMonitorTree widget what status to filter by.
        @param action: Defines the menu item selected
        @type  action: QAction"""
        __frameSearch = self.frameMonitorTree.frameSearch
        if action.text() == "Clear":
            for item in self._filterStatusButton.menu().actions():
                if item.isChecked():
                    if item.text() != "Clear":
                        __state = getattr(opencue.job_pb2.FrameState, str(item.text()))
                        __frameSearch.states.remove(__state)
                    item.setChecked(False)
        else:
            self.page = 1
            self.frameMonitorTree.frameSearch.page = self.page
            __state = getattr(opencue.job_pb2.FrameState, str(action.text()))
            if action.isChecked():
                __frameSearch.states.append(__state)
            else:
                __frameSearch.states.remove(__state)

        self._updatePageButtonState()
        self.frameMonitorTree.updateRequest()

# ==============================================================================
# QLabel that displays the job name
# ==============================================================================
    def _displayJobNameSetup(self, layout):
        """Sets up the displaying the name of the currently job.
        @param layout: The layout to add the label to
        @type  layout: QLayout"""
        self._displayJobNameLabel = QtWidgets.QLabel()
        self._displayJobNameLabel.setMinimumWidth(1)
        layout.addWidget(self._displayJobNameLabel)

        self.frameMonitorTree.job_changed.connect(self._displayJobNameUpdate)

    def _displayJobNameUpdate(self):
        """Updates the display job name label with the name of the current job."""
        if self.frameMonitorTree.getJob():
            self._displayJobNameLabel.setText("   <font color=\"green\">%s</font>   " % self.frameMonitorTree.getJob().data.name)
        else:
            self._displayJobNameLabel.clear()
