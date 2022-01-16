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

from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from NodeGraphQt import NodeGraph
from cuegui.nodegraph import CueLayerNode


class AbstractGraphWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(AbstractGraphWidget, self).__init__(parent=parent)
        self.setupUI()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.setInterval(1000 * 20)

        self.graph.node_selection_changed.connect(self.onNodeSelectionChanged)
        QtGui.qApp.quit.connect(self.timer.stop)

    def setupUI(self):
        '''Setup the UI.'''
        self.graph = NodeGraph()
        try:
            self.graph.register_node(CueLayerNode)
        except Exception:
            pass
        self.graph.viewer().installEventFilter(self)

        # disable editing node connections/dropping new nodes
        self.graph.viewer().search_triggered.disconnect(
            self.graph._on_search_triggered
        )
        self.graph.viewer().connection_sliced.disconnect(
            self.graph._on_connection_sliced
        )
        self.graph.viewer().connection_changed.disconnect(
            self.graph._on_connection_changed
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.graph.viewer())

    def onNodeSelectionChanged(self):
        '''Slot run when a node is selected.

        Updates the nodes to ensure they're visualising current data.
        Can be used to notify other widgets of object selection.
        '''
        self.update()

    def handleSelectObjects(self, rpcObjects):
        '''Select incoming objects in graph.
        '''
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
        '''Return the selected Layer rpcObjects in the graph.
        '''
        rpcObjects = [n.rpcObject for n in self.graph.selected_nodes()]
        return rpcObjects

    def eventFilter(self, target, event):
        '''Override eventFilter

        Centre nodes in graph viewer on 'F' key press.
        '''
        if hasattr(self, 'graph'):
            viewer = self.graph.viewer()
            if target == viewer:
                if event.type() == QtCore.QEvent.KeyPress:
                    if event.key() == QtCore.Qt.Key_F:
                        viewer.center_selection()
                    if event.key() == QtCore.Qt.Key_L:
                        self.layoutGraph()

        return super(AbstractGraphWidget, self).eventFilter(target, event)

    def clearGraph(self):
        '''Clear all nodes from the graph
        '''
        for node in self.graph.all_nodes():
            for port in node.output_ports():
                port.unlock()
            for port in node.input_ports():
                port.unlock()
        self.graph.clear_session()

    def createGraph(self):
        '''Create the graph to visualise OpenCue objects
        '''
        raise NotImplementedError()

    def getRootNodes(self):
        rootNodes = []
        nodes = self.graph.all_nodes()
        for node in nodes:
            if any([p for p in node.inputs().values() if p.connected_ports()]):
                continue
            else:
                rootNodes.append(node)
        return rootNodes

    def getLeafNodes(self):
        leaf_nodes = []
        nodes = self.graph.all_nodes()
        for node in nodes:
            if any(
                [p for p in node.outputs().values() if p.connected_ports()]
            ):
                continue
            else:
                leaf_nodes.append(node)
        return leaf_nodes

    def layoutGraph(self, horizontal=True):
        '''Layout the graph
        '''
        rootNodes = self.getRootNodes()
        numRoots = len(rootNodes)
        for i, node in enumerate(rootNodes):
            if horizontal:
                height = self.nodeHeight()
            else:
                height = self.nodeWidth()
            x = 0
            y = (i - numRoots) * (height + 50)
            if horizontal:
                node.set_pos(x, y)
            else:
                node.set_pos(y, x)
            self.layoutNodeChildren(node, x, y, horizontal=horizontal)

        self.graph.center_on()

    def layoutNodeChildren(self, node, x, y, horizontal=True):
        '''Recursively layout a nodes children relative to itself.
        '''
        ports = []
        for port in node.output_ports():
            ports += port.connected_ports()

        numPorts = len(ports)
        for j, port in enumerate(ports):
            childNode = port.node()

            if horizontal:
                height = self.nodeHeight()
                width = self.nodeWidth()
                childWidth = self.nodeWidth()
            else:
                height = self.nodeWidth()
                width = self.nodeHeight()
                childWidth = self.nodeHeight()

            yDelta = j - (0.5 * (numPorts - 1))
            yPos = y + (yDelta * (height + 100))

            xDelta = (width + childWidth + 100) * 0.5
            xPos = x + xDelta

            if horizontal:
                childNode.set_pos(xPos, yPos)
            else:
                childNode.set_pos(yPos, xPos)

            self.layoutNodeChildren(childNode, xPos, yPos, horizontal=horizontal)

    def nodeWidth(self):
        return max([node.view.width for node in self.graph.all_nodes()])

    def nodeHeight(self):
        return max([node.view.height for node in self.graph.all_nodes()])

    def update(self):
        '''Update nodes with latest data

        This is run every 20 seconds by the timer.
        '''
        raise NotImplementedError()
