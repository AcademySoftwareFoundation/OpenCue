from PySide2 import QtGui
from PySide2 import QtWidgets

import cuegui.Utils
import cuegui.MenuActions
from cuegui.CueNodeGraphQt import CueLayerNode
from cuegui.AbstractGraphWidget import AbstractGraphWidget


class JobMonitorGraph(AbstractGraphWidget):

    def __init__(self, parent=None):
        super(JobMonitorGraph, self).__init__(parent=parent)
        self.setup_context_menu()

        # wire signals
        QtGui.qApp.select_layers.connect(self.handle_select_objects)

    def on_node_selection_changed(self):
        '''Notify other widgets of Layer selection.

        Emit signal to notify other widgets of Layer selection, this keeps
        all widgets with selectable Layers in sync with each other.

        Also force updates the nodes, as the timed updates are infrequent.
        '''
        self.update()
        layers = self.selected_objects()
        layer_names = [layer.data.name for layer in layers]
        QtGui.qApp.select_layers.emit(layers)

    def setup_context_menu(self):
        self.__menuActions = cuegui.MenuActions.MenuActions(
            self, self.update, self.selected_objects, self.get_job
        )

        menu = self.graph.context_menu().qmenu

        depend_menu = QtWidgets.QMenu("&Dependencies", self)
        self.__menuActions.layers().addAction(depend_menu, "viewDepends")
        self.__menuActions.layers().addAction(depend_menu, "dependWizard")
        depend_menu.addSeparator()
        self.__menuActions.layers().addAction(depend_menu, "markdone")
        menu.addMenu(depend_menu)
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "useLocalCores")
        self.__menuActions.layers().addAction(menu, "reorder")
        self.__menuActions.layers().addAction(menu, "stagger")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "setProperties")
        menu.addSeparator()
        # self.__menuActions.layers().addAction(menu, "previewRVset")
        # self.__menuActions.layers().addAction(menu, "previewRVmerge")
        # menu.addSeparator()
        # self.__menuActions.layers().addAction(menu, "copyOutputPath")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "kill")
        self.__menuActions.layers().addAction(menu, "eat")
        self.__menuActions.layers().addAction(menu, "retry")
        menu.addSeparator()
        self.__menuActions.layers().addAction(menu, "retryDead")

    def set_job(self, job):
        '''Set Job to be displayed
        '''
        self.timer.stop()
        self.clear_graph()

        if job is None:
            self.job = None
            return

        job = cuegui.Utils.findJob(job)
        self.job = job
        self.create_graph()
        self.layout_graph(horizontal=True)
        self.timer.start()
    
    def get_job(self):
        return self.job

    def selected_objects(self):
        '''Return the selected Layer rpcObjects in the graph.
        '''
        layers = [n.rpcObject() for n in self.graph.selected_nodes() if isinstance(n, CueLayerNode)]
        return layers

    def create_graph(self):
        '''Create the graph to visualise the grid job submission
        '''
        if not self.job:
            return

        layers = self.job.getLayers()

        # add job layers to tree
        for layer in layers:
            node = CueLayerNode(layer)
            self.graph.add_node(node)
            node.set_name(layer.name())

        # setup connections
        self.setup_node_connections()

    def setup_node_connections(self):
        for node in self.graph.all_nodes():
            rpcObject = node.rpcObject()
            for depend in rpcObject.getWhatDependsOnThis():
                child_node = self.graph.get_node_by_name(depend.dependErLayer())
                if child_node:
                    # todo check if connection exists
                    child_node.set_input(0, node.output(0))

    def update(self):
        '''Update nodes with latest Layer data

        This is run every 20 seconds by the timer.
        '''
        layers = self.job.getLayers()
        for layer in layers:
            node = self.graph.get_node_by_name(layer.name())
            node.set_rpcObject(layer)
