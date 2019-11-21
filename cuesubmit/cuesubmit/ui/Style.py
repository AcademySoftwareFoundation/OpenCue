from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from PySide2 import QtGui


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
    border: 1px;
    font-size: 10px;
    padding: 5px 35px 5px 35px;
}

QToolButton[accessibleName="editLayer"] {
    font-size: 16px;
    font-weight: bold;
}

QToolButton:pressed {
    background-color: rgb(120, 130, 140);
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

SEPARATOR_LINE = 'border: 1px solid rgb(20, 30, 40)'

TEXT = 'background-color: rgb(40, 50, 60); color: rgb(250, 250, 250); font-weight: regular;'

TOGGLE_DEFAULT = 'background-color: rgb(75, 75, 75); border-radius: 8px; padding-bottom: 3px;'
TOGGLE_ENABLED = 'background-color: rgb(20, 160, 200); border-radius: 8px; padding-bottom: 3px;'

UNDERLINE = 'background-color: rgb(120, 120, 120);'
UNDERLINE_HIGHLIGHT = 'background-color: rgb(10, 90, 240);'


def setFont(font):
    """sets the application font"""
    global Font
    Font = font
    QtGui.qApp.setFont(font)


def init():
    """initialize the global style settings"""
    setFont(DEFAULT_FONT)
