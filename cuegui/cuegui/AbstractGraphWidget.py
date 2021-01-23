from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from NodeGraphQt import NodeGraph
from cuegui.CueNodeGraphQt import CueLayerNode


class AbstractGraphWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(AbstractGraphWidget, self).__init__(parent=parent)
        self.setupUI()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.setInterval(1000 * 20)

        self.graph.node_selection_changed.connect(self.on_node_selection_changed)
        QtGui.qApp.quit.connect(self.timer.stop)

    def setupUI(self):
        '''Setup the UI.'''
        self.graph = NodeGraph()
        try:
            self.graph.register_node(CueLayerNode)
            self.graph.register_node(BackdropNode)
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

    def on_node_selection_changed(self):
        '''Slot run when a node is selected.

        Updates the nodes to ensure they're visualising current data.
        Can be used to notify other widgets of object selection.
        '''
        self.update()

    def handle_select_objects(self, rpcObjects):
        '''Select incoming objects in graph.
        '''
        received = [o.data.name for o in rpcObjects]
        current = [rpcObject.data.name for rpcObject in self.selected_objects()]
        if received == current:
            #  prevent recursing
            return

        for node in self.graph.all_nodes():
            node.set_selected(False)
        for rpcObject in rpcObjects:
            node = self.graph.get_node_by_name(rpcObject.data.name)
            node.set_selected(True)

    def selected_objects(self):
        '''Return the selected Layer rpcObjects in the graph.
        '''
        rpcObjects = [n.rpcObject() for n in self.graph.selected_nodes()]
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
                        self.layout_graph()

        return super(AbstractGraphWidget, self).eventFilter(target, event)

    def clear_graph(self):
        '''Clear all nodes from the graph
        '''
        self.graph.clear_session()

    def create_graph(self):
        '''Create the graph to visualise OpenCue objects
        '''
        raise NotImplementedError()

    def get_root_nodes(self):
        root_nodes = []
        nodes = self.graph.all_nodes()
        for node in nodes:
            if any([p for p in node.inputs().values() if p.connected_ports()]):
                continue
            else:
                root_nodes.append(node)
        return root_nodes

    def get_leaf_nodes(self):
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

    def layout_graph(self, horizontal=True):
        '''Layout the graph
        '''
        root_nodes = self.get_root_nodes()
        num_roots = len(root_nodes)
        for i, node in enumerate(root_nodes):
            if horizontal:
                height = self.node_height()
            else:
                height = self.node_width()
            x = 0
            y = (i - num_roots) * (height + 50)
            if horizontal:
                node.set_pos(x, y)
            else:
                node.set_pos(y, x)
            self.layout_node_children(node, x, y, horizontal=horizontal)

        self.graph.center_on()

    def layout_node_children(self, node, x, y, horizontal=True):
        '''Recursively layout a nodes children relative to itself.
        '''
        ports = []
        for port in node.outputs().values():
            ports += port.connected_ports()

        num_ports = len(ports)
        for j, port in enumerate(ports):
            child_node = port.node()

            if horizontal:
                height = self.node_height()
                width = self.node_width()
                child_width = self.node_width()
            else:
                height = self.node_width()
                width = self.node_height()
                child_width = self.node_height()

            y_delta = j - (0.5 * (num_ports - 1))
            y_pos = y + (y_delta * (height + 100))

            x_delta = (width + child_width + 100) * 0.5
            x_pos = x + x_delta

            if horizontal:
                child_node.set_pos(x_pos, y_pos)
            else:
                child_node.set_pos(y_pos, x_pos)

            self.layout_node_children(child_node, x_pos, y_pos, horizontal=horizontal)

    def node_width(self):
        return max([node.view.width for node in self.graph.all_nodes()])

    def node_height(self):
        return max([node.view.height for node in self.graph.all_nodes()])

    def update(self):
        '''Update nodes with latest data

        This is run every 20 seconds by the timer.
        '''
        raise NotImplementedError()
