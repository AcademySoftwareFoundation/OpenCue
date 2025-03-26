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


"""Tree widget to display a list of monitored jobs."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from future.utils import iteritems
from builtins import map
import functools
import time
import pickle

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import opencue

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.ItemDelegate
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Style
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

COLUMN_NAME = 0
COLUMN_COMMENT = 1
COLUMN_AUTOEAT = 2
COLUMN_STATE = 3


def displayState(job):
    """Returns the string to display in the status for the given job
    @type  job: job
    @param job: The job to check the status of
    @rtype:  string
    @return: The status of the job for display"""
    if job.data.state == opencue.api.job_pb2.FINISHED:
        return "Finished"
    if job.data.is_paused:
        return "Paused"
    if job.data.job_stats.dead_frames > 0:
        return "Failing"
    if (job.data.job_stats.depend_frames and
        job.data.job_stats.depend_frames == job.data.job_stats.pending_frames and
            job.data.job_stats.running_frames == 0):
        return "Dependency"
    return "In Progress"

def sortableKey(key, datetime_key):
    """
    Returns a sortable key that sets apart similar keys using time_key

    @type  key: string or int
    @param key: A key used for sorting
    @type  datetime_key: int
    @param datetime_key: Date time represented as an integer
    @rtype:  string or float
    @return: datetime_key appended to key if key is a string,
             the 0.datetime_key summed to key if key is an int
    """
    if isinstance(key, int) and isinstance(datetime_key, int):
        return float(str(key)+"."+str(datetime_key))
    return str(key) + str(datetime_key)

class JobMonitorTree(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget to display a list of monitored jobs."""

    __loadMine = True
    __groupDependent = True
    view_object = QtCore.Signal(object)

    def __init__(self, parent):
        self.ticksWithoutUpdate = 0

        self.startColumnsForType(cuegui.Constants.TYPE_JOB)
        self.addColumn("Job", 470, id=1,
                       data=lambda job: job.data.name,
                       sort=lambda job: sortableKey(job.data.name, job.data.start_time),
                       tip="The name of the job: show-shot-user_uniqueName")
        self.addColumn("_Comment", 20, id=2,
                       sort=lambda job: job.data.has_comment,
                       tip="A comment icon will appear if a job has a comment. You\n"
                           "may click on it to view the comments.")
        self.addColumn("_Autoeat", 20, id=3,
                       sort=lambda job: job.data.auto_eat,
                       tip="If the job has auto eating enabled, a pac-man icon\n"
                           "will appear here and all frames that become dead will\n"
                           "automatically be eaten.")
        # pylint: disable=unnecessary-lambda
        self.addColumn("State", 80, id=4,
                       data=lambda job: displayState(job),
                       sort=lambda job: sortableKey(displayState(job), job.data.start_time),
                       tip="The state of each job.\n"
                           "In Progress \t The job is on the queue\n"
                           "Failing \t The job has dead frames\n"
                           "Paused \t The job has been paused\n"
                           "Finished \t The job has finished and is no longer in the queue")
        self.addColumn("Done/Total", 90, id=5,
                       data=lambda job: "%d of %d" % (job.data.job_stats.succeeded_frames,
                                                      job.data.job_stats.total_frames),
                       sort=lambda job: sortableKey(job.data.job_stats.succeeded_frames,
                                                    job.data.start_time),
                       tip="The number of succeeded frames vs the total number\n"
                           "of frames in each job.")
        self.addColumn("Running", 60, id=6,
                       data=lambda job: job.data.job_stats.running_frames,
                       sort=lambda job: sortableKey(job.data.job_stats.running_frames,
                                                    job.data.start_time),
                       tip="The number of running frames in each job,")
        self.addColumn("Dead", 50, id=7,
                       data=lambda job: job.data.job_stats.dead_frames,
                       sort=lambda job: sortableKey(job.data.job_stats.dead_frames,
                                                    job.data.start_time),
                       tip="Total number of dead frames in each job.")
        self.addColumn("Eaten", 50, id=8,
                       data=lambda job: job.data.job_stats.eaten_frames,
                       sort=lambda job: sortableKey(job.data.job_stats.eaten_frames,
                                                    job.data.start_time),
                       tip="Total number of eaten frames in each job.")
        self.addColumn("Wait", 60, id=9,
                       data=lambda job: job.data.job_stats.waiting_frames,
                       sort=lambda job: sortableKey(job.data.job_stats.waiting_frames,
                                                    job.data.start_time),
                       tip="The number of waiting frames in each job,")
        self.addColumn("MaxRss", 55, id=10,
                       data=lambda job: cuegui.Utils.memoryToString(job.data.job_stats.max_rss),
                       sort=lambda job: sortableKey(job.data.job_stats.max_rss,
                                                    job.data.start_time),
                       tip="The maximum memory used any single frame in each job.")
        self.addColumn("Age", 50, id=11,
                       data=lambda job: (cuegui.Utils.secondsToHHHMM((job.data.stop_time or
                                                               time.time()) - job.data.start_time)),
                       sort=lambda job: ((job.data.stop_time or time.time()) - job.data.start_time),
                       tip="The HOURS:MINUTES that the job has spent in the queue.")
        self.addColumn("Launched", 100, id=12,
                       data=lambda job: cuegui.Utils.dateToMMDDHHMM(job.data.start_time),
                       sort=lambda job: job.data.start_time,
                       tip="The time when the job was launched.")
        self.addColumn("Finished", 100, id=13,
                       data=lambda job: (job.data.stop_time > 0
                                         and cuegui.Utils.dateToMMDDHHMM(job.data.stop_time)
                                         or ""),
                       sort=lambda job: job.data.stop_time,
                       tip="The time when the job ended.")
        self.addColumn("Progress", 0, id=14,
                       delegate=cuegui.ItemDelegate.JobProgressBarDelegate,
                       tip="A visual overview of the progress of each job.\n"
                           "Green \t is succeeded\n"
                           "Yellow \t is running\n"
                           "Red \t is dead\n"
                           "Purple \t is waiting on a dependency\n"
                           "Light Blue \t is waiting to be booked")

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.__jobTimeLoaded = {}
        self.__userColors = {}
        self.__dependentJobs = {}
        self._dependent_items = {}
        self.__reverseDependents = {}
        self.local_plugin_saved_values = {}
        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)

        # pylint: disable=no-member
        self.itemClicked.connect(self.__itemSingleClickedCopy)
        self.itemClicked.connect(self.__itemSingleClickedComment)
        # pylint: enable=no-member

        self.__load = {}
        self.startTicksUpdate(20, False, 60)

    def tick(self):
        if self.__load:
            __jobs = self.__load.copy()
            self.__load.clear()
            self._processUpdate(None, __jobs)

        if self.tickNeedsUpdate():
            self.ticksWithoutUpdate = 0
            self._update()
            return

        self.updateJobCount()
        self.ticksWithoutUpdate += 1

    def updateJobCount(self):
        """Called at every tick. The total number of monitored
        jobs is added to the column header
        """
        count = 0
        iterator = QtWidgets.QTreeWidgetItemIterator(self)
        while iterator.value():
            count += 1
            iterator += 1

        self.headerItem().setText(0, "Job [Total Count: {}]".format(count))

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
        if col == COLUMN_COMMENT and job.isCommented():
            self.__menuActions.jobs().viewComments([job])

    def startDrag(self, dropActions):
        """Triggers a drag event"""
        cuegui.Utils.startDrag(self, dropActions, self.selectedObjects())

    def dragEnterEvent(self, event):
        """Enter Drag event"""
        cuegui.Utils.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Move Drag Event"""
        cuegui.Utils.dragMoveEvent(event)

    def dropEvent(self, event):
        """Drop Drag Event"""
        for job_name in cuegui.Utils.dropEvent(event):
            self.addJob(job_name)

    def setLoadMine(self, value):
        """Enables or disables the autoloading of the user's jobs
        @param value: New loadMine state
        @type  value: boolean or QtCore.Qt.Checked or QtCore.Qt.Unchecked"""
        self.__loadMine = (value is True or value == QtCore.Qt.Checked)

    def setGroupDependent(self, value):
        """Enables or disables the auto grouping of the dependent jobs
        @param value: New groupDependent state
        @type  value: boolean or QtCore.Qt.Checked or QtCore.Qt.Unchecked"""
        self.__groupDependent = (value is True or value == QtCore.Qt.Checked)
        self.updateRequest()

    def addJob(self, job, timestamp=None, loading_from_config=False):
        """Adds a job to the list. With locking"
        @param job: Job can be None, a job object, or a job name.
        @type  job: job, string, None
        @param loading_from_config: Whether or not this method is being called
               for loading jobs found in user config
        @type loading_from_config: bool
        """
        newJobObj = cuegui.Utils.findJob(job)
        self.ticksLock.lock()
        try:
            if newJobObj:
                jobKey = cuegui.Utils.getObjectKey(newJobObj)
                if not self.__groupDependent:
                    self.__load[jobKey] = newJobObj
                    self.__jobTimeLoaded[jobKey] = timestamp if timestamp else time.time()
                else:
                    # We'll only add the new job if it's not already listed
                    # as a dependent on another job
                    if jobKey not in self.__reverseDependents:
                        self.__load[jobKey] = newJobObj

                        # when we are adding jobs manually, we want to calculate
                        # all dependencies (active or not), so the user can see
                        # all the dependent jobs, even after the main/parent job
                        # has finished.
                        # When we're loading jobs from user config, we want to
                        # only include the active dependents. This is because
                        # the dependencies have already been calculated and
                        # listed in the config as a flat list, so attempting
                        # to re-add them will result in duplicates that will
                        # throw off the cleanup loop at the end of this method
                        active_only = not loading_from_config
                        dep = self.__menuActions.jobs(
                        ).getRecursiveDependentJobs([newJobObj],
                                                    active_only=active_only)

                        # Remove dependent if it has the same name as the job
                        # - This avoids missing jobs on MonitorJobs
                        # - Remove the parent job is necessary to avoid remove
                        # the parent job and all the dependents
                        # in the step 2 below
                        dep = [j for j in dep if j.data.name != newJobObj.data.name]

                        self.__dependentJobs[jobKey] = dep
                        # we'll also store a reversed dictionary for
                        # dependencies with the dependent as key and the main
                        # job as the value, this will be used in step 2
                        # below to remove jobs that are added here
                        # as dependents
                        for j in dep:
                            depKey = cuegui.Utils.getObjectKey(j)
                            self.__reverseDependents[depKey] = newJobObj
                            self.__jobTimeLoaded[depKey] = time.time()
                        self.__jobTimeLoaded[jobKey] = time.time()

                    for j in self.__reverseDependents:
                        if j in self.__load:
                            del self.__load[j]
        finally:
            self.ticksLock.unlock()

    def getJobProxies(self):
        """Get a list of the JobProxies that are being monitored in the session
         which will be saved to the config file

         Returning a sorted list based on the most recent timestamp - restoring jobs is capped
         by LOAD_LIMIT, so restore the most recent jobs the user added to their session

        :return: list of tuples of the JobId and timestamp
        """
        jobIdsTimeLoaded = []

        for jobProxy, _ in self._items.items():
            try:
                jobIdsTimeLoaded.append((jobProxy, self.__jobTimeLoaded[jobProxy]))
            except KeyError:
                # set timestamp to epoch time if timestamp not found
                jobIdsTimeLoaded.append((jobProxy, 0))

        # sort list on recent timestamps, only restoring the first n jobs (defined by LOAD_LIMIT)
        return list(sorted(jobIdsTimeLoaded, key=lambda x: x[1], reverse=True))

    def _removeItem(self, item):
        """Removes an item from the TreeWidget without locking
        @param item: A tree widget item
        @type  item: AbstractTreeWidgetItem"""
        self.app.unmonitor.emit(item.rpcObject)
        # pylint: disable=protected-access
        cuegui.AbstractTreeWidget.AbstractTreeWidget._removeItem(self, item)
        self.__jobTimeLoaded.pop(item.rpcObject, "")
        try:
            jobKey = cuegui.Utils.getObjectKey(item.rpcObject)
            # Remove the item from the main _items dictionary as well as the
            # __dependentJobs and the reverseDependent dictionaries
            # pylint: disable=protected-access
            cuegui.AbstractTreeWidget.AbstractTreeWidget._removeItem(self, item)
            dependent_jobs = self.__dependentJobs.get(jobKey, [])
            for djob in dependent_jobs:
                del self.__reverseDependents[djob]
            del self.__reverseDependents[jobKey]
        except KeyError:
            # Dependent jobs are not stored in as keys the main self._items
            # dictionary, trying to remove dependent jobs from self._items
            # raises a KeyError, which we can safely ignore
            pass

    def removeAllItems(self):
        """Notifies the other widgets of each item being unmonitored, then calls
        the the AbstractTreeWidget.removeAllItems like normal"""
        for proxy in list(self._items.keys()):
            self.app.unmonitor.emit(proxy)
            if proxy in self.__jobTimeLoaded:
                del self.__jobTimeLoaded[proxy]
        self.__dependentJobs.clear()
        self.__reverseDependents.clear()
        cuegui.AbstractTreeWidget.AbstractTreeWidget.removeAllItems(self)

    def removeFinishedItems(self):
        """Removes finished jobs"""
        for item in self.findItems("Finished", QtCore.Qt.MatchFixedString, COLUMN_STATE):
            self.removeItem(item)

    def getUserColors(self):
        """Returns the colored jobs to be saved"""
        return list(pickle.dumps(self.__userColors))

    def setUserColors(self, state):
        """Sets the colored jobs that were saved"""
        self.__userColors = pickle.loads(bytes(state))

    def getLocalPluginNumFrames(self):
        """Gets default values for the Local Plugin fields"""
        return self.local_plugin_saved_values.get("num_frames", 1)

    def setLocalPluginNumFrames(self, value):
        """Sets default values for the Local Plugin fields"""
        self.local_plugin_saved_values["num_frames"] = value

    def getLocalPluginNumThreads(self):
        """Gets default values for the Local Plugin fields"""
        return self.local_plugin_saved_values.get("num_threads", 1)

    def setLocalPluginNumThreads(self, value):
        """Sets default values for the Local Plugin fields"""
        self.local_plugin_saved_values["num_threads"] = value

    def getLocalPluginNumGpus(self):
        """Gets default values for the Local Plugin fields"""
        return self.local_plugin_saved_values.get("num_gpus", 0)

    def setLocalPluginNumGpus(self, value):
        """Sets default values for the LocalPlugin fields"""
        self.local_plugin_saved_values["num_gpus"] = value

    def getLocalPluginNumMem(self):
        """Gets default values for the LocalPlugin fields"""
        return self.local_plugin_saved_values.get("num_mem", 4)

    def setLocalPluginNumMem(self, value):
        """Sets default values for the LocalPlugin fields"""
        self.local_plugin_saved_values["num_mem"] = value

    def getLocalNumGpuMem(self):
        """Gets default values for the LocalPlugin fields"""
        return self.local_plugin_saved_values.get("num_gpu_mem", 0)

    def setLocalNumGpuMem(self, value):
        """Sets default values for the LocalPlugin fields"""
        self.local_plugin_saved_values["num_gpu_mem"] = value

    def contextMenuEvent(self, e):
        """Creates a context menu when an item is right clicked.
        @param e: Right click QEvent
        @type  e: QEvent"""
        menu = QtWidgets.QMenu()
        menu.setToolTipsVisible(True)

        __selectedObjects = self.selectedObjects()
        __count = len(__selectedObjects)
        jobType = cuegui.Utils.countJobTypes(__selectedObjects)

        self.__menuActions.jobs().addAction(menu, "unmonitor")
        self.__menuActions.jobs().addAction(menu, "view")
        self.__menuActions.jobs().addAction(menu, "emailArtist")
        self.__menuActions.jobs().addAction(menu, "requestCores")
        self.__menuActions.jobs().addAction(menu, "subscribeToJob")
        self.__menuActions.jobs().addAction(menu, "viewComments")

        if int(self.app.settings.value("DisableDeeding", 0)) == 0:
            self.__menuActions.jobs().addAction(menu, "useLocalCores")

        if cuegui.Constants.OUTPUT_VIEWERS:
            for viewer in cuegui.Constants.OUTPUT_VIEWERS:
                menu.addAction(viewer['action_text'],
                               functools.partial(cuegui.Utils.viewOutput,
                                                 __selectedObjects,
                                                 viewer['action_text']))

        depend_menu = QtWidgets.QMenu("&Dependencies",self)
        self.__menuActions.jobs().addAction(depend_menu, "viewDepends")
        self.__menuActions.jobs().addAction(depend_menu, "dependWizard")
        depend_menu.addSeparator()
        self.__menuActions.jobs().addAction(depend_menu, "dropExternalDependencies")
        self.__menuActions.jobs().addAction(depend_menu, "dropInternalDependencies")
        menu.addMenu(depend_menu)

        color_menu = QtWidgets.QMenu("&Set user color",self)
        self.__menuActions.jobs().addAction(color_menu, "setUserColor1")
        self.__menuActions.jobs().addAction(color_menu, "setUserColor2")
        self.__menuActions.jobs().addAction(color_menu, "setUserColor3")
        self.__menuActions.jobs().addAction(color_menu, "setUserColor4")
        self.__menuActions.jobs().addAction(color_menu, "clearUserColor")
        menu.addMenu(color_menu)

        menu.addSeparator()
        self.__menuActions.jobs().addAction(menu, "setMaxRetries")
        if __count == 1:
            self.__menuActions.jobs().addAction(menu, "reorder")
            self.__menuActions.jobs().addAction(menu, "stagger")
        menu.addSeparator()
        if jobType["unpaused"]:
            self.__menuActions.jobs().addAction(menu, "pause")
        if jobType["paused"]:
            self.__menuActions.jobs().addAction(menu, "resume")
        menu.addSeparator()
        if jobType["hasDead"]:
            self.__menuActions.jobs().addAction(menu, "retryDead")
            self.__menuActions.jobs().addAction(menu, "eatDead")
        if jobType["notEating"]:
            self.__menuActions.jobs().addAction(menu, "autoEatOn")
        if jobType["autoEating"]:
            self.__menuActions.jobs().addAction(menu, "autoEatOff")
        menu.addSeparator()
        self.__menuActions.jobs().addAction(menu, "kill")

        menu.exec_(e.globalPos())

    def actionRemoveSelectedItems(self):
        """Unmonitors selected items"""
        for item in self.selectedItems():
            self.removeItem(item)

    def actionSetUserColor(self, color):
        """Set selected items to have provided background color"""
        for item in self.selectedItems():
            objectKey = cuegui.Utils.getObjectKey(item.rpcObject)
            if color is None and objectKey in self.__userColors:
                self.__userColors.pop(objectKey)
            elif color is not None:
                self.__userColors[objectKey] = color
            item.setUserColor(color)

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

    def updateRequest(self):
        """If sufficient time has passed since last update, call _update"""
        self.ticksWithoutUpdate = 999

    def _getUpdate(self):
        """Gets the currently monitored jobs from the cuebot. Will also load
        any of the users jobs if self.__loadMine is True
        @return: dict of updated jobs
        @rtype:  dict<class.id: job>"""
        try:
            jobs = {}

            # TODO: When getJobs is fixed to allow MatchAny, this can be updated to use one call
            monitored_proxies = []
            for item in list(self._items.values()):
                objectKey = cuegui.Utils.getObjectKey(item.rpcObject)
                if item.rpcObject.data.state == opencue.api.job_pb2.FINISHED:
                    # Reuse the old object if job is finished
                    jobs[objectKey] = item.rpcObject
                else:
                    # Gather list of all other jobs to update
                    monitored_proxies.append(objectKey)

            # Refresh the dependent proxies for the next update
            for job, dependents in iteritems(self.__dependentJobs):
                ids = [d.id() for d in dependents]
                # If the job has no dependents, then ids is an empty list,
                # The getJobs call returns every job on the cue when called
                # an empty list for the id argument!
                if not ids:
                    continue
                tmp = opencue.api.getJobs(id=ids, include_finished=True)
                self.__dependentJobs[job] = tmp

            if self.__loadMine:
                # This auto-loads all the users jobs
                for job in opencue.api.getJobs(user=[cuegui.Utils.getUsername()]):
                    self.addJob(job)

                # Prune the users jobs from the remaining proxies to update
                for proxy, job in list(jobs.items()):
                    if proxy in monitored_proxies:
                        monitored_proxies.remove(proxy)

            if monitored_proxies:
                for job in opencue.api.getJobs(
                        id=[proxyId.split('.')[-1] for proxyId in monitored_proxies],
                        include_finished=True):
                    objectKey = cuegui.Utils.getObjectKey(job)
                    jobs[objectKey] = job

        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return None

        return jobs

    def _processUpdate(self, work, rpcObjects):
        if rpcObjects is None:
            return

        self._itemsLock.lockForWrite()

        # include rpcObjects from self._items that are not in rpcObjects
        for proxy, item in list(self._items.items()):
            if not proxy in rpcObjects:
                rpcObjects[proxy] = item.rpcObject
        # pylint: disable=too-many-nested-blocks
        try:
            selectedKeys = [
                cuegui.Utils.getObjectKey(item.rpcObject) for item in self.selectedItems()]
            scrolled = self.verticalScrollBar().value()
            expanded = [cuegui.Utils.getObjectKey(item.rpcObject)
                        for item in self._items.values() if item.isExpanded()]

            # Store the creation time for the current item
            for item in list(self._items.values()):
                self.__jobTimeLoaded[cuegui.Utils.getObjectKey(item.rpcObject)] = item.created
            # Store the creation time for the dependent jobs
            for item in self._dependent_items.values():
                self.__jobTimeLoaded[cuegui.Utils.getObjectKey(item.rpcObject)] = item.created

            self._items = {}
            self.clear()

            for proxy, job in iteritems(rpcObjects):
                self._items[proxy] = JobWidgetItem(job,
                                                   self.invisibleRootItem(),
                                                   self.__jobTimeLoaded.get(proxy, None))
                if proxy in self.__userColors:
                    self._items[proxy].setUserColor(self.__userColors[proxy])
                if self.__groupDependent:
                    dependent_jobs = self.__dependentJobs.get(proxy, [])
                    for djob in dependent_jobs:
                        item = JobWidgetItem(djob,
                                             self._items[proxy],
                                             self.__jobTimeLoaded.get(proxy, None))
                        dkey = cuegui.Utils.getObjectKey(djob)
                        self._dependent_items[dkey] = item
                        if dkey in self.__userColors:
                            self._dependent_items[dkey].setUserColor(
                                           self.__userColors[dkey])

            self.verticalScrollBar().setRange(scrolled, len(rpcObjects.keys()) - scrolled)
            list(map(lambda key: self._items[key].setSelected(True),
                     [key for key in selectedKeys if key in self._items]))
            list(self._items[key].setExpanded(True) for key in expanded if key in self._items)
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
        finally:
            self._itemsLock.unlock()


class JobWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Represents a job entry in the CueJobTreeWidget."""

    __initialized = False
    __commentIcon = None
    __eatIcon = None
    __backgroundColor = None
    __foregroundColor = None
    __pausedColor = None
    __dyingColor = None
    __finishedColor = None
    __newJobColor = None
    __newJobFont = None
    __centerAlign = None
    __type = None
    __userColor = None

    # pylint: disable=protected-access
    def __init__(self, rpcObject, parent, created):
        if not self.__initialized:
            if cuegui.Style.ColorTheme is None:
                cuegui.Style.init()
            self.__class__.__initialized = True
            self.__class__.__commentIcon = QtGui.QIcon(":comment.png")
            self.__class__.__eatIcon = QtGui.QIcon(":eat.png")
            self.__class__.__backgroundColor = cuegui.app().palette().color(QtGui.QPalette.Base)
            self.__class__.__foregroundColor = cuegui.Style.ColorTheme.COLOR_JOB_FOREGROUND
            self.__class__.__pausedColor = cuegui.Style.ColorTheme.COLOR_JOB_PAUSED_BACKGROUND
            self.__class__.__dyingColor = cuegui.Style.ColorTheme.COLOR_JOB_DYING_BACKGROUND
            self.__class__.__finishedColor = cuegui.Style.ColorTheme.COLOR_JOB_FINISHED_BACKGROUND
            self.__class__.__newJobColor = QtGui.QColor(255, 255, 255)
            __font = QtGui.QFont("Luxi Sans", -1, QtGui.QFont.Bold)
            __font.setUnderline(True)
            self.__class__.__newJobFont = __font
            self.__class__.__centerAlign = QtCore.Qt.AlignCenter
            self.__class__.__type = cuegui.Constants.TYPE_JOB

        # Keeps time when job was first loaded
        self.created = created or time.time()

        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_JOB, rpcObject, parent)

    def setUserColor(self, color):
        """Sets the color scheme."""
        self.__userColor = color

    def data(self, col, role):
        if role == QtCore.Qt.DisplayRole:
            return self.column_info[col][cuegui.Constants.COLUMN_INFO_DISPLAY](self.rpcObject)

        if role == QtCore.Qt.ForegroundRole:
            if col == 0:
                if self.created > time.time() - 5:
                    return self.__newJobColor
            return self.__foregroundColor

        if role == QtCore.Qt.BackgroundRole and col == COLUMN_STATE:
            if self.rpcObject.data.state == opencue.api.job_pb2.FINISHED:
                return self.__finishedColor
            if self.rpcObject.data.is_paused:
                return self.__pausedColor
            if self.rpcObject.data.job_stats.dead_frames:
                return self.__dyingColor
            return self.__backgroundColor
        if role == QtCore.Qt.BackgroundRole and self.__userColor:
            return self.__userColor

        if role == QtCore.Qt.FontRole and col == COLUMN_NAME:
            if self.created > time.time() - 5:
                return self.__newJobFont

        elif role == QtCore.Qt.TextAlignmentRole and col == COLUMN_STATE:
            return self.__centerAlign

        elif role == QtCore.Qt.DecorationRole:
            if col == COLUMN_COMMENT and self.rpcObject.isCommented():
                return self.__commentIcon
            if col == COLUMN_AUTOEAT and self.rpcObject.isAutoEating():
                return self.__eatIcon

        elif role == QtCore.Qt.UserRole:
            return self.__type

        elif role == QtCore.Qt.UserRole + 1:
            return self.rpcObject.frameStateTotals()

        elif role == QtCore.Qt.UserRole + 2:
            return self.rpcObject.state()

        elif role == QtCore.Qt.UserRole + 3:
            return self.rpcObject.isPaused()

        return cuegui.Constants.QVARIANT_NULL
