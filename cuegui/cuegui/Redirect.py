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
An interface for redirecting resources from one
job to another job.
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division


from past.builtins import cmp
from builtins import str
from builtins import range
import os
import re
import time

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import opencue

from . import Utils


# The concept here is that there is a target job that needs
# procs.  The user would choose the job.  The highest core/memory
# value would be dected and would populate 2 text boxes for cores
# and memory. The user could then adjust these and hit search.
#
# The search will find all hosts that have frames running that can be
# redirected to the target job.

class ShowCombo(QtWidgets.QComboBox):
    """
    A combo box for show selection
    """
    def __init__(self, selected="pipe", parent=None):
        QtWidgets.QComboBox.__init__(self, parent)
        self.refresh()
        self.setCurrentIndex(self.findText(selected))

    def refresh(self):
        self.clear()
        shows = opencue.api.getActiveShows()
        shows.sort(lambda x,y: cmp(x.data.name, y.data.name))

        for show in shows:
            self.addItem(show.data.name, show)

    def getShow(self):
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
        self.__menu.triggered.connect(self.__afterClicked)

    def refresh(self):
        """
        Refresh the full list of allocations.
        """
        allocs = opencue.api.getAllocations()
        allocs.sort(lambda x,y: cmp(x.data.name, y.data.name))

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

        self.__menu.aboutToShow.connect(self.__populate_menu)

    def __loadShow(self, show):
        self.__actions = { }
        try:
            if show:
                return show
        except:
            return opencue.api.findShow(show.name())

    def showChanged(self, show):
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

        self.__mem_spin = QtWidgets.QDoubleSpinBox(self)
        self.__mem_spin.setRange(1, self._cfg().get('max_memory', 200))
        self.__mem_spin.setDecimals(1)
        self.__mem_spin.setValue(4)
        self.__mem_spin.setSuffix("GB")

        self.__limit_spin = QtWidgets.QSpinBox(self)
        self.__limit_spin.setRange(1, 100)
        self.__limit_spin.setValue(10)

        self.__prh_spin = QtWidgets.QDoubleSpinBox(self)
        self.__prh_spin.setRange(1, self._cfg().get('max_proc_hour_cutoff', 30))
        self.__prh_spin.setDecimals(1)
        self.__prh_spin.setValue(10)
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
        self.__group_filter = QtWidgets.QGroupBox("Job Filters")

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
        self.__group_filter.setLayout(layout3)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__group_filter)
        layout.addWidget(self.__group)
        layout.addLayout(layout1)

        self.__job_box.textChanged.connect(self.detect)
        self.__show_combo.currentIndexChanged.connect(self.showChanged)

    def _cfg(self):
        '''
        Loads (if necessary) and returns the config values.
        Warns and returns an empty dict if there's a problem reading the config

        @return: The keys & values stored in the config file
        @rtype: dict<str:str>
        '''
        if not hasattr(self, '__config'):
            self.__config = Utils.getResourceConfig()
        return self.__config

    def showChanged(self, show):
        self.__current_show = opencue.api.findShow(str(show))
        self.__include_group_btn.showChanged(self.__current_show)

    def detect(self, name=None):
        try:
            job = opencue.api.findJob(str(self.__job_box.text()))
        except:
            return

        layers = job.getLayers()
        minCores = 1.0
        minMem = 0
        for layer in layers:
            if layer.data.minCores > minCores:
                minCores = layer.data.minCores

            if layer.data.minMemory > minMem:
                minMem = layer.data.minMemory

        self.__cores_spin.setValue(int(minCores))
        self.__mem_spin.setValue(float(minMem / 1048576.0))
        self.__show_combo.setCurrentIndex(self.__show_combo.findText(job.data.show))

    def getJob(self):
        return str(self.__job_box.text())

    def getCores(self):
        return int(self.__cores_spin.value())

    def getMemory(self):
        return int(self.__mem_spin.value() * 1048576.0)

    def getJobBox(self):
        return self.__job_box

    def getUpdateButton(self):
        return self.__update_btn

    def getRedirectButton(self):
        return self.__redirect_btn

    def getSelectAllButton(self):
        return self.__select_all_btn

    def getClearButton(self):
        return self.__clear_btn

    def getShow(self):
        return self.__current_show

    def getAllocFilter(self):
        return self.__alloc_filter

    def getLimit(self):
        return self.__limit_spin.value()

    def getCutoffTime(self):
        return int(self.__prh_spin.value() * 3600.0)

    def getRequiredService(self):
        return str(self.__require_services.text()).strip()

    def getJobNameExcludeRegex(self):
        return str(self.__exclude_regex.text()).strip()

    def getIncludedGroups(self):
        return self.__include_group_btn.getChecked()


class RedirectWidget(QtWidgets.QWidget):
    """
    Displays a table of procs that can be selected for redirect.
    """

    HEADERS = ["Name","Cores","Memory","PrcTime", "Group","Service"]

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.__hosts = { }

        self.__controls = RedirectControls(self)

        self.__model = QtGui.QStandardItemModel(self)
        self.__model.setColumnCount(5)
        self.__model.setHorizontalHeaderLabels(RedirectWidget.HEADERS)

        self.__tree = QtWidgets.QTreeView(self)
        self.__tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.__tree.setModel(self.__model)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__controls)
        layout.addWidget(self.__tree)

        self.__controls.getUpdateButton().pressed.connect(self.update)
        self.__controls.getRedirectButton().pressed.connect(self.redirect)
        self.__controls.getSelectAllButton().pressed.connect(self.selectAll)
        self.__controls.getClearButton().pressed.connect(self.clearTarget)

    def __get_selected_procs_by_alloc(self, selected_items):
        '''
        Gathers and returns the selected procs, grouped by allocation their
        allocation names

        @param selected_items: The selected rows to analyze
        @type selected_itmes: list<dict<str:varies>>

        @return: A dictionary with the allocation neames are the keys and the
                 selected procs are the values.
        @rtype: dict<str:L{opencue.wrappers.proc.Proc}>
        '''

        procs_by_alloc = {}
        for item in selected_items:
            entry = self.__hosts.get(str(item.text()))
            alloc = entry.get('alloc')
            alloc_procs = procs_by_alloc.get(alloc, [])
            alloc_procs.extend([proc for proc in entry["procs"]])
            procs_by_alloc[alloc] = alloc_procs
        return procs_by_alloc

    def __warn(self, msg):
        '''
        Displays the given message for the user to acknowledge

        @param msg: The message to display
        @type msg: str
        '''

        message = QtWidgets.QMessageBox(self)
        message.setText(msg)
        message.exec_()

    def __is_cross_show_safe(self, procs, target_show):
        '''
        Determines whether or not it's safe to redirect cores from a show
        to another, based on user response to the warning message

        @param procs: The procs to redirect
        @type procs: L{opencue.wrappers.proc.Proc}

        @param target_show: The name of the target show
        @type target_show: str

        @return: Whether or not it's safe to redirect the given procs to the
                 target show
        @rtype: bool
        '''

        xshow_jobs = [proc.getJob() for proc in procs if not
                      proc.getJob().show() == target_show]
        if not xshow_jobs:
            return True  # No cross-show procs

        msg = ('Redirecting the selected procs to the target will result '
               'in killing frames on other show/s.\nDo you have approval '
               'from (%s) to redirect cores from the following jobs?'
               % ', '.join([j.show().upper() for j in xshow_jobs]))
        return Utils.questionBoxYesNo(parent=self,
                                      title="Cross-show Redirect!",
                                      text=msg,
                                      items=[j.name() for j
                                      in xshow_jobs])

    def __is_burst_safe(self, alloc, procs, show):
        '''
        Determines whether or not it's safe to redirect cores by checking the
        burst target show burst and the number of cores being redirected. If
        there's a number of cores that may not be possible to pick up by the
        target show, that number should be lower than the threshold set in the
        cue_resources config.

        @param alloc: The name of the allocation for the cores
        @type alloc: str

        @param procs: The procs to be redirected
        @type procs: L{opencue.wrappers.proc.Proc}

        @param show: The name of the target show
        @type show: str

        @return: Whether or not it's safe to kill these cores based on
                 the subscription burst of the target show
        @rtype: bool
        '''

        # Skip if this check is disabled in the config
        cfg = self.__controls._cfg()
        wc_ok = cfg.get('wasted_cores_threshold', 100)
        if wc_ok < 0:
            return True

        show_obj = opencue.api.findShow(show)
        show_subs = dict((s.data.name.rstrip('.%s' % show), s)
                         for s in show_obj.getSubscriptions()
                         if s.data.allocationName in alloc)
        try:
            procs_to_burst = (show_subs.get(alloc).data.burst -
                              show_subs.get(alloc).data.reservedCores)
            procs_to_redirect = int(sum([p.data.reservedCores
                                         for p in procs]))
            wasted_cores = int(procs_to_redirect - procs_to_burst)
            if wasted_cores <= wc_ok:
                return True  # wasted cores won't exceed threshold

            status = ('at burst' if procs_to_burst == 0 else
                      '%d cores %s burst'
                      % (procs_to_burst,
                      'below' if procs_to_burst > 0 else  'above'))
            msg = ('Target show\'s %s subscription is %s. Redirecting '
                   'the selected procs will kill frames to free up %d '
                   'cores. You will be killing %d cores '
                   'that the target show will not be able to use. '
                   'Do you want to redirect anyway?'
                   % (alloc, status, int(procs_to_redirect), wasted_cores))
            return Utils.questionBoxYesNo(parent=self,
                                          title=status.title(),
                                          text=msg)
        except TypeError:
            self.__warn('Cannot direct %s cores to %s because %s the '
                        'target show does not have a %s subscription!'
                        % (alloc, show, show, alloc))
            return False

    def redirect(self):
        '''
        Redirect the selected procs to the target job, after running a few
        checks to verify it's safe to do that.

        @postcondition: The selected procs are redirected to the target job
        '''

        # Get selected items
        items = [self.__model.item(row) for row
                 in range(0, self.__model.rowCount())]
        selected_items = [item for item in items
                         if item.checkState() == QtCore.Qt.Checked]
        if not selected_items:  # Nothing selected, exit
            self.__warn('You have not selected anything to redirect.')
            return

        # Get the Target Job
        job_name = self.__controls.getJob()
        if not job_name:  # No target job, exit
            self.__warn('You must have a job name selected.')
            return
        job = None
        try:
            job = opencue.api.findJob(job_name)
        except opencue.EntityNotFoundException:  # Target job finished, exit
            self.__warn_and_stop('The job you\'re trying to redirect to '
                                 'appears to be no longer in the cue!')
            return

        # Gather Selected Procs
        procs_by_alloc = self.__get_selected_procs_by_alloc(selected_items)
        show_name = job.show()
        for alloc, procs in list(procs_by_alloc.items()):
            if not self.__is_cross_show_safe(procs, show_name):  # Cross-show
                return
            if not self.__is_burst_safe(alloc, procs, show_name):  # At burst
                return

        # Redirect
        errors = []
        for item in selected_items:
            entry = self.__hosts.get(str(item.text()))
            procs = entry["procs"]
            try:
                host = entry["host"]
                host.redirectToJob(procs, job)
            except Exception as e:
                errors.append(str(e))
            item.setIcon(QtGui.QIcon(QtGui.QPixmap(":retry.png")))
            item.setEnabled(False)

        if errors:  # Something went wrong!
            self.__warn('Some procs failed to redirect.')

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
        self.__model.clear()
        self.__model.setHorizontalHeaderLabels(RedirectWidget.HEADERS)

        hosts = { }
        ok = 0

        service_filter = self.__controls.getRequiredService()
        group_filter = self.__controls.getIncludedGroups()
        job_regex = self.__controls.getJobNameExcludeRegex()

        show = self.__controls.getShow()
        alloc = self.__controls.getAllocFilter()
        procs = opencue.api.getProcs(show=show.data.name, alloc=alloc.getSelected())

        progress = QtWidgets.QProgressDialog("Searching","Cancel", 0,
                                         self.__controls.getLimit(), self)
        progress.setWindowModality(QtCore.Qt.WindowModal)

        for num, proc in enumerate(procs):
            if progress.wasCanceled():
                break

            # Stick with the target show
            if proc.data.showName != show.data.name:
                continue

            if proc.data.jobName == str(self.__controls.getJob()):
                continue

            # Skip over already redirected procs
            if proc.data.redirectTarget:
                continue

            if ok >= self.__controls.getLimit():
                break

            if job_regex:
                if re.match(job_regex, proc.data.jobName):
                    continue

            if service_filter:
                if service_filter not in proc.data.services:
                    continue

            if group_filter:
                if proc.data.groupName not in group_filter:
                    continue

            name = proc.data.name.split("/")[0]
            if name not in hosts:
                cue_host = opencue.api.findHost(name)
                hosts[name] = {
                               "host": cue_host,
                               "procs":[],
                               "mem": cue_host.data.idleMemory,
                               "cores": int(cue_host.data.idleCores),
                               "time": 0,
                               "ok": False,
                               'alloc': cue_host.data.allocName}

            host = hosts[name]
            if host["ok"]:
                continue

            host["procs"].append(proc)
            host["mem"] = host["mem"] + proc.data.reservedMemory
            host["cores"] = host["cores"] + proc.data.reservedCores
            host["time"] = host["time"] + (int(time.time()) - proc.data.dispatchTime);

            if host["cores"] >= self.__controls.getCores() and \
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
        host = entry["host"]
        procs = entry["procs"]
        rtime = entry["time"]

        checkbox = QtGui.QStandardItem(host.data.name)
        checkbox.setCheckable(True)

        self.__model.appendRow([checkbox,
                               QtGui.QStandardItem(str(entry["cores"])),
                               QtGui.QStandardItem("%0.2fGB" % (entry["mem"] / 1048576.0)),
                               QtGui.QStandardItem(Utils.secondsToHHMMSS(rtime))])

        for proc in procs:
            checkbox.appendRow([QtGui.QStandardItem(proc.data.jobName),
                                QtGui.QStandardItem(str(proc.data.reservedCores)),
                                QtGui.QStandardItem("%0.2fGB" % (proc.data.reservedMemory / 1048576.0)),
                                QtGui.QStandardItem(Utils.secondsToHHMMSS(time.time() -
                                                                          proc.data.dispatchTime)),
                                QtGui.QStandardItem(proc.data.groupName),
                                QtGui.QStandardItem(",".join(proc.data.services))])

        self.__tree.setExpanded(self.__model.indexFromItem(checkbox), True)
        self.__tree.resizeColumnToContents(0)
