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


"""Tests for cuegui.FilterDialog."""


import unittest

import mock

import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtWidgets
import qtpy.QtTest

import opencue_proto.show_pb2
import opencue_proto.filter_pb2
import opencue.wrappers.filter
import opencue.wrappers.show

import cuegui.FilterDialog
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FilterDialogTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        self.show = opencue.wrappers.show.Show(opencue_proto.show_pb2.Show(name='fooShow'))
        filterProto = opencue_proto.filter_pb2.Filter(
                id='filter-one-id', name='filterOne', order=1, enabled=True)
        self.filter = opencue.wrappers.filter.Filter(filterProto)

        getStubMock.return_value.GetFilters.return_value = \
            opencue_proto.show_pb2.ShowGetFiltersResponse(
                filters=opencue_proto.filter_pb2.FilterSeq(filters=[filterProto]))

        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.filterDialog = cuegui.FilterDialog.FilterDialog(self.show, parent=self.parentWidget)

    def test_shouldTriggerRefresh(self):
        self.show.getFilters = mock.Mock(return_value=[])

        self.filterDialog._FilterDialog__btnRefresh.click()

        self.show.getFilters.assert_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_shouldAddFilter(self, getTextMock):
        newFilterId = 'new-filter-id'
        newFilterName = 'new-filter-name'
        self.show.createFilter = mock.Mock(
            return_value=opencue.wrappers.filter.Filter(
                opencue_proto.filter_pb2.Filter(id=newFilterId, name=newFilterName)))

        getTextMock.return_value = (newFilterName, True)

        self.filterDialog._FilterDialog__btnAddFilter.click()

        self.show.createFilter.assert_called_with(newFilterName)

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    def test_shouldCancelAddingFilter(self, getTextMock):
        self.show.createFilter = mock.Mock()
        getTextMock.return_value = (None, False)

        self.filterDialog._FilterDialog__btnAddFilter.click()

        self.show.createFilter.assert_not_called()

    def test_shouldUpdateMatchersAndActions(self):
        self.filterDialog._FilterDialog__matchers.setObject = mock.Mock()
        self.filterDialog._FilterDialog__actions.setObject = mock.Mock()
        filterMonitorTree = self.filterDialog._FilterDialog__filters
        filterBeingSelected = filterMonitorTree.topLevelItem(0)
        unusedColumnNumber = 0

        filterMonitorTree.itemClicked.emit(filterBeingSelected, unusedColumnNumber)

        self.filterDialog._FilterDialog__matchers.setObject.assert_called_with(self.filter)
        self.filterDialog._FilterDialog__actions.setObject.assert_called_with(self.filter)

    def test_shouldTriggerAddMultipleMatchers(self):
        self.filterDialog._FilterDialog__matchers.addMultipleMatchers = mock.Mock()

        self.filterDialog._FilterDialog__btnAddMultipleMatchers.click()

        self.filterDialog._FilterDialog__matchers.addMultipleMatchers.assert_called()

    def test_shouldTriggerReplaceAllMatchers(self):
        self.filterDialog._FilterDialog__matchers.replaceAllMatchers = mock.Mock()

        self.filterDialog._FilterDialog__btnReplaceAllMatchers.click()

        self.filterDialog._FilterDialog__matchers.replaceAllMatchers.assert_called()

    def test_shouldTriggerDeleteAllMatchers(self):
        self.filterDialog._FilterDialog__matchers.deleteAllMatchers = mock.Mock()

        self.filterDialog._FilterDialog__btnDeleteAllMatchers.click()

        self.filterDialog._FilterDialog__matchers.deleteAllMatchers.assert_called()

    def test_shouldTriggerCreateMatcher(self):
        self.filterDialog._FilterDialog__matchers.createMatcher = mock.Mock()

        self.filterDialog._FilterDialog__btnAddMatcher.click()

        self.filterDialog._FilterDialog__matchers.createMatcher.assert_called()

    def test_shouldTriggerDeleteAllActions(self):
        self.filterDialog._FilterDialog__actions.deleteAllActions = mock.Mock()

        self.filterDialog._FilterDialog__btnDeleteAllActions.click()

        self.filterDialog._FilterDialog__actions.deleteAllActions.assert_called()

    def test_shouldTriggerCreateAction(self):
        self.filterDialog._FilterDialog__actions.createAction = mock.Mock()

        self.filterDialog._FilterDialog__btnAddAction.click()

        self.filterDialog._FilterDialog__actions.createAction.assert_called()

    def test_shouldCloseDialog(self):
        self.assertEqual(qtpy.QtWidgets.QDialog.DialogCode.Rejected, self.filterDialog.result())

        self.filterDialog._FilterDialog__btnDone.click()

        self.assertEqual(qtpy.QtWidgets.QDialog.DialogCode.Accepted, self.filterDialog.result())


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class FilterMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        show = opencue.wrappers.show.Show(opencue_proto.show_pb2.Show(name='fooShow'))
        filters = [
            opencue_proto.filter_pb2.Filter(
                id='filter-one-id', name='filterOne', order=1, enabled=True),
            opencue_proto.filter_pb2.Filter(
                id='filter-two-id', name='filterTwo', order=2, enabled=False),
        ]
        getStubMock.return_value.GetFilters.return_value = \
            opencue_proto.show_pb2.ShowGetFiltersResponse(
                filters=opencue_proto.filter_pb2.FilterSeq(filters=filters))

        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.filterDialog = cuegui.FilterDialog.FilterDialog(show, parent=self.parentWidget)
        self.filterMonitorTree = self.filterDialog._FilterDialog__filters

    def test_shouldPopulateFiltersList(self):
        self.assertEqual(2, self.filterMonitorTree.topLevelItemCount())
        firstItem = self.filterMonitorTree.topLevelItem(0)
        self.assertEqual('1', firstItem.text(0))
        self.assertEqual(True, self.filterMonitorTree.itemWidget(firstItem, 1).isChecked())
        secondItem = self.filterMonitorTree.topLevelItem(1)
        self.assertEqual('2', secondItem.text(0))
        self.assertEqual(False, self.filterMonitorTree.itemWidget(secondItem, 1).isChecked())

    @mock.patch('qtpy.QtWidgets.QMenu')
    def test_shouldRaiseContextMenu(self, qMenuMock):
        filterBeingSelected = self.filterMonitorTree.topLevelItem(0)

        self.filterMonitorTree.contextMenuEvent(
            qtpy.QtGui.QContextMenuEvent(
                qtpy.QtGui.QContextMenuEvent.Reason.Mouse,
                self.filterMonitorTree.visualItemRect(filterBeingSelected).center()))

        qMenuMock.return_value.exec_.assert_called()


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class MatcherMonitorTreeTests(unittest.TestCase):

    @mock.patch('opencue.cuebot.Cuebot.getStub')
    def setUp(self, getStubMock):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()

        self.matchers = [
            opencue_proto.filter_pb2.Matcher(
                id='matcher-one-id',
                subject=opencue_proto.filter_pb2.SHOW,
                type=opencue_proto.filter_pb2.IS,
                input='showName'),
            opencue_proto.filter_pb2.Matcher(
                id='matcher-two-id',
                subject=opencue_proto.filter_pb2.JOB_NAME,
                type=opencue_proto.filter_pb2.CONTAINS,
                input='jobNameSnippet'),
        ]
        self.matcherWrappers = [
            opencue.wrappers.filter.Matcher(matcher) for matcher in self.matchers]
        self.filter = opencue.wrappers.filter.Filter(opencue_proto.filter_pb2.Filter())

        self.parentWidget = qtpy.QtWidgets.QWidget()
        self.matcherMonitorTree = cuegui.FilterDialog.MatcherMonitorTree(None, self.parentWidget)

    def test_shouldPopulateMatchersList(self):
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)

        self.matcherMonitorTree.setObject(self.filter)

        self.filter.getMatchers.assert_called()
        self.assertEqual(2, self.matcherMonitorTree.topLevelItemCount())
        firstItem = self.matcherMonitorTree.topLevelItem(0)
        self.assertEqual('JOB_NAME', self.matcherMonitorTree.itemWidget(firstItem, 0).currentText())
        self.assertEqual('CONTAINS', self.matcherMonitorTree.itemWidget(firstItem, 1).currentText())
        self.assertEqual('jobNameSnippet', self.matcherMonitorTree.itemWidget(firstItem, 2).text())
        secondItem = self.matcherMonitorTree.topLevelItem(1)
        self.assertEqual('SHOW', self.matcherMonitorTree.itemWidget(secondItem, 0).currentText())
        self.assertEqual('IS', self.matcherMonitorTree.itemWidget(secondItem, 1).currentText())
        self.assertEqual('showName', self.matcherMonitorTree.itemWidget(secondItem, 2).text())

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_shouldAddMatcher(self, getItemMock, getTextMock):
        matcherSubject = opencue_proto.filter_pb2.FACILITY
        matcherType = opencue_proto.filter_pb2.CONTAINS
        matcherText = 'facility-substring-to-match'
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        self.filter.createMatcher = mock.Mock(
            return_value=opencue.wrappers.filter.Matcher(
                opencue_proto.filter_pb2.Matcher(
                    id='matcher-three-id',
                    subject=matcherSubject,
                    type=matcherType,
                    input=matcherText)))
        getItemMock.side_effect = [
            ('FACILITY', True),
            ('CONTAINS', True),
        ]
        getTextMock.return_value = (matcherText, True)

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.createMatcher()

        self.filter.createMatcher.assert_called_with(matcherSubject, matcherType, matcherText)
        self.assertEqual(3, self.matcherMonitorTree.topLevelItemCount())
        matcherWidget = self.matcherMonitorTree.topLevelItem(0)
        self.assertEqual(
            'FACILITY', self.matcherMonitorTree.itemWidget(matcherWidget, 0).currentText())
        self.assertEqual(
            'CONTAINS', self.matcherMonitorTree.itemWidget(matcherWidget, 1).currentText())
        self.assertEqual(matcherText, self.matcherMonitorTree.itemWidget(matcherWidget, 2).text())

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_shouldCancelMatcherAdditionAtFirstPrompt(self, getItemMock, getTextMock):
        self.filter.createMatcher = mock.Mock()
        getItemMock.side_effect = [
            ('FACILITY', False),
            ('CONTAINS', True),
        ]
        getTextMock.return_value = ('unused', True)

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.createMatcher()

        self.filter.createMatcher.assert_not_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_shouldCancelMatcherAdditionAtSecondPrompt(self, getItemMock, getTextMock):
        self.filter.createMatcher = mock.Mock()
        getItemMock.side_effect = [
            ('FACILITY', True),
            ('CONTAINS', False),
        ]
        getTextMock.return_value = ('unused', True)

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.createMatcher()

        self.filter.createMatcher.assert_not_called()

    @mock.patch('qtpy.QtWidgets.QInputDialog.getText')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_shouldCancelMatcherAdditionAtThirdrompt(self, getItemMock, getTextMock):
        self.filter.createMatcher = mock.Mock()
        getItemMock.side_effect = [
            ('FACILITY', True),
            ('CONTAINS', True),
        ]
        getTextMock.return_value = ('unused', False)

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.createMatcher()

        self.filter.createMatcher.assert_not_called()

    @mock.patch(
        'qtpy.QtWidgets.QMessageBox.question',
        new=mock.Mock(return_value=qtpy.QtWidgets.QMessageBox.Yes))
    def test_shouldDeleteAllMatchers(self):
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        for matcher in self.matcherWrappers:
            matcher.delete = mock.Mock()

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.deleteAllMatchers()

        for matcher in self.matcherWrappers:
            matcher.delete.assert_called()

    @mock.patch(
        'qtpy.QtWidgets.QMessageBox.question',
        new=mock.Mock(return_value=qtpy.QtWidgets.QMessageBox.No))
    def test_shouldNotDeleteAnyMatchers(self):
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        for matcher in self.matcherWrappers:
            matcher.delete = mock.Mock()

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.deleteAllMatchers()

        for matcher in self.matcherWrappers:
            matcher.delete.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    @mock.patch('cuegui.TextEditDialog.TextEditDialog')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_shouldAddMultipleMatchers(self, getItemMock, textEditDialogMock):
        matcherSubject = opencue_proto.filter_pb2.SHOT
        matcherType = opencue_proto.filter_pb2.IS
        matcherText = 'SHOt01 \n\nshot02\nShot03'
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        self.filter.createMatcher = mock.Mock(
            return_value=opencue.wrappers.filter.Matcher(
                opencue_proto.filter_pb2.Matcher(
                    id='matcher-three-id',
                    subject=matcherSubject,
                    type=matcherType,
                    input=matcherText)))
        getItemMock.side_effect = [
            ('SHOT', True),
            ('IS', True),
        ]
        textEditDialogMock.return_value.exec_.return_value = True
        textEditDialogMock.return_value.results.return_value = matcherText
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        for matcher in self.matcherWrappers:
            matcher.delete = mock.Mock()

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.addMultipleMatchers()

        self.assertEqual(3, self.filter.createMatcher.call_count)
        self.filter.createMatcher.assert_has_calls([
            mock.call(matcherSubject, matcherType, 'shot01'),
            mock.call(matcherSubject, matcherType, 'shot02'),
            mock.call(matcherSubject, matcherType, 'shot03'),
        ])
        for matcher in self.matcherWrappers:
            matcher.delete.assert_not_called()

    @mock.patch('cuegui.Utils.questionBoxYesNo', new=mock.Mock(return_value=True))
    @mock.patch('cuegui.TextEditDialog.TextEditDialog')
    @mock.patch('qtpy.QtWidgets.QInputDialog.getItem')
    def test_shouldReplaceAllMatchers(self, getItemMock, textEditDialogMock):
        matcherSubject = opencue_proto.filter_pb2.SHOT
        matcherType = opencue_proto.filter_pb2.IS
        matcherText = 'SHOt01 \n\nshot02\nShot03'
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        self.filter.createMatcher = mock.Mock(
            return_value=opencue.wrappers.filter.Matcher(
                opencue_proto.filter_pb2.Matcher(
                    id='matcher-three-id',
                    subject=matcherSubject,
                    type=matcherType,
                    input=matcherText)))
        getItemMock.side_effect = [
            ('SHOT', True),
            ('IS', True),
        ]
        textEditDialogMock.return_value.exec_.return_value = True
        textEditDialogMock.return_value.results.return_value = matcherText
        self.filter.getMatchers = mock.Mock(return_value=self.matcherWrappers)
        for matcher in self.matcherWrappers:
            matcher.delete = mock.Mock()

        self.matcherMonitorTree.setObject(self.filter)
        self.matcherMonitorTree.replaceAllMatchers()

        self.assertEqual(3, self.filter.createMatcher.call_count)
        self.filter.createMatcher.assert_has_calls([
            mock.call(matcherSubject, matcherType, 'shot01'),
            mock.call(matcherSubject, matcherType, 'shot02'),
            mock.call(matcherSubject, matcherType, 'shot03'),
        ])
        for matcher in self.matcherWrappers:
            matcher.delete.assert_called()


if __name__ == '__main__':
    unittest.main()
