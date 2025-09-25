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


"""Tests for cuegui.AbstractDialog."""


import unittest

import mock
from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.AbstractDialog

from . import test_utils


class AbstractDialogTests(unittest.TestCase):
    def setUp(self):
        self.app = test_utils.createApplication()
        self.parent_widget = QtWidgets.QWidget()
        self.dialog = cuegui.AbstractDialog.AbstractDialog(self.parent_widget)

    def tearDown(self):
        self.dialog.deleteLater()
        self.parent_widget.deleteLater()

    def test_init(self):
        self.assertIsInstance(self.dialog, QtWidgets.QDialog)
        self.assertEqual(self.dialog.parent(), self.parent_widget)

    def test_init_without_parent(self):
        dialog = cuegui.AbstractDialog.AbstractDialog()
        self.assertIsNone(dialog.parent())
        dialog.deleteLater()

    def test_newCheckBoxSelectionMatrix(self):
        title = "Test Matrix"
        allowed_options = ["Option1", "Option2", "Option3"]
        checked_options = ["Option1", "Option3"]

        matrix = self.dialog._newCheckBoxSelectionMatrix(
            title, allowed_options, checked_options)

        self.assertIsInstance(matrix, cuegui.AbstractDialog.CheckBoxSelectionMatrix)

    def test_newDialogButtonBox_horizontal(self):
        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        button_box = self.dialog._newDialogButtonBox(buttons)

        self.assertIsInstance(button_box, QtWidgets.QDialogButtonBox)
        self.assertEqual(button_box.orientation(), QtCore.Qt.Horizontal)
        self.assertEqual(button_box.parent(), self.dialog)

    def test_newDialogButtonBox_vertical(self):
        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        button_box = self.dialog._newDialogButtonBox(buttons, QtCore.Qt.Vertical)

        self.assertIsInstance(button_box, QtWidgets.QDialogButtonBox)
        self.assertEqual(button_box.orientation(), QtCore.Qt.Vertical)

    def test_newDialogButtonBox_signals(self):
        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        button_box = self.dialog._newDialogButtonBox(buttons)

        # Test accept signal
        with mock.patch.object(self.dialog, 'accept') as mock_accept:
            button_box.accepted.emit()
            mock_accept.assert_called_once()

        # Test reject signal
        with mock.patch.object(self.dialog, 'reject') as mock_reject:
            button_box.rejected.emit()
            mock_reject.assert_called_once()

    def test_addWidgetRow_single_widget(self):
        layout = QtWidgets.QVBoxLayout()
        self.dialog.setLayout(layout)

        widget = QtWidgets.QLabel("Test Label")
        self.dialog._addWidgetRow(widget)

        # Check that a horizontal layout was added
        self.assertEqual(layout.count(), 1)
        added_layout = layout.itemAt(0).layout()
        self.assertIsInstance(added_layout, QtWidgets.QHBoxLayout)
        self.assertEqual(added_layout.count(), 1)

    def test_addWidgetRow_multiple_widgets(self):
        layout = QtWidgets.QVBoxLayout()
        self.dialog.setLayout(layout)

        widget1 = QtWidgets.QLabel("Label 1")
        widget2 = QtWidgets.QLineEdit()
        widget3 = QtWidgets.QPushButton("Button")

        self.dialog._addWidgetRow(widget1, widget2, widget3)

        # Check that a horizontal layout with 3 widgets was added
        self.assertEqual(layout.count(), 1)
        added_layout = layout.itemAt(0).layout()
        self.assertIsInstance(added_layout, QtWidgets.QHBoxLayout)
        self.assertEqual(added_layout.count(), 3)


class CheckBoxSelectionMatrixTests(unittest.TestCase):
    def setUp(self):
        self.app = test_utils.createApplication()
        self.title = "Test Matrix"
        self.allowed_options = ["Option1", "Option2", "Option3", "Option4"]
        self.checked_options = ["Option1", "Option3"]
        self.matrix = cuegui.AbstractDialog.CheckBoxSelectionMatrix(
            self.title, self.allowed_options, self.checked_options)

    def tearDown(self):
        self.matrix.deleteLater()

    def test_init(self):
        self.assertIsInstance(self.matrix, QtWidgets.QWidget)

        # Check that the group box was created with correct title
        group_box = self.matrix.findChild(QtWidgets.QGroupBox)
        self.assertIsNotNone(group_box)
        self.assertEqual(group_box.title(), self.title)

    def test_checkbox_creation(self):
        checkboxes = self.matrix.findChildren(QtWidgets.QCheckBox)
        self.assertEqual(len(checkboxes), len(self.allowed_options))

        # Check checkbox text
        checkbox_texts = [cb.text() for cb in checkboxes]
        for option in self.allowed_options:
            self.assertIn(option, checkbox_texts)

    def test_initial_checked_state(self):
        checkboxes = self.matrix.findChildren(QtWidgets.QCheckBox)
        for checkbox in checkboxes:
            if checkbox.text() in self.checked_options:
                self.assertTrue(checkbox.isChecked())
            else:
                self.assertFalse(checkbox.isChecked())

    def test_checkedBoxes(self):
        checked_boxes = self.matrix.checkedBoxes()
        self.assertEqual(len(checked_boxes), len(self.checked_options))

        for box in checked_boxes:
            self.assertIn(box.text(), self.checked_options)

    def test_checkedOptions(self):
        checked_options = self.matrix.checkedOptions()
        self.assertEqual(len(checked_options), len(self.checked_options))
        self.assertEqual(set(checked_options), set(self.checked_options))

    def test_checkBoxes(self):
        # Change selection
        new_selection = ["Option2", "Option4"]
        self.matrix.checkBoxes(new_selection)

        # Verify new selection
        checked_options = self.matrix.checkedOptions()
        self.assertEqual(set(checked_options), set(new_selection))

    def test_checkBoxes_empty(self):
        # Uncheck all boxes
        self.matrix.checkBoxes([])

        checked_options = self.matrix.checkedOptions()
        self.assertEqual(len(checked_options), 0)

    def test_checkBoxes_all(self):
        # Check all boxes
        self.matrix.checkBoxes(self.allowed_options)

        checked_options = self.matrix.checkedOptions()
        self.assertEqual(set(checked_options), set(self.allowed_options))

    def test_layout_grid(self):
        # Test that checkboxes are arranged in a 2-column grid
        group_box = self.matrix.findChild(QtWidgets.QGroupBox)
        layout = group_box.layout()
        self.assertIsInstance(layout, QtWidgets.QGridLayout)

        # For 4 options, should have 2 rows and 2 columns
        checkboxes = self.matrix.findChildren(QtWidgets.QCheckBox)
        for index, checkbox in enumerate(checkboxes):
            expected_row = index // 2
            expected_col = index % 2
            item = layout.itemAtPosition(expected_row, expected_col)
            self.assertIsNotNone(item)
            self.assertEqual(item.widget(), checkbox)

    def test_with_parent(self):
        parent_widget = QtWidgets.QWidget()
        matrix = cuegui.AbstractDialog.CheckBoxSelectionMatrix(
            "Test", ["A", "B"], ["A"], parent_widget)

        self.assertEqual(matrix.parent(), parent_widget)

        matrix.deleteLater()
        parent_widget.deleteLater()


if __name__ == '__main__':
    unittest.main()
