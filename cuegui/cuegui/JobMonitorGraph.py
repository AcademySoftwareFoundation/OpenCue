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


import grpc

from qtpy import QtWidgets

from opencue.exception import EntityNotFoundException

import cuegui
import cuegui.Logger
import cuegui.Utils
import cuegui.MenuActions
from cuegui.nodegraph import CueLayerNode
from cuegui.AbstractGraphWidget import AbstractGraphWidget

logger = cuegui.Logger.getLogger(__file__)


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

        try:
            layers = self.job.getLayers()
        except EntityNotFoundException:
            logger.info("Job not found, notifying and clearing job from view")
            cuegui.app().job_not_found.emit(self.job)
            self.setJob(None)
            return
        except grpc.RpcError as e:
            # pylint: disable=no-member
            if hasattr(e, 'code'):
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    logger.info("Job not found, notifying and clearing job from view")
                    cuegui.app().job_not_found.emit(self.job)
                    self.setJob(None)
                    return
                if e.code() == grpc.StatusCode.INTERNAL:
                    # Check if this is specifically a "job not found" error
                    error_details = str(e.details()) if hasattr(e, 'details') else str(e)
                    if "Failed to find job data" in error_details:
                        logger.info("Job data not found (moved to historical data), "
                                    "notifying and clearing job from view")
                        cuegui.app().job_not_found.emit(self.job)
                        self.setJob(None)
                        return
                    logger.error("gRPC INTERNAL error in createGraph: %s", e)
                    return
                if e.code() in [grpc.StatusCode.CANCELLED, grpc.StatusCode.UNAVAILABLE]:
                    logger.warning(
                        "gRPC connection interrupted during graph creation, will retry")
                else:
                    logger.error("gRPC error in createGraph: %s", e)
            else:
                logger.error("gRPC error in createGraph: %s", e)
            # pylint: enable=no-member
            return

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
            try:
                depends = node.rpcObject.getWhatDependsOnThis()
            except (EntityNotFoundException, grpc.RpcError) as e:
                logger.warning("Failed to get dependencies for node %s: %s", node.name(), e)
                continue
            for depend in depends:
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
            try:
                layers = self.job.getLayers()
            except EntityNotFoundException:
                logger.info("Job not found during update, notifying and clearing job from view")
                cuegui.app().job_not_found.emit(self.job)
                self.setJob(None)
                return
            except grpc.RpcError as e:
                # pylint: disable=no-member
                if hasattr(e, 'code'):
                    if e.code() == grpc.StatusCode.NOT_FOUND:
                        logger.info("Job not found during update, notifying and clearing job")
                        cuegui.app().job_not_found.emit(self.job)
                        self.setJob(None)
                        return
                    if e.code() == grpc.StatusCode.INTERNAL:
                        # Check if this is specifically a "job not found" error
                        error_details = str(e.details()) if hasattr(e, 'details') else str(e)
                        if "Failed to find job data" in error_details:
                            logger.info("Job data not found during update, "
                                        "notifying and clearing job from view")
                            cuegui.app().job_not_found.emit(self.job)
                            self.setJob(None)
                            return
                        logger.error("gRPC INTERNAL error in update: %s", e)
                        return
                    if e.code() in [grpc.StatusCode.CANCELLED, grpc.StatusCode.UNAVAILABLE]:
                        logger.warning(
                            "gRPC connection interrupted during graph update, will retry")
                    else:
                        logger.error("gRPC error in update: %s", e)
                else:
                    logger.error("gRPC error in update: %s", e)
                # pylint: enable=no-member
                return

            for layer in layers:
                node = self.graph.get_node_by_name(layer.name())
                if node is not None:
                    node.setRpcObject(layer)
