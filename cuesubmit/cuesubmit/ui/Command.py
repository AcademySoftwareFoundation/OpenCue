from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from PySide2 import QtCore, QtWidgets

from cuesubmit.ui import Widgets


class CueCommandWidget(Widgets.CueHelpWidget):
    """Help Widget that contains a text box for entering a
    shell command.
    """

    helpText = 'Enter a shell command to run'
    textChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(CueCommandWidget, self).__init__(parent)
        self.commandTextBox = CueCommandTextBox(None)
        self.contentLayout.addWidget(self.commandTextBox)
        self.setupConnections()

    def setupConnections(self):
        self.commandTextBox.commandBox.textChanged.connect(self.textChanged.emit)

    def setText(self, text):
        """Set the given text to the command box
        @type text: str
        @param text: text string to set the command box to.
        """
        self.commandTextBox.commandBox.setText(text)

    def text(self):
        """Return the current text from the commandBox
        @rtype: str
        @return: text
        """
        return self.commandTextBox.commandBox.toPlainText()


class CueCommandTextBox(QtWidgets.QWidget):
    """Widget that contains a label and text box for entering commands."""

    def __init__(self, *args, **kwargs):
        super(CueCommandTextBox, self).__init__(*args, **kwargs)
        self.mainLayout = QtWidgets.QGridLayout()
        self.mainLayout.setVerticalSpacing(1)
        self.label = QtWidgets.QLabel('Command To Run:')
        self.label.setAlignment(QtCore.Qt.AlignLeft)
        self.commandBox = QtWidgets.QTextEdit()
        self.commandBox.setAccessibleName('commandBox')
        self.horizontalLine = Widgets.CueHLine()
        self.setFixedHeight(120)
        self.commandBox.setToolTip('Enter the command to be run. Valid replacement tokens are:\n'
                                   ' #IFRAME# -- frame number\n'
                                   ' #LAYER# -- layer name\n'
                                   ' #JOB# -- job name\n'
                                   ' #FRAME# -- frame name')
        self.setupUi()

    def setupUi(self):
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.label, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.commandBox, 1, 0, 1, 4)
        self.mainLayout.addWidget(self.horizontalLine, 2, 0, 1, 4)
