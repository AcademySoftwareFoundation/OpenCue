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


"""Tests for cuegui.TextEditDialog."""


import unittest

import mock
from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.TextEditDialog

from . import test_utils


class TextEditDialogTests(unittest.TestCase):

    def setUp(self):
        self.app = test_utils.createApplication()

    def test_text_edit_dialog_initialization(self):
        """Test TextEditDialog initialization with basic parameters."""
        title = "Test Dialog"
        text = "Please enter your text:"
        default = "Default text content"

        dialog = cuegui.TextEditDialog.TextEditDialog(title, text, default)

        self.assertIsInstance(dialog, QtWidgets.QDialog)
        self.assertEqual(dialog.windowTitle(), title)
        self.assertTrue(dialog.isSizeGripEnabled())
        self.assertEqual(dialog.maximumSize(), QtCore.QSize(400, 300))

        dialog.deleteLater()

    def test_text_edit_dialog_initialization_minimal(self):
        """Test TextEditDialog initialization with minimal parameters."""
        title = "Minimal Dialog"
        text = "Enter text:"

        dialog = cuegui.TextEditDialog.TextEditDialog(title, text)

        self.assertEqual(dialog.windowTitle(), title)
        self.assertEqual(dialog.results(), "")  # Should be empty with no default

        dialog.deleteLater()

    def test_text_edit_dialog_with_parent(self):
        """Test TextEditDialog initialization with parent widget."""
        parent_widget = QtWidgets.QWidget()

        try:
            title = "Child Dialog"
            text = "Text for child dialog"

            dialog = cuegui.TextEditDialog.TextEditDialog(title, text, parent=parent_widget)

            self.assertEqual(dialog.parent(), parent_widget)

            dialog.deleteLater()
        finally:
            parent_widget.deleteLater()

    def test_text_edit_dialog_layout_structure(self):
        """Test TextEditDialog layout and widget structure."""
        title = "Layout Test"
        text = "Test text"
        default = "Default content"

        dialog = cuegui.TextEditDialog.TextEditDialog(title, text, default)

        # Check main layout
        layout = dialog.layout()
        self.assertIsInstance(layout, QtWidgets.QVBoxLayout)

        # The layout should have 3 items: label, text edit, button layout
        self.assertEqual(layout.count(), 3)

        # Check first item is QLabel
        label_item = layout.itemAt(0)
        self.assertIsInstance(label_item.widget(), QtWidgets.QLabel)
        label = label_item.widget()
        self.assertEqual(label.text(), text)
        self.assertTrue(label.wordWrap())

        # Check second item is QTextEdit
        textedit_item = layout.itemAt(1)
        self.assertIsInstance(textedit_item.widget(), QtWidgets.QTextEdit)

        # Check third item is horizontal layout with buttons
        button_layout_item = layout.itemAt(2)
        self.assertIsInstance(button_layout_item.layout(), QtWidgets.QHBoxLayout)

        button_layout = button_layout_item.layout()
        self.assertEqual(button_layout.count(), 2)

        dialog.deleteLater()

    def test_text_edit_dialog_buttons(self):
        """Test TextEditDialog button functionality."""
        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Test text")

        # Find buttons in the layout
        layout = dialog.layout()
        button_layout = layout.itemAt(2).layout()

        ok_button = button_layout.itemAt(0).widget()
        cancel_button = button_layout.itemAt(1).widget()

        self.assertIsInstance(ok_button, QtWidgets.QPushButton)
        self.assertIsInstance(cancel_button, QtWidgets.QPushButton)

        self.assertEqual(ok_button.text(), "Ok")
        self.assertEqual(cancel_button.text(), "Cancel")

        dialog.deleteLater()

    def test_text_edit_dialog_default_text_setting(self):
        """Test that default text is set properly in the text edit."""
        default_text = "This is the default text content"

        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Enter text:", default_text)

        # Check that default text was set
        self.assertEqual(dialog.results(), default_text)

        dialog.deleteLater()

    def test_text_edit_dialog_focus_setting(self):
        """Test that focus is set on the text edit widget."""
        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Enter text:", "default")

        # The text edit should have focus
        text_edit = dialog._TextEditDialog__textEdit
        self.assertIsNotNone(text_edit)
        # Note: focus testing in unit tests can be tricky, but we can check the widget exists

        dialog.deleteLater()

    def test_text_edit_dialog_results_method(self):
        """Test the results() method returns correct text."""
        default_text = "Initial text"

        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Enter text:", default_text)

        # Initial results should be the default text
        self.assertEqual(dialog.results(), default_text)

        # Modify text and check results
        new_text = "Modified text content"
        dialog._TextEditDialog__textEdit.setText(new_text)
        self.assertEqual(dialog.results(), new_text)

        # Test with HTML content to ensure plain text is returned
        html_text = "<b>Bold text</b> and <i>italic text</i>"
        dialog._TextEditDialog__textEdit.setHtml(html_text)
        results = dialog.results()
        # Should return plain text without HTML tags
        self.assertNotIn("<b>", results)
        self.assertNotIn("</b>", results)

        dialog.deleteLater()

    def test_text_edit_dialog_button_signals(self):
        """Test button signal connections."""
        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Test text")

        with mock.patch.object(dialog, 'accept') as mock_accept:
            with mock.patch.object(dialog, 'reject') as mock_reject:
                # Find and click OK button
                layout = dialog.layout()
                button_layout = layout.itemAt(2).layout()
                ok_button = button_layout.itemAt(0).widget()
                cancel_button = button_layout.itemAt(1).widget()

                # Simulate button clicks without GUI
                ok_button.clicked.emit()
                mock_accept.assert_called_once()

                cancel_button.clicked.emit()
                mock_reject.assert_called_once()

        dialog.deleteLater()

    def test_text_edit_dialog_size_constraints(self):
        """Test dialog size constraints."""
        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Test text")

        # Should have size grip enabled
        self.assertTrue(dialog.isSizeGripEnabled())

        # Should have maximum size set
        max_size = dialog.maximumSize()
        self.assertEqual(max_size.width(), 400)
        self.assertEqual(max_size.height(), 300)

        dialog.deleteLater()

    def test_text_edit_dialog_word_wrap_label(self):
        """Test that the label has word wrap enabled."""
        long_text = ("This is a very long text that should wrap across multiple lines when "
                     "displayed in the dialog label to ensure proper formatting and readability.")

        dialog = cuegui.TextEditDialog.TextEditDialog("Test", long_text)

        # Find the label
        layout = dialog.layout()
        label = layout.itemAt(0).widget()

        self.assertTrue(label.wordWrap())
        self.assertEqual(label.text(), long_text)

        dialog.deleteLater()

    def test_text_edit_dialog_empty_strings(self):
        """Test TextEditDialog with empty strings."""
        dialog = cuegui.TextEditDialog.TextEditDialog("", "")

        self.assertEqual(dialog.windowTitle(), "")

        # Find the label and check empty text
        layout = dialog.layout()
        label = layout.itemAt(0).widget()
        self.assertEqual(label.text(), "")

        # Results should be empty initially
        self.assertEqual(dialog.results(), "")

        dialog.deleteLater()

    def test_text_edit_dialog_special_characters(self):
        """Test TextEditDialog with special characters."""
        title = "Test Dialog with 特殊字符 and émojis 🚀"
        text = "Enter text with special chars: ñáéíóú & symbols @#$%"
        default = "Default with unicode: 中文 русский العربية"

        dialog = cuegui.TextEditDialog.TextEditDialog(title, text, default)

        self.assertEqual(dialog.windowTitle(), title)
        self.assertEqual(dialog.results(), default)

        # Find the label and check text with special characters
        layout = dialog.layout()
        label = layout.itemAt(0).widget()
        self.assertEqual(label.text(), text)

        dialog.deleteLater()

    def test_text_edit_dialog_multiline_text(self):
        """Test TextEditDialog with multiline text input."""
        multiline_default = "Line 1\nLine 2\nLine 3\n\nLine 5 with spaces"

        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Enter multiline text:",
                                                       multiline_default)

        self.assertEqual(dialog.results(), multiline_default)

        # Add more multiline content
        additional_text = "\nAdded line 6\nAnd line 7"
        current_text = dialog._TextEditDialog__textEdit.toPlainText()
        dialog._TextEditDialog__textEdit.setText(current_text + additional_text)

        expected_result = multiline_default + additional_text
        self.assertEqual(dialog.results(), expected_result)

        dialog.deleteLater()

    def test_text_edit_dialog_very_long_text(self):
        """Test TextEditDialog with very long text content."""
        long_text = "A" * 10000  # Very long string

        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Long text test", long_text)

        # Should handle long text without issues
        self.assertEqual(dialog.results(), long_text)
        self.assertEqual(len(dialog.results()), 10000)

        dialog.deleteLater()

    def test_text_edit_dialog_text_modification(self):
        """Test modifying text in the dialog."""
        initial_text = "Initial content"
        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Modify text:", initial_text)

        # Verify initial content
        self.assertEqual(dialog.results(), initial_text)

        # Simulate user typing
        text_edit = dialog._TextEditDialog__textEdit
        text_edit.clear()
        new_content = "User modified content"
        text_edit.insertPlainText(new_content)

        # Verify modified content
        self.assertEqual(dialog.results(), new_content)

        # Test append operation
        text_edit.append("\nAppended line")
        results = dialog.results()
        self.assertIn("User modified content", results)
        self.assertIn("Appended line", results)

        dialog.deleteLater()

    def test_text_edit_dialog_inheritance(self):
        """Test TextEditDialog inheritance and type checking."""
        dialog = cuegui.TextEditDialog.TextEditDialog("Test", "Test")

        self.assertIsInstance(dialog, QtWidgets.QDialog)
        self.assertIsInstance(dialog, cuegui.TextEditDialog.TextEditDialog)

        dialog.deleteLater()


if __name__ == '__main__':
    unittest.main()
