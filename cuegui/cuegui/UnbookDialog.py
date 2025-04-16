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


"""Dialog for unbooking frames."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
from builtins import range
from builtins import object
import re

from qtpy import QtCore
from qtpy import QtWidgets

import opencue

import cuegui.AbstractDialog


class UnbookDialog(cuegui.AbstractDialog.AbstractDialog):
    """Dialog for unbooking frames."""

    def __init__(self, jobs, parent=None):
        cuegui.AbstractDialog.AbstractDialog.__init__(self, parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.setWindowTitle("Unbook matching frames")

        __descriptionLabel = QtWidgets.QLabel(
            "Unbook and optionally kill the matching frames from the following jobs:", self)

        self.__show = opencue.api.findShow(jobs[0].data.name.split("-")[0])
        self.__jobs = [
            job.data.name for job in jobs if job.data.name.startswith(self.__show.data.name)]
        self.__subscriptions = [
            sub.data.name.split(".")[1] for sub in self.__show.getSubscriptions()]

        # Show list of jobs selected
        self.__jobList = QtWidgets.QTextEdit(self)
        self.__jobList.setText("\n".join(self.__jobs))
        self.__jobList.setReadOnly(True)
        self.__jobList.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))

        # matrix of subscribed allocations
        self.__matrix = self._newCheckBoxSelectionMatrix("Allocations",
                                                         self.__subscriptions,
                                                         self.__subscriptions)

        # The number to unbook
        __amountLabel = QtWidgets.QLabel("Amount to unbook:", self)
        self.__amount = QtWidgets.QSpinBox(self)
        self.__amount.setRange(0, 10000)
        self.__amount.setValue(1)

        # checkbox for "Kill unbooked frames"
        __killLabel = QtWidgets.QLabel("Kill unbooked frames?", self)
        self.__kill = QtWidgets.QCheckBox(self)

        # checkbox for "Redirect procs to a group or job?"
        __redirectLabel = QtWidgets.QLabel("Redirect procs to a group or job?", self)
        self.__redirect = QtWidgets.QCheckBox(self)

        self.__buttons = self._newDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        layout.addWidget(__descriptionLabel)
        layout.addWidget(self.__jobList)

        self._addWidgetRow(__amountLabel, self.__amount)
        self._addWidgetRow(__killLabel, self.__kill)
        self._addWidgetRow(__redirectLabel, self.__redirect)

        layout.addWidget(self.__matrix)

        # checkbox and LineEdit for amount or range of memory
        self.__memoryRangeBox = self.__createRangeBox(layout, "Memory requirement", "Mb", 32768)

        # checkbox and LineEdit for amount or range of runtime
        self.__runtimeRangeBox = self.__createRangeBox(
            layout, "Runtime requirement", "Minutes", 10000)

        layout.addWidget(self.__buttons)

    def __createRangeBox(self, layout, name, units, max_frame):
        __group = QtWidgets.QGroupBox(name)
        __group.setCheckable(True)
        __group.setChecked(False)
        __layout = QtWidgets.QGridLayout(__group)

        __moreThan = QtWidgets.QRadioButton("More than")
        __lessThan = QtWidgets.QRadioButton("Less than")
        __range = QtWidgets.QRadioButton("Between")

        __range.setChecked(True)

        __layout.addWidget(__moreThan, 1, 0)
        __layout.addWidget(__lessThan, 1, 1)
        __layout.addWidget(__range, 1, 2)

        __min = QtWidgets.QSpinBox(self)
        __min.setRange(0, max_frame)
        __layout.addWidget(__min, 0, 0)

        __minLabel = QtWidgets.QLabel(units)
        __layout.addWidget(__minLabel, 0, 1)

        __toLabel = QtWidgets.QLabel(" to ")
        __layout.addWidget(__toLabel, 0, 2, QtCore.Qt.AlignHCenter)

        __max = QtWidgets.QSpinBox(self)
        __max.setRange(0, max_frame)
        __layout.addWidget(__max, 0, 3)

        __maxLabel = QtWidgets.QLabel(units)
        __layout.addWidget(__maxLabel, 0, 4)

        # Setting the minimum should disable the right hand side of the range
        # pylint: disable=no-member
        __lessThan.toggled.connect(__min.setDisabled)
        __lessThan.toggled.connect(__toLabel.setDisabled)
        __lessThan.toggled.connect(__minLabel.setDisabled)

        # Setting the maximum should disable the left hand side of the range
        __moreThan.toggled.connect(__max.setDisabled)
        __moreThan.toggled.connect(__toLabel.setDisabled)
        __moreThan.toggled.connect(__maxLabel.setDisabled)
        # pylint: enable=no-member

        layout.addWidget(__group)

        return RangeBox(__group, __moreThan, __lessThan, __range, __min, __max)

    @staticmethod
    def handleIntCriterion(mixed, convert=None):
        """handleIntCriterion
            returns the proper subclass of IntSearchCriterion based on
            input from the user. There are a few formats which are accepted.

            float/int - GreaterThanFloatSearchCriterion
            string -
                gt<value> - GreaterThanFloatSearchCriterion
                lt<value> - LessThanFloatSearchCriterion
                min-max  - InRangeFloatSearchCriterion
        """
        def _convert(val):
            if not convert:
                return int(val)
            return int(convert(float(val)))

        if isinstance(mixed, (float, int)):
            result = opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
                value=_convert(mixed))
        elif isinstance(mixed, str):
            if mixed.startswith("gt"):
                result = opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
                    value=_convert(mixed[2:]))
            elif mixed.startswith("lt"):
                result = opencue.api.criterion_pb2.LessThanIntegerSearchCriterion(
                    value=_convert(mixed[2:]))
            elif mixed.find("-") > -1:
                min_frame, max_frame = mixed.split("-", 1)
                result = opencue.api.criterion_pb2.InRangeIntegerSearchCriterion(
                    min=_convert(min_frame), max=_convert(max_frame))
            else:
                try:
                    result = opencue.api.criterion_pb2.GreaterThanIntegerSearchCriterion(
                        value=_convert(mixed))
                except ValueError:
                    raise Exception("invalid int search input value: " + str(mixed))
        elif issubclass(mixed.__class__, opencue.api.criterion_pb2.EqualsIntegerSearchCriterion):
            result = mixed
        elif not mixed:
            return []
        else:
            raise Exception("invalid float search input value: " + str(mixed))

        return [result]

    def accept(self):
        """Accept Unbook action"""
        if not self.__jobs:
            self.close()

        procSearch = opencue.search.ProcSearch()
        procSearch.options['maxResults'] = [int(self.__amount.value())]
        procSearch.options['jobs'] = self.__jobs
        procSearch.options['allocs'] = [
            str(checkedBox.text()) for checkedBox in self.__matrix.checkedBoxes()]
        memoryRange = self.__memoryRangeBox.result()
        if memoryRange:
            procSearch.options['memoryRange'] = self.handleIntCriterion(
                memoryRange, lambda mb: (mb*1024))
        runtimeRange = self.__runtimeRangeBox.result()
        if runtimeRange:
            procSearch.options['durationRange'] = self.handleIntCriterion(
                runtimeRange, lambda rangeMin: (rangeMin*60))

        if self.__redirect.isChecked():
            # Select the show to redirect to
            title = "Select show"
            body = "Redirect to what show?"
            shows = {show.data.name: show for show in opencue.api.getActiveShows()}
            items = [self.__jobs[0].split("-")[0]] + sorted(shows.keys())
            (show, choice) = QtWidgets.QInputDialog.getItem(
                self, title, body, items, 0, False)
            if not choice:
                return
            show = shows[str(show)]

            # Decide between redirecting to a job or a group
            title = "Select Redirection Type"
            body = "Redirect to a job or a group?"
            items = ["Job", "Group"]
            (redirectTo, choice) = QtWidgets.QInputDialog.getItem(
                self, title, body, items, 0, False)
            if not choice:
                return

            job = group = None
            if redirectTo == "Job":
                jobs = {job.data.name: job for job in opencue.api.getJobs(show=[show.data.name])}
                dialog = SelectItemsWithSearchDialog(
                    self,
                    "Redirect to which job?",
                    list(jobs.keys()),
                    QtWidgets.QAbstractItemView.SingleSelection)
                dialog.exec_()
                selected = dialog.selected()
                if selected:
                    job = jobs[selected[0]]
                else:
                    return

            elif redirectTo == "Group":
                title = "Select Redirection Group"
                body = "Redirect to which group?"
                groups = {group.data.name: group for group in show.getGroups()}
                (group, choice) = QtWidgets.QInputDialog.getItem(
                    self, title, body, sorted(groups.keys()), 0, False)
                if not choice:
                    return
                group = groups[str(group)]

            if job or group:
                procs = opencue.api.getProcs(**procSearch.options)
                kill = self.__kill.isChecked()
                amount = 0

                for proc in procs:
                    try:
                        if job:
                            proc.redirectToJob(job, kill)
                        elif group:
                            proc.redirectToGroup(group, kill)
                        amount += 1
                    except opencue.exception.CueException:
                        pass
                self.__informationBox("Redirected procs",
                                      "Number of redirected procs: %d" % amount)
                self.close()
        else:
            # Not redirecting
            if self.__kill.isChecked():
                dialog = KillConfirmationDialog(procSearch, self.parent())
                dialog.exec_()
                if dialog.result():
                    self.close()
            else:
                procs = opencue.api.getProcs(**procSearch.options)
                amount = 0
                for proc in procs:
                    try:
                        proc.unbook()
                        amount += 1
                    except opencue.exception.CueException:
                        pass
                self.__informationBox("Unbooked frames",
                                      "Number of frames unbooked: %d" % amount)
                self.close()

    def __informationBox(self, title, message):
        QtWidgets.QMessageBox.information(self.parent(),
                                          title,
                                          message,
                                          QtWidgets.QMessageBox.Ok)


class SelectItemsWithSearchDialog(cuegui.AbstractDialog.AbstractDialog):
    """Dialog for selecting items via search."""

    def __init__(self, parent, header, items,
                 selectionMode=QtWidgets.QAbstractItemView.MultiSelection):
        cuegui.AbstractDialog.AbstractDialog.__init__(self, parent)

        QtWidgets.QVBoxLayout(self)

        self.__items = items

        self.__widget = SelectItemsWithSearchWidget(self,
                                                    header,
                                                    self.__items,
                                                    selectionMode)
        self.layout().addWidget(self.__widget)

        self.__buttons = self._newDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.layout().addWidget(self.__buttons)

    def selected(self):
        """Gets whether the item is selected."""
        if self.result():
            return self.__widget.selected()
        return None


class SelectItemsWithSearchWidget(QtWidgets.QWidget):
    """Widget for selecting items via search."""

    def __init__(
            self, parent, header, items, selectionMode=QtWidgets.QAbstractItemView.MultiSelection):
        QtWidgets.QWidget.__init__(self, parent)

        QtWidgets.QGridLayout(self)

        self.__items = items

        self.__label = QtWidgets.QLabel(header, self)
        self.layout().addWidget(self.__label, 0, 0, 1, 1)

        self.__filter = QtWidgets.QLineEdit("", self)
        self.layout().addWidget(self.__filter, 2, 0)

        self.__filter.textChanged.connect(self.filterJobs)  # pylint: disable=no-member

        self.__list = QtWidgets.QListWidget(self)
        self.__list.setSelectionMode(selectionMode)
        self.layout().addWidget(self.__list, 3, 0)

        self.filterJobs(None)

    def filterJobs(self, text):
        """Filter the list of jobs by text match."""
        self.__list.clear()
        items = [
            item for item in self.__items if not text or re.search(str(text), item, re.IGNORECASE)]
        self.__list.addItems(items)

    def selected(self):
        """Gets whether the item is selected."""
        selected = []
        for num in range(self.__list.count()):
            if self.__list.item(num).isSelected():
                selected.append(str(self.__list.item(num).text()))
        return selected


class RangeBox(object):
    """Stores the parts the make up the range box and provides a way to query
    for the result"""
    def __init__(self, group, moreThan, lessThan, rangeButton, minBox, maxBox):
        self.__group = group
        self.__moreThan = moreThan
        self.__lessThan = lessThan
        self.__range = rangeButton
        self.__min = minBox
        self.__max = maxBox

    def result(self):
        """Gets the formatted string result."""
        if self.__group.isChecked():
            if self.__moreThan.isChecked():
                return "gt%d" % self.__min.value()
            if self.__lessThan.isChecked():
                return "lt%d" % self.__max.value()
            if self.__range.isChecked():
                return "%d-%d" % (self.__min.value(), self.__max.value())
        return ""


class KillConfirmationDialog(QtWidgets.QDialog):
    """Dialog for confirming frames should be killed."""

    def __init__(self, procSearch, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        layout = QtWidgets.QVBoxLayout(self)

        self.setModal(True)
        self.setFixedWidth(500)
        self.setWindowTitle("Unbook and kill frames?")

        # pylint: disable=unused-private-member
        self.__procSearch = procSearch
        self.__procs = opencue.api.getProcs(**procSearch.options)
        self.__amount = len(self.__procs)

        if self.__amount == 1:
            msg = "Unbook and kill this %d matching frame?"
        else:
            msg = "Unbook and kill these %d matching frames?"
        __descriptionLabel = QtWidgets.QLabel(msg % self.__amount, self)

        # Show list of jobs selected
        self.__jobList = QtWidgets.QTextEdit(self)
        self.__jobList.setText(
            "\n".join(
                ["%s %s" % (proc.data.job_name, proc.data.frame_name) for proc in self.__procs]))
        self.__jobList.setReadOnly(True)
        self.__jobList.setSizePolicy(
            QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum))

        self.__buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal,
            self)

        layout.addWidget(__descriptionLabel)
        layout.addWidget(self.__jobList)
        layout.addWidget(self.__buttons)

        # pylint: disable=no-member
        self.__buttons.accepted.connect(self.accept)
        self.__buttons.rejected.connect(self.reject)
        # pylint: enable=no-member

    def accept(self):
        """Kills the procs."""
        for proc in self.__procs:
            try:
                proc.kill()
            except opencue.exception.CueException:
                pass

        if self.__amount == 1:
            msg = "%d frame has been unbooked and killed."
        else:
            msg = "%d frames have been unbooked and killed."
        QtWidgets.QMessageBox.information(self.parent(),
                                          "Unbooked and killed frames",
                                          msg % self.__amount,
                                          QtWidgets.QMessageBox.Ok)

        self.done(QtWidgets.QDialog.Accepted)
