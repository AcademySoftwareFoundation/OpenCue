from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from builtins import str
from builtins import range
import getpass

from PySide2 import QtCore, QtGui, QtWidgets

import opencue
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
        self.startupErrors = list()
        self.skipDataChangedEvent = False
        self.settings = QtCore.QSettings('opencue', 'cuesubmit')
        self.clearMessageShown = False
        self.jobTypes = jobTypes
        self.primaryWidgetType = settingsWidgetType
        self.primaryWidgetArgs = {'args': args, 'kwargs': kwargs}
        self.mainLayout = QtWidgets.QVBoxLayout()
        self.mainLayout.addSpacing(0)
        self.mainLayout.setSpacing(0)
        self.scrollArea = QtWidgets.QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollableWidget = QtWidgets.QWidget(self.scrollArea)
        self.scrollArea.setWidget(self.scrollableWidget)
        self.scrollingLayout = QtWidgets.QVBoxLayout()
        self.scrollingLayout.addSpacing(0)
        self.scrollingLayout.setSpacing(0)
        self.scrollableWidget.setLayout(self.scrollingLayout)
        self.mainLayout.addWidget(self.scrollArea)
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
            tooltip='Job names must be unique, have more than 3 characters, and contain no spaces.',
            completers=self.getFilteredHistorySetting('submit/jobName'),
            validators=[Validators.matchNoSpecialCharactersOnly, Validators.moreThan3Chars,
                        Validators.matchNoSpaces]
        )
        shows = Util.getShows()
        if not shows:
            self.startupErrors.append("No shows exist yet. Please create some or contact your OpenCue administrator to create one!\n" +\
                      "You won't be able to submit job for non-existent show!\n")
            shows = ['']  # to allow building UI
        self.showSelector = Widgets.CueSelectPulldown(
            'Show:', shows[0],
            options=shows,
            multiselect=False,
            parent=self)
        self.shotInput = Widgets.CueLabelLineEdit(
            'Shot:',
            tooltip='Name of the shot associated with this submission.',
            completers=self.getFilteredHistorySetting('submit/shotName'),
            validators=[Validators.matchNoSpecialCharactersOnly]
        )
        self.layerNameInput = Widgets.CueLabelLineEdit(
            'Layer Name:',
            tooltip='Name for this layer of the job. Should be more than 3 characters, '
                    'and contain no spaces.',
            completers=self.getFilteredHistorySetting('submit/layerName'),
            validators=[Validators.matchNoSpecialCharactersOnly, Validators.moreThan3Chars,
                        Validators.matchNoSpaces]
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
        self.limitsSelector = Widgets.CueSelectPulldown(
            'Limits:',
            options=Util.getLimits()
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

    def showEvent(self, event):
        if self.startupErrors:
            for startupError in self.startupErrors:
                msgBox = Widgets.CueMessageBox(startupError, title="No Shows Exist", parent=self)
                msgBox.show()
                msgBox.centerOnScreen() #  explicitly center on desktop center as parent is not shown yet

            # Raise at least one of the errors so the user gets feedback in the event the GUI wasn't built
            # or shown properly.
            raise opencue.exception.CueException(self.startupErrors[0])

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
        self.limitsSelector.optionsMenu.triggered.connect(self.jobDataChanged)
        self.coresInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.chunkInput.lineEdit.textChanged.connect(self.jobDataChanged)
        self.dependSelector.optionsMenu.triggered.connect(self.dependencyChanged)

    def setupUi(self):
        self.setLayout(self.mainLayout)
        self.scrollingLayout.addWidget(self.titleLogo)
        self.scrollingLayout.addWidget(Widgets.CueLabelLine('Job Info'))
        self.jobInfoLayout.addWidget(self.jobNameInput)
        self.jobInfoLayout.addWidget(self.userNameInput)
        self.showLayout.setHorizontalSpacing(20)
        self.showLayout.setColumnStretch(1, 1)
        self.showLayout.addWidget(self.showSelector, 0, 0, 1, 1, QtCore.Qt.AlignLeft)
        self.showLayout.addWidget(self.shotInput, 0, 1, 1, 2)
        self.jobInfoLayout.addLayout(self.showLayout)
        self.scrollingLayout.addLayout(self.jobInfoLayout)

        self.scrollingLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.VERTICAL))
        self.scrollingLayout.addWidget(Widgets.CueLabelLine('Layer Info'))
        self.layerInfoLayout.addWidget(self.layerNameInput)
        self.settingsLayout.addWidget(self.settingsWidget)
        self.layerInfoLayout.addLayout(self.settingsLayout)
        self.layerInfoLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.VERTICAL))
        self.layerInfoLayout.addWidget(self.frameBox)

        self.servicesLayout.addWidget(self.jobTypeSelector)
        self.servicesLayout.addWidget(self.servicesSelector)
        self.servicesLayout.addWidget(self.limitsSelector)
        self.servicesLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.layerInfoLayout.addLayout(self.servicesLayout)

        self.coresLayout.addWidget(self.coresInput)
        self.coresLayout.addWidget(self.chunkInput)
        self.coresLayout.addWidget(self.dependSelector)
        self.coresLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.HORIZONTAL))
        self.layerInfoLayout.addLayout(self.coresLayout)
        self.scrollingLayout.addLayout(self.layerInfoLayout)

        self.scrollingLayout.addSpacerItem(Widgets.CueSpacerItem(Widgets.SpacerTypes.VERTICAL))
        self.scrollingLayout.addWidget(Widgets.CueLabelLine('Submission Details'))

        self.submissionDetailsLayout.addWidget(self.jobTreeWidget)
        self.submissionDetailsLayout.addWidget(self.submitButtons)
        self.scrollingLayout.addLayout(self.submissionDetailsLayout)

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
        self.limitsSelector.clearChecked()
        self.limitsSelector.setChecked(layerObject.limits)
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
            chunk=self.chunkInput.text(),
            cores=self.coresInput.text(),
            env=None,
            services=self.servicesSelector.getChecked(),
            limits=self.limitsSelector.getChecked(),
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

    def errorInJobData(self, message):
        Widgets.CueMessageBox(message, title="Error in Job Data", parent=self).show()
        return False

    def validate(self, jobData):
        errMessage = 'ERROR: Job not submitted!\n'
        if not self.jobNameInput.validateText():
            return self.errorInJobData(errMessage + 'Invalid job name.')
        if not self.userNameInput.validateText():
            return self.errorInJobData(errMessage + 'Invalid user name.')
        if not self.shotInput.validateText():
            return self.errorInJobData(errMessage + 'Invalid shot name.')
        if not self.layerNameInput.validateText():
            return self.errorInJobData(errMessage + 'Invalid layer name.')

        if not jobData.get('name'):
            return self.errorInJobData(errMessage + 'Cannot submit without a job name.')

        layers = jobData.get('layers')
        if not layers:
            return self.errorInJobData(errMessage + 'Job has no layers.')

        for layer in layers:
            if not layer.name:
                return self.errorInJobData(errMessage + 'Please ensure all layers have a name.')
            if not layer.layerRange:
                return self.errorInJobData(errMessage +
                                           'Please ensure all layers have a frame range.')
            if not layer.cmd:
                return self.errorInJobData(errMessage +
                                           'Please ensure all layers have a command to run.')
        return True

    def updateCompleters(self):
        """Update the line edit completers after submission."""
        self.jobNameInput.lineEdit.completerStrings = self.getFilteredHistorySetting('submit/jobName')
        self.shotInput.lineEdit.completerStrings = self.getFilteredHistorySetting('submit/shotName')
        self.layerNameInput.lineEdit.completerStrings = self.getFilteredHistorySetting('submit/layerName')


    def getFilteredHistorySetting(self, setting):
        """Return a list of strings for the provided setting.
        Filtering out any None objects.
        @type setting: str
        @param setting: name of setting to get
        @rtype: list<str>
        @return: A list of strings of setting values.
        """
        try:
            return [str(value) for value in self.getHistorySetting(setting) if value is not None]
        except Exception:
            self.errorReadingSettings()
            return []

    def errorReadingSettings(self):
        """Display an error message and clear the QSettings object."""
        if not self.clearMessageShown:
            Widgets.CueMessageBox(
                "Previous submission history cannot be read from the QSettings."
                "Clearing submission history.",
                title="Cannot Read History",
                parent=self).show()
        self.clearMessageShown = True
        self.settings.clear()

    def getHistorySetting(self, setting):
        """Return a list of strings for the provided setting.
        @type setting: str
        @param setting: name of setting to get
        @rtype: list<str>
        @return: A list of strings of setting values.
        """
        size = self.settings.beginReadArray('history')
        previousValues = []
        for settingIndex in range(size):
            self.settings.setArrayIndex(settingIndex)
            previousValues.append(self.settings.value(setting))
        self.settings.endArray()
        return previousValues

    def writeHistorySetting(self, setting, values):
        """Update the QSettings object for the provided setting with values.
        @type setting: str
        @param setting: name of settings to set
        @type values: list<str>
        @param values: values to set as settings
        """
        self.settings.beginWriteArray('history')
        for settingIndex, savedValue in enumerate(values):
            self.settings.setArrayIndex(settingIndex)
            self.settings.setValue(setting, savedValue)
        self.settings.endArray()

    def updateSettingItem(self, setting, value, maxSettings=10):
        """Update the QSettings list entry for the provided setting.
        Keep around a history of the last `maxSettings` number of entries.
        @type setting: str
        @param setting: name of the setting to set
        @type value: object
        @param value: new object to add to settings
        @type maxSettings: int
        @param maxSettings: maximum number of items to keep a history of
        """
        try:
            if not value:
                return
            values = self.getHistorySetting(setting)

            if value in values:
                index = values.index(value)
            else:
                index = -1
            if len(values) == maxSettings or index != -1:
                values.pop(index)
            values.insert(0, value)

            self.writeHistorySetting(setting, values)
        except Exception:
            self.errorReadingSettings()

    def saveSettings(self, jobData):
        """Update the QSettings with the values from the form.
        @type jobData: dict
        @param jobData: dictionary containing the job submission data.
        """
        self.updateSettingItem('submit/jobName', jobData.get('name'))
        self.updateSettingItem('submit/shotName', jobData.get('shot'))
        for layer in jobData.get('layers'):
            self.updateSettingItem('submit/layerName', layer.name)

    def submit(self):
        """Submit action to submit a job."""
        jobData = self.getJobData()
        if not self.validate(jobData):
            return
        self.clearMessageShown = False
        self.saveSettings(jobData)
        self.updateCompleters()
        try:
            jobs = Submission.submitJob(jobData)
        except opencue.exception.CueException as e:
            message = "Failed to submit job!\n" + e.message
            Widgets.CueMessageBox(message, title="Failed Job Submission", parent=self).show()
            raise e

        message = "Submitted Job to OpenCue."
        for job in jobs:
            message += "\nJob ID: {}\nJob Name: {}".format(job.id(), job.name())
        Widgets.CueMessageBox(message, title="Submitted Job Data", parent=self).show()

    def cancel(self):
        """Action called when the cancel button is clicked."""
        self.parentWidget().close()
