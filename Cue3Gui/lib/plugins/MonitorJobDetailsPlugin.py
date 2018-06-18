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


import os
import time
import Cue3Gui
import Cue3

from PyQt4 import QtGui, QtCore

logger = Cue3Gui.Logger.getLogger(__file__)

PLUGIN_NAME = "Monitor Job Details"
PLUGIN_CATEGORY = "Cuetopia"
PLUGIN_DESCRIPTION = "Monitor a job's layers and frames"
PLUGIN_PROVIDES = "MonitorLayerFramesDockWidget"

class MonitorLayerFramesDockWidget(Cue3Gui.AbstractDockWidget):
    """This builds a display that can monitor the layers and frames of a job."""
    def __init__(self, parent):
        """Creates the dock widget and docks it to the parent.
        @param parent: The main window to dock to
        @type  parent: QMainWindow"""
        Cue3Gui.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__job = None

        self.__monitorLayers = Cue3Gui.LayerMonitorTree(self)
        self.__monitorFrames = Cue3Gui.FrameMonitor(self)
        self.__splitter = QtGui.QSplitter(QtCore.Qt.Vertical)

        self.setAcceptDrops(True)

        self.layout().addWidget(self.__splitter)
        self.__splitter.addWidget(self.__monitorLayers)
        self.__splitter.addWidget(self.__monitorFrames)

        #Signals in:
        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL('view_object(PyQt_PyObject)'), self.__setJob)
        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL('unmonitor(PyQt_PyObject)'), self.__unmonitor)
        QtCore.QObject.connect(QtGui.qApp, QtCore.SIGNAL('facility_changed()'), self.__setJob)

        QtCore.QObject.connect(self.__monitorLayers, QtCore.SIGNAL("handle_filter_layers_byLayer(PyQt_PyObject)"),
                               self.__monitorFrames, QtCore.SIGNAL("handle_filter_layers_byLayer(PyQt_PyObject)"))

        QtCore.QObject.connect(self.__splitter,
                               QtCore.SIGNAL('splitterMoved(int,int)'),
                               self.__splitterMoved)

        self.pluginRegisterSettings([("splitterSize",
                                      self.__splitter.sizes,
                                      self.__splitter.setSizes),
                                     ("frameColumnVisibility",
                                      self.__monitorFrames.getColumnVisibility,
                                      self.__monitorFrames.setColumnVisibility),
                                     ("layerColumnVisibility",
                                      self.__monitorLayers.getColumnVisibility,
                                      self.__monitorLayers.setColumnVisibility),
                                     ("frameColumnWidths",
                                      self.__monitorFrames.getColumnWidths,
                                      self.__monitorFrames.setColumnWidths),
                                     ("layerColumnWidths",
                                      self.__monitorLayers.getColumnWidths,
                                      self.__monitorLayers.setColumnWidths)])

    def __splitterMoved(self, pos, index):
        self.__monitorLayers.disableUpdate = not bool(pos)

    def dragEnterEvent(self, event):
        Cue3Gui.Utils.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        Cue3Gui.Utils.dragMoveEvent(event)

    def dropEvent(self, event):
        for jobName in Cue3Gui.Utils.dropEvent(event):
            self.__setJob(jobName)

    def __setJob(self, job = None):
        if Cue3Gui.Utils.isJob(job) and self.__job and Cue3.id(job) == Cue3.id(self.__job):
            return

        new_job = Cue3Gui.Utils.findJob(job)
        if new_job:
            self.__job = new_job
            self.setWindowTitle("%s" % new_job.data.name)
            self.raise_()

            self.__monitorFrames.setJob(new_job)
            self.__monitorLayers.setJob(new_job)
        elif not job and self.__job:
            self.__unmonitor(self.__job.proxy)

    def __unmonitor(self, proxy):
        """Unmonitors the current job if it matches the supplied proxy.
        @param proxy: A job proxy
        @type  proxy: proxy"""
        if self.__job and self.__job.proxy == proxy:
            self.__job = None
            self.setWindowTitle("Monitor Job Details")

            self.__monitorLayers.setJob(None)
            self.__monitorFrames.setJob(None)
