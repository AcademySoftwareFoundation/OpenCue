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


"""Widgets to provide application specific settings."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from collections import OrderedDict

from qtpy import QtCore, QtWidgets

from cuesubmit import Constants
from cuesubmit import Validators
from cuesubmit.ui import Command
from cuesubmit.ui import Widgets
from cuesubmit.ui import Style


class BaseSettingsWidget(QtWidgets.QWidget):
    """Swappable widget to provide application specific settings."""

    dataChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(BaseSettingsWidget, self).__init__(parent)
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.groupBox = QtWidgets.QGroupBox('options')
        self.groupLayout = QtWidgets.QVBoxLayout()
        self.groupBox.setLayout(self.groupLayout)
        self.groupBox.setStyleSheet(Widgets.Style.GROUP_BOX)
        self.mainLayout.addWidget(self.groupBox)
        self.setLayout(self.mainLayout)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

    def getCommandData(self):
        """Override this method to return a dictionary of the settings data."""
        raise NotImplementedError

    def setCommandData(self, commandData):
        """Given a settings data dictionary, set this widget's data."""
        raise NotImplementedError


class InMayaSettings(BaseSettingsWidget):
    """Settings widget to be used when launching from within Maya."""

    # pylint: disable=keyword-arg-before-vararg,unused-argument
    def __init__(self, cameras=None, filename=None, parent=None, *args, **kwargs):
        super(InMayaSettings, self).__init__(parent=parent)
        self.groupBox.setTitle('Maya options')
        self.mayaFileInput = Widgets.CueLabelLineEdit('Maya File:', filename)
        self.fileFilters = Constants.MAYA_FILE_FILTERS
        self.cameraSelector = Widgets.CueSelectPulldown('Render Cameras', options=cameras)
        self.selectorLayout = QtWidgets.QHBoxLayout()
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the Maya-specific widget layout."""
        self.groupLayout.addWidget(self.mayaFileInput)
        self.selectorLayout.addWidget(self.cameraSelector)
        self.selectorLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.groupLayout.addLayout(self.selectorLayout)

    def setupConnections(self):
        """Sets up widget signals."""
        self.mayaFileInput.lineEdit.textChanged.connect(self.dataChanged.emit)  # pylint: disable=no-member
        self.mayaFileInput.setFileBrowsable(fileFilter=self.fileFilters)

    def setCommandData(self, commandData):
        self.mayaFileInput.setText(commandData.get('mayaFile', ''))
        self.cameraSelector.setChecked(commandData.get('camera', '').split(','))

    def getCommandData(self):
        return {
            'mayaFile': self.mayaFileInput.text(),
            'camera': self.cameraSelector.text()
        }


class BaseMayaSettings(BaseSettingsWidget):
    """Standard Maya settings widget to be used from outside Maya."""

    # pylint: disable=keyword-arg-before-vararg,unused-argument
    def __init__(self, parent=None, *args, **kwargs):
        super(BaseMayaSettings, self).__init__(parent=parent)
        self.groupBox.setTitle('Maya options')
        self.mayaFileInput = Widgets.CueLabelLineEdit('Maya File:')
        self.fileFilters = Constants.MAYA_FILE_FILTERS
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the widget layout with a single input for the path to the Maya scene."""
        self.groupLayout.addWidget(self.mayaFileInput)

    def setupConnections(self):
        """Sets up widget signals."""
        self.mayaFileInput.lineEdit.textChanged.connect(self.dataChanged.emit)  # pylint: disable=no-member
        self.mayaFileInput.setFileBrowsable(fileFilter=self.fileFilters)

    def setCommandData(self, commandData):
        self.mayaFileInput.setText(commandData.get('mayaFile', ''))

    def getCommandData(self):
        return {
            'mayaFile': self.mayaFileInput.text(),
        }


class InNukeSettings(BaseSettingsWidget):
    """Settings widget to be used when launching from within Nuke."""

    # pylint: disable=keyword-arg-before-vararg,unused-argument
    def __init__(self, writeNodes=None, filename=None, parent=None, *args, **kwargs):
        super(InNukeSettings, self).__init__(parent=parent)
        self.groupBox.setTitle('Nuke options')
        self.fileInput = Widgets.CueLabelLineEdit('Nuke File:', filename)
        self.fileFilters = Constants.NUKE_FILE_FILTERS
        self.writeNodeSelector = Widgets.CueSelectPulldown('Write Nodes:', emptyText='[All]',
                                                           options=writeNodes)
        self.selectorLayout = QtWidgets.QHBoxLayout()
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the Nuke-specific widget layout."""
        self.groupLayout.addWidget(self.fileInput)
        self.selectorLayout.addWidget(self.writeNodeSelector)
        self.selectorLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.groupLayout.addLayout(self.selectorLayout)

    def setupConnections(self):
        """Sets up widget signals."""
        self.fileInput.lineEdit.textChanged.connect(self.dataChanged.emit)  # pylint: disable=no-member
        self.fileInput.setFileBrowsable(fileFilter=self.fileFilters)

    def setCommandData(self, commandData):
        self.fileInput.setText(commandData.get('nukeFile', ''))
        self.writeNodeSelector.setChecked(commandData.get('writeNodes', '').split(','))

    def getCommandData(self):
        return {
            'nukeFile': self.fileInput.text(),
            'writeNodes': self.writeNodeSelector.text()
        }


class BaseNukeSettings(BaseSettingsWidget):
    """Standard Nuke settings widget to be used from outside Nuke."""

    # pylint: disable=keyword-arg-before-vararg,unused-argument
    def __init__(self, parent=None, *args, **kwargs):
        super(BaseNukeSettings, self).__init__(parent=parent)
        self.groupBox.setTitle('Nuke options')
        self.fileInput = Widgets.CueLabelLineEdit('Nuke File:')
        self.fileFilters = Constants.NUKE_FILE_FILTERS
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the widget layout with a single input for the path to the Nuke script."""
        self.groupLayout.addWidget(self.fileInput)

    def setupConnections(self):
        """Sets up widget signals."""
        self.fileInput.lineEdit.textChanged.connect(self.dataChanged.emit)  # pylint: disable=no-member
        self.fileInput.setFileBrowsable(fileFilter=self.fileFilters)

    def setCommandData(self, commandData):
        self.fileInput.setText(commandData.get('nukeFile', ''))

    def getCommandData(self):
        return {
            'nukeFile': self.fileInput.text(),
        }


class ShellSettings(BaseSettingsWidget):
    """Basic settings widget for submitting simple shell commands."""

    # pylint: disable=keyword-arg-before-vararg,unused-argument
    def __init__(self, parent=None, *args, **kwargs):
        super(ShellSettings, self).__init__(parent=parent)
        self.groupBox.setTitle('Shell options')
        self.commandTextBox = Command.CueCommandWidget()

        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the widget layout with a single input for the shell command."""
        self.groupLayout.addWidget(self.commandTextBox)

    def setupConnections(self):
        """Sets up widget signals."""
        self.commandTextBox.textChanged.connect(lambda: self.dataChanged.emit(None))

    def getCommandData(self):
        return {'commandTextBox': self.commandTextBox.text()}

    def setCommandData(self, commandData):
        self.commandTextBox.setText(commandData.get('commandTextBox', ''))


class BaseBlenderSettings(BaseSettingsWidget):
    """Standard Blender settings widget to be used from outside Blender."""

    # pylint: disable=keyword-arg-before-vararg,unused-argument
    def __init__(self, parent=None, *args, **kwargs):
        super(BaseBlenderSettings, self).__init__(parent=parent)
        self.groupBox.setTitle('Blender options')
        self.fileFilters = Constants.BLENDER_FILE_FILTERS
        self.fileInput = Widgets.CueLabelLineEdit('Blender File:')
        self.outputPath = Widgets.CueLabelLineEdit(
            'Output Path (Optional):',
            tooltip='Optionally set the rendered output format. '
                    'See the "-o" flag of {} for more info.'.format(
                            Constants.BLENDER_OUTPUT_OPTIONS_URL))
        self.outputSelector = Widgets.CueSelectPulldown(
            'Output Format', options=Constants.BLENDER_FORMATS, multiselect=False)
        self.outputLayout = QtWidgets.QHBoxLayout()
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        """Creates the Blender-specific widget layout."""
        self.groupLayout.addWidget(self.fileInput)
        self.groupLayout.addLayout(self.outputLayout)
        self.outputLayout.addWidget(self.outputPath)
        self.outputLayout.addWidget(self.outputSelector)

    def setupConnections(self):
        """Sets up widget signals."""
        # pylint: disable=no-member
        self.fileInput.lineEdit.textChanged.connect(self.dataChanged.emit)
        self.outputPath.lineEdit.textChanged.connect(self.dataChanged.emit)
        self.outputSelector.optionsMenu.triggered.connect(self.dataChanged.emit)
        self.fileInput.setFileBrowsable(fileFilter=self.fileFilters)
        # pylint: enable=no-member

    def setCommandData(self, commandData):
        self.fileInput.setText(commandData.get('nukeFile', ''))
        self.outputPath.setText(commandData.get('outputPath', ''))
        self.outputSelector.setChecked(commandData.get('outputFormat', ''))

    def getCommandData(self):
        return {
            'blenderFile': self.fileInput.text(),
            'outputPath': self.outputPath.text(),
            'outputFormat': self.outputSelector.text()
        }

class DynamicSettingsWidget(BaseSettingsWidget):
    """Dynamic settings widget to be used with the cuesubmit_config.yaml file.
    See `buildDynamicWidgets` for the widgets creation
    """

    def __init__(self, parent=None, tool_name=None, parameters=None):
        super(DynamicSettingsWidget, self).__init__(parent=parent)
        self.groupBox.setTitle(f'{tool_name} options')
        self.widgets = buildDynamicWidgets(parameters)
        self.setupUi()
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Maximum)
        self.setupConnections()

    def setupUi(self):
        """Creates the custom widget layout."""
        for eachWidget in self.widgets:
            self.groupLayout.addWidget(eachWidget)

    def setupConnections(self):
        """Sets up widget signals."""
        for eachWidget in self.widgets:
            for eachSignal in eachWidget.signals:
                if isinstance(eachWidget, Command.CueCommandWidget):
                    eachSignal.connect(lambda: self.dataChanged.emit(None))
                    continue
                eachSignal.connect(self.dataChanged.emit)

    def setCommandData(self, commandData):
        """ Pass command data to each widget """
        for eachWidget in self.widgets:
            eachWidget.setter(commandData.get(eachWidget.command_id))

    def getCommandData(self):
        """ Query each widget's data """
        options = OrderedDict()
        for eachWidget in self.widgets:
            options[eachWidget.command_id] = eachWidget.getter()
        return options

def buildDynamicWidgets(parameters):
    """ Associates a widget to each parameter type
    :param parameters: list of parameters (see Util.convertCommandOptions())
    :type parameters: list<dict>
    :returns: all newly created widgets
    :rtype: list<QWidget>
    """
    widgets = []
    for option in parameters:
        label = option.get('label') or option.get('command_flag')
        validators = None
        if option.get('mandatory'):
            validators = [Validators.notEmptyString]

        if option['type'] is FileNotFoundError:
            widget = Widgets.CueLabelLineEdit( labelText='Error:' )
            widget.disable()
            widget.setText(str(option.get('value')))
            widget.label.setStyleSheet(Style.INVALID_TEXT)

        elif option['type'] in (range, int):
            widget = Widgets.CueLabelSlider(label=f'{label}:',
                                            default_value=option.get('value', 0),
                                            min_value=option.get('min', 0),
                                            max_value=option.get('max', 999),
                                            float_precision=option.get('float_precision'))

        elif option['type'] == bool:
            widget = Widgets.CueLabelToggle(label=f'{label}:',
                                            default_value=option.get('value', False))

        elif option.get('browsable'):
            default_text = option['value']
            if isinstance(option['value'], (list, tuple)):
                default_text = ''
            widget = Widgets.CueLabelLineEdit(labelText=f'{label}:',
                                              defaultText=default_text,
                                              validators=validators)
            # Folder browser (ex: outputFolder/)
            if option.get('browsable') == '/':
                widget.setFolderBrowsable()
            # File browser (ex: sceneFile*)
            elif option.get('browsable') == '*':
                widget.setFileBrowsable(fileFilter=option['value'])

        elif option['type'] == str:
            if option['value'] == '\n':
                widget = Command.CueCommandWidget()
            else:
                widget = Widgets.CueLabelLineEdit(labelText=f'{label}:',
                                                  defaultText=option.get('value', ''),
                                                  validators=validators)

        elif option['type'] in (list, tuple):
            _options = option.get('value', ['No options'])
            widget = Widgets.CueSelectPulldown(labelText=f'{label}:',
                                               options=_options,
                                               multiselect=False)
        else:
            continue

        # Hide widgets containing tokens (#IFRAME#, etc..) or solo flags
        if option['hidden']:
            widget.setDisabled(True)
            widget.setHidden(True)

        # Register widget common attributes
        widget.mandatory = option.get('mandatory')
        widget.default_value = option['value']
        widget.command_flag = option.get('command_flag') # can be None for non flagged options
        # command_id 3-tuple is used in Submission.buildDynamicCmd()
        # it contains (flag, isPath, isMandatory)
        widget.command_id = (option.get('command_flag') or option['option_line'],
                             bool(option.get('browsable')),
                             bool(option.get('mandatory')))
        widgets.append(widget)

    return widgets
