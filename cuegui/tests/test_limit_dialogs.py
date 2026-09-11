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


"""Tests for cuegui.LimitDialogs."""


import unittest

import mock

import qtpy.QtCore

import opencue.exception
import opencue.wrappers.limit

import cuegui.LimitDialogs
import cuegui.Style

from . import test_utils


@mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.Mock())
class CreateLimitDialogTests(unittest.TestCase):

    def setUp(self):
        app = test_utils.createApplication()
        app.settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.dialog = cuegui.LimitDialogs.CreateLimitDialog()

    @mock.patch('opencue.api.createLimit')
    @mock.patch('opencue.api.findLimit',
                new=mock.Mock(side_effect=opencue.exception.CueException('no such limit')))
    def testCreatesPlainLimitWithNoFailureRule(self, create_limit_mock):
        # The exit status spin box shows its minimum as "no rule", so the minimum must be a
        # value the create path accepts: 1 is rejected as the generic failure code.
        self.dialog.findChild(cuegui.LimitDialogs.QtWidgets.QLineEdit).setText('houdini')

        # pylint: disable=protected-access
        self.dialog._CreateLimitDialog__accept()

        create_limit_mock.assert_called_once()
        self.assertEqual(0, create_limit_mock.call_args[1]['exitStatus'])

    def testTypeAndModeToggleIndependently(self):
        # Ungrouped sibling radio buttons are all mutually exclusive in Qt: without an
        # explicit QButtonGroup per pair, checking a Type would uncheck the Mode.
        # pylint: disable=protected-access
        self.dialog._CreateLimitDialog__typeHost.setChecked(True)
        self.dialog._CreateLimitDialog__modeAdvisory.setChecked(True)

        self.assertTrue(self.dialog._CreateLimitDialog__typeHost.isChecked())
        self.assertFalse(self.dialog._CreateLimitDialog__typeFrame.isChecked())
        self.assertTrue(self.dialog._CreateLimitDialog__modeAdvisory.isChecked())
        self.assertFalse(self.dialog._CreateLimitDialog__modeEnforced.isChecked())

    def testSoftThresholdFollowsType(self):
        # Packing counts machines, so the threshold is meaningless for per-frame limits;
        # the field must say why it is disabled instead of showing "same as maximum".
        # pylint: disable=protected-access
        softValue = self.dialog._CreateLimitDialog__softValue

        self.assertFalse(softValue.isEnabled())
        self.assertEqual('per-host limits only', softValue.specialValueText())

        self.dialog._CreateLimitDialog__typeHost.setChecked(True)
        self.assertTrue(softValue.isEnabled())
        self.assertEqual('same as maximum', softValue.specialValueText())

        softValue.setValue(120)
        self.dialog._CreateLimitDialog__typeFrame.setChecked(True)
        self.assertFalse(softValue.isEnabled())
        self.assertEqual(0, softValue.value())

    @mock.patch('opencue.api.createLimit')
    @mock.patch('opencue.api.findLimit',
                new=mock.Mock(side_effect=opencue.exception.CueException('no such limit')))
    def testRejectsGenericFailureCode(self, create_limit_mock):
        self.dialog.findChild(cuegui.LimitDialogs.QtWidgets.QLineEdit).setText('houdini')
        # pylint: disable=protected-access
        self.dialog._CreateLimitDialog__exitStatus.setValue(1)

        with mock.patch.object(cuegui.LimitDialogs.QtWidgets.QMessageBox, 'warning'):
            self.dialog._CreateLimitDialog__accept()

        create_limit_mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
