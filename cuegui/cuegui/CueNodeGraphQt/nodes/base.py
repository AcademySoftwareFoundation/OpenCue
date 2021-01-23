from builtins import str
from NodeGraphQt import BaseNode
from cuegui.CueNodeGraphQt.widgets.node_property import NodeProgressBar



class CueBaseNode(BaseNode):

    __identifier__ = 'aswf.opencue'

    NODE_NAME = 'Base'

    def __init__(self, rpcObject=None):
        super(CueBaseNode, self).__init__()
        self.add_input(name='parent', multi_input=True, display_name=False)
        self.add_output(name='children', multi_output=True, display_name=False)

        self.__rpcObject = rpcObject

    def rpcObject(self):
        return self.__rpcObject

    def set_rpcObject(self, rpcObject):
        self.__rpcObject = rpcObject

    def add_progress_bar(self, name='', label='', value=0, max=100, format='%p%', tab=None):
        self.create_property(
            name, str(value), tab=tab
        )
        widget = NodeProgressBar(self.view, name, label, value, max=max, format=format)
        widget.value_changed.connect(lambda k, v: self.set_property(k, v))
        self.view.add_widget(widget)
