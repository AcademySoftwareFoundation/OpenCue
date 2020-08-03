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
A frame list based on AbstractTreeWidget
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import map
from builtins import object
import datetime
import glob
import os
import re
import time

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue
from opencue.compiled_proto import job_pb2

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.eta
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Style
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


QCOLOR_BLACK = QtGui.QColor(QtCore.Qt.black)
QCOLOR_GREEN = QtGui.QColor(QtCore.Qt.green)
STATUS_COLUMN = 3
PROC_COLUMN = 5
CHECKPOINT_COLUMN = 7
RUNTIME_COLUMN = 9
MEMORY_COLUMN = 11
LASTLINE_COLUMN = 15

LOCALRESOURCE = "%s/" % os.getenv("HOST", "unknown").split(".")[0]


class FrameMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):

    job_changed = QtCore.Signal()
    handle_filter_layers_byLayer = QtCore.Signal(list)

    def __init__(self, parent):
        self.frameLogDataBuffer = FrameLogDataBuffer()
        self.frameEtaDataBuffer = FrameEtaDataBuffer()

        self.startColumnsForType(cuegui.Constants.TYPE_FRAME)
        self.addColumn("Order", 60, id=1,
                       data=lambda job, frame: frame.data.dispatch_order,
                       sort=lambda job, frame: frame.data.dispatch_order,
                       tip="The order the frame will be rendered in for it's layer if resources "
                           "are available.")
        self.addColumn("Frame", 70, id=2,
                       data=lambda job, frame: frame.data.number,
                       sort=lambda job, frame: frame.data.number,
                       tip="The number of the frame.")
        self.addColumn("Layer", 250, id=3,
                       data=lambda job, frame: frame.data.layer_name,
                       sort=lambda job, frame: frame.data.layer_name,
                       tip="The layer that the frame is in.")
        self.addColumn("Status", 100, id=4,
                       data=lambda job, frame: job_pb2.FrameState.Name(frame.data.state),
                       sort=lambda job, frame: job_pb2.FrameState.Name(frame.data.state),
                       tip="The status of the frame:\n"
                           "Succeeded: \t The frame finished without errors.\n"
                           "Running: \t The frame is currently running.\n"
                           "Waiting: \t The frame is ready to be run when resources\n"
                           "\t are available.\n"
                           "Depend: \t The frame depends on another frame or job.\n"
                           "Dead: \t The frame failed with an error.")
        self.addColumn("Cores", 55, id=5,
                       data=lambda job, frame: (self.getCores(frame, True) or ""),
                       sort=lambda job, frame: (self.getCores(frame)),
                       tip="The number of cores a frame is using")
        self.addColumn("Host", 120, id=6,
                       data=lambda job, frame: frame.data.last_resource,
                       sort=lambda job, frame: frame.data.last_resource,
                       tip="The last or current resource that the frame used or is using.")
        self.addColumn("Retries", 55, id=7,
                       data=lambda job, frame: frame.data.retry_count,
                       sort=lambda job, frame: frame.data.retry_count,
                       tip="The number of times that each frame has had to retry.")
        self.addColumn("_CheckpointEnabled", 20, id=8,
                       data=lambda job, frame: "",
                       sort=lambda job, frame: (
                               frame.data.checkpoint_state == opencue.api.job_pb2.ENABLED),
                       tip="A green check mark here indicates the frame has written out at least "
                           "1 checkpoint segment.")
        self.addColumn("CheckP", 55, id=9,
                       data=lambda job, frame: frame.data.checkpoint_count,
                       sort=lambda job, frame: frame.data.checkpoint_count,
                       tip="The number of times a frame has been checkpointed.")
        self.addColumn("Runtime", 70, id=10,
                       data=lambda job, frame: (cuegui.Utils.secondsToHMMSS(
                           frame.data.start_time and
                           frame.data.stop_time and
                           frame.data.stop_time - frame.data.start_time or
                           frame.data.start_time and
                           frame.data.stop_time != frame.data.start_time and
                           time.time() - frame.data.start_time or
                           0)),
                       sort=lambda job, frame: (
                               frame.data.start_time and
                               frame.data.stop_time and
                               frame.data.stop_time - frame.data.start_time or
                               frame.data.start_time and
                               frame.data.stop_time != frame.data.start_time and
                               time.time() - frame.data.start_time or
                               0),
                       tip="The amount of HOURS:MINUTES:SECONDS that the frame\n"
                           "has run for or last ran for.\n")

        self.addColumn("LLU", 70, id=11,
                       data=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                self.frameLogDataBuffer.getLastLineData(
                                                    job, frame)[FrameLogDataBuffer.LLU] or ""),
                       sort=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                self.frameLogDataBuffer.getLastLineData(
                                                    job, frame)[FrameLogDataBuffer.LLU] or ""),
                       tip="The amount of HOURS:MINUTES:SECONDS since the last\n"
                           "time the log file was written to. A long period of\n"
                           "time without an update is an indication of a stuck\n"
                           "frame for most types of jobs")

        self.addColumn("Memory", 60, id=12,
                       data=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                cuegui.Utils.memoryToString(frame.data.used_memory) or
                                                cuegui.Utils.memoryToString(frame.data.max_rss)),
                       sort=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                frame.data.used_memory or frame.data.max_rss),
                       tip="If a frame is running:\n"
                           "\t The amount of memory currently used by the frame.\n"
                           "If a frame is not running:\n"
                           "\t The most memory this frame has used at one time.")

        self.addColumn("Remain", 70, id=13,
                       data=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                self.frameEtaDataBuffer.getEtaFormatted(job, frame)
                                                or ""),
                       sort=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                self.frameEtaDataBuffer.getEta(job, frame) or -1),
                       tip="Hours:Minutes:Seconds remaining.")

        self.addColumn("Start Time", 100, id=14,
                       data=lambda job, frame: (self.getTimeString(frame.data.start_time) or ""),
                       sort=lambda job, frame: (self.getTimeString(frame.data.start_time) or ""),
                       tip="The time the frame was started or retried.")
        self.addColumn("Stop Time", 100, id=15,
                       data=lambda job, frame: (self.getTimeString(frame.data.stop_time) or ""),
                       sort=lambda job, frame: (self.getTimeString(frame.data.stop_time) or ""),
                       tip="The time that the frame finished or died.")

        self.addColumn("Last Line", 0, id=16,
                       data=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                self.frameLogDataBuffer.getLastLineData(
                                                    job, frame)[FrameLogDataBuffer.LASTLINE] or ""),
                       sort=lambda job, frame: (frame.data.state == opencue.api.job_pb2.RUNNING and
                                                self.frameLogDataBuffer.getLastLineData(
                                                    job, frame)[FrameLogDataBuffer.LASTLINE] or ""),
                       tip="The last line of a running frame's log file.")

        self.frameSearch = opencue.search.FrameSearch()

        self.__job = None
        self.__jobState = None

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.__sortByColumnCache = {}

        self.itemClicked.connect(self.__itemSingleClickedCopy)
        self.itemClicked.connect(self.__itemSingleClickedViewLog)
        self.itemDoubleClicked.connect(self.__itemDoubleClickedViewLog)
        self.header().sortIndicatorChanged.connect(self.__sortByColumnSave)


        self.__load = None
        self.startTicksUpdate(20)

    def tick(self):
        if self.__load:
            self.__setJob(self.__load)
            self.__load = None
            self.ticksWithoutUpdate = 0
            self._update()
            return

        if self.__job:
            if self.ticksWithoutUpdate > 9990:
                logger.info("doing full update")
                self.ticksWithoutUpdate = 0
                self._update()
                return
            elif self.ticksWithoutUpdate > self.updateInterval:
                logger.info("doing changed update")
                self.ticksWithoutUpdate = 0
                self._updateChanged()
                return

        if self.ticksWithoutUpdate <= self.updateInterval + 1:
            self.ticksWithoutUpdate += 1

        # Redrawing every even number of seconds to see the current frame
        # runtime, LLU and last log line changes. Every second was excessive.
        if not self.ticksWithoutUpdate % 2:
            self.redraw()

    def getCores(self, frame, format=False):
        cores = None

        m = re.search(".*\/(\d+\.?\d*)", frame.data.last_resource)
        if m:
            cores = float(m.group(1))

            if format:
                cores = "{:.2f}".format(cores)

        return cores

    def getTimeString(self, timestamp):
        tstring = None
        if timestamp and timestamp > 0:
            tstring = datetime.datetime.fromtimestamp(timestamp).strftime("%m/%d %H:%M")

        return tstring

    def redrawRunning(self):
        """Forces the running frames to be redrawn with current values"""
        try:
            items = self.findItems("Running",
                                   QtCore.Qt.MatchExactly,
                                   STATUS_COLUMN)
            if items:
                self.dataChanged(self.indexFromItem(items[0], RUNTIME_COLUMN),
                                 self.indexFromItem(items[-1], LASTLINE_COLUMN))
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def __sortByColumnSave(self, logicalIndex, order):
        """Stores the new sort order with the current job's id
        @type  logicalIndex: int
        @param logicalIndex: The column to sort by
        @type  order: Qt::SortOrder
        @param order: The order to sort"""
        if self.__job:
            self.__sortByColumnCache[cuegui.Utils.getObjectKey(self.__job)] = (logicalIndex, order)

    def __sortByColumnLoad(self):
        """Loads the last used sort column and order for the current job, or
        uses default ascending dispatch order"""
        key = self.__job and cuegui.Utils.getObjectKey(self.__job) or None
        settings = self.__sortByColumnCache.get(key, (0, QtCore.Qt.AscendingOrder))
        self.sortByColumn(settings[0], settings[1])

    def __itemSingleClickedCopy(self, item, col):
        """Called when an item is clicked on. Copies selected object names to
        the middle click selection clip board.
        @type  item: QTreeWidgetItem
        @param item: The item single clicked on
        @type  col: int
        @param col: Column number single clicked on"""
        selected = [frame.data.name for frame in self.selectedObjects() if cuegui.Utils.isFrame(frame)]
        if selected:
            QtWidgets.QApplication.clipboard().setText(" ".join(selected))

    def __itemSingleClickedViewLog(self, item, col):
        """Called when an item is clicked on. Views the log file contents
        @type  item: QTreeWidgetItem
        @param item: The item single clicked on
        @type  col: int
        @param col: Column number single clicked on"""
        current_log_file = cuegui.Utils.getFrameLogFile(self.__job, item.rpcObject)
        try:
            old_log_files = sorted(glob.glob('%s.*' % current_log_file),
                                   key=lambda l: int(l.split('rqlog.')[-1]),
                                   reverse=True)
        except ValueError:
            pass
        QtGui.qApp.display_log_file_content.emit([current_log_file] + old_log_files)

    def __itemDoubleClickedViewLog(self, item, col):
        """Called when a frame is double clicked, views the frame log in a popup
        @type  item: QTreeWidgetItem
        @param item: The item double clicked on
        @type  col: int
        @param col: Column number double clicked on"""
        frame = item.rpcObject
        if frame.data.state == opencue.api.job_pb2.RUNNING:
            cuegui.Utils.popupFrameTail(self.__job, frame)
        else:
            cuegui.Utils.popupFrameView(self.__job, frame)

    def setJob(self, job):
        if job is None:
            return self.__setJob(None)
        job = cuegui.Utils.findJob(job)
        if job:
            self.__load = job

    def __setJob(self, job):
        """Sets the current job
        @param job: Job can be None, a job object, or a job name.
        @type  job: job, string, None"""
        self.frameSearch = opencue.search.FrameSearch()
        self.__job = job
        self.__jobState = None
        self.removeAllItems()
        self.__sortByColumnLoad()
        self._lastUpdate = 0
        self.job_changed.emit()

    def getJob(self):
        """Returns the current job
        @return: The current job
        @rtype:  job"""
        return self.__job

    def clearFilters(self):
        self.clearSelection()
        self.frameSearch = opencue.search.FrameSearch()
        self.sortByColumn(0, QtCore.Qt.AscendingOrder)
        self.updateRequest()

    def selectByStatus(self, status):
        """Selects all frames that match the given status
        @type  status: string
        @param status: A frame status to match"""
        items = self.findItems(str(status),
                               QtCore.Qt.MatchContains | QtCore.Qt.MatchWrap,
                               STATUS_COLUMN)

        # Select all found items
        for item in items:
            item.setSelected(True)

        if items:
            # Scroll to the first item
            self.scrollToItem(items[0], QtWidgets.QAbstractItemView.PositionAtTop)

    def _createItem(self, object):
        """Creates and returns the proper item"""
        return FrameWidgetItem(object, self, self.__job)

#
#    updateRequest        -> _update        -> _getUpdate        -> _processUpdate
#    updateChangedRequest -> _updateChanged -> _getUpdateChanged -> _processUpdateChanged
#
#    autoUpdate -> updateRequest
#    updateAll -> updateRequest
#    _updateAll -> _update
#

    def updateRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 9999

    def updateChangedRequest(self):
        """Updates the items in the TreeWidget if sufficient time has passed
        since last updated"""
        self.ticksWithoutUpdate = 999

    def _update(self):
        """Updates the items in the TreeWidget without checking when it was last
        updated"""
        logger.info("_update")
        self._lastUpdate = time.time()
        if hasattr(QtGui.qApp, "threadpool"):
            QtGui.qApp.threadpool.queue(self._getUpdate, self._processUpdate, "getting data for %s" % self.__class__)
        else:
            logger.warning("threadpool not found, doing work in gui thread")
            self._processUpdate(None, self._getUpdate())

    def _updateChanged(self):
        """Updates the items in the TreeWidget without checking when it was last
        updated"""
        logger.info("_updateChanged")
        self._lastUpdate = time.time()
        if hasattr(QtGui.qApp, "threadpool"):
            QtGui.qApp.threadpool.queue(self._getUpdateChanged, self._processUpdateChanged, "getting data for %s" % self.__class__)
        else:
            logger.warning("threadpool not found, doing work in gui thread")
            self._processUpdateChanged(None, self._getUpdateChanged())

    def _getUpdate(self):
        """Returns all (<=1000) requested frames from the cuebot"""
        logger.info("_getUpdate")
        try:
            if self.__job:
                self.__lastUpdateTime = int(time.time())
                return self.__job.getFrames(**self.frameSearch.options)
            return []
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def _getUpdateChanged(self):
        """Returns the updated data from the cuebot
        @rtype:  None or List<Frame>
        @return: The results from the cuebot"""
        logger.info("_getUpdateChanged")
        if not self.__job or \
           (self.__jobState and self.__jobState == opencue.api.job_pb2.FINISHED):
            logger.debug("no job or job is finished, bailing")
            return []
        logger.info(" + Nth update = %s" % self.__class__)
        updatedFrames = []
        try:
            updated_data = self.__job.getUpdatedFrames(self.__lastUpdateTime)
            self.__lastUpdateTime = updated_data.server_time
            self.__jobState = updated_data.state
            updatedFrames = updated_data.updated_frames.updated_frames

        except opencue.EntityNotFoundException as e:
            self.setJobObj(None)
        except Exception as e:
            if hasattr(e, "message") and e.message.find("timestamp cannot be over a minute off") != -1:
                logger.warning("Forcing a full update due to: %s" % e.message)
                return None
            else:
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

        logger.info(" - %s" % self.__class__)
        return updatedFrames

    def _processUpdate(self, work, rpcObjects):
        """Remove all items currently in the list.
        Create new TreeWidgetItems for all new rpcObjects.
        @param work:
        @type  work: from ThreadPool
        @param rpcObjects: A list of rpcObjects
        @type  rpcObjects: list<rpcObject> """
        logger.info("_processUpdate")
        try:
            self._itemsLock.lockForWrite()
            try:
                self.clear()
                self._items = {}
                if rpcObjects:
                    for rpcObject in rpcObjects:
                        self._items[cuegui.Utils.getObjectKey(rpcObject)] = self._createItem(rpcObject)
            finally:
                self._itemsLock.unlock()
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def _processUpdateChanged(self, work, rpcObjects):
        """Update existing TreeWidgetItems if an item already exists for the rpcObject.
        Remove items that were not updated with rpcObjects.
        @param work: from ThreadPool
        @type  work:
        @param rpcObjects: A list of rpcObjects
        @type  rpcObjects: list<rpcObject> """
        logger.info("_processUpdateChanged")
        try:
            if rpcObjects is None:
                # Update request time must be off, do a full update
                logger.warning("rpcObjects is None")
                self.updateRequest()
            else:
                self._itemsLock.lockForWrite()
                try:
                    for updatedFrame in rpcObjects:
                        # If id already exists, update it
                        self._updateFrame(updatedFrame)
                finally:
                    self._itemsLock.unlock()

            logger.info("_processUpdateChanged calling redraw")
            self.redraw()

        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def _updateFrame(self, updatedFrame):
        """Update the frame object on a WidgetItem with the values from a UpdatedFrame object.
        @type updatedFrame: job_pb2.UpdatedFrame
        @param updatedFrame: UpdatedFrame to copy values from."""
        logger.info("_updateFrame")
        frameWidget = self._items.get('Frame.{}'.format(updatedFrame.id))
        if frameWidget:
            for field in list(job_pb2.UpdatedFrame.DESCRIPTOR.fields_by_name.keys()):
                if field != "id":
                    setattr(frameWidget.rpcObject.data, field, getattr(updatedFrame, field))

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = FrameContextMenu(self, self._actionFilterSelectedLayers)
        menu.exec_(e.globalPos())

    def _actionFilterSelectedLayers(self):
        """Called when the menu item Filter Selected Layers is clicked"""
        results = {}
        for frame in self.selectedObjects():
            results[frame.layer()] = True
        self.handle_filter_layers_byLayer[str].emit(list(results.keys()))


class FrameWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    __initialized = False
    def __init__(self, object, parent, job):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__backgroundColor = QtGui.qApp.palette().color(QtGui.QPalette.Base)
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND
            self.__class__.__foregroundColorBlack = QCOLOR_BLACK
            self.__class__.__foregroundColorGreen = QCOLOR_GREEN
            self.__class__.__alignCenter = QtCore.Qt.AlignCenter
            self.__class__.__alignRight = QtCore.Qt.AlignRight
            self.__class__.__rgbFrameState = {}
            for key in cuegui.Constants.RGB_FRAME_STATE:
                self.__class__.__rgbFrameState[key] = cuegui.Constants.RGB_FRAME_STATE[key]
            self.__class__.__type = cuegui.Constants.TYPE_FRAME
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_FRAME, object, parent, job)
        self.__show = job.data.show

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](
                self._source, self.rpcObject)

        elif role == QtCore.Qt.ForegroundRole:
            if col == STATUS_COLUMN:
                return self.__foregroundColorBlack
            elif col == PROC_COLUMN and self.rpcObject.data.last_resource.startswith(LOCALRESOURCE):
                return self.__foregroundColorGreen
            else:
                return self.__foregroundColor

        elif role == QtCore.Qt.BackgroundRole and col == STATUS_COLUMN:
            return self.__rgbFrameState[self.rpcObject.data.state]

        elif role == QtCore.Qt.DecorationRole and col == CHECKPOINT_COLUMN:
            if self.rpcObject.data.checkpoint_state == opencue.api.job_pb2.ENABLED:
                return QtGui.QIcon(":markdone.png")
        elif role == QtCore.Qt.TextAlignmentRole:
            if col == STATUS_COLUMN:
                return self.__alignCenter

            if col == PROC_COLUMN:
                return self.__alignRight

        elif role == QtCore.Qt.UserRole:
            return self.__type

        return cuegui.Constants.QVARIANT_NULL

    def __lt__(self, other):
        """Custom sorting for columns that have a function defined for sorting"""
        sortLambda = self.column_info[self.treeWidget().sortColumn()][cuegui.AbstractWidgetItem.SORT_LAMBDA]
        if sortLambda:
            return sortLambda(self._source, self.rpcObject) < sortLambda(
                other._source, other.rpcObject)

        return QtWidgets.QTreeWidgetItem.__lt__(self, other)


class FrameLogDataBuffer(object):
    """A cached and threaded interface to reading the last log line"""
    maxCacheTime = 5
    maxThreads = 2
    maxQueue = 500

    # Position of data from getLastLineData
    LASTLINE = 0
    LLU = 1

    # Notes for percentage:
    # PERCENT = 2
    # go back 15 lines?
    # default to "" prior to checking
    # default to 0% if nothing found unless already a previous value

    def __init__(self):
        from .ThreadPool import ThreadPool

        self.__threadPool = ThreadPool(self.maxThreads, self.maxQueue)
        self.__currentJob = None
        self.__cache = {}
        self.__queue = {}

        self.__defaultLine = ""
        self.__defaultLLU = ""

        # Position of data in self.__cache
        self.__TIME = 0
        self.__PATH = 1
        self.__LINE = 2
        self.__LLU = 3

    def getLastLineData(self, job, frame):
        """Returns the last line and LLU of the log file or queues a request to update
        it"""
        try:
            __now = time.time()
            jobKey = cuegui.Utils.getObjectKey(job)
            if self.__currentJob != jobKey:
                # New job so clear cache
                self.__cache.clear()
                self.__queue.clear()
                self.__currentJob = jobKey

            if len(self.__queue) > len(self.__threadPool._q_queue):
                # Everything is hung up, start over
                self.__cache.clear()
                self.__queue.clear()

            frameKey = cuegui.Utils.getObjectKey(frame)
            if frameKey in self.__cache:
                # Last line is cached
                __cached = self.__cache[frameKey]
                if __cached[self.__TIME] < __now - self.maxCacheTime:
                    # Its an old cache, queue an update
                    self.__cache[frameKey][0] = __now + 60
                    self.__queue[frameKey] = __cached[self.__PATH]
                    self.__threadPool.queue(self.__doWork, self.__saveWork,
                                            "getting data for %s" % self.__class__)
                # Return the cached results anyway
                return (__cached[self.__LINE], __cached[self.__LLU])
            else:
                __path = cuegui.Utils.getFrameLogFile(job, frame)
                # Cache a blank entry until it is filled in
                self.__cache[frameKey] = [__now + 60,
                                             __path,
                                             self.__defaultLine,
                                             self.__defaultLLU]
                # Queue an update
                self.__queue[frameKey] = __path
                self.__threadPool.queue(self.__doWork, self.__saveWork,
                                        "getting data for %s" % self.__class__)
                # Since nothing is updated yet, return an empty string
                return (self.__defaultLine, self.__defaultLLU)
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def __doWork(self):
        """Pops work from the queue and returns the proxy and last log line"""
        try:
            if self.__queue:
                (proxy, path) = self.__queue.popitem()
                if os.path.exists(path):
                    return (proxy,
                            cuegui.Utils.getLastLine(path),
                            cuegui.Utils.secondsToHHMMSS(time.time() - os.stat(path).st_mtime))
                else:
                    return None
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

    def __saveWork(self, work, results):
        """Stores the resulting last log line to the cache with the proxy key"""
        try:
            if results:
                __cached = self.__cache[results[0]]
                __cached[self.__TIME] = time.time()
                __cached[self.__LINE] = results[1]
                __cached[self.__LLU] = results[2]
        except KeyError as e:
            # Could happen while switching jobs with work in the queue
            pass
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))


class FrameEtaDataBuffer(object):
    """A cached and threaded interface to reading the last log line"""
    maxCacheTime = 60
    maxThreads = 2
    maxQueue = 501


    def __init__(self):
        from .ThreadPool import ThreadPool

        self.__threadPool = ThreadPool(self.maxThreads, self.maxQueue)
        self.__currentJob = None
        self.__cache = {}

        self.__defaultETA = ''

        self.__TIME = 0
        self.__ETA = 1

    def getEtaFormatted(self, job, frame):
        result = self.getEta(job, frame)
        if result:
            return cuegui.Utils.secondsToHHMMSS(result)
        return False

    def getEta(self, job, frame):
        __now = time.time()
        try:
            jobKey = cuegui.Utils.getObjectKey(job)
            if self.__currentJob != jobKey:
                # New job so clear cache
                self.__cache.clear()
                self.__currentJob = jobKey

            frameKey = cuegui.Utils.getObjectKey(frame)
            if frameKey in self.__cache:
                # Frame eta is cached
                __cached = self.__cache[frameKey]
                if __cached[self.__TIME] < __now - self.maxCacheTime:
                    # It is an old cache, queue an update, reset the time until updated
                    self.__cache[frameKey][0] = __now + 60
                    self.__threadPool.queue(self.__doWork, self.__saveWork,
                                            "getting data for %s" % self.__class__, frameKey, job, frame)
                # Return the cached results anyway
                if __cached[self.__ETA] is not None:
                    return max(__cached[self.__ETA] - __now + __cached[self.__TIME], 0)
            else:
                # Queue an update, cache a blank entry until updated
                self.__cache[frameKey] = [__now + 60, None]
                self.__threadPool.queue(self.__doWork, self.__saveWork,
                                        "getting data for %s" % self.__class__, frameKey, job, frame)
                # Since nothing is updated yet, return a default
        except Exception as e:
            self.__cache[frameKey] = [__now,
                                         None]
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))

        return self.__defaultETA

    def __doWork(self, proxy, job, frame):
        """Pops work from the queue and returns the proxy and last log line"""
        try:
            return (proxy, cuegui.eta.ETASeconds(job, frame))
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return (proxy, self.__defaultETA)

    def __saveWork(self, work, results):
        """Stores the resulting last log line to the cache with the proxy key"""
        try:
            if results:
                __cached = self.__cache[results[0]]
                __cached[self.__TIME] = time.time()
                __cached[self.__ETA] = results[1]
        except KeyError as e:
            # Could happen while switching jobs with work in the queue
            pass
        except Exception as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))


class FrameContextMenu(QtWidgets.QMenu):
    def __init__(self, widget, filterSelectedLayersCallback):
        super(FrameContextMenu, self).__init__()

        self.__menuActions = cuegui.MenuActions.MenuActions(
            widget, widget.updateSoon, widget.selectedObjects, widget.getJob)

        count = len(widget.selectedItems())

        self.__menuActions.frames().addAction(self, "tail")
        self.__menuActions.frames().addAction(self, "view")

        if count == 1:
            if widget.selectedObjects()[0].data.retry_count >= 1:
                self.__menuActions.frames().addAction(self, "viewLastLog")

        if count >= 3:
            self.__menuActions.frames().addAction(self, "xdiff3")
        elif count == 2:
            self.__menuActions.frames().addAction(self, "xdiff2")

        self.__menuActions.frames().addAction(self, "useLocalCores")

        if QtGui.qApp.applicationName() == "CueCommander":
            self.__menuActions.frames().addAction(self, "viewHost")

        depend_menu = QtWidgets.QMenu("&Dependencies", self)
        self.__menuActions.frames().addAction(depend_menu, "viewDepends")
        self.__menuActions.frames().addAction(depend_menu, "dependWizard")
        self.__menuActions.frames().addAction(depend_menu, "getWhatThisDependsOn")
        self.__menuActions.frames().addAction(depend_menu, "getWhatDependsOnThis")
        depend_menu.addSeparator()
        self.__menuActions.frames().addAction(depend_menu, "dropDepends")
        self.__menuActions.frames().addAction(depend_menu, "markAsWaiting")
        self.__menuActions.frames().addAction(depend_menu, "markdone")

        self.addMenu(depend_menu)
        self.addSeparator()

        self.__menuActions.frames().createAction(self, "Filter Selected Layers", None,
                                                 filterSelectedLayersCallback, "stock-filters")
        self.__menuActions.frames().addAction(self, "reorder")
        self.addSeparator()
        self.__menuActions.frames().addAction(self, "previewMain")
        self.__menuActions.frames().addAction(self, "previewAovs")
        self.addSeparator()
        self.__menuActions.frames().addAction(self, "retry")
        self.__menuActions.frames().addAction(self, "eat")
        self.__menuActions.frames().addAction(self, "kill")
        self.__menuActions.frames().addAction(self, "eatandmarkdone")

