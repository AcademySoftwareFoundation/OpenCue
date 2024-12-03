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



"""Plugin for displaying node graph representation of layer in the selected job.

Job selection is triggered by other plugins using the application's view_object signal."""


from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

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
    """Plugin for displaying node graph representation of layer in the selected job."""

    def __init__(self, parent):
        """Creates the dock widget and docks it to the parent.
        @param parent: The main window to dock to
        @type  parent: QMainWindow"""
        cuegui.AbstractDockWidget.AbstractDockWidget.__init__(self, parent, PLUGIN_NAME)

        self.__job = None

        self.__monitorGraph = cuegui.JobMonitorGraph.JobMonitorGraph(self)

        self.setAcceptDrops(True)

        self.layout().addWidget(self.__monitorGraph)

        cuegui.app().view_object.connect(self.__setJob)
        cuegui.app().unmonitor.connect(self.__unmonitor)
        cuegui.app().facility_changed.connect(self.__setJob)

    # pylint: disable=missing-function-docstring
    def dragEnterEvent(self, event):
        cuegui.Utils.dragEnterEvent(event)

    # pylint: disable=missing-function-docstring
    def dragMoveEvent(self, event):
        cuegui.Utils.dragMoveEvent(event)

    # pylint: disable=missing-function-docstring
    def dropEvent(self, event):
        for jobName in cuegui.Utils.dropEvent(event):
            self.__setJob(jobName)

    def __setJob(self, job = None):
        """Set the job to be displayed
        @param job: Selected job
        @type  job: opencue.wrappers.job.Job
        """
        if cuegui.Utils.isJob(job) and self.__job and opencue.id(job) == opencue.id(self.__job):
            return

        newJob = cuegui.Utils.findJob(job)
        if newJob:
            self.__job = newJob
            self.setWindowTitle("%s" % newJob.name())
            self.raise_()

            self.__monitorGraph.setJob(newJob)
        elif not job and self.__job:
            self.__unmonitor(self.__job)

    def __unmonitor(self, proxy):
        """Unmonitors the current job if it matches the supplied proxy.
        @param proxy: A job proxy
        @type  proxy: proxy"""
        if self.__job and self.__job == proxy:
            self.__job = None
            self.setWindowTitle("Monitor Job Graph")

            self.__monitorGraph.setJob(None)
