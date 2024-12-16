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


"""Collection of utility widgets used throughout the main widget code."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import object
from functools import partial

from qtpy import QtCore, QtGui, QtWidgets

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
    textChanged = QtCore.Signal()
    stateChanged = QtCore.Signal()

    def __init__(self, labelText=None, defaultText='', tooltip=None, validators=None,
                 toggleable=False, toggleValue=False, horizontal=False,
                 completers=None, parent=None):
        super(CueLabelLineEdit, self).__init__(parent)
        self.mainLayout = QtWidgets.QGridLayout()
        self.mainLayout.setVerticalSpacing(0)
        self.toggleable = toggleable
        if self.toggleable:
            self.label = CueLabelToggle(labelText, default_value=toggleValue,
                                        tooltip=tooltip, parent=self)
        else:
            self.label = QtWidgets.QLabel(labelText)
            self.label.setAlignment(QtCore.Qt.AlignLeft)
        self.lineEdit = CueLineEdit(defaultText, completerStrings=completers)
        self.lineEdit.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.lineEdit.setToolTip(tooltip)
        self.browseButton = QtWidgets.QPushButton(text='Browse')
        self.horizontalLine = CueHLine()
        self.horizontal = int(horizontal)
        self.validators = validators or []
        self.signals = [self.lineEdit.textChanged,
                        self.lineEdit.focusChange]
        self.getter = self.lineEdit.text
        self.setter = self.setText
        self.setupUi()
        self.setupConnections()
        self.setAutoFillBackground(True)
        self.validateText()

    def setupUi(self):
        """Creates the widget layout."""
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.label, 0, 0, 1, 1)
        self.mainLayout.addWidget(self.lineEdit, 1-self.horizontal, self.horizontal, 1, 4)
        self.mainLayout.addWidget(self.horizontalLine, 2-self.horizontal, self.horizontal, 1, 4)
        self.browseButton.setVisible(False)
        self.label.setStyleSheet(Style.LABEL_TEXT)

    def setupConnections(self):
        """Sets up widget signals."""
        # pylint: disable=no-member
        self.lineEdit.textChanged.connect(self.validateText)
        self.lineEdit.textChanged.connect(self.textChanged)
        self.lineEdit.focusChange.connect(self.textFocusChange)
        if self.toggleable:
            self.label.toggle.valueChanged.connect(self.toggled)
            self.toggled(self.label.toggle.value())
        # pylint: enable=no-member

    @property
    def toggleValue(self):
        """ Return the current toggle value """
        if self.toggleable:
            return self.label.toggle.value()
        return True

    def setFileBrowsable(self, fileFilter=None):
        """ Displays the Browse button and hook it to a fileBrowser with optional file filters

        :param fileFilter: single or multiple file filters (ex: 'Maya Ascii File (*.ma)')
        :type fileFilter: str or list
        """
        self._showBrowseButton()
        if isinstance(fileFilter, (list, tuple)):
            fileFilter = ';;'.join(fileFilter)
        # pylint: disable=no-member
        self.browseButton.clicked.connect(partial(_setBrowseFileText,
                                                  widget_setter=self.setter,
                                                  fileFilter=fileFilter))

    def setFolderBrowsable(self):
        """ Displays the Browse button and hook it to a folderBrowser """
        self._showBrowseButton()
        # pylint: disable=no-member
        self.browseButton.clicked.connect(partial(_setBrowseFolderText,
                                                  widget_setter=self.setter))

    def _showBrowseButton(self):
        """ Re-layout lineEdit and browse button and display it """
        self.mainLayout.removeWidget(self.lineEdit)
        self.mainLayout.addWidget(self.lineEdit, 1, 0, 1, 3)
        self.mainLayout.addWidget(self.browseButton, 1, 3, 1, 1)
        self.browseButton.setVisible(True)

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
        self.label.setStyleSheet(Style.INVALID_TEXT)
        return False

    def text(self):
        """Return the current text.
        @rtype: str
        @return: current text
        """
        return self.lineEdit.text()

    def disable(self):
        """Make widget grey and read-only"""
        self.lineEdit.setReadOnly(True)
        self.lineEdit.setStyleSheet(Style.DISABLED_LINE_EDIT)
        self.stateChanged.emit()

    def enable(self):
        """Make widget editable"""
        self.lineEdit.setReadOnly(False)
        self.lineEdit.setStyleSheet(Style.LINE_EDIT)
        self.stateChanged.emit()

    def toggled(self, value):
        """Action when the toggle is clicked."""
        if value:
            self.enable()
        else:
            self.disable()


class CueLineEdit(QtWidgets.QLineEdit):
    """Wrapper around QLineEdit that allows for changing text with up/down arrow keys."""

    focusChange = QtCore.Signal(bool)

    def __init__(self, defaultText=None, completerStrings=None, parent=None):
        super(CueLineEdit, self).__init__(parent=parent)
        self.setText(defaultText)
        self.index = -1
        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Fixed)
        self.completer = QtWidgets.QCompleter()
        # pylint: disable=c-extension-no-member
        try:
            self.completerModel = QtCore.QStringListModel()
        except AttributeError:
            self.completerModel = QtGui.QStringListModel()
        self.completerStrings = completerStrings or []
        self.setupCompleter()
        self.setStyleSheet(Style.LINE_EDIT)

    def focusInEvent(self, e):
        """Event when in focus"""
        super(CueLineEdit, self).focusInEvent(e)
        self.focusChange.emit(True)

    def focusOutEvent(self, e):
        """Event when out of focus"""
        super(CueLineEdit, self).focusOutEvent(e)
        self.focusChange.emit(False)

    def setupCompleter(self):
        """Add completer items """
        self.completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.completerModel.setStringList(self.completerStrings)
        self.completer.setModel(self.completerModel)
        self.completer.popup().setStyleSheet(Style.POPUP_LIST_VIEW)
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

    def __init__(
            self, labelText=None, emptyText='[None]', options=None,
            tooltip=None, multiselect=True, parent=None):
        super(CueSelectPulldown, self).__init__(parent=parent)
        self.multiselect = multiselect
        self.emptyText = emptyText
        self.mainLayout = QtWidgets.QGridLayout()
        self.setLayout(self.mainLayout)
        self.label = QtWidgets.QLabel(labelText)
        self.toolButton = QtWidgets.QToolButton(parent=self)
        self.optionsMenu = QtWidgets.QMenu(self)
        self.optionsMenu.setStyleSheet(Style.PULLDOWN_LIST)
        self.setOptions(options)
        self.setToolTip(tooltip)
        self.signals = [self.optionsMenu.triggered]
        self.getter = self.text
        self.setter = self.setCheckedFromText
        if self.multiselect:
            self.toolButton.setText(self.emptyText)
        else:
            default_option = self.emptyText if self.emptyText in options else options[0]
            self.setChecked([default_option])
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the widget layout."""
        self.mainLayout.setVerticalSpacing(1)
        self.mainLayout.addWidget(self.label, 0, 0, 1, 2)
        self.mainLayout.addWidget(self.toolButton, 1, 0, 1, 2)
        self.toolButton.setMenu(self.optionsMenu)
        self.toolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)

    def setupConnections(self):
        """Sets up widget signals."""
        self.optionsMenu.triggered.connect(self.updateLabel)  # pylint: disable=no-member

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

    def setCheckedFromText(self, actionsAstext):
        """Set the given actionNames to be checked and update the label.
        @type actionNames: str
        @param actionNames: list of action names to set to checked separated by a comma and a space
        """
        if ', ' in actionsAstext and self.multiselect:
            self.setChecked(actionsAstext.split(', '))
        else:
            self.setChecked([actionsAstext])

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


class CueLabelSlider(QtWidgets.QWidget):
    """Container widget that holds a label and an int or float slider.
    Behaves as a float slider when providing a float_precision
    """

    valueChanged = QtCore.Signal(int)
    sliderMoved = QtCore.Signal(int)
    sliderReleased = QtCore.Signal()
    actionTriggered = QtCore.Signal(int)
    rangeChanged = QtCore.Signal(int, int)

    def __init__(self, label=None, parent=None,
                 default_value=0,
                 min_value=0,
                 max_value=999,
                 float_precision=None):
        super(CueLabelSlider, self).__init__(parent=parent)
        self._labelValue = f'{label} ({{value}})'
        self.float_mult = 1
        if float_precision:
            self.float_mult = 10**float_precision
        self.mainLayout = QtWidgets.QHBoxLayout()
        self.label = QtWidgets.QLabel(self._labelValue.format(value=default_value), parent=self)
        self.label.setMinimumWidth(120)
        self.label.setAlignment(QtCore.Qt.AlignVCenter)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, parent=self)
        self.slider.setMinimumWidth(120)
        self.slider.setMinimum(min_value*self.float_mult)
        self.slider.setMaximum(max_value*self.float_mult)
        self.setValue(default_value)
        self.slider.setSingleStep(1)
        self.signals = [self.valueChanged]
        self.getter = self.getValue
        self.setter = self.setValue
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the widget layout."""
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.label)
        self.mainLayout.addWidget(self.slider)

    def setupConnections(self):
        """Sets up widget signals."""
        self.valueChanged.connect(self.updateLabelValue)
        # pylint: disable=no-member
        self.slider.valueChanged.connect(self.valueChanged.emit)
        self.slider.sliderMoved.connect(self.sliderMoved.emit)
        self.slider.sliderReleased.connect(self.sliderReleased.emit)
        self.slider.actionTriggered.connect(self.actionTriggered.emit)
        self.slider.rangeChanged.connect(self.rangeChanged.emit)
        # pylint: enable=no-member

    def updateLabelValue(self, value):
        """ Updates the label with the slider's value at the end

        :param value: current slider integer value
        :type value: int
        """
        if self.float_mult!=1:
            value = value*1./self.float_mult
        self.label.setText(self._labelValue.format(value=value))

    def getValue(self):
        """ Query the slider's value
        :returns: slider's value
        :rtype: int or float
        """
        if self.float_mult!=1:
            return self.slider.value()*1./self.float_mult
        return self.slider.value()

    def setValue(self, value):
        """ Set the slider's value (consider the float multiplier)

        :param value: current slider integer value
        :type value: int
        """
        self.slider.setValue(value*self.float_mult)


class CueLabelToggle(QtWidgets.QWidget):
    """Container widget that holds a label and a toggle."""

    valueChanged = QtCore.Signal(int)
    sliderPressed = QtCore.Signal()
    sliderMoved = QtCore.Signal(int)
    sliderReleased = QtCore.Signal()
    actionTriggered = QtCore.Signal(int)
    rangeChanged = QtCore.Signal(int, int)

    def __init__(self, label=None, tooltip=None, default_value=False, parent=None):
        super(CueLabelToggle, self).__init__(parent=parent)
        self.mainLayout = QtWidgets.QHBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.toggle = CueToggle(parent=self)
        self.toggle.setValue(default_value)
        self.label = QtWidgets.QLabel(label, parent=self)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.label.setAlignment(QtCore.Qt.AlignVCenter)
        self.setToolTip(tooltip)
        self.signals = [self.toggle.valueChanged]
        self.getter = self.toggle.value
        self.setter = self.toggle.setValue
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the widget layout."""
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.toggle)
        self.mainLayout.addWidget(self.label)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)

    # pylint: disable=unused-argument
    def mousePressEvent(self, mouseEvent):
        """Passes any mousePressEvent to the toggle, this way we can click on the label."""
        self.toggle.toggle()

    def setupConnections(self):
        """Sets up widget signals."""
        # pylint: disable=no-member
        self.toggle.valueChanged.connect(self.valueChanged.emit)
        self.toggle.sliderPressed.connect(self.sliderPressed.emit)
        self.toggle.sliderMoved.connect(self.sliderMoved.emit)
        self.toggle.sliderReleased.connect(self.sliderReleased.emit)
        self.toggle.actionTriggered.connect(self.actionTriggered.emit)
        self.toggle.rangeChanged.connect(self.rangeChanged.emit)
        # pylint: enable=no-member


class CueToggle(QtWidgets.QSlider):
    """On/Off Toggle switch"""

    def __init__(self, *args, **kwargs):
        super(CueToggle, self).__init__(QtCore.Qt.Horizontal, *args, **kwargs)
        self.state = False
        self.setMinimum(0)
        self.setMaximum(1)
        self.setSingleStep(1)
        self.setFixedWidth(30)
        self.setFixedHeight(20)
        self.setupConnections()
        self.setStyleSheet(Style.TOGGLE_DEFAULT)

    def setupConnections(self):
        """Sets up widget signals."""
        # pylint: disable=no-member
        self.valueChanged.connect(self.change)
        self.sliderPressed.connect(self.toggle)
        # pylint: enable=no-member

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
        self.mainLayout.setVerticalSpacing(0)
        self.mainLayout.setRowStretch(3, 1)

        self.hideHelpText()
        self.setHelpText()
        self.setupHelpConnections()

    def setupHelpConnections(self):
        """Sets up widget signal for the help button."""
        self.helpButton.clicked.connect(self.toggleHelp)  # pylint: disable=no-member

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

def getFile(fileFilter=None):
    """ Opens a file browser and returns the result
    :param fileFilter: optional filters
      (ex: "Maya Ascii File (*.ma);;Maya Binary File (*.mb);;Maya Files (*.ma *.mb)")
    :type fileFilter: str
    :returns: Name of the file
    :rtype: str
    """
    filename, _ = QtWidgets.QFileDialog.getOpenFileName(
        caption='Select file',
        dir='.',
        filter=fileFilter
    )
    return filename

def getFolder():
    """ Opens a folder browser and returns the result
    :returns: Name of the folder
    :rtype: str
    """
    folder = QtWidgets.QFileDialog.getExistingDirectory(
        caption='Select folder',
        dir='.',
        filter=''
    )
    return folder

def _setBrowseFileText(widget_setter, fileFilter):
    """ wrapper function to open a fileBrowser and set its result back in the widget
    :param widget_setter: widget's function to set its text
    :type widget_setter: function
    :param fileFilter: optional filters
       (ex: "Maya Ascii File (*.ma);;Maya Binary File (*.mb);;Maya Files (*.ma *.mb)")
    :type fileFilter: str
    """
    result = getFile(fileFilter)
    widget_setter(result)

# pylint: disable=keyword-arg-before-vararg,unused-argument
def _setBrowseFolderText(widget_setter):
    """ wrapper function to open a folderBrowser and set its result back in the widget
    :param widget_setter: widget's function to set its text
    :type widget_setter: function
    """
    result = getFolder()
    widget_setter(result)

class CueMessageBox(QtWidgets.QMessageBox):
    """A QMessageBox with message and OK button."""

    def __init__(self, message, title=None, parent=None):
        """
        @type message: str
        @param message: error message
        @type title: str
        @param title: box title
        @type parent: QWidget
        @param parent: parent object"""
        super(CueMessageBox, self).__init__(parent)

        self.setIcon(QtWidgets.QMessageBox.Information)
        self.setText(message)
        self.setWindowTitle(title)
        self.setStandardButtons(QtWidgets.QMessageBox.Ok)

    def centerOnScreen(self):
        """Centers the message box on screen.

        Useful mainly for rare cases that parent is not shown yet for centering on desktop.
        If parent is shown, QMessageBox gets centered into it properly."""
        size = self.size()
        desktopSize = QtWidgets.QDesktopWidget().screenGeometry()
        top = (desktopSize.height() / 2) - (size.height() / 2)
        left = (desktopSize.width() / 2) - (size.width() / 2)
        self.move(left, top)
