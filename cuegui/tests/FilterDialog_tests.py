#  Copyright (c) OpenCue Project Authors
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


import mock
import unittest

import PySide2.QtCore
import PySide2.QtGui
import PySide2.QtWidgets
import PySide2.QtTest

import cuegui.FilterDialog
import cuegui.Style
import opencue.compiled_proto.show_pb2
import opencue.compiled_proto.filter_pb2
import opencue.wrappers.filter
import opencue.wrappers.show

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FilterDialogTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        test_utils.createApplication()
        PySide2.QtGui.qApp.settings = PySide2.QtCore.QSettings()
        cuegui.Style.init()

        self.show = opencue.wrappers.show.Show(opencue.compiled_proto.show_pb2.Show(name='fooShow'))
        filterProto = opencue.compiled_proto.filter_pb2.Filter(
                id='filter-one-id', name='filterOne', order=1, enabled=True)

        getStubMock.return_value.GetFilters.return_value = opencue.compiled_proto.show_pb2.ShowGetFiltersResponse(
            filters=opencue.compiled_proto.filter_pb2.FilterSeq(filters=[filterProto]))

        self.parentWidget = PySide2.QtWidgets.QWidget()
        self.filterDialog = cuegui.FilterDialog.FilterDialog(self.show, parent=self.parentWidget)

    def test_shouldTriggerRefresh(self):
        self.show.getFilters = mock.Mock(return_value=[])

        self.filterDialog._FilterDialog__btnRefresh.click()

        self.show.getFilters.assert_called()

    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_shouldAddFilter(self, getTextMock):
        newFilterId = 'new-filter-id'
        newFilterName = 'new-filter-name'
        self.show.createFilter = mock.Mock(
            return_value=opencue.wrappers.filter.Filter(
                opencue.compiled_proto.filter_pb2.Filter(id=newFilterId, name=newFilterName)))

        getTextMock.return_value = (newFilterName, True)

        self.filterDialog._FilterDialog__btnAddFilter.click()

        self.show.createFilter.assert_called_with(newFilterName)

    @mock.patch('PySide2.QtWidgets.QInputDialog.getText')
    def test_shouldCancelAddingFilter(self, getTextMock):
        self.show.createFilter = mock.Mock()
        getTextMock.return_value = (None, False)

        self.filterDialog._FilterDialog__btnAddFilter.click()

        self.show.createFilter.assert_not_called()

    def test_filterSelectionShouldUpdateMatchersAndActions(self):
        self.filterDialog._FilterDialog__matchers.setObject = mock.Mock()
        self.filterDialog._FilterDialog__actions.setObject = mock.Mock()
        filterMonitorTree = self.filterDialog._FilterDialog__filters
        filterBeingSelected = filterMonitorTree.topLevelItem(0)

        PySide2.QtTest.QTest.mouseClick(
            filterMonitorTree.viewport(),
            PySide2.QtCore.Qt.LeftButton,
            PySide2.QtCore.Qt.NoModifier,
            filterMonitorTree.visualItemRect(filterBeingSelected).center())

        self.filterDialog._FilterDialog__matchers.setObject.assert_called()
        self.filterDialog._FilterDialog__actions.setObject.assert_called()


class FilterMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        test_utils.createApplication()
        PySide2.QtGui.qApp.settings = PySide2.QtCore.QSettings()
        cuegui.Style.init()

        show = opencue.wrappers.show.Show(opencue.compiled_proto.show_pb2.Show(name='fooShow'))
        filters = [
            opencue.compiled_proto.filter_pb2.Filter(
                id='filter-one-id', name='filterOne', order=1, enabled=True),
            opencue.compiled_proto.filter_pb2.Filter(
                id='filter-two-id', name='filterTwo', order=2, enabled=False),
        ]
        getStubMock.return_value.GetFilters.return_value = opencue.compiled_proto.show_pb2.ShowGetFiltersResponse(
            filters=opencue.compiled_proto.filter_pb2.FilterSeq(filters=filters))

        self.parentWidget = PySide2.QtWidgets.QWidget()
        self.filterDialog = cuegui.FilterDialog.FilterDialog(show, parent=self.parentWidget)
        self.filterMonitorTree = self.filterDialog._FilterDialog__filters

    def test_filtersListShouldBePopulated(self):
        self.assertEqual(2, self.filterMonitorTree.topLevelItemCount())
        firstItem = self.filterMonitorTree.topLevelItem(0)
        self.assertEqual('1', firstItem.text(0))
        self.assertEqual(True, self.filterMonitorTree.itemWidget(firstItem, 1).isChecked())
        secondItem = self.filterMonitorTree.topLevelItem(1)
        self.assertEqual('2', secondItem.text(0))
        self.assertEqual(False, self.filterMonitorTree.itemWidget(secondItem, 1).isChecked())


if __name__ == '__main__':
    unittest.main()
