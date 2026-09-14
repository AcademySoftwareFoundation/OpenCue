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


"""Dialogs for creating and inspecting limits."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import time

from qtpy import QtCore
from qtpy import QtWidgets

from opencue_proto import limit_pb2

import opencue
import opencue.exception

import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)

BIND_SOURCE_NAMES = {limit_pb2.SPEC: 'spec', limit_pb2.AUTO: 'auto', limit_pb2.MANUAL: 'manual'}


def _relativeAge(epochSeconds):
    """Formats an epoch timestamp as a short relative age, '--' when unset."""
    if not epochSeconds:
        return '--'
    seconds = max(0, int(time.time()) - int(epochSeconds))
    if seconds < 120:
        return '%ds ago' % seconds
    if seconds < 7200:
        return '%dm ago' % (seconds // 60)
    if seconds < 172800:
        return '%dh ago' % (seconds // 3600)
    return '%dd ago' % (seconds // 86400)


class CreateLimitDialog(QtWidgets.QDialog):
    """Dialog for creating a limit with its full configuration."""

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.setWindowTitle("Add Limit")
        self.setMinimumWidth(480)
        self.__userTouchedMode = False

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        self.__name = QtWidgets.QLineEdit(self)
        form.addRow("Name:", self.__name)

        self.__typeFrame = QtWidgets.QRadioButton("Per frame", self)
        self.__typeFrame.setChecked(True)
        self.__typeFrame.setToolTip("Each running frame uses one license.")
        self.__typeHost = QtWidgets.QRadioButton("Per host", self)
        self.__typeHost.setToolTip(
            "All frames on the same machine share one license. Use for Houdini,\n"
            "Katana and other per-machine licenses. The maximum then means how\n"
            "many machines the farm may spread across.")
        # Sibling radio buttons are all mutually exclusive by default; group each
        # pair explicitly so Type and Mode toggle independently.
        typeGroup = QtWidgets.QButtonGroup(self)
        typeGroup.addButton(self.__typeFrame)
        typeGroup.addButton(self.__typeHost)
        typeBox = QtWidgets.QVBoxLayout()
        typeBox.addWidget(self.__typeFrame)
        typeBox.addWidget(self.__typeHost)
        form.addRow("Type:", typeBox)

        self.__maxValue = QtWidgets.QSpinBox(self)
        self.__maxValue.setRange(1, 999999999)
        self.__maxValue.setValue(1)
        form.addRow("Maximum:", self.__maxValue)

        self.__softValue = QtWidgets.QSpinBox(self)
        self.__softValue.setRange(0, 999999999)
        self.__softValue.setEnabled(False)
        form.addRow("Only pack onto machines\nalready licensed above:", self.__softValue)
        self.__softLabel = form.labelForField(self.__softValue)

        self.__modeEnforced = QtWidgets.QRadioButton("Enforced", self)
        self.__modeEnforced.setChecked(True)
        self.__modeAdvisory = QtWidgets.QRadioButton("Advisory", self)
        self.__modeAdvisory.setToolTip(
            "Advisory never holds a frame back. The license server enforces, and\n"
            "Cue still packs work onto machines that already hold a license.")
        modeGroup = QtWidgets.QButtonGroup(self)
        modeGroup.addButton(self.__modeEnforced)
        modeGroup.addButton(self.__modeAdvisory)
        modeBox = QtWidgets.QVBoxLayout()
        modeBox.addWidget(self.__modeEnforced)
        modeBox.addWidget(self.__modeAdvisory)
        form.addRow("Mode:", modeBox)

        ttlBox = QtWidgets.QHBoxLayout()
        self.__reportTtl = QtWidgets.QSpinBox(self)
        self.__reportTtl.setRange(1, 999999)
        self.__reportTtl.setValue(15)
        self.__reportTtl.setSuffix(" minutes")
        self.__noReporter = QtWidgets.QCheckBox("no external reporter", self)
        ttlBox.addWidget(self.__reportTtl)
        ttlBox.addWidget(self.__noReporter)
        form.addRow("Report timeout:", ttlBox)

        layout.addLayout(form)

        ruleGroup = QtWidgets.QGroupBox(
            "When a frame fails because this license was unavailable", self)
        ruleForm = QtWidgets.QFormLayout(ruleGroup)

        self.__exitStatus = QtWidgets.QSpinBox(self)
        self.__exitStatus.setRange(0, 999999)
        self.__exitStatus.setSpecialValueText("no rule")
        self.__exitStatus.setValue(0)
        self.__exitStatus.setToolTip(
            "The frame exit status that means this license was unavailable, as\n"
            "emitted by RQD via runner.log_exit_status_rules (330 by convention).\n"
            "Statuses 0 and 1 cannot be claimed: 0 is success and 1 is the\n"
            "generic failure code, so either would match nearly every frame.")
        ruleForm.addRow("Error code:", self.__exitStatus)

        self.__delayMinutes = QtWidgets.QSpinBox(self)
        self.__delayMinutes.setRange(0, 999999)
        self.__delayMinutes.setValue(2)
        self.__delayMinutes.setSuffix(" minutes")
        self.__delayMinutes.setSpecialValueText("don't postpone")
        ruleForm.addRow("Postpone the layer for:", self.__delayMinutes)

        self.__autoTag = QtWidgets.QCheckBox(
            "Automatically add this limit to layers that fail with this code", self)
        self.__autoTag.setChecked(True)
        self.__autoTag.setToolTip(
            "Layers rarely declare the licenses they need. This lets Cue learn "
            "from failures.")
        ruleForm.addRow(self.__autoTag)

        self.__ruleHint = QtWidgets.QLabel("", self)
        self.__ruleHint.setWordWrap(True)
        ruleForm.addRow(self.__ruleHint)

        layout.addWidget(ruleGroup)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        layout.addWidget(buttons)

        # pylint: disable=no-member
        buttons.accepted.connect(self.__accept)
        buttons.rejected.connect(self.reject)
        self.__typeHost.toggled.connect(self.__typeChanged)
        self.__noReporter.toggled.connect(self.__reportTtl.setDisabled)
        self.__exitStatus.valueChanged.connect(self.__exitStatusChanged)
        self.__modeEnforced.clicked.connect(self.__modeTouched)
        self.__modeAdvisory.clicked.connect(self.__modeTouched)
        # pylint: enable=no-member

        self.__typeChanged(self.__typeHost.isChecked())

    def __typeChanged(self, isHost):
        """Packing counts machines, so the soft threshold only applies to per-host limits."""
        self.__softValue.setEnabled(isHost)
        if self.__softLabel:
            self.__softLabel.setEnabled(isHost)
        if isHost:
            self.__softValue.setSpecialValueText("same as maximum")
            self.__softValue.setToolTip(
                "Above this many machines, only machines already holding a license\n"
                "may take the work: the farm packs instead of spreading.")
        else:
            self.__softValue.setSpecialValueText("per-host limits only")
            self.__softValue.setValue(0)
            self.__softValue.setToolTip(
                "Packing is a per-machine idea: it only means something once frames on\n"
                "the same machine share a license. Pick \"Per host\" to set a threshold.")

    def __modeTouched(self):
        self.__userTouchedMode = True

    def __exitStatusChanged(self, value):
        if value == 1:
            self.__ruleHint.setText(
                "Status 1 is the generic failure code and cannot name a license "
                "shortage; pick the specific status your RQD emits (330 by "
                "convention).")
        else:
            self.__ruleHint.setText("")
        # An error code plus enforcement plus an empty tag set is the combination that stalls a
        # farm; discovery should start advisory. Only a default, never overriding a user's pick.
        if value > 1 and not self.__userTouchedMode:
            self.__modeAdvisory.setChecked(True)

    def __accept(self):
        name = str(self.__name.text()).strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Add Limit", "Enter a name for the limit.")
            return
        try:
            opencue.api.findLimit(name)
            QtWidgets.QMessageBox.warning(
                self, "Add Limit", "A limit named %s already exists." % name)
            return
        except opencue.exception.CueException:
            pass

        exitStatus = self.__exitStatus.value()
        if exitStatus == 1:
            QtWidgets.QMessageBox.warning(
                self, "Add Limit",
                "Error code 1 is the generic failure code and would tag nearly every "
                "failing layer on the farm. Pick the specific license-shortage status "
                "your RQD emits, or clear the rule.")
            return

        limitType = limit_pb2.HOST if self.__typeHost.isChecked() else limit_pb2.FRAME
        enforcement = (limit_pb2.ADVISORY if self.__modeAdvisory.isChecked()
                       else limit_pb2.ENFORCED)
        softValue = -1
        if self.__typeHost.isChecked() and self.__softValue.value() > 0:
            softValue = self.__softValue.value()

        try:
            limit = opencue.api.createLimit(
                name, self.__maxValue.value(), limitType=limitType, enforcement=enforcement,
                softValue=softValue, exitStatus=exitStatus if exitStatus > 1 else 0,
                delayMinutes=self.__delayMinutes.value(), autoTag=self.__autoTag.isChecked())
        except opencue.exception.CueException as e:
            QtWidgets.QMessageBox.critical(
                self, "Add Limit", "Creating limit %s failed:\n%s" % (name, e))
            return

        reportTtl = 0 if self.__noReporter.isChecked() else self.__reportTtl.value() * 60
        if reportTtl != 900:
            try:
                limit.setReportTtl(reportTtl)
            except opencue.exception.CueException as e:
                # The limit exists at this point; do not report the creation as failed.
                QtWidgets.QMessageBox.warning(
                    self, "Add Limit",
                    "Limit %s was created, but setting its report TTL failed:\n%s\n\n"
                    "It keeps the default 900-second TTL; adjust it from the limit's "
                    "properties." % (name, e))
        self.accept()


class SetFailureRuleDialog(QtWidgets.QDialog):
    """Dialog for editing an existing limit's failure rule."""

    def __init__(self, limit, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.__limit = limit
        self.setWindowTitle("Set Failure Rule: %s" % limit.name())
        form = QtWidgets.QFormLayout(self)

        self.__exitStatus = QtWidgets.QSpinBox(self)
        self.__exitStatus.setRange(0, 999999)
        self.__exitStatus.setSpecialValueText("no rule")
        self.__exitStatus.setValue(limit.exitStatus())
        form.addRow("Error code:", self.__exitStatus)

        self.__delayMinutes = QtWidgets.QSpinBox(self)
        self.__delayMinutes.setRange(0, 999999)
        self.__delayMinutes.setSuffix(" minutes")
        self.__delayMinutes.setSpecialValueText("don't postpone")
        self.__delayMinutes.setValue(limit.delayMinutes())
        form.addRow("Postpone the layer for:", self.__delayMinutes)

        self.__autoTag = QtWidgets.QCheckBox(
            "Automatically add this limit to layers that fail with this code", self)
        self.__autoTag.setChecked(limit.autoTag())
        form.addRow(self.__autoTag)

        note = QtWidgets.QLabel(
            "Clearing the rule (error code \"no rule\") leaves already auto-tagged "
            "layers in place; use \"Remove Auto-Tagged Layers\" to undo those.", self)
        note.setWordWrap(True)
        form.addRow(note)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, parent=self)
        form.addRow(buttons)
        # pylint: disable=no-member
        buttons.accepted.connect(self.__accept)
        buttons.rejected.connect(self.reject)
        # pylint: enable=no-member

    def __accept(self):
        exitStatus = self.__exitStatus.value()
        if exitStatus == 1:
            QtWidgets.QMessageBox.warning(
                self, self.windowTitle(),
                "Error code 1 is the generic failure code and cannot be claimed.")
            return
        try:
            self.__limit.setFailureRule(exitStatus, self.__delayMinutes.value(),
                                        self.__autoTag.isChecked())
        except opencue.exception.CueException as e:
            QtWidgets.QMessageBox.critical(
                self, self.windowTitle(), "Setting the failure rule failed:\n%s" % e)
            return
        self.accept()


class LimitHoldsDialog(QtWidgets.QDialog):
    """Shows which hosts currently hold a limit's licenses."""

    HOLD_SOURCE_NAMES = {limit_pb2.CUE: 'Cue', limit_pb2.EXTERNAL: 'External',
                         limit_pb2.BOTH: 'Cue + External'}

    def __init__(self, limit, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.app = cuegui.app()
        self.__limit = limit
        self.setWindowTitle("License Holders: %s" % limit.name())
        self.resize(640, 480)

        layout = QtWidgets.QVBoxLayout(self)

        topBar = QtWidgets.QHBoxLayout()
        self.__filter = QtWidgets.QLineEdit(self)
        self.__filter.setPlaceholderText("Filter by hostname")
        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        topBar.addWidget(self.__filter)
        topBar.addWidget(self.__btnRefresh)
        layout.addLayout(topBar)

        self.__table = QtWidgets.QTreeWidget(self)
        self.__table.setHeaderLabels(["Host", "Tokens", "Source", "User", "Reported"])
        self.__table.setRootIsDecorated(False)
        self.__table.setSortingEnabled(True)
        layout.addWidget(self.__table)

        self.__footer = QtWidgets.QLabel("", self)
        self.__footer.setWordWrap(True)
        layout.addWidget(self.__footer)

        # pylint: disable=no-member
        self.__btnRefresh.clicked.connect(self.refresh)
        self.__filter.textChanged.connect(self.__applyFilter)
        self.__table.itemDoubleClicked.connect(self.__itemDoubleClicked)
        # pylint: enable=no-member

        self.refresh()

    def refresh(self):
        """Reloads the limit and its holder list from the Cuebot."""
        try:
            self.__limit = opencue.api.findLimit(self.__limit.name())
            holds = self.__limit.holds()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return

        self.__table.clear()
        renderHosts = 0
        for hold in holds:
            item = QtWidgets.QTreeWidgetItem([
                hold.host_name,
                str(hold.tokens),
                self.HOLD_SOURCE_NAMES.get(hold.source, str(hold.source)),
                hold.user or '--',
                _relativeAge(hold.report_time)])
            item.setData(0, QtCore.Qt.UserRole, hold.host_id)
            if hold.host_id:
                renderHosts += 1
            else:
                item.setToolTip(0, "Not a render host; probably an artist workstation.")
            self.__table.addTopLevelItem(item)

        limit = self.__limit
        parts = ["%d of %d in use" % (limit.currentUsage(), limit.maxValue()),
                 "%d reported by the license server, %d booked since" % (
                     limit.settledUsage(), limit.pendingUsage()),
                 "%d render hosts, %d workstations" % (renderHosts, len(holds) - renderHosts)]
        if 0 <= limit.softValue() < limit.maxValue():
            parts.append("Packing above %d" % limit.softValue())
        if limit.lastReportTime():
            parts.append("Reported by %s, %s" % (
                limit.reportSource() or 'unknown', _relativeAge(limit.lastReportTime())))
        self.__footer.setText(". ".join(parts) + ".")
        self.__applyFilter(self.__filter.text())

    def __applyFilter(self, text):
        needle = str(text).strip().lower()
        for i in range(self.__table.topLevelItemCount()):
            item = self.__table.topLevelItem(i)
            item.setHidden(bool(needle) and needle not in str(item.text(0)).lower())

    def __itemDoubleClicked(self, item, col):
        """Render-host rows are actionable: double-click jumps to the host monitor."""
        del col
        if item.data(0, QtCore.Qt.UserRole):
            self.app.view_hosts.emit([str(item.text(0))])


class LimitBindingsDialog(QtWidgets.QDialog):
    """Shows which layers Cue thinks need a limit's license, and how it learned that."""

    def __init__(self, limit, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.__limit = limit
        self.setWindowTitle("Tagged Layers: %s" % limit.name())
        self.resize(760, 480)

        layout = QtWidgets.QVBoxLayout(self)

        topBar = QtWidgets.QHBoxLayout()
        self.__sourceFilter = QtWidgets.QComboBox(self)
        self.__sourceFilter.addItem("All origins", None)
        self.__sourceFilter.addItem("Spec", limit_pb2.SPEC)
        self.__sourceFilter.addItem("Auto", limit_pb2.AUTO)
        self.__sourceFilter.addItem("Manual", limit_pb2.MANUAL)
        self.__filter = QtWidgets.QLineEdit(self)
        self.__filter.setPlaceholderText("Filter by layer or job name")
        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnClearAuto = QtWidgets.QPushButton("Remove Auto-Tagged Layers…", self)
        topBar.addWidget(self.__sourceFilter)
        topBar.addWidget(self.__filter)
        topBar.addWidget(self.__btnRefresh)
        topBar.addWidget(self.__btnClearAuto)
        layout.addLayout(topBar)

        self.__table = QtWidgets.QTreeWidget(self)
        self.__table.setHeaderLabels(["Layer", "Job", "Services", "Bound", "When"])
        self.__table.setRootIsDecorated(False)
        self.__table.setSortingEnabled(True)
        layout.addWidget(self.__table)

        self.__footer = QtWidgets.QLabel("", self)
        self.__footer.setWordWrap(True)
        layout.addWidget(self.__footer)

        # pylint: disable=no-member
        self.__btnRefresh.clicked.connect(self.refresh)
        self.__filter.textChanged.connect(self.__applyFilter)
        self.__sourceFilter.currentIndexChanged.connect(lambda _: self.refresh())
        self.__btnClearAuto.clicked.connect(self.__clearAutoBindings)
        # pylint: enable=no-member

        self.refresh()

    def refresh(self):
        """Reloads the binding list from the Cuebot."""
        source = self.__sourceFilter.currentData()
        sources = [source] if source is not None else None
        try:
            bindings = self.__limit.bindings(sources=sources)
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return

        self.__table.clear()
        autoCount = 0
        autoServices = {}
        for binding in bindings:
            sourceName = BIND_SOURCE_NAMES.get(binding.source, str(binding.source))
            item = QtWidgets.QTreeWidgetItem([
                binding.layer_name,
                binding.job_name,
                ",".join(binding.services),
                sourceName,
                _relativeAge(binding.create_time) if binding.source != limit_pb2.SPEC
                else 'at launch'])
            if binding.source == limit_pb2.AUTO:
                autoCount += 1
                for service in binding.services:
                    autoServices[service] = autoServices.get(service, 0) + 1
                item.setToolTip(3, "Cue inferred this binding from a frame failure; the "
                                   "submitter did not declare it.")
            self.__table.addTopLevelItem(item)

        footer = "%d layers bound" % len(bindings)
        if autoCount:
            footer += ", %d of them auto-bound" % autoCount
            if autoServices:
                top = max(autoServices.items(), key=lambda kv: kv[1])
                footer += " (%d of those run service \"%s\" — consider making this " \
                          "limit a service default)" % (top[1], top[0])
        self.__footer.setText(footer + ".")
        self.__applyFilter(self.__filter.text())

    def __applyFilter(self, text):
        needle = str(text).strip().lower()
        for i in range(self.__table.topLevelItemCount()):
            item = self.__table.topLevelItem(i)
            haystack = (str(item.text(0)) + " " + str(item.text(1))).lower()
            item.setHidden(bool(needle) and needle not in haystack)

    def __clearAutoBindings(self):
        try:
            autoCount = len(self.__limit.bindings(sources=[limit_pb2.AUTO]))
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return
        if not autoCount:
            QtWidgets.QMessageBox.information(
                self, self.windowTitle(), "No auto-tagged layers to remove.")
            return
        if QtWidgets.QMessageBox.question(
                self, self.windowTitle(),
                "Remove %d auto-tagged layers from limit %s?\n\n"
                "Only bindings Cue inferred from frame failures are removed; layers "
                "that declared this limit in their job spec are untouched." % (
                    autoCount, self.__limit.name()),
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        ) == QtWidgets.QMessageBox.Yes:
            try:
                removed = self.__limit.clearBindings([limit_pb2.AUTO])
                QtWidgets.QMessageBox.information(
                    self, self.windowTitle(), "Removed %d auto-tagged layers." % removed)
            except opencue.exception.CueException as e:
                QtWidgets.QMessageBox.critical(
                    self, self.windowTitle(), "Removing bindings failed:\n%s" % e)
            self.refresh()
