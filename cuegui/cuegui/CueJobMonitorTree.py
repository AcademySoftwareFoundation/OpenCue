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


import time

import Constants
import Logger
import Style
import Utils
from AbstractTreeWidget import AbstractTreeWidget
from AbstractWidgetItem import AbstractWidgetItem
from ItemDelegate import JobThinProgressBarDelegate
from Manifest import QtCore, QtGui, QtWidgets, opencue
from MenuActions import MenuActions

logger = Logger.getLogger(__file__)

COLUMN_COMMENT = 1
COLUMN_EAT = 2
COLUMN_MAXRSS = 13

FONT_BOLD = QtGui.QFont("Luxi Sans", -1, QtGui.QFont.Bold)

def getEta(stats):
    if stats.runningFrames:
        remaining = (((stats.pendingFrames - 1) * stats.avgFrameSec) + stats.highFrameSec)
        if remaining:
            return Utils.secondsToHHHMM(remaining / stats.runningFrames)
    return "-"

class CueJobMonitorTree(AbstractTreeWidget):

    view_object = QtCore.Signal(object)
    single_click = QtCore.Signal(object)

    def __init__(self, parent):

        self.__shows = {}

        self.startColumnsForType(Constants.TYPE_JOB)
        self.addColumn("Job", 550, id=1,
                       data=lambda job:(job.data.name),
                       tip="The name of the job: show-shot-user_uniqueName\n\n"
                           "The color behind the job will change to:\n"
                           "Blue \t if it is paused\n"
                           "Red \t if it has dead frames\n"
                           "Green \t if it has no running frames with frames waiting\n"
                           "Purple \t if all remaining frames depend on something\n"
                           "Yellow \t if the maxRss is over %sKb" % Constants.MEMORY_WARNING_LEVEL)
        self.addColumn("_Comment", 20, id=2,
                       sort=lambda job:(job.data.hasComment),
                       tip="A comment icon will appear if a job has a comment. You\n"
                           "may click on it to view the comments.")
        self.addColumn("_Autoeat", 20, id=3,
                       sort=lambda job:(job.data.autoEat),
                       tip="If the job has auto eating enabled, a pac-man icon\n"
                           "will appear here and all frames that become dead will\n"
                           "automatically be eaten.")
        self.addColumn("Run", 38, id=3,
                       data=lambda job:(job.stats.runningFrames),
                       sort=lambda job:(job.stats.runningFrames),
                       tip="The number of running frames.")
        self.addColumn("Cores", 55, id=4,
                       data=lambda job:("%.02f" % job.stats.reservedCores),
                       sort=lambda job:(job.stats.reservedCores),
                       tip="The number of reserved cores.")
        self.addColumn("Wait", 45, id=5,
                       data=lambda job:(job.stats.waitingFrames),
                       sort=lambda job:(job.stats.waitingFrames),
                       tip="The number of waiting frames.")
        self.addColumn("Depend", 55, id=6,
                       data=lambda job:(job.stats.dependFrames),
                       sort=lambda job:(job.stats.dependFrames),
                       tip="The number of dependent frames.")
        self.addColumn("Total", 50, id=7,
                       data=lambda job:(job.stats.totalFrames),
                       sort=lambda job:(job.stats.totalFrames),
                       tip="The total number of frames.")
#        self.addColumn("_Booking Bar", 150, id=8, default=False,
#                       delegate=JobBookingBarDelegate)
        self.addColumn("Min", 38, id=9,
                       data=lambda job:("%.0f" % job.data.minCores),
                       sort=lambda job:(job.data.minCores),
                       tip="The minimum number of running cores that the cuebot\n"
                           "will try to maintain.")
        self.addColumn("Max", 38, id=10,
                       data=lambda job:("%.0f" % job.data.maxCores),
                       sort=lambda job:(job.data.maxCores),
                       tip="The maximum number of running cores that the cuebot\n"
                           "will allow.")
        self.addColumn("Age", 50, id=11,
                       data=lambda job:(Utils.secondsToHHHMM(time.time() - job.data.startTime)),
                       sort=lambda job:(time.time() - job.data.startTime),
                       tip="The HOURS:MINUTES since the job was launched.")
        self.addColumn("Pri", 30, id=12,
                       data=lambda job:(job.data.priority),
                       sort=lambda job:(job.data.priority),
                       tip="The job priority. The cuebot uses this as a suggestion\n"
                           "to determine what job needs the next available matching\n"
                           "resource.")
        self.addColumn("ETA", 65, id=13,
                       data=lambda job:(""),
                       tip="(Inacurate and disabled until a better solution exists)\n"
                           "A very rough estimate of the number of HOURS:MINUTES\n"
                           "it will be before the entire job is done.")
        self.addColumn("MaxRss", 60, id=14,
                       data=lambda job:(Utils.memoryToString(job.stats.maxRss)),
                       sort=lambda job:(job.stats.maxRss),
                       tip="The most memory used at one time by any single frame.")
        self.addColumn("_Blank", 20, id=15,
                       tip="Spacer")
        self.addColumn("Progress", 0, id=16,
                       delegate=JobThinProgressBarDelegate,
                       tip="A visual overview of the job progress.\n"
                           "Green \t is succeeded\n"
                           "Yellow \t is running\n"
                           "Red \t is dead\n"
                           "Purple \t is waiting on a dependency\n"
                           "Light Blue \t is waiting to be booked")

        for itemType in [Constants.TYPE_GROUP, Constants.TYPE_ROOTGROUP]:
            self.startColumnsForType(itemType)
            self.addColumn("", 0, id=1,
                           data=lambda group: group.name)
            self.addColumn("", 0, id=2)
            self.addColumn("", 0, id=3)
            self.addColumn("", 0, id=4,
                           data=lambda group: group.stats.running_frames)
            self.addColumn("", 0, id=5,
                           data=lambda group: "%.2f" % group.stats.reserved_cores)
            self.addColumn("", 0, id=6,
                           data=lambda group: group.stats.waiting_frames)
            self.addColumn("", 0, id=7)
            self.addColumn("", 0, id=8)
            self.addColumn("", 0, id=9,
                           data=lambda group: (group.min_cores or ""))
            self.addColumn("", 0, id=10,
                           data=lambda group: (group.max_cores > 0 and group.max_cores or ""))
            self.addColumn("", 0, id=11)
            self.addColumn("", 0, id=12)
            self.addColumn("", 0, id=13)
            self.addColumn("", 0, id=14)
            self.addColumn("", 0, id=15)
            self.addColumn("", 0, id=16,
                           data=lambda group: (group.department != "Unknown" and group.department or ""))

        AbstractTreeWidget.__init__(self, parent)

        self.setAnimated(False)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        # Used to build right click context menus
        self.__menuActions = MenuActions(self, self.updateSoon, self.selectedObjects)

        QtGui.qApp.facility_changed.connect(self.removeAllShows)
        self.itemClicked.connect(self.__itemSingleClickedCopy)
        self.itemClicked.connect(self.__itemSingleClickedComment)

        # Skip updates if the user is scrolling
        self._limitUpdatesDuringScrollSetup()

        self.setUpdateInterval(22)

    def __itemSingleClickedCopy(self, item, col):
        """Called when an item is clicked on. Copies selected object names to
        the middle click selection clip board.
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        selected = [job.data.name for job in self.selectedObjects() if Utils.isJob(job)]
        if selected:
            QtWidgets.QApplication.clipboard().setText(" ".join(selected),
                                                       QtGui.QClipboard.Selection)

    def __itemSingleClickedComment(self, item, col):
        """If the comment column is clicked on, and there is a comment on the
        job, this pops up the comments dialog
        @type  item: QTreeWidgetItem
        @param item: The item clicked on
        @type  col: int
        @param col: The column clicked on"""
        job = item.rpcObject
        if col == COLUMN_COMMENT and Utils.isJob(job) and job.data.hasComment:
            self.__menuActions.jobs().viewComments([job])

    def startDrag(self, dropActions):
        """Called when a drag begins"""
        Utils.startDrag(self, dropActions, self.selectedObjects())

    def dragEnterEvent(self, event):
        Utils.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        Utils.dragMoveEvent(event)

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

        if item and item.type() in (Constants.TYPE_ROOTGROUP, Constants.TYPE_GROUP):
            job_ids = Utils.dropEvent(event, "application/x-job-ids")
            group_ids = Utils.dropEvent(event, "application/x-group-ids")
            job_names = Utils.dropEvent(event, "application/x-job-names")
            group_names = Utils.dropEvent(event, "application/x-group-names")

            if job_ids or group_ids:
                body = ""
                if group_ids:
                    body += "Groups:\n" + "\n".join(Utils.dropEvent(event, "application/x-group-names"))
                if group_ids and job_ids:
                    body += "\n\n"
                if job_ids:
                    body += "Jobs:\n" + "\n".join(Utils.dropEvent(event, "application/x-job-names"))

                result = QtWidgets.QMessageBox.question(
                    self,
                    "Move groups/jobs?",
                    "Move the following into the group: " +
                    "\"%s\"?\n\n%s" % (
                        item.rpcObject.data.name, body),
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

                if result == QtWidgets.QMessageBox.Yes:
                    if job_ids:
                        item.rpcObject.reparentJobs(job_ids)
                        # If no exception, then move was allowed, so do it locally:
                        for id_ in job_ids:
                            proxy = Utils.getObjectKey(opencue.util.proxy(id_, "Job"))
                            self._items[proxy].update(self._items[proxy].rpcObject, item)

                    if group_ids:
                        item.rpcObject.reparentGroups(group_ids)
                        # If no exception, then move was allowed, so do it locally:
                        for id_ in group_ids:
                            proxy = Utils.getObjectKey(opencue.util.proxy(id_, "Group"))
                            self._items[proxy].update(self._items[proxy].rpcObject, item)

                    self.updateSoon()

    def addShow(self, show, update = True):
        """Adds a show to the list of monitored shows
        @type  show: Show name
        @param show: string
        @type  update: boolean
        @param update: True if the display should update the displayed shows/jobs"""
        show = str(show)
        if show not in self.__shows:
            try:
                self.__shows[show] = opencue.api.findShow(show)
            except:
                logger.warning("This show does not exist: %s" % show)
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
        return self.__shows.values()

    def getShowNames(self):
        """Returns a list of monitored shows
        @rtype:  list<str>
        @return: List of monitored shows"""
        return self.__shows.keys()

    def __getCollapsed(self):
        return [item.rpcObject for item in self._items.values() if not item.isExpanded()]

    def __setCollapsed(self, collapsed):
        self.expandAll()
        for id in collapsed:
            if id in self._items:
                self._items[id].setExpanded(False)

    def _getUpdate(self):
        """Returns a list of NestedGroup from the cuebot for the monitored shows
        @rtype:  [list<NestedGroup>, set(str)]
        @return: List that contains updated nested groups and a set of all
        updated item ideas"""
        try:
            nestedShows = [opencue.wrappers.show.Show(show.data).getJobWhiteboard()
                           for show in self.getShows()]
            allIds = set(self.__getNestedIds(nestedShows))
        except Exception, e:
            map(logger.warning, Utils.exceptionOutput(e))
            return None

        return [nestedShows, allIds]

    def _processUpdate(self, work, results):
        """Adds or updates jobs and groups. Removes those that do not get updated
        @type  work: from threadpool
        @param work: from threadpool
        @type  nested_shows: [list<NestedGroup>, set(str)]
        @param nested_shows: List that contains updated nested groups and a set
        of all updated item ids"""
        if results is None:
            return
        self._itemsLock.lockForWrite()
        try:
# This is causing segfaults as sorting is somehow allowed to happen at the same time
# At this time, __getNestedIds functionality was in __processUpdateHandleNested
#            updated = self.__processUpdateHandleNested(self.invisibleRootItem(), nested_shows)
#            # Remove any items that were not updated
#            for id in list(set(self._items.keys()) - set(updated)):
#                self._removeItem(id)

            current = set(self._items.keys())

            if list(current - results[1]) or list(results[1] - current):
                # (Something removed) or (Something added)
                selected_ids = [item.rpcObject.id for item in self.selectedItems()]
                collapsed = self.__getCollapsed()
                scrolled = self.verticalScrollBar().value()

                self._items = {}
                self.clear()

                self.__processUpdateHandleNested(self.invisibleRootItem(), results[0])

                self.__setCollapsed(collapsed)
                self.verticalScrollBar().setValue(scrolled)
                [self._items[id_].setSelected(True) for id_ in selected_ids if id_ in self._items]
            else:
                # Only updates
                self.__processUpdateHandleNested(self.invisibleRootItem(), results[0])
                self.redraw()
        finally:
            self._itemsLock.unlock()

    def __getNestedIds(self, groups):
        """Returns all the ids founds in the nested list
        @type  groups:
        @param groups: A group that can contain groups and/or jobs
        @rtype:  list
        @return: The list of all child ids"""
        updated = []
        if hasattr(groups, 'nested_groups'):
            groups = groups.nested_groups
        for group in groups:
            updated.append(group.id)

            # If group has groups, recursively call this function
            if group.groups:
                updated.extend(self.__getNestedIds(group.groups))

            # If group has jobs, update them
            jobs = group.jobs
            if hasattr(jobs, 'nested_jobs'):
                jobs = jobs.nested_jobs
            for job in jobs:
                updated.append(job.id)

        return updated

    def __processUpdateHandleNested(self, parent, groups):
        """Adds or updates self._items from a list of NestedGroup objects.
        @type  parent: QTreeWidgetItem or QTreeWidget
        @param parent: The parent item for this level of items
        @type  groups: list<NestedGroup>
        @param groups: paramB_description"""
        if hasattr(groups, 'nested_groups'):
            groups = groups.nested_groups
        for group in groups:
            # If id already exists, update it
            if group.id in self._items:
                groupItem = self._items[group.id]
                groupItem.update(group, parent)

            # If id does not exist, create it
            elif Utils.isGroup(group):
                self._items[group.id] = groupItem = GroupWidgetItem(group, parent)
            else:
                self._items[group.id] = groupItem = RootGroupWidgetItem(group, parent)

            # If group has groups, recursively call this function
            if group.groups:
                self.__processUpdateHandleNested(groupItem, group.groups)

            # If group has jobs, update them
            jobs = group.jobs
            if hasattr(jobs, 'nested_jobs'):
                jobs = jobs.nested_jobs
            for job in jobs:
                if job.id in self._items:
                    self._items[job.id].update(job, groupItem)
                else:
                    self._items[job.id] = JobWidgetItem(job, groupItem)

    def mouseDoubleClickEvent(self,event):
        objects = self.selectedObjects()
        if objects:
            self.view_object.emit(objects[0])

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        selectedObjects = self.selectedObjects()
        counts = Utils.countObjectTypes(selectedObjects)

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

            jobTypes = Utils.countJobTypes(selectedObjects)

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
            self.__menuActions.jobs().addAction(menu, "setPriority")
            self.__menuActions.jobs().addAction(menu, "setMaxRetries")
            if counts["job"] == 1:
                self.__menuActions.jobs().addAction(menu, "reorder")
                self.__menuActions.jobs().addAction(menu, "stagger")
            #Broken: self.__menuActions.jobs().addAction(menu, "testCloBook")
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

class RootGroupWidgetItem(AbstractWidgetItem):
    __initialized = False
    def __init__(self, object, parent):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__icon = QtGui.QIcon(":show.png")
            self.__class__.__foregroundColor = Style.ColorTheme.COLOR_SHOW_FOREGROUND
            self.__class__.__backgroundColor = Style.ColorTheme.COLOR_SHOW_BACKGROUND
            self.__class__.__type = Constants.TYPE_ROOTGROUP

        AbstractWidgetItem.__init__(self, Constants.TYPE_ROOTGROUP, object, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][Constants.COLUMN_INFO_DISPLAY](self.rpcObject)

        elif role == QtCore.Qt.FontRole:
            return FONT_BOLD

        elif role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        elif role == QtCore.Qt.BackgroundRole:
            return self.__backgroundColor

        elif role == QtCore.Qt.DecorationRole:
            if col == 0:
                return self.__icon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        return Constants.QVARIANT_NULL

    def __lt__(self, other):
        """The shows are always ascending alphabetical"""
        if self.treeWidget().header().sortIndicatorOrder():
            return other.rpcObject.data.name < self.rpcObject.data.name
        return other.rpcObject.data.name > self.rpcObject.data.name

    def __ne__(self, other):
        return other.rpcObject != self.rpcObject

class GroupWidgetItem(AbstractWidgetItem):
    """Represents a group entry in the MonitorCue widget."""
    __initialized = False
    def __init__(self, object, parent):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__icon = QtGui.QIcon(":group.png")
            self.__class__.__foregroundColor = Style.ColorTheme.COLOR_GROUP_FOREGROUND
            self.__class__.__backgroundColor = Style.ColorTheme.COLOR_GROUP_BACKGROUND
            self.__class__.__type = Constants.TYPE_GROUP

        AbstractWidgetItem.__init__(self, Constants.TYPE_GROUP, object, parent)

    def data(self, col, role):
        """Returns the proper display data for the given column and role
        @type  col: int
        @param col: The column being displayed
        @type  role: QtCore.Qt.ItemDataRole
        @param role: The role being displayed
        @rtype:  object
        @return: The desired data"""
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][Constants.COLUMN_INFO_DISPLAY](self.rpcObject)

        elif role == QtCore.Qt.FontRole:
            return FONT_BOLD

        elif role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        elif role == QtCore.Qt.BackgroundRole:
            return self.__backgroundColor

        elif role == QtCore.Qt.DecorationRole and col == 0:
            return self.__icon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        return Constants.QVARIANT_NULL

    def __lt__(self, other):
        """Groups are always ascending alphabetical"""
        if self.treeWidget().header().sortIndicatorOrder():
            return other.rpcObject.name < self.rpcObject.name
        return other.rpcObject.name > self.rpcObject.name

    def __ne__(self, other):
        return other.rpcObject != self.rpcObject

class JobWidgetItem(AbstractWidgetItem):
    """Represents a job entry in the MonitorCue widget."""
    __initialized = False
    def __init__(self, object, parent):
        if not self.__initialized:
            self.__class__.__initialized = True
            self.__class__.__commentIcon = QtGui.QIcon(":comment.png")
            self.__class__.__eatIcon = QtGui.QIcon(":eat.png")
            self.__class__.__backgroundColor = QtGui.qApp.palette().color(QtGui.QPalette.Base)
            self.__class__.__foregroundColor = Style.ColorTheme.COLOR_JOB_FOREGROUND
            self.__class__.__pausedColor = Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND
            self.__class__.__finishedColor = Style.ColorTheme.COLOR_JOB_FINISHED_BACKGROUND
            self.__class__.__dyingColor = Style.ColorTheme.COLOR_JOB_DYING_BACKGROUND
            self.__class__.__dependedColor = Style.ColorTheme.COLOR_JOB_DEPENDED
            self.__class__.__noRunningColor = Style.ColorTheme.COLOR_JOB_WITHOUT_PROCS
            self.__class__.__highMemoryColor = Style.ColorTheme.COLOR_JOB_HIGH_MEMORY
            self.__class__.__type = Constants.TYPE_JOB

        object.parent = None

        AbstractWidgetItem.__init__(self, Constants.TYPE_JOB, object, parent)

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
                    self.column_info[col][Constants.COLUMN_INFO_DISPLAY](self.rpcObject)
            return self._cache.get(col, Constants.QVARIANT_NULL)

        elif role == QtCore.Qt.ForegroundRole:
            return self.__foregroundColor

        elif role == QtCore.Qt.BackgroundRole:
            if col == COLUMN_MAXRSS and \
               self.rpcObject.job_stats.max_rss > Constants.MEMORY_WARNING_LEVEL:
                    return self.__highMemoryColor
            if self.rpcObject.data.is_paused:
                return self.__pausedColor
            if self.rpcObject.stats.dead_frames:
                return self.__dyingColor
            if not self.rpcObject.job_stats.running_frames:
                if not self.rpcObject.job_stats.waiting_frames and \
                   self.rpcObject.job_stats.depend_frames:
                    return self.__dependedColor
                if self.rpcObject.job_stats.waiting_frames and \
                   time.time() - self.rpcObject.data.start_time > 30:
                    return self.__noRunningColor
            return self.__backgroundColor

        elif role == QtCore.Qt.DecorationRole:
            if col == COLUMN_COMMENT and self.rpcObject.data.has_comment:
                return self.__commentIcon
            elif col == COLUMN_EAT and self.rpcObject.data.auto_eat:
                return self.__eatIcon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        elif role == QtCore.Qt.UserRole + 1:
            if "FST" not in self._cache:
                self._cache["FST"] = {
                    opencue.job_pb2.FrameState.Dead: self.rpcObject.job_stats.dead_frames,
                    opencue.job_pb2.FrameState.Depend: self.rpcObject.job_stats.depend_frames,
                    opencue.job_pb2.FrameState.Eaten: self.rpcObject.job_stats.eaten_frames,
                    opencue.job_pb2.FrameState.Running: self.rpcObject.job_stats.running_frames,
                    opencue.job_pb2.FrameState.Setup: 0,
                    opencue.job_pb2.FrameState.Succeeded: self.rpcObject.job_stats.succeeded_frames,
                    opencue.job_pb2.FrameState.Waiting: self.rpcObject.job_stats.waiting_frames
                }
            return self._cache.get("FST", Constants.QVARIANT_NULL)

        return Constants.QVARIANT_NULL
