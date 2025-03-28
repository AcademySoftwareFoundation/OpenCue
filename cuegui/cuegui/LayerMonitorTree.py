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


"""Tree widget for displaying a list of layers."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import functools

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from opencue.exception import EntityNotFoundException
from opencue.api import job_pb2

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.MenuActions
import cuegui.Utils

logger = cuegui.Logger.getLogger(__file__)


def displayRange(layer):
    """Returns a string representation of a layer's frame range."""
    if layer.data.chunk_size != 1:
        return '%s chunked %s' % (layer.data.range, layer.data.chunk_size)
    return layer.data.range


class LayerMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of layers."""

    handle_filter_layers_byLayer = QtCore.Signal(list)

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_LAYER)
        self.addColumn("dispatchOrder", 0, id=1,
                       data=lambda layer: layer.data.dispatch_order,
                       sort=lambda layer: layer.data.dispatch_order)
        self.addColumn("Name", 250, id=2,
                       data=lambda layer: layer.data.name,
                       tip="Name of the layer.")
        self.addColumn("Services", 100, id=3,
                       data=lambda layer: ",".join(layer.data.services),
                       tip="The underlying application being run within the frames.")
        self.addColumn("Limits", 100, id=4,
                       data=lambda layer: ",".join(layer.data.limits),
                       tip="The limits that have been applied to this layer's frames.")
        # pylint: disable=unnecessary-lambda
        self.addColumn("Range", 150, id=5,
                       data=lambda layer: displayRange(layer),
                       tip="The range of frames that the layer should render.")
        self.addColumn("Cores", 45, id=6,
                       data=lambda layer: self.labelCoresColumn(layer.data.min_cores),
                       sort=lambda layer: layer.data.min_cores,
                       tip="The number of cores that the frames in this layer\n"
                           "will reserve as a minimum."
                           "Zero or negative value indicate that the layer will use\n"
                           "all available cores on the machine, minus this value.")
        self.addColumn("Memory", 60, id=7,
                       data=lambda layer: cuegui.Utils.memoryToString(layer.data.min_memory),
                       sort=lambda layer: layer.data.min_memory,
                       tip="The amount of memory that each frame in this layer\n"
                           "will reserve for its use. If the frame begins to use\n"
                           "more memory than this, the cuebot will increase this\n"
                           "number.")
        self.addColumn("Gpus", 45, id=8,
                       data=lambda layer: "%d" % layer.data.min_gpus,
                       sort=lambda layer: layer.data.min_gpus,
                       tip="The number of gpus that the frames in this layer\n"
                           "will reserve as a minimum.")
        self.addColumn("Gpu Memory", 40, id=9,
                       data=lambda layer: cuegui.Utils.memoryToString(layer.data.min_gpu_memory),
                       sort=lambda layer: layer.data.min_gpu_memory,
                       tip="The amount of gpu memory each frame in this layer\n"
                           "will reserve for its use. Note that we may not have\n"
                           "machines as much gpu memory as you request.")
        self.addColumn(
            "MaxRss", 60, id=10,
            data=lambda layer: cuegui.Utils.memoryToString(layer.data.layer_stats.max_rss),
            sort=lambda layer: layer.data.layer_stats.max_rss,
            tip="Maximum amount of memory used by any frame in\n"
                "this layer at any time since the job was launched.")
        self.addColumn("Total", 40, id=11,
                       data=lambda layer: layer.data.layer_stats.total_frames,
                       sort=lambda layer: layer.data.layer_stats.total_frames,
                       tip="Total number of frames in this layer.")
        self.addColumn("Done", 40, id=12,
                       data=lambda layer: layer.data.layer_stats.succeeded_frames,
                       sort=lambda layer: layer.data.layer_stats.succeeded_frames,
                       tip="Total number of done frames in this layer.")
        self.addColumn("Run", 40, id=13,
                       data=lambda layer: layer.data.layer_stats.running_frames,
                       sort=lambda layer: layer.data.layer_stats.running_frames,
                       tip="Total number or running frames in this layer.")
        self.addColumn("Depend", 53, id=14,
                       data=lambda layer: layer.data.layer_stats.depend_frames,
                       sort=lambda layer: layer.data.layer_stats.depend_frames,
                       tip="Total number of dependent frames in this layer.")
        self.addColumn("Wait", 40, id=15,
                       data=lambda layer: layer.data.layer_stats.waiting_frames,
                       sort=lambda layer: layer.data.layer_stats.waiting_frames,
                       tip="Total number of waiting frames in this layer.")
        self.addColumn("Eaten", 40, id=16,
                       data=lambda layer: layer.data.layer_stats.eaten_frames,
                       sort=lambda layer: layer.data.layer_stats.eaten_frames,
                       tip="Total number of eaten frames in this layer.")
        self.addColumn("Dead", 40, id=17,
                       data=lambda layer: layer.data.layer_stats.dead_frames,
                       sort=lambda layer: layer.data.layer_stats.dead_frames,
                       tip="Total number of dead frames in this layer.")
        self.addColumn(
            "Avg", 65, id=18,
            data=lambda layer: cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.avg_frame_sec),
            sort=lambda layer: layer.data.layer_stats.avg_frame_sec,
            tip="Average number of HOURS:MINUTES:SECONDS per frame\nin this layer.")
        self.addColumn("Tags", 100, id=19,
                       data=lambda layer: " | ".join(layer.data.tags),
                       tip="The tags define what resources may be booked on\n"
                           "frames in this layer.")
        self.addColumn("Progress", 100, id=20,
                        delegate=cuegui.ItemDelegate.ProgressDelegate,
                        data=lambda layer: layer.percentCompleted(),
                        sort=lambda layer: layer.percentCompleted(),
                        tip="Progress for the Layer")
        self.addColumn("Timeout", 45, id=21,
                       data=lambda layer: cuegui.Utils.secondsToHHHMM(layer.data.timeout*60),
                       sort=lambda layer: layer.data.timeout,
                       tip="Timeout for the frames, Hours:Minutes")
        self.addColumn("Timeout LLU", 45, id=22,
                       data=lambda layer: cuegui.Utils.secondsToHHHMM(layer.data.timeout_llu*60),
                       sort=lambda layer: layer.data.timeout_llu,
                       tip="Timeout for a frames\' LLU, Hours:Minutes")
        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # pylint: disable=no-member
        self.itemSelectionChanged.connect(self.__itemSelectionChangedFilterLayer)
        cuegui.app().select_layers.connect(self.__handle_select_layers)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects, self.getJob)
        self.__job = None

        self.disableUpdate = False
        self.__load = None
        self.startTicksUpdate(20, False, 60*60*24)

    # pylint: disable=attribute-defined-outside-init
    def tick(self):
        if self.__load:
            self.__job = self.__load
            self.__load = None
            self.ticksWithoutUpdate = 0
            if not self.disableUpdate:
                self._update()
            return

        if self.__job:
            if self.tickNeedsUpdate() and not self.disableUpdate:
                self.ticksWithoutUpdate = 0
                self._update()
                return

        self.ticksWithoutUpdate += 1

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 9999

    def labelCoresColumn(self, reserved_cores):
        """Returns the reserved cores for a job"""
        if reserved_cores > 0:
            return "%.2f" % reserved_cores
        if reserved_cores == 0:
            return "ALL"
        return "ALL (%.2f)" % reserved_cores

    # pylint: disable=inconsistent-return-statements
    def setJob(self, job):
        """Sets the current job.

        @param job: Job can be None, a job object, or a job name.
        @type  job: job, string, None"""
        if job is None:
            return self.__setJob(None)
        job = cuegui.Utils.findJob(job)
        if job:
            self.__load = job

    def __setJob(self, job):
        """Sets the current job
        @param job: Job can be None, a job object, or a job name.
        @type  job: job, string, None"""
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.__job = job
        self.removeAllItems()

    def getJob(self):
        """Gets the current job."""
        return self.__job

    def _createItem(self, obj):
        """Creates and returns the proper item"""
        return LayerWidgetItem(obj, self)

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        if self.__job:
            try:
                return self.__job.getLayers()
            except EntityNotFoundException:
                self.setJob(None)
                return []
        return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        readonly = (cuegui.Constants.FINISHED_JOBS_READONLY_LAYER and
                    self.__job and self.__job.state() == job_pb2.FINISHED)

        __selectedObjects = self.selectedObjects()

        menu = QtWidgets.QMenu()

        self.__menuActions.layers().addAction(menu, "view")

        if (len(cuegui.Constants.OUTPUT_VIEWERS) > 0
                and sum(len(layer.getOutputPaths()) for layer in __selectedObjects) > 0):
            for viewer in cuegui.Constants.OUTPUT_VIEWERS:
                action = QtWidgets.QAction(QtGui.QIcon(":viewoutput.png"),
                                           viewer['action_text'], self)
                action.triggered.connect(
                    functools.partial(cuegui.Utils.viewOutput,
                                    __selectedObjects,
                                    viewer['action_text']))
                menu.addAction(action)

        depend_menu = QtWidgets.QMenu("&Dependencies", self)
        self.__menuActions.layers().addAction(depend_menu, "viewDepends")
        self.__menuActions.layers().addAction(depend_menu, "dependWizard")
        depend_menu.addSeparator()
        self.__menuActions.layers().addAction(depend_menu, "markdone")
        menu.addMenu(depend_menu)

        if len(__selectedObjects) == 1:
            menu.addSeparator()
            if int(self.app.settings.value("DisableDeeding", 0)) == 0:
                self.__menuActions.layers().addAction(menu, "useLocalCores") \
                    .setEnabled(not readonly)
            if len({layer.data.range for layer in __selectedObjects}) == 1:
                self.__menuActions.layers().addAction(menu, "reorder").setEnabled(not readonly)
            self.__menuActions.layers().addAction(menu, "stagger").setEnabled(not readonly)

        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "setProperties").setEnabled(not readonly)
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "kill").setEnabled(not readonly)
        self.__menuActions.layers().addAction(menu, "eat").setEnabled(not readonly)
        self.__menuActions.layers().addAction(menu, "retry").setEnabled(not readonly)
        if [layer for layer in __selectedObjects if layer.data.layer_stats.dead_frames]:
            menu.addSeparator()
            self.__menuActions.layers().addAction(menu, "retryDead").setEnabled(not readonly)

        menu.exec_(e.globalPos())

    def __itemSelectionChangedFilterLayer(self):
        """Filter FrameMonitor to selected Layers.
        Emits signal to filter FrameMonitor to selected Layers.
        Also emits signal for other widgets to select Layers.
        """
        layers = self.selectedObjects()
        layer_names = [layer.data.name for layer in layers]

        # emit signal to filter Frame Monitor
        self.handle_filter_layers_byLayer.emit(layer_names)

        # emit signal to select Layers in other widgets
        cuegui.app().select_layers.emit(layers)

    def __handle_select_layers(self, layerRpcObjects):
        """Select incoming Layers in tree.
        Slot connected to QtGui.qApp.select_layers inorder to handle
        selecting Layers in Tree.
        Also emits signal to filter FrameMonitor
        """
        received_layers = [l.data.name for l in layerRpcObjects]
        current_layers = [l.data.name for l in self.selectedObjects()]
        if received_layers == current_layers:
            # prevent recursion
            return

        # prevent unnecessary calls to __itemSelectionChangedFilterLayer
        self.blockSignals(True)
        try:
            for item in self._items.values():
                item.setSelected(False)
            for layer in layerRpcObjects:
                objectKey = cuegui.Utils.getObjectKey(layer)
                if objectKey not in self._items:
                    self.addObject(layer)
                item = self._items[objectKey]
                item.setSelected(True)
        finally:
            # make sure signals are re-enabled
            self.blockSignals(False)

        # emit signal to filter Frame Monitor
        self.handle_filter_layers_byLayer.emit(received_layers)


class LayerWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single layer."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_LAYER, rpcObject, parent)
