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


"""Dialog for displaying a comment list."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import str
import pickle

from qtpy import QtCore
from qtpy import QtWidgets

import cuegui.Utils


PREDEFINED_COMMENT_HEADER = "Use a Predefined Comment:"
PREDEFINED_COMMENT_ADD = "> Add predefined comment"
PREDEFINED_COMMENT_EDIT = "> Edit predefined comment"
PREDEFINED_COMMENT_DELETE = "> Delete predefined comment"

SAVE_EDIT = "Save Changes"
SAVE_NEW = "Save New Comment"


class CommentListDialog(QtWidgets.QDialog):
    """Dialog for displaying a comment list."""

    def __init__(self, source, parent=None):
        """Initialize the dialog.
        @type  source: List of Jobs or Hosts
        @param source: The source to get the comments from
        @type  parent: QWidget
        @param parent: The dialog's parent"""
        QtWidgets.QDialog.__init__(self, parent)
        self.app = cuegui.app()

        self.__source = source

        self.__splitter = QtWidgets.QSplitter(self)
        self.__splitter.setOrientation(QtCore.Qt.Vertical)

        self.__treeSubjects = QtWidgets.QTreeWidget(self)
        self.__treeSubjects.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.__textSubject = QtWidgets.QLineEdit(self)
        self.__textMessage = QtWidgets.QTextEdit(self)

        self.__comboMacro = QtWidgets.QComboBox(self)
        self.__btnNew = QtWidgets.QPushButton("New", self)
        self.__btnSave = QtWidgets.QPushButton(SAVE_EDIT, self)
        self.__btnDel = QtWidgets.QPushButton("Delete", self)
        self.__btnClose = QtWidgets.QPushButton("Close", self)

        self.setWindowTitle("Comments")
        self.resize(800, 400)
        self.__btnNew.setDefault(True)
        self.__treeSubjects.setHeaderLabels(["Subject", "User", "Date"])

        layout = QtWidgets.QVBoxLayout(self)

        self.__splitter.addWidget(self.__treeSubjects)

        self.__group = QtWidgets.QGroupBox(self.__splitter)
        self.__group.setTitle("Edit Comment")
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

        # pylint: disable=no-member
        self.__treeSubjects.itemSelectionChanged.connect(self.__itemChanged)
        self.__comboMacro.currentTextChanged.connect(self.__macroHandle)
        self.__btnSave.pressed.connect(self.__saveComment)
        self.__btnDel.pressed.connect(self.__deleteSelectedComment)
        self.__btnNew.pressed.connect(self.__createNewComment)
        self.__btnClose.pressed.connect(self.__close)
        self.__textSubject.textEdited.connect(self.__textEdited)
        self.__textMessage.textChanged.connect(self.__textEdited)
        # pylint: enable=no-member

        self.refreshComments()
        self.__macroLoad()

    def __textEdited(self, text=None):
        """Called when the text boxes are modified, enables the save button"""
        del text
        self.__textSubject.setReadOnly(False)
        self.__textMessage.setReadOnly(False)
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
        if not self.__textSubject.text():
            cuegui.Utils.showErrorMessageBox("Comment subject cannot be empty")
            return
        if self.__btnSave.text() == SAVE_NEW:
            # If saving a new comment
            self.__addComment(self.__textSubject.text(),
                              self.__textMessage.toPlainText())
            self.refreshComments()
        else:
            # If saving a modified comment
            if self.__treeSubjects.selectedItems():
                for item in self.__treeSubjects.selectedItems():
                    comment = item.getInstance()
                    comment.setSubject(str(self.__textSubject.text()))
                    comment.setMessage(str(self.__textMessage.toPlainText()))
                    comment.save()
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
        item. if the last items from the sources are identical, then they will be selected.
        otherwise no item will be selected. If the user viewing items is not the same
        as comment author, then items will be be read only."""
        # pylint: disable=unnecessary-lambda
        types = map(lambda item: type(item), self.__treeSubjects.selectedItems())
        if self.__treeSubjects.selectedItems():
            if CommentSource in types:
                self.__createNewComment()
            else:
                first_item = self.__treeSubjects.selectedItems()[0]
                # pylint: disable=line-too-long
                identical = all(item.getInstance().message() == first_item.getInstance().message() and
                                item.getInstance().subject() == first_item.getInstance().subject()
                                for item in self.__treeSubjects.selectedItems())
                read_only = any(item.getInstance().user() != cuegui.Utils.getUsername()
                                for item in self.__treeSubjects.selectedItems())
                if identical:
                    for item in self.__treeSubjects.selectedItems():
                        item.setSelected(True)
                    if read_only:
                        self.__textSubject.setReadOnly(True)
                        self.__textMessage.setReadOnly(True)
                    else:
                        self.__textSubject.setReadOnly(False)
                        self.__textMessage.setReadOnly(False)
                    self.__textSubject.setText(first_item.getInstance().subject())
                    self.__textMessage.setText(first_item.getInstance().message())
                    self.__btnSave.setText(SAVE_EDIT)
                    self.__btnSave.setEnabled(False)
                    self.__btnDel.setEnabled(True)
                else:
                    self.__createNewComment()
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
                parent = item.parent()
                parent.removeChild(item)
                item.getInstance().delete()

    def refreshComments(self):
        """Clears and populates the comment list from the cuebot"""
        comments = {}
        for source in self.__source:
            comments[source.data.name] = source.getComments()
        self.__treeSubjects.clear()
        comments_length = 0
        # pylint: disable=consider-using-dict-items
        for source in comments:
            heading = CommentSource(source)
            heading.setSizeHint(0, QtCore.QSize(500, 1))
            self.__treeSubjects.addTopLevelItem(heading)
            for comment in comments[source]:
                item = Comment(comment)
                heading.addChild(item)
                item.setSizeHint(0, QtCore.QSize(300, 1))
                comments_length += 1
        self.__treeSubjects.resizeColumnToContents(0)
        self.__treeSubjects.expandAll()

        last_items = []
        for i in range(self.__treeSubjects.topLevelItemCount()):
            comment_source = self.__treeSubjects.topLevelItem(i)
            comment = comment_source.child(comment_source.childCount()-1)
            if comment:
                last_items.append(comment)
        if not last_items:
            self.__createNewComment()
            return

        identical = all(item.getInstance().message() == last_items[0].getInstance().message() and
                        item.getInstance().subject() == last_items[0].getInstance().subject()
                        for item in last_items)
        read_only = any(elem.getInstance().user() != cuegui.Utils.getUsername()
                        for elem in last_items)

        if identical:
            self.__btnSave.setText(SAVE_EDIT)
            self.__btnSave.setEnabled(False)
            for last_item in last_items:
                last_item.setSelected(True)
            if read_only:
                self.__textSubject.setReadOnly(True)
                self.__textMessage.setReadOnly(True)
            else:
                self.__textSubject.setReadOnly(False)
                self.__textMessage.setReadOnly(False)
        else:
            self.__createNewComment()

    def __macroLoad(self):
        """Loads the defined comment macros from settings"""
        comments_macro = self.app.settings.value("Comments", pickle.dumps({}))
        try:
            self.__macroList = pickle.loads(
                comments_macro if isinstance(comments_macro, bytes) \
                    else comments_macro.encode('UTF-8'))
        except TypeError:
            self.__macroList = pickle.loads(str(comments_macro))
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
        self.app.settings.setValue("Comments", pickle.dumps(self.__macroList))

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
        for source in self.__source:
            source.addComment(str(subject), str(message) or " ")

    def getComments(self):
        """Get Comments"""
        comments = {}
        for source in self.__source:
            comments[source.data.name] = source.getComments()
        return comments


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

        # pylint: disable=no-member
        self.__btnSave.pressed.connect(self.__save)
        self.__btnCancel.pressed.connect(self.reject)
        # pylint: enable=no-member

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


class CommentSource(QtWidgets.QTreeWidgetItem):
    """A widget to represent the heading job/host name of the list of comments"""
    def __init__(self, source):
        QtWidgets.QTreeWidgetItem.__init__(
            self,
            [source])
        self.__source = source

    def getInstace(self):
        """returns the actual comment instance this widget is displaying"""
        return self.__source
