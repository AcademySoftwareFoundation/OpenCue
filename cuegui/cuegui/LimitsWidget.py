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


"""Widget for managing limits."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from opencue_proto import limit_pb2

import opencue

import cuegui.AbstractTreeWidget
import cuegui.AbstractWidgetItem
import cuegui.Constants
import cuegui.LimitDialogs
import cuegui.Logger
import cuegui.MenuActions
import cuegui.Utils


logger = cuegui.Logger.getLogger(__file__)


def _typeName(limit):
    return limit_pb2.LimitType.Name(limit.limitType()).capitalize()


def _modeName(limit):
    """The enforcement mode, annotated so an operator never has to work out from three
    columns whether a limit is actually gating."""
    name = limit_pb2.LimitEnforcement.Name(limit.enforcement()).capitalize()
    if limit.isReportStale():
        return "%s (stale)" % name
    return name


def _lastReport(limit):
    if not limit.lastReportTime():
        return '--'
    seconds = max(0, int(time.time()) - limit.lastReportTime())
    if seconds < 120:
        return '%ds ago' % seconds
    if seconds < 7200:
        return '%dm ago' % (seconds // 60)
    return '%dh ago' % (seconds // 3600)


def _layerCounts(limit):
    if limit.autoLayerCount():
        return "%d (+%d auto)" % (limit.specLayerCount(), limit.autoLayerCount())
    return "%d" % limit.specLayerCount()


class LimitsWidget(QtWidgets.QWidget):
    """Widget for managing limits."""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.__btnRefresh = QtWidgets.QPushButton("Refresh", self)
        self.__btnRefresh.setFocusPolicy(QtCore.Qt.NoFocus)
        self.__btnAddLimit = QtWidgets.QPushButton("Add Limit", self)
        self.__btnAddLimit.setFocusPolicy(QtCore.Qt.NoFocus)

        self.__monitorLimits = LimitsTreeWidget(self)

        layout = QtWidgets.QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.__btnAddLimit, 0, 3)
        layout.addWidget(self.__btnRefresh, 0, 2)
        layout.addWidget(self.__monitorLimits, 2, 0, 3, 4)

        # pylint: disable=no-member
        self.__btnAddLimit.clicked.connect(self.__addLimit)
        self.__btnRefresh.clicked.connect(self.updateSoon)
        # pylint: enable=no-member

        self.__menuActions = cuegui.MenuActions.MenuActions(self, self.updateSoon, list)

    def updateSoon(self):
        """Requests a refresh of the limits list."""
        # pylint: disable=protected-access
        self.__monitorLimits._update()

    def __addLimit(self):
        self.__menuActions.limits().create()
        self.updateSoon()

    def getColumnVisibility(self):
        """Gets the table column visibility."""
        return self.__monitorLimits.getColumnVisibility()

    def setColumnVisibility(self, settings):
        """Sets the table column visibility."""
        self.__monitorLimits.setColumnVisibility(settings)

    def getColumnOrder(self):
        """Gets the table column order."""
        return self.__monitorLimits.getColumnOrder()

    def setColumnOrder(self, settings):
        """Sets the table column order."""
        self.__monitorLimits.setColumnOrder(settings)


class LimitsTreeWidget(cuegui.AbstractTreeWidget.AbstractTreeWidget):
    """Tree widget for displaying a list of limits."""

    def __init__(self, parent):
        self.startColumnsForType(cuegui.Constants.TYPE_LIMIT)
        self.addColumn("Limit Name", 110, id=1,
                       data=lambda limit: limit.name())
        self.addColumn("Type", 60, id=2,
                       data=_typeName,
                       tip="How the limit counts: per running frame, or per host.\n"
                           "All frames on one host share a single token of a Host limit.")
        self.addColumn("Mode", 100, id=3,
                       data=_modeName,
                       tip="Enforced blocks booking at the thresholds. Advisory never\n"
                           "blocks, but still packs work onto machines already holding\n"
                           "a license. Disabled is ignored entirely. A stale limit\n"
                           "behaves as advisory regardless of its mode.")
        self.addColumn("Max", 60, id=4,
                       data=lambda limit: ("%d" % limit.maxValue()),
                       sort=lambda limit: limit.maxValue(),
                       tip="The maximum usage. For a Host limit this is the maximum\n"
                           "number of machines the farm may spread across.")
        self.addColumn("Soft", 60, id=5,
                       data=lambda limit: '--' if limit.softValue() < 0
                                          else ("%d" % limit.softValue()),
                       sort=lambda limit: limit.softValue(),
                       tip="Above this usage only machines already holding a token may\n"
                           "book: the farm packs instead of spreading. -- means the\n"
                           "same as Max.")
        self.addColumn("In Use", 60, id=6,
                       data=lambda limit: ("%d" % limit.currentUsage()),
                       sort=lambda limit: limit.currentUsage(),
                       tip="Merged usage the dispatcher gates on: settled + pending.")
        self.addColumn("Settled", 60, id=7,
                       data=lambda limit: ("%d" % limit.settledUsage()),
                       sort=lambda limit: limit.settledUsage(),
                       tip="Usage the license server reported as of the last report.")
        self.addColumn("Pending", 60, id=8,
                       data=lambda limit: ("%d" % limit.pendingUsage()),
                       sort=lambda limit: limit.pendingUsage(),
                       tip="Booked since the last report and not yet visible to the\n"
                           "license server. Persistently high means the reporter is\n"
                           "behind, not that the farm is busy.")
        self.addColumn("Hosts", 60, id=9,
                       data=lambda limit: ("%d" % limit.hostCount()),
                       sort=lambda limit: limit.hostCount(),
                       tip="Distinct hosts holding at least one token.")
        self.addColumn("Free", 60, id=10,
                       data=lambda limit: ("%d" % max(0, limit.maxValue()
                                                      - limit.currentUsage())),
                       sort=lambda limit: max(0, limit.maxValue() - limit.currentUsage()),
                       tip="Remaining headroom under Max.")
        self.addColumn("Last Report", 90, id=11,
                       data=_lastReport,
                       sort=lambda limit: limit.lastReportTime(),
                       tip="Age of the last accepted external report; -- means this\n"
                           "limit has never been reported (internal-only). A red cell\n"
                           "means the report is older than the limit's TTL and the\n"
                           "limit has stopped blocking.")
        self.addColumn("Source", 110, id=12,
                       data=lambda limit: limit.reportSource() or '--',
                       tip="Identity of the external reporter, e.g. sesictrl@lic01.")
        self.addColumn("Error Code", 80, id=13,
                       data=lambda limit: '--' if not limit.exitStatus()
                                          else ("%d" % limit.exitStatus()),
                       sort=lambda limit: limit.exitStatus(),
                       tip="Frame exit status meaning this license was unavailable.\n"
                           "A frame failing with this status postpones its layer and\n"
                           "can bind it to this limit automatically.")
        self.addColumn("Backoff", 70, id=14,
                       data=lambda limit: '--' if not limit.delayMinutes()
                                          else ("%dm" % limit.delayMinutes()),
                       sort=lambda limit: limit.delayMinutes(),
                       tip="How long a layer is postponed when a frame reports the\n"
                           "error code. -- means layers are tagged without delaying.")
        self.addColumn("Layers", 90, id=15,
                       data=_layerCounts,
                       sort=lambda limit: limit.specLayerCount() + limit.autoLayerCount(),
                       tip="Layers bound to this limit: spec-declared (+auto-bound).\n"
                           "While the auto count climbs, coverage is still converging\n"
                           "and the limit is not ready to be Enforced.")

        cuegui.AbstractTreeWidget.AbstractTreeWidget.__init__(self, parent)

        # Used to build right click context menus
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.updateSoon, self.selectedObjects)

        self.itemDoubleClicked.connect(self.__itemDoubleClicked)  # pylint: disable=no-member
        self.app.facility_changed.connect(self.__facilityChanged)

        self.setUpdateInterval(60)

    def __facilityChanged(self):
        """Called when the facility is changed"""
        self.removeAllItems()
        self._update()

    def __itemDoubleClicked(self, item, col):
        """Double-clicking a limit opens its holder list."""
        del col
        cuegui.LimitDialogs.LimitHoldsDialog(item.rpcObject, self).show()

    def _createItem(self, rpcObject):
        """Creates and returns the proper item"""
        item = LimitWidgetItem(rpcObject, self)
        return item

    def _getUpdate(self):
        """Returns the proper data from the cuebot"""
        try:
            return opencue.api.getLimits()
        except opencue.exception.CueException as e:
            list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
            return []

    def contextMenuEvent(self, e):
        """When right clicking on an item, this raises a context menu"""
        menu = QtWidgets.QMenu()
        self.__menuActions.limits().addAction(menu, "editMaxValue")
        self.__menuActions.limits().addAction(menu, "editSoftValue")
        typeMenu = menu.addMenu("Set Type")
        self.__menuActions.limits().addAction(typeMenu, "setTypeFrame")
        self.__menuActions.limits().addAction(typeMenu, "setTypeHost")
        modeMenu = menu.addMenu("Set Mode")
        self.__menuActions.limits().addAction(modeMenu, "setModeEnforced")
        self.__menuActions.limits().addAction(modeMenu, "setModeAdvisory")
        self.__menuActions.limits().addAction(modeMenu, "setModeDisabled")
        self.__menuActions.limits().addAction(menu, "setReportTimeout")
        self.__menuActions.limits().addAction(menu, "setFailureRule")
        menu.addSeparator()
        self.__menuActions.limits().addAction(menu, "showHolds")
        self.__menuActions.limits().addAction(menu, "showBindings")
        self.__menuActions.limits().addAction(menu, "removeAutoTagged")
        menu.addSeparator()
        self.__menuActions.limits().addAction(menu, "rename")
        self.__menuActions.limits().addAction(menu, "delete")
        menu.exec_(QtCore.QPoint(e.globalX(), e.globalY())) # pylint: disable=no-member

    def tick(self):
        pass


class LimitWidgetItem(cuegui.AbstractWidgetItem.AbstractWidgetItem):
    """Widget item for displaying a single limit."""

    MODE_COLUMN = 2
    IN_USE_COLUMN = 5
    LAST_REPORT_COLUMN = 10

    __COLOR_STALE = QtGui.QColor(180, 60, 60)
    __COLOR_SATURATED = QtGui.QColor(160, 120, 40)
    # Packing between soft and max is a healthy state -- the farm is consolidating, not
    # stuck -- so it gets a distinct, calmer tone than saturation.
    __COLOR_PACKING = QtGui.QColor(50, 110, 110)

    def __init__(self, rpcObject, parent):
        cuegui.AbstractWidgetItem.AbstractWidgetItem.__init__(
            self, cuegui.Constants.TYPE_LIMIT, rpcObject, parent)

    def data(self, col, role):
        limit = self.rpcObject
        if role == QtCore.Qt.BackgroundRole:
            if col == self.LAST_REPORT_COLUMN and limit.isReportStale():
                return self.__COLOR_STALE
            if col == self.IN_USE_COLUMN:
                if limit.currentUsage() >= limit.maxValue():
                    return self.__COLOR_SATURATED
                if 0 <= limit.softValue() <= limit.currentUsage():
                    return self.__COLOR_PACKING
        if role == QtCore.Qt.ToolTipRole:
            if col == self.LAST_REPORT_COLUMN and limit.isReportStale():
                return ("No report for over %d seconds (from %s); the limit has stopped "
                        "blocking and behaves as advisory."
                        % (limit.reportTtl(), limit.reportSource() or 'unknown source'))
        return cuegui.AbstractWidgetItem.AbstractWidgetItem.data(self, col, role)
