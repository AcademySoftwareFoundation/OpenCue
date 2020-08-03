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
A layer list based on AbstractTreeWidget
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from PySide2 import QtCore
from PySide2 import QtWidgets

from opencue.exception import EntityNotFoundException

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.MenuActions
import cuegui.Utils


def displayRange(layer):
    if layer.data.chunk_size != 1:
        return '%s chunked %s' % (layer.data.range, layer.data.chunk_size)
    return layer.data.range


class LayerMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):

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
        self.addColumn("Range", 150, id=5,
                       data=lambda layer: displayRange(layer),
                       tip="The range of frames that the layer should render.")
        self.addColumn("Cores", 45, id=6,
                       data=lambda layer: "%.2f" % layer.data.min_cores,
                       sort=lambda layer: layer.data.min_cores,
                       tip="The number of cores that the frames in this layer\n"
                           "will reserve as a minimum.")
        self.addColumn("Memory", 60, id=7,
                       data=lambda layer: cuegui.Utils.memoryToString(layer.data.min_memory),
                       sort=lambda layer: layer.data.min_memory,
                       tip="The amount of memory that each frame in this layer\n"
                           "will reserve for its use. If the frame begins to use\n"
                           "more memory than this, the cuebot will increase this\n"
                           "number.")
        self.addColumn("Gpu", 40, id=8,
                       data=lambda layer: cuegui.Utils.memoryToString(layer.data.min_gpu),
                       sort=lambda layer: layer.data.min_gpu,
                       tip="The amount of gpu memory each frame in this layer\n"
                           "will reserve for its use. Note that we may not have\n"
                           "machines as much gpu memory as you request.")
        self.addColumn("MaxRss", 60, id=9,
                       data=lambda layer: cuegui.Utils.memoryToString(layer.data.layer_stats.max_rss),
                       sort=lambda layer: layer.data.layer_stats.max_rss,
                       tip="Maximum amount of memory used by any frame in\n"
                           "this layer at any time since the job was launched.")
        self.addColumn("Total", 40, id=10,
                       data=lambda layer: layer.data.layer_stats.total_frames,
                       sort=lambda layer: layer.data.layer_stats.total_frames,
                       tip="Total number of frames in this layer.")
        self.addColumn("Done", 40, id=11,
                       data=lambda layer: layer.data.layer_stats.succeeded_frames,
                       sort=lambda layer: layer.data.layer_stats.succeeded_frames,
                       tip="Total number of done frames in this layer.")
        self.addColumn("Run", 40, id=12,
                       data=lambda layer: layer.data.layer_stats.running_frames,
                       sort=lambda layer: layer.data.layer_stats.running_frames,
                       tip="Total number or running frames in this layer.")
        self.addColumn("Depend", 53, id=13,
                       data=lambda layer: layer.data.layer_stats.depend_frames,
                       sort=lambda layer: layer.data.layer_stats.depend_frames,
                       tip="Total number of dependent frames in this layer.")
        self.addColumn("Wait", 40, id=14,
                       data=lambda layer: layer.data.layer_stats.waiting_frames,
                       sort=lambda layer: layer.data.layer_stats.waiting_frames,
                       tip="Total number of waiting frames in this layer.")
        self.addColumn("Eaten", 40, id=15,
                       data=lambda layer: layer.data.layer_stats.eaten_frames,
                       sort=lambda layer: layer.data.layer_stats.eaten_frames,
                       tip="Total number of eaten frames in this layer.")
        self.addColumn("Dead", 40, id=16,
                       data=lambda layer: layer.data.layer_stats.dead_frames,
                       sort=lambda layer: layer.data.layer_stats.dead_frames,
                       tip="Total number of dead frames in this layer.")
        self.addColumn("Avg", 65, id=17,
                       data=lambda layer: cuegui.Utils.secondsToHHMMSS(layer.data.layer_stats.avg_frame_sec),
                       sort=lambda layer: layer.data.layer_stats.avg_frame_sec,
                       tip="Average number of HOURS:MINUTES:SECONDS per frame\n"
                           "in this layer.")
        self.addColumn("Tags", 100, id=18,
                       data=lambda layer: " | ".join(layer.data.tags),
                       tip="The tags define what resources may be booked on\n"
                           "frames in this layer.")

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.itemDoubleClicked.connect(self.__itemDoubleClickedFilterLayer)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects, self.getJob)
        self.__job = None

        self.disableUpdate = False
        self.__load = None
        self.startTicksUpdate(20, False, 60*60*24)

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

    def setJob(self, job):
        """Sets the current job
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
        __selectedObjects = self.selectedObjects()

        menu = QtWidgets.QMenu()

        self.__menuActions.layers().addAction(menu, "view")
        depend_menu = QtWidgets.QMenu("&Dependencies", self)
        self.__menuActions.layers().addAction(depend_menu, "viewDepends")
        self.__menuActions.layers().addAction(depend_menu, "dependWizard")
        depend_menu.addSeparator()
        self.__menuActions.layers().addAction(depend_menu, "markdone")
        menu.addMenu(depend_menu)

        if len(__selectedObjects) == 1:
            menu.addSeparator()
            self.__menuActions.layers().addAction(menu, "useLocalCores")
            if len(set([layer.data.range for layer in __selectedObjects])) == 1:
                self.__menuActions.layers().addAction(menu, "reorder")
            self.__menuActions.layers().addAction(menu, "stagger")

        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "setProperties")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "kill")
        self.__menuActions.layers().addAction(menu, "eat")
        self.__menuActions.layers().addAction(menu, "retry")
        if [layer for layer in __selectedObjects if layer.data.layer_stats.dead_frames]:
            menu.addSeparator()
            self.__menuActions.layers().addAction(menu, "retryDead")

        menu.exec_(e.globalPos())

    def __itemDoubleClickedFilterLayer(self, item, col):
        self.handle_filter_layers_byLayer.emit([item.rpcObject.data.name])

class LayerWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    def __init__(self, object, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_LAYER, object, parent)
