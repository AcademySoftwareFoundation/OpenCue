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


"""Tests for cuegui.plugins.LogViewPlugin."""


import os
import unittest

import mock

import pyfakefs.fake_filesystem_unittest
import qtpy.QtCore
import qtpy.QtGui
import qtpy.QtTest
import qtpy.QtWidgets

import cuegui.Main
import cuegui.plugins.LogViewPlugin
import cuegui.Style
from .. import test_utils


_LOG_TEXT_1 = '''Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Mauris a odio quis arcu ornare molestie sit amet ac dui.
Integer eros lorem, aliquet eget hendrerit et, sollicitudin a diam.
Suspendisse placerat mi eu rhoncus ultricies.
Quisque tempor tortor quis luctus blandit. Cras at finibus urna.
Morbi tincidunt consequat ullamcorper.
Etiam volutpat ligula nec ligula mattis, in porttitor mauris pharetra.'''

_LOG_TEXT_2 = '''Donec efficitur orci non ex sagittis, ac euismod nibh tempus.
Duis at placerat neque. Mauris at urna id nisl varius dignissim ut at eros.
Praesent quis egestas ligula. Morbi tristique nunc iaculis nisl laoreet rutrum
mattis ut elit. Vestibulum porttitor metus a nisl imperdiet, eget faucibus
mauris laoreet. Ut sem eros, molestie sed sem eu, vehicula molestie orci.
In non tortor at augue imperdiet sodales quis at diam.
Nulla efficitur odio posuere elit ultricies, quis rhoncus ante scelerisque.
Donec porta gravida eros id vulputate. Phasellus vel nisl arcu.'''


# pylint: disable=no-member
class LogViewPluginTests(pyfakefs.fake_filesystem_unittest.TestCase):
    @mock.patch('opencue.cuebot.Cuebot.getStub', new=mock.MagicMock())
    def setUp(self):
        self.setUpPyfakefs()
        paletteFile = os.path.join(os.path.dirname(cuegui.__file__), 'config', 'darkpalette.qss')
        self.fs.add_real_file(paletteFile, read_only=True)
        self.logPath1 = '/some/log/file'
        self.logPath2 = '/another/different/log/somewhere/else'
        self.log1 = self.fs.create_file(self.logPath1, contents=_LOG_TEXT_1)
        self.fs.create_file(self.logPath2, contents=_LOG_TEXT_2)

        test_utils.createApplication()
        cuegui.app().settings = qtpy.QtCore.QSettings()
        cuegui.Style.init()
        self.parentWidget = qtpy.QtWidgets.QMainWindow()
        self.logViewPlugin = cuegui.plugins.LogViewPlugin.LogViewPlugin(self.parentWidget)

    def test_shouldDisplayFirstLogFile(self):
        cuegui.app().display_log_file_content.emit([self.logPath1, self.logPath2])
        self.logViewPlugin.logview_widget._receive_log_results(_LOG_TEXT_1, 0)
        self.assertEqual(_LOG_TEXT_1, self.logViewPlugin.logview_widget._content_box.toPlainText())

    def test_shouldUpdateLogFile(self):
        cuegui.app().display_log_file_content.emit([self.logPath1, self.logPath2])
        self.logViewPlugin.logview_widget._receive_log_results(_LOG_TEXT_1, 0)
        new_contents = _LOG_TEXT_1 + '\nanother line at the end'
        self.log1.set_contents(new_contents)
        cuegui.app().display_log_file_content.emit([self.logPath1, self.logPath2])
        self.logViewPlugin.logview_widget._receive_log_results(new_contents, 0)
        self.assertEqual(new_contents, self.logViewPlugin.logview_widget._content_box.toPlainText())

    def test_shouldHighlightAllSearchResults(self):
        self.logViewPlugin.logview_widget._receive_log_results(_LOG_TEXT_1, 0)
        self.logViewPlugin.logview_widget._case_stv_checkbox.setCheckState(
              qtpy.QtCore.Qt.CheckState.Unchecked)

        self.logViewPlugin.logview_widget._search_box.setText('lorem')
        self.logViewPlugin.logview_widget._search_button.click()
        matches = self.logViewPlugin.logview_widget._matches

        self.assertEqual([(0, 5), (127, 5)], matches)
        self.assertTrue(
            self.__isHighlighted(
                self.logViewPlugin.logview_widget._content_box, matches[0][0], matches[0][1]))
        self.assertTrue(
            self.__isHighlighted(
                self.logViewPlugin.logview_widget._content_box, matches[1][0], matches[1][1]))

    def test_shouldMoveCursorToSecondSearchResult(self):
        self.logViewPlugin.logview_widget._receive_log_results(_LOG_TEXT_1, 0)
        self.logViewPlugin.logview_widget._case_stv_checkbox.setCheckState(
            qtpy.QtCore.Qt.CheckState.Unchecked)

        self.logViewPlugin.logview_widget._search_box.setText('lorem')
        self.logViewPlugin.logview_widget._search_button.click()
        matches = self.logViewPlugin.logview_widget._matches
        self.logViewPlugin.logview_widget._next_button.click()

        self.assertEqual([(0, 5), (127, 5)], matches)
        # Cursor should be at the end of the matched text.
        self.assertEqual(132, self.logViewPlugin.logview_widget._cursor.position())

    def test_shouldMoveCursorLastSearchResult(self):
        self.logViewPlugin.logview_widget._receive_log_results(_LOG_TEXT_1, 0)
        self.logViewPlugin.logview_widget._case_stv_checkbox.setCheckState(
            qtpy.QtCore.Qt.CheckState.Unchecked)

        self.logViewPlugin.logview_widget._search_box.setText('lorem')
        self.logViewPlugin.logview_widget._search_button.click()
        matches = self.logViewPlugin.logview_widget._matches
        self.logViewPlugin.logview_widget._prev_button.click()

        self.assertEqual([(0, 5), (127, 5)], matches)
        # Cursor should be at the end of the matched text.
        self.assertEqual(132, self.logViewPlugin.logview_widget._cursor.position())

    def test_shouldPerformCaseInsensitiveSearch(self):
        self.logViewPlugin.logview_widget._receive_log_results(_LOG_TEXT_1, 0)
        self.logViewPlugin.logview_widget._case_stv_checkbox.setCheckState(
            qtpy.QtCore.Qt.CheckState.Checked)
        self.logViewPlugin.logview_widget._search_box.setText('lorem')
        self.logViewPlugin.logview_widget._search_button.click()
        matches = self.logViewPlugin.logview_widget._matches

        self.assertEqual([(127, 5)], matches)
        self.assertTrue(
            self.__isHighlighted(
                self.logViewPlugin.logview_widget._content_box, matches[0][0], matches[0][1]))

    @staticmethod
    def __isHighlighted(textBox, startPosition, selectionLength):
        cursor = textBox.cursorForPosition(qtpy.QtCore.QPoint(0, 0))
        cursor.setPosition(startPosition)
        cursor.movePosition(qtpy.QtGui.QTextCursor.Right,
                            qtpy.QtGui.QTextCursor.KeepAnchor,
                            selectionLength)
        return cursor.charFormat().background() == qtpy.QtCore.Qt.red


if __name__ == '__main__':
    unittest.main()
