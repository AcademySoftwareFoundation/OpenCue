from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from PySide2 import QtGui

import opencue

import cuegui.AbstractDockWidget
import cuegui.Logger
import cuegui.Utils

import cuegui.JobMonitorGraph


logger = cuegui.Logger.getLogger(__file__)

PLUGIN_NAME = "Job Graph"
PLUGIN_CATEGORY = "Cuetopia"
PLUGIN_DESCRIPTION = "Visualise a job's layers in a node graph"
PLUGIN_PROVIDES = "MonitorGraphDockWidget"


class MonitorGraphDockWidget(cuegui.AbstractDockWidget.AbstractDockWidget):

    def __init__(self, parent):
        """Creates the dock widget and docks it to the parent.
        @param parent: The main window to dock to
        @type  parent: QMainWindow"""
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__job = None

        self.__monitorGraph = cuegui.JobMonitorGraph.JobMonitorGraph(self)

        self.setAcceptDrops(True)

        self.layout().addWidget(self.__monitorGraph)

        QtGui.qApp.view_object.connect(self.__setJob)
        QtGui.qApp.unmonitor.connect(self.__unmonitor)
        QtGui.qApp.facility_changed.connect(self.__setJob)

    def dragEnterEvent(self, event):
        cuegui.Utils.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        cuegui.Utils.dragMoveEvent(event)

    def dropEvent(self, event):
        for jobName in cuegui.Utils.dropEvent(event):
            self.__setJob(jobName)

    def __setJob(self, job = None):
        if cuegui.Utils.isJob(job) and self.__job and opencue.id(job) == opencue.id(self.__job):
            return

        new_job = cuegui.Utils.findJob(job)
        if new_job:
            self.__job = new_job
            self.setWindowTitle("%s" % new_job.data.name)
            self.raise_()

            self.__monitorGraph.set_job(new_job)
        elif not job and self.__job:
            self.__unmonitor(self.__job)

    def __unmonitor(self, proxy):
        """Unmonitors the current job if it matches the supplied proxy.
        @param proxy: A job proxy
        @type  proxy: proxy"""
        if self.__job and self.__job == proxy:
            self.__job = None
            self.setWindowTitle("Monitor Job Graph")

            self.__monitorGraph.set_job(None)
