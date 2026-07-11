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


"""Widget for displaying a list of frames with controls at the top."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import str
from copy import deepcopy
import math

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
import grpc

import FileSequence
from opencue_proto import job_pb2

import cuegui.FrameMonitorTree
import cuegui.FrameRangeSelection
import cuegui.Logger


log = cuegui.Logger.getLogger(__file__)


class FrameMonitor(QtWidgets.QWidget):
    """Widget for displaying a list of frames with controls at the top."""

    handle_filter_layers_byLayer = QtCore.Signal(list)

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.frameMonitorTree = cuegui.FrameMonitorTree.FrameMonitorTree(self)
        self.page = self.frameMonitorTree.frameSearch.page
        self.frameSearchLimit = self.frameMonitorTree.frameSearch.limit
        # Filter Layers menu widgets, populated lazily in _filterLayersUpdate.
        self._filterLayersSearchBox = None
        self._filterLayersList = None
        # Guards against itemChanged firing while the list is populated/synced
        # programmatically.
        self._filterLayersUpdating = False
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
        hlayout.addStretch()
        hlayout.addWidget(QtWidgets.QLabel("(Limited to {0} frames)"
                                           .format(self.frameSearchLimit)))
        hlayout.addStretch()
        self._displayJobNameSetup(hlayout)

        self.layout().addLayout(hlayout)
        self.layout().addWidget(self.frameMonitorTree)

        self._frameRangeSelectionFilterSetup(self.layout())

    def updateRequest(self):
        """Requests an update of the frame list."""
        self.frameMonitorTree.updateRequest()

    def updateChangedRequest(self):
        """Updates the frame list if sufficient time has passed since last updated."""
        self.frameMonitorTree.updateChangedRequest()

    def setJob(self, job):
        """Sets the current job."""
        self.frameMonitorTree.setJob(job)

    def getColumnWidths(self):
        """Gets the table column widths."""
        return self.frameMonitorTree.getColumnWidths()

    def setColumnWidths(self, widths):
        """Sets the table column widths."""
        self.frameMonitorTree.setColumnWidths(widths)

    def getColumnVisibility(self):
        """Gets the table column visibility."""
        return self.frameMonitorTree.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets the table column visibility."""
        self.frameMonitorTree.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets the table column order."""
        return self.frameMonitorTree.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets the table column order."""
        self.frameMonitorTree.setColumnOrder(settings)

    def filterLayersFromDoubleClick(self, layerNames):
        """Event handler for filtering layers."""
        self._filterLayersHandleByLayer(layerNames)

    # ==============================================================================
    # Frame range bar to filter by frame range
    # ==============================================================================
    def _frameRangeSelectionFilterSetup(self, layout):
        widget = cuegui.FrameRangeSelection.FrameRangeSelectionWidget(self)
        layout.addWidget(widget)
        widget.selectionChanged.connect(self._frameRangeSelectionFilterHandle)
        self.frameRangeSelection = widget
        self.frameMonitorTree.job_changed.connect(self._frameRangeSelectionFilterUpdate)

    def _frameRangeSelectionFilterUpdate(self):
        if not self.frameMonitorTree.getJob():
            self.frameRangeSelection.setFrameRange(["1", str(self.frameSearchLimit)])
        else:
            try:
                layers = self.frameMonitorTree.getJob().getLayers()

                _min = None
                _max = None

                for layer in layers:
                    seq = FileSequence.FrameSet(layer.range())
                    seq.normalize()
                    frameList = seq.getAll()
                    if _min is not None:
                        _min = min(_min, int(frameList[0]))
                    else:
                        _min = int(frameList[0])

                    if _max is not None:
                        _max = max(_max, int(frameList[-1]))
                    else:
                        _max = int(frameList[-1])

                if _min == _max:
                    _max += 1

                self.frameRangeSelection.default_select_size = self.frameSearchLimit // len(layers)

                self.frameRangeSelection.setFrameRange([str(_min), str(_max)])
            except grpc.RpcError as e:
                # Handle gRPC connection errors gracefully
                # pylint: disable=no-member
                if hasattr(e, 'code') and e.code() in [grpc.StatusCode.CANCELLED,
                                                         grpc.StatusCode.UNAVAILABLE]:
                    log.warning(
                        "gRPC connection interrupted while updating frame range filter, will retry")
                else:
                    log.error("gRPC error in _frameRangeSelectionFilterUpdate: %s", e)
                # pylint: enable=no-member
                # Set a default range if we can't get layers
                self.frameRangeSelection.setFrameRange(["1", str(self.frameSearchLimit)])

    def _frameRangeSelectionFilterHandle(self, start, end):
        self.frameMonitorTree.frameSearch.options['range'] = "%s-%s" % (start, end)
        self.frameMonitorTree.updateRequest()

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
        self.btn_refresh.clicked.connect(self.frameMonitorTree.updateRequest)  # pylint: disable=no-member
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
        btn.clicked.connect(self._clearButtonHandle)  # pylint: disable=no-member

    def _clearButtonHandle(self):
        """Called when the clear button is clicked"""
        self._filterStatusClear()
        self._filterLayersUpdate()
        self._frameRangeSelectionFilterUpdate()
        self.frameMonitorTree.clearFilters()
        self._updatePageButtonState()

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
        self.prev_page_btn.clicked.connect(lambda: self._pageButtonsHandle(-1))  # pylint: disable=no-member

        # Next page button
        self.next_page_btn = QtWidgets.QPushButton(">")
        self.next_page_btn.setFocusPolicy(QtCore.Qt.NoFocus)
        self.next_page_btn.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.next_page_btn)
        self.next_page_btn.clicked.connect(lambda: self._pageButtonsHandle(1))  # pylint: disable=no-member
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
        self.frameMonitorTree.frameSearch.options['page'] = self.page
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
        if total_frames <= self.frameSearchLimit:
            self.page_label.setText('<font color="gray">{0}</font>'
                                    .format('Page 1 of 1'))
            return

        has_filters = False
        # Layer filters live in the embedded, scrollable list widget.
        if self._filterLayersList:
            for i in range(self._filterLayersList.count()):
                if self._filterLayersList.item(i).checkState() == QtCore.Qt.Checked:
                    has_filters = True
                    break
        # Status filters are plain checkable menu actions.
        if not has_filters and self._filterStatusButton.menu():
            for item in self._filterStatusButton.menu().actions():
                if item.isChecked():
                    has_filters = True
                    break
        total_pages = int(math.ceil(total_frames / float(self.frameSearchLimit)))
        page_label_text = 'Page {0}'.format(self.page)
        if has_filters:
            temp_search = deepcopy(self.frameMonitorTree.frameSearch)
            temp_search.page = self.page + 1
            temp_frames = job.getFrames(**temp_search.options)
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
        menu.triggered.connect(self._selectStatusHandle)  # pylint: disable=no-member

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
        if not menu:
            menu = QtWidgets.QMenu(self)
            btn.setMenu(menu)

            # Build a single embedded widget: a search box, a fixed-height
            # scrollable checkable list, and a Clear button. Using a
            # QListWidget guarantees vertical scrolling regardless of the
            # platform's Qt style, instead of the default QMenu behaviour of
            # wrapping thousands of layers into off-screen columns.
            container = QtWidgets.QWidget(menu)
            vlayout = QtWidgets.QVBoxLayout(container)
            vlayout.setContentsMargins(2, 2, 2, 2)
            vlayout.setSpacing(2)

            search_box = QtWidgets.QLineEdit(container)
            search_box.setPlaceholderText("Search layers...")
            search_box.setClearButtonEnabled(True)
            search_box.textChanged.connect(self._filterLayersSearch)
            vlayout.addWidget(search_box)

            layer_list = QtWidgets.QListWidget(container)
            layer_list.setMinimumWidth(250)
            layer_list.setMaximumHeight(400)
            layer_list.itemChanged.connect(self._filterLayersHandle)
            vlayout.addWidget(layer_list)

            clear_btn = QtWidgets.QPushButton("Clear", container)
            clear_btn.clicked.connect(self._filterLayersClear)
            vlayout.addWidget(clear_btn)

            widget_action = QtWidgets.QWidgetAction(menu)
            widget_action.setDefaultWidget(container)
            menu.addAction(widget_action)
            menu.aboutToShow.connect(search_box.setFocus)

            self._filterLayersSearchBox = search_box
            self._filterLayersList = layer_list

        if self.frameMonitorTree.getJob():
            try:
                layers = [x.data.name for x in self.frameMonitorTree.getJob().getLayers()]
            except grpc.RpcError as e:
                # Handle gRPC connection errors gracefully
                # pylint: disable=no-member
                if hasattr(e, 'code') and e.code() in [grpc.StatusCode.CANCELLED,
                                                         grpc.StatusCode.UNAVAILABLE]:
                    log.warning(
                        "gRPC connection interrupted while updating layer filter, will retry")
                else:
                    log.error("gRPC error in _filterLayersUpdate: %s", e)
                # pylint: enable=no-member
                layers = []
        else:
            layers = []

        # Preserve any active layer filters across the rebuild.
        checked = set(self.frameMonitorTree.frameSearch.options.get('layer', []))
        self._filterLayersUpdating = True
        try:
            self._filterLayersList.clear()
            for name in sorted(layers):
                list_item = QtWidgets.QListWidgetItem(name, self._filterLayersList)
                list_item.setFlags(list_item.flags() | QtCore.Qt.ItemIsUserCheckable)
                list_item.setCheckState(
                    QtCore.Qt.Checked if name in checked else QtCore.Qt.Unchecked)
        finally:
            self._filterLayersUpdating = False
        self._filterLayersSearchBox.clear()

    def _filterLayersSearch(self, text):
        """Shows only the layers whose name contains the search text.
        @param text: The text typed into the filter layers search box
        @type  text: str"""
        if not self._filterLayersList:
            return
        text = text.strip().lower()
        for i in range(self._filterLayersList.count()):
            list_item = self._filterLayersList.item(i)
            list_item.setHidden(text not in str(list_item.text()).lower())

    def _filterLayersHandle(self, item):
        """Called when a layer checkbox in the filter layers list is toggled.
        Tells the FrameMonitorTree widget what layers to filter by.
        @param item: The list item whose check state changed
        @type  item: QListWidgetItem"""
        if self._filterLayersUpdating:
            return
        layers = self.frameMonitorTree.frameSearch.options.get('layer', [])
        name = str(item.text())
        if item.checkState() == QtCore.Qt.Checked:
            if name not in layers:
                layers.append(name)
            self.page = 1
            self.frameMonitorTree.frameSearch.page = self.page
            # getFrames() reads the page from options; keep it in sync so the
            # filtered results start on page 1 rather than the current page.
            self.frameMonitorTree.frameSearch.options['page'] = self.page
        elif name in layers:
            layers.remove(name)
        self.frameMonitorTree.frameSearch.options['layer'] = layers

        self.frameMonitorTree.updateRequest()
        self._updatePageButtonState()

    def _filterLayersClear(self):
        """Unchecks every layer filter."""
        layers = self.frameMonitorTree.frameSearch.options.get('layer', [])
        self._filterLayersUpdating = True
        try:
            for i in range(self._filterLayersList.count()):
                list_item = self._filterLayersList.item(i)
                if list_item.checkState() == QtCore.Qt.Checked:
                    list_item.setCheckState(QtCore.Qt.Unchecked)
                    name = str(list_item.text())
                    if name in layers:
                        layers.remove(name)
        finally:
            self._filterLayersUpdating = False
        self.frameMonitorTree.frameSearch.options['layer'] = layers

        self.frameMonitorTree.updateRequest()
        self._updatePageButtonState()

    def _filterLayersHandleByLayer(self, layer_list):
        """When the FrameMonitorTree widget emits a:
        "handle_filter_layers_byLayer(PyQt_PyObject)"
        This function will be called and filter the display according to the
        layers provided by the signal.
        @param layer_list: A list of layers to filter by.
        @type  layer_list: list<string>"""
        layers = self.frameMonitorTree.frameSearch.options.get('layer', [])
        self._filterLayersUpdating = True
        try:
            for i in range(self._filterLayersList.count()):
                list_item = self._filterLayersList.item(i)
                name = str(list_item.text())
                is_checked = list_item.checkState() == QtCore.Qt.Checked
                # If checked and not in list: remove
                if is_checked and name not in layer_list:
                    if name in layers:
                        layers.remove(name)
                    list_item.setCheckState(QtCore.Qt.Unchecked)
                # If not checked and in list: add
                elif not is_checked and name in layer_list:
                    layers.append(name)
                    list_item.setCheckState(QtCore.Qt.Checked)
                    self.page = 1
                    self.frameMonitorTree.frameSearch.page = self.page
                    # getFrames() reads the page from options; keep it in sync
                    # so filtered results start on page 1.
                    self.frameMonitorTree.frameSearch.options['page'] = self.page
        finally:
            self._filterLayersUpdating = False
        self.frameMonitorTree.frameSearch.options['layer'] = layers

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
        menu.triggered.connect(self._filterStatusHandle)  # pylint: disable=no-member

        for item in [("Clear", QtCore.Qt.ALT | QtCore.Qt.Key_QuoteLeft),
                     None,
                     ("Succeeded", QtCore.Qt.ALT | QtCore.Qt.Key_1),
                     ("Running", QtCore.Qt.ALT | QtCore.Qt.Key_2),
                     ("Waiting", QtCore.Qt.ALT | QtCore.Qt.Key_3),
                     ("Depend", QtCore.Qt.ALT | QtCore.Qt.Key_4),
                     ("Dead", QtCore.Qt.ALT | QtCore.Qt.Key_5),
                     ("Eaten", QtCore.Qt.ALT | QtCore.Qt.Key_6)]:
            if item:
                a = QtWidgets.QAction(item[0], menu)
                if item[0] != "Clear":
                    a.setCheckable(True)
                if item[1]:
                    a.setShortcut(QtGui.QKeySequence(item[1]))
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
        states = __frameSearch.options.get('state', [])
        if action.text() == "Clear":
            for item in self._filterStatusButton.menu().actions():
                if item.isChecked():
                    if item.text() != "Clear":
                        __state = getattr(job_pb2, str(item.text()).upper())
                        states.remove(__state)
                    item.setChecked(False)
        else:
            self.page = 1
            self.frameMonitorTree.frameSearch.page = self.page
            self.frameMonitorTree.frameSearch.options['page'] = self.page
            __state = getattr(job_pb2, str(action.text()).upper())
            if action.isChecked():
                states.append(__state)
            else:
                states.remove(__state)
        __frameSearch.options['state'] = states

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
            self._displayJobNameLabel.setText(
                "   <font color=\"green\">%s</font>   " % self.frameMonitorTree.getJob().data.name)
        else:
            self._displayJobNameLabel.clear()
