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


"""Widget styling information."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from qtpy import QtGui


MAIN_WINDOW = """

QWidget {
    background-color: rgb(40, 50, 60);
    color: rgb(200, 200, 200);
}

QScrollBar:vertical {
    width: 14px;
    margin: 12px 0 -12px 0;
}

QScrollBar::handle:vertical {
    background: rgb(60, 70, 80);
    margin: 0 0 24px 0;
}

QFrame[accessibleName="horizontalLine"] {
    color: black;
    border: 2px solid rgb(20, 30, 40);
}

QLabel {
    background-color: rgb(40, 50, 60);
    color: rgb(160, 160, 160);
    font-weight: regular;
    font-size: 10pt;
}

QLineEdit {
    color: rgb(220, 220, 220);
    border: 0px solid;
    background-color: rgb(60, 70, 80);
    border-radius: 4px;
}

QPushButton {
    background-color: rgb(60, 70, 80);
    border-radius: 3px;
    border: 0px;
    font-size: 10px;
    padding: 5px 35px 5px 35px;
}

QPushButton[accessibleName="helpButton"] {
    padding: 0px;
}

QPushButton:pressed {
    background-color: rgb(120, 130, 140);
}

QScrollBar {
    background-color: rgb(90, 100, 110);
    color: rgb(40, 50, 60);
    border-radius: 2px;
    width: 10px
}

QScrollBar::handle {
    background-color: rgb(40, 50, 60);
    border-radius: 3px;
    max-height: 10px;
}

QTextEdit {
    background-color: rgb(60, 70, 80);
    border: 0px;
    border-radius: 3px;
    padding-left: 5px;
}

QTextEdit[accessibleName="commandBox"] {
    font-family: Courier New;
}

QToolButton {
    background-color: rgb(60, 70, 80);
    border-radius: 3px;
    border: 2px solid transparent;
    font-size: 10px;
    padding: 5px 35px 5px 35px;
}

QToolButton[accessibleName="editLayer"] {
    font-size: 16px;
    font-weight: bold;
}

QToolButton:hover, QToolButton:focus {
    background-color: rgb(80, 90, 100);
    border-color: rgb(30, 40, 50);
}

QToolButton:pressed {
    background-color: rgb(60, 70, 80);
    border-color: rgb(30, 40, 50);
}

QToolButton::menu-indicator {
    bottom: 7px;
    right: 7px;
}

QTreeView {
    border: 2px solid rgb(20, 30, 40);
}

QHeaderView {
    background-color: rgb(20, 30, 40);
}

"""

DEFAULT_FONT = 'Luxi Sans'

HELP_TEXT_FIELD = """
QTextEdit {
    background-color: rgb(70, 80, 90);
    color: rgb(150, 150, 150);
    font-size: 10pt;
    margin: 5px 40px 5px 15px;
}
"""

POPUP_LIST_VIEW = """
    background-color: rgb(70, 80, 90);
"""

INVALID_TEXT = """
QLabel {
    color: rgb(220, 20, 20);
    background-color: rgb(40, 50, 60);
    font-weight: bold;
    font-size: 10pt
}
"""

LABEL_TEXT = """
QLabel {
    background-color: rgb(40, 50, 60);
    color: rgb(160, 160, 160);
    font-weight: regular;
    font-size: 10pt;
}
"""

LINE_EDIT = """
QLineEdit {
    color: rgb(220, 220, 220);
    border: 0px solid;
    background-color: rgb(60, 70, 80);
    border-radius: 4px;
}
"""

HEADER_VIEW = """
QHeaderView::section {
    background-color: rgb(31, 40, 48);
    color: white;
    padding-left: 4px;
    border: 1px solid rgb(46, 56, 63);
    border-bottom-color: rgb(25, 34, 42);
    border-right-color: rgb(25, 34, 42);
    font-size: 10pt;
    height: 16px;
}
"""

TREE_VIEW = """
QTreeView {
    show-decoration-selected: 1;
}

QTreeView::item {
    color: white;
    height: 20px;
}

QTreeView::item:hover {
    background: rgb(32, 85, 123);
}
QTreeView::item:selected {
    background: rgb(52, 139, 200);
}
QTreeView::branch:hover:!has-children:!selected {
    background: rgb(32, 85, 123);
}
QTreeView::branch:selected {
    background: rgb(52, 139, 200);
}
QTreeView::branch:open:has-children {
    border-image: none;
}
QTreeView::branch:closed:has-children {
    border-image: none;
}
"""

PULLDOWN_LIST = """
QMenu {
    color: rgb(200, 200, 200);
    border: 0px solid  rgb(30, 40, 50);
    border-bottom: 1px solid  rgb(30, 40, 50);
    border-left: 1px solid qlineargradient(
                                x1: 0, y1: 0,
                                x2: 0, y2: 1,
                                stop: 0 transparent, stop: 1 rgb(30, 40, 50));
    border-right: 1px solid qlineargradient(
                                x1: 0, y1: 0,
                                x2: 0, y2: 1,
                                stop: 0 transparent, stop: 1 rgb(30, 40, 50));
}

QMenu::item:selected {
    background-color: rgb(30, 40, 50);
}
"""

DISABLED_LINE_EDIT = """
QLineEdit {
    color: rgb(110, 110, 110);
    border: 0px solid;
    background-color: rgb(30, 35, 40);
    border-radius: 4px;
}
"""

GROUP_BOX = """
QGroupBox {
    border: 3px solid rgb(30, 40, 50);
    border-radius: 6px;
    font-size: 8pt;
}
"""

SEPARATOR_LINE = 'border: 1px solid rgb(20, 30, 40)'

TEXT = 'background-color: rgb(40, 50, 60); color: rgb(250, 250, 250); font-weight: regular;'

TOGGLE_DEFAULT = 'background-color: rgb(75, 75, 75); border-radius: 8px; padding-bottom: 3px;'
TOGGLE_ENABLED = 'background-color: rgb(20, 160, 200); border-radius: 8px; padding-bottom: 3px;'

UNDERLINE = 'background-color: rgb(120, 120, 120);'
UNDERLINE_HIGHLIGHT = 'background-color: rgb(10, 90, 240);'


# pylint: disable=global-variable-undefined
def setFont(font):
    """sets the application font"""
    global Font
    Font = font
    # pylint: disable=no-member
    QtGui.qApp.setFont(font)
    # pylint: enable=no-member


def init():
    """initialize the global style settings"""
    setFont(DEFAULT_FONT)
