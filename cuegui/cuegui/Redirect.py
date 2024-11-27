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


"""An interface for redirecting resources from one job to another job.

The concept here is that there is a target job that needs procs. The user would choose the job.
The highest core/memory value would be detected and would populate 2 text boxes for cores and
memory. The user could then adjust these and hit search. The search will find all hosts that have
frames running that can be redirected to the target job."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import range
import os
import re
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

import opencue

import cuegui.Logger
import cuegui.Utils

logger = cuegui.Logger.getLogger(__file__)

MEMORY_PATTERN = re.compile("[0-9]+(?:TB|GB|MB|KB)")
MEMORY_BTYPE = "TB|GB|MB|KB"


class ShowCombo(QtWidgets.QComboBox):
    """
    A combo box for show selection
    """
    def __init__(self, selected="pipe", parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.refresh()
        self.setCurrentIndex(self.findText(selected))

    def refresh(self):
        """Refreshes the show list."""
        self.clear()
        shows = opencue.api.getActiveShows()
        shows.sort(key=lambda x: x.data.name)

        for show in shows:
            self.addItem(show.data.name, show)

    def getShow(self):
        """Gets the selected show."""
        return str(self.setCurrentText())


class AllocFilter(QtWidgets.QPushButton):
    """
    A drop down box for selecting allocations you want
    to include in the redirect.
    """
    default = ["lax.spinux"]

    def __init__(self, parent=None):
        QtWidgets.QPushButton.__init__(self, "Allocations", parent)
        self.__menu = QtWidgets.QMenu(self)
        self.__selected = None

        self.refresh()
        self.setMenu(self.__menu)

        # This is used to provide the number of allocations selected
        # on the button title.
        self.__menu.triggered.connect(self.__afterClicked)  # pylint: disable=no-member

    def refresh(self):
        """Refreshes the full list of allocations."""
        allocs = opencue.api.getAllocations()
        allocs.sort(key=lambda x: x.data.name)

        self.__menu.clear()
        checked = 0
        for alloc in allocs:
            a = QtWidgets.QAction(self.__menu)
            a.setText(alloc.data.name)
            a.setCheckable(True)
            if alloc.data.name in AllocFilter.default:
                a.setChecked(True)
                checked += 1
            self.__menu.addAction(a)
        self.__setSelected()
        self.setText("Allocations (%d)" % checked)

    def getSelected(self):
        """
        Return an immutable set of selected allocations.
        """
        return self.__selected

    def isFiltered(self, host):
        """
        Return true if the host should be filtered.
        """
        return host.data.allocName not in self.__selected

    def __setSelected(self):
        """
        Build the selected set of allocations.
        """
        selected = []
        for item in self.__menu.actions():
            if item.isChecked():
                selected.append(str(item.text()))
        self.__selected = selected

    def __afterClicked(self, action):
        """
        Execute after an allocation has been selected for filtering.
        """
        del action
        self.__setSelected()
        self.setText("Allocations (%d)" % len(self.__selected))


class JobBox(QtWidgets.QLineEdit):
    """
    A text box that auto-completes job names.
    """
    def __init__(self,  parent=None):
        QtWidgets.QLineEdit.__init__(self, parent)

        self.__c = None
        self.refresh()

    def refresh(self):
        """Refreshes the list of job names."""
        slist = opencue.api.getJobNames()
        slist.sort()

        self.__c = QtWidgets.QCompleter(slist, self)
        self.__c.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setCompleter(self.__c)


class GroupFilter(QtWidgets.QPushButton):
    """
    A Button widget that displays a drop down menu of
    selectable groups.
    """
    def __init__(self, show, name, parent=None):
        QtWidgets.QPushButton.__init__(self, name, parent)

        self.__show = self.__loadShow(show)
        self.__menu = QtWidgets.QMenu(self)
        self.__actions = { }

        self.setMenu(self.__menu)

        self.__menu.aboutToShow.connect(self.__populate_menu)  # pylint: disable=no-member

    # pylint: disable=inconsistent-return-statements
    def __loadShow(self, show):
        self.__actions = {}
        # pylint: disable=bare-except
        try:
            if show:
                return show
        except:
            return opencue.api.findShow(show.name())

    def showChanged(self, show):
        """Loads a new show."""
        self.__show = self.__loadShow(show)

    def __populate_menu(self):
        self.__menu.clear()
        for group in self.__show.getGroups():
            if opencue.id(group) in self.__actions:
                self.__menu.addAction(self.__actions[opencue.id(group)])
            else:
                action = QtWidgets.QAction(self)
                action.setText(group.data.name)
                action.setCheckable(True)
                self.__actions[opencue.id(group)] = action
                self.__menu.addAction(action)

    def getChecked(self):
        """Gets a list of action text for all selected actions."""
        return [str(action.text()) for action in
                list(self.__actions.values()) if action.isChecked()]


class RedirectControls(QtWidgets.QWidget):
    """
    A widget that contains all the controls to search for possible
    procs that can be redirected.
    """
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__current_show = opencue.api.findShow(os.getenv("SHOW", "pipe"))

        self.__show_combo = ShowCombo(self.__current_show.data.name, self)
        self.__job_box = JobBox(self)
        self.__alloc_filter = AllocFilter(self)

        self.__cores_spin = QtWidgets.QSpinBox(self)
        self.__cores_spin.setRange(1, self._cfg().get('max_cores', 32))
        self.__cores_spin.setValue(1)

        self.__max_cores_spin = QtWidgets.QSpinBox(self)
        self.__max_cores_spin.setRange(1, self._cfg().get('max_cores', 32))
        self.__max_cores_spin.setValue(32)

        self.__mem_spin = QtWidgets.QDoubleSpinBox(self)
        self.__mem_spin.setRange(1, self._cfg().get('max_memory', 250))
        self.__mem_spin.setDecimals(1)
        self.__mem_spin.setValue(4)
        self.__mem_spin.setSuffix("GB")

        self.__limit_spin = QtWidgets.QSpinBox(self)
        self.__limit_spin.setRange(1, 100)
        self.__limit_spin.setValue(10)

        self.__prh_spin = QtWidgets.QDoubleSpinBox(self)
        # increase Proc Hour upper bound limit
        self.__prh_spin.setRange(1, 500)
        self.__prh_spin.setDecimals(1)
        self.__prh_spin.setValue(20)
        self.__prh_spin.setSuffix("PrcHrs")

        # Job Filters
        self.__include_group_btn = GroupFilter(self.__current_show, "Include Groups", self)
        self.__require_services = QtWidgets.QLineEdit(self)
        self.__exclude_regex =  QtWidgets.QLineEdit(self)

        self.__update_btn = QtWidgets.QPushButton("Search", self)
        self.__redirect_btn = QtWidgets.QPushButton("Redirect", self)
        self.__select_all_btn = QtWidgets.QPushButton("Select All", self)
        self.__clear_btn = QtWidgets.QPushButton("Clr", self)

        self.__group = QtWidgets.QGroupBox("Resource Filters")
        self.__groupFilter = QtWidgets.QGroupBox("Job Filters")

        layout1 = QtWidgets.QHBoxLayout()
        layout1.addWidget(self.__update_btn)
        layout1.addWidget(self.__redirect_btn)
        layout1.addWidget(self.__select_all_btn)
        layout1.addWidget(QtWidgets.QLabel("Target:", self))
        layout1.addWidget(self.__job_box)
        layout1.addWidget(self.__clear_btn)

        layout2 = QtWidgets.QHBoxLayout()
        layout2.addWidget(self.__alloc_filter)
        layout2.addWidget(QtWidgets.QLabel("Minimum Cores:", self))
        layout2.addWidget(self.__cores_spin)
        layout2.addWidget(QtWidgets.QLabel("Max Cores:", self))
        layout2.addWidget(self.__max_cores_spin)
        layout2.addWidget(QtWidgets.QLabel("Minimum Memory:", self))
        layout2.addWidget(self.__mem_spin)
        layout2.addWidget(QtWidgets.QLabel("Result Limit:", self))
        layout2.addWidget(self.__limit_spin)
        layout2.addWidget(QtWidgets.QLabel("Proc Hour Cutoff:", self))
        layout2.addWidget(self.__prh_spin)

        layout3 = QtWidgets.QHBoxLayout()
        layout3.addWidget(QtWidgets.QLabel("Show:", self))
        layout3.addWidget(self.__show_combo)
        layout3.addWidget(self.__include_group_btn)
        layout3.addWidget(QtWidgets.QLabel("Require Services", self))
        layout3.addWidget(self.__require_services)
        layout3.addWidget(QtWidgets.QLabel("Exclude Regex", self))
        layout3.addWidget(self.__exclude_regex)

        self.__group.setLayout(layout2)
        self.__groupFilter.setLayout(layout3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__groupFilter)
        layout.addWidget(self.__group)
        layout.addLayout(layout1)

        # pylint: disable=no-member
        self.__job_box.textChanged.connect(self.detect)
        self.__show_combo.currentIndexChanged.connect(self.showChanged)
        # pylint: enable=no-member

    def _cfg(self):
        '''
        Loads (if necessary) and returns the config values.
        Warns and returns an empty dict if there's a problem reading the config

        @return: The keys & values stored in the config file
        @rtype: dict<str:str>
        '''
        if not hasattr(self, '__config'):
            self.__config = cuegui.Utils.getResourceConfig()
        return self.__config

    def showChanged(self, show_index):
        """Load a new show."""
        del show_index
        show = self.__show_combo.currentText()
        self.__current_show = opencue.api.findShow(str(show))
        self.__include_group_btn.showChanged(self.__current_show)

    def detect(self, name=None):
        """Populates initial values when the job name is changed."""
        del name
        try:
            job = opencue.api.findJob(str(self.__job_box.text()))
        except opencue.exception.CueException:
            return

        layers = job.getLayers()
        minCores = 1.0
        minMem = 0
        for layer in layers:
            if layer.data.min_cores > minCores:
                minCores = layer.data.min_cores

            if layer.data.min_memory > minMem:
                minMem = layer.data.min_memory

        self.__cores_spin.setValue(int(minCores))
        self.__mem_spin.setValue(float(minMem / 1048576.0))
        self.__show_combo.setCurrentIndex(self.__show_combo.findText(job.data.show))

    def getJob(self):
        """Gets the current job name."""
        return str(self.__job_box.text())

    def getCores(self):
        """Gets the core count."""
        return int(self.__cores_spin.value())

    def getMaxCores(self):
        """Gets the max core count."""
        return int(self.__max_cores_spin.value())

    def getMemory(self):
        """Gets the memory amount."""
        return int(self.__mem_spin.value() * 1048576.0)

    def getJobBox(self):
        """Gets the job box widget."""
        return self.__job_box

    def getUpdateButton(self):
        """Gets the update button widget."""
        return self.__update_btn

    def getRedirectButton(self):
        """Gets the redirect button widget."""
        return self.__redirect_btn

    def getSelectAllButton(self):
        """Gets the select all button widget."""
        return self.__select_all_btn

    def getClearButton(self):
        """Gets the clear button widget."""
        return self.__clear_btn

    def getShow(self):
        """Gets the current show."""
        return self.__current_show

    def getAllocFilter(self):
        """Gets the allocation filter."""
        return self.__alloc_filter

    def getLimit(self):
        """Gets the limit."""
        return self.__limit_spin.value()

    def getCutoffTime(self):
        """Gets the cutoff time."""
        return int(self.__prh_spin.value() * 3600.0)

    def getRequiredService(self):
        """Gets the required service name."""
        return str(self.__require_services.text()).strip()

    def getJobNameExcludeRegex(self):
        """Gets the regex of job name to exclude."""
        return str(self.__exclude_regex.text()).strip()

    def getIncludedGroups(self):
        """Gets the value of the include groups checkbox."""
        return self.__include_group_btn.getChecked()


class RedirectWidget(QtWidgets.QWidget):
    """
    Displays a table of procs that can be selected for redirect.
    """

    HEADERS = ["Name", "Cores", "Memory", "PrcTime", "Group", "Service",
               "Job Cores", "Pending", "LLU", "Log"]

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.app = cuegui.app()
        self.__hosts = {}

        self.__controls = RedirectControls(self)

        self.__model = QtGui.QStandardItemModel(self)
        self.__model.setColumnCount(7)
        self.__model.setHorizontalHeaderLabels(RedirectWidget.HEADERS)

        self.__proxyModel = ProxyModel(self)
        self.__proxyModel.setSourceModel(self.__model)

        self.__tree = QtWidgets.QTreeView(self)
        self.__tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.__tree.setSortingEnabled(True)
        self.__tree.setModel(self.__proxyModel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__controls)
        layout.addWidget(self.__tree)

        # pylint: disable=no-member
        self.__controls.getUpdateButton().pressed.connect(self.update)
        self.__controls.getRedirectButton().pressed.connect(self.redirect)
        self.__controls.getSelectAllButton().pressed.connect(self.selectAll)
        self.__controls.getClearButton().pressed.connect(self.clearTarget)

        self.__tree.doubleClicked.connect(self.mouseDoubleClickEvent)
        self.__tree.clicked.connect(self.mousePressEvent)
        # pylint: disable=no-member

    @QtCore.Slot("QModelIndex")
    def mousePressEvent(self, item):
        """Called when an item is clicked on. Copies selected object names to
        the middle click selection clip board.
        """
        try:
            QtWidgets.QApplication.clipboard().setText(item.data(), QtGui.QClipboard.Selection)
        except AttributeError as e:
            logger.info("Error item no longer available %s", e)

    @QtCore.Slot("QModelIndex")
    def mouseDoubleClickEvent(self, index):
        """ emit proc to Job Monitor Tree """
        attr = getattr(index, 'data', None)
        if attr is not None:
            try:
                jobObject = opencue.api.getJobs(job=[index.data()])
                if jobObject:
                    if cuegui.Utils.isJob(jobObject[0]):
                        self.app.view_object.emit(jobObject[0])
            except opencue.exception.CueException as e:
                text = ('Not able to add job to Job Monitor Tree. '
                        'Error Message:\n %s' % e)
                self.__warn(text)

    def __getSelectedProcsByAlloc(self, selectedItems):
        """
        Gathers and returns the selected procs, grouped by allocation their
        allocation names

        @param selectedItems: The selected rows to analyze
        @type selectedItems: list<dict<str:varies>>

        @return: A dictionary with the allocation names are the keys and the
                 selected procs are the values.
        @rtype: dict<str:L{opencue.wrappers.proc.Proc}>
        """

        procByAlloc = {}
        for item in selectedItems:
            entry = self.__hosts.get(str(item.text()))
            alloc = entry.get('alloc')
            allocProcs = procByAlloc.get(alloc, [])
            allocProcs.extend(list(entry["procs"]))
            procByAlloc[alloc] = allocProcs
        return procByAlloc

    def __warn(self, msg):
        """
        Displays the given message for the user to acknowledge

        @param msg: The message to display
        @type msg: str
        """

        message = QtWidgets.QMessageBox(self)
        message.setText(msg)
        message.exec_()

    def __isCrossShowSafe(self, procs, targetShow):
        """
        Determines whether or not it's safe to redirect cores from a show
        to another, based on user response to the warning message

        @param procs: The procs to redirect
        @type procs: L{opencue.wrappers.proc.Proc}

        @param targetShow: The name of the target show
        @type targetShow: str

        @return: Whether or not it's safe to redirect the given procs to the
                 target show
        @rtype: bool
        """

        xshowJobs = [proc.getJob() for proc in procs if
                     proc.getJob().show() != targetShow]

        if not xshowJobs:
            return True  # No cross-show procs

        msg = ('Redirecting the selected procs to the target will result '
               'in killing frames on other show/s.\nDo you have approval '
               'from (%s) to redirect cores from the following jobs?'
               % ', '.join([j.show().upper() for j in xshowJobs]))
        return cuegui.Utils.questionBoxYesNo(parent=self,
                                      title="Cross-show Redirect!",
                                      text=msg,
                                      items=[j.name() for j
                                      in xshowJobs])

    def __isBurstSafe(self, alloc, procs, show):
        """
        Determines whether or not it's safe to redirect cores by checking the
        burst target show burst and the number of cores being redirected. If
        there's a number of cores that may not be possible to pick up by the
        target show, that number should be lower than the threshold set in the
        cuegui.yaml `resources` config.

        @param alloc: The name of the allocation for the cores
        @type alloc: str

        @param procs: The procs to be redirected
        @type procs: L{opencue.wrappers.proc.Proc}

        @param show: The name of the target show
        @type show: str

        @return: Whether or not it's safe to kill these cores based on
                 the subscription burst of the target show
        @rtype: bool
        """

        # Skip if this check is disabled in the config
        # pylint: disable=protected-access
        cfg = self.__controls._cfg()
        # pylint: enable=protected-access
        wcThreshold = cfg.get('redirect_wasted_cores_threshold', 100)
        if wcThreshold < 0:
            return True

        showObj = opencue.api.findShow(show)
        stripShowRegex = '\\.%s' % show
        showSubs = dict((re.sub(stripShowRegex, "", s.data.name), s)
                         for s in showObj.getSubscriptions()
                         if s.data.allocation_name in alloc)
        try:
            procsBurst = (showSubs.get(alloc).data.burst -
                              showSubs.get(alloc).data.reserved_cores)
            # pylint: disable=consider-using-generator
            procsRedirect = int(sum([p.data.reserved_cores
                                         for p in procs]))
            wastedCores = int(procsRedirect - procsBurst)
            if wastedCores <= wcThreshold:
                return True  # wasted cores won't exceed threshold

            status = ('at burst' if procsBurst == 0 else
                      '%d cores %s burst'
                      % (abs(procsBurst),
                      'below' if procsBurst > 0 else  'above'))
            msg = ('Target show\'s %s subscription is %s. Redirecting '
                   'the selected procs will kill frames to free up %d '
                   'cores. You will be killing %d cores '
                   'that the target show will not be able to use. '
                   'Do you want to redirect anyway?'
                   % (alloc, status, int(procsRedirect), wastedCores))
            return cuegui.Utils.questionBoxYesNo(parent=self,
                                          title=status.title(),
                                          text=msg)
        except TypeError:
            self.__warn('Cannot direct %s cores to %s because %s the '
                        'target show does not have a %s subscription!'
                        % (alloc, show, show, alloc))
            return False

    @classmethod
    def __isAllowed(cls, procs, targetJob):
        """Checks if the follow criteria are met to allow redirect to target job:
            - if source/target job have pending frames
            - if target job hasn't reached maximum cores
            - check if adding frames will push target job over it's max cores

        @param procs: The (source) procs to be redirected
        @type procs: L{opencue.wrappers.proc.Proc}
        @param targetJob: target job to move procs to
        @return: true/false of whether criteria are met
                 and error message if any
        @rtype: tuple(boolean, string)
        """
        errMsg = ""
        allowed = False

        # Case 1: Check if target job hasn't reached it's max cores
        if targetJob.coresReserved() < targetJob.maxCores():
            allowed = True
            errMsg = "Target job %s cores reserved %s \
                      reached max cores %s " %(targetJob.name(),
                                               targetJob.coresReserved(),
                                               targetJob.maxCores())

        # Case 2: 1. Check target job for pending frames
        #         2. Check source procs for pending frames
        if allowed and targetJob.waitingFrames() <= 0:
            allowed = False
            errMsg = "Target job %s has no pending (waiting) frames" % targetJob.name()

        if allowed:
            for proc in procs:
                job = proc.getJob()
                if job.waitingFrames() <= 0:
                    allowed = False
                    errMsg = "Source job %s has no pending (waiting) frames" % job.name()
                    break

        # Case 3: Check if each proc or summed up procs will
        #         push targetJob over it's max cores
        if allowed:
            totalProcCores = 0
            for proc in procs:
                totalProcCores += proc.coresReserved()
                msg = ('proc cores reserved of %s will push %s '
                         'over it\'s max cores limit of %s')
                if (proc.coresReserved() + targetJob.coresReserved()) > targetJob.maxCores() or \
                        (totalProcCores + targetJob.coresReserved()) > targetJob.maxCores():
                    errMsg = msg % (str(proc.coresReserved() + targetJob.coresReserved()),
                                     targetJob.name(), str(targetJob.maxCores()))
                    allowed = False
                    break

            if totalProcCores > targetJob.maxCores():
                errMsg = msg % (totalProcCores, targetJob.name(),
                                str(targetJob.maxCores()))
                allowed = False

        return allowed, errMsg

    def redirect(self):
        """
        Redirect the selected procs to the target job, after running a few
        checks to verify it's safe to do that.

        @postcondition: The selected procs are redirected to the target job
        """

        # Get selected items
        items = [self.__model.item(row) for row
                 in range(0, self.__model.rowCount())]
        selectedItems = [item for item in items
                         if item.checkState() == QtCore.Qt.Checked]
        if not selectedItems:  # Nothing selected, exit
            self.__warn('You have not selected anything to redirect.')
            return

        # Get the Target Job
        jobName = self.__controls.getJob()
        if not jobName:  # No target job, exit
            self.__warn('You must have a job name selected.')
            return
        job = None
        try:
            job = opencue.api.findJob(jobName)
        except opencue.EntityNotFoundException:  # Target job finished, exit
            text = ('The job you\'re trying to redirect to '
                    'appears to be no longer in the cue!')
            cuegui.Utils.showErrorMessageBox(text, title="ERROR!")

            return

        # Gather Selected Procs
        procByAlloc = self.__getSelectedProcsByAlloc(selectedItems)
        showName = job.show()
        # Check if safe to redirect
        #   1. don't redirect if target job's reserved cores reached job max
        #   2. at burst
        #   3. cross-show safe
        warning = ""
        try:
            for alloc, procs in list(procByAlloc.items()):
                if not self.__isCrossShowSafe(procs, showName):
                    warning = "Is not cross show safe"
                    break
                if not self.__isBurstSafe(alloc, procs, showName):
                    warning = "Is not burst safe"
                    break
                allowed, errMsg = self.__isAllowed(procs, targetJob=job)
                if not allowed:
                    warning = errMsg
                    break
        except opencue.exception.CueException as e:
            warning = str(e)

        if warning:
            warning = "Failed to Redirect:\n" + warning
            self.__warn(warning)
            return

        # Redirect
        errors = []
        for item in selectedItems:
            entry = self.__hosts.get(str(item.text()))
            procs = entry["procs"]
            # pylint: disable=broad-except
            try:
                host = entry["host"]
                host.redirectToJob(procs, job)
            except Exception as e:
                errors.append(str(e))
            item.setIcon(QtGui.QIcon(QtGui.QPixmap(":retry.png")))
            item.setEnabled(False)

        if errors:  # Something went wrong!
            stackTrace = "\n".join(errors)
            text = 'Some procs failed to redirect with errors:\n' + stackTrace
            self.__warn(text)
        else:
            text = 'Redirect To Job Request sent for:\n' + job.name()
            self.__warn(text)

    def selectAll(self):
        """
        Select all items in the results.
        """
        for row in range(0, self.__model.rowCount()):
            item = self.__model.item(row)
            item.setCheckState(QtCore.Qt.Checked)

    def clearTarget(self):
        """
        Clear the target
        """
        self.__controls.getJobBox().clear()

    def update(self):
        """ Update the model """
        self.__model.clear()
        self.__model.setHorizontalHeaderLabels(RedirectWidget.HEADERS)

        hosts = { }
        ok = 0

        serviceFilter = self.__controls.getRequiredService()
        groupFilter = self.__controls.getIncludedGroups()
        jobRegexFilter = self.__controls.getJobNameExcludeRegex()

        show = self.__controls.getShow()
        alloc = self.__controls.getAllocFilter()
        procs = opencue.api.getProcs(show=[str(show.data.name)], alloc=alloc.getSelected())

        progress = QtWidgets.QProgressDialog("Searching","Cancel", 0,
                                         self.__controls.getLimit(), self)
        progress.setWindowModality(QtCore.Qt.WindowModal)

        for proc in procs:
            if progress.wasCanceled():
                break

            # Stick with the target show
            if proc.data.show_name != show.data.name:
                continue

            if proc.data.job_name == str(self.__controls.getJob()):
                continue

            # Skip over already redirected procs
            if proc.data.redirect_target:
                continue

            if ok >= self.__controls.getLimit():
                break

            if jobRegexFilter:
                if re.match(jobRegexFilter, proc.data.job_name):
                    continue

            if serviceFilter:
                if serviceFilter not in proc.data.services:
                    continue

            if groupFilter:
                if proc.data.group_name not in groupFilter:
                    continue

            name = proc.data.name.split("/")[0]
            lluTime = cuegui.Utils.getLLU(proc)
            job = proc.getJob()
            logLines = cuegui.Utils.getLastLine(proc.data.log_path) or ""

            if name not in hosts:
                cue_host = opencue.api.findHost(name)
                hosts[name] = {
                               "host": cue_host,
                               "procs": [],
                               "mem": cue_host.data.idle_memory,
                               "cores": int(cue_host.data.idle_cores),
                               "time": 0,
                               "ok": False,
                               'alloc': cue_host.data.alloc_name}

            host = hosts[name]
            if host["ok"]:
                continue

            host["procs"].append(proc)
            host["mem"] = host["mem"] + proc.data.reserved_memory
            host["cores"] = int(host["cores"]) + int(proc.data.reserved_cores)
            host["time"] = host["time"] + (int(time.time()) - proc.data.dispatch_time)
            host["llu"] = cuegui.Utils.numFormat(lluTime, "t")
            host["log"] = logLines
            host['job_cores'] = job.data.job_stats.reserved_cores
            host['waiting'] = job.pendingFrames() or 0

            if host["cores"] >= self.__controls.getCores() and \
                    host["cores"] <= self.__controls.getMaxCores() and \
                    host["mem"] >= self.__controls.getMemory() and \
                    host["time"] < self.__controls.getCutoffTime():
                self.__addHost(host)
                host["ok"] = True
                ok = ok + 1
                progress.setValue(ok)

        progress.setValue(self.__controls.getLimit())
        # Save this for later on
        self.__hosts = hosts

    def __addHost(self, entry):
        """ Add Host to ProxyModel """
        host = entry["host"]
        procs = entry["procs"]
        rtime = entry["time"]

        checkbox = QtGui.QStandardItem(host.data.name)
        checkbox.setCheckable(True)

        self.__proxyModel.sourceModel().appendRow([checkbox,
                                QtGui.QStandardItem(str(entry["cores"])),
                                QtGui.QStandardItem("%0.2fGB" % (entry["mem"] / 1048576.0)),
                                QtGui.QStandardItem(cuegui.Utils.secondsToHHMMSS(rtime))])

        for proc in procs:
            checkbox.appendRow([QtGui.QStandardItem(proc.data.job_name),
                                QtGui.QStandardItem(str(proc.data.reserved_cores)),
                                QtGui.QStandardItem(
                                    "%0.2fGB" % (proc.data.reserved_memory / 1048576.0)),
                                QtGui.QStandardItem(cuegui.Utils.secondsToHHMMSS(time.time() -
                                                                        proc.data.dispatch_time)),
                                QtGui.QStandardItem(proc.data.group_name),
                                QtGui.QStandardItem(",".join(proc.data.services)),
                                QtGui.QStandardItem(str(entry["job_cores"])),
                                QtGui.QStandardItem(str(entry["waiting"])),
                                QtGui.QStandardItem(str(entry["llu"])),
                                QtGui.QStandardItem(str(entry["log"]))
                                ])

        proxy = self.__tree.model()
        model = proxy.sourceModel()
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            self.__tree.expand(proxy.mapFromSource(index))
            self.__tree.resizeColumnToContents(0)
        self.__tree.setWordWrap(True)


class ProxyModel(QtCore.QSortFilterProxyModel):
    """Provides support for sorting data passed between the model and the tree view"""

    def lessThan(self, left, right):
        """Handle sorting comparison"""
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)

        try:
            return int(leftData) < int(rightData)
        except ValueError:
            if re.search(MEMORY_PATTERN, leftData):
                # strip memory type to compare
                leftDataBtype = re.search(MEMORY_BTYPE, leftData).group()
                leftDataMem = re.sub(MEMORY_BTYPE, "", leftData)
                leftBtyes = cuegui.Utils.byteConversion(float(leftDataMem), leftDataBtype)

                rightDataBtype = re.search(MEMORY_BTYPE, rightData).group()
                rightDataMem = re.sub(MEMORY_BTYPE, "", rightData)
                rightBytes = cuegui.Utils.byteConversion(float(rightDataMem), rightDataBtype)
                return float(leftBtyes) < float(rightBytes)

            return leftData < rightData

        except TypeError:
            return leftData < rightData
