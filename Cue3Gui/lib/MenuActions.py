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


"""
Provides actions and functions for right click menu items.
"""
import os
import sys
import time
import commands
import pexpect
import glob
import urllib2
import subprocess

from Manifest import QtCore, QtGui, Cue3, FileSequence

import Action
import Utils
import Logger
import Constants
import CreatorDialog
import PreviewWidget

from DependWizard import DependWizard
from EmailDialog import EmailDialog
from LocalBooking import LocalBookingDialog
from Comments import CommentListDialog
from ShowDialog import ShowDialog
from LayerDialog import LayerTagsDialog, LayerPropertiesDialog
from GroupDialog import NewGroupDialog, ModifyGroupDialog
from UnbookDialog import UnbookDialog
from ServiceDialog import ServiceDialog

logger = Logger.getLogger(__file__)

TITLE = 0
TOOLTIP = 1
ICON = 2

# New icons are here: /usr/share/icons/crystalsvg/16x16

class AbstractActions(object):
    __iconCache = {}
    def __init__(self, caller, updateCallable, selectedIceObjectsCallable, sourceCallable):
        self._caller = caller
        self.__selectedIceObjects = selectedIceObjectsCallable
        self._getSource = sourceCallable
        self._update = updateCallable

        self.__actionCache = {}

    def _getSelected(self, iceObjects):
        if iceObjects:
            return iceObjects
        return self.__selectedIceObjects()

    def _getOnlyJobObjects(self, iceObjects):
        return filter(Utils.isJob, self._getSelected(iceObjects))

    def _getOnlyLayerObjects(self, iceObjects):
        return filter(Utils.isLayer, self._getSelected(iceObjects))

    def _getOnlyFrameObjects(self, iceObjects):
        return filter(Utils.isFrame, self._getSelected(iceObjects))

    def _getOnlyShowObjects(self, iceObjects):
        return filter(Utils.isShow, self._getSelected(iceObjects))

    def _getOnlyRootGroupObjects(self, iceObjects):
        return filter(Utils.isRootGroup, self._getSelected(iceObjects))

    def _getOnlyGroupObjects(self, iceObjects):
        return filter(Utils.isGroup, self._getSelected(iceObjects))

    def _getOnlyHostObjects(self, iceObjects):
        return filter(Utils.isHost, self._getSelected(iceObjects))

    def _getOnlyProcObjects(self, iceObjects):
        return filter(Utils.isProc, self._getSelected(iceObjects))

    def _getOnlyTaskObjects(self, iceObjects):
        return filter(Utils.isTask, self._getSelected(iceObjects))

    def createAction(self, menu, title, tip = None, callback = None, icon = None):
        if not tip:
            tip = title
        menu.addAction(Action.create(menu, title, tip, callback, icon))

    def addAction(self, menu, actionName, callback = None):
        """Adds the requested menu item to the menu
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
        if not self.__actionCache.has_key(key):
            info = getattr(self, "%s_info" % actionName)

            # Uses a cache to only load icons once
            if not self.__iconCache.has_key(info[ICON]):
                if type(info[ICON]) is QtGui.QColor:
                    pixmap = QtGui.QPixmap(100, 100)
                    pixmap.fill(info[ICON])
                    self.__iconCache[info[ICON]] = QtGui.QIcon(pixmap)
                else:
                    self.__iconCache[info[ICON]] = QtGui.QIcon(":%s.png" % info[ICON])

            action = QtGui.QAction(self.__iconCache[info[ICON]], info[TITLE], self._caller)

            if not callback:
                callback = actionName
            if isinstance(callback, str):
                callback = getattr(self, callback)

            QtCore.QObject.connect(action, QtCore.SIGNAL("triggered()"), callback)
            self.__actionCache[key] = action

        menu.addAction(self.__actionCache[key])

    def cuebotCall(self, callable, errorMessageTitle, *args):
        """Makes the given call to the cuebot and if an exception occurs display
        a critical message box.
        @type  callable: function
        @param callable: The cuebot function to call.
        @type  errorMessageTitle: string
        @param errorMessageTitle: The text to display in the title of the error
                                  message box.
        @type  callable: Variable arguments
        @param callable: The arguments to pass to the callable
        @rtype:  callable return type
        @return: Returns any results from the callable or None on exception"""
        try:
            return callable(*args)
        except Exception, e:
            QtGui.QMessageBox.critical(self._caller,
                                       errorMessageTitle,
                                       e.message,
                                       QtGui.QMessageBox.Ok)
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
        (input, choice) = QtGui.QInputDialog.getText(self._caller,
                                                     title,
                                                     body,
                                                     QtGui.QLineEdit.Normal,
                                                     default)
        return (str(input), choice)

class JobActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    unmonitor_info = ["Unmonitor", "Unmonitor selected jobs", "eject"]
    def unmonitor(self, iceObjects = None):
        self._caller.actionRemoveSelectedItems()

    view_info = ["View Job", None, "view"]
    def view(self, iceObjects = None):
        for job in self._getOnlyJobObjects(iceObjects):
            QtGui.qApp.emit(QtCore.SIGNAL("view_object(PyQt_PyObject)"), job)

    viewDepends_info = ["&View Dependencies...", None, "log"]
    def viewDepends(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        from DependDialog import DependDialog
        DependDialog(jobs[0], self._caller).show()

    emailArtist_info = ["Email Artist...", None, "mail"]
    def emailArtist(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            EmailDialog(jobs[0], [], self._caller).show()

    setMinCores_info = ["Set Minimum Cores...", "Set Job(s) Minimum Cores", "configure"]
    def setMinCores(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            current = max([job.data.minCores for job in jobs])
            title = "Set Minimum Cores"
            body = "Please enter the new minimum cores value:"
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0, 50000, 0)
            if choice:
                for job in jobs:
                    job.proxy.setMinCores(float(value))
                self._update()

    setMaxCores_info = ["Set Maximum Cores...", "Set Job(s) Maximum Cores", "configure"]
    def setMaxCores(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            current = max([job.data.maxCores for job in jobs])
            title = "Set Maximum Cores"
            body = "Please enter the new maximum cores value:"
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0, 50000, 0)
            if choice:
                for job in jobs:
                    job.proxy.setMaxCores(float(value))
                self._update()

    setPriority_info = ["Set Priority...", None, "configure"]
    def setPriority(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            current = max([job.data.priority for job in jobs])
            title = "Set Priority"
            body = "Please enter the new priority value:"
            (value, choice) = QtGui.QInputDialog.getInteger(self._caller,
                                                            title, body,
                                                            current,
                                                            0, 1000000, 1)
            if choice:
                for job in jobs:
                    job.proxy.setPriority(int(value))
                self._update()

    setMaxRetries_info = ["Set Max Retries...", None, "configure"]
    def setMaxRetries(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            title = "Set Max Retries"
            body = "Please enter the number of retries that a frame should be allowed before it becomes dead:"
            (value, choice) = QtGui.QInputDialog.getInteger(self._caller,
                                                            title, body,
                                                            0, 0, 10, 1)
            if choice:
                for job in jobs:
                    job.proxy.setMaxRetries(int(value))
                self._update()

    pause_info = ["&Pause", None, "pause"]
    def pause(self, iceObjects = None):
        """pause selected jobs"""
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            for job in jobs:
                job.proxy.pause()
            self._update()

    resume_info = ["&Unpause", None, "unpause"]
    def resume(self, iceObjects = None):
        """resume selected jobs"""
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            for job in jobs:
                job.proxy.resume()
            self._update()

    kill_info = ["&Kill", None, "kill"]
    def kill(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            if Utils.questionBoxYesNo(self._caller, "Kill jobs?",
                                      "Are you sure you want to kill these jobs?",
                                      [job.data.name for job in jobs]):
                for job in jobs:
                    job.proxy.kill()
                self._update()

    eatDead_info = ["Eat dead frames", None, "eat"]
    def eatDead(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Eat all DEAD frames in selected jobs?",
                                      [job.data.name for job in jobs]):
                frameSearch = Cue3.FrameSearch(state=Cue3.FrameState.Dead)
                for job in jobs:
                    job.proxy.eatFrames(frameSearch)
                self._update()

    autoEatOn_info = ["Enable auto eating", None, "eat"]
    def autoEatOn(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            frameSearch = Cue3.FrameSearch(state=Cue3.FrameState.Dead)
            for job in jobs:
                job.proxy.setAutoEat(True)
                job.proxy.eatFrames(frameSearch)
            self._update()

    autoEatOff_info = ["Disable auto eating", None, "eat"]
    def autoEatOff(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            for job in jobs:
                job.proxy.setAutoEat(False)
            self._update()

    retryDead_info = ["Retry dead frames", None, "retry"]
    def retryDead(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Retry all DEAD frames in selected jobs?",
                                      [job.data.name for job in jobs]):
                frameSearch = Cue3.FrameSearch(state=Cue3.FrameState.Dead)
                for job in jobs:
                    job.proxy.retryFrames(frameSearch)
                self._update()

    dropExternalDependencies_info = ["Drop External Dependencies", None, "kill"]
    def dropExternalDependencies(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Drop all external dependencies in selected jobs?",
                                      [job.data.name for job in jobs]):
                for job in jobs:
                    job.proxy.dropDepends(Cue3.DependTarget.External)
                self._update()

    dropInternalDependencies_info = ["Drop Internal Dependencies", None, "kill"]
    def dropInternalDependencies(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Drop all internal dependencies in selected jobs?",
                                      [job.data.name for job in jobs]):
                for job in jobs:
                    job.proxy.dropDepends(Cue3.DependTarget.Internal)
                self._update()

    viewComments_info = ["Comments...", None, "comment"]
    def viewComments(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            CommentListDialog(jobs[0],self._caller).show()

    dependWizard_info = ["Dependency &Wizard...", None, "configure"]
    def dependWizard(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            DependWizard(self._caller, jobs)

    def __getJobRange(self, job):
        __minRange = []
        __maxRange = []
        for layer in job.proxy.getLayers():
            fs = FileSequence.FrameSet(layer.data.range)
            fs.normalize()
            __minRange.append(fs[0])
            __maxRange.append(fs[-1])
        return (min(__minRange), max(__maxRange))

    reorder_info = ["Reorder Frames...", None, "configure"]
    def reorder(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if not jobs: return

        __job = jobs[0]
        (__minRange, __maxRange) = self.__getJobRange(__job)

        title = "Reorder %s" % __job.data.name
        body = "What frame range should be reordered?"
        (range, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice: return

        body = "What order should the range %s take?" % range
        items = [order for order in dir(Cue3.Order) if not order.startswith("_")]
        (order, choice) = QtGui.QInputDialog.getItem(self._caller,
                                                     title,
                                                     body,
                                                     sorted(items),
                                                     0,
                                                     False)
        if not choice: return

        self.cuebotCall(__job.proxy.reorderFrames, "Reorder Frames Failed",
                        range, getattr(Cue3.Order, str(order)))

    stagger_info = ["Stagger Frames...", None, "configure"]
    def stagger(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if not jobs: return

        __job = jobs[0]
        (__minRange, __maxRange) = self.__getJobRange(__job)

        title = "Stagger %s" % __job.data.name
        body = "What frame range should be staggered?"
        (range, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice: return

        body = "What increment should the range %s be staggered?" % range
        (increment, choice) = QtGui.QInputDialog.getInteger(self._caller,
                                                            title, body,
                                                            1,
                                                            1, 100000, 1)

        if not choice: return

        self.cuebotCall(__job.proxy.staggerFrames, "Stagger Frames Failed",
                        range, int(increment))

    unbook_info = ["Unbook Frames...", None, "kill"]
    def unbook(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            dialog = UnbookDialog(jobs, self._caller)
            dialog.exec_()
            self._update()

    sendToGroup_info = ["Send To Group...", None, "configure"]
    def sendToGroup(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if not jobs:
            return

        title = "Send jobs to group"
        groups = dict([(group.data.name, group) for group in Cue3.findShow(jobs[0].data.show).getGroups()])
        body = "What group should these jobs move to?\n" + \
               "\n".join([job.data.name for job in jobs])

        (group, choice) = QtGui.QInputDialog.getItem(self._caller,
                                                     title,
                                                     body,
                                                     sorted(groups.keys()),
                                                     0,
                                                     False)
        if not choice:
            return

        groups[str(group)].proxy.reparentJobs([job.proxy for job in jobs])
        self._update()


    useLocalCores_info = ["Use local cores...",
                             "Set a single job to use the local desktop cores",
                             "configure"]

    def useLocalCores(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            job = jobs[0]
            dialog = LocalBookingDialog(job, self._caller)
            dialog.exec_()

        copyLogFileDir_info = ["Copy log file directory", None, "configure"]
    def copyLogFileDir(self, iceObjects = None):
        jobs = self._getOnlyJobObjects(iceObjects)
        if jobs:
            paths = [job.data.logDir for job in jobs]
            QtGui.QApplication.clipboard().setText(" ".join(paths),
                                                   QtGui.QClipboard.Clipboard)

    setUserColor1_info = ["Set Color 1", "Set user defined background color", Constants.COLOR_USER_1]
    def setUserColor1(self, iceObjects = None):
        self._caller.actionSetUserColor(Constants.COLOR_USER_1)

    setUserColor2_info = ["Set Color 2", "Set user defined background color", Constants.COLOR_USER_2]
    def setUserColor2(self, iceObjects = None):
        self._caller.actionSetUserColor(Constants.COLOR_USER_2)

    setUserColor3_info = ["Set Color 3", "Set user defined background color", Constants.COLOR_USER_3]
    def setUserColor3(self, iceObjects = None):
        self._caller.actionSetUserColor(Constants.COLOR_USER_3)

    setUserColor4_info = ["Set Color 4", "Set user defined background color", Constants.COLOR_USER_4]
    def setUserColor4(self, iceObjects = None):
        self._caller.actionSetUserColor(Constants.COLOR_USER_4)

    clearUserColor_info = ["Clear", "Clear user defined background color", None]
    def clearUserColor(self, iceObjects = None):
        self._caller.actionSetUserColor(None)

class LayerActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    view_info = ["View Layer", None, "view"]
    def view(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            self._caller.emit(QtCore.SIGNAL("handle_filter_layers_byLayer(PyQt_PyObject)"),
                              [layer.data.name for layer in layers])

    viewDepends_info = ["&View Dependencies...", None, "log"]
    def viewDepends(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        from DependDialog import DependDialog
        DependDialog(layers[0], self._caller).show()

    setMinCores_info = ["Set Minimum Cores", "Set the number of cores required for this layer", "configure"]
    def setMinCores(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            current = max([layer.data.minCores for layer in layers])
            title = "Set minimum number of cores required"
            body = "Please enter the new minimum number of cores that frames in the selected layer(s) should require:"
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0.01, 64.0, 2)
            if choice:
                for layer in layers:
                    layer.proxy.setMinCores(float(value))
                self._update()

    setMinMemoryKb_info = ["Set Minimum Memory", "Set the amount of memory required for this layer", "configure"]
    def setMinMemoryKb(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            current = max([layer.data.minMemory / 1048576 for layer in layers])
            title = "Set minimum amount of memory required"
            body = "Please enter the new minimum amount of memory in GB that frames in the selected layer(s) should require:"
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0.01, 64.0, 1)
            if choice:
                for layer in layers:
                    layer.setMinMemory(long(value * 1048576))
                self._update()

    useLocalCores_info = ["Use local cores...",
                          "Set a single layer to use the local desktop cores.",
                          "configure"]

    def useLocalCores(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            layer = layers[0]
            dialog = LocalBookingDialog(layer, self._caller)
            dialog.exec_()


    setProperties_info = ["Properties", None, "configure"]
    def setProperties(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            dialog = LayerPropertiesDialog(layers)
            dialog.exec_()

    setTags_info = ["Set Tags", None, "configure"]
    def setTags(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            dialog = LayerTagsDialog(layers)
            dialog.exec_()
            self._update()

    kill_info = ["&Kill", None, "kill"]
    def kill(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Kill ALL frames in selected layers?",
                                      [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.kill()
                self._update()

    eat_info = ["&Eat", None, "eat"]
    def eat(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Eat ALL frames in selected layers?",
                                      [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.eat()
                self._update()

    retry_info = ["&Retry", None, "retry"]
    def retry(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Retry ALL frames in selected layers?",
                                      [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.retry()
                self._update()

    retryDead_info = ["Retry dead frames", None, "retry"]
    def retryDead(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Retry all DEAD frames in selected layers?",
                                      [layer.data.name for layer in layers]):
                frameSearch = Cue3.FrameSearch(layer=[layer.data.name for layer in layers], state=[Cue3.FrameState.Dead])
                layer.parent.retryFrames(frameSearch)
                self._update()

    markdone_info = ["Mark done", None, "markdone"]
    def markdone(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Mark done ALL frames in selected layers?",
                                      [layer.data.name for layer in layers]):
                for layer in layers:
                    layer.proxy.markdoneFrames()
                self._update()

    dependWizard_info = ["Dependency &Wizard...", None, "configure"]
    def dependWizard(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if layers:
            DependWizard(self._caller, [self._getSource()], layers)

    reorder_info = ["Reorder Frames...", None, "configure"]
    def reorder(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if not layers: return

        # Only allow multiple layers with the same range
        if len(set([layer.data.range for layer in layers])) != 1: return

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

        (range, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice: return

        body = "What order should the range %s take?" % range
        items = [order for order in dir(Cue3.Order) if not order.startswith("_")]
        (order, choice) = QtGui.QInputDialog.getItem(self._caller,
                                                     title,
                                                     body,
                                                     sorted(items),
                                                     0,
                                                     False)
        if not choice: return

        for layer in layers:
            self.cuebotCall(layer.proxy.reorderFrames, "Reorder Frames Failed",
                            range, getattr(Cue3.Order, str(order)))

    stagger_info = ["Stagger Frames...", None, "configure"]
    def stagger(self, iceObjects = None):
        layers = self._getOnlyLayerObjects(iceObjects)
        if not layers: return

        __layer = layers[0]
        fs = FileSequence.FrameSet(__layer.data.range)
        fs.normalize()
        __minRange = fs[0]
        __maxRange = fs[-1]

        title = "Stagger %s" % __layer.data.name
        body = "What frame range should be staggered?"
        (range, choice) = self.getText(title, body, "%s-%s" % (__minRange, __maxRange))
        if not choice: return

        body = "What increment should the range %s be staggered?" % range
        (increment, choice) = QtGui.QInputDialog.getInteger(self._caller,
                                                            title, body,
                                                            1,
                                                            1, 100000, 1)

        if not choice: return

        self.cuebotCall(__layer.proxy.staggerFrames, "Stagger Frames Failed",
                        range, int(increment))

class FrameActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    view_info = ["&View Log", None, "log"]
    def view(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            job = self._getSource()
            if len(frames) <= 6 or \
               Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "View %d frame logs?" % len(frames)):
                for frame in frames:
                    Utils.popupFrameView(job, frame)

    tail_info = ["&Tail Log", None, "log"]
    def tail(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            job = self._getSource()
            if len(frames) <= 6 or \
               Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Tail %d frame logs?" % len(frames)):
                for frame in frames:
                    Utils.popupFrameTail(job, frame)

    viewLastLog_info = ["View Last Log", None, "loglast"]
    def viewLastLog(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            job = self._getSource()
            path = Utils.getFrameLogFile(job, frames[0])
            files = dict((int(j.split(".")[-1]),j) for j in glob.glob("%s.*" % (path)) if j[-1].isdigit())
            if files:
                Utils.popupView(files[sorted(files.keys())[-1]])
            else:
                Utils.popupView(path)

    useLocalCores_info = ["Use local cores...",
                          "Set a single frame to use the local desktop cores.",
                          "configure"]

    def useLocalCores(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            frame = frames[0]
            dialog = LocalBookingDialog(frame, self._caller)
            dialog.exec_()

    xdiff2_info = ["View xdiff of 2 logs", None, "log"]
    def xdiff2(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if len(frames) >= 2:
            Utils.popupFrameXdiff(self._getSource(), frames[0], frames[1])

    xdiff3_info = ["View xdiff of 3 logs", None, "log"]
    def xdiff3(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if len(frames) >= 3:
            Utils.popupFrameXdiff(self._getSource(), frames[0], frames[1],  frames[2])

    viewHost_info = ["View Host", None, "log"]
    def viewHost(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        hosts = list(set([frame.data.lastResource.split("/")[0] for frame in frames if frame.data.lastResource]))
        if hosts:
            QtGui.qApp.emit(QtCore.SIGNAL("view_hosts(PyQt_PyObject)"), hosts)
            QtGui.qApp.emit(QtCore.SIGNAL("single_click(PyQt_PyObject)"), Cue3.findHost(hosts[0]))

    getWhatThisDependsOn_info = ["print getWhatThisDependsOn", None, "log"]
    def getWhatThisDependsOn(self, iceObjects = None):
        frame = self._getOnlyFrameObjects(iceObjects)[0]

        print "type", "target", "anyFrame", "active", "dependErJob", "dependErLayer", "dependErFrame", "dependOnJob", "dependOnLayer", "dependOnFrame"
        for item in frame.getWhatThisDependsOn():
            print item.data.type, item.data.target, item.data.anyFrame, item.data.active,
            print "This:", item.data.dependErJob, item.data.dependErLayer, item.data.dependErFrame, "On:", item.data.dependOnJob, item.data.dependOnLayer, item.data.dependOnFrame

    viewDepends_info = ["&View Dependencies...", None, "log"]
    def viewDepends(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        from DependDialog import DependDialog
        DependDialog(frames[0], self._caller).show()

    getWhatDependsOnThis_info = ["print getWhatDependsOnThis", None, "log"]
    def getWhatDependsOnThis(self, iceObjects = None):
        frame = self._getOnlyFrameObjects(iceObjects)[0]
        print frame.getWhatDependsOnThis()

    retry_info = ["&Retry", None, "retry"]
    def retry(self, iceObjects = None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(iceObjects)]
        if names:
            job = self._getSource()
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Retry selected frames?",
                                      names):
                frameSearch = Cue3.FrameSearch(name=names)
                job.proxy.retryFrames(frameSearch)
                self._update()

    previewMain_info = ["Preview Main", None, "previewMain"]
    def previewMain(self, iceObjects=None):
        try:
            job = self._getSource()
            frame = self._getOnlyFrameObjects(iceObjects)[0]
            d = PreviewWidget.PreviewProcessorDialog(job, frame, False)
            d.process()
            d.exec_()
        except Exception, e:
            QtGui.QMessageBox.critical(None, "Preview Error", 
                                       "Error displaying preview frames, %s" % e)

    previewAovs_info = ["Preview All", None, "previewAovs"]
    def previewAovs(self, iceObjects=None):
        try:
            job = self._getSource()
            frame = self._getOnlyFrameObjects(iceObjects)[0]
            d = PreviewWidget.PreviewProcessorDialog(job, frame, True)
            d.process()
            d.exec_()
        except Exception, e:
            QtGui.QMessageBox.critical(None, "Preview Error", 
                                       "Error displaying preview frames, %s" % e)
    eat_info = ["&Eat", None, "eat"]
    def eat(self, iceObjects = None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(iceObjects)]
        if names:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Eat selected frames?",
                                      names):
                frameSearch = Cue3.FrameSearch(name=names)
                self._getSource().proxy.eatFrames(frameSearch)
                self._update()

    kill_info = ["&Kill", None, "kill"]
    def kill(self, iceObjects = None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(iceObjects)]
        if names:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Kill selected frames?",
                                      names):
                frameSearch = Cue3.FrameSearch(name=names)
                self._getSource().proxy.killFrames(frameSearch)
                self._update()

    markAsWaiting_info = ["Mark as &waiting", None, "configure"]
    def markAsWaiting(self, iceObjects = None):
        names = [frame.data.name for frame in self._getOnlyFrameObjects(iceObjects)]
        if names:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Mark selected frames as waiting?\n"
                                      "(Ignores all of the frames's dependencies once)",
                                      names):
                frameSearch = Cue3.FrameSearch(name=names)
                self._getSource().proxy.markAsWaiting(frameSearch)
                self._update()

    dropDepends_info = ["D&rop depends", None, "configure"]
    def dropDepends(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        names = [frame.data.name for frame in frames]
        if frames:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Drop dependencies on selected frames?\n"
                                      "(Drops all of the frame's dependencies)",
                                      names):
                for frame in frames:
                    frame.proxy.dropDepends(Cue3.DependTarget.AnyTarget)
                self._update()

    dependWizard_info = ["Dependency &Wizard...", None, "configure"]
    def dependWizard(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            DependWizard(self._caller, [self._getSource()], [], frames)

    markdone_info = ["Mark done", None, "markdone"]
    def markdone(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            frameNames = [frame.data.name for frame in frames]
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Mark done all selected frames?\n"
                                      "(Drops any dependencies that are waiting on these frames)",
                                      frameNames):
                frameSearch = Cue3.FrameSearch(name=frameNames)
                self._getSource().proxy.markDoneFrames(frameSearch)
                self._update()

    reorder_info = ["Reorder...", None, "configure"]
    def reorder(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if not frames: return

        __job = self._getSource()

        title = "Reorder %s" % __job.data.name
        body = "How should these frames be reordered?"
        items = [order for order in dir(Cue3.Order) if not order.startswith("_")]
        (order, choice) = QtGui.QInputDialog.getItem(self._caller,
                                                     title,
                                                     body,
                                                     sorted(items),
                                                     0,
                                                     False)
        if not choice: return

        # Store the proxy and a place for the frame numbers keyed to the layer name
        __layersDict = dict([(layer.data.name, (layer.proxy, [])) for layer in __job.getLayers()])

        # For each frame, store the number in the list for that layer
        for frame in frames:
            __layersDict[frame.data.layerName][1].append(str(frame.data.number))

        # For each layer, join the frame range and reorder the frames
        for layer in __layersDict:
            (layerProxy, frames) = __layersDict[layer]
            if frames:
                fs = FileSequence.FrameSet(",".join(frames))
                fs.normalize()
                self.cuebotCall(layerProxy.reorderFrames,
                                "Reorder Frames Failed",
                                str(fs),
                                getattr(Cue3.Order, str(order)))

        copyLogFileName_info = ["Copy log file name", None, "configure"]
    def copyLogFileName(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if not frames: return
        job = self._getSource()
        paths = [Utils.getFrameLogFile(job, frame) for frame in frames]
        QtGui.QApplication.clipboard().setText(paths,
                                               QtGui.QClipboard.Clipboard)

    eatandmarkdone_info = ["Eat and Mark done", None, "eatandmarkdone"]
    def eatandmarkdone(self, iceObjects = None):
        frames = self._getOnlyFrameObjects(iceObjects)
        if frames:
            frameNames = [frame.data.name for frame in frames]

            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Eat and Mark done all selected frames?\n"
                                      "(Drops any dependencies that are waiting on these frames)\n\n"
                                      "If a frame is part of a layer that will now only contain\n"
                                      "eaten or succeeded frames, any dependencies on the\n"
                                      "layer will be dropped as well.",
                                      frameNames):

                # Mark done the layers to drop their dependences if the layer is done

                if len(frames) == 1:
                    # Since only a single frame selected, check if layer is only one frame
                    layer = Cue3.findLayer(self._getSource().data.name, frames[0].data.layerName)
                    if layer.stats.totalFrames == 1:
                        # Single frame selected of single frame layer, mark done and eat it all
                        print 'single frame layer found'
                        layer.proxy.eatFrames()
                        layer.proxy.markdoneFrames()

                        self._update()
                        return

                frameSearch = Cue3.FrameSearch(name=frameNames)
                self._getSource().proxy.eatFrames(frameSearch)
                self._getSource().proxy.markDoneFrames(frameSearch)

                # Warning: The below assumes that eaten frames are desired to be markdone

                # Wait for the markDoneFrames to be processed, then drop the dependencies on the layer if all frames are done
                layerNames = [frame.data.layerName for frame in frames]
                time.sleep(1)
                for layer in self._getSource().proxy.getLayers():
                    if layer.data.name in layerNames:
                        if layer.stats.eatenFrames + layer.stats.succeededFrames == layer.stats.totalFrames:
                            layer.proxy.markdoneFrames()
                self._update()


class ShowActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    properties_info = ["Show Properties", None, "view"]
    def properties(self, iceObjects = None):
        shows = self._getOnlyShowObjects(iceObjects)
        for show in shows:
            ShowDialog(show, self._caller).show()

    createSubscription_info = ["Create Subscription...", None, "configure"]
    def createSubscription(self, iceObjects = None):
        d = CreatorDialog.SubscriptionCreatorDialog(show=self._getOnlyShowObjects(iceObjects)[0])
        d.exec_()

    viewTasks_info = ["View Tasks...", None, "view"]
    def viewTasks(self, iceObjects = None):
        shows = self._getOnlyShowObjects(iceObjects)
        from TasksDialog import TasksDialog
        for show in shows:
            TasksDialog(show, self._caller).show()

class RootGroupActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    properties_info  = ["Show Properties...", None, "view"]
    def properties(self, iceObjects = None):
        rootgroups = self._getOnlyRootGroupObjects(iceObjects)
        if rootgroups:
            ShowDialog(Cue3.findShow(rootgroups[0].data.name), self._caller).show()

    groupProperties_info  = ["Group Properties...", None, "view"]
    def groupProperties(self, iceObjects = None):
        rootgroups = self._getOnlyRootGroupObjects(iceObjects)
        for rootgroup in rootgroups:
            ModifyGroupDialog(rootgroup, self._caller).show()
        self._update()

    setCuewho_info = ["Change Cuewho...", None, "configure"]
    def setCuewho(self, iceObjects = None):
        rootgroups = self._getOnlyRootGroupObjects(iceObjects)
        if rootgroups:
            names = [rootgroup.data.name for rootgroup in rootgroups]
            title = "Set Cuewho"
            body = "Who should be cuewho on the following shows?\n%s" % "\n".join(names)
            (name, choice) = self.getText(title, body, Utils.getUsername())
            if choice:
                for rootgroup in rootgroups:
                    print commands.getoutput("cuewho -s %s -who %s" % (rootgroup.data.name, name))

    showCuewho_info = ["Display Cuewho", None, "configure"]
    def showCuewho(self, iceObjects = None):
        rootgroups = self._getOnlyRootGroupObjects(iceObjects)
        if rootgroups:
            message = []
            for rootgroup in rootgroups:
                cuewho = Utils.getCuewho(rootgroup.data.name)
                extension = Utils.getExtension(cuewho)
                message.append("Cuewho for %s is: %s %s" % (rootgroup.data.name, cuewho, extension ))
            QtGui.QMessageBox.information(self._caller,
                                          "Show Cuewho",
                                          '\n'.join(message),
                                          QtGui.QMessageBox.Ok)

    createGroup_info = ["Create Group...", None, "configure"]
    def createGroup(self, iceObjects = None):
        rootgroups = self._getOnlyRootGroupObjects(iceObjects)
        if len(rootgroups) == 1:
            NewGroupDialog(rootgroups[0], self._caller).show()
            self._update()

    viewFilters_info = ["View Filters...", None, "view"]
    def viewFilters(self, iceObjects = None):
        from FilterDialog import FilterDialog
        for rootgroup in self._getOnlyRootGroupObjects(iceObjects):
            FilterDialog(Cue3.findShow(rootgroup.data.name), self._caller).show()

    taskProperties_info = ["Task Properties...", None, "view"]
    def taskProperties(self, iceObjects = None):
        from TasksDialog import TasksDialog
        for rootgroup in self._getOnlyRootGroupObjects(iceObjects):
            TasksDialog(Cue3.findShow(rootgroup.data.name), self._caller).show()


    serviceProperties_info = ["Service Properies...", None, "view"]
    def serviceProperties(self, iceObjects = None):
        from TasksDialog import TasksDialog
        for rootgroup in self._getOnlyRootGroupObjects(iceObjects):
            ServiceDialog(Cue3.findShow(rootgroup.data.name), self._caller).exec_()

class GroupActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    properties_info = ["Group Properties", None, "view"]
    def properties(self, iceObjects = None):
        groups = self._getOnlyGroupObjects(iceObjects)
        for group in groups:
            ModifyGroupDialog(group, self._caller).show()
        self._update()

    createGroup_info = ["Create Group...", None, "configure"]
    def createGroup(self, iceObjects = None):
        groups = self._getOnlyGroupObjects(iceObjects)
        if len(groups) == 1:
            NewGroupDialog(groups[0], self._caller).show()
            self._update()

    deleteGroup_info = ["Delete Group", None, "configure"]
    def deleteGroup(self, iceObjects = None):
        groups = self._getOnlyGroupObjects(iceObjects)
        if groups:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Delete selected groups?",
                                      [group.data.name for group in groups]):
                for group in groups:
                    self.cuebotCall(group.delete,
                                    "Delete Group %s Failed" % group.data.name)

class SubscriptionActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    editSize_info = ["Edit Subscription Size...", None, "configure"]
    def editSize(self, iceObjects = None):
        subs = self._getSelected(iceObjects)
        if subs:
            current = max([sub.data.size for sub in subs])
            title = "Edit Subscription Size"
            body = "Please enter the new subscription size value:\nThis " \
                   "should only be changed by administrators.\nPlease " \
                   "contact the resource department."
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0, 50000, 0)
            if choice:
                msg = QtGui.QMessageBox()
                msg.setText("You are about to modify a number that can effect a shows billing. Are you in PSR-Resources?")
                msg.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
                msg.setDefaultButton(QtGui.QMessageBox.No)
                if msg.exec_() == QtGui.QMessageBox.No:
                    return

                for sub in subs:
                    self.cuebotCall(sub.proxy.setSize,
                                    "Set Size on Subscription %s Failed" % sub.data.name,
                                    float(value))
                self._update()

    editBurst_info = ["Edit Subscription Burst...", None, "configure"]
    def editBurst(self, iceObjects = None):
        subs = self._getSelected(iceObjects)
        if subs:
            current = max([sub.data.burst for sub in subs])
            title = "Edit Subscription Burst"
            body = "Please enter the maximum number of cores that this " \
                   "subscription should be allowed to reach:"
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0, 50000, 0)
            if choice:
                for sub in subs:
                    self.cuebotCall(sub.proxy.setBurst,
                                    "Set Burst on Subscription %s Failed" % sub.data.name,
                                    float(value))
                self._update()

    delete_info = ["Delete Subscription", None, "configure"]
    def delete(self, iceObjects = None):
        subs = self._getSelected(iceObjects)
        if subs:
            if Utils.questionBoxYesNo(self._caller, "Delete Subscriptions?",
                                      "Are you sure you want to delete these subscriptions?",
                                      [sub.data.name for sub in subs]):
                for sub in subs:
                    self.cuebotCall(sub.delete,
                                    "Delete Subscription %s Failed" % sub.data.name)
                self._update()

class AllocationActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

class HostActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    viewComments_info = ["Comments...", None, "comment"]
    def viewComments(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        if hosts:
            CommentListDialog(hosts[0], self._caller).show()

    viewProc_info = ["View Procs", None, "log"]
    def viewProc(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        hosts = list(set([host.data.name for host in hosts]))
        if hosts:
            QtGui.qApp.emit(QtCore.SIGNAL("view_procs(PyQt_PyObject)"), hosts)

    hinv_info = ["View Host Information (hinv)", None, "view"]
    def hinv(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        for host in hosts:
            try:
                lines = pexpect.run("rsh %s hinv" % host.data.name, timeout=10).splitlines()
                QtGui.QMessageBox.information(self._caller,
                                              "%s hinv" % host.data.name,
                                              "\n".join(lines),
                                              QtGui.QMessageBox.Ok)
            except Exception, e:
                logger.warning("Failed to get host's hinv: %s" % e)

    lock_info = ["Lock Host", None, "lock"]
    def lock(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        for host in hosts:
            host.proxy.lock()
        self._update()

    unlock_info = ["Unlock Host", None, "lock"]
    def unlock(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        for host in hosts:
            host.proxy.unlock()
        self._update()

    delete_info = ["Delete Host", "Delete host from cuebot", "kill"]
    def delete(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        title = "Confirm"
        body = "Delete selected hosts?\n\nThis should only be done\nby cue3 administrators!"
        if Utils.questionBoxYesNo(self._caller,
                                  title,
                                  body,
                                  [host.data.name for host in hosts]):
            for host in hosts:
                # Delete current render partitions to avoid oracle exception
                for rp in host.proxy.getRenderPartitions():
                    rp.proxy.delete()

                self.cuebotCall(host.proxy.delete,
                                "Delete %s Failed" % host.data.name)
            self._update()

    rebootWhenIdle_info = ["Reboot when idle", None, "retry"]
    def rebootWhenIdle(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        title = "Confirm"
        body = "Send request to lock the machine and reboot it when idle?\n\nThis should only be done\nby cue3 administrators!"
        if Utils.questionBoxYesNo(self._caller,
                                  title,
                                  body,
                                  [host.data.name for host in hosts]):
            for host in hosts:
                self.cuebotCall(host.proxy.rebootWhenIdle,
                                "Reboot %s When Idle Failed" % host.data.name)
            self._update()

    addTags_info = ["Add Tags...", None, "configure"]
    def addTags(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        if hosts:
            title = "Add Tags"
            body = "What tags should be added?\n\nUse a comma or space between each"
            (tags, choice) = self.getText(title, body, "")
            if choice:
                tags = str(tags).replace(" ", ",").split(",")
                for host in hosts:
                    self.cuebotCall(host.proxy.addTags,
                                    "Add Tags to %s Failed" % host.data.name,
                                    tags)
                self._update()

    removeTags_info = ["Remove Tags...", None, "configure"]
    def removeTags(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        if hosts:
            title = "Remove Tags"
            body = "What tags should be removed?\n\nUse a comma or space between each"
            (tags, choice) = self.getText(title, body, ",".join(hosts[0].data.tags))
            if choice:
                tags = str(tags).replace(" ", ",").split(",")
                for host in hosts:
                    self.cuebotCall(host.proxy.removeTags,
                                    "Remove Tags From %s Failed" % host.data.name,
                                    tags)
                self._update()

    renameTag_info = ["Rename Tag...", None, "configure"]
    def renameTag(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        if hosts:
            title = "Rename tag"
            body = "What tag should be renamed?"
            (oldTag, choice) = QtGui.QInputDialog.getItem(self._caller,
                                                          title, body,
                                                          hosts[0].data.tags,
                                                          0, False)
            if not choice: return

            oldTag = str(oldTag)
            title = "Rename tag"
            body = "What is the new name for the tag?"
            (newTag, choice) = self.getText(title, body, oldTag)
            if not choice: return

            for host in hosts:
                self.cuebotCall(host.proxy.renameTag,
                                "Rename Tags on %s Failed" % host.data.name,
                                oldTag, newTag)
            self._update()

    changeAllocation_info = ["Change Allocation...", None, "configure"]
    def changeAllocation(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        if hosts:
            allocations = dict([(alloc.data.name, alloc) for alloc in Cue3.getAllocations()])
            title = "Move host to allocation"
            body = "What allocation should the host(s) be moved to?"
            (allocationName, choice) = QtGui.QInputDialog.getItem(self._caller,
                                                                  title, body,
                                                                  sorted(allocations.keys()),
                                                                  0, False)
            if choice:
                allocation = allocations[str(allocationName)]
                for host in hosts:
                    self.cuebotCall(host.proxy.setAllocation,
                                    "Set Allocation on %s Failed" % host.data.name,
                                    allocation.proxy)
                self._update()

    setRepair_info = ["Set Repair State", None, "configure"]
    def setRepair(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        repair = Cue3.HardwareState.Repair
        for host in hosts:
            if host.data.state != repair:
                host.proxy.setHardwareState(repair)
        self._update()

    clearRepair_info = ["Clear Repair State", None, "configure"]
    def clearRepair(self, iceObjects = None):
        hosts = self._getOnlyHostObjects(iceObjects)
        repair = Cue3.HardwareState.Repair
        down = Cue3.HardwareState.Down
        for host in hosts:
            if host.data.state == repair:
                host.proxy.setHardwareState(down)
        self._update()

class ProcActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    view_info = ["&View Job", None, "view"]
    def view(self, iceObjects = None):
        for job in list(set([proc.data.jobName for proc in self._getOnlyProcObjects(iceObjects)])):
            try:
                QtGui.qApp.emit(QtCore.SIGNAL("view_object(PyQt_PyObject)"), Cue3.findJob(job))
            except Exception, e:
                log.warning("Unable to load: %s" % job)

    kill_info = ["&Kill", None, "kill"]
    def kill(self, iceObjects = None):
        procs = self._getOnlyProcObjects(iceObjects)
        if procs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Kill selected frames?",
                                      ["%s -> %s @ %s" % (proc.data.jobName, proc.data.frameName, proc.data.name) for proc in procs]):
                for proc in procs:
                    self.cuebotCall(proc.proxy.kill,
                                    "Kill Proc %s Failed" % proc.data.name)
                self._update()

    unbook_info = ["Unbook", None, "eject"]
    def unbook(self, iceObjects = None):
        procs = self._getOnlyProcObjects(iceObjects)
        if procs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Unbook selected frames?",
                                      ["%s -> %s @ %s" % (proc.data.jobName, proc.data.frameName, proc.data.name) for proc in procs]):
                for proc in procs:
                    self.cuebotCall(proc.proxy.unbook,
                                    "Unbook Proc %s Failed" % proc.data.name,
                                    False)
                self._update()

    unbookKill_info = ["Unbook and Kill", None, "unbookkill"]
    def unbookKill(self, iceObjects = None):
        procs = self._getOnlyProcObjects(iceObjects)
        if procs:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Unbook and Kill selected frames?",
                                      ["%s -> %s @ %s" % (proc.data.jobName, proc.data.frameName, proc.data.name) for proc in procs]):
                for proc in procs:
                    self.cuebotCall(proc.proxy.unbook,
                                    "Unbook and Kill Proc %s Failed" % proc.data.name,
                                    True)
                self._update()

class DependenciesActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    satisfy_info = ["Satisfy Dependency", None, "kill"]
    def satisfy(self, iceObjects = None):
        dependencies = self._getSelected(iceObjects)
        for dependency in dependencies:
            dependency.proxy.satisfy()
        self._update()

    unsatisfy_info = ["Unsatisfy Dependency", None, "retry"]
    def unsatisfy(self, iceObjects = None):
        dependencies = self._getSelected(iceObjects)
        for dependency in dependencies:
            dependency.proxy.unsatisfy()
        self._update()

class FilterActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    rename_info = ["Rename...", None, ""]
    def rename(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        if filters:
            title = "Rename Filter"
            body = "What is the new name for the filter?"
            (name, choice) = self.getText(title, body, filters[0].data.name)

            if choice:
                filters[0].setName(name)
                self._update()

    delete_info = ["Delete", None, "kill"]
    def delete(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        if filters:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Delete selected filters?",
                                      [filter.data.name for filter in filters]):
                for filter in filters:
                    filter.delete()
                self._update()

    raiseOrder_info = ["Raise Order", None, ""]
    def raiseOrder(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        for filter in filters:
            filter.raiseOrder()
        self._update()

    lowerOrder_info = ["Lower Order", None, ""]
    def lowerOrder(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        for filter in filters:
            filter.lowerOrder()
        self._update()

    orderFirst_info = ["Order First", None, ""]
    def orderFirst(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        for filter in filters:
            filter.orderFirst()
        self._update()

    orderLast_info = ["Order Last", None, ""]
    def orderLast(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        for filter in filters:
            filter.orderLast()
        self._update()

    setOrder_info = ["Set Order...", None, ""]
    def setOrder(self, iceObjects = None):
        filters = self._getSelected(iceObjects)
        if filters:
            title = "Set Filter Order"
            body = "Please enter the new filter order:"
            (value, choice) = QtGui.QInputDialog.getInteger(self._caller,
                                                            title, body,
                                                            filters[0].order(),
                                                            0, 50000, 1)
            if choice:
                filters[0].setOrder(int(value))
                self._update()

class MatcherActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    delete_info = ["Delete", None, "kill"]
    def delete(self, iceObjects = None):
        matchers = self._getSelected(iceObjects)
        if matchers:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Delete selected matchers?",
                                      [matcher.data.name for matcher in matchers]):
                for matcher in matchers:
                    matcher.delete()
                self._update()

    setValue_info = ["Change Value...", None, "configure"]
    def setValue(self, iceObjects = None):
        matchers = self._getSelected(iceObjects)
        if matchers:
            title = "Change Matcher Value"
            body = "What is the new value for the matcher?"
            (value, choice) = self.getText(title, body, matchers[0].input())

            if choice:
                matchers[0].setValue(value)
                self._update()

class ActionActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    delete_info = ["Delete", None, "kill"]
    def delete(self, iceObjects = None):
        actions = self._getSelected(iceObjects)
        if actions:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Delete selected actions?",
                                      [action.data.name for action in actions]):
                for action in actions:
                    action.delete()
                self._update()

class TaskActions(AbstractActions):
    def __init__(self, *args):
        AbstractActions.__init__(self, *args)

    setMinCores_info = ["Set Minimum Cores...", "Set Task(s) Minimum Cores", "configure"]
    def setMinCores(self, iceObjects = None):
        tasks = self._getSelected(iceObjects)
        if tasks:
            current = max([task.data.minCores for task in tasks])
            title = "Set Minimum Cores"
            body = "Please enter the new minimum cores value:"
            (value, choice) = QtGui.QInputDialog.getDouble(self._caller,
                                                           title, body,
                                                           current,
                                                           0, 50000, 0)
            if choice:
                for task in tasks:
                    task.proxy.setMinCores(float(value))
                self._update()

    clearAdjustment_info = ["Clear Minimum Core Adjustment", "Clear Task(s) Minimum Core Adjustment", "configure"]
    def clearAdjustment(self, iceObjects = None):
        tasks = self._getSelected(iceObjects)
        for task in tasks:
            task.proxy.clearAdjustment()
        self._update()

    delete_info = ["Delete Task", None, "configure"]
    def delete(self, iceObjects = None):
        tasks = self._getOnlyTaskObjects(iceObjects)
        if tasks:
            if Utils.questionBoxYesNo(self._caller, "Confirm",
                                      "Delete selected tasks?",
                                      [task.data.shot for task in tasks]):
                for task in tasks:
                    task.proxy.delete()
                self._update()


class MenuActions(object):
    def __init__(self, caller, updateCallable, selectedIceObjectsCallable, sourceCallable = None):
        """This object provides access to common right click actions
        @param caller: The Widget that is creating the menu
        @type  caller: QWidget
        @param updateCallable: A callable that will update the display
        @type  updateCallable: callable
        @param selectedIceObjectsCallable: A callable that will return a list of
                                           selected ice objects
        @type  selectedIceObjectsCallable: callable
        @param sourceCallable: A callable that will return the source of the
                               data. Only required for frames.
        @type  sourceCallable: callable"""
        self.__caller = caller
        self.__updateCallable = updateCallable
        self.__selectedIceObjectsCallable = selectedIceObjectsCallable
        self.__sourceCallable = sourceCallable

    def __getArgs(self):
        return self.__caller, self.__updateCallable, self.__selectedIceObjectsCallable, self.__sourceCallable

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
