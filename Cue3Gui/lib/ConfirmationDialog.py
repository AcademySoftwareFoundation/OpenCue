#  Copyright (c) 2018 Sony Pictures Imageworks Inc.
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


"""
A confirmation dialog
"""
from Manifest import os, QtCore, QtGui, Cue3

import Utils

class ConfirmationDialog(QtGui.QDialog):
    def __init__(self, title, text, items = [], parent = None):
        """A confirmation dialog
        @type  title: string
        @param title: The title for the confirmation dialog
        @type  text: string
        @param text: The text to display
        @type  items: list<string>
        @param items: Optional, a list of items, such as job names that will be
                      acted on
        @type  parent: QObject
        @param parent: The parent for this object"""
        QtGui.QDialog.__init__(self, parent)

        __btn_accept = QtGui.QPushButton("Ok", self)
        __btn_cancel = QtGui.QPushButton("Cancel", self)
        __label_text = QtGui.QLabel(text, self)
        __label_text.setWordWrap(True)
        __icon = QtGui.QLabel(self)
        __icon.setPixmap(QtGui.QIcon(":warning.png").pixmap(30, 30))

        layout = QtGui.QHBoxLayout(self)
        layout.addWidget(__icon)
        # Alignment is not correct unless done using setAlignment
        layout.setAlignment(__icon, QtCore.Qt.AlignTop)

        __vlayout = QtGui.QVBoxLayout()
        __vlayout.addWidget(__label_text)
        layout.addLayout(__vlayout)

        if items:
            __list_items = QtGui.QListWidget(self)
            __list_items.addItems(items)
            __list_items.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
            __vlayout.addWidget(__list_items)

        __hlayout = QtGui.QHBoxLayout()
        __hlayout.addWidget(__btn_accept)
        __hlayout.addWidget(__btn_cancel)
        __vlayout.addLayout(__hlayout)

        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setSizeGripEnabled(True)
        self.setMaximumSize(400,300)
        self.setWindowTitle(title)

        QtCore.QObject.connect(__btn_accept,
                               QtCore.SIGNAL('clicked()'),
                               self.accept)
        QtCore.QObject.connect(__btn_cancel,
                               QtCore.SIGNAL('clicked()'),
                               self.reject)
