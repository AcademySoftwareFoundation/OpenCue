
import getpass

from PySide2 import QtCore, QtGui, QtWidgets

from cuesubmit import Constants
from cuesubmit import JobTypes
from cuesubmit import Layer
from cuesubmit import Submission
from cuesubmit import Util
from cuesubmit import Validators
from cuesubmit.ui import Frame
from cuesubmit.ui import Job
from cuesubmit.ui import Widgets


class CueSubmitButtons(QtWidgets.QWidget):
    """Container widget that holds a cancel and submit button."""

    submitted = QtCore.Signal()
    cancelled = QtCore.Signal()

    def __init__(self, parent=None):
        super(CueSubmitButtons, self).__init__(parent)
        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.setLayout(self.buttonLayout)
        self.submitButton = QtWidgets.QPushButton('Submit', parent=self)
        self.cancelButton = QtWidgets.QPushButton('Cancel', parent=self)
        self.buttonLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.buttonLayout.addWidget(self.cancelButton)
        self.buttonLayout.addWidget(self.submitButton)
        self.state = None
        self.setupConnections()

    def setupConnections(self):
        self.submitButton.pressed.connect(self.submitPressed)
        self.cancelButton.pressed.connect(self.cancelPressed)

    def submitPressed(self):
        self.state = "submitted"
        self.submitted.emit()

    def cancelPressed(self):
        self.state = "cancelled"
        self.cancelled.emit()


class CueSubmitWidget(QtWidgets.QWidget):
    """Central widget for submission."""

    def __init__(self, settingsWidgetType, jobTypes=JobTypes.JobTypes, parent=None, *args, **kwargs):
        super(CueSubmitWidget, self).__init__(parent)
        self.skipDataChangedEvent = False
        self.jobTypes = jobTypes
        self.primaryWidgetType = settingsWidgetType
        self.primaryWidgetArgs = {'args': args, 'kwargs': kwargs}
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addSpacing(0)
        self.mainLayout.setSpacing(0)
        self.jobInfoLayout = QtWidgets.QVBoxLayout()
        self.layerInfoLayout = QtWidgets.QVBoxLayout()
        self.submissionDetailsLayout = QtWidgets.QVBoxLayout()
        self.jobInfoLayout.setContentsMargins(20, 0, 0, 0)
        self.layerInfoLayout.setContentsMargins(20, 0, 0, 0)
        self.submissionDetailsLayout.setContentsMargins(20, 0, 0, 0)
        self.settingsLayout = QtWidgets.QHBoxLayout()

        self.coresLayout = QtWidgets.QHBoxLayout()
        self.servicesLayout = QtWidgets.QHBoxLayout()
        self.showLayout = QtWidgets.QGridLayout()

        self.titleLogo = QtWidgets.QLabel()
        self.titleLogo.setPixmap(QtGui.QPixmap('{}/images/OpenCue.png'.format(Constants.DIR_PATH)))
        self.userNameInput = Widgets.CueLabelLineEdit(
            'User Name:',
            getpass.getuser(),
            tooltip='User name that should be associated with this job.',
            completers=['foo', 'bar'],
            validators=[Validators.matchNoSpecialCharactersOnly]
        )
        self.jobNameInput = Widgets.CueLabelLineEdit(
            'Job Name:',
            tooltip='Job names must be unique.',
            completers=['foo', 'bar'],
            validators=[Validators.matchNoSpecialCharactersOnly]
        )
        shows = Util.getShows()
        self.showSelector = Widgets.CueSelectPulldown(
            'Show:', shows[0],
            options=shows,
            multiselect=False,
            parent=self)
        self.shotInput = Widgets.CueLabelLineEdit('Shot:')
        self.layerNameInput = Widgets.CueLabelLineEdit(
            'Layer Name:',
            tooltip='Name for this layer of the job',
            validators=[Validators.matchNoSpecialCharactersOnly]

        )
        self.frameBox = Frame.FrameSpecWidget()
        jobTypes = self.jobTypes.types()
        self.jobTypeSelector = Widgets.CueSelectPulldown(
            'Job Type:',
            options=jobTypes,
            multiselect=False
        )
        self.jobTypeSelector.setChecked(self.primaryWidgetType)
        self.servicesSelector = Widgets.CueSelectPulldown(
            'Services:',
            options=Util.getServices()
        )
        self.coresInput = Widgets.CueLabelLineEdit(
            'Min Cores:',
            '0',
            tooltip='Minimum number of cores to run. 0 is any',
            validators=[Validators.matchNumbersOnly]
        )
        self.chunkInput = Widgets.CueLabelLineEdit(
            'Chunk Size:',
            '1',
            tooltip='Chunk frames by this value. Integers equal or greater than 1.',
            validators=[Validators.matchPositiveIntegers]
        )
        self.chunkInput.lineEdit.setFixedWidth(120)
        self.dependSelector = Widgets.CueSelectPulldown(
            'Dependency Type:',
            emptyText='',
            options=[Layer.DependType.Null, Layer.DependType.Layer, Layer.DependType.Frame],
            multiselect=False)

        self.settingsWidget = self.jobTypes.build(self.primaryWidgetType, *args, **kwargs)
        self.jobTreeWidget = Job.CueJobWidget()
        self.submitButtons = CueSubmitButtons()
        self.setupUi()
        self.setupConnections()
        self.jobDataChanged()

    def setupConnections(self):
        self.submitButtons.cancelled.connect(self.cancel)
        self.submitButtons.submitted.connect(self.submit)
        self.jobTreeWidget.selectionChanged.connect(self.jobLayerSelectionChanged)
        self.jobNameInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.layerNameInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.frameBox.frameSpecInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.settingsWidget.dataChanged.connect(self.jobDataChanged)
        self.jobTypeSelector.optionsMenu.triggered.connect(self.jobTypeChanged)
        self.servicesSelector.optionsMenu.triggered.connect(self.jobDataChanged)
        self.coresInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.chunkInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.dependSelector.optionsMenu.triggered.connect(self.dependencyChanged)

    def setupUi(self):
        self.setLayout(self.mainLayout)
        self.mainLayout.addWidget(self.titleLogo)
        self.mainLayout.addWidget(Widgets.CueLabelLine('Job Info'))
        self.jobInfoLayout.addWidget(self.jobNameInput)
        self.jobInfoLayout.addWidget(self.userNameInput)
        self.showLayout.setHorizontalSpacing(20)
        self.showLayout.setColumnStretch(1, 1)
        self.showLayout.addWidget(self.showSelector, 0, 0, 1, 1, QtCore.Qt.AlignLeft)
        self.showLayout.addWidget(self.shotInput, 0, 1, 1, 2)
        self.jobInfoLayout.addLayout(self.showLayout)
        self.mainLayout.addLayout(self.jobInfoLayout)

        self.mainLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.VERTICAL))
        self.mainLayout.addWidget(Widgets.CueLabelLine('Layer Info'))
        self.layerInfoLayout.addWidget(self.layerNameInput)
        self.settingsLayout.addWidget(self.settingsWidget)
        self.layerInfoLayout.addLayout(self.settingsLayout)
        self.layerInfoLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.VERTICAL))
        self.layerInfoLayout.addWidget(self.frameBox)

        self.servicesLayout.addWidget(self.jobTypeSelector)
        self.servicesLayout.addWidget(self.servicesSelector)
        self.servicesLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.layerInfoLayout.addLayout(self.servicesLayout)

        self.coresLayout.addWidget(self.coresInput)
        self.coresLayout.addWidget(self.chunkInput)
        self.coresLayout.addWidget(self.dependSelector)
        self.coresLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.layerInfoLayout.addLayout(self.coresLayout)
        self.mainLayout.addLayout(self.layerInfoLayout)

        self.mainLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.VERTICAL))
        self.mainLayout.addWidget(Widgets.CueLabelLine('Submission Details'))

        self.submissionDetailsLayout.addWidget(self.jobTreeWidget)
        self.submissionDetailsLayout.addWidget(self.submitButtons)
        self.mainLayout.addLayout(self.submissionDetailsLayout)

    def dependencyChanged(self):
        """Action called when the dependency type is changed."""
        if self.jobTreeWidget.getCurrentRow() == 0:
            self.dependSelector.setChecked([None])
        self.jobDataChanged()

    def getJobData(self):
        """Return the current job data info from the widget.
        @rtype: dict
        @return: dictionary containing the job submission settings
        """
        return {
            'name': self.jobNameInput.text(),
            'username': self.userNameInput.text(),
            'show': self.showSelector.text(),
            'shot': self.shotInput.text(),
            'layers': self.jobTreeWidget.getAllLayers()
        }

    def jobLayerSelectionChanged(self, layerObject):
        """Action called when the layer selection is changed."""
        if not layerObject.layerType:
            layerObject.update(layerType=self.jobTypes.types()[0])
        self.skipDataChangedEvent = True
        self.layerNameInput.setText(layerObject.name)
        self.frameBox.frameSpecInput.setText(layerObject.layerRange)
        self.updateJobTypeSelector(layerObject.layerType)
        self.servicesSelector.clearChecked()
        self.servicesSelector.setChecked(layerObject.services)
        self.coresInput.setText(str(layerObject.cores))
        self.chunkInput.setText(str(layerObject.chunk))
        self.dependSelector.clearChecked()
        self.dependSelector.setChecked([layerObject.dependType])
        self.settingsWidget.setCommandData(layerObject.cmd)
        self.skipDataChangedEvent = False

    def jobDataChanged(self):
        """Action called when any job data is changed.
        Updates the layer data object.
        """
        if self.skipDataChangedEvent:
            return
        self.jobTreeWidget.updateLayerData(
            name=self.layerNameInput.text(),
            layerType=self.jobTypeSelector.text(),
            cmd=self.settingsWidget.getCommandData(),
            layerRange=self.frameBox.frameSpecInput.text(),
            chunk=None,
            cores=self.coresInput.text(),
            env=None,
            services=[i.strip() for i in self.servicesSelector.text().split(',')],
            dependType=self.dependSelector.text(),
            dependsOn=None
        )
        self.jobTreeWidget.updateJobData(self.jobNameInput.text())

    def jobTypeChanged(self):
        """Action when the job type is changed."""
        self.updateSettingsWidget(self.jobTypeSelector.text())
        self.jobDataChanged()

    def updateJobTypeSelector(self, layerType):
        """Update the job type selector to the given layerType.
        @type layerType: str
        @param layerType: layerType to set the selector to
        """
        self.jobTypeSelector.clearChecked()
        self.jobTypeSelector.setChecked([layerType])
        self.updateSettingsWidget(layerType)

    def updateSettingsWidget(self, layerType):
        """Change the selected layer's settings widget to layerType.
        @type layerType: str
        @param layerType: layerType to switch to."""
        self.settingsLayout.removeWidget(self.settingsWidget)
        self.settingsWidget.deleteLater()
        widgetType = layerType or self.primaryWidgetType
        self.settingsWidget = self.jobTypes.build(widgetType, *self.primaryWidgetArgs['args'],
                                                  **self.primaryWidgetArgs['kwargs'])
        self.settingsWidget.dataChanged.connect(self.jobDataChanged)
        self.settingsLayout.addWidget(self.settingsWidget)

    def submit(self):
        """Submit action to submit a job."""
        Submission.submitJob(self.getJobData())

    def cancel(self):
        """Action called when the cancel button is clicked."""
        self.parentWidget().close()
