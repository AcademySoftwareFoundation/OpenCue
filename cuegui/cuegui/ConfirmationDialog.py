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


"""Confirmation dialog."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets


class ConfirmationDialog(QtWidgets.QDialog):
    """Confirmation dialog."""

    # pylint: disable=dangerous-default-value
    def __init__(self, title, text, items=[], parent=None):
        """
        @type  title: string
        @param title: The title for the confirmation dialog
        @type  text: string
        @param text: The text to display
        @type  items: list<string>
        @param items: Optional, a list of items, such as job names that will be
                      acted on
        @type  parent: QObject
        @param parent: The parent for this object"""
        QtWidgets.QDialog.__init__(self, parent)

        __btn_accept = QtWidgets.QPushButton("Ok", self)
        __btn_cancel = QtWidgets.QPushButton("Cancel", self)
        __label_text = QtWidgets.QLabel(text, self)
        __label_text.setWordWrap(True)
        __icon = QtWidgets.QLabel(self)
        __icon.setPixmap(QtGui.QIcon(":warning.png").pixmap(30, 30))

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(__icon)
        # Alignment is not correct unless done using setAlignment
        layout.setAlignment(__icon, QtCore.Qt.AlignTop)

        __vlayout = QtWidgets.QVBoxLayout()
        __vlayout.addWidget(__label_text)
        layout.addLayout(__vlayout)

        if items:
            __list_items = QtWidgets.QListWidget(self)
            __list_items.addItems(items)
            __list_items.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
            __vlayout.addWidget(__list_items)

        __hlayout = QtWidgets.QHBoxLayout()
        __hlayout.addWidget(__btn_accept)
        __hlayout.addWidget(__btn_cancel)
        __vlayout.addLayout(__hlayout)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setMaximumSize(400,300)
        self.setWindowTitle(title)

        # pylint: disable=no-member
        __btn_accept.clicked.connect(self.accept)
        __btn_cancel.clicked.connect(self.reject)
        # pylint: enable=no-member
