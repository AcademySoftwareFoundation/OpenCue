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


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
import pickle

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Utils


PREDEFINED_COMMENT_HEADER = "Use a Predefined Comment:"
PREDEFINED_COMMENT_ADD = "> Add predefined comment"
PREDEFINED_COMMENT_EDIT = "> Edit predefined comment"
PREDEFINED_COMMENT_DELETE = "> Delete predefined comment"

SAVE_EDIT = "Save Changes"
SAVE_NEW = "Save New Comment"


class CommentListDialog(QtWidgets.QDialog):
    """A dialog to display a comment list"""
    def __init__(self, source, parent=None):
        """Initialize the dialog
        @type  source: Job or Host
        @param source: The source to get the comments from
        @type  parent: QWidget
        @param parent: The dialog's parent"""
        QtWidgets.QDialog.__init__(self, parent)
        self.__source = source

        self.__labelTitle = QtWidgets.QLabel(self.__source.data.name, self)

        self.__splitter = QtWidgets.QSplitter(self)
        self.__splitter.setOrientation(QtCore.Qt.Vertical)

        self.__treeSubjects = QtWidgets.QTreeWidget(self)
        self.__textSubject = QtWidgets.QLineEdit(self)
        self.__textMessage = QtWidgets.QTextEdit(self)

        self.__comboMacro = QtWidgets.QComboBox(self)
        self.__btnNew = QtWidgets.QPushButton("New", self)
        self.__btnSave = QtWidgets.QPushButton(SAVE_EDIT, self)
        self.__btnDel = QtWidgets.QPushButton("Delete", self)
        self.__btnClose = QtWidgets.QPushButton("Close", self)

        self.setWindowTitle("Comments")
        self.resize(600, 300)
        self.__btnNew.setDefault(True)
        self.__treeSubjects.setHeaderLabels(["Subject", "User", "Date"])

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.__labelTitle)

        self.__splitter.addWidget(self.__treeSubjects)

        self.__group = QtWidgets.QGroupBox(self.__splitter)
        glayout = QtWidgets.QVBoxLayout()
        glayout.addWidget(self.__textSubject)
        glayout.addWidget(self.__textMessage)
        self.__group.setLayout(glayout)

        layout.addWidget(self.__splitter)

        btnLayout = QtWidgets.QHBoxLayout()
        btnLayout.addWidget(self.__comboMacro)
        btnLayout.addStretch()
        btnLayout.addWidget(self.__btnSave)
        btnLayout.addWidget(self.__btnNew)
        btnLayout.addWidget(self.__btnDel)
        btnLayout.addWidget(self.__btnClose)
        layout.addLayout(btnLayout)

        self.__treeSubjects.itemSelectionChanged.connect(self.__itemChanged)
        self.__comboMacro.currentTextChanged.connect(self.__macroHandle)
        self.__btnSave.pressed.connect(self.__saveComment)
        self.__btnDel.pressed.connect(self.__deleteSelectedComment)
        self.__btnNew.pressed.connect(self.__createNewComment)
        self.__btnClose.pressed.connect(self.__close)
        self.__textSubject.textEdited.connect(self.__textEdited)
        self.__textMessage.textChanged.connect(self.__textEdited)

        self.refreshComments()
        self.__macroLoad()

    def __textEdited(self, text=None):
        """Called when the text boxes are modified, enables the save button"""
        self.__btnSave.setEnabled(True)

    def __close(self):
        if self.__btnSave.isEnabled():
            if cuegui.Utils.questionBoxYesNo(self,
                                      "Save Changes?",
                                      "Do you want to save your changes?"):
                self.__saveComment()
        self.close()

    def __saveComment(self):
        """Saves the new or selected comment"""
        if self.__btnSave.text() == SAVE_NEW:
            # If saving a new comment
            self.__addComment(self.__textSubject.text(),
                              self.__textMessage.toPlainText())
            self.refreshComments()
        else:
            # If saving a modified comment
            if self.__treeSubjects.currentItem():
                comment = self.__treeSubjects.currentItem().getInstance()
                comment.setSubject(str(self.__textSubject.text()))
                comment.setMessage(str(self.__textMessage.toPlainText()))
                self.__treeSubjects.currentItem().getInstance().save()
                self.refreshComments()

    def __createNewComment(self):
        """Clears the dialog to create a new comment"""
        if not self.__treeSubjects.selectedItems() and \
           self.__textSubject.text() and \
           not self.__textMessage.toPlainText():
            self.__textMessage.setFocus(QtCore.Qt.OtherFocusReason)
        else:
            self.__textSubject.setText("")
            self.__textMessage.setText("")
            self.__textSubject.setReadOnly(False)
            self.__textMessage.setReadOnly(False)
            self.__textSubject.setFocus(QtCore.Qt.OtherFocusReason)
            self.__treeSubjects.clearSelection()
            self.__btnSave.setText(SAVE_NEW)
            self.__btnSave.setEnabled(False)
            self.__btnDel.setEnabled(False)

    def __itemChanged(self):
        """when the current item changes this sets the bottom view and current
        item"""
        if self.__treeSubjects.selectedItems():
            item = self.__treeSubjects.selectedItems()[0]

            if item.getInstance().user != cuegui.Utils.getUsername():
                self.__textSubject.setReadOnly(True)
                self.__textMessage.setReadOnly(True)
            else:
                self.__textSubject.setReadOnly(False)
                self.__textMessage.setReadOnly(False)

            self.__textSubject.setText(item.getInstance().subject())
            self.__textMessage.setText(item.getInstance().message())
            self.__treeSubjects.setCurrentItem(item)
            self.__btnSave.setText(SAVE_EDIT)
            self.__btnSave.setEnabled(False)
            self.__btnDel.setEnabled(True)
        else:
            self.__createNewComment()

    def __deleteSelectedComment(self):
        """Deletes the currently selected comment"""
        if not self.__treeSubjects.selectedItems():
            return
        if cuegui.Utils.questionBoxYesNo(self,
                                  "Confirm Delete",
                                  "Delete the selected comment?"):
            for item in self.__treeSubjects.selectedItems():
                item.getInstance().delete()
                self.__treeSubjects.takeTopLevelItem(self.__treeSubjects.indexOfTopLevelItem(item))

    def refreshComments(self):
        """Clears and populates the comment list from the cuebot"""
        comments = self.__source.getComments()
        self.__treeSubjects.clear()
        for comment in comments:
            item = Comment(comment)
            item.setSizeHint(0, QtCore.QSize(300, 1))
            self.__treeSubjects.addTopLevelItem(item)
        self.__treeSubjects.resizeColumnToContents(0)
        last_item = self.__treeSubjects.topLevelItem(len(comments) - 1)
        if last_item:
            self.__btnSave.setText(SAVE_EDIT)
            self.__btnSave.setEnabled(False)
            last_item.setSelected(True)
        else:
            self.__createNewComment()

    def __macroLoad(self):
        """Loads the defined comment macros from settings"""
        self.__macroList = pickle.loads(
            str(QtGui.qApp.settings.value("Comments", pickle.dumps({}))))
        self.__macroRefresh()

    def __macroRefresh(self):
        """Updates the combo box with the current comment macros"""
        self.__comboMacro.clear()
        self.__comboMacro.addItems([PREDEFINED_COMMENT_HEADER] +
                                   sorted(self.__macroList.keys()) +
                                   [PREDEFINED_COMMENT_ADD,
                                    PREDEFINED_COMMENT_EDIT,
                                    PREDEFINED_COMMENT_DELETE])

    def __macroSave(self):
        """Saves the current comment macros to settings"""
        QtGui.qApp.settings.setValue("Comments", pickle.dumps(self.__macroList))

    def __macroHandle(self, selection):
        """Called when the comment macro combo box is selected
        @type  selection: str
        @param selection: The text of the selected item"""
        self.__comboMacro.setCurrentIndex(0)
        selection = str(selection)

        if selection in self.__macroList:
            self.__addComment(self.__macroList[selection][0],
                              self.__macroList[selection][1])
            self.refreshComments()
            self.__treeSubjects.setFocus(QtCore.Qt.OtherFocusReason)

        elif selection == PREDEFINED_COMMENT_ADD:
            commentMacroDialog = CommentMacroDialog("", "", "", self)
            if commentMacroDialog.exec_():
                (name, subject, message) = list(commentMacroDialog.values())
                self.__macroList[name] = [subject, message]
                self.__macroSave()
                self.__macroRefresh()

        elif selection == PREDEFINED_COMMENT_DELETE:
            (comment, choice) = self.__macroSelectDialog("delete")
            if choice:
                if comment in self.__macroList:
                    del self.__macroList[comment]
                    self.__macroSave()
                    self.__macroRefresh()

        elif selection == PREDEFINED_COMMENT_EDIT:
            (comment, choice) = self.__macroSelectDialog("edit")
            if choice:
                if comment in self.__macroList:
                    commentMacroDialog = CommentMacroDialog(comment,
                                                            self.__macroList[comment][0],
                                                            self.__macroList[comment][1],
                                                            self)
                    if commentMacroDialog.exec_():
                        (name, subject, message) = list(commentMacroDialog.values())

                        if name != comment:
                            del self.__macroList[comment]

                        self.__macroList[name] = [subject, message]
                        self.__macroSave()
                        self.__macroRefresh()

    def __macroSelectDialog(self, action):
        """Creates a dialog where the user can select what predefined comment to
        act on.
        @type  action: str
        @param action: The action that will be performed on the comment, such as
                       "edit" or "delete"
        @rtype:  tuple(str, bool)
        @return: The results from the dialog"""
        result = QtWidgets.QInputDialog.getItem(
            self,
            "%s a predefined comment" % action.title(),
            "Please select the predefined comment to %s:" % action.lower(),
            sorted(self.__macroList.keys()),
            0,
            False)
        return (str(result[0]), result[1])

    def __addComment(self, subject, message):
        self.__source.addComment(str(subject), str(message) or " ")


class CommentMacroDialog(QtWidgets.QDialog):
    """A dialog for adding or modifying macro comments"""
    def __init__(self, name="", subject="", message="", parent=None):
        """Initializes the new/edit comment dialog
        @type  name: str
        @param name: The name of the macro
        @type  subject: str
        @param subject: The subject of the macro
        @type  name: str
        @param name: The message of the macro
        @type  parent: QWidget
        @param parent: The dialog's parent"""
        QtWidgets.QDialog.__init__(self, parent)

        self.__textName = QtWidgets.QLineEdit(name, self)
        self.__textSubject = QtWidgets.QLineEdit(subject, self)
        self.__textMessage = QtWidgets.QTextEdit(message, self)

        self.__btnSave = QtWidgets.QPushButton("Apply", self)
        self.__btnCancel = QtWidgets.QPushButton("Cancel", self)

        self.setWindowTitle("Add/Modify Comment Macro")
        self.resize(450, 225)

        btnLayout = QtWidgets.QHBoxLayout()
        btnLayout.addStretch()
        btnLayout.addWidget(self.__btnSave)
        btnLayout.addWidget(self.__btnCancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Name:", self))
        layout.addWidget(self.__textName)
        layout.addWidget(QtWidgets.QLabel("Subject:", self))
        layout.addWidget(self.__textSubject)
        layout.addWidget(QtWidgets.QLabel("Message:", self))
        layout.addWidget(self.__textMessage)
        layout.addLayout(btnLayout)

        self.__btnSave.pressed.connect(self.__save)
        self.__btnCancel.pressed.connect(self.reject)

    def __save(self):
        """Validates and then exits from the dialog in success"""
        if list(self.values())[0] != "" and \
           list(self.values())[1] != "" and \
           list(self.values())[0] not in (PREDEFINED_COMMENT_HEADER,
                                    PREDEFINED_COMMENT_ADD,
                                    PREDEFINED_COMMENT_EDIT,
                                    PREDEFINED_COMMENT_DELETE):
            self.accept()

    def values(self):
        """Returns the entered values
        @rtype:  tuple(str, str, str)
        @return: (name, subject, message)"""
        return (str(self.__textName.text()),
                str(self.__textSubject.text()),
                str(self.__textMessage.toPlainText()))


class Comment(QtWidgets.QTreeWidgetItem):
    """A widget to represent an item in the comment list"""
    def __init__(self, comment):
        QtWidgets.QTreeWidgetItem.__init__(
            self,
            [comment.subject(),
             comment.user(),
             cuegui.Utils.dateToMMDDHHMM(comment.timestamp())])
        self.__comment = comment

    def getInstance(self):
        """returns the actual comment instance this widget is displaying"""
        return self.__comment
