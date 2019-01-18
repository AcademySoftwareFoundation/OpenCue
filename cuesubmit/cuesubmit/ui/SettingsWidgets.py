
from PySide2 import QtCore, QtWidgets

from cuesubmit.ui import Command
from cuesubmit.ui import Widgets


class BaseSettingsWidget(QtWidgets.QWidget):
    """Swappable widget to provide application specific settings. """

    dataChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(BaseSettingsWidget, self).__init__(parent)
        self.mainLayout = QtWidgets.QVBoxLayout()
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

    def __init__(self, cameras=None, filename=None, parent=None, *args, **kwargs):
        super(InMayaSettings, self).__init__(parent=parent)
        self.mayaFileInput = Widgets.CueLabelLineEdit('Maya File:', filename)
        self.cameraSelector = Widgets.CueSelectPulldown('Render Cameras', options=cameras)
        self.selectorLayout = QtWidgets.QHBoxLayout()
        self.setupUi()

    def setupUi(self):
        self.mainLayout.addWidget(self.mayaFileInput)
        self.selectorLayout.addWidget(self.cameraSelector)
        self.selectorLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.mainLayout.addLayout(self.selectorLayout)

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

    def __init__(self, parent=None, *args, **kwargs):
        super(BaseMayaSettings, self).__init__(parent=parent)
        self.mayaFileInput = Widgets.CueLabelLineEdit('Maya File:')
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        self.mainLayout.addWidget(self.mayaFileInput)

    def setupConnections(self):
        self.mayaFileInput.lineEdit.textChanged.connect(self.dataChanged.emit)

    def setCommandData(self, commandData):
        self.mayaFileInput.setText(commandData.get('mayaFile', ''))

    def getCommandData(self):
        return {
            'mayaFile': self.mayaFileInput.text(),
        }


class InNukeSettings(BaseSettingsWidget):
    """Settings widget to be used when launching from within Nuke."""

    def __init__(self, writeNodes=None, filename=None, parent=None, *args, **kwargs):
        super(InNukeSettings, self).__init__(parent=parent)
        self.fileInput = Widgets.CueLabelLineEdit('Nuke File:', filename)
        self.writeNodeSelector = Widgets.CueSelectPulldown('Write Nodes:', emptyText='[All]',
                                                           options=writeNodes)
        self.selectorLayout = QtWidgets.QHBoxLayout()
        self.setupUi()

    def setupUi(self):
        self.mainLayout.addWidget(self.fileInput)
        self.selectorLayout.addWidget(self.writeNodeSelector)
        self.selectorLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.mainLayout.addLayout(self.selectorLayout)

    def setCommandData(self, commandData):
        self.fileInput.setText(commandData.get('nukeFile', ''))
        self.cameraSelector.setChecked(commandData.get('camera', '').split(','))

    def getCommandData(self):
        return {
            'nukeFile': self.fileInput.text(),
            'writeNodes': self.writeNodeSelector.text()
        }


class BaseNukeSettings(BaseSettingsWidget):
    """Standard Nuke settings widget to be used from outside Nuke."""

    def __init__(self, parent=None, *args, **kwargs):
        super(BaseNukeSettings, self).__init__(parent=parent)
        self.fileInput = Widgets.CueLabelLineEdit('Nuke File:')
        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        self.mainLayout.addWidget(self.fileInput)

    def setupConnections(self):
        self.fileInput.lineEdit.textChanged.connect(self.dataChanged.emit)

    def setCommandData(self, commandData):
        self.fileInput.setText(commandData.get('nukeFile', ''))

    def getCommandData(self):
        return {
            'nukeFile': self.fileInput.text(),
        }


class ShellSettings(BaseSettingsWidget):
    """Basic settings widget for submitting simple shell commands."""

    def __init__(self, parent=None, *args, **kwargs):
        super(ShellSettings, self).__init__(parent=parent)

        self.commandTextBox = Command.CueCommandWidget()

        self.setupUi()
        self.setupConnections()

    def setupUi(self):
        self.mainLayout.addWidget(self.commandTextBox)

    def setupConnections(self):
        self.commandTextBox.textChanged.connect(lambda: self.dataChanged.emit(None))

    def getCommandData(self):
        return {'commandTextBox': self.commandTextBox.text()}

    def setCommandData(self, commandData):
        self.commandTextBox.setText(commandData.get('commandTextBox', ''))
