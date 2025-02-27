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


"""Plugin for viewing logs."""


from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from builtins import str
from builtins import range
import os
import re
import string
import sys
import time
import traceback

from qtpy import QtGui
from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Constants
import cuegui.AbstractDockWidget


PLUGIN_NAME = 'LogView'
PLUGIN_CATEGORY = 'Other'
PLUGIN_DESCRIPTION = 'Displays Frame Log'
PLUGIN_PROVIDES = 'LogViewPlugin'
PRINTABLE = set(string.printable)


class LogReader(object):
    """
    Custom class to abstract reading log files from multiple backends
    """
    filepath = None
    type = None

    def __init__(self, filepath):
        """LogReader class initialization
           @type    filepath: string
           @param   filepath: The filepath to log to
        """
        self.filepath = filepath

    def size(self):
        """Return the size of the file"""
        return int(os.stat(self.filepath).st_size)

    def getMtime(self):
        """Return modification time of the file"""
        return os.path.getmtime(self.filepath)

    def exists(self):
        """Check if the file exists"""
        return os.path.exists(self.filepath)

    def read(self):
        """Read the data from the backend"""
        content = None
        if self.exists() is True:
            with open(self.filepath, "r", encoding='utf-8') as fp:
                content = fp.read()

        return content


class LineNumberArea(QtWidgets.QWidget):
    """
    Custom widget for the line numbers. This widget is designed to be attached
    to a QPlainTextEdit or a QTextEdit, and expects the editor widget as a
    required arg for creating the Widget
    """

    def __init__(self, editor):
        """
        Creates the LineNumberArea instance

        @param editor: The text editor widget to attach this widget to
        @type editor: QtWidgets.QPlainTextEdit or QtWidgets.QTextEdit
        """

        super(LineNumberArea, self).__init__(editor)
        self.editor = editor

    def paintEvent(self, event):
        """
        The paint event for this widget will trigger the text update on the
        editor widget

        @pararm event: The event to trigger
        @type event: QtGui.QPaintEvent
        """

        self.editor.line_number_area_paint_event(event)


class LogTextEdit(QtWidgets.QPlainTextEdit):
    """
    This is an extension of QPlainTextEdit, with an added custom widget for
    line numbers and automatic highlighting for the current line (the line
    where the cursor is)
    """

    mousePressedSignal = QtCore.Signal(object)

    def __init__(self, parent):
        """
        Creates the LogTextEdit instance and calls the necessary methods to
        update the line-number area

        @param parent: The parent widget
        @type parent: QtWidgets.QWidget
        """
        super(LogTextEdit, self).__init__(parent)

        self._context_menu = None

        # Use a Fixed-Width font for easier debugging
        self.font = self.document().defaultFont()
        self.font.setFamily('Courier New')
        self.document().setDefaultFont(self.font)

        self._line_num_area = LineNumberArea(self)
        # pylint: disable=no-member
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        # pylint: enable=no-member

        self.update_line_number_area_width()
        self.setReadOnly(True)
        self.setMaximumBlockCount(20000)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)  # pylint: disable=no-member

        self.copy_action = QtWidgets.QAction('Copy', self)
        self.copy_action.setStatusTip('Copy Selection')
        self.copy_action.setShortcut('Ctrl+C')
        self.copy_action.triggered[bool].connect(lambda triggered:  # pylint: disable=unsubscriptable-object
            self.copy_selection(QtGui.QClipboard.Clipboard))
        self.addAction(self.copy_action)

    def context_menu(self):
        """
        A custom context menu to pop up when the user Right-Clicks in the
        Log View. Triggered by the customContextMenuRequested signal
        """
        self._context_menu = QtWidgets.QMenu(self)
        self._context_menu.addAction(self.copy_action)
        self._context_menu.exec_(QtGui.QCursor.pos())

    def mouseReleaseEvent(self, event):
        """
        This is used to trigger the text highlighting update at the parent's
        level
        * For performance sake, we're only highlighting visible matches, which
        is why we need to know when the user scrolls manually

        @param event: The mouse release event
        type event: PyQt4.QtGui.QMouseEvent

        @postcondition: The mousePressedSignal is emitted (triggers highlights
                        for surronding matches), and the current selection is
                        stored in the "selection" (AKA. middle-mouse) clipboard
        """

        super(LogTextEdit, self).mouseReleaseEvent(event)
        pos = event.pos()
        self.mousePressedSignal.emit(pos)
        self.copy_selection(QtGui.QClipboard.Selection)

    def copy_selection(self, mode):
        """
        Copy (Ctrl + C) action. Stores the currently selected text in the
        clipboard.

        @param mode: The QClipboard mode value
            (QtGui.QClipboard.Clipboard = GLOBAL
             QtGui.QClipboard.Selection = Selection (middle-mouse))
        @type mode: int
        """
        selection = self.textCursor().selection()
        QtWidgets.QApplication.clipboard().setText('', mode)
        QtWidgets.QApplication.clipboard().setText(selection.toPlainText(), mode)

    def get_line_number_area_width(self):
        """
        Returns the recommended width for the line number area based on the
        current line-count and the font being used

        @return: The recommended width for the line-number area
        @rtype: int
        """

        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self):
        """
        Sets the width for the line number area to the recommended width based
        on line count and the font being used

        @postcondition: The line number area is resized to have the new
                        recommended width
        """

        width = self.get_line_number_area_width()
        self.setViewportMargins(width, 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """
        Calls the necessary methods to update the size and content of the
        line number area.
        * This slot is connected to the updateRequest signal of this object

        @param rect: The rect to update
        @type rect: QtCore.QRect

        @param dy: The scroll value (will be 0 if the update request was
                   triggerred by an event other than scroll)
        @type dy: int
        """

        if dy:
            self._line_num_area.scroll(0, dy)
        else:
            self._line_num_area.update(0,
                                       rect.y(),
                                       self._line_num_area.width(),
                                       rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width()

    def highlight_current_line(self):
        """
        Highlights the line where the cursor is

        @postcondition: The line where the cursor is will have a different
                        background color
        """

        crnt_selection = QtWidgets.QTextEdit.ExtraSelection()
        line_color = QtGui.QColor(QtCore.Qt.red).lighter(12)
        # pylint: disable=no-member
        crnt_selection.format.setBackground(line_color)
        crnt_selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection,
                                          True)
        # pylint: enable=no-member
        crnt_selection.cursor = self.textCursor()
        crnt_selection.cursor.clearSelection()
        self.setExtraSelections([crnt_selection])

    def resizeEvent(self, event):
        """
        Overriding to make sure the line-number area also gets resized when the
        text-editor widget gets resized

        @param event: The resize event
        @type event: QtGui.QResizeEvent
        """

        super(LogTextEdit, self).resizeEvent(event)
        contents_rect = self.contentsRect()
        new_rect = QtCore.QRect(contents_rect.left(),
                                contents_rect.top(),
                                self.get_line_number_area_width(),
                                contents_rect.height())
        self._line_num_area.setGeometry(new_rect)

    def line_number_area_paint_event(self, event):
        """
        Paint the line numbers in the line-number area.
        *This is triggered by the paintEvent of the line-number area

        @param event: The paint event
        @type event: QtGui.QPaintEvent
        """

        painter = QtGui.QPainter(self._line_num_area)
        block = self.firstVisibleBlock()
        block_it = block.iterator()
        block_number = block.blockNumber()
        block_geo = self.blockBoundingGeometry(block)
        top = block_geo.translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        height = self.fontMetrics().height()
        while not block_it.atEnd() and block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(block_number + 1)
                painter.setPen(QtGui.QColor(QtCore.Qt.yellow).lighter(30))
                painter.drawText(0,
                                 top,
                                 self._line_num_area.width(),
                                 height,
                                 QtCore.Qt.AlignRight,
                                 number)
            block = block_it.fragment()
            block_it += 1
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

class LogLoadSignals(QtCore.QObject):
    """Signals for the LoadLog action"""
    SIG_LOG_LOAD_ERROR = QtCore.Signal(tuple)
    SIG_LOG_LOAD_RESULT = QtCore.Signal(str, str)
    SIG_LOG_LOAD_FINISHED = QtCore.Signal()

class LogLoader(QtCore.QRunnable):
    """A thread to load logs"""
    def __init__(self, fn, *args, **kwargs):
        super(LogLoader, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = LogLoadSignals()

    @QtCore.Slot()
    def run(self):
        """Thread run action"""
        # pylint: disable=bare-except
        try:
            content, log_mtime = self.fn(*self.args, **self.kwargs)
        except:
            exctype, value = sys.exc_info()[:2]
            self.signals.SIG_LOG_LOAD_ERROR.emit(
                (exctype, value, traceback.format_exc()))
        else:
            self.signals.SIG_LOG_LOAD_RESULT.emit(content, log_mtime)
        finally:
            self.signals.SIG_LOG_LOAD_FINISHED.emit()

class LogViewWidget(QtWidgets.QWidget):
    """
    Displays the log file for the selected frame
    """
    SIG_CONTENT_UPDATED = QtCore.Signal(str, str)
    def __init__(self, parent=None):
        """
        Create the UI elements
        """
        QtWidgets.QWidget.__init__(self, parent)
        self.app = cuegui.app()

        # Main Widget
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._scrollArea = QtWidgets.QScrollArea()
        self._scrollArea.setWidgetResizable(True)
        self._scrollArea.setFocusPolicy(QtCore.Qt.NoFocus)
        self._scrollWidget = QtWidgets.QWidget(self)
        QtWidgets.QVBoxLayout(self._scrollWidget)
        self._scrollArea.setWidget(self._scrollWidget)
        layout.addWidget(self._scrollArea)

        # Log Path
        path_widget = QtWidgets.QWidget(self)
        path_layout = QtWidgets.QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        self._first_log_button = QtWidgets.QPushButton('<<', self)
        self._first_log_button.clicked.connect(  # pylint: disable=no-member
                                lambda: self._load_other_log(float('inf')))
        self._first_log_button.setEnabled(False)
        self._first_log_button.setToolTip('Load First Log')
        path_layout.addWidget(self._first_log_button)
        self._prev_log_button = QtWidgets.QPushButton('<', self)
        self._prev_log_button.clicked.connect(lambda: self._load_other_log(1))  # pylint: disable=no-member
        self._prev_log_button.setEnabled(False)
        self._prev_log_button.setToolTip('Load Previous Log')
        path_layout.addWidget(self._prev_log_button)
        self._next_log_button = QtWidgets.QPushButton('>', self)
        self._next_log_button.clicked.connect(lambda: self._load_other_log(-1))  # pylint: disable=no-member
        self._next_log_button.setEnabled(False)
        self._next_log_button.setToolTip('Load Next Log')
        path_layout.addWidget(self._next_log_button)
        self._last_log_button = QtWidgets.QPushButton('>>', self)
        self._last_log_button.clicked.connect(  # pylint: disable=no-member
                                lambda: self._load_other_log(-float('inf')))
        self._last_log_button.setEnabled(False)
        self._last_log_button.setToolTip('Load Current Log')
        path_layout.addWidget(self._last_log_button)
        font = self._last_log_button.font()
        font.setPointSize(8)
        for button in [self._first_log_button, self._last_log_button,
                       self._prev_log_button, self._next_log_button]:
            button.setFixedWidth(20)
            button.setFont(font)

        self._path = QtWidgets.QLineEdit('', path_widget)
        self._path.setFocusPolicy(QtCore.Qt.NoFocus)
        path_layout.addWidget(self._path)
        self._scrollWidget.layout().addWidget(path_widget)
        self._scrollWidget.layout().setContentsMargins(0, 0, 0, 0)

        # Word-Wrap
        self._word_wrap_checkbox = QtWidgets.QCheckBox('Word Wrap', self)
        self._word_wrap_checkbox.setFont(font)
        path_layout.addWidget(self._word_wrap_checkbox)
        self._word_wrap_checkbox.setCheckState(QtCore.Qt.Checked)
        self._word_wrap_checkbox.stateChanged.connect(self._set_word_wrap)  # pylint: disable=no-member

        # Content
        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QHBoxLayout(content_widget)
        self._content_box = LogTextEdit(self)
        content_layout.addWidget(self._content_box)
        self._scrollWidget.layout().addWidget(content_widget)
        self._content_box.moveCursor(QtGui.QTextCursor.End)
        self._content_box.ensureCursorVisible()

        self.highlighter = Highlighter(self._content_box.document())

        # Search
        search_top_widget = QtWidgets.QWidget(self)
        search_top_layout = QtWidgets.QVBoxLayout(search_top_widget)
        search_top_layout.setContentsMargins(0, 0, 0, 0)

        self._matches = []
        self._last_search_case_stv = False
        search_widget = QtWidgets.QWidget(self)
        search_layout = QtWidgets.QHBoxLayout(search_widget)
        self._case_stv_checkbox = QtWidgets.QCheckBox('Aa')
        search_layout.addWidget(self._case_stv_checkbox)
        self._case_stv_checkbox.stateChanged.connect(self._move_to_search_box)  # pylint: disable=no-member

        self._search_box = QtWidgets.QLineEdit('', self)
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setPlaceholderText('Search log...')
        search_layout.addWidget(self._search_box)
        self._search_box.show()
        self._search_box.editingFinished.connect(self._find_text)  # pylint: disable=no-member
        self._search_button = QtWidgets.QPushButton('Find', self)
        search_layout.addWidget(self._search_button)
        self._prev_button = QtWidgets.QPushButton('Prev')
        self._prev_button.clicked.connect(self._move_to_prev_match)  # pylint: disable=no-member
        self._next_button = QtWidgets.QPushButton('Next')
        self._next_button.clicked.connect(self._move_to_next_match)  # pylint: disable=no-member
        search_layout.addWidget(self._next_button)
        search_layout.addWidget(self._prev_button)
        search_refresh_button = QtWidgets.QPushButton('Refresh', self)
        search_layout.addWidget(search_refresh_button)
        search_refresh_button.clicked.connect(self._move_to_search_box)  # pylint: disable=no-member

        clear_search_button = QtWidgets.QPushButton('Clr', self)
        search_layout.addWidget(clear_search_button)
        clear_search_button.clicked.connect(self._clear_search_text)  # pylint: disable=no-member
        self._search_button.clicked.connect(self._find_text)  # pylint: disable=no-member

        matches_widget = QtWidgets.QWidget(self)
        matches_layout = QtWidgets.QHBoxLayout(matches_widget)
        matches_layout.setContentsMargins(0, 0, 0, 0)
        self._matches_label = QtWidgets.QLabel('', self)
        self._matches_label.setFixedHeight(9)
        self._matches_label.setStyleSheet('QLabel {color : gray};')
        self._matches_label.setFont(font)
        matches_layout.addWidget(self._matches_label)
        self._log_index_label = QtWidgets.QLabel('', self)
        self._log_index_label.setAlignment(QtCore.Qt.AlignRight)
        self._log_index_label.setStyleSheet('QLabel {color : gray}')
        self._log_index_label.setFont(font)
        matches_layout.addWidget(self._log_index_label)
        search_top_layout.addWidget(search_widget)
        search_top_layout.addWidget(matches_widget)
        self._scrollWidget.layout().addWidget(search_top_widget)

        # Cursor & ScrollBar
        self._cursor = self._content_box.textCursor()
        pos = QtCore.QPoint(0, 0)
        self._highlight_cursor = self._content_box.cursorForPosition(pos)
        # Signals are defined in code, so pylint thinks they don't exist.
        self.app.display_log_file_content.connect(self._set_log_files)
        self._log_scrollbar = self._content_box.verticalScrollBar()

        self._new_log = False
        self._current_log_index = 0
        self._log_files = []
        self._log_file = None
        self._log_file_exists = False
        self._log_mtime = 0
        self._frame_status = None
        self._scrollbar_value = 0
        self._scrollbar_max = 0
        self._search_text = ''
        self._content_timestamp = 0
        self._search_timestamp = 0
        self._first_visible_index = 0
        self._last_visible_index = 0
        self._matches_to_highlight = []
        self._format = QtGui.QTextCharFormat()
        self._format.setBackground(QtCore.Qt.red)
        self._current_match = 0
        self._content_box.mousePressedSignal.connect(self._on_mouse_pressed)

        self.SIG_CONTENT_UPDATED.connect(self._update_log_content)
        self.log_thread_pool = QtCore.QThreadPool()
        self.log_thread_pool.waitForDone()

    def _on_mouse_pressed(self, pos):
        """
        Mouse press event, to be called when the user scrolls by hand or moves
        the cursor manually by pressing somewhere in the log-view area.
        It calls the necessary methods to highlight the search pattern matches
        closest to the current cursor position
        """

        if not self._matches or not self._matches_to_highlight:
            return

        self._update_visible_indices()
        cursor_for_pos = self._content_box.cursorForPosition(pos)
        index = cursor_for_pos.position()
        # pylint: disable=consider-using-enumerate
        for i in range(0, len(self._matches)):
            if index < self._matches[i][0]:
                self._current_match = i
                self._highlight_matches()
                break

    def _load_other_log(self, offset):
        """
        Sets the current log index by adding or subtracting 1 from the current
        index, then triggers reloading the appropriate log file content

        @praram offset: The offset to apply to the current log index
        @type offset: int
        """

        index = max(0, min(self._current_log_index + offset,
                           len(self._log_files) - 1))
        self._current_log_index = index
        self._set_log_file()

    def _set_log_files(self, log_files):
        """
        Sets the log files list. This "slot" is connected to the frame
        selection in FrameMonitorTree

        @param log_files: The log files to display from
        @type log_files: list<str>
        """
        self._log_files = log_files
        self._current_log_index = 0
        self._set_log_file()

    def _set_log_file(self):
        """
        Sets and displays the content of the log file.
        """

        self._clear_search_data()
        self._content_box.setPlainText('')
        self._new_log = True
        self._log_file = self._log_files[self._current_log_index]
        self._display_log_content()

        prev_logs = self._current_log_index < len(self._log_files) - 1
        next_logs = self._current_log_index > 0
        self._prev_log_button.setEnabled(prev_logs)
        self._first_log_button.setEnabled(prev_logs)
        self._next_log_button.setEnabled(next_logs)
        self._last_log_button.setEnabled(next_logs)
        log_index_txt = ('Log %s of %s%s'
                         % (str(self._current_log_index+1),
                            len(self._log_files),
                            (' (current)' if self._current_log_index == 0
                             else '')))
        self._log_index_label.setText(log_index_txt)

    def _set_word_wrap(self, state):
        """
        Sets the word-wrap mode for the log content box, then refreshes the
        content to reflect the change

        @param state: he state to set the word-wrap to
        @type state: int

        @postcondition: The new word-wrap state is implemented, the content is
                        refreshed, all highlights are removed
        """

        self._content_box.setWordWrapMode(QtGui.QTextOption.WordWrap if state
                                          else QtGui.QTextOption.NoWrap)
        self._set_log_file()

    def _move_to_next_match(self):
        """
        Moves the cursor to the next occurrence of search pattern match,
        scrolling up/down through the content to display the cursor position.
        When the cursor is not set and this method is called, the cursor will
        be moved to the first match. Subsequent calls move the cursor through
        the next matches (moving forward). When the cursor is at the last match
        and this method is called, the cursor will be moved back to the first
        match. If there are no matches, this method does nothing.
        """

        if not self._matches:
            return

        if self._current_match >= len(self._matches):
            self._current_match = 0

        self._move_to_match(self._matches[self._current_match][0],
                            self._matches[self._current_match][1])
        self._current_match += 1

    def _move_to_prev_match(self):
        """
        Moves the cursor to the previous occurrence of search pattern match,
        scrolling up/down through the content to display the cursor position.
        When called the first time, it moves the cursor to the last match,
        subsequent calls move the cursor backwards through the matches. When
        the cursor is at the first match and this method is called, the cursor
        will be moved back to the last match
        If there are no matches, this method does nothing.
        """

        if not self._matches:
            return

        if self._current_match < 0:
            self._current_match = len(self._matches) - 1

        self._move_to_match(self._matches[self._current_match][0],
                            self._matches[self._current_match][1])
        self._current_match -= 1

    def _move_to_match(self, pos, length):
        """
        Moves the cursor in the content box to the given pos, then moves it
        forwards by "length" steps, selecting the characters in between

        @param pos: The starting position to move the cursor to
        @type pos: int

        @param length: The number of steps to move+select after the starting
                       index
        @type length: int

        @postcondition: The cursor is moved to pos, the characters between pos
                        and length are selected, and the content is scrolled
                        up/down to ensure the cursor is visible
        """

        self._cursor.setPosition(pos)
        self._cursor.movePosition(QtGui.QTextCursor.Right,
                                  QtGui.QTextCursor.KeepAnchor,
                                  length)
        self._content_box.setTextCursor(self._cursor)
        self._content_box.ensureCursorVisible()
        self._scrollbar_value = self._log_scrollbar.value()
        self._highlight_matches()
        self._matches_label.setText('%d:%d matches'
                                    % (self._current_match + 1,
                                       len(self._matches)))

    def _move_to_search_box(self):
        """
        Case-sensitive checkbox state has changed. Trigger a new search

        @postcondition: All previous search data is cleared, a new search is
                        performed and focus is given to the search box
        """

        self._clear_search_data()
        self._find_text()
        self._search_box.setFocus()

    def _find_text(self):
        """
        Finds and stores the list of text fragments matching the search pattern
        entered in the search box.

        @postcondition: The text matching the search pattern is stored for
                        later access & processing
        """

        if self._new_log:
            return  # Prevent searching while loading a new log file

        prev_search = self._search_text
        self._search_text = self._search_box.text()
        if not self._search_text:  # Nothing to search for, clear search data
            self._clear_search_data()
            return

        search_case_stv = self._case_stv_checkbox.isChecked()
        if self._content_timestamp <= self._search_timestamp:
            if prev_search == self._search_text:  # Same content & pattern
                if self._last_search_case_stv == search_case_stv:
                    self._move_to_next_match()
                    return

        # New Search
        self._clear_search_data()
        self._last_search_case_stv = search_case_stv
        try:
            search_gen = (re.finditer(str(self._search_text),
                                      self._content_box.toPlainText())
                          if search_case_stv else
                          re.finditer(str(self._search_text),
                                      self._content_box.toPlainText(),
                                      re.IGNORECASE))

            for match in search_gen:
                index = match.start()
                length = len(match.group(0))
                self._matches.append((index, length))
            if not self._matches:
                self._matches_label.setStyleSheet('QLabel {color : gray}')
                self._matches_label.setText('No Matches Found')
            self._matches_to_highlight = set(self._matches)
            self._update_visible_indices()
            self._highlight_matches()
            self._search_timestamp = time.time()
            prev_search = self._search_text

            # Start navigating
            self._current_match = 0
            self._move_to_next_match()
        except re.error as err:
            self._matches_label.setText('ERROR: %s' % str(err))
            self._matches_label.setStyleSheet('QLabel {color : indianred}')

    def _highlight_matches(self):
        """
        Highlights the matches closest to the current match
        (current = the one the cursor is at)
        (closest = up to 300 matches before + up to 300 matches after)

        @postcondition: The matches closest to the current match have a new
                        background color (Red)
        """

        if not self._matches_to_highlight or not self._matches:
            return  # nothing to match

        # Update matches around the current one (300 before and 300 after)
        highlight = self._matches[max(self._current_match - 300, 0):
                                  min(self._current_match + 300, len(self._matches))]

        matches = list(set(highlight).intersection(self._matches_to_highlight))
        for match in matches:
            self._highlight_cursor.setPosition(match[0])
            self._highlight_cursor.movePosition(QtGui.QTextCursor.Right,
                                                QtGui.QTextCursor.KeepAnchor,
                                                match[-1])
            self._highlight_cursor.setCharFormat(self._format)

    def _clear_search_text(self):
        """
        Removes the text in the search pattern box

        @postcondition: The text in the search field is removed.
        """

        self._search_box.setText('')
        self._clear_search_data()

    def _clear_search_data(self):
        """
        Removes the text in the search pattern box, clears all highlights and
        stored search data

        @postcondition: The text in the search field is removed, match list is
                        cleared, and format/selection in the main content box
                        are also removed.
        """

        if not self._log_file:
            return

        # find matched text to "unhighlight" red by resetting the char format
        highlight = self._matches[max(self._current_match - 300, 0):
                                  min(self._current_match + 300, len(self._matches))]
        matches = list(set(highlight).intersection(self._matches_to_highlight))

        for match in matches:
            self._highlight_cursor.setPosition(match[0])
            self._highlight_cursor.movePosition(QtGui.QTextCursor.Right,
                                                QtGui.QTextCursor.KeepAnchor,
                                                match[-1])
            self._highlight_cursor.setCharFormat(QtGui.QTextCharFormat())
            self._highlight_cursor.clearSelection()

        # reset text matches
        self._matches = []
        self._matches_to_highlight = set()
        self._search_timestamp = 0
        self._matches_label.setText('')

    def _set_scrollbar_value(self, val):
        """
        Stores the passed value in self._scrollbar_value. This slot is
        connected to the valueChanged event of the main scrollbar, and is used
        for storing the scrollbar value after updating the content box.
        * It also triggers the same actions triggered by pressing the mouse
        somewhere in the content box, (updating)
        """

        self._scrollbar_value = val
        self._on_mouse_pressed(QtCore.QPoint(0, 0))

    def _update_visible_indices(self):
        """
        Updates the stored first & last visible text content indices so we
        can focus operations like highlighting on text that is visible

        @postcondition: The _first_visible_index & _last_visible_index are
                        up to date (in sync with the current viewport)
        """

        viewport = self._content_box.viewport()
        try:
            top_left = QtCore.QPoint(0, 0)
            bottom_right = QtCore.QPoint(viewport.width() - 1,
                                         viewport.height() - 1)
            first = self._content_box.cursorForPosition(top_left).position()
            last = self._content_box.cursorForPosition(bottom_right).position()
            self._first_visible_index = first
            self._last_visible_index = last
        except IndexError:  # When there's nothing in the content box
            pass

    def _display_log_content(self):
        """
        Displays the log file content in the TextEdit field, and schedules the
        next run of the update method

        @postcondition: The _update_log method is scheduled to run again
                        after 5 seconds
        """
        log_reader = LogReader(self._log_file)

        try:
            if log_reader.exists() is not True:
                self._log_file_exists = False
                content = 'Log file does not exist: %s' % self._log_file
                self._content_timestamp = time.time()
                self._update_log_content(content, self._log_mtime)
            else:
                # Creating the load logs process as qrunnables so
                # that they don't block the ui while loading
                log_loader = LogLoader(self._load_log, log_reader,
                                       self._new_log, self._log_mtime)
                log_loader.signals.SIG_LOG_LOAD_RESULT.connect(self._receive_log_results)
                log_loader.setAutoDelete(True)
                self.log_thread_pool.start(log_loader)
                self.log_thread_pool.waitForDone()
                self._new_log = False
        finally:
            QtCore.QTimer.singleShot(5000, self._display_log_content)

    @QtCore.Slot()
    def _load_log(self, log_reader, new_log, curr_log_mtime):
        content = None
        log_size = log_reader.size()
        if log_size > 1 * 1e6:
            content = ('Log file size (%0.1f MB) exceeds the size '
                       'threshold (1.0 MB).'
                       % float(log_size / (1024 * 1024)))
        elif not new_log and log_reader.exists():
            log_mtime = log_reader.getMtime()
            if log_mtime > curr_log_mtime:
                curr_log_mtime = log_mtime  # no new updates
                content = ''

        if content is None:
            content = ''
            try:
                content = log_reader.read()
            except IOError:
                content = 'Can not access log file: %s' % log_reader.filepath

        return content, curr_log_mtime

    @QtCore.Slot()
    def _receive_log_results(self, content, log_mtime):
        self.SIG_CONTENT_UPDATED.emit(content, log_mtime)

    @QtCore.Slot(str, str)
    def _update_log_content(self, content, log_mtime):
        """
        Updates the content of the content box with the content of the log
        file, if necessary. The full path to the log file will be populated in
        the "log path" field.
        If the log file isn't online, or couldn't be read for any reason,
        a warning message will be displayed in the content box.
        If the log file was not modified since the last time this plugin read
        it, this method will do nothing.
        By default, the cursor will automatically be moved to the end of the
        content and the scrollbar value will be adjusted to ensure the cursor
        is visible. However, if the content was previously scrolled up (the
        cursor is not at the end of the content), this method will adjust the
        slider size to ensure user-set value of the scrollbar is maintained.

        @postcondition: The content of the log file is displayed in the content
                        box, and the content is scrolled to the end,
                        (if necessary)
        """

        self._log_mtime = log_mtime

        self.app.processEvents()

        # Update the content in the gui (if necessary)
        if self._new_log:
            self._content_box.setPlainText(content)
        else:
            current_text = (self._content_box.toPlainText() or '')

            # ignore decoding higher order bytes outside ordinal range(128)
            # ex: umlats, latin-1 etc.
            try:
                content = content.decode("utf-8", errors="ignore")
                current_text = current_text.decode("utf-8", errors="ignore")
            except AttributeError:
                pass
            new_text = content.lstrip(str(current_text))
            if new_text:
                self._content_box.appendPlainText(new_text)
        self._content_timestamp = time.time()
        self._path.setText(self._log_file)

        scroll_to_end = (self._scrollbar_max == self._scrollbar_value
                         or self._new_log)

        # Adjust scrollbar value (if necessary)
        self._scrollbar_max = self._log_scrollbar.maximum()
        val = self._scrollbar_max if scroll_to_end else self._scrollbar_value
        self._log_scrollbar.setValue(val)
        self._scrollbar_value = self._log_scrollbar.value()


class LogViewPlugin(cuegui.AbstractDockWidget.AbstractDockWidget):
    """
    Plugin for displaying the log file content for the selected frame with
    the ability to perform regex-based search.
    """

    def __init__(self, parent=None):
        """
        Create a LogViewPlugin instance

        @param parent: The parent widget
        @type parent: QtWidgets.QWidget or None
        """
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(
            self, parent, PLUGIN_NAME, QtCore.Qt.RightDockWidgetArea)
        self.logview_widget = LogViewWidget(self)
        self.layout().addWidget(self.logview_widget)


class Highlighter(QtGui.QSyntaxHighlighter):
    """Color-codes log text according to log content."""

    def __init__(self, parent=None):
        super(Highlighter, self).__init__(parent)

        self.on = True

        self.timeFormat = QtGui.QTextCharFormat()
        self.timeFormat.setFontWeight(QtGui.QFont.Bold)
        self.timeFormat.setForeground(cuegui.Style.ColorTheme.LOG_TIME)

        self.errorFormat = QtGui.QTextCharFormat()
        self.errorFormat.setFontWeight(QtGui.QFont.Bold)
        self.errorFormat.setForeground(cuegui.Style.ColorTheme.LOG_ERROR)

        self.warnFormat = QtGui.QTextCharFormat()
        self.warnFormat.setFontWeight(QtGui.QFont.Bold)
        self.warnFormat.setForeground(cuegui.Style.ColorTheme.LOG_WARNING)

        self.infoFormat = QtGui.QTextCharFormat()
        self.infoFormat.setFontWeight(QtGui.QFont.Bold)
        self.infoFormat.setForeground(cuegui.Style.ColorTheme.LOG_INFO)

        self.completeFormat = QtGui.QTextCharFormat()
        self.completeFormat.setFontWeight(QtGui.QFont.Bold)
        self.completeFormat.setForeground(cuegui.Style.ColorTheme.LOG_COMPLETE)

    def highlightBlock(self, text):
        """Handle blocks that should be highlighted"""
        if not self.on:
            return

        line = text.lower()
        done = False

        for error in cuegui.Constants.LOG_HIGHLIGHT_ERROR:
            if error in line:
                self.setFormat(0, len(text), self.errorFormat)
                done = True
                break

        if not done:
            for warn in cuegui.Constants.LOG_HIGHLIGHT_WARN:
                if warn in line:
                    self.setFormat(0, len(text), self.warnFormat)
                    done = True
                    break

        if not done:
            for info in cuegui.Constants.LOG_HIGHLIGHT_INFO:
                if info in line:
                    self.setFormat(0, len(text), self.infoFormat)
                    done = True
                    break

        if 'alf_progress' in line:
            sidx = line.index('alf_progress')
            eidx = line.index('%')
            self.setFormat(sidx, eidx + 1, self.infoFormat)

        if ' | ' in line:
            idx = line.index(' | ')
            self.setFormat(0, idx, self.timeFormat)

        if 'render job complete' in line:
            self.setFormat(0, len(text), self.completeFormat)

        self.setCurrentBlockState(0)
