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


"""Wizard interface for setting up dependencies."""


from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from builtins import map
from builtins import str
from builtins import range
import re

from qtpy import QtCore
from qtpy import QtWidgets

import FileSequence
import opencue

import cuegui.Cuedepend
import cuegui.Logger
import cuegui.Utils
import cuegui.ProgressDialog


logger = cuegui.Logger.getLogger(__file__)

__all__ = ["DependWizard"]

# These are the available types of dependencies
JOJ = opencue.api.depend_pb2.JOB_ON_JOB
JOL = opencue.api.depend_pb2.JOB_ON_LAYER
JOF = opencue.api.depend_pb2.JOB_ON_FRAME
LOJ = opencue.api.depend_pb2.LAYER_ON_JOB
LOL = opencue.api.depend_pb2.LAYER_ON_LAYER
LOF = opencue.api.depend_pb2.LAYER_ON_FRAME
FOJ = opencue.api.depend_pb2.FRAME_ON_JOB
FOL = opencue.api.depend_pb2.FRAME_ON_LAYER
FOF = opencue.api.depend_pb2.FRAME_ON_FRAME
FBF = opencue.api.depend_pb2.FRAME_BY_FRAME
LOS = opencue.api.depend_pb2.LAYER_ON_SIM_FRAME
JFBF = "JobFrameByFrame"

# This determines what order each page is displayed in
PAGE_SELECT_DEPEND_TYPE = 10
PAGE_SELECT_JOB_LAYER = 20
PAGE_SELECT_JOB_FRAME = 30
PAGE_SELECT_ONJOB = 40
PAGE_SELECT_ONLAYER = 50
PAGE_SELECT_ONFRAME = 60
PAGE_CONFIRMATION = 100

# This defines the displayed name for each dependency type
DEPEND_NAME = {JOJ: "Job On Job (soft depend)",
                JOL: "Job On Layer",
                JOF: "Job On Frame",
                JFBF: "Frame By Frame for all layers (Hard Depend)",
                LOJ: "Layer On Job",
                LOL: "Layer On Layer",
                LOF: "Layer On Frame",
                FOJ: "Frame On Job",
                FOL: "Frame On Layer",
                FOF: "Frame On Frame",
                FBF: "Frame By Frame",
                LOS: "Layer on Simulation Frame"}

PROGRESS_TITLE = "Cancel setting up dependencies?"
PROGRESS_TEXT = "Are you sure you want to cancel setting up these dependencies?\n\n" + \
                "The dependencies that are already partially setup will still remain."


class DependWizard(QtWidgets.QWizard):
    """Wizard interface for setting up dependencies."""

    def __init__(self, parent, jobs, layers=None, frames=None):
        QtWidgets.QWizard.__init__(self, parent)

        # Only allow jobs from one show
        jobs = [job for job in jobs if job.data.show == jobs[0].data.show]

        self.jobs = jobs
        if layers is None:
            self.layers = []
            self.layerOptions = []
        else:
            self.layers = [layer.data.name for layer in layers]
            self.layerOptions = layers
        if frames is None:
            self.frames = []
        else:
            self.frames = [frame.data.name for frame in frames]

        self.dependType = None
        self.onJobOptions = []
        self.onJob = []
        self.onLayerOptions = []
        self.onLayer = []
        self.onFrame = []

        # Create the pages
        self.__pages = {}
        self.__pages[PAGE_SELECT_DEPEND_TYPE] = PageDependType(self, jobs, layers, frames)
        self.__pages[PAGE_SELECT_JOB_LAYER] = PageSelectLayer(self)
        self.__pages[PAGE_SELECT_JOB_FRAME] = PageSelectFrame(self)
        self.__pages[PAGE_SELECT_ONJOB] = PageSelectOnJob(self)
        self.__pages[PAGE_SELECT_ONLAYER] = PageSelectOnLayer(self)
        self.__pages[PAGE_SELECT_ONFRAME] = PageSelectOnFrame(self)
        self.__pages[PAGE_CONFIRMATION] = PageConfirmation(self, jobs, layers, frames)

        # Add the pages to the wizard
        # pylint: disable=consider-using-dict-items
        for key in self.__pages :
            self.setPage(key, self.__pages[key])

        # Define the start id
        self.setStartId(PAGE_SELECT_DEPEND_TYPE)

        self.setWindowTitle("Dependency Wizard")
        self.setOption(QtWidgets.QWizard.IndependentPages, False)

        self._onJobOptionsPopulate()

        self.show()

    def _onJobOptionsPopulate(self):
        """Populates self.onJobOptions to contain a list of job names for the given job's show."""
        self.onJobOptions = []
        try:
            show = self.jobs[0].data.name.split('-')[0]
            self.onJobOptions = [name for name in sorted(opencue.api.getJobNames())
                                 if name.startswith(show)]
        except opencue.exception.CueException as e:
            logger.critical("Failed getting list of jobs")
            list(map(logger.critical, cuegui.Utils.exceptionOutput(e)))


class AbstractWizardPage(QtWidgets.QWizardPage):
    """Base class for the depend wizard pages."""

    def __init__(self, parent):
        QtWidgets.QWizardPage.__init__(self, parent)
        self.setLayout(QtWidgets.QGridLayout(self))

        self._widgets = []

    def _addLabel(self, text, row, col, rowSpan=1, columnSpan=1, align=QtCore.Qt.AlignLeft):
        """Adds a QLabel to the current WizardPage
        @type  text: str
        @param text: The text to display in the edit box
        @type  row: int
        @param row: The row to place the widget
        @type  col: int
        @param col: The column to place the widget
        @type  rowSpan: int
        @param rowSpan: The number of rows to span with the widget
        @type  columnSpan: int
        @param columnSpan: The number of columns to span with the widget
        @type  align:
        @param align: The text alignment
        @rtype:  QLabel
        @return: A reference to the new widget"""
        label = QtWidgets.QLabel(text, self)
        label.setAlignment(align)
        self.layout().addWidget(label, row, col, rowSpan, columnSpan)
        self._widgets.append(label)
        return label

    def _addTextEdit(self, row, col, text, height=None):
        """Adds a QTextEdit to the current WizardPage
        @type  row: int
        @param row: The row to place the widget
        @type  col: int
        @param col: The column to place the widget
        @type  height: int
        @param height: The fixed height of the label (default = None)
        @rtype:  QTextEdit
        @return: A reference to the new widget"""
        label = QtWidgets.QTextEdit(text, self)
        label.setReadOnly(True)
        label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                                  QtWidgets.QSizePolicy.Maximum))
        if height:
            label.setFixedHeight(height)
        self.layout().addWidget(label, row, col)
        self._widgets.append(label)
        return label

    def _addLineEdit(self, row, col, text):
        """Adds a line edit box to the current WizardPage
        @type  row: int
        @param row: The row to place the widget
        @type  col: int
        @param col: The column to place the widget
        @type  text: str
        @param text: The text to display in the edit box
        @rtype:  QLineEdit
        @return: A reference to the new widget"""
        edit = QtWidgets.QLineEdit(text, self)
        self.layout().addWidget(edit, row, col)
        self._widgets.append(edit)
        return edit

    def _addSpinBox(self, row, col, min_val, max_val, value):
        """Adds a line edit box to the current WizardPage
        @type  row: int
        @param row: The row to place the widget
        @type  col: int
        @param col: The column to place the widget
        @type  min_val: int
        @param min_val: The minimum number to allow
        @type  max_val: int
        @param max_val: The maximum number to allow
        @type  value: int
        @param value: The value to display initially
        @rtype:  QLineEdit
        @return: A reference to the new widget"""
        spin = QtWidgets.QSpinBox(self)
        spin.setRange(min_val, max_val)
        spin.setValue(value)
        self.layout().addWidget(spin, row, col)
        self._widgets.append(spin)
        return spin

    def _addCombo(self, row, col):
        """Adds a combo box to the current WizardPage.
        @type  row: int
        @param row: The row to place the widget
        @type  col: int
        @param col: The column to place the widget
        @rtype:  QComboBox
        @return: A reference to the new widget"""
        combo = QtWidgets.QComboBox()
        self.layout().addWidget(combo, row, col)
        self._widgets.append(combo)
        return combo

    def _addListWidget(self, row, col, selection=None):
        """Adds a QListWidget to the current WizardPage.
        @type  row: int
        @param row: The row to place the widget
        @type  col: int
        @param col: The column to place the widget
        @type  selection: PyQt4.QtGui.SelectionMode
        @param selection: Allowed selection type
        @rtype:  QListWidget
        @return: A reference to the new widget"""
        list_widget = QtWidgets.QListWidget(self)
        if selection:
            list_widget.setSelectionMode(selection)
        self.layout().addWidget(list_widget, row, col)
        self._widgets.append(list_widget)
        return list_widget

    @staticmethod
    def _getNames(items):
        """Returns a list of names for all items provided.
        @type  items: str, list<job>, list<layer>, list<frame> or list<str>
        @param items: Any items to return the names of
        @rtype:  list<str>
        @return: A list of names for the given items"""
        if not items:
            return []
        if isinstance(items, str):
            return [items]
        names_of_items_with_data = [
            item.data.name for item in items
            if hasattr(item, "data") and hasattr(item.data, "name")]
        names_of_items_without_data = [str(item) for item in items if not hasattr(item, "data")]
        return names_of_items_with_data + names_of_items_without_data

    # pylint: disable=inconsistent-return-statements
    def _displayItems(self, name, items, row):
        """Displays a label description and a list of items.
        If more than one item is given
        The label will be "This %{name}:"
        The list will be displayed using a QLabel
        If only one item is given:
        The label with be "These %{name}s:"
        The list will be displayed using a QTextEdit
        @type  name: str
        @param name:
        @type  items: list<str>
        @param items:
        @type  row: int
        @param row: The row to place the widget on
        @rtype:  QTextEdit or QLabel
        @return: A reference to the widget displaying the list"""
        if items:
            if len(items) > 1:
                self._addLabel("These %ss:" % name, row, 0)
            else:
                self._addLabel("This %s:" % name, row, 0)

            if len(items) > 5:
                display = self._addTextEdit(row, 1, "")
            else:
                display = self._addLabel("", row, 1)

            if isinstance(items[0], str):
                display.setText("\n".join(items))
            else:
                display.setText("\n".join(self._getNames(items)))
            return display

    def _removeAllWidgets(self):
        """Removes all widgets references in self._widgets"""
        for widget in reversed(self._widgets):
            self.layout().removeWidget(widget)
            self._widgets.remove(widget)
            widget.hide()


class PageDependType(AbstractWizardPage):
    """This page asks the user for the type of dependency to create.

    PAGE_SELECT_DEPEND_TYPE"""

    def __init__(self, parent, jobs, layers=None, frames=None):
        AbstractWizardPage.__init__(self, parent)

        self.setTitle("Select Dependency Type")

        self.jobs = jobs
        if layers is None:
            self.layers = []
        else:
            self.layers = layers
        if frames is None:
            self.frames = []
        else:
            self.frames = frames

        self._displayItems("Job", jobs, 0)
        self._displayItems("Layer", layers, 1)
        self._displayItems("Frame", frames, 2)

        if frames:
            allowed_options = [FOJ, FOL, FOF]
        elif layers:
            allowed_options = [LOJ, LOL, LOF, FBF]
            if len(layers) == 1:
                allowed_options.extend([FOJ, FOL, FOF])
            allowed_options.extend([LOS])
        elif jobs:
            allowed_options = [JOJ, JOL, JOF, JFBF]
            if len(jobs) == 1:
                allowed_options.extend([LOJ, LOL, LOF, FBF, FOJ, FOL, FOF, LOS])

        # Add the group box for the dependency type options
        self.__groupBox = QtWidgets.QGroupBox()
        self.__groupLayout = QtWidgets.QGridLayout(self.__groupBox)

        # Add the options to the group box
        self.__options = {}
        for option in allowed_options:
            self.__options[option] = QtWidgets.QRadioButton(DEPEND_NAME[option])
            self.__groupLayout.addWidget(self.__options[option])
        self.__options[allowed_options[0]].setChecked(True)

        self.layout().addWidget(self.__groupBox, 3, 0, 1, -1)

    # pylint: disable=inconsistent-return-statements
    def __msg(self):
        for item in [("frame", self.wizard().frames),
                     ("layer", self.wizard().layers),
                     ("job", self.wizard().jobs)]:
            if len(item[1]) > 1:
                return "these %ss" % item[0]
            if item[1]:
                return "this %s" % item[0]

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        self.setSubTitle("What type of dependency would you like %s to have?" % self.__msg())

        # it is not respecting or providing my size hints otherwise
        self.wizard().setMinimumSize(500, 500)

    # pylint: disable=missing-function-docstring
    def validatePage(self):
        # pylint: disable=consider-using-dict-items
        for option in self.__options:
            if self.__options[option].isChecked():
                self.wizard().dependType = option
                return True
        return False

    def nextId(self):
        """Returns the next page id
        @return: next page id
        @rtype:  int"""
        if self.wizard().dependType is None:
            return PAGE_SELECT_DEPEND_TYPE
        if self.frames:
            return PAGE_SELECT_ONJOB
        if len(self.layers) == 1 and \
             self.wizard().dependType in (FOJ, FOL, FOF):
            return PAGE_SELECT_JOB_FRAME
        if self.layers:
            return PAGE_SELECT_ONJOB
        if len(self.jobs) == 1 and \
            self.wizard().dependType in (LOJ, LOL, LOF, FOJ, FOL, FOF, FBF, LOS):
            return PAGE_SELECT_JOB_LAYER
        if self.jobs:
            return PAGE_SELECT_ONJOB
        logger.critical(
            "error, no place to go: jobs:%s layers:%s frames:%s type:%s",
            len(self.jobs), len(self.layers), len(self.frames), self.wizard().dependType)
        raise RuntimeError()


class PageSelectLayer(AbstractWizardPage):
    """This page asks the user for the layer that should depend on something.

    PAGE_SELECT_JOB_LAYER"""

    def __init__(self, parent):
        AbstractWizardPage.__init__(self, parent)

        self.setTitle("Select Layer")
        self.setSubTitle("What layer needs the dependency?")

        self._addLabel("Layer:", 0, 0)

        self.__layerList = self._addListWidget(2, 0, QtWidgets.QAbstractItemView.MultiSelection)

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        self.wizard().layerOptions = self.wizard().jobs[0].getLayers()

        QtWidgets.QWizardPage.initializePage(self)

        self.__layerList.clear()
        self.__layerList.addItems(self._getNames(self.wizard().layerOptions))

        for num in range(self.__layerList.count()):
            self.__layerList.item(num).setSelected(
                str(self.__layerList.item(num).text()) in self._getNames(self.wizard().onLayer))

    # pylint: disable=missing-function-docstring
    def validatePage(self):
        self.wizard().layers = []
        for num in range(self.__layerList.count()):
            if self.__layerList.item(num).isSelected():
                self.wizard().layers.append(str(self.__layerList.item(num).text()))

        if self.wizard().layers:
            return True
        QtWidgets.QMessageBox.warning(
            self, "Warning",
            "Please select one or more layers or go back and change the dependency type",
            QtWidgets.QMessageBox.Ok)
        return False

    def nextId(self):
        """Returns the next page id
        @return: next page id
        @rtype:  int"""
        if self.wizard().dependType in (FOJ, FOL, FOF):
            return PAGE_SELECT_JOB_FRAME
        return PAGE_SELECT_ONJOB


class PageSelectFrame(AbstractWizardPage):
    """This page asks the user for the frames that should depend on something.

    PAGE_SELECT_JOB_FRAME"""

    def __init__(self, parent):
        AbstractWizardPage.__init__(self, parent)

        self.setTitle("Select Frame")
        self.setSubTitle("What frames need the dependency?")

        self._addLabel("Frame:", 0, 0)
        self.__frame = self._addLineEdit(1, 9, "1")
        self.registerField("frame", self.__frame)

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        QtWidgets.QWizardPage.initializePage(self)

    # pylint: disable=missing-function-docstring
    def validatePage(self):
        frames = str(self.field("frame"))
        if frames:
            # pylint: disable=broad-except
            try:
                fs = FileSequence.FrameSet(frames)
                fs.normalize()
                self.wizard().frames = list(map(int, fs.getAll()))
                return True
            except Exception as e:
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
        return False

    def nextId(self):
        """Returns the next page id
        @return: next page id
        @rtype:  int"""
        return PAGE_SELECT_ONJOB


class PageSelectOnJob(AbstractWizardPage):
    """This page asks the user for the job that should be depended on.

    PAGE_SELECT_ONJOB"""

    def __init__(self, parent):
        AbstractWizardPage.__init__(self, parent)

        self.setTitle("Select Job(s) to Depend On")
        self.setSubTitle("What job(s) should it depend on?")

        self._addLabel("Depend on Job:", 0, 0)

        self.__jobFilterLineEdit = self._addLineEdit(2, 0, "")
        self.__jobFilterLineEdit.textChanged.connect(self.filterJobs)  # pylint: disable=no-member

        self.__jobList = self._addListWidget(3, 0)

    def filterJobs(self, text):
        """Pre-filters the list of possible jobs.

        Excludes job names that would cause a job to depend on itself."""
        exclude = []
        if self.wizard().dependType in (JOJ, LOJ, FOJ, JFBF):
            for job in self.wizard().jobs:
                exclude.append(job.data.name)

        self.__jobList.clear()
        self.__jobList.addItems(
            [job for job in self.wizard().onJobOptions
             if re.search(str(text), job, re.IGNORECASE) and job not in exclude])

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        # If the filter edit box is empty, populate it with SHOW-SHOT-USER_
        # based on the first job selected to receive the dependency
        if not self.__jobFilterLineEdit.text():
            self.__jobFilterLineEdit.setText(self.wizard().jobs[0].data.name.split("_")[0] + "_")

        if self.wizard().dependType in (JOJ, LOJ, FOJ, JFBF):
            self.__jobList.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        else:
            self.__jobList.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        for num in range(self.__jobList.count()):
            self.__jobList.item(num).setSelected(
                str(self.__jobList.item(num).text()) in self.wizard().onJob)

        QtWidgets.QWizardPage.initializePage(self)

    # pylint: disable=missing-function-docstring
    def validatePage(self):
        self.wizard().onJob = []
        for num in range(self.__jobList.count()):
            if self.__jobList.item(num).isSelected():
                self.wizard().onJob.append(str(self.__jobList.item(num).text()))

        if self.wizard().onJob:
            return True
        QtWidgets.QMessageBox.warning(self,
                                      "Warning",
                                      "Please select one or more jobs or go back "
                                      "and change the dependency type",
                                      QtWidgets.QMessageBox.Ok)
        return False

    def nextId(self):
        """Returns the next page id
        @return: next page id
        @rtype:  int"""
        if self.wizard().dependType in (JOL, JOF, LOL, LOF, FOL, FOF, FBF, LOS):
            return PAGE_SELECT_ONLAYER
        return PAGE_CONFIRMATION


class PageSelectOnLayer(AbstractWizardPage):
    """This page asks the user for the layer that should be depended on.

    PAGE_SELECT_ONLAYER"""

    def __init__(self, parent):
        AbstractWizardPage.__init__(self, parent)

        self.setTitle("Select Layer to Depend On")
        self.setSubTitle("What Layer should it depend on?")

        self._addLabel("Depend on Layer:", 0, 0)
        self.__onLayerList = self._addListWidget(1, 0)

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        QtWidgets.QWizardPage.initializePage(self)

        self.wizard().onLayerOptions = opencue.api.findJob(self.wizard().onJob[0]).getLayers()

        if self.wizard().dependType in (LOS,):
            self.wizard().onLayerOptions = [
                layer for layer in self.wizard().onLayerOptions
                if 'simulation' in layer.data.services or
                   'simulationhi' in layer.data.services or
                   'houdini' in layer.data.services]

        if self.wizard().dependType in (JOL, LOL, FOL, FBF, JOF, LOF, FOF):
            self.__onLayerList.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        else:
            self.__onLayerList.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        self.__onLayerList.clear()
        self.__onLayerList.addItems(self._getNames(self.wizard().onLayerOptions))

        for num in range(self.__onLayerList.count()):
            self.__onLayerList.item(num).setSelected(
                str(self.__onLayerList.item(num).text()) in self._getNames(self.wizard().onLayer))

    # pylint: disable=missing-function-docstring
    def validatePage(self):
        self.wizard().onLayer = []
        for num in range(self.__onLayerList.count()):
            if self.__onLayerList.item(num).isSelected():
                self.wizard().onLayer.append(str(self.__onLayerList.item(num).text()))

        if self.wizard().onLayer:
            return True
        QtWidgets.QMessageBox.warning(
            self, "Warning",
            "Please select one or more layers or go back and change the dependency type",
            QtWidgets.QMessageBox.Ok)
        return False

    def nextId(self):
        """Returns the next page id
        @return: next page id
        @rtype:  int"""
        if self.wizard().dependType in (JOF, LOF, FOF, LOS):
            return PAGE_SELECT_ONFRAME
        return PAGE_CONFIRMATION


class PageSelectOnFrame(AbstractWizardPage):
    """This page asks the user for the frame that should be depended on.

    PAGE_SELECT_ONFRAME"""

    def __init__(self, parent):
        AbstractWizardPage.__init__(self, parent)

        self.setTitle("Select Frame to Depend On")
        self.setSubTitle("What Frames should it depend on?")

        self._addLabel("Depend on Frame:", 0, 0)
        self.__frame = self._addLineEdit(1, 0, "1")
        self.registerField("onFrame", self.__frame)

        self.setField("onFrame", "")

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        QtWidgets.QWizardPage.initializePage(self)

    # pylint: disable=missing-function-docstring
    def validatePage(self):
        frames = str(self.field("onFrame"))
        if frames:
            # pylint: disable=broad-except
            try:
                fs = FileSequence.FrameSet(frames)
                fs.normalize()
                self.wizard().onFrame = list(map(int, fs.getAll()))
                return True
            except Exception as e:
                list(map(logger.warning, cuegui.Utils.exceptionOutput(e)))
        return False

    def nextId(self):
        """Returns the next page id
        @return: next page id
        @rtype:  int"""
        return PAGE_CONFIRMATION


class PageConfirmation(AbstractWizardPage):
    """Page to collect final confirmation of depend details before creating it.

    PAGE_CONFIRMATION"""

    def __init__(self, parent, jobs, layers, frames):
        del jobs
        del layers
        del frames

        AbstractWizardPage.__init__(self, parent)

        self.work = []

        self.setTitle("Confirmation")
        self.setSubTitle("Are you sure?")

    # pylint: disable=missing-function-docstring
    def initializePage(self):
        self._removeAllWidgets()

        self._displayItems("Dependency type", [DEPEND_NAME[self.wizard().dependType]], 0)

        self._addLabel("", 1, 0)

        self._displayItems("Job", self.wizard().jobs, 2)

        if self.wizard().dependType in (LOJ, LOL, LOF, FOJ, FOL, FOF, FBF, LOS):
            self._displayItems("Layer", self.wizard().layers, 3)
        if self.wizard().dependType in (FOJ, FOL, FOF, LOS):
            self._displayItems("Frame", self.wizard().frames, 4)

        self._addLabel("", 5, 0)
        self._addLabel("Depends on:", 6, 0, 1, -1, QtCore.Qt.AlignCenter)

        self._displayItems("Job", self.wizard().onJob, 7)
        if self.wizard().dependType in (JOL, JOF, LOL, LOF, FOL, FOF, FBF, LOS):
            self._displayItems("Layer", self.wizard().onLayer, 8)
        if self.wizard().dependType in (JOF, LOF, FOF, LOS):
            self._displayItems("Frame", self.wizard().onFrame, 9)

    # pylint: disable=too-many-nested-blocks
    # pylint: disable=missing-function-docstring
    def validatePage(self):
        # Just names:
        jobs = self._getNames(self.wizard().jobs)
        layers = self._getNames(self.wizard().layers)
        frames = self._getNames(self.wizard().frames)
        onJobs = self.wizard().onJob
        onLayers = self.wizard().onLayer or [None]
        onFrames = self.wizard().onFrame or [None]

        self.work = []

        if self.wizard().dependType == JFBF:
            for onJob in onJobs:
                onLayers = opencue.api.findJob(onJob).getLayers()

                for job in jobs:
                    for layer in opencue.api.findJob(job).getLayers():
                        for onLayer in onLayers:
                            if layer.data.type == onLayer.data.type:
                                self.__addDependWork(layer, onLayer)

            cuegui.ProgressDialog.ProgressDialog(
                "Setting up Hard Depend", self.__createFrameByFrameDepend, self.work, 2,
                PROGRESS_TITLE, PROGRESS_TEXT, self.parent())
            return True

        if frames:
            for onJob in onJobs:
                for onLayer in onLayers:
                    for framelayer in frames:
                        if framelayer.find("-") != -1:
                            frame, layer = framelayer.split("-")
                        else:
                            frame = framelayer
                            layer = layers[0]
                        for onFrame in onFrames:
                            self.__addDependWork(
                                self.wizard().dependType, jobs[0], layer, int(frame),
                                onJob, onLayer, onFrame)

        elif layers:
            for onJob in onJobs:
                for onLayer in onLayers:
                    for layer in layers:
                        for onFrame in onFrames:
                            self.__addDependWork(
                                self.wizard().dependType, jobs[0], layer, None,
                                onJob, onLayer, onFrame)

        elif jobs:
            for onJob in onJobs:
                for onLayer in onLayers:
                    for job in jobs:
                        for onFrame in onFrames:
                            self.__addDependWork(
                                self.wizard().dependType, job, None, None, onJob, onLayer, onFrame)

        cuegui.ProgressDialog.ProgressDialog(
            "Setting up dependencies", cuegui.Cuedepend.createDepend, self.work, 2, PROGRESS_TITLE,
            PROGRESS_TEXT, self.parent())
        return True

    def __addDependWork(self, *args):
        """Adds arguments for a call to Cuedepend.createDepend to a list.

        @type  args: string, string, string, int, string, string, int
        @param args: The arguements required by Cuedepend.createDepend"""
        self.work.append(args)

    @staticmethod
    def __createFrameByFrameDepend(layer, onLayer):
        """A function callback provided to the ProgressDialog that sets up a
        frame by frame dependency.

        @type  layer: opencue.wrappers.layer.Layer
        @param layer: The layer that contains the frames that will have the dependency
        @type  onLayer: opencue.wrappers.layer.Layer
        @param onLayer: The layer that contains that frames that will be depended on"""
        layer.createFrameByFrameDependency(onLayer)
