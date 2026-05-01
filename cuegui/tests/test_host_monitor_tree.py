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

import opencue.wrappers.host
import opencue_proto.host_pb2

import cuegui.HostMonitorTree
import cuegui.ItemDelegate
import cuegui.Style

from . import test_utils


def _makeHost(free_mcp, total_mcp):
    return opencue.wrappers.host.Host(
        opencue_proto.host_pb2.Host(
            id='host-id', name='host01', free_mcp=free_mcp, total_mcp=total_mcp))


class TempCellHelpersTests(unittest.TestCase):

    def test_formatIncludesPercentWhenTotalKnown(self):
        # 50% free.
        host = _makeHost(free_mcp=10 * 1024 * 1024, total_mcp=20 * 1024 * 1024)
        self.assertEqual("10.0G (50%)", cuegui.HostMonitorTree._formatTempCell(host))

    def test_formatRoundsPercentToNearestInteger(self):
        # 1/3 free -> 33%.
        host = _makeHost(free_mcp=1 * 1024 * 1024, total_mcp=3 * 1024 * 1024)
        self.assertEqual("1.0G (33%)", cuegui.HostMonitorTree._formatTempCell(host))

    def test_formatFallsBackWhenTotalUnknown(self):
        host = _makeHost(free_mcp=5 * 1024 * 1024, total_mcp=0)
        # No percent suffix when total is unknown.
        self.assertEqual("5.0G", cuegui.HostMonitorTree._formatTempCell(host))

    def test_ratioIsFractionOfFreeOverTotal(self):
        host = _makeHost(free_mcp=25, total_mcp=100)
        self.assertAlmostEqual(0.25, cuegui.HostMonitorTree._tempFreeRatio(host))

    def test_ratioFallsBackToFreeWhenTotalUnknown(self):
        host = _makeHost(free_mcp=42, total_mcp=0)
        # When total is unknown, sort by free amount so ordering is still
        # somewhat sensible.
        self.assertEqual(42, cuegui.HostMonitorTree._tempFreeRatio(host))


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
        # column — no bar delegate, only the formatted "<free> (NN%)" text.
        temp_free_col_index = 9
        delegate = self.tree.itemDelegateForColumn(temp_free_col_index)

        self.assertNotIsInstance(delegate, cuegui.ItemDelegate.HostTempBarDelegate)


if __name__ == '__main__':
    unittest.main()
