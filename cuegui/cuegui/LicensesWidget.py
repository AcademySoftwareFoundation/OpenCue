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


"""Widget for inspecting application licenses.

Read-only by design: the numbers belong to the license server Cuebot polls
(``scheduler.license.provider``), and the tuning (provider, headroom, poll
cadence) lives in ``opencue.properties``. This view shows what the poller
currently knows and how much of each pool this OpenCue deploy is using.
"""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from qtpy import QtCore
from qtpy import QtWidgets

import opencue

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.Logger
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


def _licenseType(lic):
    """Display string for the license kind."""
    return "Host-based" if lic.hostBased() else "Floating"


class LicensesWidget(QtWidgets.QWidget):
    """Widget for inspecting application licenses (read-only)."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__lblStatus = QtWidgets.QLabel("Loading license status...", self)
        self.__lblStatus.setContentsMargins(4, 2, 4, 2)
        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__monitorLicenses = LicensesTreeWidget(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__lblStatus, 0, 0, 1, 3)
        layout.addWidget(self.__btnRefresh, 0, 3)
        layout.addWidget(self.__monitorLicenses, 2, 0, 3, 4)

        # pylint: disable=no-member
        self.__btnRefresh.clicked.connect(self.updateSoon)
        # pylint: enable=no-member
        self.__monitorLicenses.status_update.connect(self.__setStatus)

    def updateSoon(self):
        """Requests a refresh of the license list."""
        # pylint: disable=protected-access
        self.__monitorLicenses._update()

    def __setStatus(self, status):
        """Renders the poller status line above the license table."""
        if status is None:
            # The last refresh could not reach Cuebot: the table was emptied,
            # so the status line must not keep promising a healthy provider.
            self.__lblStatus.setText(
                "License status unavailable — could not reach Cuebot.")
            return
        if not status.configured():
            text = ("License provider not configured (scheduler.license.provider); "
                    "layers declaring licenses are held.")
        elif not status.hasSample():
            text = "Waiting for the first sample from %s" % status.provider()
        else:
            text = "Provider %s — sample %ds old (stale after %ds), poll every %ds" % (
                status.provider(), status.ageSeconds(), status.staleSeconds(),
                status.pollSeconds())
            if status.stale():
                text = "STALE — licensed layers are held. " + text
        self.__lblStatus.setText(text)

    def getColumnVisibility(self):
        """Gets the table column visibility."""
        return self.__monitorLicenses.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets the table column visibility."""
        self.__monitorLicenses.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets the table column order."""
        return self.__monitorLicenses.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets the table column order."""
        self.__monitorLicenses.setColumnOrder(settings)


class LicensesTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying the licenses in the current provider sample."""

    status_update = QtCore.Signal(object)
    """Emitted with the :class:`opencue.wrappers.license.LicensingStatus` of the
    last refresh, on the main thread, after the table has been updated."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_LICENSE)
        self.addColumn("License", 90, id=1,
                       data=lambda license: license.name())
        self.addColumn("Feature", 130, id=2,
                       data=lambda license: license.feature())
        self.addColumn("Type", 80, id=3,
                       data=_licenseType,
                       tip="Floating licenses consume one seat per frame.\n"
                           "Host-based licenses consume one seat per machine, shared\n"
                           "by every frame on it.")
        self.addColumn("Total", 60, id=4,
                       data=lambda license: ("%d" % license.total()),
                       sort=lambda license: license.total(),
                       tip="Seats the license server owns.")
        self.addColumn("Available", 75, id=5,
                       data=lambda license: ("%d" % license.available()),
                       sort=lambda license: license.available(),
                       tip="Seats the license server reports free, net of every\n"
                           "consumer: workstations, CI and other farms included.")
        self.addColumn("In Use", 60, id=6,
                       data=lambda license: ("%d" % license.inUse()),
                       sort=lambda license: license.inUse(),
                       tip="Seats checked out anywhere, per the license server\n"
                           "(total minus available).")
        self.addColumn("Headroom", 75, id=7,
                       data=lambda license: ("%d" % license.headroom()),
                       sort=lambda license: license.headroom(),
                       tip="Seats deliberately withheld from the farm for interactive\n"
                           "users (scheduler.license.headroom.<name>).")
        self.addColumn("Cue Frames", 80, id=8,
                       data=lambda license: ("%d" % license.runningFrames()),
                       sort=lambda license: license.runningFrames(),
                       tip="Frames currently running on this OpenCue deploy whose\n"
                           "layer declares this license.")
        self.addColumn("Cue Hosts", 75, id=9,
                       data=lambda license: ("%d" % license.runningHosts()),
                       sort=lambda license: license.runningHosts(),
                       tip="Distinct hosts running those frames.")
        self.addColumn("Provider Hosts", 95, id=10,
                       data=lambda license: ("%d" % license.providerHostCount()),
                       sort=lambda license: license.providerHostCount(),
                       tip="Hosts the license server reports holding a seat, any\n"
                           "consumer; 0 when the provider does not report hosts.")

        # Before the base __init__, which may run a synchronous first update
        # through _processUpdate when no threadpool exists.
        self.__lastStatus = None

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        self.app.facility_changed.connect(self.__facilityChanged)

        self.setUpdateInterval(60)

    def __facilityChanged(self):
        """Called when the facility is changed"""
        self.removeAllItems()
        self._update()

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        return LicenseWidgetItem(rpcObject, self)

    def _getUpdate(self):
        """Returns the licenses in Cuebot's current provider sample."""
        try:
            status = opencue.api.getLicensingStatus()
            self.__lastStatus = status
            return status.licenses()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            # A stale status must not outlive the rows it described: the
            # empty return clears the table, so clear the status with it.
            self.__lastStatus = None
            return []

    def _processUpdate(self, work, rpcObjects):
        """Updates the table, then publishes the poller status of the same
        refresh; runs on the main thread."""
        super(LicensesTreeWidget, self)._processUpdate(work, rpcObjects)
        self.status_update.emit(self.__lastStatus)

    def tick(self):
        pass


class LicenseWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single license."""

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_LICENSE, rpcObject, parent)
