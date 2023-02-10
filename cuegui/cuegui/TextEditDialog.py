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


"""A TextEdit dialog."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from qtpy import QtCore
from qtpy import QtWidgets


class TextEditDialog(QtWidgets.QDialog):
    """A TextEdit dialog."""

    def __init__(self, title, text, default="", parent=None):
        """
        @type  title: string
        @param title: The title for the confirmation dialog
        @type  text: string
        @param text: The text to display
        @type  parent: QObject
        @param parent: The parent for this object"""
        QtWidgets.QDialog.__init__(self, parent)

        __btn_accept = QtWidgets.QPushButton("Ok", self)
        __btn_cancel = QtWidgets.QPushButton("Cancel", self)
        __label_text = QtWidgets.QLabel(text, self)
        __label_text.setWordWrap(True)

        __vlayout = QtWidgets.QVBoxLayout(self)
        __vlayout.addWidget(__label_text)

        self.__textEdit = QtWidgets.QTextEdit(self)
        __vlayout.addWidget(self.__textEdit)

        __hlayout = QtWidgets.QHBoxLayout()
        __hlayout.addWidget(__btn_accept)
        __hlayout.addWidget(__btn_cancel)
        __vlayout.addLayout(__hlayout)

        self.setSizeGripEnabled(True)
        self.setMaximumSize(400,300)
        self.setWindowTitle(title)

        # pylint: disable=no-member
        __btn_accept.clicked.connect(self.accept)
        __btn_cancel.clicked.connect(self.reject)
        # pylint: enable=no-member

        self.__textEdit.setText(default)
        self.__textEdit.setFocus(QtCore.Qt.OtherFocusReason)

    def results(self):
        """Gets the dialog results as plaintext."""
        return self.__textEdit.toPlainText()
