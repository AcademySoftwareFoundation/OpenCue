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


"""Tree widget for displaying a show/job hierarchy."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from builtins import str
from builtins import map
import time

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue
import opencue.compiled_proto.job_pb2
import opencue.wrappers.group

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.ItemDelegate
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Style
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

COLUMN_COMMENT = 1
COLUMN_EAT = 2
COLUMN_MAXRSS = 13
FONT_BOLD = QtGui.QFont("Luxi Sans", -1, QtGui.QFont.Bold)
UPDATE_INTERVAL = 22


def getEta(stats):
    """Gets estimated time remaining for a job."""
    if stats.runningFrames:
        remaining = (((stats.pendingFrames - 1) * stats.avgFrameSec) + stats.highFrameSec)
        if remaining:
            return cuegui.Utils.secondsToHHHMM(remaining // stats.runningFrames)
    return "-"


class CueJobMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a show/job hierarchy."""

    view_object = QtCore.Signal(object)
    single_click = QtCore.Signal(object)

    def __init__(self, parent):

        self.__shows = {}
        self.currtime = time.time()

        self.startColumnsForType(cuegui.Constants.TYPE_JOB)
        self.addColumn(
            "Job", 550, id=1, data=lambda job: job.data.name,
            tip="The name of the job: show-shot-user_uniqueName\n\n"
                "The color behind the job will change to:\n"
                "Blue \t if it is paused\n"
                "Red \t if it has dead frames\n"
                "Green \t if it has no running frames with frames waiting\n"
                "Purple \t if all remaining frames depend on something\n"
                "Yellow \t if the maxRss is over %sKb" % cuegui.Constants.MEMORY_WARNING_LEVEL)
        self.addColumn("_Comment", 20, id=2,
                       sort=lambda job: job.data.has_comment,
                       tip="A comment icon will appear if a job has a comment. You\n"
                           "may click on it to view the comments.")
        self.addColumn("_Autoeat", 20, id=3,
                       sort=lambda job: job.data.auto_eat,
                       tip="If the job has auto eating enabled, a pac-man icon\n"
                           "will appear here and all frames that become dead will\n"
                           "automatically be eaten.")
        self.addColumn("Run", 38, id=4,
                       data=lambda job: job.data.job_stats.running_frames,
                       sort=lambda job: job.data.job_stats.running_frames,
                       tip="The number of running frames.")
        self.addColumn("Cores", 55, id=5,
                       data=lambda job: "%.02f" % job.data.job_stats.reserved_cores,
                       sort=lambda job: job.data.job_stats.reserved_cores,
                       tip="The number of reserved cores.")
        self.addColumn("Gpus", 55, id=6,
                       data=lambda job: "%d" % job.data.job_stats.reserved_gpus,
                       sort=lambda job: job.data.job_stats.reserved_gpus,
                       tip="The number of reserved gpus.")
        self.addColumn("Wait", 45, id=7,
                       data=lambda job: job.data.job_stats.waiting_frames,
                       sort=lambda job: job.data.job_stats.waiting_frames,
                       tip="The number of waiting frames.")
        self.addColumn("Depend", 55, id=8,
                       data=lambda job: job.data.job_stats.depend_frames,
                       sort=lambda job: job.data.job_stats.depend_frames,
                       tip="The number of dependent frames.")
        self.addColumn("Total", 50, id=9,
                       data=lambda job: job.data.job_stats.total_frames,
                       sort=lambda job: job.data.job_stats.total_frames,
                       tip="The total number of frames.")
        self.addColumn("_Booking Bar", 150, id=10,
                       delegate=cuegui.ItemDelegate.JobBookingBarDelegate)
        self.addColumn("Min", 38, id=11,
                       data=lambda job: "%.0f" % job.data.min_cores,
                       sort=lambda job: job.data.min_cores,
                       tip="The minimum number of running cores that the cuebot\n"
                           "will try to maintain.")
        self.addColumn("Max", 38, id=12,
                       data=lambda job: "%.0f" % job.data.max_cores,
                       sort=lambda job: job.data.max_cores,
                       tip="The maximum number of running cores that the cuebot\n"
                           "will allow.")
        self.addColumn("Min Gpus", 38, id=13,
                       data=lambda job: "%d" % job.data.min_gpus,
                       sort=lambda job: job.data.min_gpus,
                       tip="The minimum number of running gpus that the cuebot\n"
                           "will try to maintain.")
        self.addColumn("Max Gpus", 38, id=14,
                       data=lambda job: "%d" % job.data.max_gpus,
                       sort=lambda job: job.data.max_gpus,
                       tip="The maximum number of running gpus that the cuebot\n"
                           "will allow.")
        self.addColumn(
            "Age", 50, id=15,
            data=lambda job: cuegui.Utils.secondsToHHHMM(self.currtime - job.data.start_time),
            sort=lambda job: self.currtime - job.data.start_time,
            tip="The HOURS:MINUTES since the job was launched.")
        self.addColumn("Pri", 30, id=16,
                       data=lambda job: job.data.priority,
                       sort=lambda job: job.data.priority,
                       tip="The job priority. The cuebot uses this as a suggestion\n"
                           "to determine what job needs the next available matching\n"
                           "resource.")
        self.addColumn("ETA", 65, id=17,
                       data=lambda job: "",
                       tip="(Inacurate and disabled until a better solution exists)\n"
                           "A very rough estimate of the number of HOURS:MINUTES\n"
                           "it will be before the entire job is done.")
        self.addColumn("MaxRss", 60, id=18,
                       data=lambda job: cuegui.Utils.memoryToString(job.data.job_stats.max_rss),
                       sort=lambda job: job.data.job_stats.max_rss,
                       tip="The most memory used at one time by any single frame.")
        self.addColumn("MaxGpuMem", 60, id=19,
                       data=lambda job: cuegui.Utils.memoryToString(job.data.job_stats.max_gpu_mem),
                       sort=lambda job: job.data.job_stats.max_gpu_mem,
                       tip="The most gpu memory used at one time by any single frame.")
        self.addColumn("_Blank", 20, id=20,
                       tip="Spacer")
        self.addColumn("Progress", 0, id=21,
                       delegate=cuegui.ItemDelegate.JobThinProgressBarDelegate,
                       tip="A visual overview of the job progress.\n"
                           "Green \t is succeeded\n"
                           "Yellow \t is running\n"
                           "Red \t is dead\n"
                           "Purple \t is waiting on a dependency\n"
                           "Light Blue \t is waiting to be booked")

        for itemType in [cuegui.Constants.TYPE_GROUP, cuegui.Constants.TYPE_ROOTGROUP]:
            self.startColumnsForType(itemType)
            self.addColumn("", 0, id=1,
                           data=lambda group: group.data.name)
            self.addColumn("", 0, id=2)
            self.addColumn("", 0, id=3)
            self.addColumn("", 0, id=4,
                           data=lambda group: group.data.stats.running_frames)
            self.addColumn("", 0, id=5,
                           data=lambda group: "%.2f" % group.data.stats.reserved_cores)
            self.addColumn("", 0, id=6,
                           data=lambda group: "%d" % group.data.stats.reserved_gpus)
            self.addColumn("", 0, id=7,
                           data=lambda group: group.data.stats.waiting_frames)
            self.addColumn("", 0, id=8)
            self.addColumn("", 0, id=9)
            self.addColumn("", 0, id=10,
                           data=lambda group: (group.data.min_cores or ""))
            self.addColumn("", 0, id=11,
                           data=lambda group: (
                                   group.data.max_cores > 0 and group.data.max_cores or ""))
            self.addColumn("", 0, id=12,
                           data=lambda group: (group.data.min_gpus or ""))
            self.addColumn("", 0, id=13,
                           data=lambda group: (
                                   group.data.max_gpus > 0 and group.data.max_gpus or ""))
            self.addColumn("", 0, id=14)
            self.addColumn("", 0, id=15)
            self.addColumn("", 0, id=16)
            self.addColumn("", 0, id=17)
            self.addColumn("", 0, id=18)
            self.addColumn("", 0, id=19)
            self.addColumn("", 0, id=20,
                           data=lambda group: (group.data.department != "Unknown" and
                                               group.data.department or ""))
            self.addColumn("", 0, id=21)

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.setAnimated(False)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        # pylint: disable=no-member
        QtGui.qApp.facility_changed.connect(self.removeAllShows)
        # pylint: enable=no-member
        self.itemClicked.connect(self.__itemSingleClickedCopy)
        self.itemClicked.connect(self.__itemSingleClickedComment)

        # Skip updates if the user is scrolling
        self._limitUpdatesDuringScrollSetup()

        self.setUpdateInterval(UPDATE_INTERVAL)

    def __itemSingleClickedCopy(self, item, col):
        """Called when an item is clicked on. Copies selected object names to
        the middle click selection clip board.
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        del item
        del col
        selected = [job.data.name for job in self.selectedObjects() if cuegui.Utils.isJob(job)]
        if selected:
            QtWidgets.QApplication.clipboard().setText(
                " ".join(selected), QtGui.QClipboard.Selection)

    def __itemSingleClickedComment(self, item, col):
        """If the comment column is clicked on, and there is a comment on the
        job, this pops up the comments dialog
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        job = item.rpcObject
        if col == COLUMN_COMMENT and cuegui.Utils.isJob(job) and job.data.has_comment:
            self.__menuActions.jobs().viewComments([job])

    def startDrag(self, dropActions):
        """Called when a drag begins"""
        cuegui.Utils.startDrag(self, dropActions, self.selectedObjects())

    def dragEnterEvent(self, event):
        cuegui.Utils.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        cuegui.Utils.dragMoveEvent(event)

        # Causes the list to scroll when dragging is over the top or bottom 20%
        ypos = event.answerRect().y()
        height = self.viewport().height()
        move = 0

        if ypos < height * .2:
            if ypos < height * .1:
                move = -5
            else:
                move = -2
        elif ypos > height * .8:
            if ypos > height * .9:
                move = 2
            else:
                move = 5
        if move:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + move)

    def dropEvent(self, event):
        item = self.itemAt(event.pos())

        if item and item.type() in (cuegui.Constants.TYPE_ROOTGROUP, cuegui.Constants.TYPE_GROUP):
            job_ids = cuegui.Utils.dropEvent(event, "application/x-job-ids")
            group_ids = cuegui.Utils.dropEvent(event, "application/x-group-ids")

            if job_ids or group_ids:
                body = ""
                if group_ids:
                    body += "Groups:\n" + "\n".join(
                        cuegui.Utils.dropEvent(event, "application/x-group-names"))
                if group_ids and job_ids:
                    body += "\n\n"
                if job_ids:
                    body += "Jobs:\n" + "\n".join(
                        cuegui.Utils.dropEvent(event, "application/x-job-names"))

                result = QtWidgets.QMessageBox.question(
                    self,
                    "Move groups/jobs?",
                    "Move the following into the group: " +
                    "\"%s\"?\n\n%s" % (
                        item.rpcObject.data.name, body),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

                if result == QtWidgets.QMessageBox.Yes:
                    if job_ids:
                        jobs = [opencue.api.getJob(id_) for id_ in job_ids]
                        item.rpcObject.asGroup().reparentJobs(jobs)

                    if group_ids:
                        item.rpcObject.asGroup().reparentGroupIds(group_ids)

                    self.updateRequest()

    def addShow(self, show, update=True):
        """Adds a show to the list of monitored shows
        @type  show: Show name
        @param show: string
        @type  update: boolean
        @param update: True if the display should update the displayed shows/jobs"""
        show = str(show)
        if show not in self.__shows:
            try:
                self.__shows[show] = opencue.api.findShow(show)
            except opencue.exception.EntityNotFoundException:
                logger.warning("This show does not exist: %s", show)
            if update:
                self._update()

    def removeShow(self, show):
        """Unmonitors a show
        @type  show: str
        @param show: The show to unmonitor"""
        show = str(show)
        self._itemsLock.lockForWrite()
        try:
            if show in self.__shows:
                del self.__shows[show]
        finally:
            self._itemsLock.unlock()
        self._update()

    def removeAllShows(self):
        """Unmonitors all shows"""
        if self.__shows:
            self.removeAllItems()
            self.__shows = {}
            self._update()

    def getShows(self):
        """Returns a list of monitored show objects
        @rtype:  list<show>
        @return: List of monitored show objects"""
        return list(self.__shows.values())

    def getShowNames(self):
        """Returns a list of monitored shows
        @rtype:  list<str>
        @return: List of monitored shows"""
        return list(self.__shows.keys())

    def __getCollapsed(self):
        return [item.rpcObject for item in list(self._items.values()) if not item.isExpanded()]

    def __setCollapsed(self, collapsed):
        self.expandAll()
        for itemId in collapsed:
            if itemId in self._items:
                self._items[itemId].setExpanded(False)

    def _getUpdate(self):
        """Returns a list of NestedGroup from the cuebot for the monitored shows
        @rtype:  [list<NestedGroup>, set(str)]
        @return: List that contains updated nested groups and a set of all
        updated item ideas"""
        self.currtime = time.time()
        try:
            groups = [show.getJobWhiteboard() for show in self.getShows()]
            nestedGroups = []
            allIds = []
            for group in groups:
                nestedGroups.append(opencue.wrappers.group.NestedGroup(group))
                allIds.extend(self.__getNestedIds(group))
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return None

        return [nestedGroups, allIds]

    def _processUpdate(self, work, rpcObjects):
        """Adds or updates jobs and groups. Removes those that do not get updated
        @type  work: from threadpool
        @param work: from threadpool
        @type  rpcObjects: [list<NestedGroup>, set(str)]
        @param rpcObjects: List that contains updated nested groups and a set
        of all updated item ids"""
        if rpcObjects is None:
            return
        self._itemsLock.lockForWrite()
        # pylint: disable=broad-except
        try:
            current = set(self._items.keys())
            if current == set(rpcObjects[1]):
                # Only updates
                self.__processUpdateHandleNested(self.invisibleRootItem(), rpcObjects[0])
                self.redraw()
            else:
                # (Something removed) or (Something added)
                selected_ids = [item.rpcObject.id() for item in self.selectedItems()]
                collapsed = self.__getCollapsed()
                scrolled = self.verticalScrollBar().value()
                self._items = {}
                self.clear()
                self.__processUpdateHandleNested(self.invisibleRootItem(), rpcObjects[0])
                self.__setCollapsed(collapsed)
                self.verticalScrollBar().setValue(scrolled)
                list(map(lambda id_: self._items[id_].setSelected(True),
                         [id_ for id_ in selected_ids if id_ in self._items]))
        except Exception:
            logger.warning("Failed to process update.", exc_info=True)
        finally:
            self._itemsLock.unlock()

    def __getNestedIds(self, group):
        """Returns all the ids founds in the nested list
        @type  group: job_pb2.Group
        @param group: A group that can contain groups and/or jobs
        @rtype:  list
        @return: The list of all child ids"""
        updated = []
        for innerGroup in group.groups.nested_groups:
            updated.append(innerGroup.id)

            # If group has groups, recursively call this function
            for g in innerGroup.groups.nested_groups:
                updated_g = self.__getNestedIds(g)
                if updated_g:
                    updated.extend(updated_g)

            # If group has jobs, update them
            for jobId in innerGroup.jobs:
                updated.append(jobId)

        return updated

    def __processUpdateHandleNested(self, parent, groups):
        """Adds or updates self._items from a list of NestedGroup objects.
        @type  parent: QTreeWidgetItem or QTreeWidget
        @param parent: The parent item for this level of items
        @type  groups: list<NestedGroup>
        @param groups: paramB_description"""
        for group in groups:
            # If id already exists, update it
            if group.data.parent.id:
                parent = self._items.get(group.data.parent.id)

            if group.id() in self._items:
                groupItem = self._items[group.id()]
                groupItem.update(group, parent)
            elif group.data.parent.id:
                self._items[group.id()] = groupItem = GroupWidgetItem(group, parent)
            else:
                self._items[group.id()] = groupItem = RootGroupWidgetItem(group, parent)

            nestedGroups = [
                opencue.wrappers.group.NestedGroup(nestedGroup)
                for nestedGroup in group.data.groups.nested_groups]
            self.__processUpdateHandleNested(groupItem, nestedGroups)

            for jobId in group.data.jobs:
                job = opencue.api.getJob(jobId)
                try:
                    if job.id() in self._items:
                        self._items[job.id()].update(job, groupItem)
                    else:
                        self._items[job.id()] = JobWidgetItem(job, groupItem)
                except RuntimeError:
                    logger.warning(
                        "Failed to create tree item. RootView might be closed", exc_info=True)

    def mouseDoubleClickEvent(self, event):
        del event
        objects = self.selectedObjects()
        if objects:
            self.view_object.emit(objects[0])

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        selectedObjects = self.selectedObjects()
        counts = cuegui.Utils.countObjectTypes(selectedObjects)

        menu = QtWidgets.QMenu()
        if counts["rootgroup"] > 0:
            if counts["group"] > 0 or counts["job"] > 0:
                if counts["rootgroup"] == 1:
                    rmenu = QtWidgets.QMenu("Root Group ->", self)
                else:
                    rmenu = QtWidgets.QMenu("Root Groups ->", self)
                menu.addMenu(rmenu)
                menu.addSeparator()
            else:
                rmenu = menu
            self.__menuActions.rootgroups().addAction(rmenu, "properties")
            self.__menuActions.rootgroups().addAction(rmenu, "serviceProperties")
            self.__menuActions.rootgroups().addAction(rmenu, "groupProperties")
            self.__menuActions.rootgroups().addAction(rmenu, "taskProperties")
            self.__menuActions.rootgroups().addAction(rmenu, "viewFilters")
            self.__menuActions.rootgroups().addAction(rmenu, "createGroup")
            menu.addSeparator()
            self.__menuActions.rootgroups().addAction(rmenu, "setCuewho")
            self.__menuActions.rootgroups().addAction(rmenu, "showCuewho")

        if counts["group"] > 0:
            if counts["rootgroup"] > 0 or counts["job"] > 0:
                if counts["group"] == 1:
                    gmenu = QtWidgets.QMenu("Group ->", self)
                else:
                    gmenu = QtWidgets.QMenu("Groups ->", self)
                menu.addMenu(gmenu)
                menu.addSeparator()
            else:
                gmenu = menu

            self.__menuActions.groups().addAction(gmenu, "properties")
            self.__menuActions.groups().addAction(gmenu, "createGroup")
            gmenu.addSeparator()
            self.__menuActions.groups().addAction(gmenu, "deleteGroup")

        if counts["job"] > 0:

            jobTypes = cuegui.Utils.countJobTypes(selectedObjects)

            self.__menuActions.jobs().addAction(menu, "view")
            self.__menuActions.jobs().addAction(menu, "emailArtist")
            self.__menuActions.jobs().addAction(menu, "viewComments")
            self.__menuActions.jobs().addAction(menu, "sendToGroup")

            depend_menu = QtWidgets.QMenu("Dependencies", self)
            self.__menuActions.jobs().addAction(depend_menu, "viewDepends")
            self.__menuActions.jobs().addAction(depend_menu, "dependWizard")
            depend_menu.addSeparator()
            self.__menuActions.jobs().addAction(depend_menu, "dropExternalDependencies")
            self.__menuActions.jobs().addAction(depend_menu, "dropInternalDependencies")
            menu.addMenu(depend_menu)

            menu.addSeparator()
            self.__menuActions.jobs().addAction(menu, "setMinCores")
            self.__menuActions.jobs().addAction(menu, "setMaxCores")
            self.__menuActions.jobs().addAction(menu, "setMinGpu")
            self.__menuActions.jobs().addAction(menu, "setMaxGpu")
            self.__menuActions.jobs().addAction(menu, "setPriority")
            self.__menuActions.jobs().addAction(menu, "setMaxRetries")
            if counts["job"] == 1:
                self.__menuActions.jobs().addAction(menu, "reorder")
                self.__menuActions.jobs().addAction(menu, "stagger")
            menu.addSeparator()
            if jobTypes["unpaused"]:
                self.__menuActions.jobs().addAction(menu, "pause")
            if jobTypes["paused"]:
                self.__menuActions.jobs().addAction(menu, "resume")
            menu.addSeparator()
            if jobTypes["hasDead"]:
                self.__menuActions.jobs().addAction(menu, "retryDead")
                self.__menuActions.jobs().addAction(menu, "eatDead")
            if jobTypes["notEating"]:
                self.__menuActions.jobs().addAction(menu, "autoEatOn")
            if jobTypes["autoEating"]:
                self.__menuActions.jobs().addAction(menu, "autoEatOff")
            menu.addSeparator()
            self.__menuActions.jobs().addAction(menu, "unbook")
            menu.addSeparator()
            self.__menuActions.jobs().addAction(menu, "kill")

        menu.exec_(e.globalPos())

    def actionEatSelectedItems(self):
        """Eats all dead frames for selected jobs"""
        self.__menuActions.jobs().eatDead()

    def actionRetrySelectedItems(self):
        """Retries all dead frames for selected jobs"""
        self.__menuActions.jobs().retryDead()

    def actionKillSelectedItems(self):
        """Removes selected jobs from cue"""
        self.__menuActions.jobs().kill()

    def actionPauseSelectedItems(self):
        """Pause selected jobs"""
        self.__menuActions.jobs().pause()

    def actionResumeSelectedItems(self):
        """Resume selected jobs"""
        self.__menuActions.jobs().resume()

    def tick(self):
        pass


class RootGroupWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item representing a single root group."""

    __initialized = False

    # pylint: disable=protected-access
    def __init__(self, rpcObject, parent):
        if not self.__initialized:
            if cuegui.Style.ColorTheme is None:
                cuegui.Style.init()
            self.__class__.__initialized = True
            self.__class__.__icon = QtGui.QIcon(":show.png")
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_SHOW_FOREGROUND
            self.__class__.__backgroundColor = cuegui.Style.ColorTheme.COLOR_SHOW_BACKGROUND
            self.__class__.__type = cuegui.Constants.TYPE_ROOTGROUP

        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_ROOTGROUP, rpcObject, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](self.rpcObject)

        if role == QtCore.Qt.FontRole:
            return FONT_BOLD

        if role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        if role == QtCore.Qt.BackgroundRole:
            return self.__backgroundColor

        if role == QtCore.Qt.DecorationRole:
            if col == 0:
                return self.__icon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        return cuegui.Constants.QVARIANT_NULL

    def __lt__(self, other):
        """The shows are always ascending alphabetical"""
        if self.treeWidget().header().sortIndicatorOrder():
            return other.rpcObject.name() < self.rpcObject.name()
        return other.rpcObject.name() > self.rpcObject.name()

    def __ne__(self, other):
        return other.rpcObject != self.rpcObject


class GroupWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Represents a group entry in the MonitorCue widget."""

    __initialized = False

    # pylint: disable=protected-access
    def __init__(self, rpcObject, parent):
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
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](self.rpcObject)

        if role == QtCore.Qt.FontRole:
            return FONT_BOLD

        if role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        if role == QtCore.Qt.BackgroundRole:
            return self.__backgroundColor

        if role == QtCore.Qt.DecorationRole and col == 0:
            return self.__icon

        if role == QtCore.Qt.UserRole:
            return self.__type

        return cuegui.Constants.QVARIANT_NULL

    def __lt__(self, other):
        """Groups are always ascending alphabetical"""
        if self.treeWidget().header().sortIndicatorOrder():
            return other.rpcObject.name() < self.rpcObject.name()
        return other.rpcObject.name() > self.rpcObject.name()

    def __ne__(self, other):
        if hasattr(other, 'rpcObject'):
            return other.rpcObject != self.rpcObject
        return True


class JobWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Represents a job entry in the MonitorCue widget."""

    __initialized = False

    # pylint: disable=protected-access
    def __init__(self, rpcObject, parent):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__commentIcon = QtGui.QIcon(":comment.png")
            self.__class__.__eatIcon = QtGui.QIcon(":eat.png")
            # pylint: disable=no-member
            self.__class__.__backgroundColor = QtGui.qApp.palette().color(QtGui.QPalette.Base)
            # pylint: enable=no-member
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND
            self.__class__.__pausedColor = cuegui.Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND
            self.__class__.__finishedColor = cuegui.Style.ColorTheme.COLOR_JOB_FINISHED_BACKGROUND
            self.__class__.__dyingColor = cuegui.Style.ColorTheme.COLOR_JOB_DYING_BACKGROUND
            self.__class__.__dependedColor = cuegui.Style.ColorTheme.COLOR_JOB_DEPENDED
            self.__class__.__noRunningColor = cuegui.Style.ColorTheme.COLOR_JOB_WITHOUT_PROCS
            self.__class__.__highMemoryColor = cuegui.Style.ColorTheme.COLOR_JOB_HIGH_MEMORY
            self.__class__.__type = cuegui.Constants.TYPE_JOB

        rpcObject.parent = None

        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_JOB, rpcObject, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            if col not in self._cache:
                self._cache[col] = \
                    self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](self.rpcObject)
            return self._cache.get(col, cuegui.Constants.QVARIANT_NULL)

        if role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        if role == QtCore.Qt.BackgroundRole:
            if col == COLUMN_MAXRSS and \
               self.rpcObject.data.job_stats.max_rss > cuegui.Constants.MEMORY_WARNING_LEVEL:
                return self.__highMemoryColor
            if self.rpcObject.data.is_paused:
                return self.__pausedColor
            if self.rpcObject.data.job_stats.dead_frames:
                return self.__dyingColor
            if not self.rpcObject.data.job_stats.running_frames:
                if not self.rpcObject.data.job_stats.waiting_frames and \
                   self.rpcObject.data.job_stats.depend_frames:
                    return self.__dependedColor
                if self.rpcObject.data.job_stats.waiting_frames and \
                   time.time() - self.rpcObject.data.start_time > 30:
                    return self.__noRunningColor
            return self.__backgroundColor

        if role == QtCore.Qt.DecorationRole:
            if col == COLUMN_COMMENT and self.rpcObject.data.has_comment:
                return self.__commentIcon
            if col == COLUMN_EAT and self.rpcObject.data.auto_eat:
                return self.__eatIcon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        elif role == QtCore.Qt.UserRole + 1:
            if "FST" not in self._cache:
                jobStats = self.rpcObject.data.job_stats
                self._cache["FST"] = {
                    opencue.compiled_proto.job_pb2.WAITING: jobStats.waiting_frames,
                    opencue.compiled_proto.job_pb2.RUNNING: jobStats.running_frames,
                    opencue.compiled_proto.job_pb2.SUCCEEDED: jobStats.succeeded_frames,
                    opencue.compiled_proto.job_pb2.CHECKPOINT: 0,
                    opencue.compiled_proto.job_pb2.SETUP: 0,
                    opencue.compiled_proto.job_pb2.EATEN: jobStats.eaten_frames,
                    opencue.compiled_proto.job_pb2.DEAD: jobStats.dead_frames,
                    opencue.compiled_proto.job_pb2.DEPEND: jobStats.depend_frames,
                }
            return self._cache.get("FST", cuegui.Constants.QVARIANT_NULL)

        return cuegui.Constants.QVARIANT_NULL
