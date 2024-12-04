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


"""Help Widget that contains a text box for entering a shell command."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from qtpy import QtCore, QtWidgets

from cuesubmit.ui import Widgets
from cuesubmit import Constants


class CueCommandWidget(Widgets.CueHelpWidget):
    """Help Widget that contains a text box for entering a shell command."""

    helpText = 'Enter a shell command to run'
    textChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super(CueCommandWidget, self).__init__(parent)
        self.commandTextBox = CueCommandTextBox(None)
        self.contentLayout.addWidget(self.commandTextBox)
        self.signals = [self.textChanged]
        self.getter = self.text
        self.setter = self.setText
        self.setupConnections()

    def setupConnections(self):
        """Sets up widget signals."""
        self.commandTextBox.commandBox.textChanged.connect(self.textChanged.emit)  # pylint: disable=no-member

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
        tokensToolTip = '\n'.join([' {0} -- {1}'.format(token, info)
                                   for token, info in Constants.COMMAND_TOKENS.items()])
        self.commandBox.setToolTip('Enter the command to be run. Valid replacement tokens are:\n'
                                   + tokensToolTip)
        self.setupUi()

    def setupUi(self):
        """Creates the widget layout."""
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.label, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.commandBox, 1, 0, 1, 4)
        self.mainLayout.addWidget(self.horizontalLine, 2, 0, 1, 4)
