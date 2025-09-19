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


"""Node graph to display Layers of a Job"""


from qtpy import QtWidgets

import cuegui.Utils
import cuegui.MenuActions
from cuegui.nodegraph import CueLayerNode
from cuegui.AbstractGraphWidget import AbstractGraphWidget


class JobMonitorGraph(AbstractGraphWidget):
    """Graph widget to display connections of layers in a job"""

    def __init__(self, parent=None):
        super(JobMonitorGraph, self).__init__(parent=parent)
        self.job = None
        self.setupContextMenu()

        # wire signals
        cuegui.app().select_layers.connect(self.handleSelectObjects)

    def onNodeSelectionChanged(self):
        """Notify other widgets of Layer selection.

        Emit signal to notify other widgets of Layer selection, this keeps
        all widgets with selectable Layers in sync with each other.

        Also force updates the nodes, as the timed updates are infrequent.
        """
        self.update()
        layers = self.selectedObjects()
        cuegui.app().select_layers.emit(layers)

    def setupContextMenu(self):
        """Setup context menu for nodes in node graph"""
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.update, self.selectedObjects, self.getJob
        )

        menu = self.graph.context_menu().qmenu

        dependMenu = QtWidgets.QMenu("&Dependencies", self)
        self.__menuActions.layers().addAction(dependMenu, "viewDepends")
        self.__menuActions.layers().addAction(dependMenu, "dependWizard")
        dependMenu.addSeparator()
        self.__menuActions.layers().addAction(dependMenu, "markdone")
        menu.addMenu(dependMenu)
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "reorder")
        self.__menuActions.layers().addAction(menu, "stagger")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "setProperties")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "kill")
        self.__menuActions.layers().addAction(menu, "eat")
        self.__menuActions.layers().addAction(menu, "retry")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "retryDead")

    def setJob(self, job):
        """Set Job to be displayed
        @param job: Job to display as node graph
        @type  job: opencue.wrappers.job.Job
        """
        self.timer.stop()
        self.clearGraph()

        if job is None:
            self.job = None
            return

        job = cuegui.Utils.findJob(job)
        self.job = job
        self.createGraph()
        self.timer.start()

    def getJob(self):
        """Return the currently set job
        :rtype: opencue.wrappers.job.Job
        :return: Currently set job
        """
        return self.job

    def selectedObjects(self):
        """Return the selected Layer rpcObjects in the graph.
        :rtype: [opencue.wrappers.layer.Layer]
        :return: List of selected layers
        """
        layers = [n.rpcObject for n in self.graph.selected_nodes() if isinstance(n, CueLayerNode)]
        return layers

    def createGraph(self):
        """Create the graph to visualise the grid job submission
        """
        if not self.job:
            return

        layers = self.job.getLayers()

        # add job layers to tree
        for layer in layers:
            node = CueLayerNode(layer)
            self.graph.add_node(node)
            node.set_name(layer.name())

        # setup connections
        self.setupNodeConnections()

        self.graph.auto_layout_nodes()
        self.graph.center_on()

    def setupNodeConnections(self):
        """Setup connections between nodes based on their dependencies"""
        for node in self.graph.all_nodes():
            for depend in node.rpcObject.getWhatDependsOnThis():
                child_node = self.graph.get_node_by_name(depend.dependErLayer())
                if child_node:
                    # todo check if connection exists
                    child_node.set_input(0, node.output(0))

        for node in self.graph.all_nodes():
            for port in node.output_ports():
                port.lock()
            for port in node.input_ports():
                port.lock()

    def update(self):
        """Update nodes with latest Layer data

        This is run every 20 seconds by the timer.
        """
        if self.job is not None:
            layers = self.job.getLayers()
            for layer in layers:
                node = self.graph.get_node_by_name(layer.name())
                node.setRpcObject(layer)
