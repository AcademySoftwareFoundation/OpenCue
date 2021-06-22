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


"""Provides actions and functions for right click menu items."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


from builtins import filter
from builtins import str
from builtins import object
import glob
import subprocess
import time

from PySide2 import QtGui
from PySide2 import QtWidgets
import six

import FileSequence
import opencue
import opencue.compiled_proto.job_pb2

# pylint: disable=cyclic-import
import cuegui.Action
import cuegui.Comments
import cuegui.Constants
import cuegui.CreatorDialog
import cuegui.DependDialog
import cuegui.DependWizard
import cuegui.EmailDialog
import cuegui.FilterDialog
import cuegui.GroupDialog
import cuegui.LayerDialog
import cuegui.LocalBooking
import cuegui.Logger
import cuegui.PreviewWidget
import cuegui.ServiceDialog
import cuegui.ShowDialog
import cuegui.TasksDialog
import cuegui.UnbookDialog
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

TITLE = 0
TOOLTIP = 1
ICON = 2


# pylint: disable=missing-function-docstring,no-self-use,unused-argument


class AbstractActions(object):
    """Parent class for all job-specific actions classes."""

    __iconCache = {}

    def __init__(self, caller, updateCallable, selectedRpcObjectsCallable, sourceCallable):
        self._caller = caller
        self.__selectedRpcObjects = selectedRpcObjectsCallable
        self._getSource = sourceCallable
        self._update = updateCallable

        self.__actionCache = {}

    def _getSelected(self, rpcObjects):
        if rpcObjects:
            return rpcObjects
        return self.__selectedRpcObjects()

    def _getOnlyJobObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isJob, self._getSelected(rpcObjects)))

    def _getOnlyLayerObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isLayer, self._getSelected(rpcObjects)))

    def _getOnlyFrameObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isFrame, self._getSelected(rpcObjects)))

    def _getOnlyShowObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isShow, self._getSelected(rpcObjects)))

    def _getOnlyRootGroupObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isRootGroup, self._getSelected(rpcObjects)))

    def _getOnlyGroupObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isGroup, self._getSelected(rpcObjects)))

    def _getOnlyHostObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isHost, self._getSelected(rpcObjects)))

    def _getOnlyProcObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isProc, self._getSelected(rpcObjects)))

    def _getOnlyTaskObjects(self, rpcObjects):
        return list(filter(cuegui.Utils.isTask, self._getSelected(rpcObjects)))

    def createAction(self, menu, title, tip=None, callback=None, icon=None):
        """Creates a context menu action."""
        if not tip:
            tip = title
        menu.addAction(cuegui.Action.create(menu, title, tip, callback, icon))

    def addAction(self, menu, actionName, callback = None):
        """Adds the requested menu item to the menu.

        @param menu: The menu that the action will be added to
        @type  menu: QMenu
        @param actionName: The name of the action to add to the menu
        @type  actionName: str
        @param callback: The function that should be called when the action is
                         selected. If not provided, the default function with
                         the same name as the action will be used
        @type  callback: callable"""
        # If the user provides a callable, use it, otherwise use the default
        # Add the action with the proper settings to the menu

        # Uses a cache to only create actions once
        key = (actionName, callback)
        if key not in self.__actionCache:
            info = getattr(self, "%s_info" % actionName)

            # Uses a cache to only load icons once
            if isinstance(info[ICON], QtGui.QColor):
                # QColor objects are not hashable
                icon_key = info[TITLE]
            else:
                icon_key = info[ICON]
            if icon_key not in self.__iconCache:
                # pylint: disable=unidiomatic-typecheck
                if type(info[ICON]) is QtGui.QColor:
                    pixmap = QtGui.QPixmap(100, 100)
                    pixmap.fill(info[ICON])
                    self.__iconCache[icon_key] = QtGui.QIcon(pixmap)
                else:
                    self.__iconCache[icon_key] = QtGui.QIcon(":%s.png" % info[ICON])

            action = QtWidgets.QAction(self.__iconCache[icon_key], info[TITLE], self._caller)

            if not callback:
                callback = actionName
            if isinstance(callback, six.string_types):
                callback = getattr(self, callback)

            action.triggered.connect(callback)
            self.__actionCache[key] = action

        menu.addAction(self.__actionCache[key])

    def cuebotCall(self, functionToCall, errorMessageTitle, *args):
        """Makes the given call to the Cuebot, displaying exception info if needed.

        @type  functionToCall: function
        @param functionToCall: The cuebot function to call.
        @type  errorMessageTitle: string
        @param errorMessageTitle: The text to display in the title of the error
                                  message box.
        @type  args: list
        @param args: The arguments to pass to the callable
        @rtype:  callable return type
        @return: Returns any results from the callable or None on exception"""
        try:
            return functionToCall(*args)
        except opencue.exception.CueException as e:
            logger.exception('Failed Cuebot call')
            QtWidgets.QMessageBox.critical(self._caller,
                                           errorMessageTitle,
                                           str(e),
                                           QtWidgets.QMessageBox.Ok)
            return None

    def getText(self, title, body, default):
        """Prompts the user for text input.

        @type  title: string
        @param title: The title to display in the input dialog
        @type  body: string
        @param body: The text to display in the input dialog
        @type  default: string
        @param default: The default text to provide in the input dialog
        @rtype: tuple(str, bool)
        @return: (input, choice)"""
        (user_input, choice) = QtWidgets.QInputDialog.getText(
            self._caller, title, body, QtWidgets.QLineEdit.Normal, default)
        return str(user_input), choice


class JobActions(AbstractActions):
    """Actions for jobs."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    unmonitor_info = ["Unmonitor", "Unmonitor selected jobs", "eject"]

    def unmonitor(self, rpcObjects=None):
        self._caller.actionRemoveSelectedItems()

    view_info = ["View Job", None, "view"]

    def view(self, rpcObjects=None):
        for job in self._getOnlyJobObjects(rpcObjects):
            # pylint: disable=no-member
            QtGui.qApp.view_object.emit(job)
            # pylint: enable=no-member

    viewDepends_info = ["&View Dependencies...", None, "log"]

    def viewDepends(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)

        cuegui.DependDialog.DependDialog(jobs[0], self._caller).show()

    emailArtist_info = ["Email Artist...", None, "mail"]

    def emailArtist(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            cuegui.EmailDialog.EmailDialog(jobs[0], self._caller).show()

    setMinCores_info = ["Set Minimum Cores...", "Set Job(s) Minimum Cores", "configure"]

    def setMinCores(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            current = max([job.data.min_cores for job in jobs])
            title = "Set Minimum Cores"
            body = "Please enter the new minimum cores value:"
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                               title, body,
                                                               current,
                                                               0, 50000, 0)
            if choice:
                for job in jobs:
                    job.setMinCores(float(value))
                self._update()

    setMaxCores_info = ["Set Maximum Cores...", "Set Job(s) Maximum Cores", "configure"]

    def setMaxCores(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            current = max([job.data.max_cores for job in jobs])
            title = "Set Maximum Cores"
            body = "Please enter the new maximum cores value:"
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                               title, body,
                                                               current,
                                                               0, 50000, 0)
            if choice:
                for job in jobs:
                    job.setMaxCores(float(value))
                self._update()

    setMinGpu_info = ["Set Minimum Gpu...", "Set Job(s) Minimum Gpu", "configure"]
    def setMinGpu(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            current = max([job.data.min_cores for job in jobs])
            title = "Set Minimum Gpu"
            body = "Please enter the new minimum gpu value:"
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                               title, body,
                                                               current,
                                                               0, 50000, 0)
            if choice:
                for job in jobs:
                    job.setMinGpu(float(value))
                self._update()

    setMaxGpu_info = ["Set Maximum Gpu...", "Set Job(s) Maximum Gpu", "configure"]
    def setMaxGpu(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            current = max([job.data.max_cores for job in jobs])
            title = "Set Maximum Gpu"
            body = "Please enter the new maximum gpu value:"
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                               title, body,
                                                               current,
                                                               0, 50000, 0)
            if choice:
                for job in jobs:
                    job.setMaxGpu(float(value))
                self._update()

    setPriority_info = ["Set Priority...", None, "configure"]

    def setPriority(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            current = max([job.data.priority for job in jobs])
            title = "Set Priority"
            body = "Please enter the new priority value:"
            (value, choice) = QtWidgets.QInputDialog.getInt(self._caller,
                                                            title, body,
                                                            current,
                                                            0, 1000000, 1)
            if choice:
                for job in jobs:
                    job.setPriority(int(value))
                self._update()

    setMaxRetries_info = ["Set Max Retries...", None, "configure"]

    def setMaxRetries(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            title = "Set Max Retries"
            body = ('Please enter the number of retries that a frame should be '
                    'allowed before it becomes dead:')
            (value, choice) = QtWidgets.QInputDialog.getInt(self._caller,
                                                            title, body,
                                                            0, 0, 10, 1)
            if choice:
                for job in jobs:
                    job.setMaxRetries(int(value))
                self._update()

    pause_info = ["&Pause", None, "pause"]

    def pause(self, rpcObjects=None):
        """pause selected jobs"""
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            for job in jobs:
                job.pause()
            self._update()

    resume_info = ["&Unpause", None, "unpause"]

    def resume(self, rpcObjects=None):
        """resume selected jobs"""
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            for job in jobs:
                job.resume()
            self._update()

    kill_info = ["&Kill", None, "kill"]

    def kill(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Kill jobs?",
                                             "Are you sure you want to kill these jobs?",
                                             [job.data.name for job in jobs]):
                for job in jobs:
                    job.kill()
                self._update()

    eatDead_info = ["Eat dead frames", None, "eat"]

    def eatDead(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Eat all DEAD frames in selected jobs?",
                                             [job.data.name for job in jobs]):
                for job in jobs:
                    job.eatFrames(state=[opencue.compiled_proto.job_pb2.DEAD])
                self._update()

    autoEatOn_info = ["Enable auto eating", None, "eat"]

    def autoEatOn(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            for job in jobs:
                job.setAutoEat(True)
                job.eatFrames(state=[opencue.compiled_proto.job_pb2.DEAD])
            self._update()

    autoEatOff_info = ["Disable auto eating", None, "eat"]

    def autoEatOff(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            for job in jobs:
                job.setAutoEat(False)
            self._update()

    retryDead_info = ["Retry dead frames", None, "retry"]

    def retryDead(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Retry all DEAD frames in selected jobs?",
                                             [job.data.name for job in jobs]):
                for job in jobs:
                    job.retryFrames(
                        state=[opencue.compiled_proto.job_pb2.DEAD])
                self._update()

    dropExternalDependencies_info = ["Drop External Dependencies", None, "kill"]

    def dropExternalDependencies(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Drop all external dependencies in selected jobs?",
                                             [job.data.name for job in jobs]):
                for job in jobs:
                    job.dropDepends(opencue.api.depend_pb2.EXTERNAL)
                self._update()

    dropInternalDependencies_info = ["Drop Internal Dependencies", None, "kill"]

    def dropInternalDependencies(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Drop all internal dependencies in selected jobs?",
                                             [job.data.name for job in jobs]):
                for job in jobs:
                    job.dropDepends(opencue.api.depend_pb2.INTERNAL)
                self._update()

    viewComments_info = ["Comments...", None, "comment"]

    def viewComments(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            cuegui.Comments.CommentListDialog(jobs[0], self._caller).show()

    dependWizard_info = ["Dependency &Wizard...", None, "configure"]

    def dependWizard(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            cuegui.DependWizard.DependWizard(self._caller, jobs)

    def __getJobRange(self, job):
        __minRange = []
        __maxRange = []
        for layer in job.getLayers():
            fs = FileSequence.FrameSet(layer.data.range)
            fs.normalize()
            __minRange.append(fs[0])
            __maxRange.append(fs[-1])
        return (min(__minRange), max(__maxRange))

    reorder_info = ["Reorder Frames...", None, "configure"]

    def reorder(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if not jobs:
            return

        __job = jobs[0]
        (__minRange, __maxRange) = self.__getJobRange(__job)

        title = "Reorder %s" % __job.data.name
        body = "What frame range should be reordered?"
        (frame_range, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice:
            return

        body = "What order should the range %s take?" % frame_range
        items = list(opencue.compiled_proto.job_pb2.Order.keys())
        (order, choice) = QtWidgets.QInputDialog.getItem(
            self._caller, title, body, sorted(items), 0, False)
        if not choice:
            return

        self.cuebotCall(
            __job.reorderFrames, "Reorder Frames Failed",
            frame_range, getattr(opencue.compiled_proto.job_pb2, str(order)))

    stagger_info = ["Stagger Frames...", None, "configure"]

    def stagger(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if not jobs:
            return

        __job = jobs[0]
        (__minRange, __maxRange) = self.__getJobRange(__job)

        title = "Stagger %s" % __job.data.name
        body = "What frame range should be staggered?"
        (frameRange, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice:
            return

        body = "What increment should the range %s be staggered?" % frameRange
        (increment, choice) = QtWidgets.QInputDialog.getInt(
            self._caller, title, body, 1, 1, 100000, 1)

        if not choice:
            return

        self.cuebotCall(__job.staggerFrames, "Stagger Frames Failed",
                        frameRange, int(increment))

    unbook_info = ["Unbook Frames...", None, "kill"]

    def unbook(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            dialog = cuegui.UnbookDialog.UnbookDialog(jobs, self._caller)
            dialog.exec_()
            self._update()

    sendToGroup_info = ["Send To Group...", None, "configure"]

    def sendToGroup(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if not jobs:
            return

        title = "Send jobs to group"
        groups = {
            group.data.name: group for group in opencue.api.findShow(jobs[0].data.show).getGroups()}
        body = "What group should these jobs move to?\n" + \
               "\n".join([job.data.name for job in jobs])

        (group, choice) = QtWidgets.QInputDialog.getItem(
            self._caller, title, body, sorted(groups.keys()), 0, False)
        if not choice:
            return

        groups[str(group)].reparentJobs(jobs)
        self._update()

    useLocalCores_info = [
        "Use local cores...", "Set a single job to use the local desktop cores", "configure"]

    def useLocalCores(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            job = jobs[0]
            dialog = cuegui.LocalBooking.LocalBookingDialog(job, self._caller)
            dialog.exec_()

    copyLogFileDir_info = ["Copy log file directory", None, "configure"]

    def copyLogFileDir(self, rpcObjects=None):
        jobs = self._getOnlyJobObjects(rpcObjects)
        if jobs:
            paths = [job.data.log_dir for job in jobs]
            QtWidgets.QApplication.clipboard().setText(
                " ".join(paths), QtGui.QClipboard.Clipboard)

    setUserColor1_info = [
        "Set Color 1", "Set user defined background color", cuegui.Constants.COLOR_USER_1]

    def setUserColor1(self, rpcObjects=None):
        self._caller.actionSetUserColor(cuegui.Constants.COLOR_USER_1)

    setUserColor2_info = [
        "Set Color 2", "Set user defined background color", cuegui.Constants.COLOR_USER_2]

    def setUserColor2(self, rpcObjects=None):
        self._caller.actionSetUserColor(cuegui.Constants.COLOR_USER_2)

    setUserColor3_info = [
        "Set Color 3", "Set user defined background color", cuegui.Constants.COLOR_USER_3]

    def setUserColor3(self, rpcObjects=None):
        self._caller.actionSetUserColor(cuegui.Constants.COLOR_USER_3)

    setUserColor4_info = [
        "Set Color 4", "Set user defined background color", cuegui.Constants.COLOR_USER_4]

    def setUserColor4(self, rpcObjects=None):
        self._caller.actionSetUserColor(cuegui.Constants.COLOR_USER_4)

    clearUserColor_info = ["Clear", "Clear user defined background color", None]

    def clearUserColor(self, rpcObjects=None):
        self._caller.actionSetUserColor(None)


class LayerActions(AbstractActions):
    """Actions for layers."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    view_info = ["View Layer", None, "view"]

    def view(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            self._caller.handle_filter_layers_byLayer.emit([layer.data.name for layer in layers])

    viewDepends_info = ["&View Dependencies...", None, "log"]

    def viewDepends(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        cuegui.DependDialog.DependDialog(layers[0], self._caller).show()

    setMinCores_info = [
        "Set Minimum Cores", "Set the number of cores required for this layer", "configure"]

    def setMinCores(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            current = max([layer.data.min_cores for layer in layers])
            title = "Set minimum number of cores required"
            body = ('Please enter the new minimum number of cores that frames in the '
                    'selected layer(s) should require:')
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0.01, 64.0, 2)
            if choice:
                for layer in layers:
                    layer.setMinCores(float(value))
                self._update()

    setMinMemoryKb_info = [
        "Set Minimum Memory", "Set the amount of memory required for this layer", "configure"]

    def setMinMemoryKb(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            current = max([layer.data.min_memory / 1048576 for layer in layers])
            title = "Set minimum amount of memory required"
            body = ('Please enter the new minimum amount of memory in GB that frames '
                    'in the selected layer(s) should require:')
            (value, choice) = QtWidgets.QInputDialog.getDouble(
                self._caller, title, body, current, 0.01, 64.0, 1)
            if choice:
                for layer in layers:
                    layer.setMinMemory(int(value * 1048576))
                self._update()

    useLocalCores_info = [
        "Use local cores...", "Set a single layer to use the local desktop cores.", "configure"]

    def useLocalCores(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            layer = layers[0]
            dialog = cuegui.LocalBooking.LocalBookingDialog(layer, self._caller)
            dialog.exec_()

    setProperties_info = ["Properties", None, "configure"]

    def setProperties(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            dialog = cuegui.LayerDialog.LayerPropertiesDialog(layers)
            dialog.exec_()
            self._update()

    setTags_info = ["Set Tags", None, "configure"]

    def setTags(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            dialog = cuegui.LayerDialog.LayerTagsDialog(layers)
            dialog.exec_()
            self._update()

    kill_info = ["&Kill", None, "kill"]

    def kill(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Kill ALL frames in selected layers?",
                                             [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.kill()
                self._update()

    eat_info = ["&Eat", None, "eat"]

    def eat(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Eat ALL frames in selected layers?",
                                             [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.eat()
                self._update()

    retry_info = ["&Retry", None, "retry"]

    def retry(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Retry ALL frames in selected layers?",
                                             [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.retry()
                self._update()

    retryDead_info = ["Retry dead frames", None, "retry"]

    def retryDead(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Retry all DEAD frames in selected layers?",
                                             [layer.data.name for layer in layers]):
                layers[-1].parent().retryFrames(layer=[layer.data.name for layer in layers],
                                                state=[opencue.api.job_pb2.DEAD])
                self._update()

    markdone_info = ["Mark done", None, "markdone"]

    def markdone(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Mark done ALL frames in selected layers?",
                                             [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.markdone()
                self._update()

    dependWizard_info = ["Dependency &Wizard...", None, "configure"]

    def dependWizard(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if layers:
            cuegui.DependWizard.DependWizard(self._caller, [self._getSource()], layers=layers)

    reorder_info = ["Reorder Frames...", None, "configure"]

    def reorder(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if not layers:
            return

        # Only allow multiple layers with the same range
        if len({layer.data.range for layer in layers}) != 1:
            return

        __layer = layers[0]
        fs = FileSequence.FrameSet(__layer.data.range)
        fs.normalize()
        __minRange = fs[0]
        __maxRange = fs[-1]

        body = "What frame range should be reordered?"
        if len(layers) > 1:
            title = "Reorder layers"
            for layer in layers:
                body += '\n%s' % layer.data.name
        else:
            title = "Reorder layer %s" % __layer.data.name

        (frameRange, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice:
            return

        body = "What order should the range %s take?" % frameRange
        items = list(opencue.compiled_proto.job_pb2.Order.keys())
        (order, choice) = QtWidgets.QInputDialog.getItem(
            self._caller, title, body, sorted(items), 0, False)
        if not choice:
            return

        for layer in layers:
            self.cuebotCall(layer.reorderFrames, "Reorder Frames Failed",
                            frameRange, getattr(opencue.compiled_proto.job_pb2, str(order)))

    stagger_info = ["Stagger Frames...", None, "configure"]

    def stagger(self, rpcObjects=None):
        layers = self._getOnlyLayerObjects(rpcObjects)
        if not layers:
            return

        __layer = layers[0]
        fs = FileSequence.FrameSet(__layer.data.range)
        fs.normalize()
        __minRange = fs[0]
        __maxRange = fs[-1]

        title = "Stagger %s" % __layer.data.name
        body = "What frame range should be staggered?"
        (frameRange, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice:
            return

        body = "What increment should the range %s be staggered?" % frameRange
        (increment, choice) = QtWidgets.QInputDialog.getInt(
            self._caller, title, body, 1, 1, 100000, 1)
        if not choice:
            return

        self.cuebotCall(__layer.staggerFrames, "Stagger Frames Failed",
                        frameRange, int(increment))


class FrameActions(AbstractActions):
    """Actions for frames."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    view_info = ["&View Log", None, "log"]

    def view(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            job = self._getSource()
            if len(frames) <= 6 or \
               cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "View %d frame logs?" % len(frames)):
                for frame in frames:
                    cuegui.Utils.popupFrameView(job, frame)

    tail_info = ["&Tail Log", None, "log"]

    def tail(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            job = self._getSource()
            if len(frames) <= 6 or \
               cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Tail %d frame logs?" % len(frames)):
                for frame in frames:
                    cuegui.Utils.popupFrameTail(job, frame)

    viewLastLog_info = ["View Last Log", None, "loglast"]

    def viewLastLog(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            job = self._getSource()
            path = cuegui.Utils.getFrameLogFile(job, frames[0])
            files = dict(
                (int(j.split(".")[-1]), j) for j in glob.glob("%s.*" % path) if j[-1].isdigit())
            if files:
                cuegui.Utils.popupView(files[sorted(files.keys())[-1]])
            else:
                cuegui.Utils.popupView(path)

    useLocalCores_info = ["Use local cores...",
                          "Set a single frame to use the local desktop cores.",
                          "configure"]

    def useLocalCores(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            frame = frames[0]
            dialog = cuegui.LocalBooking.LocalBookingDialog(frame, self._caller)
            dialog.exec_()

    xdiff2_info = ["View xdiff of 2 logs", None, "log"]

    def xdiff2(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if len(frames) >= 2:
            cuegui.Utils.popupFrameXdiff(self._getSource(), frames[0], frames[1])

    xdiff3_info = ["View xdiff of 3 logs", None, "log"]

    def xdiff3(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if len(frames) >= 3:
            cuegui.Utils.popupFrameXdiff(self._getSource(), frames[0], frames[1],  frames[2])

    viewHost_info = ["View Host", None, "log"]

    def viewHost(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        hosts = list({frame.data.last_resource.split("/")[0]
                      for frame in frames if frame.data.last_resource})
        if hosts:
            # pylint: disable=no-member
            QtGui.qApp.view_hosts.emit(hosts)
            QtGui.qApp.single_click.emit(opencue.api.findHost(hosts[0]))
            # pylint: enable=no-member

    getWhatThisDependsOn_info = ["print getWhatThisDependsOn", None, "log"]

    def getWhatThisDependsOn(self, rpcObjects=None):
        frame = self._getOnlyFrameObjects(rpcObjects)[0]

        for item in frame.getWhatThisDependsOn():
            logger.info(item.data.type, item.data.target, item.data.any_frame, item.data.active)
            logger.info(
                "This: %s %s %s", item.data.depend_er_job, item.data.depend_er_layer,
                item.data.depend_er_frame)
            logger.info(
                "On: %s %s %s", item.data.depend_on_job, item.data.depend_on_layer,
                item.data.depend_on_frame)

    viewDepends_info = ["&View Dependencies...", None, "log"]

    def viewDepends(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        cuegui.DependDialog.DependDialog(frames[0], self._caller).show()

    getWhatDependsOnThis_info = ["print getWhatDependsOnThis", None, "log"]

    def getWhatDependsOnThis(self, rpcObjects=None):
        frame = self._getOnlyFrameObjects(rpcObjects)[0]
        logger.info(frame.getWhatDependsOnThis())

    retry_info = ["&Retry", None, "retry"]

    def retry(self, rpcObjects=None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(rpcObjects)]
        if names:
            job = self._getSource()
            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm", "Retry selected frames?", names):
                job.retryFrames(name=names)
                self._update()

    previewMain_info = ["Preview Main", None, "previewMain"]

    # pylint: disable=broad-except
    def previewMain(self, rpcObjects=None):
        try:
            job = self._getSource()
            frame = self._getOnlyFrameObjects(rpcObjects)[0]
            d = cuegui.PreviewWidget.PreviewProcessorDialog(job, frame, False)
            d.process()
            d.exec_()
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Preview Error",
                                           "Error displaying preview frames, %s" % e)

    previewAovs_info = ["Preview All", None, "previewAovs"]

    # pylint: disable=broad-except
    def previewAovs(self, rpcObjects=None):
        try:
            job = self._getSource()
            frame = self._getOnlyFrameObjects(rpcObjects)[0]
            d = cuegui.PreviewWidget.PreviewProcessorDialog(job, frame, True)
            d.process()
            d.exec_()
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "Preview Error",
                                           "Error displaying preview frames, %s" % e)
    eat_info = ["&Eat", None, "eat"]

    def eat(self, rpcObjects=None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(rpcObjects)]
        if names:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Eat selected frames?",
                                             names):
                self._getSource().eatFrames(name=names)
                self._update()

    kill_info = ["&Kill", None, "kill"]

    def kill(self, rpcObjects=None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(rpcObjects)]
        if names:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Kill selected frames?",
                                             names):
                self._getSource().killFrames(name=names)
                self._update()

    markAsWaiting_info = ["Mark as &waiting", None, "configure"]

    def markAsWaiting(self, rpcObjects=None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(rpcObjects)]
        if names:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Mark selected frames as waiting?\n"
                                             "(Ignores all of the frames's dependencies once)",
                                             names):
                self._getSource().markAsWaiting(name=names)
                self._update()

    dropDepends_info = ["D&rop depends", None, "configure"]

    def dropDepends(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        names = [frame.data.name for frame in frames]
        if frames:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Drop dependencies on selected frames?\n"
                                             "(Drops all of the frame's dependencies)",
                                             names):
                for frame in frames:
                    frame.dropDepends(opencue.api.depend_pb2.ANY_TARGET)
                self._update()

    dependWizard_info = ["Dependency &Wizard...", None, "configure"]

    def dependWizard(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            cuegui.DependWizard.DependWizard(self._caller, [self._getSource()], frames=frames)

    markdone_info = ["Mark done", None, "markdone"]

    def markdone(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            frameNames = [frame.data.name for frame in frames]
            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm",
                    'Mark done all selected frames?\n'
                    '(Drops any dependencies that are waiting on these frames)', frameNames):
                self._getSource().markdoneFrames(name=frameNames)
                self._update()

    reorder_info = ["Reorder...", None, "configure"]

    def reorder(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if not frames:
            return

        __job = self._getSource()

        title = "Reorder %s" % __job.data.name
        body = "How should these frames be reordered?"
        items = list(opencue.compiled_proto.job_pb2.Order.keys())
        (order, choice) = QtWidgets.QInputDialog.getItem(
            self._caller, title, body, sorted(items), 0, False)
        if not choice:
            return

        # Store the proxy and a place for the frame numbers keyed to the layer name
        __layersDict = {layer.data.name: (layer, []) for layer in __job.getLayers()}

        # For each frame, store the number in the list for that layer
        for frame in frames:
            __layersDict[frame.data.layer_name][1].append(str(frame.data.number))

        # For each layer, join the frame range and reorder the frames
        for layer in __layersDict:
            (layerProxy, frames) = __layersDict[layer]
            if frames:
                fs = FileSequence.FrameSet(",".join(frames))
                fs.normalize()
                self.cuebotCall(layerProxy.reorderFrames,
                                "Reorder Frames Failed",
                                str(fs),
                                getattr(opencue.compiled_proto.job_pb2, str(order)))

    copyLogFileName_info = ["Copy log file name", None, "configure"]

    def copyLogFileName(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if not frames:
            return
        job = self._getSource()
        paths = [cuegui.Utils.getFrameLogFile(job, frame) for frame in frames]
        QtWidgets.QApplication.clipboard().setText(paths,
                                                   QtGui.QClipboard.Clipboard)

    eatandmarkdone_info = ["Eat and Mark done", None, "eatandmarkdone"]

    def eatandmarkdone(self, rpcObjects=None):
        frames = self._getOnlyFrameObjects(rpcObjects)
        if frames:
            frameNames = [frame.data.name for frame in frames]

            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm",
                    "Eat and Mark done all selected frames?\n"
                    "(Drops any dependencies that are waiting on these frames)\n\n"
                    "If a frame is part of a layer that will now only contain\n"
                    "eaten or succeeded frames, any dependencies on the\n"
                    "layer will be dropped as well.",
                    frameNames):

                # Mark done the layers to drop their dependencies if the layer is done

                if len(frames) == 1:
                    # Since only a single frame selected, check if layer is only one frame
                    layer = opencue.api.findLayer(self._getSource().data.name,
                                                  frames[0].data.layer_name)
                    if layer.data.layer_stats.total_frames == 1:
                        # Single frame selected of single frame layer, mark done and eat it all
                        layer.eat()
                        layer.markdone()

                        self._update()
                        return

                self._getSource().eatFrames(name=frameNames)
                self._getSource().markdoneFrames(name=frameNames)

                # Warning: The below assumes that eaten frames are desired to be markdone

                # Wait for the markDoneFrames to be processed, then drop the dependencies on
                # the layer if all frames are done.
                layerNames = [frame.data.layer_name for frame in frames]
                time.sleep(1)
                for layer in self._getSource().getLayers():
                    if layer.data.name in layerNames:
                        if (
                                layer.data.layer_stats.eaten_frames +
                                layer.data.layer_stats.succeeded_frames ==
                                layer.data.layer_stats.total_frames):
                            layer.markdone()
                self._update()


class ShowActions(AbstractActions):
    """Actions for shows."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    properties_info = ["Show Properties", None, "view"]
    def properties(self, rpcObjects=None):
        shows = self._getOnlyShowObjects(rpcObjects)
        for show in shows:
            cuegui.ShowDialog.ShowDialog(show, self._caller).show()

    createSubscription_info = ["Create Subscription...", None, "configure"]
    def createSubscription(self, rpcObjects=None):
        d = cuegui.CreatorDialog.SubscriptionCreatorDialog(
            show=self._getOnlyShowObjects(rpcObjects)[0])
        d.exec_()

    viewTasks_info = ["View Tasks...", None, "view"]
    def viewTasks(self, rpcObjects=None):
        shows = self._getOnlyShowObjects(rpcObjects)
        for show in shows:
            cuegui.TasksDialog.TasksDialog(show, self._caller).show()


class RootGroupActions(AbstractActions):
    """"Actions for root groups."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    properties_info  = ["Show Properties...", None, "view"]
    def properties(self, rpcObjects=None):
        rootgroups = self._getOnlyRootGroupObjects(rpcObjects)
        if rootgroups:
            cuegui.ShowDialog.ShowDialog(
                opencue.api.findShow(rootgroups[0].data.name), self._caller).show()

    groupProperties_info  = ["Group Properties...", None, "view"]
    def groupProperties(self, rpcObjects=None):
        rootgroups = self._getOnlyRootGroupObjects(rpcObjects)
        for rootgroup in rootgroups:
            cuegui.GroupDialog.ModifyGroupDialog(rootgroup, self._caller).show()
        self._update()

    setCuewho_info = ["Change Cuewho...", None, "configure"]
    def setCuewho(self, rpcObjects=None):
        rootgroups = self._getOnlyRootGroupObjects(rpcObjects)
        if rootgroups:
            names = [rootgroup.data.name for rootgroup in rootgroups]
            title = "Set Cuewho"
            body = "Who should be cuewho on the following shows?\n%s" % "\n".join(names)
            (name, choice) = self.getText(title, body, cuegui.Utils.getUsername())
            if choice:
                for rootgroup in rootgroups:
                    logger.info(subprocess.check_output(
                        "cuewho -s %s -who %s" % (rootgroup.data.name, name)))

    showCuewho_info = ["Display Cuewho", None, "configure"]
    def showCuewho(self, rpcObjects=None):
        rootgroups = self._getOnlyRootGroupObjects(rpcObjects)
        if rootgroups:
            message = []
            for rootgroup in rootgroups:
                cuewho = cuegui.Utils.getCuewho(rootgroup.data.name)
                extension = cuegui.Utils.getExtension(cuewho)
                message.append("Cuewho for %s is: %s %s" % (rootgroup.data.name, cuewho, extension))
            QtWidgets.QMessageBox.information(
                self._caller, "Show Cuewho", '\n'.join(message), QtWidgets.QMessageBox.Ok)

    createGroup_info = ["Create Group...", None, "configure"]
    def createGroup(self, rpcObjects=None):
        rootgroups = self._getOnlyRootGroupObjects(rpcObjects)
        if len(rootgroups) == 1:
            cuegui.GroupDialog.NewGroupDialog(rootgroups[0], self._caller).show()
            self._update()

    viewFilters_info = ["View Filters...", None, "view"]
    def viewFilters(self, rpcObjects=None):
        for rootgroup in self._getOnlyRootGroupObjects(rpcObjects):
            cuegui.FilterDialog.FilterDialog(
                opencue.api.findShow(rootgroup.data.name), self._caller).show()

    taskProperties_info = ["Task Properties...", None, "view"]
    def taskProperties(self, rpcObjects=None):
        for rootgroup in self._getOnlyRootGroupObjects(rpcObjects):
            cuegui.TasksDialog.TasksDialog(
                opencue.api.findShow(rootgroup.data.name), self._caller).show()


    serviceProperties_info = ["Service Properties...", None, "view"]
    def serviceProperties(self, rpcObjects=None):
        for rootgroup in self._getOnlyRootGroupObjects(rpcObjects):
            cuegui.ServiceDialog.ServiceDialog(
                opencue.api.findShow(rootgroup.data.name), self._caller).exec_()


class GroupActions(AbstractActions):
    """Actions for groups."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    properties_info = ["Group Properties", None, "view"]
    def properties(self, rpcObjects=None):
        groups = self._getOnlyGroupObjects(rpcObjects)
        for group in groups:
            cuegui.GroupDialog.ModifyGroupDialog(group, self._caller).show()
        self._update()

    createGroup_info = ["Create Group...", None, "configure"]
    def createGroup(self, rpcObjects=None):
        groups = self._getOnlyGroupObjects(rpcObjects)
        if len(groups) == 1:
            cuegui.GroupDialog.NewGroupDialog(groups[0], self._caller).show()
            self._update()

    deleteGroup_info = ["Delete Group", None, "configure"]
    def deleteGroup(self, rpcObjects=None):
        groups = self._getOnlyGroupObjects(rpcObjects)
        if groups:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Delete selected groups?",
                                             [group.name() for group in groups]):
                for group in groups:
                    if isinstance(group, opencue.wrappers.group.NestedGroup):
                        group = group.asGroup()
                    self.cuebotCall(group.delete, "Delete Group {} Failed".format(group.name()))


class SubscriptionActions(AbstractActions):
    """Actions for subscriptions."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    editSize_info = ["Edit Subscription Size...", None, "configure"]
    def editSize(self, rpcObjects=None):
        subs = self._getSelected(rpcObjects)
        if subs:
            current = max([sub.data.size for sub in subs])
            title = "Edit Subscription Size"
            body = "Please enter the new subscription size value:\nThis " \
                   "should only be changed by administrators.\nPlease " \
                   "contact the resource department."
            minSize = 0
            decimalPlaces = 0
            (value, choice) = QtWidgets.QInputDialog.getDouble(
                self._caller, title, body, current/100.0, minSize, cuegui.Constants.QT_MAX_INT,
                decimalPlaces)
            if choice:
                msg = QtWidgets.QMessageBox()
                msg.setText(
                    "You are about to modify a number that can affect a show's billing. Are you "
                    "sure you want to do this?")
                msg.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
                msg.setDefaultButton(QtWidgets.QMessageBox.No)
                if msg.exec_() == QtWidgets.QMessageBox.No:
                    return

                for sub in subs:
                    self.cuebotCall(sub.setSize,
                                    "Set Size on Subscription %s Failed" % sub.data.name,
                                    int(value*100.0))
                self._update()

    editBurst_info = ["Edit Subscription Burst...", None, "configure"]
    def editBurst(self, rpcObjects=None):
        subs = self._getSelected(rpcObjects)
        if subs:
            current = max([sub.data.burst for sub in subs])
            title = "Edit Subscription Burst"
            body = "Please enter the maximum number of cores that this " \
                   "subscription should be allowed to reach:"
            minSize = 0
            decimalPlaces = 0
            (value, choice) = QtWidgets.QInputDialog.getDouble(
                self._caller, title, body, current/100.0, minSize, cuegui.Constants.QT_MAX_INT,
                decimalPlaces)
            if choice:
                for sub in subs:
                    self.cuebotCall(sub.setBurst,
                                    "Set Burst on Subscription %s Failed" % sub.data.name,
                                    int(value*100.0))
                self._update()

    delete_info = ["Delete Subscription", None, "configure"]
    def delete(self, rpcObjects=None):
        subs = self._getSelected(rpcObjects)
        if subs:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Delete Subscriptions?",
                                             "Are you sure you want to delete these subscriptions?",
                                             [sub.data.name for sub in subs]):
                for sub in subs:
                    self.cuebotCall(sub.delete,
                                    "Delete Subscription %s Failed" % sub.data.name)
                self._update()


class AllocationActions(AbstractActions):
    """Actions for allocations."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)


class HostActions(AbstractActions):
    """Actions for hosts."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    viewComments_info = ["Comments...", None, "comment"]

    def viewComments(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        if hosts:
            cuegui.Comments.CommentListDialog(hosts[0], self._caller).show()

    viewProc_info = ["View Procs", None, "log"]

    def viewProc(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        hosts = list({host.data.name for host in hosts})
        if hosts:
            # pylint: disable=no-member
            QtGui.qApp.view_procs.emit(hosts)
            # pylint: enable=no-member

    lock_info = ["Lock Host", None, "lock"]

    def lock(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        for host in hosts:
            host.lock()
        self._update()

    unlock_info = ["Unlock Host", None, "lock"]

    def unlock(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        for host in hosts:
            host.unlock()
        self._update()

    delete_info = ["Delete Host", "Delete host from cuebot", "kill"]

    def delete(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        title = "Confirm"
        body = "Delete selected hosts?\n\nThis should only be done\nby opencue administrators!"
        if cuegui.Utils.questionBoxYesNo(self._caller,
                                         title,
                                         body,
                                         [host.data.name for host in hosts]):
            for host in hosts:
                for rp in host.getRenderPartitions():
                    rp.delete()

                self.cuebotCall(host.delete,
                                "Delete %s Failed" % host.data.name)
            self._update()

    rebootWhenIdle_info = ["Reboot when idle", None, "retry"]

    def rebootWhenIdle(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        title = "Confirm"
        body = ("Send request to lock the machine and reboot it when idle?\n\n" +
                "This should only be done\n" +
                "by opencue administrators!")
        if cuegui.Utils.questionBoxYesNo(self._caller,
                                         title,
                                         body,
                                         [host.data.name for host in hosts]):
            for host in hosts:
                self.cuebotCall(host.rebootWhenIdle,
                                "Reboot %s When Idle Failed" % host.data.name)
            self._update()

    addTags_info = ["Add Tags...", None, "configure"]

    def addTags(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        if hosts:
            title = "Add Tags"
            body = "What tags should be added?\n\nUse a comma or space between each"
            (tags, choice) = self.getText(title, body, "")
            if choice:
                tags = str(tags).replace(" ", ",").split(",")
                for host in hosts:
                    self.cuebotCall(host.addTags,
                                    "Add Tags to %s Failed" % host.data.name,
                                    tags)
                self._update()

    removeTags_info = ["Remove Tags...", None, "configure"]

    def removeTags(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        if hosts:
            title = "Remove Tags"
            body = "What tags should be removed?\n\nUse a comma or space between each"
            (tags, choice) = self.getText(title, body, ",".join(hosts[0].data.tags))
            if choice:
                tags = str(tags).replace(" ", ",").split(",")
                for host in hosts:
                    self.cuebotCall(host.removeTags,
                                    "Remove Tags From %s Failed" % host.data.name,
                                    tags)
                self._update()

    renameTag_info = ["Rename Tag...", None, "configure"]

    def renameTag(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        if hosts:
            title = "Rename tag"
            body = "What tag should be renamed?"
            (oldTag, choice) = QtWidgets.QInputDialog.getItem(
                self._caller, title, body, hosts[0].data.tags, 0, False)
            if not choice:
                return

            oldTag = str(oldTag)
            title = "Rename tag"
            body = "What is the new name for the tag?"
            (newTag, choice) = self.getText(title, body, oldTag)
            if not choice:
                return

            for host in hosts:
                self.cuebotCall(
                    host.renameTag, "Rename Tags on %s Failed" % host.data.name, oldTag, newTag)
            self._update()

    changeAllocation_info = ["Change Allocation...", None, "configure"]

    def changeAllocation(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        if hosts:
            allocations = {alloc.data.name: alloc for alloc in opencue.api.getAllocations()}
            title = "Move host to allocation"
            body = "What allocation should the host(s) be moved to?"
            (allocationName, choice) = QtWidgets.QInputDialog.getItem(
                self._caller, title, body, sorted(allocations.keys()), 0, False)
            if choice:
                allocation = allocations[str(allocationName)]
                for host in hosts:
                    self.cuebotCall(host.setAllocation,
                                    "Set Allocation on %s Failed" % host.data.name,
                                    allocation)
                self._update()

    setRepair_info = ["Set Repair State", None, "configure"]

    def setRepair(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        repair = opencue.api.host_pb2.REPAIR
        for host in hosts:
            if host.data.state != repair:
                host.setHardwareState(repair)
        self._update()

    clearRepair_info = ["Clear Repair State", None, "configure"]

    def clearRepair(self, rpcObjects=None):
        hosts = self._getOnlyHostObjects(rpcObjects)
        repair = opencue.api.host_pb2.REPAIR
        down = opencue.api.host_pb2.DOWN
        for host in hosts:
            if host.data.state == repair:
                host.setHardwareState(down)
        self._update()

    setThreadModeAuto_info = ["Thread Mode Auto", None, "configure"]
    def setThreadModeAuto(self, rpcObjects=None):
        for host in self._getOnlyHostObjects(rpcObjects):
            host.setThreadMode("AUTO")
        self._update()

    setThreadModeAll_info = ["Thread Mode All", None, "configure"]
    def setThreadModeAll(self, rpcObjects=None):
        for host in self._getOnlyHostObjects(rpcObjects):
            host.setThreadMode("ALL")
        self._update()

    setThreadModeVariable_info = ["Thread Mode Variable", None, "configure"]
    def setThreadModeVariable(self, rpcObjects=None):
        for host in self._getOnlyHostObjects(rpcObjects):
            host.setThreadMode("VARIABLE")
        self._update()


class ProcActions(AbstractActions):
    """Actions for procs."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    view_info = ["&View Job", None, "view"]

    def view(self, rpcObjects=None):
        for job in list({proc.data.job_name for proc in self._getOnlyProcObjects(rpcObjects)}):
            try:
                # pylint: disable=no-member
                QtGui.qApp.view_object.emit(opencue.api.findJob(job))
                # pylint: enable=no-member
            except opencue.exception.CueException:
                logger.warning("Unable to load: %s", job)

    kill_info = ["&Kill", None, "kill"]

    def kill(self, rpcObjects=None):
        procs = self._getOnlyProcObjects(rpcObjects)
        if procs:
            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm", "Kill selected frames?",
                    ["%s -> %s @ %s" % (proc.data.job_name, proc.data.frame_name, proc.data.name)
                     for proc in procs]):
                for proc in procs:
                    self.cuebotCall(proc.kill,
                                    "Kill Proc %s Failed" % proc.data.name)
                self._update()

    unbook_info = ["Unbook", None, "eject"]

    def unbook(self, rpcObjects=None):
        procs = self._getOnlyProcObjects(rpcObjects)
        if procs:
            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm", "Unbook selected frames?",
                    ["%s -> %s @ %s" % (proc.data.job_name, proc.data.frame_name, proc.data.name)
                     for proc in procs]):
                for proc in procs:
                    self.cuebotCall(proc.unbook,
                                    "Unbook Proc %s Failed" % proc.data.name,
                                    False)
                self._update()

    unbookKill_info = ["Unbook and Kill", None, "unbookkill"]

    def unbookKill(self, rpcObjects=None):
        procs = self._getOnlyProcObjects(rpcObjects)
        if procs:
            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm", "Unbook and Kill selected frames?",
                    ["%s -> %s @ %s" % (proc.data.job_name, proc.data.frame_name, proc.data.name)
                     for proc in procs]):
                for proc in procs:
                    self.cuebotCall(proc.unbook,
                                    "Unbook and Kill Proc %s Failed" % proc.data.name,
                                    True)
                self._update()


class DependenciesActions(AbstractActions):
    """Actions for depends."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    satisfy_info = ["Satisfy Dependency", None, "kill"]

    def satisfy(self, rpcObjects=None):
        dependencies = self._getSelected(rpcObjects)
        for dependency in dependencies:
            dependency.satisfy()
        self._update()

    unsatisfy_info = ["Unsatisfy Dependency", None, "retry"]

    def unsatisfy(self, rpcObjects=None):
        dependencies = self._getSelected(rpcObjects)
        for dependency in dependencies:
            dependency.unsatisfy()
        self._update()


class FilterActions(AbstractActions):
    """Actions for filters."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    rename_info = ["Rename...", None, ""]

    def rename(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        if filters:
            title = "Rename Filter"
            body = "What is the new name for the filter?"
            (name, choice) = self.getText(title, body, filters[0].data.name)

            if choice:
                filters[0].setName(name)
                self._update()

    delete_info = ["Delete", None, "kill"]

    def delete(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        if filters:
            if cuegui.Utils.questionBoxYesNo(
                    self._caller, "Confirm", "Delete selected filters?",
                    [selectedFilter.data.name for selectedFilter in filters]):
                for filterToDelete in filters:
                    filterToDelete.delete()
                self._update()

    raiseOrder_info = ["Raise Order", None, ""]

    def raiseOrder(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        for selectedFilter in filters:
            selectedFilter.raiseOrder()
        self._update()

    lowerOrder_info = ["Lower Order", None, ""]

    def lowerOrder(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        for selectedFilter in filters:
            selectedFilter.lowerOrder()
        self._update()

    orderFirst_info = ["Order First", None, ""]

    def orderFirst(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        for selectedFilter in filters:
            selectedFilter.orderFirst()
        self._update()

    orderLast_info = ["Order Last", None, ""]

    def orderLast(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        for selectedFilter in filters:
            selectedFilter.orderLast()
        self._update()

    setOrder_info = ["Set Order...", None, ""]

    def setOrder(self, rpcObjects=None):
        filters = self._getSelected(rpcObjects)
        if filters:
            title = "Set Filter Order"
            body = "Please enter the new filter order:"
            (value, choice) = QtWidgets.QInputDialog.getInt(self._caller,
                                                            title, body,
                                                            filters[0].order(),
                                                            0, 50000, 1)
            if choice:
                filters[0].setOrder(int(value))
                self._update()


class MatcherActions(AbstractActions):
    """Actions for matchers."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    delete_info = ["Delete", None, "kill"]
    def delete(self, rpcObjects=None):
        matchers = self._getSelected(rpcObjects)
        if matchers:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Delete selected matchers?",
                                             [matcher.name() for matcher in matchers]):
                for matcher in matchers:
                    matcher.delete()
                self._update()

    setValue_info = ["Change Value...", None, "configure"]
    def setValue(self, rpcObjects=None):
        matchers = self._getSelected(rpcObjects)
        if matchers:
            title = "Change Matcher Value"
            body = "What is the new value for the matcher?"
            (value, choice) = self.getText(title, body, matchers[0].input())

            if choice:
                matchers[0].setValue(value)
                self._update()


class ActionActions(AbstractActions):
    """Actions for filter actions."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    delete_info = ["Delete", None, "kill"]
    def delete(self, rpcObjects=None):
        actions = self._getSelected(rpcObjects)
        if actions:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Delete selected actions?",
                                             [action.name() for action in actions]):
                for action in actions:
                    action.delete()
                self._update()


class TaskActions(AbstractActions):
    """Actions for tasks."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    setMinCores_info = ["Set Minimum Cores...", "Set Task(s) Minimum Cores", "configure"]
    def setMinCores(self, rpcObjects=None):
        tasks = self._getSelected(rpcObjects)
        if tasks:
            current = max([task.data.min_cores for task in tasks])
            title = "Set Minimum Cores"
            body = "Please enter the new minimum cores value:"
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                               title, body,
                                                               current,
                                                               0, 50000, 0)
            if choice:
                for task in tasks:
                    task.setMinCores(float(value))
                self._update()

    clearAdjustment_info = [
        "Clear Minimum Core Adjustment", "Clear Task(s) Minimum Core Adjustment", "configure"]
    def clearAdjustment(self, rpcObjects=None):
        tasks = self._getSelected(rpcObjects)
        for task in tasks:
            task.clearAdjustment()
        self._update()

    delete_info = ["Delete Task", None, "configure"]
    def delete(self, rpcObjects=None):
        tasks = self._getOnlyTaskObjects(rpcObjects)
        if tasks:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Delete selected tasks?",
                                             [task.data.shot for task in tasks]):
                for task in tasks:
                    task.delete()
                self._update()


class LimitActions(AbstractActions):
    """Actions for limits."""

    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    create_info = ["Create Limit", None, "configure"]
    def create(self, rpcObjects=None):
        title = "Add Limit"
        body = "Enter a name for the new limit."

        (limit, choice) = self.getText(title, body, "")
        if choice:
            limit = limit.strip()
            self.cuebotCall(opencue.api.createLimit,
                            "Creating Limit {} has Failed.".format(limit),
                            *[limit, 0])
            self._update()

    delete_info = ["Delete Limit", None, "kill"]
    def delete(self, rpcObjects=None):
        limits = self._getSelected(rpcObjects)
        if limits:
            if cuegui.Utils.questionBoxYesNo(self._caller, "Confirm",
                                             "Delete selected limits?",
                                             [limit.data.name for limit in limits]):
                for limit in limits:
                    limit.delete()
                self._update()

    editMaxValue_info = ["Edit Max Value", None, "configure"]
    def editMaxValue(self, rpcObjects=None):
        limits = self._getSelected(rpcObjects)
        if limits:
            current = max([limit.data.max_value for limit in limits])
            title = "Edit Max Value"
            body = "Please enter the new Limit max value:"
            (value, choice) = QtWidgets.QInputDialog.getDouble(self._caller,
                                                               title, body,
                                                               current,
                                                               0, 999999999, 0)
            if choice:
                for limit in limits:
                    self.cuebotCall(limit.setMaxValue,
                                    "Set Max Value on Limit %s Failed" % limit.data.name,
                                    int(value))
                self._update()

    rename_info = ["Rename", None, "configure"]
    def rename(self, rpcObjects=None):
        limits = self._getSelected(rpcObjects)
        if limits and len(limits) == 1:
            title = "Rename a Limit"
            body = "Please enter the new Limit name:"
            (value, choice) = QtWidgets.QInputDialog.getText(self._caller, title, body)
            if choice:
                self.cuebotCall(limits[0].rename, "Rename failed.", value)
            self._update()


# pylint: disable=attribute-defined-outside-init
class MenuActions(object):
    """Provides access to common right click actions."""

    def __init__(self, caller, updateCallable, selectedRpcObjectsCallable, sourceCallable = None):
        """
        @param caller: The Widget that is creating the menu
        @type  caller: QWidget
        @param updateCallable: A callable that will update the display
        @type  updateCallable: callable
        @param selectedRpcObjectsCallable: A callable that will return a list of
                                           selected ice objects
        @type  selectedRpcObjectsCallable: callable
        @param sourceCallable: A callable that will return the source of the
                               data. Only required for frames.
        @type  sourceCallable: callable"""
        self.__caller = caller
        self.__updateCallable = updateCallable
        self.__selectedRpcObjectsCallable = selectedRpcObjectsCallable
        self.__sourceCallable = sourceCallable

    def __getArgs(self):
        return self.__caller, self.__updateCallable, self.__selectedRpcObjectsCallable,\
               self.__sourceCallable

    def jobs(self):
        if not hasattr(self, "_jobs"):
            self._jobs = JobActions(*self.__getArgs())
        return self._jobs

    def layers(self):
        if not hasattr(self, "_layers"):
            self._layers = LayerActions(*self.__getArgs())
        return self._layers

    def frames(self):
        if not hasattr(self, "_frames"):
            if not self.__sourceCallable:
                raise ValueError
            self._frames = FrameActions(*self.__getArgs())
        return self._frames

    def shows(self):
        if not hasattr(self, "_shows"):
            self._shows = ShowActions(*self.__getArgs())
        return self._shows

    def rootgroups(self):
        if not hasattr(self, "_rootgroups"):
            self._rootgroups = RootGroupActions(*self.__getArgs())
        return self._rootgroups

    def groups(self):
        if not hasattr(self, "_groups"):
            self._groups = GroupActions(*self.__getArgs())
        return self._groups

    def subscriptions(self):
        if not hasattr(self, "_subscriptions"):
            self._subscriptions = SubscriptionActions(*self.__getArgs())
        return self._subscriptions

    def allocations(self):
        if not hasattr(self, "_allocations"):
            self._allocations = AllocationActions(*self.__getArgs())
        return self._allocations

    def hosts(self):
        if not hasattr(self, "_hosts"):
            self._hosts = HostActions(*self.__getArgs())
        return self._hosts

    def procs(self):
        if not hasattr(self, "_procs"):
            self._procs = ProcActions(*self.__getArgs())
        return self._procs

    def dependencies(self):
        if not hasattr(self, "_dependencies"):
            self._dependencies = DependenciesActions(*self.__getArgs())
        return self._dependencies

    def filters(self):
        if not hasattr(self, "_filters"):
            self._filters = FilterActions(*self.__getArgs())
        return self._filters

    def matchers(self):
        if not hasattr(self, "_matchers"):
            self._matchers = MatcherActions(*self.__getArgs())
        return self._matchers

    def actions(self):
        if not hasattr(self, "_actions"):
            self._actions = ActionActions(*self.__getArgs())
        return self._actions

    def tasks(self):
        if not hasattr(self, "_tasks"):
            self._tasks = TaskActions(*self.__getArgs())
        return self._tasks

    def limits(self):
        if not hasattr(self, "_limits"):
            self._limits = LimitActions(*self.__getArgs())
        return self._limits
