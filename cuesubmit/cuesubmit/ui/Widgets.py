from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
from PySide2 import QtCore, QtGui, QtWidgets

from cuesubmit import Constants
from cuesubmit.ui import Style


class SpacerTypes(object):
    """Utility object for defining types of Spacers."""
    VERTICAL = (QtWidgets.QSizePolicy.Minimum,
                QtWidgets.QSizePolicy.Expanding)
    HORIZONTAL = (QtWidgets.QSizePolicy.Expanding,
                  QtWidgets.QSizePolicy.Minimum)
    MINIMUM = (QtWidgets.QSizePolicy.Minimum,
               QtWidgets.QSizePolicy.Minimum)
    MAXIMUM = (QtWidgets.QSizePolicy.Maximum,
               QtWidgets.QSizePolicy.Maximum)
    FIXED = (QtWidgets.QSizePolicy.Fixed,
             QtWidgets.QSizePolicy.Fixed)


class CueLabelLineEdit(QtWidgets.QWidget):
    """Container widget that contains a lineedit and label."""
    def __init__(self, labelText=None, defaultText='', tooltip=None, validators=None,
                 completers=None, parent=None):
        super(CueLabelLineEdit, self).__init__(parent)
        self.mainLayout = QtWidgets.QGridLayout()
        self.mainLayout.setVerticalSpacing(0)
        self.label = QtWidgets.QLabel(labelText)
        self.label.setAlignment(QtCore.Qt.AlignLeft)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.lineEdit = CueLineEdit(defaultText, completerStrings=completers)
        self.lineEdit.setToolTip(tooltip)
        self.horizontalLine = CueHLine()
        self.validators = validators or []
        self.setupUi()
        self.setupConnections()
        self.setAutoFillBackground(True)

    def setupUi(self):
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.label, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.lineEdit, 1, 0, 1, 4)
        self.mainLayout.addWidget(self.horizontalLine, 2, 0, 1, 4)
        self.label.setStyleSheet(Style.LABEL_TEXT)

    def setupConnections(self):
        self.lineEdit.textChanged.connect(self.validateText)
        self.lineEdit.focusChange.connect(self.textFocusChange)

    def setText(self, text):
        """Set the text to the given value.
        @type text: str
        @param text: text to set value to
        """
        self.lineEdit.setText(text)

    def textFocusChange(self, value):
        """Highlight the underline when in focus."""
        if value:
            self.horizontalLine.setStyleSheet(Style.UNDERLINE_HIGHLIGHT)
        else:
            self.horizontalLine.setStyleSheet(Style.UNDERLINE)

    def validateText(self):
        """Check validators and set the style of the label."""
        results = [i(self.lineEdit.text()) for i in self.validators]
        if all(results):
            self.label.setStyleSheet(Style.LABEL_TEXT)
            return True
        else:
            self.label.setStyleSheet(Style.INVALID_TEXT)
            return False

    def text(self):
        """Return the current text.
        @rtype: str
        @return: current text
        """
        return self.lineEdit.text()


class CueLineEdit(QtWidgets.QLineEdit):
    """Wrapper around QLineEdit that allows for changing text with up/down arrow keys."""

    focusChange = QtCore.Signal(bool)

    def __init__(self, defaultText=None, completerStrings=None, parent=None):
        super(CueLineEdit, self).__init__(parent=parent)
        self.setText(defaultText)
        self.index = -1
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        self.completer = QtWidgets.QCompleter()
        try:
            self.completerModel = QtCore.QStringListModel()
        except AttributeError:
            self.completerModel = QtGui.QStringListModel()
        self.completerStrings = completerStrings or []
        self.setupCompleter()
        self.setStyleSheet(Style.LINE_EDIT)

    def focusInEvent(self, e):
        super(CueLineEdit, self).focusInEvent(e)
        self.focusChange.emit(True)

    def focusOutEvent(self, e):
        super(CueLineEdit, self).focusOutEvent(e)
        self.focusChange.emit(False)

    def setupCompleter(self):
        """Add completer items """
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completerModel.setStringList(self.completerStrings)
        self.completer.setModel(self.completerModel)
        self.setCompleter(self.completer)

    def keyPressEvent(self, event):
        """Add up and down arrow key events to built in functionality."""
        keyPressed = event.key()
        if keyPressed in [Constants.UP_KEY, Constants.DOWN_KEY, Constants.TAB_KEY]:
            if keyPressed == Constants.UP_KEY:
                self.index = max(0, self.index-1)
            elif keyPressed == Constants.DOWN_KEY:
                self.index = min(len(self.completerStrings) - 1, self.index + 1)
            elif keyPressed == Constants.TAB_KEY and self.completerStrings:
                self.tabPressed()
            if self.completerStrings:
                self.setTextToCompleterIndex()
        super(CueLineEdit, self).keyPressEvent(event)

    def setTextToCompleterIndex(self):
        """Set the current text to current index of the completers."""
        self.setText(self.completerStrings[self.index])

    def tabPressed(self):
        """Action called with the tab key is pressed.
        Completes the string based on the completers.
        """
        current_text = self.text()
        matches = [i for i in self.completerStrings if i.startswith(current_text)]
        if matches:
            self.setText(matches[0])


class CueSelectPulldown(QtWidgets.QWidget):
    """A button that acts like a dropdown and supports multiselect."""

    def __init__(self, labelText=None, emptyText='[None]', options=None, multiselect=True, parent=None):
        super(CueSelectPulldown, self).__init__(parent=parent)
        self.multiselect = multiselect
        self.emptyText = emptyText
        self.mainLayout = QtWidgets.QGridLayout()
        self.setLayout(self.mainLayout)
        self.label = QtWidgets.QLabel(labelText)
        self.toolButton = QtWidgets.QToolButton(parent=self)
        self.optionsMenu = QtWidgets.QMenu(self)
        self.setOptions(options)
        if self.multiselect:
            self.toolButton.setText(self.emptyText)
        else:
            self.setChecked(options[0])
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        self.mainLayout.setVerticalSpacing(1)
        self.mainLayout.addWidget(self.label, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.toolButton, 1, 0, 1, 1)
        self.toolButton.setMenu(self.optionsMenu)
        self.toolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)

    def setupConnections(self):
        self.optionsMenu.triggered.connect(self.updateLabel)

    def setOptions(self, options):
        """Add options to the menu options.
        @type options: list<str>
        @param options: list of options to add
        """
        self.optionsMenu.clear()
        for option in options:
            optionAction = self.optionsMenu.addAction(option)
            optionAction.setCheckable(True)

    def getChecked(self):
        """Return the checked items.
        @rtype: list<str>
        @return: list of checked items
        """
        return [action.text() for action in self.optionsMenu.actions() if action.isChecked()]

    def clearChecked(self):
        """Set all items to be unchecked."""
        for action in self.optionsMenu.actions():
            action.setChecked(False)

    def setChecked(self, actionNames):
        """Set the given actionNames to be checked and update the label.
        @type actionNames: list<str>
        @param actionNames: list of action names to set to checked
        """
        nothingChecked = True
        for action in self.optionsMenu.actions():
            if action.text() in actionNames:
                action.setChecked(True)
                nothingChecked = False
            else:
                action.setChecked(False)
        if nothingChecked:
            if not self.multiselect:
                self.optionsMenu.actions()[0].setChecked(True)
        self.updateLabelText()

    def text(self):
        """Return the tool button's current text value.
        @rtype: str
        @return: string of the current text
        """
        return self.toolButton.text()

    def updateLabel(self, action):
        """Multiselect friendly wrapper for updating the tool button label."""
        if not self.multiselect:
            self.clearChecked()
            action.setChecked(True)
        self.updateLabelText()

    def updateLabelText(self):
        """Update the tool button's label text to be the current checked items."""
        checked = self.getChecked()
        if checked:
            actions = ", ".join(checked)
        else:
            actions = self.emptyText
        self.toolButton.setText(actions)


class CueSpacerItem(QtWidgets.QSpacerItem):
    """A utility SpacerItem that simplifies the creation of QSpacerItems"""

    def __init__(self, spacerType, width=20, height=40):
        """
        @type spacerType: SpacerTypes.type
        @param spacerType: a valid SpacerType
        """
        super(CueSpacerItem, self).__init__(width, height, spacerType[0], spacerType[1])


class CueLabelToggle(QtWidgets.QWidget):
    """Container widget that holds a label and a toggle."""

    valueChanged = QtCore.Signal(int)
    sliderPressed = QtCore.Signal()
    sliderMoved = QtCore.Signal(int)
    sliderReleased = QtCore.Signal()
    actionTriggered = QtCore.Signal(int)
    rangeChanged = QtCore.Signal(int, int)

    def __init__(self, label=None, parent=None):
        super(CueLabelToggle, self).__init__(parent=parent)
        self.mainLayout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel(label, parent=self)
        self.label.setMinimumWidth(120)
        self.label.setAlignment(QtCore.Qt.AlignVCenter)
        self.toggle = CueToggle(parent=self)
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.toggle)
        self.mainLayout.addSpacerItem(CueSpacerItem(SpacerTypes.HORIZONTAL))

    def setupConnections(self):
        self.toggle.valueChanged.connect(self.valueChanged.emit)
        self.toggle.sliderPressed.connect(self.sliderPressed.emit)
        self.toggle.sliderMoved.connect(self.sliderMoved.emit)
        self.toggle.sliderReleased.connect(self.sliderReleased.emit)
        self.toggle.actionTriggered.connect(self.actionTriggered.emit)
        self.toggle.rangeChanged.connect(self.rangeChanged.emit)


class CueToggle(QtWidgets.QSlider):
    """On/Off Toggle switch"""

    def __init__(self, *args, **kwargs):
        super(CueToggle, self).__init__(QtCore.Qt.Horizontal, *args, **kwargs)
        self.state = False
        self.setMinimum(0)
        self.setMaximum(1)
        self.setSingleStep(1)
        self.setFixedWidth(30)
        self.setupConnections()
        self.setStyleSheet(Style.TOGGLE_DEFAULT)

    def setupConnections(self):
        self.valueChanged.connect(self.change)
        self.sliderPressed.connect(self.toggle)

    def change(self):
        """Action when the toggle is dragged."""
        if self.value() == 1:
            self.setStyleSheet(Style.TOGGLE_ENABLED)
        else:
            self.setStyleSheet(Style.TOGGLE_DEFAULT)

    def toggle(self):
        """Action when the toggle is clicked.
        This trigger the change action as well."""
        if self.value() == 0:
            self.setValue(1)
        else:
            self.setValue(0)


class CueHelpWidget(QtWidgets.QWidget):
    """Container widget that adds a help button which shows or hides a help text box.
    Set the helpText to the text you'd like to show and add widgets to the contentLayout."""
    helpText = ""

    def __init__(self, parent=None):
        super(CueHelpWidget, self).__init__(parent=parent)
        self.helpVisible = False
        self.mainLayout = QtWidgets.QGridLayout()
        self.mainLayout.setVerticalSpacing(1)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.mainLayout)

        self.helpButton = CueHelpButton()
        self.helpButton.setAccessibleName('helpButton')
        self.helpButton.setToolTip(self.helpText)
        self.helpTextField = QtWidgets.QTextEdit()

        self.mainLayout.addLayout(self.contentLayout, 0, 0, 1, 4)
        self.mainLayout.addWidget(self.helpButton, 0, 4, 1, 1)
        self.mainLayout.addWidget(self.helpTextField, 1, 0, 1, 5)
        self.mainLayout.addItem(CueSpacerItem(SpacerTypes.VERTICAL), 3, 0, 1, 5)
        self.mainLayout.setVerticalSpacing(0)
        self.mainLayout.setRowStretch(3, 1)

        self.hideHelpText()
        self.setHelpText()
        self.setupHelpConnections()

    def setupHelpConnections(self):
        self.helpButton.clicked.connect(self.toggleHelp)

    def setHelpText(self):
        """Set the help text to the widget."""
        self.setToolTip(self.helpText)
        self.helpTextField.setText(self.helpText)
        self.helpTextField.setReadOnly(True)
        self.helpTextField.setStyleSheet(Style.HELP_TEXT_FIELD)

    def toggleHelp(self):
        """Show or hide the help text area."""
        if self.helpVisible:
            self.hideHelpText()
            self.helpVisible = False
        else:
            self.showHelpText()
            self.helpVisible = True

    def hideHelpText(self):
        """Collapse the help text area."""
        self.helpTextField.setMaximumHeight(0)

    def showHelpText(self):
        """Expand the help text area."""
        self.helpTextField.setMaximumHeight(250)


class CueHelpButton(QtWidgets.QPushButton):
    """Standard help button."""
    def __init__(self, parent=None):
        super(CueHelpButton, self).__init__(parent=parent)
        self.setText('?')
        self.setFixedSize(17, 17)


class CueHLine(QtWidgets.QFrame):
    """A simple horizontal line."""
    def __init__(self):
        super(CueHLine, self).__init__()
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setAccessibleName = 'horizontalLine'


class CueLabelLine(QtWidgets.QWidget):
    """A Horizontal line with a label"""
    def __init__(self, labelText, parent=None):
        super(CueLabelLine, self).__init__(parent)
        self.mainLayout = QtWidgets.QGridLayout()
        self.setLayout(self.mainLayout)
        self.label = QtWidgets.QLabel(labelText)
        self.line = separatorLine()
        self.mainLayout.addWidget(self.label, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.line, 0, 1, 2, 2)
        self.mainLayout.setColumnStretch(1, 1)


def separatorLine():
    """Return a simple separator line."""
    line = QtWidgets.QGroupBox()
    line.setFixedHeight(2)
    line.setAutoFillBackground(True)
    line.setStyleSheet(Style.SEPARATOR_LINE)
    return line


class CueMessageBox(QtWidgets.QMessageBox):
    ''' Display QMessageBox with message and OK button.
        @type message: str
        @param message: error message
        @type title: str
        @param title: box title
        @type parent: QWidget
        @param parent: parent object, used for centering, deleting
        @type centerOnScreen: bool
        @param centerOnScreen: useful mainly for rare cases that parent is not shown yet for centering on desktop
                              If parent is shown,  QMessageBox gets centered into it properly.
    '''
    def __init__(self, message, title=None, parent=None):
        super(CueMessageBox, self).__init__(parent)

        self.setIcon(QtWidgets.QMessageBox.Information)
        self.setText(message)
        self.setWindowTitle(title)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)

    def centerOnScreen(self):
        ''' Useful mainly for rare cases that parent is not shown yet for centering on desktop
                              If parent is shown,  QMessageBox gets centered into it properly.'''
        size = self.size()
        desktopSize = QtWidgets.QDesktopWidget().screenGeometry()
        top = (desktopSize.height() / 2) - (size.height() / 2)
        left = (desktopSize.width() / 2) - (size.width() / 2)
        self.move(left, top)
