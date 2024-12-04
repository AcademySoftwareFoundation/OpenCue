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


"""Base class for CueGUI graph widgets."""

from qtpy import QtCore
from qtpy import QtWidgets

from NodeGraphQtPy import NodeGraph
from NodeGraphQtPy.errors import NodeRegistrationError
from cuegui.nodegraph import CueLayerNode
from cuegui import app


class AbstractGraphWidget(QtWidgets.QWidget):
    """Base class for CueGUI graph widgets"""

    def __init__(self, parent=None):
        super(AbstractGraphWidget, self).__init__(parent=parent)
        self.graph = NodeGraph()
        self.setupUI()

        self.timer = QtCore.QTimer(self)
        # pylint: disable=no-member
        self.timer.timeout.connect(self.update)
        self.timer.setInterval(1000 * 20)

        self.graph.node_selection_changed.connect(self.onNodeSelectionChanged)
        app().quit.connect(self.timer.stop)

    def setupUI(self):
        """Setup the UI."""
        try:
            self.graph.register_node(CueLayerNode)
        except NodeRegistrationError:
            pass
        self.graph.viewer().installEventFilter(self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.graph.viewer())

    def onNodeSelectionChanged(self):
        """Slot run when a node is selected.

        Updates the nodes to ensure they're visualising current data.
        Can be used to notify other widgets of object selection.
        """
        self.update()

    def handleSelectObjects(self, rpcObjects):
        """Select incoming objects in graph.
        """
        received = [o.name() for o in rpcObjects]
        current = [rpcObject.name() for rpcObject in self.selectedObjects()]
        if received == current:
            #  prevent recursing
            return

        for node in self.graph.all_nodes():
            node.set_selected(False)
        for rpcObject in rpcObjects:
            node = self.graph.get_node_by_name(rpcObject.name())
            node.set_selected(True)

    def selectedObjects(self):
        """Return the selected nodes rpcObjects in the graph.
        :rtype: [opencue.wrappers.layer.Layer]
        :return: List of selected layers
        """
        rpcObjects = [n.rpcObject for n in self.graph.selected_nodes()]
        return rpcObjects

    def eventFilter(self, target, event):
        """Override eventFilter

        Centre nodes in graph viewer on 'F' key press.

        @param target: widget event occurred on
        @type  target: QtWidgets.QWidget
        @param event: Qt event
        @type  event: QtCore.QEvent
        """
        if hasattr(self, "graph"):
            viewer = self.graph.viewer()
            if target == viewer:
                if event.type() == QtCore.QEvent.KeyPress:
                    if event.key() == QtCore.Qt.Key_F:
                        self.graph.center_on()
                    if event.key() == QtCore.Qt.Key_L:
                        self.graph.auto_layout_nodes()

        return super(AbstractGraphWidget, self).eventFilter(target, event)

    def clearGraph(self):
        """Clear all nodes from the graph
        """
        for node in self.graph.all_nodes():
            for port in node.output_ports():
                port.unlock()
            for port in node.input_ports():
                port.unlock()
        self.graph.clear_session()

    def createGraph(self):
        """Create the graph to visualise OpenCue objects
        """
        raise NotImplementedError()

    def update(self):
        """Update nodes with latest data

        This is run every 20 seconds by the timer.
        """
        raise NotImplementedError()
