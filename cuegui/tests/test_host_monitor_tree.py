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


"""Tests for cuegui.HostMonitorTree."""


import unittest

import mock
import qtpy.QtCore
import qtpy.QtWidgets

import opencue.exception
import opencue.wrappers.host
import opencue_proto.host_pb2
import opencue_proto.limit_pb2

import cuegui.HostMonitorTree
import cuegui.ItemDelegate
import cuegui.Style

from . import test_utils


def _makeHost(free_mcp, total_mcp, name='host01'):
    return opencue.wrappers.host.Host(
        opencue_proto.host_pb2.Host(
            id='host-id', name=name, free_mcp=free_mcp, total_mcp=total_mcp))


class TempCellHelpersTests(unittest.TestCase):

    def test_freeAmountIsHumanReadable(self):
        host = _makeHost(free_mcp=10 * 1024 * 1024, total_mcp=20 * 1024 * 1024)
        self.assertEqual("10.0G", cuegui.HostMonitorTree._formatTempFreeAmount(host))

    def test_freeAmountRendersWhenTotalUnknown(self):
        # Total is not required for the amount column.
        host = _makeHost(free_mcp=5 * 1024 * 1024, total_mcp=0)
        self.assertEqual("5.0G", cuegui.HostMonitorTree._formatTempFreeAmount(host))

    def test_percentIncludesPercentSign(self):
        # 50% free.
        host = _makeHost(free_mcp=10 * 1024 * 1024, total_mcp=20 * 1024 * 1024)
        self.assertEqual("50%", cuegui.HostMonitorTree._formatTempFreePercent(host))

    def test_percentRoundsToNearestInteger(self):
        # 1/3 free -> 33%.
        host = _makeHost(free_mcp=1 * 1024 * 1024, total_mcp=3 * 1024 * 1024)
        self.assertEqual("33%", cuegui.HostMonitorTree._formatTempFreePercent(host))

    def test_percentIsEmptyWhenTotalUnknown(self):
        host = _makeHost(free_mcp=5 * 1024 * 1024, total_mcp=0)
        self.assertEqual("", cuegui.HostMonitorTree._formatTempFreePercent(host))

    def test_ratioIsFractionOfFreeOverTotal(self):
        host = _makeHost(free_mcp=25, total_mcp=100)
        self.assertAlmostEqual(0.25, cuegui.HostMonitorTree._tempFreeRatio(host))

    def test_ratioFallsBackToFreeWhenTotalUnknown(self):
        host = _makeHost(free_mcp=42, total_mcp=0)
        # When total is unknown, sort by free amount so ordering is still
        # somewhat sensible.
        self.assertEqual(42, cuegui.HostMonitorTree._tempFreeRatio(host))


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class LicenseFilterTests(unittest.TestCase):
    """The license filter matches against a holds map fetched per refresh."""

    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        # Kept as instance attr so the parent isn't garbage-collected mid-test.
        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.tree = cuegui.HostMonitorTree.HostMonitorTree(self.parentWidget)
        self.tree.licenseFilters = ['houdini']

    @staticmethod
    def _hold(host_name, limit_name, source=opencue_proto.limit_pb2.CUE):
        return opencue_proto.limit_pb2.LimitHold(
            host_name=host_name, limit_name=limit_name, source=source)

    @mock.patch('opencue.api.getHosts')
    @mock.patch('opencue.api.getLimitHolds')
    def test_filterMatchesHostsHoldingTheLicense(self, holds_mock, hosts_mock):
        hosts_mock.return_value = [_makeHost(1, 2, name='host01'),
                                   _makeHost(1, 2, name='host02')]
        holds_mock.return_value = [self._hold('host01', 'houdini')]

        result = self.tree._getUpdate()

        self.assertEqual(['host01'], [host.data.name for host in result])

    @mock.patch('opencue.api.getHosts')
    @mock.patch('opencue.api.getLimitHolds')
    def test_holdsWithAnExternalComponentAreParenthesized(self, holds_mock, hosts_mock):
        hosts_mock.return_value = [_makeHost(1, 2, name='host01')]
        holds_mock.return_value = [
            self._hold('host01', 'houdini'),
            self._hold('host01', 'mari', source=opencue_proto.limit_pb2.EXTERNAL),
            self._hold('host01', 'nuke', source=opencue_proto.limit_pb2.BOTH)]

        self.tree._getUpdate()

        # BOTH includes external usage, so it is marked like EXTERNAL; the Cue side of it is
        # already visible through the host's running frames.
        self.assertEqual(['(mari)', '(nuke)', 'houdini'],
                         sorted(self.tree._HostMonitorTree__hostLimits.get('host01', [])))

    @mock.patch('opencue.api.getHosts')
    @mock.patch('opencue.api.getLimitHolds')
    def test_holdsFailureKeepsTheLastGoodMap(self, holds_mock, hosts_mock):
        hosts_mock.return_value = [_makeHost(1, 2, name='host01'),
                                   _makeHost(1, 2, name='host02')]
        holds_mock.return_value = [self._hold('host01', 'houdini')]
        self.tree._getUpdate()

        # A transient failure must not be read as "nobody holds anything", which would
        # filter every host away and show an empty farm with no explanation.
        holds_mock.side_effect = opencue.exception.CueException('cuebot hiccup')
        result = self.tree._getUpdate()

        self.assertEqual(['host01'], [host.data.name for host in result])

    @mock.patch('opencue.api.getHosts')
    @mock.patch('opencue.api.getLimitHolds')
    def test_holdsNeverAvailableSkipsTheFilter(self, holds_mock, hosts_mock):
        hosts_mock.return_value = [_makeHost(1, 2, name='host01'),
                                   _makeHost(1, 2, name='host02')]
        holds_mock.side_effect = opencue.exception.CueException('cuebot hiccup')

        # With no map to match on, showing every host beats showing none.
        result = self.tree._getUpdate()

        self.assertEqual(['host01', 'host02'], [host.data.name for host in result])


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class HostWidgetItemTempBarDataTests(unittest.TestCase):

    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        # Kept as instance attr so the parent isn't garbage-collected mid-test.
        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.tree = cuegui.HostMonitorTree.HostMonitorTree(self.parentWidget)

    def test_userRole4ReturnsUsedAndTotal(self):
        host = _makeHost(free_mcp=30, total_mcp=100)
        item = cuegui.HostMonitorTree.HostWidgetItem(host, self.tree)

        # Any column index is fine — the role is what selects the bar payload.
        used, total = item.data(0, qtpy.QtCore.Qt.UserRole + 4)

        self.assertEqual(70, used)
        self.assertEqual(100, total)

    def test_tempColumnIsWiredToBarDelegate(self):
        # Column id=9 is the bar-only "Temp" column. addColumn appends in
        # order so it lives at index 8 (zero-based).
        temp_col_index = 8
        delegate = self.tree.itemDelegateForColumn(temp_col_index)

        self.assertIsInstance(delegate, cuegui.ItemDelegate.HostTempBarDelegate)

    def test_tempFreeColumnHasNoBarDelegate(self):
        # "Temp Free" sits right after "Temp" at index 9. It's a plain text
        # column showing the absolute free amount (e.g. "23.5G") — no bar.
        temp_free_col_index = 9
        delegate = self.tree.itemDelegateForColumn(temp_free_col_index)

        self.assertNotIsInstance(delegate, cuegui.ItemDelegate.HostTempBarDelegate)

    def test_tempFreePercentColumnHasNoBarDelegate(self):
        # "Temp Free %" sits at index 10, after "Temp Free". Plain text only
        # ("50%"), sorted by ratio to mirror the bar at index 8.
        temp_free_pct_col_index = 10
        delegate = self.tree.itemDelegateForColumn(temp_free_pct_col_index)

        self.assertNotIsInstance(delegate, cuegui.ItemDelegate.HostTempBarDelegate)


if __name__ == '__main__':
    unittest.main()
